# SPDX-License-Identifier: Apache-2.0
"""Integration test for the AI-GA workflow demo."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

pytest.importorskip("prometheus_client")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _write_stub(directory: Path) -> None:
    mod = directory / "openai_agents"
    mod.mkdir()
    mod_init = mod / "__init__.py"
    mod_init.write_text(
        """
import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class Agent:
    name: str = ""
    tools = []

class OpenAIAgent:
    def __init__(self, *a, base_url=None, **kw):
        self.base_url = base_url

def Tool(*_a, **_k):
    def dec(f):
        return f
    return dec

class AgentRuntime:
    def __init__(self, *a, port=5001, llm=None, api_key=None, **k):
        self.port = int(os.getenv('AGENTS_RUNTIME_PORT', port))
        self._agent = None

    def register(self, agent):
        self._agent = agent

    def run(self):
        agent = self._agent
        if agent is None:
            raise RuntimeError('no agent registered')
        port = self.port

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == f'/v1/agents/{agent.name}/invoke':
                    length = int(self.headers.get('content-length', '0'))
                    body = self.rfile.read(length)
                    try:
                        payload = json.loads(body or '{}')
                    except json.JSONDecodeError:
                        payload = {}
                    result = asyncio.run(agent.policy(payload, None))
                    data = json.dumps(result).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *_):
                pass

        server = HTTPServer(('127.0.0.1', port), Handler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
        server.server_close()
"""
    )

    # Stubs required by workflow_demo
    (directory / "alpha_opportunity_stub.py").write_text(
        "def identify_alpha(domain: str = 'finance'):\n    return 'stub-alpha'"
    )
    (directory / "alpha_conversion_stub.py").write_text(
        "def convert_alpha(alpha: str):\n    return {}"
    )


@pytest.mark.xfail(reason="workflow runtime unstable in CI")
def test_aiga_workflow_runtime(tmp_path: Path) -> None:
    port = _free_port()
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    _write_stub(stub_dir)

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = ""
    env["AGENTS_RUNTIME_PORT"] = str(port)
    env["PYTHONPATH"] = f"{stub_dir}:{env.get('PYTHONPATH', '')}"

    cmd = [
        sys.executable,
        "-c",
        ("from alpha_factory_v1.demos.aiga_meta_evolution " "import workflow_demo; workflow_demo.main()"),
    ]
    proc = subprocess.Popen(cmd, env=env)
    try:
        url = f"http://localhost:{port}/v1/agents/alpha_workflow/invoke"
        for _ in range(20):
            time.sleep(0.5)
            try:
                resp = requests.post(url, json={}, timeout=5)
                if resp.status_code == 200:
                    break
            except Exception:
                continue
        else:
            raise AssertionError("runtime not reachable")

        data = resp.json()
        assert "alpha" in data and "plan" in data
    finally:
        proc.terminate()
        proc.wait(timeout=5)
