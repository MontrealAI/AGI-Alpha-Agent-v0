# SPDX-License-Identifier: Apache-2.0
"""Tests for the taxonomy TypeScript module."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

TAXONOMY_TS = Path("src/taxonomy.ts")


@pytest.mark.skipif(not shutil.which("tsc") or not shutil.which("node"), reason="tsc/node not available")
def test_taxonomy_mine_and_prune(tmp_path: Path) -> None:
    js_out = tmp_path / "src" / "taxonomy.js"
    subprocess.run(
        ["tsc", "--target", "es2020", "--module", "es2020", TAXONOMY_TS, "--outDir", tmp_path], check=True
    )

    script = tmp_path / "run.mjs"
    script.write_text(
        f"import {{ mineTaxonomy, pruneTaxonomy }} from '{js_out.resolve().as_posix()}';\n"
        "const runs = [\n"
        "  {params:{sector:'A'}},\n"
        "  {params:{sector:'B'}},\n"
        "  {params:{sector:'A'}}\n"
        "];\n"
        "let g = mineTaxonomy(runs);\n"
        "g = pruneTaxonomy(g, new Set(['A']));\n"
        "console.log(JSON.stringify(g));\n"
    )
    result = subprocess.run(["node", script], capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    assert set(data["nodes"].keys()) == {"A"}
