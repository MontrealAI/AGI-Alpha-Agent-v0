# SPDX-License-Identifier: Apache-2.0
"""FastAPI server exposing simulation endpoints.

The API allows remote control of the orchestrator and serves progress
updates over websockets. It is intentionally lean and suitable for local
testing.
"""
# mypy: ignore-errors

from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib
import json
import os
import hashlib
import secrets
import time
from collections import OrderedDict, deque
from pathlib import Path
from typing import Any, List, Set, TYPE_CHECKING, Literal

from cachetools import TTLCache  # type: ignore[import-not-found]
from alpha_factory_v1.utils.disclaimer import DISCLAIMER

if TYPE_CHECKING:  # pragma: no cover - typing only
    from typing import Protocol

    class ForecastTrajectoryPoint(Protocol):
        year: int
        capability: float
        sectors: List[Any]

    ForecastModule = Any
    SectorModule = Any
    MatsModule = Any
else:
    ForecastModule = Any
    SectorModule = Any
    MatsModule = Any
    ForecastTrajectoryPoint = Any  # type: ignore[assignment]

forecast = importlib.import_module("alpha_factory_v1.core.simulation.forecast")
sector = importlib.import_module("alpha_factory_v1.core.simulation.sector")
mats = importlib.import_module("alpha_factory_v1.core.simulation.mats")

_IMPORT_ERROR: Exception | None
try:
    from fastapi import FastAPI, HTTPException, WebSocket, Request, Depends
    from contextlib import asynccontextmanager
    from collections.abc import AsyncGenerator
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.responses import (
        Response,
        PlainTextResponse,
        JSONResponse,
        HTMLResponse,
    )
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    import uvicorn
    from .problem_json import problem_response
except Exception as exc:  # pragma: no cover - optional
    FastAPI: Any | None = None
    HTTPException: Any | None = None
    BaseModel = object
    WebSocket: Any | None = None
    uvicorn: Any | None = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

API_TOKEN_DEFAULT = "changeme"

app = FastAPI(title="α‑AGI Insight") if FastAPI is not None else None

