# SPDX-License-Identifier: Apache-2.0
"""Independent role review probes over frozen evidence, without changing study source."""

from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STUDY = Path(__file__).resolve().parent.parent


def read(relative: str) -> Any:
    """Read a named study evidence file."""
    return json.loads((STUDY / relative).read_text())


def digest(relative: str) -> str:
    """Bind each probe to its exact source bytes."""
    return hashlib.sha256((STUDY / relative).read_bytes()).hexdigest()


def run() -> dict[str, Any]:
    """Check complete numerical rows, accounting, and prospective decision boundaries."""
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, evidence: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})

    freeze = read("technical/results/FREEZE.json")
    source_matches = {path: digest(path) == h for path, h in freeze["source_hashes"].items()}
    artifact_matches = {
        path: digest("technical/artifacts/" + path) == h for path, h in freeze["artifact_hashes"].items()
    }
    check("primary_source_freeze", all(source_matches.values()), source_matches)
    check("primary_artifact_freeze", all(artifact_matches.values()), artifact_matches)
    dev = read("technical/results/development_rows.json")
    confirmation = read("technical/results/confirmation_rows.json")
    robust_dev = read("technical/robust/results/development_rows.json")
    robust = read("technical/robust/results/confirmation_rows.json")
    seeds = {
        "learning": {210_000 + i * 101 for i in range(11)},
        "development": {r["seed"] for r in dev},
        "confirmation": {r["seed"] for r in confirmation},
        "robust_development": {r["seed"] for r in robust_dev},
        "robust_confirmation": {r["seed"] for r in robust},
    }
    intersections = {a + ":" + b: sorted(x & seeds[b]) for a, x in seeds.items() for b in seeds if a < b}
    check("disjoint_task_seeds", not any(intersections.values()), intersections)
    for name, rows, expected in [("primary", confirmation, 1728), ("robust", robust, 1728)]:
        keys = {(r["task_id"], r["method"], r["budget"]) for r in rows}
        check(
            name + "_complete_confirmation",
            len(keys) == len(rows) == expected,
            {"rows": len(rows), "unique_keys": len(keys), "expected": expected},
        )
        violations = [r["task_id"] + ":" + r["method"] for r in rows if r["oracle_calls"] > r["budget"]]
        check(name + "_all_observation_budgets", not violations, {"violations": violations})
        index = {(r["task_id"], r["method"], r["budget"]): r for r in rows}
        excluded = {"method", "artifact_version", "observed_seconds"}
        mismatches = []
        for row in rows:
            if row["method"] != "v2":
                continue
            ordinary = index[(row["task_id"], "library_v2", row["budget"])]
            if {k: v for k, v in row.items() if k not in excluded} != {
                k: v for k, v in ordinary.items() if k not in excluded
            }:
                mismatches.append([row["task_id"], row["budget"]])
        check(
            name + "_same_content_library_parity",
            not mismatches,
            {"paired_task_budgets": len(rows) // 9, "mismatches": mismatches},
        )
    primary_violations = []
    for row in confirmation:
        actual = row["operational_verified_response"]
        accepted = actual is not None and actual >= 2.0 and row["chosen_plan_cost"] <= 1.2
        bounded = row["chosen_plan_inputs"] is None or all(-1 <= x <= 1 for x in row["chosen_plan_inputs"])
        consistent = bool(accepted) == row["accepted"] == row["operational_acceptance_from_actual_query"]
        counted = (
            row["oracle_calls"]
            == row["training_calls"] + row["visible_validation_calls"] + row["final_verification_calls"]
            if row["method"] != "beta_direct"
            else row["oracle_calls"] == row["final_verification_calls"]
        )
        if not (consistent and bounded and counted):
            primary_violations.append([row["task_id"], row["method"], row["budget"]])
    check(
        "primary_actual_verification_acceptance_and_cost_inclusion",
        not primary_violations,
        {"rows_checked": len(confirmation), "violations": primary_violations},
    )
    robust_violations = []
    for row in robust:
        accepted = (
            row["actual_verified_contexts"] == 16
            and row["verified_mean"] >= 0.4
            and row["verified_nonnegative_count"] >= 12
            and row["chosen_plan_cost"] <= 1.2
        )
        if accepted != row["accepted"]:
            robust_violations.append([row["task_id"], row["method"], row["budget"]])
    check(
        "robust_actual_sixteen_context_acceptance",
        not robust_violations,
        {"rows_checked": len(robust), "violations": robust_violations},
    )
    predeclared = read("technical/robust/results/PREDECLARED.json")
    robust_freeze = read("technical/robust/results/FREEZE.json")
    robust_source_matches = {p: digest("technical/" + p) == h for p, h in robust_freeze["hashes"].items()}
    check(
        "robust_predeclared_source_unchanged_through_confirmation",
        predeclared["hashes"] == robust_freeze["hashes"] and all(robust_source_matches.values()),
        robust_source_matches,
    )
    learning = read("technical/results/learning_ledger.json")
    fitted_supports = [set(event["learned_nonzero_terms"]) for event in learning["events"]]
    v1, v2 = read("technical/artifacts/v1.json"), read("technical/artifacts/v2.json")
    expected_union = sorted(set().union(*fitted_supports))
    expected_counts = [sum(i in support for support in fitted_supports) for i in range(len(v2["frequency"]))]
    check(
        "artifacts_are_updates_of_empirically_fitted_models",
        sorted(fitted_supports[0]) == v1["support"]
        and expected_union == v2["support"]
        and expected_counts == v2["frequency"],
        {"learning_jobs": len(fitted_supports), "v1_terms": len(v1["support"]), "v2_terms": len(v2["support"])},
    )

    source = STUDY / "economics/run_economics.py"
    spec = importlib.util.spec_from_file_location("review_economics", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load economics source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = read("economics/scenario.json")
    offerings_list = read("economics/offerings.json")["offerings"]
    offerings = {o["id"]: o for o in offerings_list}
    altered = copy.deepcopy(dev)
    for row in altered:
        if row["method"] == "v2":
            for key in ["accepted", "design_accepted", "prediction_accepted", "diagnosis_accepted"]:
                row[key] = not row[key]
            row["oracle_calls"] += 1000
    decisions = []
    for name in ["private", "shared", "shared_no_gym"]:
        before = module.build_policy(name, dev, offerings_list, config, learning)
        after = module.build_policy(name, altered, offerings_list, config, learning)
        a = next(item for item in before["decisions"] if item["candidate"] == "gym")
        b = next(item for item in after["decisions"] if item["candidate"] == "gym")
        decisions.append({"policy": name, "before": a, "after": b, "equal": a == b})
    check("gym_decisions_do_not_read_v2_outcomes", all(d["equal"] for d in decisions), decisions)
    hidden_labels = copy.deepcopy(dev)
    for row in hidden_labels:
        row["regime"] = "unavailable-diagnostic-label"
    regular = module.build_policy("shared", dev, offerings_list, config, learning)
    unlabeled = module.build_policy("shared", hidden_labels, offerings_list, config, learning)
    check(
        "enterprise_selection_does_not_read_regime_labels", regular == unlabeled, {"equal_policy": regular == unlabeled}
    )

    route = {
        "method": "beta_direct",
        "budget": 96,
        "price": 100.0,
        "quality_forecast": 1.0,
        "expected_profit_per_arrival": 80.0,
    }
    policy = {
        "name": "accounting-review-fixture",
        "setup_calls": 0,
        "origin_calls_A": 0,
        "fixed_B": 3.0,
        "fixed_C": 4.0,
        "retained_versions": [],
        "base_methods": ["beta_direct"],
        "routes": {
            name: {"origin": copy.deepcopy(route) if name == "verified_design" else None, "peer": None}
            for name in offerings
        },
    }
    observations = []
    for truth in [True, False]:
        for delay in [1, 40]:
            values = copy.deepcopy(config)
            values.update(horizon_days=30, agents=1, warranty_reserve_fraction=0.05, collection_delay_days=delay)
            events = [
                {
                    "event_id": 0,
                    "day": 1,
                    "task_id": "accounting-task",
                    "offering": "verified_design",
                    "agent": 0,
                    "buyer_u": 0.9,
                    "transfer_u": 0.9,
                    "validator_bad": True,
                }
            ]
            index = {
                ("accounting-task", "beta_direct", 96): {
                    "method": "beta_direct",
                    "oracle_calls": 2,
                    "design_accepted": truth,
                    "observed_seconds": 0.0,
                }
            }
            report, _ = module.simulate(
                policy, events, index, offerings, values, {"events": [{"category": "A", "accepted": False}]}, True
            )
            expected_A = 9 + 9.2 + 3.0
            observations.append(
                {
                    "truth": truth,
                    "collection_delay": delay,
                    "report": report,
                    "passed": abs(report["cost_A"] - expected_A) < 1e-8
                    and report["cost_B"] == 3
                    and report["cost_C"] == 4
                    and abs(report["cash_identity_residual"]) < 1e-8
                    and abs(report["profit"] - ((100 if truth else 0) - expected_A - 7)) < 1e-8
                    and abs(
                        report["available_funds"] - max(0, report["cash"] - report["obligations"] - report["reserves"])
                    )
                    < 1e-8,
                }
            )
    check("complete_cost_cash_fees_refunds_delay_identities", all(r["passed"] for r in observations), observations)
    with (STUDY / "economics/results/enterprise_runs.csv").open(newline="") as stream:
        enterprise = list(csv.DictReader(stream))
    accounting_violations = []
    for row in enterprise:

        def number(key: str) -> float:
            return float(row[key])

        complete = number("cost_A") + number("cost_B") + number("cost_C")
        cash = (
            number("seed_capital")
            + number("simulated_collections")
            - number("refunds_paid")
            - complete
            + number("payment_fee_payables")
        )
        available = max(0, number("cash") - number("obligations") - number("reserves"))
        valid = (
            abs(complete - number("complete_cost")) < 1e-7
            and abs(number("simulated_revenue") - complete - number("profit")) < 1e-7
            and abs(cash - number("cash")) < 1e-7
            and abs(available - number("available_funds")) < 1e-7
            and number("query_calls") <= number("query_capacity") + 1e-7
        )
        if not valid:
            accounting_violations.append([row["scenario"], row["seed"], row["policy"]])
    check(
        "every_enterprise_complete_cost_cash_capacity_identity",
        not accounting_violations,
        {"runs_checked": len(enterprise), "violations": accounting_violations},
    )
    enterprise_index = {(r["scenario"], r["seed"], r["policy"]): r for r in enterprise}
    library_violations = []
    for row in enterprise:
        if row["policy"] == "shared":
            comparison = enterprise_index[(row["scenario"], row["seed"], "shared_library")]
            if abs(float(row["profit"]) - float(comparison["profit"])) > 1e-8:
                library_violations.append([row["scenario"], row["seed"]])
    check(
        "enterprise_same_content_library_profit_parity",
        not library_violations,
        {"paired_runs": len(enterprise) // 6, "violations": library_violations},
    )
    amendment = read("economics/RESERVATION_CORRECTION.json")
    check(
        "economics_correction_retains_original_freeze_and_source",
        amendment["corrected_source_sha256"] == digest("economics/run_economics.py")
        and amendment["original_source_sha256"]
        == digest("economics/history/pre_reservation_correction_run_economics.py")
        and amendment["original_policy_sha256"]
        == digest("economics/history/pre_reservation_correction_policy_freeze.json")
        and amendment["original_policy_sha256"] == digest("economics/policy_freeze.json"),
        amendment,
    )
    gate = read("integration/results/development-admission-v1/summary.json")
    check(
        "empirical_candidates_remain_denied",
        all(r["verdict"] == "reject" and r["admission"] is None for r in gate["candidate_verdicts"])
        and not any(gate["retrieval_allowed"]),
        gate["candidate_verdicts"],
    )
    return {
        "schema": "capability-opportunity-independent-role-probes/v1",
        "status": "INDEPENDENT_REVIEW_ROLE_WITHIN_SAME_RESEARCH_TEAM",
        "organizationally_independent": False,
        "checks": checks,
        "passed": sum(row["passed"] for row in checks),
        "total": len(checks),
        "source_sha256": {
            p: digest(p)
            for p in [
                "technical/run_study.py",
                "technical/benchmark.py",
                "technical/learning.py",
                "technical/robust/run_robust.py",
                "economics/run_economics.py",
            ]
        },
        "recorded_failures_preserved": ["validation/reservations_before_correction.json"],
        "corrected_reservations": read("validation/reservations_after_correction.json"),
        "limits": "Synthetic executable tests and source review only. Market assumptions, frontier ability, physical validity, current identities and organizational independence are not validated.",
    }


if __name__ == "__main__":
    result = run()
    out = STUDY / "validation/independent_review.json"
    if out.exists():
        raise FileExistsError("Preserve the previous independent review")
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "total": result["total"],
                "failures": [r["name"] for r in result["checks"] if not r["passed"]],
            }
        )
    )
