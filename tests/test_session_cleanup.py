# SPDX-License-Identifier: Apache-2.0
"""Nested test runs must not remove the outer session's browser assets."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("nested", [True, False])
def test_browser_assets_survive_until_owning_session_ends(tmp_path: Path, nested: bool) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    shutil.copyfile(Path(__file__).with_name("conftest.py"), tests_dir / "conftest.py")
    (tests_dir / "test_sample.py").write_text("def test_sample():\n    assert True\n")
    assets = tmp_path / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/dist"
    assets.mkdir(parents=True)
    marker = assets / "index.html"
    marker.write_text("shared browser build")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    env = os.environ.copy()
    env["AF_CLEANUP_DISK"] = "1"
    if nested:
        env["ALPHA_PYTEST_OWNER_PID"] = str(os.getpid())
    else:
        env.pop("ALPHA_PYTEST_OWNER_PID", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--confcutdir=tests", "tests"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.exists() is nested
