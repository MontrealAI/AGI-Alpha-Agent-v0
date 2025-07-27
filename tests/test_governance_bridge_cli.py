# SPDX-License-Identifier: Apache-2.0
"""Ensure the governance-bridge CLI is available."""

import subprocess

import pytest


pytest.importorskip("openai_agents", minversion="0.0.17")


def test_governance_bridge_help() -> None:
    """Verify the console script prints usage information."""
    result = subprocess.run(
        ["governance-bridge", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_governance_bridge_port_arg() -> None:
    """Verify the CLI accepts the --port option."""
    result = subprocess.run(
        ["governance-bridge", "--port", "1234", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
