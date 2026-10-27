# SPDX-License-Identifier: Apache-2.0
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from independent_audit import audit


def run_controls(study, output):
    source = study / "deliveries/03.02-Data-Indexing-and-Selection/recovered.ipynb"
    base = json.loads(source.read_text())
    output.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).with_name("independent_run.py")
    checker = Path(__file__).with_name("independent_checks.py")
    with tempfile.TemporaryDirectory(prefix="agi-alpha-independent-controls-") as td:
        temp = Path(td)
        wrong = json.loads(json.dumps(base))
        wrong["cells"].append(
            {
                "cell_type": "code",
                "metadata": {},
                "source": "data.loc['California', 'area'] = 0",
                "execution_count": None,
                "outputs": [],
            }
        )
        examples = {"wrong-output": wrong}
        for name, text in [
            (
                "display-error",
                "class Broken:\n    def _repr_html_(self):\n        raise ValueError('deliberate formatting error')\nBroken()",
            ),
            ("outbound", "import socket\nsocket.socket().connect(('example.com', 443))"),
        ]:
            examples[name] = {
                "nbformat": 4,
                "nbformat_minor": 0,
                "metadata": {},
                "cells": [
                    {"cell_type": "code", "metadata": {}, "source": text, "outputs": [], "execution_count": None}
                ],
            }
        # Reproduce the material graphical defect found during visual review.
        # Numeric code stays identical; only the inline lifecycle is removed.
        graphical = json.loads((study / "deliveries/05.02-Introducing-Scikit-Learn/recovered.ipynb").read_text())
        replacements = 0
        for cell in graphical["cells"]:
            text = cell.get("source", "")
            text = "".join(text) if isinstance(text, list) else text
            replacements += text.count("%matplotlib inline")
            cell["source"] = text.replace("%matplotlib inline", "import matplotlib; matplotlib.use('Agg')")
        assert replacements == 1
        examples["plot-lifecycle"] = graphical
        reports = []
        for name, notebook in examples.items():
            nb = temp / (name + ".ipynb")
            nb.write_text(json.dumps(notebook))
            out = output / ("independent-adverse-" + name + ".json")
            env = {**os.environ, "MPLCONFIGDIR": str(temp / "mpl"), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
            case = "05.02-Introducing-Scikit-Learn" if name == "plot-lifecycle" else "03.02-Data-Indexing-and-Selection"
            result = subprocess.run(
                [sys.executable, str(script), str(nb), "--case", case, "--checks", str(checker), "--output", str(out)],
                cwd=temp,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            report = json.loads(out.read_text())
            valid = result.returncode == 1 and report["accepted"] is False
            if name == "wrong-output":
                valid = (
                    valid
                    and report["all_cells_completed"]
                    and any(x["name"] == "areas_unchanged" and not x["pass"] for x in report["checks"])
                )
            if name == "display-error":
                valid = valid and bool(report["display_errors"]) and report["executed_code_cells"] == 0
            if name == "plot-lifecycle":
                valid = (
                    valid
                    and report["all_cells_completed"]
                    and len(report["checks"]) == 10
                    and all(x["pass"] for x in report["checks"])
                    and any(not x["pass"] for x in report["graphical_checks"])
                )
            blocker_layer = None
            if name == "outbound":
                denied_at_creation = any(row["error_type"] == "PermissionError" for row in report["cells"])
                valid = (
                    valid
                    and (bool(report["outbound_attempts"]) or denied_at_creation)
                    and report["executed_code_cells"] == 0
                )
                blocker_layer = "environment_socket_creation" if denied_at_creation else "instrumented_connect"
            reports.append(
                {
                    "control": name,
                    "expected_rejection_observed": bool(valid),
                    "exit_code": result.returncode,
                    "blocker_layer": blocker_layer,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        identity_root = temp / "identity"
        shutil.copytree(study / "inputs/confirmation", identity_root / "inputs/confirmation")
        for filename in ["iris.csv", "iris-provenance.json"]:
            shutil.copy2(study / "inputs" / filename, identity_root / "inputs" / filename)
        for row in json.loads((study / "inputs/confirmation/source_manifest.json").read_text())["cases"]:
            case = Path(row["name"]).stem
            target = identity_root / "deliveries" / case
            target.mkdir(parents=True)
            for filename in ["recovered.ipynb", "identity.json", "changes.json"]:
                shutil.copy2(study / "deliveries" / case / filename, target / filename)
        before = audit(identity_root)
        manifest = identity_root / "deliveries/03.02-Data-Indexing-and-Selection/identity.json"
        identity = json.loads(manifest.read_text())
        identity["output_sha256"] = "0" * 64
        manifest.write_text(json.dumps(identity))
        after = audit(identity_root)
        valid = before["accepted"] and not after["accepted"] and not after["cases"][0]["checks"]["output_sha"]
        reports.append(
            {
                "control": "tampered-output-identity",
                "expected_rejection_observed": bool(valid),
                "before": before,
                "after": after,
            }
        )
    result = {
        "schema": "independent-adverse-controls/v2",
        "all_expected_rejections": all(x["expected_rejection_observed"] for x in reports),
        "controls": reports,
    }
    (output / "independent-adverse-controls.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("study", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = run_controls(args.study.resolve(), args.output.resolve())
    print(
        json.dumps({"all_expected_rejections": result["all_expected_rejections"], "controls": len(result["controls"])})
    )
    raise SystemExit(0 if result["all_expected_rejections"] else 1)
