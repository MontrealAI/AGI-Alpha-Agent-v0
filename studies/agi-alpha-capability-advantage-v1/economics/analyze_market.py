"""Read-only reporting for a completed, frozen market campaign.

This module never imports or calls a simulator. It does not change prices,
calibration, seeds, source, or outcomes. Aggregate scenario counts describe a
sensitivity panel and are not commercial probabilities or forecasts.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ARMS = ("A", "B", "C", "D")
KEYS = (
    "B_minus_A_cents", "C_minus_B_cents", "B_minus_D_cents", "C_minus_D_cents",
    "B_minus_A_project_cents", "C_minus_B_project_cents",
    "B_minus_D_project_cents", "C_minus_D_project_cents",
    "B_minus_A_unrounded_compute_project_cents", "C_minus_B_unrounded_compute_project_cents",
    "B_minus_D_unrounded_compute_project_cents", "C_minus_D_unrounded_compute_project_cents",
)


def load(path: Path):
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def dump(path: Path, value) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def sign(value: float) -> str:
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def sign_counts(values) -> dict:
    counts = Counter(sign(value) for value in values)
    return {key: counts[key] for key in ("negative", "zero", "positive")}


def describe(values) -> dict:
    values = sorted(values)
    if not values:
        return {"n": 0, "min": None, "median": None, "max": None}
    n = len(values)
    median = values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2
    return {"n": n, "min": values[0], "median": median, "max": values[-1], **sign_counts(values)}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def close(a: float, b: float) -> None:
    if not math.isclose(a, b, abs_tol=1e-6, rel_tol=1e-10):
        raise ValueError(f"History does not reconcile: {a} != {b}")


def asset_rows(world: dict, arm: str) -> tuple[list[dict], list[dict]]:
    """One fixed-cost allocation per asset; retain failed zero-use assets."""
    run = world["arms"][arm]
    rows, recipients = [], []
    for family, asset in run["assets"].items():
        uses = [job for job in run["histories"]["jobs"]
                if job["family"] == family and job["actual_asset_value_cents"] is not None]
        upkeep = [bill for bill in run["histories"]["bills"]
                  if bill["reference"] == f"capability:{family}:maintenance/revalidation"]
        close(sum(job["actual_asset_value_cents"] for job in uses), asset["avoided"])
        close(sum(bill["amountCents"] for bill in upkeep), asset["upkeep"])
        if len(uses) != asset["uses"]:
            raise ValueError("Asset invocation mismatch")
        prefix = -asset["cost"]
        first_week = first_use = None
        index = 0
        by_week = defaultdict(list)
        maintenance = Counter()
        for job in uses:
            by_week[job["week"]].append(job)
        for bill in upkeep:
            maintenance[bill["week"]] += bill["amountCents"]
        for week in sorted(set(by_week) | set(maintenance)):
            prefix -= maintenance[week]
            for job in by_week[week]:
                index += 1
                prefix += job["actual_asset_value_cents"]
                if prefix >= 0 and first_week is None:
                    first_week, first_use = week, index
        net = asset["avoided"] - asset["cost"] - asset["upkeep"]
        close(prefix, net)
        n = len(uses)
        accepted = sum(job["accepted"] for job in uses)
        direct_positive = sum(job["actual_asset_value_cents"] > 0 for job in uses)
        fixed = asset["cost"] + asset["upkeep"]
        common = {"condition_id": world["condition_id"], "schedule_id": world["cost_schedule"],
                  "seed": world["seed"], "arm": arm, "family": family}
        row = {**common, "funding": asset["funding"], "failed_creation": asset["failed"],
               "built_week": asset["builtWeek"], "available_week": asset["availableWeek"],
               "nominal_expiry_week": asset["expiresWeek"],
               "assumed_lifetime_weeks": run["condition"]["useful_life_weeks"],
               "observed_active_maintenance_weeks": len(upkeep),
               "construction_cents": asset["cost"], "upkeep_cents": asset["upkeep"],
               "attempted_uses": n, "accepted_uses": accepted, "direct_positive_uses": direct_positive,
               "unique_recipients": len({job["recipient"] for job in uses}),
               "direct_savings_before_shared_fixed_cents": asset["avoided"],
               "direct_savings_after_shared_fixed_cents": net,
               "net_per_attempted_use_cents": net / n if n else None,
               "net_per_accepted_use_cents": net / accepted if accepted else None,
               "unallocated_fixed_cost_if_no_users_cents": fixed if not n else 0,
               "first_chronological_break_even_week": first_week,
               "first_chronological_break_even_attempt": first_use,
               "terminal_direct_payback": asset["direct_payback_diagnostic"],
               "individual_finance_qualification": asset["individual_finance_qualification"]}
        rows.append(row)
        allocations = defaultdict(list)
        for job in uses:
            allocations[job["recipient"]].append(job)
        allocated = 0.0
        for recipient, jobs in sorted(allocations.items()):
            share = fixed * len(jobs) / n
            allocated += share
            direct = sum(job["actual_asset_value_cents"] for job in jobs)
            recipients.append({**common, "recipient": recipient, "attempted_uses": len(jobs),
                               "accepted_uses": sum(job["accepted"] for job in jobs),
                               "direct_savings_before_shared_fixed_cents": direct,
                               "allocated_build_and_upkeep_cents": share,
                               "asset_allocated_net_cents": direct - share,
                               "allocation_rule": "equal fixed share per attempted use, including failures"})
        if n:
            close(allocated, fixed)
    return rows, recipients


def analyze(results: Path, output: Path) -> dict:
    root = results.parent
    completion_path = results / "completion.json"
    if not completion_path.exists():
        raise ValueError("COMPLETED_CAMPAIGN_REQUIRED_NO_PARTIAL_INSPECTION")
    completion = load(completion_path)
    if completion.get("status") != "COMPLETE" or completion.get("worlds") != 2304:
        raise ValueError("COMPLETE_FROZEN_2304_WORLD_CAMPAIGN_REQUIRED")
    freeze_path = root / "market-freeze.json"
    if sha(freeze_path) != completion["source_freeze_sha256"]:
        raise ValueError("Freeze mismatch")
    freeze = load(freeze_path)
    for row in freeze["files"]:
        path = root / row["path"]
        if sha(path) != row["sha256"] or path.stat().st_size != row["bytes"]:
            raise ValueError(f"Frozen source changed: {path}")
    protocol = load(root / "market-protocol.json")
    summary = load(results / "summary.json")
    compact = load(results / "compact-worlds.json")
    if len(summary["conditions"]) != 144 or len(compact) != 2304:
        raise ValueError("Missing primary cells")
    if len({(r["condition_id"], r["schedule_id"], r["seed"]) for r in compact}) != 2304:
        raise ValueError("Duplicate primary worlds")
    output.mkdir(exist_ok=False)

    cell_rows = []
    for cell in summary["conditions"]:
        row = {"condition_id": cell["condition_id"], "schedule_id": cell["schedule_id"], **cell["condition"]}
        row.pop("id")
        for key in KEYS:
            for field in ("mean", "min", "max", "negative", "zero", "positive"):
                row[f"{key}_{field}"] = cell["differences"][key][field]
        for arm in ARMS:
            data = cell["arms"][arm]
            for field in ("profit", "project_profit", "accepted", "collections", "transfers"):
                row[f"{arm}_{field}_mean"] = data[field]["mean"]
            row[f"{arm}_funded_later_assets"] = data["funded_later_capabilities"]
            row[f"{arm}_qualifying_bundle_worlds"] = data["qualifying_later_bundle_worlds"]
        cell_rows.append(row)
    write_csv(output / "all-144-cells.csv", cell_rows)
    case_rows = [{"condition_id": row["condition_id"], "schedule_id": row["schedule_id"],
                  "seed": row["seed"], **row["differences"],
                  **{f"{arm}_bundle_qualifies": row["succession"][arm]["qualifies"] for arm in ARMS}}
                 for row in compact]
    write_csv(output / "all-2304-paired-cases.csv", case_rows)

    cells_by_sign = {key: {label: [f"{row['condition_id']}/{row['schedule_id']}"
                                  for row in summary["conditions"]
                                  if sign(row["differences"][key]["mean"]) == label]
                           for label in ("negative", "zero", "positive")} for key in KEYS}
    signs = {key: {"cell_means": {s: len(v) for s, v in cells_by_sign[key].items()},
                   "paired_worlds": sign_counts(row["differences"][key] for row in compact)} for key in KEYS}
    by_schedule = {schedule["id"]: {key: {
        "cell_means": sign_counts(row["differences"][key]["mean"] for row in summary["conditions"]
                                  if row["schedule_id"] == schedule["id"]),
        "paired_worlds": sign_counts(row["differences"][key] for row in compact
                                     if row["schedule_id"] == schedule["id"])} for key in KEYS}
                   for schedule in protocol["schedules"]}
    assets, recipients, world_rows = [], [], []
    failures = {arm: Counter() for arm in ARMS}
    buyer_choices = {arm: Counter() for arm in ARMS}
    reason_counts = {arm: Counter() for arm in ARMS}
    known = {(row["condition_id"], row["schedule_id"], row["seed"]): row for row in compact}
    finance_true = Counter()
    completed_worlds = 0
    with gzip.open(results / "complete-worlds.jsonl.gz", "rt") as stream:
        for line in stream:
            world = json.loads(line)
            key = (world["condition_id"], world["cost_schedule"], world["seed"])
            compact_row = known[key]
            for metric in KEYS:
                close(world["differences"][metric], compact_row["differences"][metric])
            for arm in ARMS:
                run = world["arms"][arm]
                new_assets, new_recipients = asset_rows(world, arm)
                assets.extend(new_assets)
                recipients.extend(new_recipients)
                for choice in run["histories"]["buyerChoices"]:
                    buyer_choices[arm][choice["choice"]] += 1
                for decision in run["histories"]["decisions"]:
                    reason_counts[arm].update(decision["reasons"])
                counts = Counter()
                for job in run["histories"]["jobs"]:
                    if job["route"] != "validated-acquisition":
                        continue
                    counts["shared_attempts"] += 1
                    if not job["accepted"]:
                        counts["rejected_shared_jobs"] += 1
                        counts["rejected_shared_cost_cents"] += job["cost_cents"]
                    if job["acquisition_failed"]:
                        counts["acquisition_failure_flagged_jobs"] += 1
                        counts["acquisition_failure_flagged_cost_cents"] += job["cost_cents"]
                    if job["stale"]:
                        counts["stale_flagged_jobs"] += 1
                        counts["stale_flagged_cost_cents"] += job["cost_cents"]
                    if job["stale"] and job["acquisition_failed"]:
                        counts["both_failure_flags_jobs"] += 1
                        counts["both_failure_flags_cost_cents"] += job["cost_cents"]
                counts["failed_asset_constructions"] = sum(asset["failed"] for asset in run["assets"].values())
                counts["failed_asset_construction_cents"] = sum(asset["cost"] for asset in run["assets"].values() if asset["failed"])
                counts["internal_contributor_rewards_cents"] = sum(row["reward_cents"] for row in run["histories"]["contributionAllocations"])
                counts["competitor_copying_cost_cents"] = run["competitor"]["copying_costs_cents"]
                failures[arm].update(counts)
                if world["succession"][arm]["qualifies"]:
                    finance_true[arm] += 1
                record = {"condition_id": key[0], "schedule_id": key[1], "seed": key[2], "arm": arm,
                          **run["summary"], **dict(counts)}
                if arm in ("B", "C"):
                    record.update({f"bundle_{k}": v for k, v in world["succession"][arm].items()
                                   if isinstance(v, (int, float, bool))})
                world_rows.append(record)
            completed_worlds += 1
    if completed_worlds != 2304:
        raise ValueError("Compressed full-history count mismatch")
    for arm in ARMS:
        expected = sum(row["succession"][arm]["qualifies"] for row in compact)
        if finance_true[arm] != expected:
            raise ValueError("Bundle counts do not reconcile")
    write_csv(output / "asset-payback-and-lifetimes.csv", assets)
    write_csv(output / "recipient-asset-values.csv", recipients)
    write_csv(output / "all-9216-enterprise-histories.csv", world_rows)

    rep_path = results / "preselected-representative.json"
    rep = load(rep_path)
    preselected = protocol["representative"]
    if (rep["condition_id"], rep["cost_schedule"], rep["seed"]) != (
            preselected["condition_id"], preselected["schedule_id"], preselected["seed"]):
        raise ValueError("Representative changed")
    rep_summary = {"selection": preselected, "condition": rep["arms"]["A"]["condition"],
                   "differences": rep["differences"], "succession": rep["succession"],
                   "arms": {arm: {"summary": rep["arms"][arm]["summary"],
                                   "assets": rep["arms"][arm]["assets"],
                                   "buyer_choices": dict(Counter(row["choice"] for row in rep["arms"][arm]["histories"]["buyerChoices"])),
                                   "investment_decision_reasons": dict(Counter(reason for row in rep["arms"][arm]["histories"]["decisions"] for reason in row["reasons"]))}
                            for arm in ARMS}}
    dump(output / "preselected-representative-summary.json", rep_summary)
    asset_summary = {}
    for arm in ARMS:
        subset = [row for row in assets if row["arm"] == arm]
        person = [row for row in recipients if row["arm"] == arm]
        asset_summary[arm] = {
            "constructed_asset_records": len(subset),
            "failed_construction_records": sum(row["failed_creation"] for row in subset),
            "positive_terminal_direct_payback_records": sum(row["terminal_direct_payback"] for row in subset),
            "chronological_break_even_observed_records": sum(row["first_chronological_break_even_attempt"] is not None for row in subset),
            "per_attempt_net_cents_distribution_across_asset_records": describe(row["net_per_attempted_use_cents"] for row in subset if row["net_per_attempted_use_cents"] is not None),
            "per_accepted_use_net_cents_distribution_across_asset_records": describe(row["net_per_accepted_use_cents"] for row in subset if row["net_per_accepted_use_cents"] is not None),
            "first_break_even_attempt_distribution_if_observed": describe(row["first_chronological_break_even_attempt"] for row in subset if row["first_chronological_break_even_attempt"] is not None),
            "observed_active_maintenance_weeks": describe(row["observed_active_maintenance_weeks"] for row in subset),
            "recipient_asset_records": len(person),
            "recipient_asset_allocated_net_cents_distribution": describe(row["asset_allocated_net_cents"] for row in person),
            "unallocated_fixed_cost_on_zero_use_assets_cents": sum(row["unallocated_fixed_cost_if_no_users_cents"] for row in subset),
        }
    paired_rounding_sign_changes = {}
    for left, right in (("B", "A"), ("C", "B"), ("B", "D"), ("C", "D")):
        cash_key = f"{left}_minus_{right}_project_cents"
        raw_key = f"{left}_minus_{right}_unrounded_compute_project_cents"
        paired_rounding_sign_changes[f"{left}_minus_{right}"] = {
            "worlds_where_cash_and_unrounded_sign_differ": sum(sign(row["differences"][cash_key]) != sign(row["differences"][raw_key]) for row in compact),
            "cash_zero_but_unrounded_positive": sum(row["differences"][cash_key] == 0 and row["differences"][raw_key] > 0 for row in compact),
            "cash_zero_but_unrounded_negative": sum(row["differences"][cash_key] == 0 and row["differences"][raw_key] < 0 for row in compact),
        }
    report = {
        "schema": "capability-advantage-market-analysis/v1",
        "analysis_created_at_utc": datetime.now(timezone.utc).isoformat(),
        "basis": "DESCRIPTIVE_ANALYSIS_OF_CLOSED_FROZEN_SENSITIVITY_PANEL_NO_NEW_OUTCOMES",
        "counts": {"cells": 144, "paired_worlds": 2304, "enterprise_histories": 9216},
        "completion": completion,
        "signs": signs, "signs_by_cost_schedule": by_schedule, "cell_ids_by_sign": cells_by_sign,
        "qualifying_later_bundle_worlds": {arm: finance_true[arm] for arm in ARMS},
        "funded_later_asset_records": {arm: sum(row["later_investment_counts"][arm] for row in compact) for arm in ARMS},
        "project_profit_world_signs": {arm: sign_counts(row["arms"][arm]["project_inclusive_profit_cents"] for row in compact) for arm in ARMS},
        "prospective_deployment_profit_world_signs": {arm: sign_counts(row["arms"][arm]["prospective_deployment_profit_cents"] for row in compact) for arm in ARMS},
        "asset_direct_values": asset_summary,
        "failure_and_incentive_counts_across_simulated_histories": {arm: dict(failures[arm]) for arm in ARMS},
        "buyer_choice_counts_across_simulated_histories": {arm: dict(buyer_choices[arm]) for arm in ARMS},
        "investment_rejection_reason_counts_across_repeated_weekly_decisions": {arm: dict(reason_counts[arm]) for arm in ARMS},
        "rounding_sign_changes": paired_rounding_sign_changes,
        "preselected_representative": rep_summary,
        "actual_cost_boundary": summary["unknown_actual_cost_boundary"],
        "interpretation_limits": [
            "Every monetary value is a declared model assumption; actual customer collections are zero and actual complete costs are unknown.",
            "Counts across the designed panel are descriptive counts, not market probabilities, expected commercial profits, or pooled estimates of an economy.",
            "Each paired world holds condition, cost schedule, and seed fixed. Cell means summarize only the 16 seeds of that declared condition.",
            "The balanced-marginal panel is not a full factorial. Marginal associations cannot identify isolated factor effects.",
            "Asset direct values compare complete recorded shared execution with the recipient's retaining independent alternative. Shared fixed construction and upkeep are allocated once per asset, equally across attempted uses including failures.",
            "Asset allocation excludes unrelated prototypes and common enterprise overhead. Whole-project paired outcomes account for completed unused prototypes and enterprise overhead separately; do not add these two views together.",
            "Unallocated zero-use asset costs remain explicit. Negative and failed cases are retained.",
            "First break-even is an observed within-simulation prefix diagnostic, can be reversed by later maintenance, and does not establish stationary future savings or an individual-generation financing result.",
            "Useful lives of 8 or 26 weeks are assumptions; observed maintenance weeks may be shorter because prerequisite expiry, failure, or insolvency removes availability.",
            "Failure-flag cost columns overlap when both acquisition and stale flags occur. The rejected-shared-cost column is the non-duplicated total.",
            "Contributor payments redistribute value and are not additional enterprise revenue. Competitor copying expenditures belong to competitor cash, not enterprise receipts.",
            "Bundle qualification concerns G2+G3 together and requires direct payback and the same-world project-inclusive counterfactual. It does not establish individual asset success, real self-financing, or scarce capability.",
            "Raw prior capability was not run; all four reconstructed comparators accepted the primary cohort. No global uniqueness, unsupported capability, actual market demand, or Level6 claim is identified.",
        ],
        "sources": [{"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}
                    for path in [completion_path, freeze_path, root / "market-protocol.json", root / "calibration.json",
                                 results / "summary.json", results / "compact-worlds.json",
                                 results / "complete-worlds.jsonl.gz", rep_path, Path(__file__).resolve()]],
    }
    dump(output / "analysis.json", report)
    return {"analysis": str(output / "analysis.json"), "cells": 144, "paired_worlds": 2304,
            "qualifying_later_bundle_worlds": report["qualifying_later_bundle_worlds"],
            "market_outcomes_run_by_analyzer": 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parent
    parser.add_argument("--results", type=Path, default=root / "results-primary")
    parser.add_argument("--output", type=Path, default=root / "analysis-primary")
    args = parser.parse_args()
    print(json.dumps(analyze(args.results.resolve(), args.output.resolve())))


if __name__ == "__main__":
    main()
