# SPDX-License-Identifier: Apache-2.0
"""FastAPI server exposing simulation endpoints."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib
import json
import os
import secrets
import time
import logging
import shutil
import random
from collections import OrderedDict, deque
from pathlib import Path
from typing import Any, List, TYPE_CHECKING, cast, Set
import smtplib
from email.message import EmailMessage

from cachetools import TTLCache

from alpha_factory_v1.core.archive import Archive, ArchiveDB

# alerts is optional so demos can run without the Insight utilities
try:
    from alpha_factory_v1.core.utils import alerts  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional

    class alerts:  # type: ignore
        """Fallback alert handler when Insight utilities are missing."""

        @staticmethod
        def send_alert(message: str, url: str | None = None) -> None:
            _log.warning("alert: %s", message)


from alpha_factory_v1.core.utils.config import init_config
from alpha_factory_v1.core.monitoring import metrics
from alpha_factory_v1.core.capsules import CapsuleFacts, ImpactScorer, load_capsule_facts
from alpha_factory_v1.utils.disclaimer import DISCLAIMER

__all__ = [
    "app",
    "InsightPoint",
    "InsightRequest",
    "InsightResponse",
    "PopulationResponse",
    "ResultsResponse",
    "RunsResponse",
    "SimRequest",
    "SimStartResponse",
    "LineageNode",
    "StatusResponse",
    "StakeRequest",
    "StakeResponse",
    "ProofResponse",
    "main",
]

_log = logging.getLogger(__name__)


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

try:
    from fastapi import (
        FastAPI,
        HTTPException,
        WebSocketDisconnect,
        Request,
        Depends,
        APIRouter,
    )
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.responses import Response, PlainTextResponse
    from fastapi.staticfiles import StaticFiles
    from contextlib import asynccontextmanager
    from collections.abc import AsyncGenerator
    from pydantic import BaseModel, ConfigDict
    import uvicorn
    from .problem_json import problem_response
except ModuleNotFoundError as exc:  # pragma: no cover - optional
    _log.warning("FastAPI components unavailable: %s", exc)
    FastAPI = None  # type: ignore
    HTTPException = None  # type: ignore
    BaseModel = object  # type: ignore
    WebSocketDisconnect = Any  # type: ignore
    uvicorn = None  # type: ignore

if TYPE_CHECKING:
    from fastapi import WebSocket
elif FastAPI is not None:
    from fastapi import WebSocket
else:
    WebSocket = Any  # type: ignore

try:
    import prometheus_client
    from prometheus_client import (
        Counter,
        generate_latest,
    )
    from alpha_factory_v1.core.utils.tracing import api_request_seconds
except ModuleNotFoundError:  # pragma: no cover - optional
    prometheus_client = None  # type: ignore

if FastAPI is None:
    raise RuntimeError("FastAPI is required")

app: FastAPI | None = FastAPI(title="AGI Simulation API") if FastAPI is not None else None

if app is not None:
    API_TOKEN = os.getenv("API_TOKEN", "REPLACE_ME_TOKEN")
    if API_TOKEN == "REPLACE_ME_TOKEN":
        _log.warning("API_TOKEN not set; using placeholder token for local use.")

    security = HTTPBearer()

    async def _http_exception_handler(request: Request, exc: HTTPException) -> Response:
        return problem_response(exc)

    app.add_exception_handler(HTTPException, _http_exception_handler)

    def _noop(*_a: Any, **_kw: Any) -> Any:
        class _N:
            def labels(self, *_a: Any, **_kw: Any) -> "_N":
                return self

            def observe(self, *_a: Any) -> None:
                ...

            def inc(self, *_a: Any) -> None:
                ...

        return _N()

    if prometheus_client is not None:
        from alpha_factory_v1.backend.metrics_registry import get_metric

        def _get_metric(cls: Any, name: str, desc: str, labels: list[str]) -> Any:
            return get_metric(cls, name, desc, labels)

        REQ_COUNT = _get_metric(Counter, "api_requests_total", "HTTP requests", ["method", "endpoint", "status"])
        REQ_LAT = api_request_seconds
    else:  # pragma: no cover - prometheus not installed
        REQ_COUNT = _noop()
        REQ_LAT = api_request_seconds

    metrics_router = APIRouter()

    @metrics_router.get("/metrics", response_class=PlainTextResponse)
    async def _metrics() -> Response:
        if prometheus_client is None:
            raise HTTPException(status_code=503, detail="prometheus_client not installed")
        return PlainTextResponse(generate_latest(), media_type="text/plain; version=0.0.4")

    class SimpleRateLimiter(BaseHTTPMiddleware):
        def __init__(self, app: FastAPI, limit: int = 60, window: int = 60) -> None:
            super().__init__(app)
            self.limit = int(os.getenv("API_RATE_LIMIT", str(limit)))
            self.window = window
            # Map IP address to a deque of request timestamps. TTLCache automatically
            # evicts entries that have been idle for ``window`` seconds so we don't
            # need to scan all entries on each request.
            self.counters: TTLCache[str, deque[float]] = TTLCache(maxsize=1024, ttl=window)
            self.lock = asyncio.Lock()

        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            async with self.lock:
                dq = self.counters.get(ip)
                if dq is None:
                    dq = deque()
                # drop timestamps outside the current window
                while dq and now - dq[0] > self.window:
                    dq.popleft()
                if len(dq) >= self.limit:
                    dq.append(now)
                    self.counters[ip] = dq
                    return Response("Too Many Requests", status_code=429)
                dq.append(now)
                self.counters[ip] = dq
            return await call_next(request)

    class MetricsMiddleware(BaseHTTPMiddleware):
        """Collect metrics and watch for excessive throttling."""

        def __init__(self, app: FastAPI, window: int = 60) -> None:
            super().__init__(app)
            self.window = window
            self.window_start = time.time()
            self.req_count = 0
            self.resp_429 = 0

        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            now = time.time()
            if now - self.window_start >= self.window:
                if self.req_count and (self.resp_429 / self.req_count) > 0.05:
                    alerts.send_alert(f"High rate of 429 responses: {self.resp_429}/{self.req_count}")
                self.window_start = now
                self.req_count = 0
                self.resp_429 = 0

            self.req_count += 1
            start = time.perf_counter()
            response = await call_next(request)
            duration = time.perf_counter() - start
            if response.status_code == 429:
                self.resp_429 += 1
            REQ_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
            REQ_LAT.labels(request.method, request.url.path).observe(duration)
            return response

    async def verify_token(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> None:
        if credentials.credentials != API_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")

    app_f: FastAPI = app
    app_f.add_middleware(SimpleRateLimiter)
    app_f.add_middleware(MetricsMiddleware)
    origins = [o.strip() for o in os.getenv("API_CORS_ORIGINS", "*").split(",") if o.strip()]
    app_f.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app_f.middleware_stack = app_f.build_middleware_stack()
    stack = app_f.middleware_stack
    limiter = None
    metrics_mw = None
    while hasattr(stack, "app"):
        if isinstance(stack, SimpleRateLimiter):
            limiter = stack
        if isinstance(stack, MetricsMiddleware):
            metrics_mw = stack
        stack = stack.app
    app_f.state.limiter = limiter
    app_f.state.metrics = metrics_mw
    app_f.include_router(metrics_router)
    app_f.state.orchestrator = None
    app_f.state.orch_task = None
    app_f.state.static_analysis_task = None

    @asynccontextmanager
    async def lifespan(app_f: FastAPI) -> AsyncGenerator[None, None]:
        _log.warning(DISCLAIMER)
        init_config()
        if API_TOKEN == "REPLACE_ME_TOKEN":
            _log.error("API_TOKEN is set to the default 'REPLACE_ME_TOKEN'. Edit .env to use a strong secret.")
            raise RuntimeError("API_TOKEN placeholder detected")
        orch_mod = importlib.import_module("alpha_factory_v1.core.orchestrator")
        app_f.state.orchestrator = orch_mod.Orchestrator()
        app_f.state.orch_task = asyncio.create_task(app_f.state.orchestrator.run_forever())
        _load_results()
        app_f.state.static_analysis_task = asyncio.create_task(_static_analysis_task())
        try:
            yield
        finally:
            static_task = getattr(app_f.state, "static_analysis_task", None)
            if static_task:
                static_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await static_task
                app_f.state.static_analysis_task = None
            task = getattr(app_f.state, "orch_task", None)
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                app_f.state.orch_task = None
            app_f.state.orchestrator = None

    app_f.router.lifespan_context = lifespan


_simulations: OrderedDict[str, ResultsResponse] = OrderedDict()
_progress_ws: Set[WebSocket] = set()
_latest_id: str | None = None
_meme_usage: dict[str, int] = {}
_results_dir = Path(
    os.getenv(
        "SIM_RESULTS_DIR",
        os.path.join(os.getenv("ALPHA_DATA_DIR", "/tmp/alphafactory"), "simulations"),
    )
)
_max_results = int(os.getenv("MAX_RESULTS", "100"))
_max_sim_tasks = max(1, int(os.getenv("MAX_SIM_TASKS", "4")))
_sim_semaphore = asyncio.Semaphore(_max_sim_tasks)
_results_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

# Capsule facts for impact scoring
_CAPSULE_FACTS = load_capsule_facts(Path(__file__).resolve().parents[1] / "capsules")

# Kill-switch multisig tokens
_kill_tokens = {
    t
    for t in (
        os.getenv("KILL_TOKEN_A"),
        os.getenv("KILL_TOKEN_B"),
        os.getenv("KILL_TOKEN_C"),
    )
    if t
}
_pending_votes: TTLCache[str, float] = TTLCache(maxsize=3, ttl=300)


def _load_results() -> None:
    entries: list[tuple[float, ResultsResponse]] = []
    latest_time = 0.0
    latest_id: str | None = None
    for f in _results_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            res = ResultsResponse(**data)
        except (json.JSONDecodeError, ValueError) as exc:
            _log.warning("Skipping corrupt results file %s: %s", f, exc)
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
    path.write_text(result.model_dump_json())
    _simulations[result.id] = result
    while len(_simulations) > _max_results:
        old_id, _ = _simulations.popitem(last=False)
        with contextlib.suppress(FileNotFoundError):
            (_results_dir / f"{old_id}.json").unlink()
    global _latest_id
    _latest_id = result.id


def _send_analysis_email(report: str) -> None:
    recipients = [e.strip() for e in os.getenv("MAINTAINERS_EMAILS", "").split(",") if e.strip()]
    if not recipients:
        return
    msg = EmailMessage()
    msg["Subject"] = "Weekly Static Analysis Report"
    msg["From"] = os.getenv("SMTP_FROM", "noreply@alpha-factory.local")
    msg["To"] = ", ".join(recipients)
    msg.set_content(report)
    server = os.getenv("SMTP_SERVER", "localhost")
    port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    try:
        with smtplib.SMTP(server, port) as s:
            if user and password:
                s.login(user, password)
            s.send_message(msg)
    except Exception as exc:  # pragma: no cover - SMTP errors
        _log.warning("static analysis email failed: %s", exc)


async def _static_analysis_task() -> None:
    interval = int(os.getenv("STATIC_ANALYSIS_INTERVAL", str(7 * 24 * 3600)))
    semgrep = shutil.which("semgrep")
    if not semgrep:
        _log.warning(
            "semgrep not found. Install with `pip install semgrep` or set STATIC_ANALYSIS_INTERVAL=0 to disable"
        )
        return
    await asyncio.sleep(interval)
    while True:
        try:
            proc = await asyncio.create_subprocess_exec(
                semgrep,
                "--config",
                "semgrep.yml",
                stdout=asyncio.subprocess.PIPE,
            )
            out, _ = await proc.communicate()
            _send_analysis_email(out.decode())
        except Exception as exc:  # pragma: no cover - semgrep errors
            _log.warning("static analysis failed: %s", exc)
        await asyncio.sleep(interval)


class SectorSpec(BaseModel):
    """Sector configuration for simulation."""

    name: str
    energy: float = 1.0
    entropy: float = 1.0
    growth: float = 0.05


class SimRequest(BaseModel):
    """Payload for the ``/simulate`` endpoint."""

    horizon: int = 5
    num_sectors: int = 6
    energy: float = 1.0
    entropy: float = 1.0
    pop_size: int = 6
    generations: int = 3
    curve: str = "logistic"
    k: float | None = None
    x0: float | None = None
    seed: int | None = None
    sectors: list[SectorSpec] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "horizon": 5,
                "pop_size": 6,
                "generations": 3,
                "curve": "logistic",
                "seed": 42,
            }
        }
    )


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
    impact: float | None = None


class SimStartResponse(BaseModel):
    """Identifier returned when launching a simulation."""

    id: str


class ResultsResponse(BaseModel):
    """Stored simulation outcome."""

    version: int = 1
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


class LineageNode(BaseModel):
    """Archive entry for lineage visualisation."""

    id: int
    parent: int | None = None
    diff: str | None = None
    pass_rate: float


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


class AgentStatus(BaseModel):
    """Status information for a single agent."""

    name: str
    last_beat: float
    restarts: int


class StatusResponse(BaseModel):
    """Response model for ``/status``."""

    agents: list[AgentStatus]


class StakeRequest(BaseModel):
    """Payload registering a stake amount."""

    agent_id: str
    amount: float


class StakeResponse(BaseModel):
    """Simple acknowledgement for ``/stake``."""

    status: str


class ProofResponse(BaseModel):
    """CID and proof string for ``/proof``."""

    cid: str
    proof: str | None = None


async def _background_run(sim_id: str, cfg: SimRequest) -> None:
    """Execute one simulation in the background.

    Args:
        sim_id: Unique identifier for the run.
        cfg: Parameters controlling the forecast generation.

    Returns:
        None
    """

    if cfg.sectors:
        secs = [sector.Sector(s.name, s.energy, s.entropy, s.growth) for s in cfg.sectors]
    else:
        secs = [sector.Sector(f"s{i:02d}", cfg.energy, cfg.entropy) for i in range(cfg.num_sectors)]
    traj: list[ForecastTrajectoryPoint] = []
    for year in range(1, cfg.horizon + 1):
        t = year / cfg.horizon
        cap = forecast.capability_growth(t, cfg.curve, k=cfg.k, x0=cfg.x0)
        for sec in secs:
            if not sec.disrupted:
                sec.energy *= 1.0 + sec.growth
                if forecast.thermodynamic_trigger(sec, cap):
                    sec.disrupted = True
                    sec.energy += forecast._innovation_gain(cfg.pop_size, cfg.generations, seed=cfg.seed)
        snapshot = [sector.Sector(s.name, s.energy, s.entropy, s.growth, s.disrupted) for s in secs]
        point = forecast.TrajectoryPoint(year, cap, snapshot)
        traj.append(point)
        for ws in list(_progress_ws):
            try:
                await ws.send_json({"id": sim_id, "year": year, "capability": cap})
            except (RuntimeError, WebSocketDisconnect) as exc:
                _log.debug("Dropping progress WebSocket %s: %s", ws, exc)
                _progress_ws.discard(ws)
        await asyncio.sleep(0)

    def eval_fn(genome: list[float]) -> tuple[float, float, float]:
        x, y = genome
        return x**2, y**2, (x + y) ** 2

    pop = mats.run_evolution(
        eval_fn,
        2,
        population_size=cfg.pop_size,
        generations=cfg.generations,
        seed=cfg.seed,
    )
    metrics.dgm_children_total.inc(len(pop))

    # Pick first available capsule facts for impact scoring
    _facts = next(iter(_CAPSULE_FACTS.values()), CapsuleFacts(0.0, 0.0))
    _scorer = ImpactScorer()

    pop_data = [
        PopulationMember(
            effectiveness=ind.fitness[0],
            risk=ind.fitness[1],
            complexity=ind.fitness[2],
            rank=ind.rank,
            impact=_scorer.score(_facts, ind.fitness[0]),
        )
        for ind in pop
    ]

    result = ResultsResponse(
        id=sim_id,
        forecast=[ForecastPoint(year=p.year, capability=p.capability) for p in traj],
        population=pop_data,
    )
    _save_result(result)

    try:
        from alpha_factory_v1.core.snark import publish_score_proof
        from alpha_factory_v1.core.archive.db import ArchiveDB

        threshold = float(os.getenv("PROOF_THRESHOLD", "0.5"))
        score_a = traj[-1].capability if traj else 0.0
        score_b = pop_data[0].effectiveness if pop_data else 0.0
        db = ArchiveDB(Path(os.getenv("ARCHIVE_DB", "archive.db")))
        publish_score_proof(_results_dir / f"{sim_id}.json", sim_id, [score_a, score_b], threshold, db)
    except Exception as exc:  # pragma: no cover - best effort
        _log.debug("Proof generation failed: %s", exc)


async def _bounded_run(sim_id: str, cfg: SimRequest) -> None:
    """Run a simulation with concurrency limits enforced."""
    async with _sim_semaphore:
        await _background_run(sim_id, cfg)


if app is not None:

    @app.post("/simulate", response_model=SimStartResponse)
    async def simulate(req: SimRequest, _: None = Depends(verify_token)) -> Any:
        """Start a simulation and return its identifier."""

        start = time.perf_counter()
        status = "200"
        try:
            sim_id = secrets.token_hex(8)
            asyncio.create_task(_bounded_run(sim_id, req))
            return SimStartResponse(id=sim_id)
        except HTTPException as exc:
            status = str(exc.status_code)
            return problem_response(exc)
        finally:
            REQ_COUNT.labels("POST", "/simulate", status).inc()
            REQ_LAT.labels("POST", "/simulate").observe(time.perf_counter() - start)

    @app.get("/results/{sim_id}", response_model=ResultsResponse)
    async def get_results(sim_id: str, _: None = Depends(verify_token)) -> Any:
        """Return final forecast data for ``sim_id`` if available."""

        start = time.perf_counter()
        status = "200"
        try:
            result = _simulations.get(sim_id)
            if result is None:
                status = "404"
                raise HTTPException(status_code=404)
            return result
        except HTTPException as exc:
            status = str(exc.status_code)
            return problem_response(exc)
        finally:
            REQ_COUNT.labels("GET", "/results/{sim_id}", status).inc()
            REQ_LAT.labels("GET", "/results/{sim_id}").observe(time.perf_counter() - start)

    @app.get("/results", response_model=ResultsResponse)
    async def get_latest(_: None = Depends(verify_token)) -> Any:
        """Return the most recently completed simulation."""

        start = time.perf_counter()
        status = "200"
        try:
            if _latest_id is None:
                status = "404"
                raise HTTPException(status_code=404)
            result = _simulations.get(_latest_id)
            if result is None:
                status = "404"
                raise HTTPException(status_code=404)
            return result
        except HTTPException as exc:
            status = str(exc.status_code)
            return problem_response(exc)
        finally:
            REQ_COUNT.labels("GET", "/results", status).inc()
            REQ_LAT.labels("GET", "/results").observe(time.perf_counter() - start)

    @app.get("/population/{sim_id}", response_model=PopulationResponse)
    async def get_population(sim_id: str, _: None = Depends(verify_token)) -> Any:
        """Return the final population for ``sim_id`` if available."""

        start = time.perf_counter()
        status = "200"
        try:
            result = _simulations.get(sim_id)
            if result is None:
                status = "404"
                raise HTTPException(status_code=404)
            return PopulationResponse(id=sim_id, population=result.population or [])
        except HTTPException as exc:
            status = str(exc.status_code)
            return problem_response(exc)
        finally:
            REQ_COUNT.labels("GET", "/population/{sim_id}", status).inc()
            REQ_LAT.labels("GET", "/population/{sim_id}").observe(time.perf_counter() - start)

    @app.get("/runs", response_model=RunsResponse)
    async def list_runs(_: None = Depends(verify_token)) -> RunsResponse:
        """Return identifiers for all stored runs."""
        return RunsResponse(ids=list(_simulations.keys()))

    @app.get("/memes")
    async def meme_usage(_: None = Depends(verify_token)) -> dict[str, int]:
        """Return meme usage counts."""
        return _meme_usage

    @app.get("/lineage", response_model=list[LineageNode])
    async def lineage(_: None = Depends(verify_token)) -> list[LineageNode]:
        """Return archive lineage information."""
        path = Path(os.getenv("ARCHIVE_PATH", "archive.db"))
        arch = Archive(path)
        nodes: list[LineageNode] = []
        for a in arch.all():
            nodes.append(
                LineageNode(
                    id=a.id,
                    parent=a.meta.get("parent"),
                    diff=a.meta.get("diff") or a.meta.get("patch"),
                    pass_rate=a.score,
                )
            )
        return nodes

    @app.get("/lineage/{node_id}", response_model=list[LineageNode])
    async def lineage_subtree(node_id: int, _: None = Depends(verify_token)) -> list[LineageNode]:
        """Return lineage up to ``node_id``."""
        path = Path(os.getenv("ARCHIVE_PATH", "archive.db"))
        arch = Archive(path)
        nodes: list[LineageNode] = []
        found = False
        for a in arch.all():
            nodes.append(
                LineageNode(
                    id=a.id,
                    parent=a.meta.get("parent"),
                    diff=a.meta.get("diff") or a.meta.get("patch"),
                    pass_rate=a.score,
                )
            )
            if a.id == node_id:
                found = True
                break
        if not found:
            raise HTTPException(status_code=404)
        return nodes

    @app.get("/status", response_model=StatusResponse)
    async def status(_: None = Depends(verify_token)) -> StatusResponse:
        """Return orchestrator agent stats."""

        orch = cast(Any, app_f.state.orchestrator)
        if orch is None:
            raise HTTPException(status_code=503, detail="Orchestrator not running")
        items = [
            AgentStatus(name=r.agent.name, last_beat=r.last_beat, restarts=r.restarts) for r in orch.runners.values()
        ]
        return StatusResponse(agents=items)

    @app.post("/kill-switch")
    async def kill_switch(request: Request, _: None = Depends(verify_token)) -> dict[str, str]:
        token = request.headers.get("X-Kill-Token")
        if token is None:
            data = await request.json()
            token = data.get("token")
        if token not in _kill_tokens:
            raise HTTPException(status_code=403, detail="Invalid kill token")
        _pending_votes[token] = time.time()
        if len(_pending_votes) >= 2:
            task = getattr(app_f.state, "orch_task", None)
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                app_f.state.orch_task = None
                app_f.state.orchestrator = None
            alerts.send_alert("Kill-switch activated – orchestrator disabled")
            _pending_votes.clear()
            return {"status": "disabled"}
        return {"status": f"{len(_pending_votes)}/2 confirmations"}

    @app.post("/stake", response_model=StakeResponse)
    async def set_stake(req: StakeRequest, _: None = Depends(verify_token)) -> Any:
        """Register ``req.agent_id`` with ``req.amount`` tokens."""

        start = time.perf_counter()
        status = "200"
        try:
            orch = cast(Any, app_f.state.orchestrator)
            if orch is None:
                raise HTTPException(status_code=503, detail="Orchestrator not running")
            orch.registry.set_stake(req.agent_id, req.amount)
            return StakeResponse(status="ok")
        except HTTPException as exc:
            status = str(exc.status_code)
            return problem_response(exc)
        finally:
            REQ_COUNT.labels("POST", "/stake", status).inc()
            REQ_LAT.labels("POST", "/stake").observe(time.perf_counter() - start)

    @app.post("/dispatch")
    async def trigger_dispatch(_: None = Depends(verify_token)) -> Any:
        """Trigger a GitHub workflow dispatch."""

        start = time.perf_counter()
        status = "200"
        try:
            url = os.getenv("DISPATCH_URL")
            token = os.getenv("DISPATCH_TOKEN")
            if not url or not token:
                raise HTTPException(status_code=503, detail="dispatch not configured")
            httpx = importlib.import_module("httpx")
            r = httpx.post(url, json={}, headers={"Authorization": f"Bearer {token}"}, timeout=10)
            r.raise_for_status()
            return {"status": "ok"}
        except HTTPException as exc:
            status = str(exc.status_code)
            return problem_response(exc)
        except Exception as exc:  # pragma: no cover - network failures
            status = "502"
            return problem_response(HTTPException(status_code=502, detail=str(exc)))
        finally:
            REQ_COUNT.labels("POST", "/dispatch", status).inc()
            REQ_LAT.labels("POST", "/dispatch").observe(time.perf_counter() - start)

    @app.get("/proof/{agent_id}", response_model=ProofResponse)
    async def get_proof(agent_id: str, _: None = Depends(verify_token)) -> Any:
        """Return stored proof CID for ``agent_id`` if present."""

        start = time.perf_counter()
        status = "200"
        try:
            path = Path(os.getenv("ARCHIVE_PATH", "archive.db"))
            db = ArchiveDB(path)
            cid = db.get_proof_cid(agent_id)
            if cid is None:
                raise HTTPException(status_code=404)
            proof = db.get_state(f"proof:{agent_id}")
            return ProofResponse(cid=cid, proof=proof)
        except HTTPException as exc:
            status = str(exc.status_code)
            return problem_response(exc)
        finally:
            REQ_COUNT.labels("GET", "/proof/{agent_id}", status).inc()
            REQ_LAT.labels("GET", "/proof/{agent_id}").observe(time.perf_counter() - start)

    @app.post("/insight", response_model=InsightResponse)
    async def insight(req: InsightRequest, _: None = Depends(verify_token)) -> Any:
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
        token = websocket.headers.get("authorization")
        if token and token.startswith("Bearer "):
            token = token.split(" ", 1)[1]
        else:
            token = websocket.query_params.get("token", "")
        if token != API_TOKEN:
            await websocket.close(code=1008)
            return
        """Stream year-by-year progress updates to the client."""
        await websocket.accept()
        _progress_ws.add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except (WebSocketDisconnect, RuntimeError) as exc:
            _log.debug("Progress WebSocket closed: %s", exc)
        finally:
            _progress_ws.discard(websocket)

    # Serve the React SPA built assets if present
    static_dir = Path(__file__).resolve().parent / "web_client" / "dist"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="spa")


def main(argv: List[str] | None = None) -> None:
    """CLI entry to launch the API server.

    Args:
        argv: Optional list of command line arguments.

    Returns:
        None
    """
    if FastAPI is None:
        raise SystemExit("FastAPI is required to run the API server")

    init_config()
    parser = argparse.ArgumentParser(description="Run the AGI simulation API server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    args = parser.parse_args(argv)
    try:
        uvicorn.run(cast(Any, app), host=args.host, port=args.port)
    except Exception as exc:  # pragma: no cover - runtime failure
        _log.exception("server failed: %s", exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
