# SPDX-License-Identifier: Apache-2.0
"""Tests for entropy.ts"""

import shutil
import subprocess
from pathlib import Path

import pytest

ENTROPY_TS = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/src/utils/entropy.ts")


@pytest.mark.skipif(not shutil.which("tsc") or not shutil.which("node"), reason="tsc/node not available")
def test_pareto_entropy(tmp_path: Path) -> None:
    subprocess.run(
        [
            "tsc",
            "--target",
            "es2020",
            "--module",
            "es2020",
            ENTROPY_TS,
            "--outDir",
            tmp_path,
        ],
        check=True,
    )
    js_out = tmp_path / "entropy.js"

    script = tmp_path / "run.mjs"
    script.write_text(
        f"import {{ paretoEntropy }} from '{js_out.resolve().as_posix()}';\n"
        "const pts = [{logic:0.1,feasible:0.1},{logic:0.9,feasible:0.9}];\n"
        "console.log(paretoEntropy(pts,2).toFixed(2));\n",
        encoding="utf-8",
    )
    res = subprocess.run(["node", script], capture_output=True, text=True, check=True)
    assert res.stdout.strip() == "1.00"
