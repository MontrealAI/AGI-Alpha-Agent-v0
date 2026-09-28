# SPDX-License-Identifier: Apache-2.0

"""Legacy tool registry and optional telemetry adapters.

Generated Python uses the shared Docker boundary; environment flags never enable
host execution. Extension discovery is explicit. Cost/carbon values are heuristic
estimates. Optional integrations require their own dependencies and validation.
"""

from __future__ import annotations

import asyncio, importlib, inspect, json, logging, os, sys, time, types, uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Union, List

###############################################################################
# Configuration
###############################################################################

ROOT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = ROOT_DIR / "tools_ext"


DB_URL = os.getenv("TOOLS_DB_URL", f"sqlite:///{ROOT_DIR/'tools_invocations.sqlite'}")
SANDBOX_TRUSTED = bool(int(os.getenv("TOOLS_TRUSTED", "0")))
CALL_TIMEOUT = float(os.getenv("TOOLS_TIMEOUT", "30"))  # seconds
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # auto|openai|anthropic|hf|local

# cost & carbon heuristics – tuned via real‑world cloud billing
USD_PER_CPU_SEC = float(os.getenv("USD_PER_CPU_SEC", "2.5e-5"))
GCO2_PER_CPU_SEC = float(os.getenv("GCO2_PER_CPU_SEC", "0.42"))

_LOGGER = logging.getLogger("alpha_factory.tools")
if os.getenv("TOOLS_DEBUG"):
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
else:
    _LOGGER.setLevel(logging.INFO)

###############################################################################
# Telemetry & lineage store
###############################################################################


def _get_engine():
    from sqlalchemy import create_engine

    return create_engine(DB_URL, future=True, echo=False)


def _init_db():
    from sqlalchemy import text

    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
        CREATE TABLE IF NOT EXISTS invocations(
            id TEXT PRIMARY KEY,
            tool TEXT,
            ts_start REAL,
            ts_end REAL,
            args JSON,
            output JSON,
            latency REAL,
            token_in INT,
            token_out INT,
            usd REAL,
            gco2e REAL,
            score REAL,
            error TEXT
        )
        """
            )
        )


def _log_invocation(row: Dict[str, Any]) -> None:
    """Write a single row to DB – non‑blocking via thread executor"""
    import concurrent.futures, functools
    from sqlalchemy import text

    _init_db()
    engine = _get_engine()

    def _write():
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
            INSERT INTO invocations values
            (:id,:tool,:ts_start,:ts_end,:args,:output,:latency,
             :token_in,:token_out,:usd,:gco2e,:score,:error)
            """
                ),
                row,
            )

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _write)


###############################################################################
# Utility – cheap token estimator
###############################################################################


def _rough_token_count(txt: str) -> int:
    # heuristic: 1 token ≈ 4 chars for English
    return max(1, len(txt) // 4)


###############################################################################
# Registry
###############################################################################


class Tool:
    """Container for a single registered tool"""

    def __init__(
        self,
        name: str,
        func: Callable[..., Awaitable[Any]] | Callable[..., Any],
        schema: Dict[str, Any],
        description: str = "",
    ) -> None:
        self.name = name
        self.func = func
        self.schema = schema
        self.description = (description or inspect.getdoc(func) or "").strip()

    async def __call__(self, **kwargs):
        try:
            import jsonschema

            jsonschema.validate(kwargs, self.schema)
        except ModuleNotFoundError:
            _LOGGER.debug("jsonschema not installed – skipping validation")

        uid = str(uuid.uuid4())
        t0 = time.time()
        err = None
        out = None

        try:
            coro: Awaitable
            if asyncio.iscoroutinefunction(self.func):
                coro = self.func(**kwargs)
            else:

                async def _sync_wrapper():
                    return self.func(**kwargs)

                coro = _sync_wrapper()

            out = await asyncio.wait_for(coro, timeout=CALL_TIMEOUT)
            return out
        except Exception as e:
            err = repr(e)
            raise
        finally:
            t1 = time.time()
            latency = t1 - t0
            arg_json = json.dumps(kwargs, default=str)[:20_000]
            out_json = json.dumps(out, default=str)[:20_000] if out is not None else None
            row = dict(
                id=uid,
                tool=self.name,
                ts_start=t0,
                ts_end=t1,
                args=arg_json,
                output=out_json,
                latency=latency,
                token_in=_rough_token_count(arg_json),
                token_out=_rough_token_count(out_json or ""),
                usd=latency * USD_PER_CPU_SEC,
                gco2e=latency * GCO2_PER_CPU_SEC,
                score=_score_vector(latency),  # placeholder single score
                error=err,
            )
            _log_invocation(row)


_REGISTRY: Dict[str, Tool] = {}


def register(schema: Dict[str, Any]):
    """Decorator: register a coroutine / function as an exposed tool"""

    def deco(fn: Callable):
        if fn.__name__ in _REGISTRY:
            raise ValueError(f"Duplicate tool name: {fn.__name__}")
        _REGISTRY[fn.__name__] = Tool(fn.__name__, fn, schema, fn.__doc__)
        _LOGGER.debug("Registered tool: %s", fn.__name__)
        return fn

    return deco


def registry() -> Dict[str, Tool]:
    return dict(_REGISTRY)


def get(name: str) -> Tool:
    return _REGISTRY[name]


###############################################################################
# Simple multi‑objective score – extensible
###############################################################################


def _score_vector(latency: float) -> float:
    """Return scalar aggregating multiple objectives (placeholder).
    Lower is better.  Extend as needed."""
    return latency


###############################################################################
# Core built‑in tools
###############################################################################


@register(
    {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 10, "minimum": 1, "maximum": 25},
        },
        "required": ["query"],
    }
)
async def web_search(query: str, top_k: int = 10) -> List[Dict[str, str]]:
    """
    🔎 **Web Search** – privacy‑respecting search via DuckDuckGo `lite` API.
    Returns list[{title,url,snippet}] sorted by relevance.
    """
    import aiohttp, urllib.parse

    params = {"q": query, "kl": "us-en", "count": str(top_k)}
    url = "https://duckduckgo.com/i.js"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as sess:
        async with sess.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}) as r:
            if r.status != 200:
                raise RuntimeError(f"HTTP {r.status}")
            data = await r.json()
            return [
                {
                    "title": itm.get("title"),
                    "url": urllib.parse.unquote(itm.get("url", "")),
                    "snippet": itm.get("snippet"),
                }
                for itm in data.get("results", [])
            ][:top_k]


