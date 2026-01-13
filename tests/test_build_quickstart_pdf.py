# SPDX-License-Identifier: Apache-2.0
import re
import subprocess
import shutil
from pathlib import Path

import pytest

BROWSER_DIR = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1")
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
def test_pdf_copied_after_build(tmp_path: Path) -> None:
    node_major = _node_major()
    if node_major is None or node_major < 22:
        pytest.skip("Node.js 22+ is required to build the Insight demo")
    dist = BROWSER_DIR / "dist"
    pdf = dist / "insight_browser_quickstart.pdf"
    if pdf.exists():
        pdf.unlink()
    result = subprocess.run(
        [
            "npm",
            "run",
            "build",
        ],
        cwd=BROWSER_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert pdf.exists(), "insight_browser_quickstart.pdf missing in dist"
