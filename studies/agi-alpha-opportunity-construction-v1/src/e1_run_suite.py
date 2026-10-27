# SPDX-License-Identifier: Apache-2.0
"""Freeze E1 technical policy, then retain all predeclared fresh synthetic cases."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from e1_instrument import compare, digest
from e1_verify import verify_offer

Json = dict[str, Any]
BASE = Path(__file__).resolve().parent.parent


def read(path: Path) -> Json:
    """Read a JSON object."""
    return cast(Json, json.loads(path.read_text()))


def save(path: Path, value: Any) -> None:
    """Save reviewable stable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def now() -> str:
    """Return UTC time with an explicit timezone."""
    return datetime.now(timezone.utc).isoformat()


def file_hash(path: Path) -> str:
    """Hash exact file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze() -> None:
    """Freeze implementation, schema, origin inputs and fresh-case policy before generation."""
    path = BASE / "technical/FROZEN_TECHNICAL_POLICY.json"
    if path.exists():
        raise RuntimeError("Freeze already exists; do not silently replace the frozen implementation")
    policy = read(BASE / "technical/fresh_case_policy.json")
    origin = read(BASE / "technical/origin_result.json")
    if not origin["results"]["combined"]["acceptance_check"]["valid"]:
        raise RuntimeError("Origin must have a valid inspectable result before freezing")
    record = {
        "schema": "agi-alpha.e1-freeze.v1",
        "frozen_utc": now(),
        "hash_algorithm": "sha256",
        "files": {name: file_hash(BASE / name) for name in policy["freeze_files"]},
        "origin_result_sha256": file_hash(BASE / "technical/origin_result.json"),
        "origin_checker_passed": True,
        "fresh_cases_generated_or_executed_before_freeze": False,
        "scope": "Complete finite synthetic commitment package, not childcare delivery or a novel solver.",
    }
    save(path, record)
    print(json.dumps(record))


def verify_frozen() -> Json:
    """Reject execution if any frozen source/config file has changed."""
    record = read(BASE / "technical/FROZEN_TECHNICAL_POLICY.json")
    for name, expected in record["files"].items():
        if file_hash(BASE / name) != expected:
            raise RuntimeError(f"Frozen technical file changed: {name}")
    return record


def change_fixed_cost(offer: Json, amount: int) -> None:
    """Change an explicitly synthetic complete offer without retaining inconsistent component costs."""
    offer["fixed_opening_cost_cents"] = amount
    offer["cost_breakdown"] = {"synthetic_complete_opening_quote": amount}


def targeted(origin: Json, label: str) -> Json:
    """Construct a predeclared mechanism or failure test without observing solver outcomes."""
    case = copy.deepcopy(origin)
    case["case_id"] = f"targeted_{label}"
    if label == "locked_choices":
        for worker in case["workers"]:
            worker["permitted_shift_ids"] = [worker["current_shift_id"]]
    elif label == "insufficient_qualified_staff":
        for staff in case["staff"]:
            staff["qualification_tags"] = []
    elif label == "insufficient_care_capacity":
        for offer in case["offers"]:
            offer["declared_child_capacity"] = 1
    elif label == "no_acceptable_location":
        case["children"][0]["acceptable_location_ids"] = []
    elif label == "long_backup_commute":
        for child in case["children"]:
            child["commute_minutes_by_location"]["site_B"] = {"before": 90, "after": 90}
    elif label in ("primary_provider_withdrawn", "backup_provider_withdrawn"):
        provider = "provider_A" if label.startswith("primary") else "provider_B"
        next(p for p in case["providers"] if p["id"] == provider)["declared_offer_acceptance"] = False
    elif label == "correlated_provider_absence":
        case["scenarios"].append(
            {
                "id": "both_absent",
                "announced_minute": 300,
                "failed_provider_ids": ["provider_A", "provider_B"],
                "failed_staff_ids": [],
                "closed_location_ids": [],
            }
        )
    elif label == "late_contingency_notice":
        for scenario in case["scenarios"]:
            if scenario["id"] != "normal":
                scenario["announced_minute"] = 600
    elif label == "underfunded":
        for payer in case["payers"]:
            payer["payment_ceiling_cents"] = 1000 if payer["kind"] == "parent" else 5000
    elif label == "no_worker_compensation_payer":
        for payer in case["payers"]:
            payer["allowed_cost_categories"] = [
                x for x in payer["allowed_cost_categories"] if x != "worker_compensation"
            ]
    elif label == "existing_capacity":
        for offer in case["offers"]:
            offer["commitment_required"] = False
    elif label == "low_opening_cost":
        for offer in case["offers"]:
            change_fixed_cost(offer, 2000)
    elif label == "high_change_compensation":
        for worker in case["workers"]:
            for shift_id in worker["permitted_shift_ids"]:
                if shift_id != worker["current_shift_id"]:
                    worker["change_compensation_cents"][shift_id] = 10000
    elif label == "three_employers_six_children":
        original_workers = [w for w in case["workers"] if w["employer_id"] == "E_A"]
        for collection in ("workers", "children", "payers"):
            selected = (
                [x for x in case[collection] if x["employer_id"] == "E_A"]
                if collection == "workers"
                else [x for x in case[collection] if "E_A" in x["id"]]
            )
            for value in selected:
                clone = json.loads(json.dumps(value).replace("E_A", "E_C"))
                case[collection].append(clone)
        case["employers"].append({"id": "E_C", "staffing_quotas": {"early": 2, "late": 2}})
        for location in case["locations"]:
            location["declared_concurrent_child_capacity"] = 6
        for offer in case["offers"]:
            offer["declared_child_capacity"] = 6
            offer["minimum_qualified_staff"] = 2
            assistant = copy.deepcopy(next(s for s in case["staff"] if s["id"] == offer["staff_ids"][0]))
            assistant["id"] += "_second"
            case["staff"].append(assistant)
            offer["staff_ids"].append(assistant["id"])
            change_fixed_cost(offer, 25000)
            if offer["role"] == "backup":
                offer["standby_retainer_cents"] = 4000
        del original_workers
    elif label == "same_caregiver_overlapping_blocks":
        for provider in ("A", "B"):
            early = next(o for o in case["offers"] if o["id"] == f"{provider}_early")
            late = next(o for o in case["offers"] if o["id"] == f"{provider}_late")
            late["staff_ids"] = list(early["staff_ids"])
            person = next(s for s in case["staff"] if s["id"] == early["staff_ids"][0])
            person["available_windows"] = [[330, 870]]
            person["max_active_minutes"] = 600
            person["max_reserved_minutes"] = 600
    elif label in ("exact_payment_boundary", "one_cent_below_boundary"):
        next(p for p in case["payers"] if p["id"] == "payer_E_A")["payment_ceiling_cents"] = (
            10000 if label == "exact_payment_boundary" else 9999
        )
    else:
        raise ValueError(label)
    case["case_generation"] = {
        "kind": "predeclared_targeted",
        "label": label,
        "solver_outcome_not_used_to_generate": True,
    }
    return case


def randomized(origin: Json, seed: int, rules: Json) -> Json:
    """Draw all declared variations once and preserve failures."""
    rng = random.Random(seed)
    case = copy.deepcopy(origin)
    case["case_id"] = f"seed_{seed}"
    for worker in case["workers"]:
        if rng.random() > rules["worker_alternative_permission_probability"]:
            worker["permitted_shift_ids"] = [worker["current_shift_id"]]
        for shift_id in worker["change_compensation_cents"]:
            if shift_id != worker["current_shift_id"]:
                worker["change_compensation_cents"][shift_id] = rng.choice(
                    rules["worker_alternative_compensation_cents"]
                )
    for child in case["children"]:
        if rng.random() < rules["remove_primary_location_probability"]:
            child["acceptable_location_ids"].remove("site_A")
        if rng.random() < rules["remove_backup_location_probability"]:
            child["acceptable_location_ids"].remove("site_B")
        for location in child["commute_minutes_by_location"]:
            child["commute_minutes_by_location"][location] = {
                "before": rng.choice(rules["commute_minutes"]),
                "after": rng.choice(rules["commute_minutes"]),
            }
    for provider in case["providers"]:
        if rng.random() < rules["provider_withdrawal_probability"]:
            provider["declared_offer_acceptance"] = False
    for person in case["staff"]:
        if rng.random() < rules["staff_qualification_removal_probability"]:
            person["qualification_tags"] = []
    for location in case["locations"]:
        location["declared_concurrent_child_capacity"] = rng.choice(rules["location_capacity"])
    existing = rng.random() < rules["all_capacity_already_open_probability"]
    for offer in case["offers"]:
        offer["declared_child_capacity"] = rng.choice(rules["offer_capacity"])
        amount = rng.randrange(
            rules["opening_cost_cents_min"],
            rules["opening_cost_cents_max"] + rules["opening_cost_step_cents"],
            rules["opening_cost_step_cents"],
        )
        change_fixed_cost(offer, amount)
        offer["per_child_cost_cents"] = rng.choice(rules["per_child_cost_cents"])
        offer["commitment_required"] = not existing
        if offer["role"] == "backup":
            offer["standby_retainer_cents"] = rng.choice(rules["standby_retainer_cents"])
    for payer in case["payers"]:
        prefix = "parent" if payer["kind"] == "parent" else "employer"
        payer["payment_ceiling_cents"] = rng.randrange(
            rules[f"{prefix}_ceiling_cents_min"],
            rules[f"{prefix}_ceiling_cents_max"] + rules[f"{prefix}_ceiling_step_cents"],
            rules[f"{prefix}_ceiling_step_cents"],
        )
    if rng.random() < rules["correlated_outage_probability"]:
        case["scenarios"].append(
            {
                "id": "both_absent",
                "announced_minute": 300,
                "failed_provider_ids": ["provider_A", "provider_B"],
                "failed_staff_ids": [],
                "closed_location_ids": [],
            }
        )
    case["case_generation"] = {
        "kind": "fixed_seed_randomized",
        "seed": seed,
        "solver_outcome_not_used_to_generate": True,
    }
    return case


def origin_tamper_checks() -> None:
    """Challenge the checker with adversarial modifications of the already observed origin."""
    case = read(BASE / "technical/origin_case.json")
    origin = read(BASE / "technical/origin_result.json")
    offer = origin["results"]["combined"]["offer"]
    records = []
    for label in (
        "care_gap",
        "missing_backup_world",
        "understated_reserve",
        "unaccepted_shift",
        "qualification_removed",
        "payer_ceiling_reduced",
        "cost_obligation_deleted",
        "reported_employer_output_changed",
    ):
        changed_case, changed_offer = copy.deepcopy(case), copy.deepcopy(offer)
        if label == "care_gap":
            changed_offer["worlds"][0]["child_care"][0]["provided_care_interval"][0] += 1
        elif label == "missing_backup_world":
            del changed_offer["scenario_assignments"]["primary_provider_absent"]
        elif label == "understated_reserve":
            changed_offer["backup_obligation"]["maximum_activation_reserve_cents"] -= 1
        elif label == "unaccepted_shift":
            next(w for w in changed_case["workers"] if w["id"] == "E_A_W2")["permitted_shift_ids"] = ["late"]
            changed_offer["transformation_witness"]["case_sha256"] = digest(changed_case)
        elif label == "qualification_removed":
            next(s for s in changed_case["staff"] if s["id"] == "staff_B_early")["qualification_tags"] = []
            changed_offer["transformation_witness"]["case_sha256"] = digest(changed_case)
        elif label == "payer_ceiling_reduced":
            next(p for p in changed_case["payers"] if p["id"] == "payer_E_A")["payment_ceiling_cents"] = 1
            changed_offer["transformation_witness"]["case_sha256"] = digest(changed_case)
        elif label == "cost_obligation_deleted":
            changed_offer["cost_items"] = [
                x for x in changed_offer["cost_items"] if x["category"] != "worker_compensation"
            ]
        elif label == "reported_employer_output_changed":
            changed_offer["employer_output_checks"][0]["actual_worker_minutes"] -= 1
        check = verify_offer(changed_case, changed_offer)
        records.append({"tamper": label, "rejected": not check["valid"], "check": check})
    result = {
        "schema": "agi-alpha.e1-origin-tamper-checks.v1",
        "run_utc": now(),
        "all_tampered_witnesses_rejected": all(x["rejected"] for x in records),
        "cases": records,
        "scope": "Origin-only checker tests before freeze, not fresh outcome selection.",
    }
    save(BASE / "technical/origin_tamper_checks.json", result)
    print(
        json.dumps(
            {"all_tampered_witnesses_rejected": result["all_tampered_witnesses_rejected"], "count": len(records)}
        )
    )


def fresh() -> None:
    """Generate once after freeze and retain every input and every result."""
    frozen = verify_frozen()
    output = BASE / "technical/fresh"
    if output.exists():
        raise RuntimeError("Fresh output exists; preserve the original run instead of overwriting it")
    origin = read(BASE / "technical/origin_case.json")
    policy = read(BASE / "technical/fresh_case_policy.json")
    started = now()
    cases = [targeted(origin, label) for label in policy["targeted_cases"]]
    cases += [randomized(origin, seed, policy["sampling_rules"]) for seed in policy["random_seeds"]]
    for case in cases:
        save(output / f"{case['case_id']}.input.json", case)
    rows = []
    for case in cases:
        result = compare(case)
        save(output / f"{case['case_id']}.result.json", result)
        combined = result["results"]["combined"]
        fixed = result["results"]["fixed_roster_pooled_care"]
        offer = combined["offer"]
        rows.append(
            {
                "case_id": case["case_id"],
                "kind": case["case_generation"]["kind"],
                "input_sha256": digest(case),
                "statuses": {k: v["status"] for k, v in result["results"].items()},
                "all_searches_exhaustive": all(
                    v["exhaustive_within_declared_bounds"] for v in result["results"].values()
                ),
                "same_formulation_control_ties": result["same_formulation_exact_control"]["identical_selected_result"],
                "combined_quote_cents": offer["maximum_funded_package_cents"] if offer else None,
                "maximum_coordinator_fee_cents": offer["maximum_admissible_coordinator_fee_cents"] if offer else None,
                "combined_checker_valid": combined.get("acceptance_check", {}).get("valid"),
                "new_complete_funded_package_vs_fixed_roster": combined["status"] == "offered"
                and fixed["status"] != "offered",
                "refusal_reasons": combined["rejection_reasons"],
            }
        )
    counts = Counter(row["statuses"]["combined"] for row in rows)
    summary = {
        "schema": "agi-alpha.e1-fresh-summary.v1",
        "started_utc": started,
        "finished_utc": now(),
        "freeze_record": frozen,
        "all_frozen_hashes_verified_before_execution": True,
        "case_count": len(rows),
        "targeted_count": len(policy["targeted_cases"]),
        "fixed_seed_random_count": len(policy["random_seeds"]),
        "combined_status_counts": dict(counts),
        "same_formulation_ties": sum(row["same_formulation_control_ties"] for row in rows),
        "new_complete_packages_vs_fixed": sum(row["new_complete_funded_package_vs_fixed_roster"] for row in rows),
        "every_case_retained": True,
        "cases": rows,
        "interpretation": "Finite synthetic engineering cases; rates are not estimates of demand or real-world prevalence.",
    }
    verify_frozen()
    summary["all_frozen_hashes_unchanged_after_execution"] = True
    save(BASE / "technical/fresh_suite_summary.json", summary)
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "case_count",
                    "combined_status_counts",
                    "same_formulation_ties",
                    "new_complete_packages_vs_fixed",
                )
            }
        )
    )


def main() -> None:
    """Execute an explicit stage; fresh runs require an existing immutable freeze record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["origin-checks", "freeze", "fresh"])
    args = parser.parse_args()
    {"origin-checks": origin_tamper_checks, "freeze": freeze, "fresh": fresh}[args.command]()


if __name__ == "__main__":
    main()