@register(
    {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Python source to execute in sandbox"}},
        "required": ["code"],
    }
)
async def sandbox_exec(code: str) -> str:
    """Execute generated Python in Docker; no host fallback or trust-env bypass."""
    from ..isolation import run_python

    return await asyncio.to_thread(run_python, code)


@register(
    {
        "type": "object",
        "properties": {"values": {"type": "array", "items": {"type": "number"}}},
        "required": ["values"],
    }
)
async def stats(values: List[float]) -> Dict[str, float]:
    """
    📊 Compute basic statistics over a numeric vector.
    """
    import statistics as st

    return {
        "n": len(values),
        "mean": st.mean(values),
        "median": st.median(values),
        "stdev": st.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


###############################################################################
# Dynamic discovery
###############################################################################


def _discover_tools():
    sys.path.append(str(TOOLS_DIR))
    for p in TOOLS_DIR.glob("*.py"):
        mod_name = p.stem
        if mod_name.startswith("_"):
            continue
        try:
            importlib.import_module(mod_name)
            _LOGGER.info("Loaded external tool module: %s", mod_name)
        except Exception as e:
            _LOGGER.warning("Failed loading %s – %s", mod_name, e)


# Extensions are executable local code: discover only through an explicit call.

###############################################################################
# Provider‑agnostic LLM function‑spec helper
###############################################################################


def openai_functions_spec() -> List[Dict[str, Any]]:
    """Return JSON function specs compatible with OpenAI / Anthropic calls"""
    return [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.schema,
        }
        for t in _REGISTRY.values()
    ]


###############################################################################
# === OPTIONAL FastAPI lineage UI ============================================
###############################################################################

if os.getenv("TOOLS_UI") == "1":
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
        import uvicorn, asyncio

        app = FastAPI(title="Alpha‑Factory Tools Lineage")

        class Invocation(BaseModel):
            id: str
            tool: str
            ts_start: float
            ts_end: float
            latency: float
            usd: float
            gco2e: float
            score: float
            error: Optional[str]

        @app.get("/invocations", response_model=List[Invocation])
        async def list_invocations(limit: int = 100):
            from sqlalchemy import text

            engine = _get_engine()
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT id,tool,ts_start,ts_end,"
                        "latency,usd,gco2e,score,error "
                        "FROM invocations ORDER BY ts_start DESC "
                        "LIMIT :lim"
                    ),
                    dict(lim=limit),
                )
                return [Invocation(**dict(r)) for r in rows]

        def _launch_server():
            uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("TOOLS_UI_PORT", "8000")))

        # Fire up server in background
        asyncio.get_event_loop().create_task(asyncio.to_thread(_launch_server))
        _LOGGER.info("Lineage UI launched at http://localhost:8000")
    except ImportError:
        _LOGGER.warning("FastAPI or dependencies missing – UI disabled")
