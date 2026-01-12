# SPDX-License-Identifier: Apache-2.0
"""Ensure the governance-sim CLI runs."""

import shutil
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform.startswith("win"), reason="governance-sim not supported on Windows")
def test_governance_sim_cli() -> None:
    """Verify the console script prints a result."""
    command = shutil.which("governance-sim")
    if command:
        cmd = [command]
    else:
        cmd = [sys.executable, "-m", "alpha_factory_v1.demos.solving_agi_governance.governance_sim"]
    result = subprocess.run(
        cmd + ["-N", "10", "-r", "20"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "mean cooperation" in result.stdout.lower()
