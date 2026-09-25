# SPDX-License-Identifier: Apache-2.0
"""End-to-end test for the aiga_meta_evolution service."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import requests
import pytest

pytest.importorskip("openai_agents")

ENTRYPOINT = "alpha_factory_v1/demos/aiga_meta_evolution/agent_aiga_entrypoint.py"


@pytest.mark.e2e
def test_aiga_service_health(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = ""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env["API_PORT"] = str(port)
    env["CHECKPOINT_DIR"] = str(tmp_path / "checkpoints")
    env["ENABLE_GRADIO"] = "false"

    proc = subprocess.Popen([sys.executable, ENTRYPOINT], env=env)
    try:
        url = f"http://127.0.0.1:{port}/health"
        resp = None
        for _ in range(100):
            assert proc.poll() is None, "service exited before becoming healthy"
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    resp = r
                    break
            except Exception:
                pass
            time.sleep(0.1)
        assert resp is not None, "service did not start"
        data = resp.json()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            pytest.fail("service did not shut down gracefully")

    assert "status" in data
    assert "generations" in data
    assert "best_fitness" in data
