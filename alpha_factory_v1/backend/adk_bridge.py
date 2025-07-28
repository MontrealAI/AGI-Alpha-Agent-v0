# SPDX-License-Identifier: Apache-2.0
# alpha_factory_v1/backend/adk_bridge.py
# ============================================================================
#  Alpha-Factory 👁️✨  ▸  Google ADK Bridge (Agent-to-Agent Federation Layer)
#  ────────────────────────────────────────────────────────────────────────────
#  • Safe no-op if Google ADK is not installed or not explicitly enabled.
#  • One-line integration:
#
#        from alpha_factory_v1.backend import adk_bridge
#        adk_bridge.auto_register(list_of_agents)   # after you create agents
#        adk_bridge.maybe_launch()                  # fire-and-forget gateway
#
#  • Security: set ALPHA_FACTORY_ADK_TOKEN to require an
#              `x-alpha-factory-token` header on every remote call.
#  • Tunable:  ALPHA_FACTORY_ADK_HOST / …_PORT if you need a custom bind.
#  • Zero impact on existing FastAPI / gunicorn stack.
# ============================================================================

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import secrets
import threading
from typing import Iterable, Any

logger = logging.getLogger("alpha_factory.adk_bridge")

__all__ = [
    "adk_enabled",
    "auto_register",
    "maybe_launch",
]

# ─────────────────────────────────────────────────────────────────────────────
#  ➊  Feature flags & dynamic import
# ─────────────────────────────────────────────────────────────────────────────
_ENABLE = os.getenv("ALPHA_FACTORY_ENABLE_ADK", "false").lower() in {"1", "true", "yes", "on"}
_TOKEN = os.getenv("ALPHA_FACTORY_ADK_TOKEN") or None  # optional auth
_HOST = os.getenv("ALPHA_FACTORY_ADK_HOST", "0.0.0.0")
_PORT = int(os.getenv("ALPHA_FACTORY_ADK_PORT", "9000"))

adk = None
try:  # runtime optional dependency
    import google_adk as adk  # packaged as "google-adk"
except ModuleNotFoundError:  # fallback to the namespaced import
    try:
        from google import adk  # type: ignore
    except Exception:
        adk = None

_ADK_OK = adk is not None
if not _ADK_OK and _ENABLE:
    logger.warning(
        "ADK integration requested but google-adk package is missing. "
        "Run  ➜  pip install google-adk   or disable ADK via "
        "ALPHA_FACTORY_ENABLE_ADK=false."
    )


# Guard-function lets callers know whether ADK functionality is live
def adk_enabled() -> bool:
    """True ↦ ADK present ∧ explicitly enabled via env-flag."""
    return _ADK_OK and _ENABLE


# ─────────────────────────────────────────────────────────────────────────────
#  ➋  Internal router & helpers
# ─────────────────────────────────────────────────────────────────────────────
_router: "adk.Router | None" = None  # created lazily
_server_started: bool = False  # idempotent launch() guard


def _ensure_router() -> "adk.Router":
    """Instantiate a singleton ADK Router on first call."""
    global _router
    if _router is None:  # lazy import only when needed
        _router = adk.Router()
        logger.info("Google ADK router initialised.")
    return _router


def _auth_middleware():  # injected only when token set
    from fastapi import Request
    from fastapi.responses import JSONResponse

    async def _mw(request: Request, call_next):  # noqa: D401
        # Constant-time header compare to resist timing attacks
        header = request.headers.get("x-alpha-factory-token", "")
        token_ok = (_TOKEN is None) or secrets.compare_digest(header, _TOKEN)
        if not token_ok:
            return JSONResponse(status_code=401, content={"error": "unauthorised ADK call"})
        return await call_next(request)

    return _mw


