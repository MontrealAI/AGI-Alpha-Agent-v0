# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest


pytest.importorskip("openai_agents", minversion="0.0.17")


def test_governance_bridge_adk_runtime(tmp_path: Path) -> None:
    """Launch governance-bridge with ADK enabled and verify logs."""
    stub = tmp_path / "google_adk.py"
    stub.write_text(
        """
class Router:
    def __init__(self):
        self.app = type('app', (), {'middleware': lambda *a, **k: lambda f: f})()
    def register_agent(self, agent):
        pass
class Agent: ...
class AgentException(Exception):
    pass
"""
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{tmp_path}:{env.get('PYTHONPATH', '')}"
    env["ALPHA_FACTORY_ENABLE_ADK"] = "true"

    proc = subprocess.Popen(
        ["governance-bridge", "--enable-adk", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        time.sleep(2)
        proc.terminate()
        out, _ = proc.communicate(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    assert "Registered GovernanceSimAgent" in out
    assert "ADK" in out