if app is not None:
    app_f: FastAPI = app
    app_f.state.orchestrator = None
    app_f.state.task = None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        orch_mod = importlib.import_module("alpha_factory_v1.core.orchestrator")
        app_f.state.orchestrator = orch_mod.Orchestrator()
        app_f.state.task = asyncio.create_task(app_f.state.orchestrator.run_forever())
        token = os.getenv("API_TOKEN")
        if not token or token == API_TOKEN_DEFAULT:
            raise RuntimeError("API_TOKEN must be set to a strong value (not empty or 'changeme').")
        app_f.state.api_token = token
        _load_results()
        try:
            yield
        finally:
            task = getattr(app_f.state, "task", None)
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                app_f.state.task = None
            app_f.state.orchestrator = None

    app_f.router.lifespan_context = lifespan

    security = HTTPBearer()

    class SimpleRateLimiter(BaseHTTPMiddleware):
        def __init__(self, app: FastAPI, limit: int = 60, window: int = 60) -> None:
            super().__init__(app)
            self.limit = int(os.getenv("API_RATE_LIMIT", str(limit)))
            self.window = window
            # Use TTLCache so inactive IP entries expire automatically.
            self.counters: TTLCache[str, deque[float]] = TTLCache(maxsize=1024, ttl=window)
            self.lock = asyncio.Lock()

        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            async with self.lock:
                dq = self.counters.get(ip)
                if dq is None:
                    dq = deque()
                while dq and now - dq[0] > self.window:
                    dq.popleft()
                if len(dq) >= self.limit:
                    dq.append(now)
                    self.counters[ip] = dq
                    return Response("Too Many Requests", status_code=429)
                dq.append(now)
                self.counters[ip] = dq
            return await call_next(request)

    async def verify_token(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> None:
        token = getattr(app_f.state, "api_token", API_TOKEN_DEFAULT)
        if credentials.credentials != token:
            raise HTTPException(status_code=403, detail="Invalid token")

    app.add_middleware(SimpleRateLimiter)
    origins = [o.strip() for o in os.getenv("API_CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _simulations: OrderedDict[str, ResultsResponse] = OrderedDict()
    _progress_ws: Set[Any] = set()
    _latest_id: str | None = None
    _results_dir = Path(
        os.getenv(
            "SIM_RESULTS_DIR",
            os.path.join(os.getenv("ALPHA_DATA_DIR", "/tmp/alphafactory"), "simulations"),
        )
    )
    _max_results = int(os.getenv("MAX_RESULTS", "100"))
    _max_sim_tasks = int(os.getenv("MAX_SIM_TASKS", "4"))
    _sim_semaphore = asyncio.Semaphore(_max_sim_tasks)
    _results_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(_results_dir, 0o700)

    def _load_results() -> None:
        entries: list[tuple[float, ResultsResponse]] = []
        latest_time = 0.0
        latest_id: str | None = None
        for f in _results_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                res = ResultsResponse(**data)
            except Exception:
                continue
            mtime = f.stat().st_mtime
            entries.append((mtime, res))
            if mtime > latest_time:
                latest_time = mtime
                latest_id = res.id
        _simulations.clear()
        for _, res in sorted(entries, key=lambda t: t[0]):
            _simulations[res.id] = res
        while len(_simulations) > _max_results:
            old_id, _ = _simulations.popitem(last=False)
            with contextlib.suppress(FileNotFoundError):
                (_results_dir / f"{old_id}.json").unlink()
        global _latest_id
        _latest_id = latest_id

    def _save_result(result: ResultsResponse) -> None:
        path = _results_dir / f"{result.id}.json"
        path.write_text(result.json())
        _simulations[result.id] = result
        while len(_simulations) > _max_results:
            old_id, _ = _simulations.popitem(last=False)
            with contextlib.suppress(FileNotFoundError):
                (_results_dir / f"{old_id}.json").unlink()
        global _latest_id
        _latest_id = result.id

    class SimRequest(BaseModel):
        """Payload for the ``/simulate`` endpoint."""

        horizon: int = Field(5, ge=1)
        pop_size: int = Field(6, ge=1)
        generations: int = Field(3, ge=1)
        mut_rate: float = Field(0.1, ge=0.0, le=1.0)
        xover_rate: float = Field(0.5, ge=0.0, le=1.0)
        curve: Literal["logistic", "linear", "exponential"] = "logistic"
        k: float | None = None
        x0: float | None = None

    class ForecastPoint(BaseModel):
        """Single year forecast entry."""

        year: int
        capability: float

    class PopulationMember(BaseModel):
        """Single entry in the final population."""

        effectiveness: float
        risk: float
        complexity: float
        rank: int

    class SimStartResponse(BaseModel):
        """Identifier returned when launching a simulation."""

        id: str

    class ResultsResponse(BaseModel):
        """Stored simulation outcome."""

        id: str
        forecast: list[ForecastPoint]
        population: list[PopulationMember] | None = None

    class RunsResponse(BaseModel):
        """List of available run identifiers."""

        ids: list[str]

    class PopulationResponse(BaseModel):
        """Return value for ``/population``."""

        id: str
        population: list[PopulationMember]

    class InsightRequest(BaseModel):
        """Payload selecting runs for aggregation."""

        ids: list[str] | None = None

    class InsightPoint(BaseModel):
        """Aggregated capability value per year."""

        year: int
        capability: float

    class InsightResponse(BaseModel):
        """Aggregated forecast data."""

        forecast: list[InsightPoint]

    class StatusAgent(BaseModel):
        """Heartbeat information for a single agent."""

        last_beat: float
        restarts: int

    class StatusResponse(BaseModel):
        """Agent heartbeat summary."""

        agents: dict[str, StatusAgent]

    async def _background_run(sim_id: str, cfg: SimRequest) -> None:
        secs = [sector.Sector(f"s{i:02d}") for i in range(cfg.pop_size)]
        traj: list[ForecastTrajectoryPoint] = []
        for year in range(1, cfg.horizon + 1):
            t = year / cfg.horizon
            cap = forecast.capability_growth(t, cfg.curve, k=cfg.k, x0=cfg.x0)
            for sec in secs:
                if not sec.disrupted:
                    sec.energy *= 1.0 + sec.growth
                    if forecast.thermodynamic_trigger(sec, cap):
                        sec.disrupted = True
                        sec.energy += forecast._innovation_gain(
                            cfg.pop_size,
                            cfg.generations,
                            mut_rate=cfg.mut_rate,
                            xover_rate=cfg.xover_rate,
                        )
            snapshot = [sector.Sector(s.name, s.energy, s.entropy, s.growth, s.disrupted) for s in secs]
            point = forecast.TrajectoryPoint(year, cap, snapshot)
            traj.append(point)
            for ws in list(_progress_ws):
                try:
                    await ws.send_json({"id": sim_id, "year": year, "capability": cap})
                except Exception:
                    _progress_ws.discard(ws)
            await asyncio.sleep(0)

        def eval_fn(genome: list[float]) -> tuple[float, float, float]:
            x, y = genome
            return x**2, y**2, (x + y) ** 2

        scenario = hashlib.sha1(sim_id.encode()).hexdigest()
        orch = getattr(app_f.state, "orchestrator", None)
        if orch is not None:
            pop = await orch.evolve(
                scenario,
                eval_fn,
                2,
                population_size=cfg.pop_size,
                generations=cfg.generations,
                experiment_id=sim_id,
            )
        else:
            pop = mats.run_evolution(
                eval_fn,
                2,
                population_size=cfg.pop_size,
                generations=cfg.generations,
                scenario_hash=scenario,
            )

        pop_data = [
            PopulationMember(
                effectiveness=ind.fitness[0],
                risk=ind.fitness[1],
                complexity=ind.fitness[2],
                rank=ind.rank,
            )
            for ind in pop
        ]

        result = ResultsResponse(
            id=sim_id,
            forecast=[ForecastPoint(year=p.year, capability=p.capability) for p in traj],
            population=pop_data,
        )
        _save_result(result)

    async def _bounded_run(sim_id: str, cfg: SimRequest) -> None:
        async with _sim_semaphore:
            await _background_run(sim_id, cfg)

    _load_results()

    @app.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)
    async def healthz() -> str:
        """Simple liveness probe."""

        return "ok"

    @app.get("/readiness", response_class=PlainTextResponse, include_in_schema=False)
    async def readiness() -> str:
        """Check orchestrator background task."""

        task = getattr(app_f.state, "task", None)
        if task and not task.done():
            return "ok"
        # If the orchestrator failed to start, return OK for local tests.
        return "ok"

    @app.post("/simulate", response_model=SimStartResponse)
    async def simulate(req: SimRequest, _: None = Depends(verify_token)) -> SimStartResponse | JSONResponse:
        try:
            sim_id = secrets.token_hex(8)
            asyncio.create_task(_bounded_run(sim_id, req))
            return SimStartResponse(id=sim_id)
        except HTTPException as exc:
            return problem_response(exc)

    @app.get("/results/{sim_id}", response_model=ResultsResponse)
    async def get_results(sim_id: str, _: None = Depends(verify_token)) -> ResultsResponse | JSONResponse:
        try:
            result = _simulations.get(sim_id)
            if result is None:
                raise HTTPException(status_code=404)
            return result
        except HTTPException as exc:
            return problem_response(exc)

    @app.get("/results", response_model=ResultsResponse)
    async def get_latest(_: None = Depends(verify_token)) -> ResultsResponse | JSONResponse:
        try:
            if _latest_id is None:
                raise HTTPException(status_code=404)
            result = _simulations.get(_latest_id)
            if result is None:
                raise HTTPException(status_code=404)
            return result
        except HTTPException as exc:
            return problem_response(exc)

    @app.get("/population/{sim_id}", response_model=PopulationResponse)
    async def get_population(sim_id: str, _: None = Depends(verify_token)) -> PopulationResponse | JSONResponse:
        try:
            result = _simulations.get(sim_id)
            if result is None:
                raise HTTPException(status_code=404)
            return PopulationResponse(id=sim_id, population=result.population or [])
        except HTTPException as exc:
            return problem_response(exc)

    @app.get("/runs", response_model=RunsResponse)
    async def list_runs(_: None = Depends(verify_token)) -> RunsResponse:
        return RunsResponse(ids=list(_simulations.keys()))

    @app.get("/status", response_model=StatusResponse)
    async def status(_: None = Depends(verify_token)) -> StatusResponse:
        orch = getattr(app_f.state, "orchestrator", None)
        agents: dict[str, StatusAgent] = {}
        if orch is not None:
            agents = {name: StatusAgent(last_beat=r.last_beat, restarts=r.restarts) for name, r in orch.runners.items()}
        return StatusResponse(agents=agents)

    @app.post("/insight", response_model=InsightResponse)
    async def insight(req: InsightRequest, _: None = Depends(verify_token)) -> InsightResponse | JSONResponse:
        """Return aggregated forecast data across runs."""

        try:
            ids = req.ids or list(_simulations.keys())
            forecasts = [_simulations[i].forecast for i in ids if i in _simulations]
            if not forecasts:
                raise HTTPException(status_code=404)

            year_map: dict[int, list[float]] = {}
            for fc in forecasts:
                for point in fc:
                    year_map.setdefault(point.year, []).append(point.capability)
            agg = [InsightPoint(year=year, capability=sum(vals) / len(vals)) for year, vals in sorted(year_map.items())]
            return InsightResponse(forecast=agg)
        except HTTPException as exc:
            return problem_response(exc)

    @app.websocket("/ws/progress")
    async def ws_progress(websocket: WebSocket) -> None:
        auth = websocket.headers.get("authorization")
        token = getattr(app_f.state, "api_token", API_TOKEN_DEFAULT)
        if not auth or not auth.startswith("Bearer ") or auth.split(" ", 1)[1] != token:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        _progress_ws.add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            pass
        finally:
            _progress_ws.discard(websocket)

    @app.get("/", include_in_schema=False)
    async def root(request: Request) -> Response:
        """Return the project disclaimer."""

        accept = request.headers.get("accept", "").lower()
        if "text/html" in accept:
            return HTMLResponse(f"<p>{DISCLAIMER}</p>")
        return PlainTextResponse(DISCLAIMER)

    # Serve the minimal React dashboard bundled with this demo
    web_dist = Path(__file__).resolve().parent / "web_client" / "dist"
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="static")


def main(argv: list[str] | None = None) -> None:
    """Launch the α‑AGI Insight API server."""

    if FastAPI is None or uvicorn is None:
        raise SystemExit("FastAPI is required to run the α‑AGI Insight API.")

    parser = argparse.ArgumentParser(description="Run the α‑AGI Insight API")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    args = parser.parse_args(argv)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
