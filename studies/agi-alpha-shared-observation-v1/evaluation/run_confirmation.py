# SPDX-License-Identifier: Apache-2.0
"""Run frozen finite-model confirmation and preserve every candidate/reference result."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from reference import check, load, reference


def save(path: Path, value: dict[str, Any]) -> None:
    """Serialize an evidence object without nonfinite JSON numbers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def verify_freeze(root: Path, path: Path) -> None:
    """Require exact frozen source/input identities before execution."""
    freeze = json.loads(path.read_text())
    for name, entry in freeze["files"].items():
        expected = entry["sha256"] if isinstance(entry, dict) else entry
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if expected != actual:
            raise ValueError(f"freeze mismatch: {name}")


def main() -> int:
    """Execute the protected cohort with the actual frozen compiler."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--input-dir", type=Path, default=Path("evaluation/protected/cases"))
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/confirmation-v1"))
    parser.add_argument("--technical-freeze", type=Path, default=Path("evidence/technical-freeze-v1_0_1.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    verify_freeze(root, root / args.technical_freeze)
    verify_freeze(root, root / "evaluation/reference-freeze-v1.json")
    input_dir, output_dir = root / args.input_dir, root / args.output_dir
    if output_dir.exists():
        raise ValueError("refusing to overwrite existing confirmation evidence")
    manifest = json.loads((input_dir / "manifest.json").read_text())
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for entry in manifest["cases"]:
        input_path = input_dir / entry["filename"]
        mission, digest = load(input_path)
        if digest != entry["sha256"]:
            raise ValueError(f"case digest mismatch: {input_path.name}")
        folder = output_dir / entry["case_id"]
        folder.mkdir(parents=True)
        candidate_path = folder / "candidate.json"
        command = [
            sys.executable,
            str(root / "capability/compiler.py"),
            "--mission",
            str(input_path),
            "--output",
            str(candidate_path),
            "--profile",
            str(root / "capability/sensor_profile.json"),
        ]
        before = time.perf_counter()
        process = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=30, check=False)
        elapsed = time.perf_counter() - before
        expected = reference(mission, digest)
        save(folder / "reference.json", expected)
        if candidate_path.exists():
            try:
                supplied = json.loads(candidate_path.read_text())
                checked = check(mission, supplied, digest)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                checked = {"conforms_to_independent_reference": False, "failures": [f"candidate read/check: {exc}"]}
        else:
            checked = {"conforms_to_independent_reference": False, "failures": ["candidate output absent"]}
        if process.returncode != 0:
            checked["conforms_to_independent_reference"] = False
            checked["failures"].append(f"compiler exit code {process.returncode}")
        save(folder / "check.json", checked)
        save(
            folder / "process.json",
            {
                "command": command,
                "returncode": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "wall_seconds": elapsed,
            },
        )
        rows.append(
            {
                "case_id": entry["case_id"],
                "category": entry["category"],
                "conforms": checked["conforms_to_independent_reference"],
                "observation_accepted": expected["observation_accepted"],
                "baseline_feasible": expected["total_baseline_cost"] is not None,
                "total_value_of_information": expected["total_value_of_information"],
                "operator_count": len(mission["operators"]),
                "state_count": len(mission["states"]),
                "branch_count": sum(len(op["branches"]) for op in expected["operators"]),
                "unreachable_branches": sum(not b["reachable"] for op in expected["operators"] for b in op["branches"]),
                "unsafe_reachable_branches": sum(
                    b["reachable"] and not b["valid"] for op in expected["operators"] for b in op["branches"]
                ),
                "wall_seconds": elapsed,
                "failures": checked["failures"],
            }
        )
    categories = {}
    for category in dict.fromkeys(row["category"] for row in rows):
        group = [row for row in rows if row["category"] == category]
        categories[category] = {
            "cases": len(group),
            "conforms": sum(row["conforms"] for row in group),
            "accepted": sum(row["observation_accepted"] for row in group),
            "refused": sum(not row["observation_accepted"] for row in group),
        }
    summary = {
        "schema": "shared-observation-confirmation-summary/v1",
        "started_at_utc": started,
        "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "technical_freeze": str(args.technical_freeze),
        "reference_freeze": "evaluation/reference-freeze-v1.json",
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "case_count": len(rows),
        "conforms_count": sum(row["conforms"] for row in rows),
        "accepted_count": sum(row["observation_accepted"] for row in rows),
        "refused_count": sum(not row["observation_accepted"] for row in rows),
        "categories": categories,
        "rows": rows,
        "execution_authorized": False,
        "frontier_model_trials": 0,
        "live_customer_acceptances": 0,
        "evidence_type": "executed finite synthetic model; independently checked software output",
    }
    save(output_dir / "summary.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, indent=2))
    return 0 if summary["conforms_count"] == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
