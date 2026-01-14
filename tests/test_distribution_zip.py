# SPDX-License-Identifier: Apache-2.0
import re
import subprocess
import shutil
import zipfile
from pathlib import Path

import pytest

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
    if not (BROWSER_DIR / "node_modules").is_dir():
        pytest.skip("node_modules missing; run npm ci to install Insight demo dependencies")
    zip_path = BROWSER_DIR / "insight_browser.zip"
    if zip_path.exists():
        zip_path.unlink()
    result = subprocess.run(
        [
            "npm",
            "run",
            "build:dist",
        ],
        cwd=BROWSER_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert zip_path.exists(), "insight_browser.zip missing"
    assert zip_path.stat().st_size <= MAX_ZIP_BYTES, "zip size exceeds 500 MiB"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    expected = {
        "index.html",
        "insight.bundle.js",
        "service-worker.js",
        "style.css",
        "insight_browser_quickstart.pdf",
    }
    # ensure expected files exist
    for name in expected:
        assert name in names, f"{name} missing from zip"
    # ensure assets directory exists and contains files
    assert any(n.startswith("assets/") for n in names), "assets directory missing"
    assert "assets/manifest.json" in names, "assets/manifest.json missing from zip"
    # ensure no unexpected files
    allowed_prefixes = {"assets/"}
    for name in names:
        if name in expected:
            continue
        if any(name.startswith(p) for p in allowed_prefixes):
            continue
        pytest.fail(f"Unexpected file {name} in zip")
