# SPDX-License-Identifier: Apache-2.0
"""Aggregate frozen receipts; does not rerun discovery or invent monetary costs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    output = ROOT / "results/confirmation_summary.json"
    if output.exists():
        raise RuntimeError("refusing to replace a published confirmation aggregate")
    arms = {}
    for label in ("U", "E", "E_plus"):
        name = "S3_" + label
        path = ROOT / "results/trials" / name
        state = json.loads((path / "state.json").read_text())
        acceptance = json.loads((ROOT / "results" / (name + "_acceptance.json")).read_text())
        events = [json.loads(x) for x in (path / "events.jsonl").read_text().splitlines()]
        assert state["closed"] and state["within_envelope"]
        for rel, identity in state["submission_inventory"].items():
            assert sha(path / "frozen_submission" / rel) == identity["sha256"]
        for rel, identity in state["initial_inventory"].items():
            assert sha(path / rel) == identity["sha256"], rel
        arms[label] = {
            "accepted": acceptance["accepted"],
            "passed_missions": acceptance["passed"],
            "total_missions": acceptance["total"],
            "campaigns": 1,
            "source_families": 2,
            "request_variants_per_mission": acceptance["request_variants_per_mission"],
            **{
                k: state[k]
                for k in ("elapsed_seconds", "operations", "tool_elapsed_seconds", "output_bytes", "within_envelope")
            },
            "logged_python_executions": state["test_executions"],
            "nonzero_exit_python_executions": sum(
                e.get("kind") == "run" and e.get("returncode", 0) != 0 for e in events
            ),
            "initial_inputs_unchanged": True,
            "token_counts": None,
            "actual_complete_cost_usd": None,
            "accepted_output_cost_usd": None,
            "customer_effort_minutes": None,
            "residual_human_attention_minutes": None,
            "submission_sha256": sha(path / "frozen_submission/qualification/submission.py"),
            "state_sha256": sha(path / "state.json"),
            "events_sha256": sha(path / "events.jsonl"),
            "acceptance_sha256": sha(ROOT / "results" / (name + "_acceptance.json")),
            "recorded_test_methods_including_public": {"U": 11, "E": 14, "E_plus": 13}[label],
        }
    capsule = ROOT / "instrument/capability_capsule.zip"
    received = ROOT / "integration/results/received-workflow.bin"
    assert capsule.read_bytes() == received.read_bytes()
    supplied = ROOT / "results/trials/S3_E_plus/frozen_submission/qualification/capability/model_reuse.py"
    assert supplied.read_bytes() == (ROOT / "instrument/model_reuse.py").read_bytes()
    conventional = json.loads((ROOT / "conventional/acceptance.json").read_text())
    result = {
        "edition": "2.1.0",
        "study": "S3 scientific-model reuse qualification",
        "status": "observed hosted construction and frozen finite acceptance",
        "arms": arms,
        "unit_of_inference": "one four-mission campaign over two public source families, one hosted recipient per arm",
        "conventional": {k: conventional[k] for k in ("accepted", "passed", "total", "source_inputs_unchanged")},
        "operational_alpha_acceptance_percentage_points": 100
        * (arms["E"]["passed_missions"] - arms["U"]["passed_missions"])
        / 4,
        "additional_learned_alpha_acceptance_percentage_points": 100
        * (arms["E_plus"]["passed_missions"] - arms["E"]["passed_missions"])
        / 4,
        "recipient": {
            "initial_access": "fresh agent context; E+ has established E card and newly received capsule; U and E may construct ordinary alternatives",
            "actual_capsule_sha256": sha(capsule),
            "actual_received_bytes_equal": True,
            "capsule_code_unchanged": True,
            "executed_received_functions": ["inventory", "stationary", "dimension_bound", "clock_witness", "qualify"],
            "benefit": "technical use and scope-aware transfer observed; incremental accepted outcomes or complete-cost advantage not established",
            "live_authentication": False,
        },
        "actual_collections_usd": 0,
        "actual_complete_cost_usd": None,
        "actual_profit_usd": None,
        "observed_commercial_feasibility_crossings": 0,
        "observed_exclusive_technical_crossings": 0,
        "limitations": [
            "No ordinary human-user sample; same inherited hosted frontier model, API snapshot/effort/billing unobserved",
            "Observable wall/operation envelopes, not matched hidden compute or tokens",
            "All arms receive the discovered formulation; this tests execution and reuse, not superior autonomous discovery",
            "E uses the previously frozen generic contract workflow, not an empirically optimized scientific prompt",
            "Boehm tests applicability withdrawal and source/table interpretation, not a new nonlinear fit or complete identifiability analysis",
            "Public source availability prevents a contamination-proof claim",
            "Internal separate evaluators, not independent external scientific validation",
            "No confidence interval turns deterministic request variants into independent opportunities",
        ],
        "source_freezes": {
            str(p.relative_to(ROOT.parent)): sha(p)
            for p in [
                ROOT / "SELECTION.json",
                ROOT / "protocol/PROTOCOL_FREEZE.json",
                ROOT / "protocol/EXPOSURE_FREEZE.json",
                ROOT / "development/INSTRUMENT_FREEZE.json",
            ]
        },
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "summary": str(output),
                "acceptance": {k: v["passed_missions"] for k, v in arms.items()},
                "sha256": sha(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