# ─────────────────────────────────────────────────────────────────────────────
#  ➌  Public API – one-liners used by orchestrator/demo scripts
# ─────────────────────────────────────────────────────────────────────────────
def auto_register(agents: Iterable[Any]) -> None:
    """
    Register a collection of *already-constructed* Alpha-Factory agents with
    the ADK router.  Safe to call even if ADK is disabled.

    Parameters
    ----------
    agents :
        An iterable whose members expose:
        • ``name``          – str   (identifier)
        • ``run(prompt)``   – callable returning str | dict | any JSON-serialisable
    """
    if not adk_enabled():
        return

    router = _ensure_router()

    for ag in agents:
        try:
            router.register_agent(_AF2ADKWrapper(ag))
            logger.debug("ADK ✔ registered agent '%s'", ag.name)
        except Exception:  # pragma: no cover
            logger.exception("ADK ✖ could not register agent '%s'", ag)


def maybe_launch(*, host: str | None = None, port: int | None = None, **uvicorn_kw) -> None:
    """
    Fire-and-forget launch of the ADK FastAPI gateway **in a background thread**.

    • Idempotent – subsequent calls are ignored.
    • No-op when ADK is disabled/not installed.
    • For production you’d front this with your existing reverse-proxy.

    Environment fallbacks
    ---------------------
    ALPHA_FACTORY_ADK_HOST / …_PORT
        Override listen address globally.
    """
    global _server_started
    if not adk_enabled() or _server_started:
        return

    host = host or _HOST
    port = port or _PORT
    router = _ensure_router()

    # Inject optional auth-middleware exactly once
    if _TOKEN:
        app = getattr(router, "app", None)
        if app is not None and hasattr(app, "middleware"):
            app.middleware("http")(_auth_middleware())

    def _serve() -> None:  # run inside daemon-thread
        import uvicorn

        logger.info("ADK gateway listening on http://%s:%d  (A2A protocol)", host, port)
        uvicorn.run(router.app, host=host, port=port, log_level="info", **uvicorn_kw)

    threading.Thread(target=_serve, daemon=True, name="ADK-Gateway").start()
    _server_started = True


# ─────────────────────────────────────────────────────────────────────────────
#  ➍  Thin adapter:  Alpha-Factory ▶︎ google-adk Agent
# ─────────────────────────────────────────────────────────────────────────────
class _AF2ADKWrapper(adk.Agent):
    """
    Minimal shim translating between ADK’s *TaskRequest/TaskResponse* and the
    Alpha-Factory agent `.run()` API.
    """

    def __init__(self, af_agent: Any):
        super().__init__(
            name=str(getattr(af_agent, "name", "af-agent")),
            description=getattr(af_agent, "description", "Alpha-Factory agent"),
        )
        self._impl = af_agent

    # ADK’s async run-signature ------------------------------------------------
    async def run(self, task_request: "adk.TaskRequest"):  # noqa: D401
        prompt: str = task_request.content
        logger.debug("[ADK→%s] prompt=%s", self._impl.name, prompt[:120])
        try:
            if inspect.iscoroutinefunction(self._impl.run):
                result = await self._impl.run(prompt)
            else:
                result = await asyncio.to_thread(self._impl.run, prompt)
        except Exception as exc:  # bubble up as ADK error payload
            logger.exception("Agent '%s' raised.", self._impl.name)
            raise adk.AgentException(str(exc)) from exc

        # Normalise arbitrary return types into something JSON-serialisable
        if not isinstance(result, (str, dict, list, int, float, bool, type(None))):
            result = str(result)

        return adk.TaskResponse(content=result)


# ─────────────────────────────────────────────────────────────────────────────
#  ➎  Friendly log banner (once on import) – helps troubleshooting
# ─────────────────────────────────────────────────────────────────────────────
if adk_enabled():
    logger.info("Google ADK support ENABLED  ➜  router will bind on %s:%d after `maybe_launch()`.", _HOST, _PORT)
else:
    logger.info("Google ADK support disabled (flag=%s, import=%s).", _ENABLE, _ADK_OK)
