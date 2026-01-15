# SPDX-License-Identifier: Apache-2.0
"""Tests for the replay TypeScript module."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPLAY_TS = Path("src/replay.ts")


@pytest.mark.skipif(not shutil.which("tsc") or not shutil.which("node"), reason="tsc/node not available")
def test_branching_and_cid(tmp_path: Path) -> None:
    js_out = tmp_path / "src" / "replay.js"
    subprocess.run(
        [
            "tsc",
            "--target",
            "es2020",
            "--module",
            "es2020",
            REPLAY_TS,
            "--outDir",
            tmp_path,
        ],
        check=True,
    )

    script = tmp_path / "run.mjs"
    script.write_text(
        f"import {{ ReplayDB }} from '{js_out.resolve().as_posix()}';\n"
        "const db = new ReplayDB('jest');\n"
        "await db.open();\n"
        "const root = await db.addFrame(null,{msg:'root'});\n"
        "const a = await db.addFrame(root,{msg:'a'});\n"
        "const b = await db.addFrame(root,{msg:'b'});\n"
        "const cid1 = await db.computeCid(b);\n"
        "const thread = await db.exportThread(b);\n"
        "const cid2 = await ReplayDB.cidForFrames(thread);\n"
        "console.log(thread.length,cid1===cid2);\n",
        encoding="utf-8",
    )
    res = subprocess.run(["node", script], capture_output=True, text=True, check=True)
    parts = res.stdout.strip().split()
    assert int(parts[0]) == 2
    assert parts[1] == "true"
