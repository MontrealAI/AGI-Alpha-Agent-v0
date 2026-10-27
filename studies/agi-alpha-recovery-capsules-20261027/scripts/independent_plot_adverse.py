# SPDX-License-Identifier: Apache-2.0
"""Regress native inline to Agg and require independent graphical rejection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("study", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    study = args.study.resolve()
    outdir = args.output.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    case = "05.02-Introducing-Scikit-Learn"
    source = study / "deliveries" / case / "recovered.ipynb"
    notebook = json.loads(source.read_bytes())
    mutations = 0
    for cell in notebook["cells"]:
        code = cell.get("source", "")
        code = "".join(code) if isinstance(code, list) else code
        if "%matplotlib inline" in code:
            code = code.replace("%matplotlib inline", "import matplotlib\nmatplotlib.use('Agg')")
            cell["source"] = code.splitlines(keepends=True)
            mutations += 1
    assert mutations == 1, "Expected one original native inline magic"
    with tempfile.TemporaryDirectory(prefix="agi-alpha-plot-adverse-") as work:
        work = Path(work)
        candidate = work / "forced-agg.ipynb"
        candidate.write_text(json.dumps(notebook, indent=2) + "\n")
        env = dict(os.environ, MPLCONFIGDIR="/tmp/agi-alpha-capsule-mpl", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
        process = subprocess.run([
            sys.executable, str(study / "scripts" / "independent_run.py"),
            str(candidate), "--case", case,
            "--checks", str(study / "scripts" / "independent_checks.py"),
            "--output", str(outdir / "forced-agg-execution.json")
        ], cwd=work, env=env, capture_output=True, text=True, timeout=120)
        run = json.loads((outdir / "forced-agg-execution.json").read_text())
        correct = (
            process.returncode == 1 and not run["accepted"]
            and run["all_cells_completed"]
            and all(row["pass"] for row in run["checks"])
            and any(not row["pass"] for row in run["graphical_checks"])
        )
        result = {
            "schema": "independent-graphical-adverse-control/v1",
            "case": case, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "mutation": "Replace original inline magic with Agg; no numerical code changed",
            "expected_rejection": correct,
            "all_32_code_cells_execute": run["all_cells_completed"],
            "all_10_case_numerical_checks_still_pass": all(row["pass"] for row in run["checks"]),
            "graphical_checks": run["graphical_checks"],
            "subprocess_exit_code": process.returncode,
            "stdout": process.stdout, "stderr": process.stderr
        }
        (outdir / "independent-plot-adverse-control.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"expected_rejection": correct, "numeric_checks_preserved": result["all_10_case_numerical_checks_still_pass"]}))
        raise SystemExit(0 if correct else 1)


if __name__ == "__main__":
    main()
