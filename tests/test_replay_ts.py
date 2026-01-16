# SPDX-License-Identifier: Apache-2.0
"""Tests for the replay TypeScript module."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPLAY_TS = Path("alpha_factory_v1/core/replay.ts")


@pytest.mark.skipif(not shutil.which("tsc") or not shutil.which("node"), reason="tsc/node not available")
def test_branching_and_cid(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"type":"module"}', encoding="utf-8")
    js_out = tmp_path / REPLAY_TS.with_suffix(".js")
    subprocess.run(
        [
            "tsc",
            "--target",
            "es2020",
            "--module",
            "es2020",
            "--outDir",
            str(tmp_path),
            "--rootDir",
            ".",
            REPLAY_TS,
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
