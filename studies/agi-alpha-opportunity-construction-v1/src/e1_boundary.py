# SPDX-License-Identifier: Apache-2.0
"""Run a separately frozen, adaptive follow-up boundary study without changing E1 v1."""

from __future__ import annotations

import argparse
import copy
import itertools
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

from e1_instrument import compare, digest
from e1_run_suite import BASE, change_fixed_cost, file_hash, now, read, save, verify_frozen

Json = dict[str, Any]


def freeze_boundary() -> None:
    """Freeze the new question before generating any of its cases."""
    original = verify_frozen()
    path = BASE / "technical/FROZEN_BOUNDARY_POLICY.json"
    if path.exists():
        raise RuntimeError("Boundary freeze already exists")
    policy = read(BASE / "technical/boundary_policy.json")
    record = {
        "schema": "agi-alpha.e1-boundary-freeze.v1",
        "frozen_utc": now(),
        "original_technical_freeze": original,
        "original_fresh_summary_sha256": file_hash(BASE / "technical/fresh_suite_summary.json"),
        "designed_after_original_fresh_outcomes": True,
        "new_grid_cases_generated_or_executed_before_freeze": False,
        "files": {name: file_hash(BASE / name) for name in policy["freeze_files"]},
        "scope": "A new adaptive research question, prospectively fixed for its own executions.",
    }
    save(path, record)
    print(json.dumps(record))


def check_boundary() -> Json:
    """Check both the original and additional frozen source sets."""
    verify_frozen()
    record = read(BASE / "technical/FROZEN_BOUNDARY_POLICY.json")
    for name, expected in record["files"].items():
        if file_hash(BASE / name) != expected:
            raise RuntimeError(f"Boundary source/config changed: {name}")
    return cast(Json, record)


def grid_case(origin: Json, policy: Json, quote: int, ceiling: int, permissions: str, backup: bool) -> Json:
    """Change only the declared cost, ceiling and permission dimensions."""
    case = copy.deepcopy(origin)
    case["case_id"] = f"grid_F{quote}_C{ceiling}_{permissions}" + ("" if backup else "_no_backup")
    for offer in case["offers"]:
        change_fixed_cost(offer, quote)
    for worker in case["workers"]:
        flexible = permissions == "both_employers" or (
            permissions == "employer_A_only" and worker["employer_id"] == "E_A"
        )
        if not flexible:
            worker["permitted_shift_ids"] = [worker["current_shift_id"]]
    for payer in case["payers"]:
        payer["payment_ceiling_cents"] = (
            policy["grid"]["parent_ceiling_cents_per_parent"] if payer["kind"] == "parent" else ceiling
        )
    case["coordinator_fee_cents"] = policy["grid"]["coordinator_fee_cents"]
    if not backup:
        next(p for p in case["providers"] if p["id"] == "provider_B")["declared_offer_acceptance"] = False
    case["case_generation"] = {
        "kind": "prospectively_frozen_followup_grid",
        "fixed_opening_quote_cents": quote,
        "employer_ceiling_cents": ceiling,
        "roster_permissions": permissions,
        "backup_available": backup,
        "physical_offers_otherwise_unchanged": True,
    }
    return cast(Json, case)


