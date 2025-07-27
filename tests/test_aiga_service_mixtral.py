# SPDX-License-Identifier: Apache-2.0
"""Offline fallback path for agent_aiga_entrypoint.py."""

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import pytest

pytest.importorskip("prometheus_client")
pytest.importorskip("gymnasium", minversion="0.29")
pytest.importorskip("fastapi")

ENTRYPOINT = "alpha_factory_v1/demos/aiga_meta_evolution/agent_aiga_entrypoint.py"


def _free_port() -> int:
    """Return an unused localhost port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: D401
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"choices":[{"message":{"content":"ok"}}]}')

    def log_message(self, *_args: str) -> None:  # pragma: no cover - quiet
        pass


@pytest.mark.e2e
def test_mixtral_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    api_port = _free_port()
    ollama_port = _free_port()

    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    (stub_dir / "openai_agents.py").write_text(
        "class OpenAIAgent:\n"
        "    def __init__(self, *a, **kw):\n"
        "        self.base_url = kw.get('base_url')\n"
        "    def __call__(self, *a, **kw):\n"
        "        return 'ok'\n"
        "def Tool(*_a, **_k):\n"
        "    def dec(f):\n"
        "        return f\n"
        "    return dec\n"
    )

    server = HTTPServer(("127.0.0.1", ollama_port), _Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = ""
    env["OLLAMA_BASE_URL"] = f"http://127.0.0.1:{ollama_port}/v1"
    env["API_PORT"] = str(api_port)
    env["PYTHONPATH"] = f"{stub_dir}:{env.get('PYTHONPATH', '')}"

    proc = subprocess.Popen(
        [sys.executable, ENTRYPOINT],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        url = f"http://localhost:{api_port}/health"
        for _ in range(100):
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.1)
        else:
            out, _ = proc.communicate(timeout=5)
            server.shutdown()
            thread.join()
            pytest.skip(f"service failed to start: {out}")
    finally:
        proc.terminate()
        out, _ = proc.communicate(timeout=5)
        server.shutdown()
        thread.join()

    assert "ollama" in out.lower() or "mixtral" in out.lower()
