# SPDX-License-Identifier: Apache-2.0
"""Ensure the governance-bridge CLI is available."""

import shutil
import subprocess
import sys

import pytest


pytest.importorskip("openai_agents", minversion="0.0.17")


def _bridge_command() -> list[str]:
    command = shutil.which("governance-bridge")
    if command:
        return [command]
    return [sys.executable, "-m", "alpha_factory_v1.demos.solving_agi_governance.openai_agents_bridge"]


def test_governance_bridge_help() -> None:
    """Verify the console script prints usage information."""
    result = subprocess.run(
        _bridge_command() + ["--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_governance_bridge_port_arg() -> None:
    """Verify the CLI accepts the --port option."""
    result = subprocess.run(
        _bridge_command() + ["--port", "1234", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
