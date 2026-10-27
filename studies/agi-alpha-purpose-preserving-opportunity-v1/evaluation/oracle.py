# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

SEASONS = ("early", "mid", "late")
HABITATS = ("dry", "mesic", "wet")
SCOPE = "documented-source-screen"


def integer(value: Any, minimum: int) -> bool:
    return type(value) is int and value >= minimum


def text_value(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_inputs(task: Any, catalog: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(task, dict):
        return ["task must be an object"]
    taxa = catalog.get("taxa") if isinstance(catalog, dict) else None
    if not isinstance(taxa, list):
        errors.append("catalog.taxa must be a list")
        taxa = []
    taxon_ids: list[str] = []
    for i, taxon in enumerate(taxa):
        if not isinstance(taxon, dict):
            errors.append(f"catalog.taxa[{i}] must be an object")
            continue
        if not text_value(taxon.get("id")):
            errors.append(f"catalog.taxa[{i}].id is missing")
        else:
            taxon_ids.append(taxon["id"])
        for name, choices in (("seasons", SEASONS), ("water", HABITATS)):
            values = taxon.get(name)
            if not isinstance(values, list) or any(v not in choices for v in values):
                errors.append(f"catalog.taxa[{i}].{name} is invalid")
        if taxon.get("nectar") is not None and type(taxon.get("nectar")) is not bool:
            errors.append(f"catalog.taxa[{i}].nectar is invalid")
        hosts = taxon.get("hosts")
        if not isinstance(hosts, list) or any(not text_value(v) for v in hosts):
            errors.append(f"catalog.taxa[{i}].hosts is invalid")
        if not taxon.get("source"):
            errors.append(f"catalog.taxa[{i}].source is missing")
    if len(set(taxon_ids)) != len(taxon_ids):
        errors.append("catalog taxon IDs must be unique")
    for name in ("id", "purpose", "region"):
        if not text_value(task.get(name)):
            errors.append(f"task.{name} is missing")
    if task.get("habitat") not in HABITATS:
        errors.append("task.habitat is invalid")
    if task.get("resource_mode") not in ("flower", "nectar"):
        errors.append("task.resource_mode is invalid")
    seasons = task.get("required_seasons")
    if (
        not isinstance(seasons, list)
        or not seasons
        or any(s not in SEASONS for s in seasons)
        or len(set(seasons)) != len(seasons)
    ):
        errors.append("task.required_seasons must be nonempty and unique")
    if not integer(task.get("min_species_per_season"), 1):
        errors.append("task.min_species_per_season must be a positive integer")
    if task.get("required_host") not in (None, "monarch"):
        errors.append("task.required_host is unsupported")
    if not integer(task.get("delivery_week"), 0):
        errors.append("task.delivery_week must be a nonnegative integer")
    if not integer(task.get("quoted_price_cents"), 0):
        errors.append("task.quoted_price_cents must be a nonnegative integer")
    rows = task.get("rows")
    if not isinstance(rows, list):
        errors.append("task.rows must be a list")
        rows = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"task.rows[{i}] must be an object")
            continue
        for name in ("taxon", "unit"):
            if not text_value(row.get(name)):
                errors.append(f"task.rows[{i}].{name} is missing")
        if not integer(row.get("quantity"), 1):
            errors.append(f"task.rows[{i}].quantity must be a positive integer")
        if row.get("lot_id") is not None and not isinstance(row.get("lot_id"), str):
            errors.append(f"task.rows[{i}].lot_id is invalid")
    lots = task.get("lots")
    if not isinstance(lots, list):
        errors.append("task.lots must be a list")
        lots = []
    lot_ids: list[str] = []
    for i, lot in enumerate(lots):
        if not isinstance(lot, dict):
            errors.append(f"task.lots[{i}] must be an object")
            continue
        for name in ("id", "taxon", "unit"):
            if not text_value(lot.get(name)):
                errors.append(f"task.lots[{i}].{name} is missing")
        if text_value(lot.get("id")):
            lot_ids.append(lot["id"])
        if not integer(lot.get("quantity"), 0):
            errors.append(f"task.lots[{i}].quantity must be a nonnegative integer")
        if lot.get("available_week") is not None and not integer(lot.get("available_week"), 0):
            errors.append(f"task.lots[{i}].available_week is invalid")
        if lot.get("region") is not None and not isinstance(lot.get("region"), str):
            errors.append(f"task.lots[{i}].region is invalid")
        if lot.get("evidence_status") not in ("verified", "unknown", "failed"):
            errors.append(f"task.lots[{i}].evidence_status is invalid")
    if len(set(lot_ids)) != len(lot_ids):
        errors.append("lot IDs must be unique")
    return errors


def reference_report(task: Any, catalog: Any) -> dict[str, Any]:
    errors = validate_inputs(task, catalog)
    task_obj = task if isinstance(task, dict) else {}
    report: dict[str, Any] = {
        "task_id": task_obj.get("id"),
        "scope": SCOPE,
        "original_purpose": task_obj.get("purpose"),
        "input_errors": errors,
        "source_coverage": {},
        "supply_coverage": {},
        "host": {
            "required": task_obj.get("required_host"),
            "source_taxa": [],
            "supply_taxa": [],
            "pass": False,
        },
        "blockers": [],
        "original_unmet_obligations": [],
        "source_screen_pass": False,
        "field_outcomes_verified": False,
        "customer_acceptance_verified": False,
        "production_authorized": False,
    }
    if errors:
        return report
    taxa = {t["id"]: t for t in catalog["taxa"]}
    lots = {lot["id"]: lot for lot in task["lots"]}
    requested: Counter[str] = Counter()
    for row in task["rows"]:
        lot = lots.get(row.get("lot_id"))
        if lot is not None and row["unit"] == lot["unit"]:
            requested[lot["id"]] += row["quantity"]
    biological: set[str] = set()
    supplied: set[str] = set()
    blockers: list[dict[str, Any]] = []
    for i, row in enumerate(task["rows"]):
        reason: list[str] = []
        taxon = taxa.get(row["taxon"])
        if taxon is None:
            reason.append("unknown_taxon")
        else:
            if task["habitat"] not in taxon["water"]:
                reason.append("habitat_not_documented")
            if task["resource_mode"] == "nectar":
                if taxon.get("nectar") is None:
                    reason.append("nectar_unknown")
                elif taxon["nectar"] is False:
                    reason.append("pollen_only")
            if not reason:
                biological.add(row["taxon"])
        lot_id = row.get("lot_id")
        if not lot_id:
            reason.append("missing_lot")
            lot = None
        else:
            lot = lots.get(lot_id)
            if lot is None:
                reason.append("unknown_lot")
        if lot is not None:
            if lot["taxon"] != row["taxon"]:
                reason.append("lot_taxon_mismatch")
            if lot["unit"] != row["unit"]:
                reason.append("unit_mismatch")
            if lot["evidence_status"] != "verified":
                reason.append(f"lot_evidence_{lot['evidence_status']}")
            if not text_value(lot.get("region")):
                reason.append("region_unknown")
            elif lot["region"] != task["region"]:
                reason.append("region_mismatch")
            if lot.get("available_week") is None:
                reason.append("availability_unknown")
            elif lot["available_week"] > task["delivery_week"]:
                reason.append("unavailable_by_deadline")
            if row["unit"] == lot["unit"] and requested[lot["id"]] > lot["quantity"]:
                reason.append("insufficient_lot_quantity")
        if not reason:
            supplied.add(row["taxon"])
        for code in sorted(reason):
            blockers.append({"row": i, "code": code, "lot_id": lot_id or None})
    minimum = task["min_species_per_season"]
    seasons = [s for s in SEASONS if s in task["required_seasons"]]
    for field, eligible in (("source_coverage", biological), ("supply_coverage", supplied)):
        for season in seasons:
            names = sorted(t for t in eligible if season in taxa[t]["seasons"])
            report[field][season] = {
                "taxa": names,
                "count": len(names),
                "required": minimum,
                "gap": max(0, minimum - len(names)),
            }
    host = task.get("required_host")
    if host is None:
        report["host"]["pass"] = True
    else:
        report["host"]["source_taxa"] = sorted(t for t in biological if host in taxa[t]["hosts"])
        report["host"]["supply_taxa"] = sorted(t for t in supplied if host in taxa[t]["hosts"])
        report["host"]["pass"] = bool(report["host"]["supply_taxa"])
    report["blockers"] = blockers
    for season in seasons:
        coverage = report["supply_coverage"][season]
        if coverage["gap"]:
            report["original_unmet_obligations"].append(
                {
                    "kind": "seasonal",
                    "season": season,
                    "required": minimum,
                    "qualified": coverage["count"],
                    "gap": coverage["gap"],
                }
            )
    if not report["host"]["pass"]:
        report["original_unmet_obligations"].append({"kind": "host", "host": host})
    report["source_screen_pass"] = not blockers and not report["original_unmet_obligations"]
    return report


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        items = [canonical(v) for v in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    return value


def check_report(task: Any, catalog: Any, report: Any) -> dict[str, Any]:
    expected = reference_report(task, catalog)
    if not isinstance(report, dict):
        return {"accepted": False, "task_id": expected["task_id"], "mismatches": ["report must be an object"]}
    fields = list(expected)
    if expected["input_errors"]:
        fields = [
            "task_id",
            "scope",
            "original_purpose",
            "source_screen_pass",
            "field_outcomes_verified",
            "customer_acceptance_verified",
            "production_authorized",
        ]
    mismatches: list[str] = []
    for field in fields:
        actual = json.dumps(canonical(report.get(field)), sort_keys=True, ensure_ascii=False)
        wanted = json.dumps(canonical(expected[field]), sort_keys=True, ensure_ascii=False)
        if field not in report or actual != wanted:
            mismatches.append(field)
    if expected["input_errors"]:
        if not isinstance(report.get("input_errors"), list) or not report["input_errors"]:
            mismatches.append("input_errors must identify malformed input")
    return {"accepted": not mismatches, "task_id": expected["task_id"], "mismatches": mismatches}


def read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("expected", "check"))
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--reports")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    catalog = read_json(args.catalog)
    data = read_json(args.tasks)
    tasks = data["tasks"] if isinstance(data, dict) else data
    if args.mode == "expected":
        result: Any = {"reports": [reference_report(task, catalog) for task in tasks]}
    else:
        if not args.reports:
            parser.error("check mode requires --reports")
        submitted = read_json(args.reports)
        reports = submitted["reports"] if isinstance(submitted, dict) else submitted
        grouped: dict[Any, list[Any]] = {}
        for report in reports:
            key = report.get("task_id") if isinstance(report, dict) else None
            grouped.setdefault(key, []).append(report)
        checks = []
        for task in tasks:
            matches = grouped.get(task.get("id"), [])
            if len(matches) == 1:
                checks.append(check_report(task, catalog, matches[0]))
            else:
                checks.append(
                    {"accepted": False, "task_id": task.get("id"), "mismatches": ["missing or duplicated report"]}
                )
        task_ids = {task.get("id") for task in tasks}
        unexpected = [key for key in grouped if key not in task_ids]
        result = {
            "n_tasks": len(tasks),
            "accepted": sum(check["accepted"] for check in checks),
            "all_accepted": all(check["accepted"] for check in checks) and not unexpected,
            "checks": checks,
            "unexpected_report_ids": unexpected,
            "acceptance_scope": "structured research-task correctness, not customer acceptance",
        }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "mode": args.mode}))
    return 0 if args.mode == "expected" or result["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
