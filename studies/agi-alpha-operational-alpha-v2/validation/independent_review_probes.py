# SPDX-License-Identifier: Apache-2.0
"""Separate internal audit of frozen evidence and accounting identities."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT.parents[2] / "research_runs"


def load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import audit target")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(runs: Path = RUNS) -> dict[str, Any]:
    records: list[dict[str, Any]] = []

    def record(name: str, passed: bool, **detail: Any) -> None:
        records.append({"name": name, "passed": passed, **detail})

    frozen = json.loads((ROOT / "protocol/CONFIRMATION_FREEZE.json").read_text())
    for relative, expected in frozen["files"].items():
        actual = digest(ROOT / relative)
        record("frozen-identity:" + relative, actual == expected, sha256=actual)
    evaluator = load(ROOT / "benchmark/private/evaluate.py", "audit_evaluator")
    for case, expected in [("development", 6), ("c1", 7), ("c2", 3), ("c3", 6), ("c4", 6)]:
        original = evaluator.evaluate(case, ROOT / "benchmark/cases" / case)
        reference = evaluator.evaluate(case, ROOT / "benchmark/private/references" / case)
        record("starter-calibration:" + case, original["passed"] == expected and original["total"] == 10,
               observed_passed=original["passed"], expected_passed=expected)
        record("reference-feasible:" + case, reference["accepted"] and reference["total"] == 10)
    for arm in ("U", "E"):
        state = json.loads((runs / arm / "state.json").read_text())
        events = [json.loads(line) for line in (runs / arm / "events.jsonl").read_text().splitlines()]
        operations = [row["operation"] for row in events if "operation" in row]
        record("successful-operation-sequence:" + arm, operations == list(range(1, state["operations"] + 1)))
        record("post-freeze-start:" + arm, state["started_at"] > frozen["utc_epoch"])
        record("closed-within-envelope:" + arm, state["closed"] and state["within_envelope"])
        for case in ("c1", "c2", "c3", "c4"):
            submission = runs / arm / "frozen_submission" / case
            result = evaluator.evaluate(case, submission)
            record("submitted-acceptance:" + arm + "/" + case, result["accepted"],
                   passed_categories=result["passed"], total_categories=result["total"],
                   source_sha256=result["source_sha256"])
            record("deliverables-and-public-test:" + arm + "/" + case,
                   (submission / "REPAIR.md").is_file() and (submission / "test_regression.py").is_file()
                   and (submission / "test_public.py").read_bytes()
                   == (ROOT / "benchmark/cases" / case / "test_public.py").read_bytes())
    capsule = ROOT / "workflows/workflow_capsule.zip"
    record("transport-and-ordinary-library-identities",
           capsule.read_bytes() == (ROOT / "integration/results/workflow-v2/received-workflow.bin").read_bytes()
           == (ROOT / "integration/results/workflow-v2/ordinary-library-workflow.bin").read_bytes())
    with zipfile.ZipFile(capsule) as archive:
        record("capsule-content-closure", sorted(archive.namelist())
               == sorted(["expert_v1.json", "learned_v2.json", "contract_probes.py", "CAPABILITY.md"]))
    economic = load(ROOT / "economics/run_economics.py", "audit_economic")
    config = json.loads((ROOT / "economics/protocol.json").read_text())
    synthetic = {"arms": {arm: {"accepted": 4, "attempted": 4} for arm in ("U", "E", "E_plus")}}
    choice = {"price_ratio": 0.5, "reserve_days": 7}
    histories = 0
    events_count = 0
    errors = []
    for seed in range(701, 713):
        for profile in ("reference", "thin_demand", "low_price_human", "transfer_shift"):
            paired: dict[str, Any] = {}
            for policy in economic.POLICIES:
                row = economic.simulate(synthetic, config, seed, profile, policy, choice, record=True)
                histories += 1
                events_count += len(row["events"])
                cash = config["seed_capital_cents"]
                expense_ids = []
                for event in row["events"]:
                    if event["kind"] == "cost":
                        cash -= event["cents"]
                        expense_ids.append(event["activity"])
                    elif event["kind"] == "collection":
                        cash += event["cents"]
                    elif event["kind"] == "refund":
                        cash -= event["cents"]
                    if cash != event["cash_cents"]:
                        errors.append([seed, profile, policy, "event-cash"])
                    if event["kind"] == "day-close" and event["capacity_unused"] < 0:
                        errors.append([seed, profile, policy, "negative-capacity"])
                    if event["kind"] == "delivery" and event["job"] != event["original_task_id"]:
                        errors.append([seed, profile, policy, "changed-retry-task"])
                if cash != row["cash_cents"] or cash != row["seed_capital_cents"] + row["profit_cents"]:
                    errors.append([seed, profile, policy, "final-cash"])
                if len(expense_ids) != len(set(expense_ids)):
                    errors.append([seed, profile, policy, "duplicate-cost-id"])
                if row["obligations_cents"] or row["receivables_cents"]:
                    errors.append([seed, profile, policy, "unclosed-settlement"])
                if row["actual_profit_cents"] is not None or row["actual_collections_cents"] != 0:
                    errors.append([seed, profile, policy, "actual-simulation-confusion"])
                if policy in ("shared_retention", "library_retention"):
                    row.pop("policy")
                    paired[policy] = row
            if paired["shared_retention"] != paired["library_retention"]:
                errors.append([seed, profile, "library-graph-mismatch"])
    record("independent-event-cash-and-library-audit", not errors,
           synthetic_audit_histories=histories, events=events_count, errors=errors,
           seeds=[701, 712], note="Artificial audit input; neither pilot estimates nor economic confirmation.")
    result = {"schema": "operational-alpha-independent-internal-review/v1", "utc_epoch": time.time(),
              "reviewer": "separate internal agent; not external replication",
              "economic_source_sha256": digest(ROOT / "economics/run_economics.py"),
              "economic_protocol_sha256": digest(ROOT / "economics/protocol.json"),
              "passed": sum(row["passed"] for row in records), "total": len(records), "checks": records}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, default=RUNS)
    args = parser.parse_args()
    result = run(args.runs.resolve())
    (ROOT / "validation/probes.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("passed", "total", "economic_source_sha256")}))
