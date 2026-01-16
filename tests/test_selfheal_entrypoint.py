# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")
pytest.importorskip("gradio")


def test_selfheal_live_endpoint() -> None:
    script = Path("alpha_factory_v1/demos/self_healing_repo/agent_selfheal_entrypoint.py")
    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "")
    proc = subprocess.Popen([sys.executable, str(script)], env=env)
    url = "http://127.0.0.1:7863/__live"
    try:
        for _ in range(50):
            try:
                r = httpx.get(url)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.1)
        else:
            raise AssertionError("server did not start")
        assert r.status_code == 200
        assert r.text.strip() == "OK"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
