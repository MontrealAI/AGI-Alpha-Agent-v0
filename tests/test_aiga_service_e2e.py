# SPDX-License-Identifier: Apache-2.0
"""End-to-end test for the aiga_meta_evolution service."""
import os
import subprocess
import sys
import time
import requests
import pytest

pytest.importorskip("openai_agents")

ENTRYPOINT = "alpha_factory_v1/demos/aiga_meta_evolution/agent_aiga_entrypoint.py"


@pytest.mark.e2e
@pytest.mark.xfail(reason="service start unstable in CI")
def test_aiga_service_health() -> None:
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = ""
    env.setdefault("API_PORT", "8000")

    proc = subprocess.Popen([sys.executable, ENTRYPOINT], env=env)
    try:
        url = "http://localhost:8000/health"
        resp = None
        for _ in range(100):
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
        proc.wait(timeout=5)

    assert "status" in data
    assert "generations" in data
    assert "best_fitness" in data
