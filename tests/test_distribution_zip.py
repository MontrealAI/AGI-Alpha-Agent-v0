# SPDX-License-Identifier: Apache-2.0
import os
import base64
import hashlib
import re
import subprocess
import shutil
import zipfile
from pathlib import Path

import pytest

from tests.conftest import _ensure_insight_node_modules

BROWSER_DIR = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1")
MAX_ZIP_BYTES = 500 * 1024 * 1024
NODE_MAJOR_RE = re.compile(r"v?(\d+)")


def _node_major() -> int | None:
    if not shutil.which("node"):
        return None
    try:
        version = subprocess.check_output(["node", "--version"], text=True).strip()
    except subprocess.SubprocessError:
        return None
    match = NODE_MAJOR_RE.match(version)
    if not match:
        return None
    return int(match.group(1))


@pytest.mark.skipif(not shutil.which("npm"), reason="npm not available")
def test_distribution_zip(tmp_path: Path) -> None:
    node_major = _node_major()
    if node_major is None or node_major < 22:
        pytest.skip("Node.js 22+ is required to build the Insight demo")
    zip_path = BROWSER_DIR / "insight_browser.zip"
    if zip_path.exists():
        zip_path.unlink()
    env = os.environ.copy()
    env.setdefault("FETCH_ASSETS_SKIP_LLM", "1")
    _ensure_insight_node_modules(env)
    result = subprocess.run(
        [
            "npm",
            "run",
            "build:dist",
        ],
        cwd=BROWSER_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert zip_path.exists(), "insight_browser.zip missing"
    assert zip_path.stat().st_size <= MAX_ZIP_BYTES, "zip size exceeds 500 MiB"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        host = zf.read("sandbox_worker_host.html").decode()
        assert "<script src=" not in host, "Opaque sandbox must not fetch external scripts offline"
        script = re.search(r"<script>([\s\S]*?)</script>", host)
        assert script, "Self-contained sandbox script missing"
        digest = base64.b64encode(hashlib.sha384(script[1].encode()).digest()).decode()
        assert f"'sha384-{digest}'" in zf.read("index.html").decode()
    expected = {
        "index.html",
        "insight.bundle.js",
        "service-worker.js",
        "style.css",
        "d3.exports.js",
        "d3_exports.js",
        "bootstrap.js",
        "sandbox_worker_host.html",
        "sandbox_worker_host.js",
        "worker/evolver.js",
        "worker/arenaWorker.js",
        "worker/umapWorker.js",
    }
    if Path("docs/insight_browser_quickstart.pdf").exists():
        expected.add("insight_browser_quickstart.pdf")
    # ensure expected files exist
    for name in expected:
        assert name in names, f"{name} missing from zip"
    # ensure assets directory exists and contains files
    assert any(n.startswith("assets/") for n in names), "assets directory missing"
    assert "assets/manifest.json" in names, "assets/manifest.json missing from zip"
    # ensure no unexpected files
    allowed_prefixes = {"assets/", "worker/"}
    for name in names:
        if name in expected:
            continue
        if any(name.startswith(p) for p in allowed_prefixes):
            continue
        pytest.fail(f"Unexpected file {name} in zip")
