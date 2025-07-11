# SPDX-License-Identifier: Apache-2.0
import subprocess
import shutil
import zipfile
from pathlib import Path

import pytest

BROWSER_DIR = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1")
MAX_ZIP_BYTES = 500 * 1024 * 1024


@pytest.mark.skipif(not shutil.which("npm"), reason="npm not available")
def test_distribution_zip(tmp_path: Path) -> None:
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
        "manifest.json",
        "style.css",
        "insight_browser_quickstart.pdf",
    }
    # ensure expected files exist
    for name in expected:
        assert name in names, f"{name} missing from zip"
    # ensure assets directory exists and contains files
    assert any(n.startswith("assets/") for n in names), "assets directory missing"
    # ensure no unexpected files
    allowed_prefixes = {"assets/"}
    for name in names:
        if name in expected:
            continue
        if any(name.startswith(p) for p in allowed_prefixes):
            continue
        pytest.fail(f"Unexpected file {name} in zip")
