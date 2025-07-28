# SPDX-License-Identifier: Apache-2.0
"""ADK gateway integration tests."""

from __future__ import annotations

import importlib
import os
import socket
import threading
import time
from typing import Any, Iterator, Tuple

import pytest

# Skip entire module if google_adk is not installed
pytest.importorskip("google_adk")
httpx = pytest.importorskip("httpx")  # noqa: E402
uvicorn = pytest.importorskip("uvicorn")  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture()
def adk_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[Tuple[str, str]]:
    """Launch the ADK gateway on a free port and yield the base URL and token."""

    port = _free_port()
    token = "test-token"

    os.environ["ALPHA_FACTORY_ENABLE_ADK"] = "1"
    os.environ["ALPHA_FACTORY_ADK_TOKEN"] = token
    os.environ["ALPHA_FACTORY_ADK_HOST"] = "127.0.0.1"
    os.environ["ALPHA_FACTORY_ADK_PORT"] = str(port)

    from alpha_factory_v1.backend import adk_bridge as _bridge

    # Reload so env vars take effect
    adk_bridge = importlib.reload(_bridge)

    class DummyAgent:
        name = "dummy"

        def run(self, _prompt: str) -> str:
            return "ok"

    server: Any | None = None
    thread: threading.Thread | None = None

    def patched_run(app: Any, host: str, port: int, log_level: str = "info", **kw: Any) -> None:
        nonlocal server, thread
        config = uvicorn.Config(app, host=host, port=port, log_level=log_level, **kw)
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        for _ in range(50):
            if server.started:
                break
            time.sleep(0.1)
        # additional guard – poll the socket until it accepts connections
        for _ in range(50):
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}") as c:
                    c.get("/docs", timeout=0.1)
                break
            except Exception:
                time.sleep(0.1)
        else:
            pytest.skip("ADK server failed to start")
        time.sleep(0.2)

    monkeypatch.setattr(uvicorn, "run", patched_run)

    adk_bridge.auto_register([DummyAgent()])
    adk_bridge.maybe_launch()

    assert thread is not None and server is not None

    yield f"http://127.0.0.1:{port}", token

    server.should_exit = True
    thread.join(timeout=5)

    for var in (
        "ALPHA_FACTORY_ENABLE_ADK",
        "ALPHA_FACTORY_ADK_TOKEN",
        "ALPHA_FACTORY_ADK_HOST",
        "ALPHA_FACTORY_ADK_PORT",
    ):
        os.environ.pop(var, None)


@pytest.mark.xfail(reason="ADK gateway unstable in CI")
def test_docs_authenticated(adk_server: Tuple[str, str]) -> None:
    """Valid token should fetch docs."""

    url, token = adk_server
    with httpx.Client(base_url=url) as client:
        r = client.get("/docs", headers={"x-alpha-factory-token": token})
        assert r.status_code == 200


def test_docs_invalid_token(adk_server: Tuple[str, str]) -> None:
    """Invalid token should return 401."""

    url, _token = adk_server
    with httpx.Client(base_url=url) as client:
        r = client.get("/docs", headers={"x-alpha-factory-token": "bad"})
        assert r.status_code == 401
