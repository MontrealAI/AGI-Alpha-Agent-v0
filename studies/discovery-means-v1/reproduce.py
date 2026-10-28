# SPDX-License-Identifier: Apache-2.0
"""Replay frozen finite-model evidence without modifying original receipts."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def sha(path: Path) -> str:
    """Return the exact source identity."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path) -> ModuleType:
    """Load a verified local module through the active installed environment."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    """Verify source bindings and replay every frozen finite case."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, required=True, help="New output directory; must not exist")
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    study = repo / "studies/discovery-means-v1"
    evidence = study / "evaluation"
    manifest_path = evidence / "task_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    candidate_path = repo / "contrib/discovery_means_v1/instrument.py"
    expected_solver_hashes = set(manifest["source_freeze"].values())
    if expected_solver_hashes != {sha(candidate_path)}:
        raise RuntimeError("Candidate source differs from the frozen instrument")
    if sha(evidence / "evaluate.py") != manifest["generator_sha256"]:
        raise RuntimeError("Frozen independent evaluator differs")
    if sha(evidence / "protocol.json") != manifest["protocol_sha256"]:
        raise RuntimeError("Frozen protocol differs")
    native_receipt = json.loads((repo / "contrib/discovery_means_v1/evidence/native-receipt.json").read_text())
    loaded = {}
    for name, identity in native_receipt["loaded_modules"].items():
        if name == "discovery_means.instrument":
            continue
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        if sha(path) != identity["sha256"]:
            raise RuntimeError(f"Installed native module identity differs: {name}")
        loaded[name] = {"path": str(path), "sha256": sha(path)}
    out = args.out.resolve()
    if out.exists():
        raise RuntimeError("Replay output already exists; choose a new directory")
    out.mkdir(parents=True)
    evaluator = load_module("frozen_independent_evaluation", evidence / "evaluate.py")
    candidate = load_module("frozen_candidate_instrument", candidate_path)
    original_rows = {r["case_id"]: r for r in json.loads((evidence / "results.json").read_text())["rows"]}
    rows = []
    for case in manifest["cases"]:
        problem = evaluator.clean_case(case)
        oracle = evaluator.conventional_adaptive(problem)
        report = candidate.solve(copy.deepcopy(problem))
        static = evaluator.conventional_static(problem)
        audit = evaluator.audit_policy(problem, report["policy"]) if report["status"] == "optimal" else None
        correct = report["status"] == oracle["status"]
        if report["status"] == "optimal":
            correct = bool(correct and audit["accepted"] and report["worst_cost"] == oracle["worst_cost"]
                           and audit["worst_cost"] == oracle["worst_cost"]
                           and audit["worst_depth"] == report["worst_depth"])
        previous = original_rows[case["case_id"]]
        rows.append({"case_id": case["case_id"], "correct": correct, "instrument": report,
                     "certificate_audit": audit, "static": static,
                     "instrument_report_equal_original": report == previous["instrument"],
                     "oracle_equal_original": oracle == previous["oracle"],
                     "static_equal_original": static == previous["static"]})
    validation = []
    for probe in manifest["invalid_probes"]:
        try:
            candidate.solve(evaluator.clean_case(probe["case"]))
            rejected = False
        except (ValueError, TypeError):
            rejected = True
        validation.append({"probe": probe["probe"], "rejected": rejected})
    agent_audits: dict[str, Any] = {}
    by_id = {case["case_id"]: case for case in manifest["cases"]}
    for filename in ("generalist_outputs.json", "prompt_outputs.json"):
        reports = json.loads((evidence / filename).read_text())
        ids = [r["case_id"] for r in reports]
        if len(ids) != len(by_id) or set(ids) != set(by_id) or len(set(ids)) != len(ids):
            raise RuntimeError("Hosted-arm denominator differs")
        correct = 0
        for report in reports:
            previous = original_rows[report["case_id"]]["oracle"]
            expected = "feasible" if previous["status"] == "optimal" else "infeasible"
            ok = report["status"] == expected and report["worst_cost"] == previous["worst_cost"]
            if report["status"] == "feasible":
                audit = evaluator.audit_policy(evaluator.clean_case(by_id[report["case_id"]]), report["policy"])
                ok = ok and audit["accepted"] and audit["worst_cost"] == previous["worst_cost"]
            correct += bool(ok)
        agent_audits[filename] = {"correct": correct, "denominator": len(ids), "new_model_run": False}
    shutil.copyfile(manifest_path, out / "task_manifest.json")
    shutil.copyfile(evidence / "native_predecessor.py", out / "native_predecessor.py")
    native_run = subprocess.run([sys.executable, str(out / "native_predecessor.py")], capture_output=True,
                                text=True, check=True, timeout=30)
    (out / "native_replay.stdout.txt").write_text(native_run.stdout)
    native = json.loads((out / "native_predecessor_results.json").read_text())
    summary = {"cases": len(rows), "correct": sum(r["correct"] for r in rows),
               "reports_equal_original": sum(r["instrument_report_equal_original"] for r in rows),
               "oracles_equal_original": sum(r["oracle_equal_original"] for r in rows),
               "static_equal_original": sum(r["static_equal_original"] for r in rows),
               "validation_rejected": sum(r["rejected"] for r in validation),
               "native": native["summary"], "hosted_output_reaudits": agent_audits}
    result = {"scope": "Portable replay of existing synthetic finite evidence; no new confirmation or hosted model run",
              "source_sha256": sha(candidate_path), "task_manifest_sha256": sha(manifest_path),
              "installed_native_modules": loaded, "rows": rows, "validation": validation, "summary": summary}
    (out / "replay.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    if summary["correct"] != 24 or summary["reports_equal_original"] != 24 or summary["validation_rejected"] != 6:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