def successor(origin: Json, spec: Json, underfunded: bool) -> Json:
    """Build a renamed, retimed, heterogeneous-commute mission from its frozen specification."""
    case = copy.deepcopy(origin)
    mappings: dict[str, str] = {"early": "morning", "late": "afternoon"}
    for employer, new_employer in (("E_A", "EMP_C1"), ("E_B", "EMP_C2")):
        mappings[employer] = new_employer
        mappings[f"payer_{employer}"] = f"sponsor_{new_employer}"
        for index in range(1, 5):
            worker = f"{employer}_W{index}"
            mappings[worker] = f"crew_{new_employer}_{index}"
            mappings[f"{worker}_C"] = f"dependent_{new_employer}_{index}"
            mappings[f"parent_{worker}"] = f"family_{new_employer}_{index}"
    for old, new in (("A", "NORTH"), ("B", "SOUTH")):
        mappings[f"provider_{old}"] = f"care_{new}"
        mappings[f"site_{old}"] = f"location_{new}"
        for shift, renamed in (("early", "morning"), ("late", "afternoon")):
            mappings[f"{old}_{shift}"] = f"{new}_{renamed}"
            mappings[f"staff_{old}_{shift}"] = f"carer_{new}_{renamed}"
    mappings["primary_provider_absent"] = "north_unavailable"
    mappings["backup_provider_absent"] = "south_unavailable"

    def rename(value: Any) -> Any:
        if isinstance(value, dict):
            return {mappings.get(k, k): rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return mappings.get(value, value) if isinstance(value, str) else value

    case = rename(case)
    case["case_id"] = spec["case_id"] + ("_underfunded" if underfunded else "")
    offset = spec["shift_and_offer_and_availability_and_notice_offset_minutes"]
    for shift in case["shifts"]:
        shift["start_minute"] += offset
        shift["end_minute"] += offset
    for location in case["locations"]:
        location["opening_windows"] = [[a + offset, b + offset] for a, b in location["opening_windows"]]
    for staff in case["staff"]:
        staff["available_windows"] = [[a + offset, b + offset] for a, b in staff["available_windows"]]
    for offer in case["offers"]:
        offer["window"] = [value + offset for value in offer["window"]]
        change_fixed_cost(offer, spec["fixed_opening_quote_cents"])
        offer["per_child_cost_cents"] = spec["per_child_cost_cents"]
        if offer["role"] == "backup":
            offer["standby_retainer_cents"] = spec["standby_retainer_cents"]
    for scenario in case["scenarios"]:
        scenario["announced_minute"] += offset
    for i, child in enumerate(case["children"]):
        child["commute_minutes_by_location"]["location_NORTH"] = {
            "before": spec["primary_before_commutes"][i],
            "after": spec["primary_after_commutes"][i],
        }
        child["commute_minutes_by_location"]["location_SOUTH"] = {
            "before": spec["backup_before_commutes"][i],
            "after": spec["backup_after_commutes"][i],
        }
    for worker in case["workers"]:
        for shift in worker["change_compensation_cents"]:
            worker["change_compensation_cents"][shift] = (
                0 if shift == worker["current_shift_id"] else spec["worker_change_compensation_cents"]
            )
    money = spec["underfunded_paired_variant"] if underfunded else spec
    for payer in case["payers"]:
        payer["payment_ceiling_cents"] = money[
            "parent_ceiling_cents" if payer["kind"] == "parent" else "employer_ceiling_cents"
        ]
    case["coordinator_fee_cents"] = spec["coordinator_fee_cents"]
    case["case_generation"] = {
        "kind": "prospectively_specified_successor",
        "underfunded_control": underfunded,
        "all_participants_and_resources_renamed": True,
        "new_work_and_care_times": True,
        "new_heterogeneous_location_specific_commutes": True,
        "construction_and_checker_inherited_without_modification": True,
        "outcome_acceptance_and_economics_not_inherited": True,
    }
    return cast(Json, case)


def run_boundary() -> None:
    """Retain all grid/control/successor inputs before executing their frozen comparisons."""
    frozen = check_boundary()
    output = BASE / "technical/boundary"
    if output.exists():
        raise RuntimeError("Preserve the original boundary execution instead of overwriting it")
    policy = read(BASE / "technical/boundary_policy.json")
    origin = read(BASE / "technical/origin_case.json")
    grid = policy["grid"]
    cases = [
        grid_case(origin, policy, quote, ceiling, permissions, True)
        for quote, ceiling, permissions in itertools.product(
            grid["fixed_opening_quote_cents_per_primary_or_backup_block"],
            grid["payment_ceiling_cents_per_employer"],
            grid["roster_permissions"],
        )
    ]
    cases.extend(
        grid_case(origin, policy, quote, ceiling, "both_employers", False)
        for quote, ceiling in itertools.product(
            grid["fixed_opening_quote_cents_per_primary_or_backup_block"],
            grid["payment_ceiling_cents_per_employer"],
        )
    )
    cases.extend(successor(origin, policy["successor"], underfunded) for underfunded in (False, True))
    started = now()
    for case in cases:
        save(output / f"{case['case_id']}.input.json", case)
    rows = []
    for case in cases:
        result = compare(case)
        save(output / f"{case['case_id']}.result.json", result)
        selected = result["results"]["combined"]
        offer = selected["offer"]
        rows.append(
            {
                "case_id": case["case_id"],
                "case_generation": case["case_generation"],
                "input_sha256": digest(case),
                "statuses": {k: v["status"] for k, v in result["results"].items()},
                "all_searches_exhaustive": all(
                    x["exhaustive_within_declared_bounds"] for x in result["results"].values()
                ),
                "same_formulation_control_ties": result["same_formulation_exact_control"]["identical_selected_result"],
                "quote_cents": offer["maximum_funded_package_cents"] if offer else None,
                "maximum_coordination_fee_cents": offer["maximum_admissible_coordinator_fee_cents"] if offer else None,
                "checker_valid": selected.get("acceptance_check", {}).get("valid"),
                "care_minutes_per_world": offer["useful_outcome"]["care_minutes_per_world"] if offer else None,
                "refusal_reasons": selected["rejection_reasons"],
                "new_complete_package_vs_fixed": selected["status"] == "offered"
                and result["results"]["fixed_roster_pooled_care"]["status"] != "offered",
            }
        )
    summary = {
        "schema": "agi-alpha.e1-boundary-summary.v1",
        "started_utc": started,
        "finished_utc": now(),
        "freeze_record": frozen,
        "case_count": len(rows),
        "combined_status_counts": dict(Counter(row["statuses"]["combined"] for row in rows)),
        "same_formulation_ties": sum(row["same_formulation_control_ties"] for row in rows),
        "every_case_retained": True,
        "cases": rows,
        "original_zero_of_24_randomized_offers_result_retained": True,
        "interpretation": "An adaptive deterministic feasible-region study, not an eligibility frequency estimate.",
    }
    check_boundary()
    summary["all_original_and_followup_frozen_hashes_unchanged"] = True
    save(BASE / "technical/boundary_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("case_count", "combined_status_counts", "same_formulation_ties")}))


def main() -> None:
    """Freeze or execute the separately specified follow-up."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "run"])
    args = parser.parse_args()
    {"freeze": freeze_boundary, "run": run_boundary}[args.command]()


if __name__ == "__main__":
    main()
