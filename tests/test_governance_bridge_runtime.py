# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import subprocess
import time

import pytest


pytest.importorskip("openai_agents", minversion="0.0.17")


def test_governance_bridge_runtime() -> None:
    """Launch governance-bridge and verify agent registration."""
    proc = subprocess.Popen(
        ["governance-bridge", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
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
