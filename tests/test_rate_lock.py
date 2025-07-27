# SPDX-License-Identifier: Apache-2.0
import asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from typing import Any

import sys
import types
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "stubs"))
try:
    import openai_agents
except Exception:
    pass
pytest.importorskip("gymnasium", minversion="0.29")
sys.path.insert(0, str(root))
from alpha_factory_v1.demos.aiga_meta_evolution import agent_aiga_entrypoint as mod

oa = pytest.importorskip("openai_agents", minversion="0.0.17")
if not hasattr(oa, "OpenAIAgent"):
    pytest.skip("openai_agents missing OpenAIAgent", allow_module_level=True)

a2a_mod = sys.modules.setdefault("a2a", types.ModuleType("a2a"))
a2a_mod.A2ASocket = lambda *a, **k: None  # type: ignore[attr-defined]
gr_mod: Any = sys.modules.setdefault("gradio", types.ModuleType("gradio"))
gr_mod.Blocks = lambda *a, **k: types.SimpleNamespace(
    __enter__=lambda s: s,
    __exit__=lambda *e: None,
)


async def _make_client() -> tuple[AsyncClient, Any]:
    app = FastAPI()
    app.middleware("http")(mod._count_requests)

    @app.get("/")  # type: ignore[misc]
    async def root() -> dict[str, bool]:
        return {"ok": True}

    transport = ASGITransport(app=app)
    client = AsyncClient(base_url="http://test", transport=transport)
    return client, app


async def _run_concurrent() -> None:
    client, _ = await _make_client()
    async with client:
        await asyncio.gather(*[client.get("/") for _ in range(5)])


def test_concurrent_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "1000")
    mod._REQUEST_LOG.clear()
    asyncio.run(_run_concurrent())
    assert len(mod._REQUEST_LOG.get("127.0.0.1", [])) == 5
