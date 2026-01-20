# SPDX-License-Identifier: Apache-2.0
"""CLI regression test for ``alpha_asi_world_model_demo`` helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
import tempfile

import pytest

pytest.importorskip("nbformat")


def test_cli_emit_helpers() -> None:
    """Ensure emit flags generate expected files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
        for flag in ["--emit-docker", "--emit-helm", "--emit-notebook"]:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo",
                    flag,
                ],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr

        assert (tmp / "Dockerfile").exists()
        assert (tmp / "helm_chart" / "values.yaml").exists()
        assert (tmp / "alpha_asi_world_model_demo.ipynb").exists()

    assert not Path(tmpdir).exists()
