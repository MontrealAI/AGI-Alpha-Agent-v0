# SPDX-License-Identifier: Apache-2.0
"""Replay disclosed E1 cases and known checker defects against separately frozen V2."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from e1_instrument_v2 import compare, digest
from e1_verify_v2 import verify_offer

Json = dict[str, Any]
BASE = Path(__file__).resolve().parents[1]


def read(path: Path) -> Json:
    """Load a JSON object."""
    return cast(Json, json.loads(path.read_text()))


def sha(path: Path) -> str:
    """Hash exact file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: Json) -> None:
    """Preserve existing evidence by refusing to overwrite a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def frozen() -> Json:
    """Require all source, policy and prior evidence hashes declared by the freeze."""
    manifest = read(BASE / "technical/FROZEN_TECHNICAL_V2.json")
    for category in ("files", "preserved_evidence"):
        for relative, expected in manifest[category].items():
            if sha(BASE / relative) != expected:
                raise ValueError(f"Frozen file changed: {relative}")
    return manifest


def replay() -> None:
    """Recompute every origin, original fresh and boundary case without regenerating inputs."""
    manifest = frozen()
    policy = read(BASE / "technical/v2_replay_policy.json")
    started = datetime.now(timezone.utc).isoformat()
    entries = []
    counts: Counter[str] = Counter()
    for item in policy["cases"]:
        input_path, prior_path = BASE / item["input"], BASE / item["prior_result"]
        if sha(input_path) != item["input_sha256"] or sha(prior_path) != item["prior_result_sha256"]:
            raise ValueError(f"Prior evidence changed: {item['input']}")
        case, prior = read(input_path), read(prior_path)
        result = compare(case)
        checks = {}
        for mode, value in result["results"].items():
            old = prior["results"][mode]
            checks[mode] = {
                "same_status": value["status"] == old["status"],
                "same_complete_selected_offer": value["offer"] == old["offer"],
                "exhaustive": value["exhaustive_within_declared_bounds"],
                "selected_offer_verified": not value["offer"] or value["acceptance_check"]["valid"],
            }
        unchanged = all(all(check.values()) for check in checks.values())
        tie = result["same_formulation_exact_control"]["identical_selected_result"]
        target = BASE / "technical/v2_replay" / f"{case['case_id']}.result.json"
        save(target, result)
        entries.append(
            {
                "case_id": case["case_id"],
                "source_input": item["input"],
                "result": str(target.relative_to(BASE)),
                "result_sha256": sha(target),
                "combined_status": result["results"]["combined"]["status"],
                "all_regression_checks_passed": unchanged,
                "ordinary_control_ties": tie,
                "per_mode_checks": checks,
            }
        )
        counts[result["results"]["combined"]["status"]] += 1
    frozen()
    summary = {
        "schema": "agi-alpha.e1-v2-replay.v1",
        "interpretation": "Disclosed-input regression only; this is not fresh technical confirmation.",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "v2_frozen_utc": manifest["frozen_utc"],
        "case_count": len(entries),
        "combined_status_counts": dict(counts),
        "all_regression_checks_passed": all(e["all_regression_checks_passed"] for e in entries),
        "same_formulation_ties": sum(e["ordinary_control_ties"] for e in entries),
        "all_frozen_hashes_unchanged": True,
        "cases": entries,
    }
    save(BASE / "technical/v2_replay_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "cases"}))


def known_defects() -> None:
    """Check disclosed V1 defects plus nearby serialized fields; no fresh-validation claim."""
    frozen()
    origin = read(BASE / "technical/origin_case.json")
    baseline = read(BASE / "technical/origin_result_v2.json")["results"]["combined"]["offer"]
    mutations = [
        "backup_offer_ids",
        "reserve_staff_minutes",
        "worker_permitted_shifts",
        "worker_employer",
        "two_realized_worlds",
        "two_operating_days",
        "not_synthetic",
        "wrong_currency",
        "cost_detail",
        "child_parent",
        "repeatable_days",
    ]
    checks = []
    for name in mutations:
        case, offer = deepcopy(origin), deepcopy(baseline)
        if name == "backup_offer_ids":
            offer["backup_obligation"]["backup_offer_ids"] = []
        elif name == "reserve_staff_minutes":
            offer["backup_obligation"]["reserve_staff_minutes"] = {}
        elif name == "worker_permitted_shifts":
            offer["worker_schedule"][0]["permitted_shift_ids"] = []
        elif name == "worker_employer":
            offer["worker_schedule"][0]["employer_id"] = "UNDECLARED"
        elif name == "two_realized_worlds":
            case["horizon"]["maximum_backup_event_worlds_realized"] = 2
        elif name == "two_operating_days":
            case["horizon"]["operating_days"] = 2
        elif name == "not_synthetic":
            case["synthetic"] = False
        elif name == "wrong_currency":
            case["currency"] = "USD"
        elif name == "cost_detail":
            offer["cost_items"][0]["detail"]["primary_cost_is_nonrefundable_if_provider_absent"] = False
        elif name == "child_parent":
            offer["worlds"][0]["child_care"][0]["parent_worker_id"] = "UNDECLARED"
        elif name == "repeatable_days":
            offer["repeatable_eligible_workload"]["verified_operating_days"] = 2
        offer["transformation_witness"]["case_sha256"] = digest(case)
        check = verify_offer(case, offer)
        target = BASE / "technical/v2_known_defect_checks" / f"{name}.json"
        save(target, {"name": name, "input": case, "offer": offer, "check": check})
        checks.append({"name": name, "rejected": not check["valid"], "errors": check["errors"]})
    scaled = deepcopy(origin)
    factor = 10**9
    scaled["case_id"] = "origin_all_monetary_fields_scaled_1e9"
    scaled["coordinator_fee_cents"] *= factor
    for worker in scaled["workers"]:
        worker["change_compensation_cents"] = {
            key: value * factor for key, value in worker["change_compensation_cents"].items()
        }
    for offer in scaled["offers"]:
        for field in ("fixed_opening_cost_cents", "per_child_cost_cents", "standby_retainer_cents"):
            offer[field] *= factor
        offer["cost_breakdown"] = {key: value * factor for key, value in offer["cost_breakdown"].items()}
    for payer in scaled["payers"]:
        payer["payment_ceiling_cents"] *= factor
    result = compare(scaled)
    selected = result["results"]["combined"]
    scale_ok = (
        selected["status"] == "offered"
        and selected["acceptance_check"]["valid"]
        and selected["offer"]["maximum_funded_package_cents"] == 40500 * factor
        and selected["offer"]["maximum_admissible_coordinator_fee_cents"] == 7000 * factor
        and result["same_formulation_exact_control"]["identical_selected_result"]
    )
    folder = BASE / "technical/v2_known_defect_checks"
    save(folder / "scaled_money.input.json", scaled)
    save(folder / "scaled_money.result.json", result)
    summary = {
        "schema": "agi-alpha.e1-v2-known-defect-checks.v1",
        "interpretation": "Disclosed defects and developer nearby-field regression, not independent fresh audit.",
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_valid": verify_offer(origin, baseline)["valid"],
        "tamper_count": len(checks),
        "tamper_rejections": sum(c["rejected"] for c in checks),
        "checks": checks,
        "monetary_scaling_factor": factor,
        "monetary_scaling_passed": scale_ok,
        "scaled_status": selected["status"],
    }
    save(BASE / "technical/v2_known_defect_checks.json", summary)
    frozen()
    print(json.dumps(summary))


def main() -> None:
    """Run one evidence stage without overwriting frozen or previous artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("replay", "known-defects"))
    args = parser.parse_args()
    {"replay": replay, "known-defects": known_defects}[args.command]()


if __name__ == "__main__":
    main()
