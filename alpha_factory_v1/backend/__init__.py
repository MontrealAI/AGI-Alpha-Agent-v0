# SPDX-License-Identifier: Apache-2.0
"""
alpha_factory_v1/backend/__init__.py
────────────────────────────────────
• ASGI entry-point with FastAPI (if available) or a zero-dep HTTP fallback.
• Small JSON API:  /api/logs · /api/csrf · /metrics   +   live /ws/trace.
• NEW 2025-05-02:  Backwards-compatibility shim that maps the historic
  `openai_agents` namespace → the official `agents` package shipped with the
  **OpenAI Agents SDK** (installed via `pip install openai-agents`).

The shim guarantees that *all existing demos* (e.g. self-healing_repo) keep
running after the dependency upgrade—no code changes needed elsewhere.

This module remains self-contained and safe to import even when:
  • the OpenAI Agents SDK *is not* installed (graceful degradation), or
  • no OPENAI_API_KEY is provided (the orchestrator later drops to local
    SBERT/LLaMA-cpp—see llm_provider.py).
"""

from __future__ import annotations

# ─────────────────────── Back-compat shim (critical) ──────────────────────
import importlib
import logging
import sys
import types
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, NoReturn
import tempfile
import json
import secrets
import time

_LOG = logging.getLogger("alphafactory.startup")

try:  # attempt to import the new canonical package name first
    _agents_pkg = importlib.import_module("agents")  # provided by openai-agents ≥0.0.13
except ModuleNotFoundError:  # SDK not installed
    _LOG.warning("OpenAI Agents SDK not found - running in degraded mode. " "Install with:  pip install openai-agents")
    # Create a *minimal* stub so `import openai_agents` will not crash.
    shim = types.ModuleType("openai_agents")
    shim.__spec__ = importlib.machinery.ModuleSpec("openai_agents", loader=None)

    class _MissingSDK:  # pylint: disable=too-few-public-methods
        """Stub that raises helpful errors when the real SDK is absent."""

        def __getattr__(self, item: str) -> NoReturn:  # noqa: D401
            raise ModuleNotFoundError(
                "The OpenAI Agents SDK is required for this operation. "
                "Please install it with:  pip install openai-agents"
            )

        def __call__(self, *args: object, **kwargs: object) -> NoReturn:  # noqa: D401
            raise ModuleNotFoundError(
                "The OpenAI Agents SDK is required for this operation. "
                "Please install it with:  pip install openai-agents"
            )

    # Expose typical top-level symbols so `from openai_agents import Agent`
    # fails with an informative message *at call-time* rather than import-time.
    for _name in (
        "Agent",
        "OpenAIAgent",
        "Tool",
        "FunctionTool",
        "tool",
        "AgentRuntime",
    ):
        setattr(shim, _name, _MissingSDK())

    sys.modules["openai_agents"] = shim
else:  # SDK is present → register alias & expose full public API verbatim
    shim = types.ModuleType("openai_agents")
    shim.__dict__.update(_agents_pkg.__dict__)
    shim.__spec__ = _agents_pkg.__spec__
    sys.modules["openai_agents"] = shim
    _LOG.info("OpenAI Agents SDK detected — legacy imports patched successfully.")

# Legacy import path: allow `import backend` and `import backend.finance_agent`
sys.modules.setdefault("backend", sys.modules[__name__])

_agents_mod = importlib.import_module(".agents", __name__)
sys.modules.setdefault(__name__ + ".agents", _agents_mod)
sys.modules["backend.agents"] = _agents_mod

_fin_mod = importlib.import_module(".agents.finance_agent", __name__)
sys.modules.setdefault(__name__ + ".finance_agent", _fin_mod)
sys.modules["backend.finance_agent"] = _fin_mod


# ──────────────────────── log & CSRF helpers (unchanged) ──────────────────
LOG_DIR = Path(tempfile.gettempdir()) / "alphafactory"


def _read_logs(max_lines: int = 100) -> List[str]:
    """Return the tail of the most-recent log file (≤ *max_lines*)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_files = sorted(LOG_DIR.glob("*.log"))
    if not log_files:
        return []
    return log_files[-1].read_text(errors="replace").splitlines()[-max_lines:]


# Tiny in-memory buffer holding single-use CSRF tokens (shared with /ws/trace)
# Maps token -> timestamp
_api_buffer: Dict[str, float] = {}

API_PREFIX = "/api"

# ───────────────────────────── FastAPI branch ─────────────────────────────
try:
    from fastapi import FastAPI, APIRouter

    fast_app = FastAPI(
        title="Alpha-Factory API",
        summary="Multi-Agent AGENTIC α-AGI backend",
        version="1.0.0",
    )

    api_router = APIRouter(prefix=API_PREFIX)

    # .— /logs ————————————————————————————————————————————————.
    @api_router.get("/logs")
    async def api_logs() -> List[str]:
        """Return the most recent (≤100) log lines."""
        return _read_logs()

    # .— /csrf ————————————————————————————————————————————————.
    @api_router.get("/csrf")
    async def csrf_token() -> dict[str, str]:
        """Issue a one-time CSRF token for the /ws/trace handshake."""
        token = secrets.token_urlsafe(32)
        _api_buffer[token] = time.time()
        return {"token": token}

    fast_app.include_router(api_router)

    # .— /ws/trace ————————————————————————————————————————————————.
    try:
        from .trace_ws import attach as _attach_trace_ws

        _attach_trace_ws(fast_app, prefix=API_PREFIX)  # registers /ws/trace
    except Exception:  # pragma: no cover
        _LOG.debug("trace_ws not attached (optional component missing).")

    # .— /metrics (Prometheus) ————————————————————————————————————————.
    try:
        from .agents.finance_agent import metrics_asgi_app

        fast_app.mount(f"{API_PREFIX}/metrics", metrics_asgi_app())
    except Exception:  # pragma: no cover
        _LOG.debug("Prometheus metrics endpoint not active.")

    # Export the ASGI application expected by uvicorn & gunicorn
    app = fast_app

# ─────────────────────── zero-dependency HTTP fallback ────────────────────
except ModuleNotFoundError:  # pragma: no cover

    async def app(
        scope: Dict[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[Any]],
    ) -> None:  # type: ignore  # noqa: D401, N802
        """Tiny HTTP-only ASGI app used when FastAPI is not installed."""
        if scope["type"] != "http":  # only handle plain HTTP
            return

        path = scope.get("path", "/")

        if path == f"{API_PREFIX}/logs":
            body = json.dumps(_read_logs()).encode()
            ctype = b"application/json"
        else:
            body = b"Alpha-Factory online"
            ctype = b"text/plain"

        headers = [(b"content-type", ctype)]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": body})
