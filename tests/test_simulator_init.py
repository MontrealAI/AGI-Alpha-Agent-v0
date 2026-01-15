# SPDX-License-Identifier: Apache-2.0
import shutil
import subprocess
from pathlib import Path

import pytest

SIM_TS = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/src/simulator.ts")


@pytest.mark.skipif(not shutil.which("tsc") or not shutil.which("node"), reason="tsc/node not available")
def test_simulator_init_fast(tmp_path: Path) -> None:
    js_out = tmp_path / "alpha_factory_v1" / "demos" / "alpha_agi_insight_v1" / "insight_browser_v1" / "src" / "simulator.js"
    subprocess.run(
        [
            "tsc",
            "--target",
            "es2020",
            "--module",
            "es2020",
            SIM_TS,
            "--outDir",
            tmp_path,
        ],
        check=True,
    )

    script = tmp_path / "run.mjs"
    script.write_text(
        f"import {{ Simulator }} from '{js_out.resolve().as_posix()}';\n"
        "const start = performance.now();\n"
        "const it = Simulator.run({popSize:1,generations:1});\n"
        "await it.next();\n"
        "console.log(performance.now()-start);\n",
        encoding="utf-8",
    )
    res = subprocess.run(["node", script], capture_output=True, text=True, check=True)
    elapsed = float(res.stdout.strip())
    assert elapsed < 70
