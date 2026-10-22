# SPDX-License-Identifier: Apache-2.0
"""Exercise local asset paths at the real offline child-process boundary."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_local_assets_reach_credential_clean_offline_child(tmp_path: Path) -> None:
    insight_root = tmp_path / "insight assets"
    fetch_root = tmp_path / "fallback assets"
    insight_root.mkdir()
    fetch_root.mkdir()
    probe = tmp_path / "test_runner_boundary.py"
    probe.write_text(
        f"""# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path
import runpy
import socket
import pytest


def test_child_boundary():
    insight_root = Path({str(insight_root)!r})
    fetch_root = Path({str(fetch_root)!r})
    assert os.environ["INSIGHT_ASSET_ROOT"] == str(insight_root)
    assert os.environ["FETCH_ASSETS_DIR"] == str(fetch_root)
    asset_root = runpy.run_path({str(ROOT / "tests" / "test_assets_replaced.py")!r})["_asset_root"]
    assert asset_root() == insight_root
    del os.environ["INSIGHT_ASSET_ROOT"]
    assert asset_root() == fetch_root
    for key in ("OPENAI_API_KEY", "GITHUB_TOKEN", "UNRELATED_PRIVATE_TOKEN"):
        assert key not in os.environ
    assert os.environ["NEO4J_PASSWORD"] == "local-tests-only-strong-password"
    assert os.environ["API_TOKEN"] == "test-token"
    assert os.environ["ALPHA_TEST_OFFLINE"] == "1"
    with socket.socket() as client:
        with pytest.raises(OSError, match="external network disabled by offline test runner"):
            client.connect(("198.51.100.1", 443))
"""
    )
    env = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "HOME": str(tmp_path / "home"),
        "LANG": "C.UTF-8",
        "INSIGHT_ASSET_ROOT": str(insight_root),
        "FETCH_ASSETS_DIR": str(fetch_root),
        "OPENAI_API_KEY": "fixture-openai-only",
        "GITHUB_TOKEN": "fixture-github-only",
        "UNRELATED_PRIVATE_TOKEN": "fixture-private-only",
        "NEO4J_PASSWORD": "fixture-password-only",
        "API_TOKEN": "fixture-api-only",
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_local_tests",
            "--noconftest",
            "-c",
            "/dev/null",
            "-p",
            "no:cacheprovider",
            str(probe),
            "-q",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
