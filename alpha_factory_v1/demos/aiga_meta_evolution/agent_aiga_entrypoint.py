# SPDX-License-Identifier: Apache-2.0
# mypy: disable-error-code=unused-ignore
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

agent_aiga_entrypoint.py – AI‑GA Meta‑Evolution Service
================================================================
Production‑grade entry point that wraps the *MetaEvolver* demo into a
Kubernetes‑/Docker‑friendly micro‑service with:
• **FastAPI** HTTP API (health, metrics, evolve, checkpoint, best‑alpha)
• **Gradio** dashboard on *:7862* for non‑technical users
• **Prometheus** metrics + optional **OpenTelemetry** traces
• Optional **ADK** registration + **A2A** mesh socket (auto‑noop if libs absent)
• Fully offline when `OPENAI_API_KEY` is missing – falls back to Ollama/Mistral
• Atomic checkpointing & antifragile resume (SIGTERM‑safe)
• SBOM‑ready logging + SOC‑2 log hygiene

The file is *self‑contained*; **no existing behaviour removed** – only
additive hardening to satisfy enterprise infosec & regulator audits.
"""
from __future__ import annotations

import os, asyncio, signal, logging, time, json
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# optional‑imports block keeps runtime lean
try:
    from opentelemetry import trace  # type: ignore
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore
except ImportError:  # pragma: no cover
    trace = None  # type: ignore
    FastAPIInstrumentor = None  # type: ignore

try:
    from adk.runtime import AgentRuntime  # type: ignore
except ImportError:  # pragma: no cover
    AgentRuntime = None  # type: ignore

try:
    from a2a import A2ASocket  # type: ignore
except ImportError:  # pragma: no cover
    A2ASocket = None  # type: ignore

try:  # optional dependency
    from openai_agents import OpenAIAgent, Tool
except Exception:
    try:
        from openai_agents import Agent as OpenAIAgent, Tool  # type: ignore
    except Exception:  # pragma: no cover - missing package
        from .openai_agents_bridge import OpenAIAgent, Tool
try:
    from alpha_factory_v1.backend import adk_bridge
except Exception:  # pragma: no cover - optional dependency
    adk_bridge = None
if __package__ is None:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent))
    __package__ = "alpha_factory_v1.demos.aiga_meta_evolution"

from .openai_agents_bridge import EvolverAgent
from .meta_evolver import MetaEvolver
from .curriculum_env import CurriculumEnv
from .utils import build_llm
import gradio as gr

try:  # optional JWT auth
    import jwt  # type: ignore
except Exception:  # pragma: no cover - optional
    jwt = None  # type: ignore

# ---------------------------------------------------------------------------
# CONFIG --------------------------------------------------------------------
# ---------------------------------------------------------------------------
SERVICE_NAME = os.getenv("SERVICE_NAME", "aiga-meta-evolution")
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7862"))
API_PORT = int(os.getenv("API_PORT", "8000"))
MAX_GEN = int(os.getenv("MAX_GEN", "1000"))  # safety rail
ENABLE_OTEL = os.getenv("ENABLE_OTEL", "false").lower() == "true"
ENABLE_SENTRY = os.getenv("ENABLE_SENTRY", "false").lower() == "true"
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "120"))
AUTH_TOKEN = os.getenv("AUTH_BEARER_TOKEN")
JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY")
JWT_ISSUER = os.getenv("JWT_ISSUER", "aiga.local")

SAVE_DIR = Path(os.getenv("CHECKPOINT_DIR", "/data/checkpoints"))
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# LOGGING --------------------------------------------------------------------
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOGLEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
log = logging.getLogger(SERVICE_NAME)

if ENABLE_SENTRY and SENTRY_DSN:
    try:
        import sentry_sdk  # type: ignore

        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)
        log.info("Sentry enabled")
    except ImportError:  # pragma: no cover - optional
        log.warning("Sentry requested but sentry_sdk missing")

# ---------------------------------------------------------------------------
# METRICS --------------------------------------------------------------------
# ---------------------------------------------------------------------------
FITNESS_GAUGE = Gauge("aiga_best_fitness", "Best fitness achieved so far")
GEN_COUNTER = Counter("aiga_generations_total", "Total generations processed")
STEP_LATENCY = Histogram("aiga_step_seconds", "Seconds spent per evolution step")
REQUEST_COUNTER = Counter("aiga_http_requests", "API requests", ["route"])

# rate-limit state
_REQUEST_LOG: dict[str, list[float]] = {}
_RATE_LOCK = asyncio.Lock()

# ---------------------------------------------------------------------------
# LLM TOOLING ----------------------------------------------------------------
# ---------------------------------------------------------------------------
LLM = build_llm()


@Tool(name="describe_candidate", description="Explain why this architecture might learn fast")
async def describe_candidate(arch: str):
    """Summarise why a given architecture could perform well."""
    return await LLM(f"In two sentences, explain why architecture '{arch}' might learn quickly.")


# ---------------------------------------------------------------------------
# CORE RUNTIME ---------------------------------------------------------------
# ---------------------------------------------------------------------------
class AIGAMetaService:
    """Thread‑safe façade around *MetaEvolver*."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.evolver = MetaEvolver(
            env_cls=CurriculumEnv,
            llm=LLM,
            checkpoint_dir=SAVE_DIR,
            start_socket=True,
        )
        self._restore_if_any()

    # -------- public ops --------
    async def evolve(self, gens: int = 1) -> None:
        """Run ``gens`` generations of evolution."""
        async with self._lock:
            start = time.perf_counter()
            self.evolver.run_generations(gens)
            GEN_COUNTER.inc(gens)
            FITNESS_GAUGE.set(self.evolver.best_fitness)
            STEP_LATENCY.observe(time.perf_counter() - start)

    async def checkpoint(self) -> None:
        """Persist the current state to disk."""
        async with self._lock:
            self.evolver.save()

    async def reset(self) -> None:
        """
        Reset the state of the MetaEvolver to its initial configuration.

        This method is thread-safe and uses a lock to prevent concurrent
        modifications to the evolver's state.
        """
        async with self._lock:
            self.evolver.reset()

    async def best_alpha(self) -> Dict[str, Any]:
        """Return the best architecture and a short description."""
        arch = self.evolver.best_architecture
        summary = await describe_candidate(arch)
        return {"architecture": arch, "fitness": self.evolver.best_fitness, "summary": summary}

    # -------- helpers --------
    def _restore_if_any(self) -> None:
        try:
            self.evolver.load()
            log.info("restored state → best fitness %.4f", self.evolver.best_fitness)
        except FileNotFoundError:
            log.info("no prior checkpoint – fresh run")

    # -------- dashboard helpers --------
    def history_plot(self):
        """Return a ``pandas`` DataFrame of the fitness history."""
        return self.evolver.history_plot()

    def latest_log(self):
        """Return a short summary of the current champion."""
        return self.evolver.latest_log()


