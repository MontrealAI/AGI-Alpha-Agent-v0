# SPDX-License-Identifier: Apache-2.0
"""Tests for the memeplex TypeScript module."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MEMEPLEX_TS = REPO_ROOT / "src" / "memeplex.ts"


@pytest.mark.skipif(not shutil.which("tsc") or not shutil.which("node"), reason="tsc/node not available")
def test_meme_mining(tmp_path: Path) -> None:
    js_out = tmp_path / "src" / "memeplex.js"
    subprocess.run(
        [
            "tsc",
            "--target",
            "es2020",
            "--module",
            "es2020",
            "--moduleResolution",
            "node",
            "--rootDir",
            str(REPO_ROOT),
            "--outDir",
            str(tmp_path),
            MEMEPLEX_TS,
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    script = tmp_path / "run.mjs"
    script.write_text(
        f"import {{ mineMemes }} from '{js_out.resolve().as_posix()}';\n"
        "const runs = [\n"
        "  {edges:[{from:'A',to:'B'},{from:'B',to:'C'}]},\n"
        "  {edges:[{from:'A',to:'B'}]},\n"
        "  {edges:[{from:'A',to:'B'}]}\n"
        "];\n"
        "const memes = mineMemes(runs,2);\n"
        "console.log(JSON.stringify(memes));\n",
        encoding="utf-8",
    )
    res = subprocess.run(["node", script], capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    assert len(data) == 1
    assert data[0]["count"] == 3
