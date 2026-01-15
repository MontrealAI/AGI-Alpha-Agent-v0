# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BROWSER_DIR = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1")

REASON_NODE = "node not available"


@pytest.mark.skipif(
    not shutil.which("node"),
    reason=REASON_NODE,
)  # type: ignore[misc]
def test_manual_build_missing_tsc(tmp_path: Path) -> None:
    try:
        node_version = subprocess.check_output(["node", "--version"], text=True).strip()
    except subprocess.SubprocessError:
        pytest.skip("node not available")
    if not node_version.lstrip("v").startswith("22."):
        pytest.skip("Node.js 22+ required for manual build")
    work = tmp_path / "browser"
    shutil.copytree(BROWSER_DIR, work)
    # provide required .env
    (work / ".env").write_text((BROWSER_DIR / ".env.sample").read_text())
    (work / "build" / "__init__.py").touch()

    # scrub placeholder text to avoid asset download
    for sub in ("wasm", "wasm_llm"):
        d = work / sub
        if d.exists():
            for p in d.rglob("*"):
                if p.is_file():
                    data = p.read_bytes().replace(b"placeholder", b"")
                    p.write_bytes(data)
    bundle = work / "lib" / "bundle.esm.min.js"
    bundle.write_text(bundle.read_text().replace("Placeholder", ""))

    # isolate PATH with node only
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    node = shutil.which("node")
    assert node
    os.symlink(node, bin_dir / "node")

    env = os.environ.copy()
    env["PATH"] = str(bin_dir)
    env["PINNER_TOKEN"] = "dummy"
    env["WEB3_STORAGE_TOKEN"] = "dummy"

    result = subprocess.run(
        [sys.executable, "manual_build.py"],
        cwd=work,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "TypeScript compiler not found" in result.stderr