service = AIGAMetaService()

# ---------------------------------------------------------------------------
# FASTAPI --------------------------------------------------------------------
# ---------------------------------------------------------------------------
app = FastAPI(title="AI‑GA Meta‑Evolution API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if ENABLE_OTEL and FastAPIInstrumentor:
    FastAPIInstrumentor.instrument_app(app)

# ---------- routes ----------


@app.middleware("http")
async def _count_requests(request, call_next):
    path = request.url.path
    if path.startswith("/metrics"):
        return await call_next(request)
    # -------- auth gate --------
    if AUTH_TOKEN or JWT_PUBLIC_KEY:
        header = request.headers.get("authorization")
        if not header:
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer":
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        if AUTH_TOKEN and token == AUTH_TOKEN:
            pass
        elif JWT_PUBLIC_KEY and jwt:
            try:
                jwt.decode(token, JWT_PUBLIC_KEY, algorithms=["RS256"], issuer=JWT_ISSUER)
            except Exception:
                return JSONResponse({"detail": "unauthorized"}, status_code=401)
        else:
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
    REQUEST_COUNTER.labels(route=path).inc()
    ip = request.client.host
    now = time.time()
    window = now - 60
    async with _RATE_LOCK:
        times = [t for t in _REQUEST_LOG.get(ip, []) if t > window]
        if not times:
            _REQUEST_LOG.pop(ip, None)
        else:
            _REQUEST_LOG[ip] = times
        exceed = len(times) >= RATE_LIMIT
        if not exceed:
            times.append(now)
            _REQUEST_LOG[ip] = times
    if exceed:
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    return await call_next(request)


@app.get("/health")
async def read_health():
    """Return service status and best fitness."""
    return {
        "status": "ok",
        "generations": int(GEN_COUNTER._value.get()),
        "best_fitness": service.evolver.best_fitness,
    }


@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.post("/evolve/{gens}")
async def evolve_endpoint(gens: int, background_tasks: BackgroundTasks):
    """Schedule ``gens`` generations in the background."""
    if gens < 1 or gens > MAX_GEN:
        raise HTTPException(400, f"gens must be 1–{MAX_GEN}")
    background_tasks.add_task(service.evolve, gens)
    return {"msg": f"scheduled evolution for {gens} generations"}


@app.post("/checkpoint")
async def checkpoint_endpoint(background_tasks: BackgroundTasks):
    """Persist the current checkpoint asynchronously."""
    background_tasks.add_task(service.checkpoint)
    return {"msg": "checkpoint scheduled"}


@app.post("/reset")
async def reset_endpoint(background_tasks: BackgroundTasks):
    """Reset the evolver state asynchronously."""
    background_tasks.add_task(service.reset)
    return {"msg": "reset scheduled"}


@app.get("/alpha")
async def best_alpha():
    """Return current best architecture + LLM summary (meta‑explanation)."""
    return await service.best_alpha()


# ---------------------------------------------------------------------------
# GRADIO DASHBOARD -----------------------------------------------------------
# ---------------------------------------------------------------------------
async def _launch_gradio() -> None:  # noqa: D401
    with gr.Blocks(title="AI‑GA Meta‑Evolution Demo") as ui:
        plot = gr.LinePlot(label="Fitness by Generation")
        log_md = gr.Markdown()

        def on_step(g=5):
            asyncio.run(service.evolve(g))
            return service.history_plot(), service.latest_log()

        gr.Button("Evolve 5 Generations").click(on_step, [], [plot, log_md])
    ui.launch(server_name="0.0.0.0", server_port=GRADIO_PORT, share=False)


# ---------------------------------------------------------------------------
# SIGNAL HANDLERS ------------------------------------------------------------
# ---------------------------------------------------------------------------
async def _graceful_exit(*_):
    log.info("SIGTERM received – persisting state …")
    await service.checkpoint()
    loop = asyncio.get_event_loop()
    loop.stop()


# ---------------------------------------------------------------------------
# MAIN -----------------------------------------------------------------------
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(_graceful_exit(s)))

    # start Gradio dashboard asynchronously
    loop.create_task(_launch_gradio())

    # register with agent mesh (optional)
    if AgentRuntime:
        AgentRuntime.register(SERVICE_NAME, f"http://localhost:{API_PORT}")
    if adk_bridge and adk_bridge.adk_enabled():
        evolver_agent = EvolverAgent()
        adk_bridge.auto_register([evolver_agent])
        adk_bridge.maybe_launch()

    # run FastAPI (blocking)
    uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="info")
