# SPDX-License-Identifier: Apache-2.0
"""Descriptive analysis and deterministic replay after both protected confirmations."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
TECHNICAL = HERE.parent
sys.path.insert(0, str(TECHNICAL))
from learning import features, fit_portfolio
from run_study import source_hashes, write_json


def paired(rows: list[dict[str, Any]], budget: int, regime: str, comparator: str) -> dict[str, Any]:
    subset = [r for r in rows if r["budget"] == budget and (regime == "all" or r["regime"] == regime)]
    ids = sorted({r["task_id"] for r in subset})
    differences = []
    successes_skill = successes_beta = 0
    for task in ids:
        group = [r for r in subset if r["task_id"] == task]
        skill = next(r for r in group if r["method"] == "v2")["accepted"]
        ordinary = any(r["accepted"] for r in group if r["method"].startswith("beta_")) if comparator == "hindsight_best" else next(r for r in group if r["method"] == comparator)["accepted"]
        differences.append(int(skill) - int(ordinary))
        successes_skill += int(skill)
        successes_beta += int(ordinary)
    draws = np.mean(np.random.default_rng(771_007 + budget).choice(differences, size=(10000, len(ids))), axis=1)
    wins = differences.count(1)
    losses = differences.count(-1)
    return {"budget": budget, "regime": regime, "comparator": comparator, "n": len(ids),
            "skill_successes": successes_skill, "beta_successes": successes_beta,
            "wins": wins, "losses": losses, "acceptance_delta": float(np.mean(differences)),
            "conditional_bootstrap_95pct": np.quantile(draws, [0.025, 0.975]).tolist(),
            "paired_sign_test_two_sided": float(binomtest(wins, wins + losses).pvalue) if wins + losses else 1.0,
            "inference_limit": "Conditional synthetic task sampling; no assumption validation, physical generalization or correction for all exploratory comparisons"}


def main() -> None:
    ledger_path = TECHNICAL / "results/learning_ledger.json"
    ledger = json.loads(ledger_path.read_text())
    for event in ledger["events"]:
        event["research_diagnostic_calls"] = 32
    ledger["research_diagnostic_calls"] = 32 * len(ledger["events"])
    ledger["accounting_clarification"] = "Diagnostic benchmark uses16faulty plus16original labels, outside896prediction/menuaudit; corrected postprocessing preserves frozen numerical source and outcomes."
    write_json(ledger_path, ledger)
    robust = TECHNICAL / "robust"
    rows = json.loads((robust / "results/confirmation_rows.json").read_text())
    development = json.loads((robust / "results/development_rows.json").read_text())
    beta_names = ["beta_space", "beta_dopt", "beta_adaptive", "beta_direct"]
    choices = {}
    for budget in [24, 40, 64, 96]:
        scores = []
        for name in beta_names:
            group = [r for r in development if r["method"] == name and r["budget"] == budget]
            scores.append((-sum(r["accepted"] for r in group), sum(r["oracle_calls"] for r in group), name))
        choices[budget] = min(scores)[2]
    comparisons = []
    for budget in [24, 40, 64, 96]:
        for regime in ["all", "compatible", "partial_shift", "novel_family"]:
            for comparator in sorted({choices[budget], "beta_direct", "hindsight_best"}):
                comparisons.append(paired(rows, budget, regime, comparator))
    crossings = []
    losses = []
    for budget in [24, 40, 64, 96]:
        for task in sorted({r["task_id"] for r in rows}):
            group = [r for r in rows if r["task_id"] == task and r["budget"] == budget]
            specialist = next(r for r in group if r["method"] == "v2")
            betas = [r for r in group if r["method"].startswith("beta_")]
            if specialist["accepted"] and not any(r["accepted"] for r in betas):
                crossings.append({"task_id": task, "budget": budget, "regime": specialist["regime"],
                                  "specialist": specialist, "all_ordinary_methods": betas})
            if any(r["accepted"] for r in betas) and not specialist["accepted"]:
                losses.append({"task_id": task, "budget": budget, "regime": specialist["regime"],
                               "specialist": specialist, "all_ordinary_methods": betas})
    write_json(robust / "results/paired_analysis.json", {
        "development_only_baseline_choices": choices,
        "selection_rule": "Highest development acceptance, ties lower observed query total, then lexical method name",
        "selection_timing_limit": "This descriptive rule was recorded after confirmation; it uses development outcomes only and is not presented as an additional prospectively frozen enterprise policy",
        "comparisons": comparisons, "crossing_cases": crossings, "reverse_crossings": losses,
        "all_failed_cases_preserved_in_raw_rows": True,
        "regime_qualification_limit": "Family compatibility is hidden from deployed policies; stratified comparisons do not authorize oracle selection"})

    spec = importlib.util.spec_from_file_location("robust_replay", robust / "run_robust.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    artifacts = {name: json.loads((TECHNICAL / "artifacts" / file).read_text()) for name, file in [
        ("v1", "v1.json"), ("v2", "v2.json"), ("wrong_prior", "wrong-prior.json")]}
    witness = next(x for x in crossings if x["budget"] == 40 and x["regime"] == "compatible")
    original = witness["specialist"]
    replay, deliverable = module.run(original["seed"], original["regime"], 40, "v2", artifacts)
    matched = []
    for key, value in original.items():
        if key in ["observed_seconds", "split"]:
            continue
        other = replay[key]
        if isinstance(value, float):
            assert np.isclose(value, other, rtol=1e-8, atol=1e-10), key
        else:
            assert value == other, key
        matched.append(key)
    deliverable["selection"] = "First compatible 40-call crossing in sorted confirmation task order; post-hoc illustration, not extra independent evidence"
    deliverable["replayed_calls_research_overhead"] = replay["oracle_calls"]
    deliverable["lineage"] = {"origin": "artifacts/origin-deliverable.json", "v1": "artifacts/v1.json", "v2": "artifacts/v2.json",
                               "fresh_recipient": "robust-operation recipient, identity simulated", "new_offering": "One control setting verified in16finiteenvironmentcontexts"}
    write_json(robust / "results/crossing_deliverable.json", deliverable)

    origin = json.loads((TECHNICAL / "artifacts/origin-deliverable.json").read_text())
    inputs = np.asarray(origin["training_observations"]["inputs"])
    targets = np.asarray(origin["training_observations"]["outputs"])
    origin_replay, _ = fit_portfolio(features(inputs[:104]), targets[:104], features(inputs[104:]), targets[104:])
    max_error = float(np.max(np.abs(origin_replay - np.asarray(origin["coefficients"]))))
    assert max_error < 1e-8
    frozen = json.loads((TECHNICAL / "results/FREEZE.json").read_text())
    artifact_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (TECHNICAL / "artifacts").glob("*.json")}
    assert frozen["source_hashes"] == source_hashes()
    assert frozen["artifact_hashes"] == artifact_hashes
    supplement_frozen = json.loads((robust / "results/FREEZE.json").read_text())
    assert supplement_frozen["hashes"] == module.hashes()
    write_json(HERE / "REPRODUCTION_CHECK.json", {"origin_max_coefficient_difference": max_error,
               "fresh_replayed_task": original["task_id"], "fresh_method": "v2", "fresh_budget": 40,
               "matched_fields": matched, "primary_source_and_artifact_freeze_matches": True,
               "supplement_source_and_artifact_freeze_matches": True,
               "runtime_timing_excluded": True, "independence": "Deterministic replay by technical author; root audit is separate"})

    config = json.loads((TECHNICAL.parent / "economics/scenario.json").read_text())
    token_cost = sum((v["input_tokens"] * v["input_usd_per_million"] + v["output_tokens"] * v["output_usd_per_million"]) / 1e6 for v in config["model_token_bundle_assumed"].values())
    delivery_overhead = token_cost + config["job_tool_and_packaging_cost_assumed"] + config["job_service_overhead_cost_assumed"]
    private_fixed_b = config["retention_cost_per_version_assumed"] + config["admission_administration_cost_assumed"] + 30 * config["maintenance_per_version_per_day_assumed"]
    shared_fixed_b = private_fixed_b + config["sharing_setup_cost_assumed"] + 2 * config["sharing_cost_per_peer_assumed"]
    sensitivity = []
    for cost_per_call in [0.10, 0.50, 2.0]:
        for price in [100.0, 300.0, 600.0]:
            for reuse in [20, 100, 500]:
                for regime in ["all", "compatible"]:
                    for name in sorted({choices[40], "beta_direct", "v2"}):
                        sample = [r for r in rows if r["method"] == name and r["budget"] == 40 and (regime == "all" or r["regime"] == regime)]
                        success = float(np.mean([r["accepted"] for r in sample]))
                        queries = float(np.mean([r["oracle_calls"] for r in sample]))
                        specialist = name == "v2"
                        A = queries * cost_per_call + delivery_overhead + success * price * config["payment_fee_fraction"] + (config["specialist_invocation_cost_assumed"] if specialist else 0)
                        B = shared_fixed_b / reuse if specialist else 0
                        C = 1280 * cost_per_call / reuse if specialist else 0
                        collection = success * price
                        sensitivity.append({"regime": regime, "method": name, "query_cap": 40, "call_price_assumed_usd": cost_per_call,
                                            "offering_price_hypothesis_usd": price, "reuse_hypothesis": reuse,
                                            "observed_success_fraction": success, "observed_mean_calls": queries,
                                            "simulated_mean_collections": collection, "complete_delivery_A": A,
                                            "allocated_admission_retention_sharing_upkeep_B": B, "allocated_gym_C": C,
                                            "conditional_mean_net_before_common_offering_RnD": collection - A - B - C})
    development_queries = sum(r["oracle_calls"] for r in development)
    confirmation_queries = sum(r["oracle_calls"] for r in rows)
    audit_queries = (12 + 48) * 8576
    full_research_queries = development_queries + confirmation_queries + audit_queries + replay["oracle_calls"]
    write_json(robust / "results/economic_sensitivity.json", {
        "status": "HYPOTHETICAL_PRICE_AND_COST_SENSITIVITY_NOT_CUSTOMER_SALES",
        "configuration_source": "economics/scenario.json assumed overheads and paymentfee; original enterprise policy unchanged",
        "assumed_delivery_overhead_usd": delivery_overhead,
        "assumed_shared_fixed_B_usd": shared_fixed_b,
        "rows": sensitivity,
        "mandatory_cost_boundary": "Rows include all observed delivery/failure/verification calls plus assumed token/tools/packaging/overhead/fee/invocation, and amortized actualGym1280calls and statedB. Common opportunity-development/assessmentR&D is separately fully reported below and must be added for whole-studyprofit; these rows are not whole-studyreturn.",
        "study_RnD": {"development_actual_oracle_queries": development_queries, "confirmation_actual_oracle_queries": confirmation_queries,
                      "unique_research_audit_queries": audit_queries, "illustrative_replay_queries": replay["oracle_calls"],
                      "total_query_units": full_research_queries,
                      "cost_sensitivity": [{"assumed_usd_per_query": c, "total_study_cost_usd": c * full_research_queries} for c in [0.1, 0.5, 2.0]],
                      "observed_paid_cash_expense_usd": 0},
        "critical_limits": ["No demand, willingness-to-pay, sales, collection or physically calibrated querytime/cost measured",
                            "No original primaryenterprise policy was reoptimized",
                            "Compatibility is hidden from operationalpolicies; compatible-stratum scenario is not an oracle-admission strategy",
                            "StudyR&D can overwhelm operating contribution and must not be erased",
                            "Finitecontext success does not establish continuousenvironment robustness or specialistASI"]})
    print(json.dumps({"witness": original["task_id"], "robust_crossings": len(crossings), "reverse_crossings": len(losses),
                      "origin_replay_error": max_error, "freeze_checks": "passed", "full_supplement_research_query_units": full_research_queries}))


if __name__ == "__main__":
    main()
