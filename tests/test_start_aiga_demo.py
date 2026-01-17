# SPDX-License-Identifier: Apache-2.0
"""Tests for the AI-GA meta-evolution demo launcher."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path("alpha_factory_v1/demos/aiga_meta_evolution/start_aiga_demo.py")


def test_start_aiga_demo_help() -> None:
    """--help prints usage information."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--help",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_start_aiga_demo_missing_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing Docker binary should raise a clear error."""
    from alpha_factory_v1.demos.aiga_meta_evolution import start_aiga_demo as mod

    def boom(*_a, **_kw):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(mod.subprocess, "run", boom)

    with pytest.raises(FileNotFoundError):
        mod.main([])
