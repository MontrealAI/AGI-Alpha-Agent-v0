# SPDX-License-Identifier: Apache-2.0
"""Directed software QA, not sampled commercial or capability evidence.

Capture the exact current kernel before executing it. The funded fixture forces
one affordable capital allocation but leaves all cash, resource, assessment,
admission, transfer, and reuse gates active. The recovery fixture changes one
recovery duration to exceed the monthly capacity and verifies unresolved work.
Neither fixture changes the primary protocol or writes simulator source.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "sim"
sys.path.insert(0, str(SIM))
source = (SIM / "economy_v3.py").read_bytes()
kernel = types.ModuleType("economy_directed_qa")
kernel.__file__ = str(SIM / "economy_v3.py")
sys.modules[kernel.__name__] = kernel
exec(compile(source, kernel.__file__, "exec"), kernel.__dict__)
configuration, costs = kernel.load_inputs(SIM / "config_v3.json")
original_retention = kernel.choose_retention


def deterministic_inputs(c, sc, seed, world):
    """Known synthetic inputs, with no claim to estimate their probabilities."""
    n_agents, domains = c["scope"]["recipient_agents"], c["scope"]["domains"]
    equiv = {n: kernel.np.zeros((n_agents, domains), dtype=bool) for n in ("R", "V")}
    partial = copy.deepcopy(equiv)
    months = []
    for month in range(1, c["months"] + 1):
        u = kernel.np.full((3, 40), 0.0)
        u[:, 4] = 0.99  # No intake abstention in this directed fixture.
        u[:, 5] = 0.99  # No common fault except the explicit recovery case.
        u[:, 27] = 0.99  # A jointly metered R+V candidate.
        recipient = (month - 1) % n_agents
        weights = kernel.recipient_weights(c, 0)
        u[:, 3] = sum(weights[:recipient]) + weights[recipient] / 2
        if c["qa_directed_fixture"]["case"] == "unresolved_recovery" and month == 1:
            u[0, 6] = 1.0  # One wrong semantic result passes the explicit weak test.
        values = kernel.np.full(3, 1.8)
        taste = kernel.np.zeros((3, 4))
        taste[:, 0] = 10.0  # All three synthetic customers choose the service.
        months.append((u, values, taste, False))
    return equiv, partial, months, 1.0


def force_one_affordable_retention(c, sc, table, register, belief, assets, campaign,
                                 pending, month, cash, reserve, policy, minutes, tokens):
    if (c["qa_directed_fixture"]["case"] != "funded_retention"
            or policy not in ("optimized_network", "fixed_network")
            or campaign or month < 2 or c.get("_qa_purchase_selected")):
        return None
    candidate = next((x for x in pending if not x.get("decided")), None)
    if candidate is None:
        return None
    action = candidate["action"]
    budget = register["incremental_retention_options"][action]
    bill = budget["derived_budget_usd"] * sc["activity_quantity_multiplier"]
    if cash - reserve - c["policy"]["minimum_research_cash_headroom"] < bill:
        return None
    c["_qa_purchase_selected"] = True
    price = kernel.price_plan(c, sc, table, belief, assets, month, policy)["fraction"]
    return {
        "action": action, "components": candidate["components"], "bill": bill,
        "expected_incremental_terminal_cash": 0.0,
        "estimated_build_months": 1, "forecast_horizon": c["months"] - month,
        "opportunity_cost_forecast": 0.0, "cash_after_purchase": cash - bill,
        "reserve": reserve, "price_before": price, "price_after": price,
        "deterministic_reserve_test_passed": True, "retention_candidate": candidate,
        "qa_forced_capital_action": True,
        "qa_scope": "Exercise funded accounting; no positive optimizer forecast is asserted.",
    }


kernel.initial_primitives = deterministic_inputs
kernel.choose_retention = force_one_affordable_retention
receipts = []
for case in ("funded_retention", "unresolved_recovery"):
    c, register = copy.deepcopy(configuration), copy.deepcopy(costs)
    c["study_id"] += ":DIRECTED-QA:" + case
    c["status"] = "DIRECTED SOFTWARE QA ONLY; NOT ECONOMIC OR CAPABILITY EVIDENCE"
    c["qa_directed_fixture"] = {
        "case": case, "basis": "AUTHOR_SPECIFIED_SYNTHETIC_BRANCH_TEST",
        "all_buyers_and_task_outcomes_directed": True,
        "force_one_affordable_retention": case == "funded_retention",
        "not_a_primary_or_favorable_economic_scenario": True,
    }
    c["months"] = 12 if case == "funded_retention" else 4
    c["scope"]["domain_weights"] = [1, 0, 0, 0, 0]
    c["scope"]["existing_equivalent_R"] = 0
    c["scope"]["existing_equivalent_V"] = 0
    c["scope"]["partial_equivalent_probability"] = 0
    c["paid_job_learning"].update(
        optional_research_enabled=False, enabled=case == "funded_retention",
        scan_probability=1, candidate_probability_given_scan=1,
        rights_available_probability=1, retention_generalization_success=1,
    )
    c["network"]["beta_epochs"] = [copy.deepcopy(c["network"]["beta_epochs"][0])]
    c["network"]["beta_epochs"][0]["public_equivalent_probability_per_month"] = 0
    sc = copy.deepcopy(c["scenarios"]["central"])
    sc.update(semantic_correctness=1.0, reconstruction_correctness=0.5,
              retained_component_correctness=1.0, validator_specificity=1.0,
              semantic_validator_sensitivity=1.0, mechanical_validator_sensitivity=1.0,
              shared_fault_probability=0.0, correction_success=0.25,
              collection_probability=1.0, collection_lag=1,
              transfer_success=1.0, activity_quantity_multiplier=1.0)
    if case == "unresolved_recovery":
        sc["semantic_validator_sensitivity"] = 0.0
        register["recovery"]["resource_minutes"] = 2 * c["operations"]["monthly_workbench_minutes"]
    c["scenarios"] = {"central": sc}
    out = ROOT / "results" / ("qa_paid_job_funded" if case == "funded_retention" else "qa_unresolved_recovery")
    if out.exists():
        raise SystemExit(f"Preserve prior fixture directory; choose a fresh output path: {out}")
    out.mkdir(parents=True)
    (out / "DEVELOPMENT_ONLY.md").write_text(
        "# Directed software QA only\n\nKnown synthetic inputs and a specifically directed branch. "
        "No result here is demand calibration, autonomous allocation evidence, or a commercial success case.\n")
    (out / "frozen_config.json").write_text(json.dumps(c, indent=2) + "\n")
    (out / "frozen_workflow_costs.json").write_text(json.dumps(register, indent=2) + "\n")
    (out / "kernel_snapshot.py").write_bytes(source)
    summary = kernel.run_scenario(c, register, "central", 1, 195101, out)
    entry = {
        "case": case, "basis": "DIRECTED_SOFTWARE_QA_ONLY", "output": str(out.relative_to(ROOT)),
        "kernel_sha256": hashlib.sha256(source).hexdigest(),
        "fixture_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "graph_sha256": hashlib.sha256((SIM / "graph_lifecycle_v3.py").read_bytes()).hexdigest(),
        "worlds": 1, "policies": list(kernel.POLICIES),
        "summary": summary,
    }
    (out / "fixture_manifest.json").write_text(json.dumps(entry, indent=2) + "\n")
    receipts.append({k: v for k, v in entry.items() if k != "summary"})
    print(json.dumps({"case": case, "policies": {p: {
        "retention_attempts": summary["policies"][p].get("retention_attempts"),
        "retention_admissions": summary["policies"][p].get("retention_admissions"),
        "retention_uses": summary["policies"][p].get("retention_uses"),
    } for p in kernel.POLICIES}}), flush=True)
(ROOT / "qa" / "paid_job_directed_fixture_manifest.json").write_text(json.dumps(receipts, indent=2) + "\n")
