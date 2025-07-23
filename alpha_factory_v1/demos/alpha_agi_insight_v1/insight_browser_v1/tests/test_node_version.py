# SPDX-License-Identifier: Apache-2.0
import subprocess
from pathlib import Path
import runpy
import sys
from unittest import mock
import pytest


def test_requires_node_22() -> None:
    browser_dir = Path(__file__).resolve().parents[1]
    script = browser_dir / "build.js"
    node_code = "Object.defineProperty(process.versions,'node',{value:'21.0.0'});" f" import('./{script.name}')"
    res = subprocess.run(
        ["node", "-e", node_code],
        cwd=browser_dir,
        text=True,
        capture_output=True,
    )
    assert res.returncode == 1
    assert "Node.js 22+ is required. Current version: 21.0.0" in res.stderr


def test_allows_node_22() -> None:
    browser_dir = Path(__file__).resolve().parents[1]
    script = browser_dir / "build.js"
    node_code = "Object.defineProperty(process.versions,'node',{value:'22.0.0'});" f" import('./{script.name}')"
    res = subprocess.run(
        ["node", "-e", node_code],
        cwd=browser_dir,
        text=True,
        capture_output=True,
    )
    assert res.returncode == 0, res.stderr


def test_requires_python_311() -> None:
    browser_dir = Path(__file__).resolve().parents[1]
    script = browser_dir / "manual_build.py"
    with mock.patch.object(sys, "version_info", (3, 10)):
        with pytest.raises(SystemExit):
            runpy.run_path(script, run_name="__main__")
