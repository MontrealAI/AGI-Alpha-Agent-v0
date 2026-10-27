# SPDX-License-Identifier: Apache-2.0
"""Preserve original requirements through a bounded, documented source screen."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
SEASONS = {"early", "mid", "late"}
HABITATS = {"dry", "mesic", "wet"}
LIMIT = 128


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def identity(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def integer(value: Any, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= 10**9


def text(value: Any) -> bool:
    return type(value) is str and 0 < len(value) <= 2000


def validate(task: Any, catalog: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(task, dict) or not isinstance(catalog, dict):
        return ["task and catalog must be objects"]
    try:
        if len(canonical([task, catalog])) > 2_000_000:
            return ["input exceeds the declared byte budget"]
    except (TypeError, ValueError, RecursionError):
        return ["input must be finite bounded JSON"]
    for key in ("id", "purpose", "region"):
        if not text(task.get(key)):
            errors.append(f"invalid {key}")
    if not text(task.get("habitat")) or task["habitat"] not in HABITATS:
        errors.append("invalid habitat")
    if not text(task.get("resource_mode")) or task["resource_mode"] not in {"flower", "nectar"}:
        errors.append("invalid resource_mode")
    periods = task.get("required_seasons")
    if not isinstance(periods, list) or not periods or any(not text(s) or s not in SEASONS for s in periods):
        errors.append("invalid required_seasons")
    elif len(periods) != len(set(periods)):
        errors.append("duplicate required_seasons")
    if not integer(task.get("min_species_per_season"), 1):
        errors.append("invalid min_species_per_season")
    if not integer(task.get("delivery_week")):
        errors.append("invalid delivery_week")
    if task.get("required_host") is not None and not text(task["required_host"]):
        errors.append("invalid required_host")
    if not integer(task.get("quoted_price_cents", 0)):
        errors.append("invalid quoted_price_cents")
    for key in ("rows", "lots"):
        values = task.get(key)
        if not isinstance(values, list) or len(values) > LIMIT:
            errors.append(f"invalid {key}")
            continue
        seen: set[str] = set()
        for i, row in enumerate(values):
            if not isinstance(row, dict):
                errors.append(f"invalid {key}[{i}]")
                continue
            for field in ("taxon", "unit") if key == "rows" else ("id", "taxon", "unit"):
                if not text(row.get(field)):
                    errors.append(f"invalid {key}[{i}].{field}")
            if not integer(row.get("quantity"), 1 if key == "rows" else 0):
                errors.append(f"invalid {key}[{i}].quantity")
            if key == "rows" and row.get("lot_id") is not None and row.get("lot_id") != "" and not text(row["lot_id"]):
                errors.append(f"invalid rows[{i}].lot_id")
            if key == "lots":
                lot_id = row.get("id")
                if isinstance(lot_id, str):
                    if lot_id in seen:
                        errors.append("duplicate lot id")
                    seen.add(lot_id)
                if row.get("available_week") is not None and not integer(row.get("available_week")):
                    errors.append(f"invalid lots[{i}].available_week")
                if row.get("region") is not None and row.get("region") != "" and not text(row["region"]):
                    errors.append(f"invalid lots[{i}].region")
                if not text(row.get("evidence_status")) or row["evidence_status"] not in {
                    "verified",
                    "unknown",
                    "failed",
                }:
                    errors.append(f"invalid lots[{i}].evidence_status")
    taxa = catalog.get("taxa")
    if not isinstance(taxa, list) or len(taxa) > LIMIT:
        errors.append("invalid catalog taxa")
    else:
        seen = set()
        for i, taxon in enumerate(taxa):
            if not isinstance(taxon, dict):
                errors.append(f"invalid taxon[{i}]")
                continue
            if not text(taxon.get("id")):
                errors.append(f"invalid taxon[{i}].id")
            elif taxon["id"] in seen:
                errors.append("duplicate taxon id")
            else:
                seen.add(taxon["id"])
            for key, permitted in (("seasons", SEASONS), ("water", HABITATS)):
                seq = taxon.get(key)
                if (
                    not isinstance(seq, list)
                    or any(not text(v) or v not in permitted for v in seq)
                    or len(seq) != len(set(seq))
                ):
                    errors.append(f"invalid taxon[{i}].{key}")
            if not isinstance(taxon.get("hosts"), list) or any(not text(h) for h in taxon["hosts"]):
                errors.append(f"invalid taxon[{i}].hosts")
            if taxon.get("nectar") is not None and type(taxon.get("nectar")) is not bool:
                errors.append(f"invalid taxon[{i}].nectar")
    return sorted(set(errors))


def _source_reasons(taxon: dict[str, Any] | None, task: dict[str, Any]) -> list[str]:
    if taxon is None:
        return ["unknown_taxon"]
    reasons = []
    if task["habitat"] not in taxon["water"]:
        reasons.append("habitat_not_documented")
    if task["resource_mode"] == "nectar":
        if taxon["nectar"] is False:
            reasons.append("pollen_only")
        elif taxon["nectar"] is not True:
            reasons.append("nectar_unknown")
    return reasons


def _coverage(ids: set[str], taxa: dict[str, dict[str, Any]], task: dict[str, Any]) -> dict[str, Any]:
    result = {}
    minimum = task["min_species_per_season"]
    for season in task["required_seasons"]:
        supported = sorted(t for t in ids if season in taxa[t]["seasons"])
        result[season] = {
            "taxa": supported,
            "count": len(supported),
            "required": minimum,
            "gap": max(0, minimum - len(supported)),
        }
    return result


def audit(task: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    """Return documentary qualification, explicit gaps and an unchanged purpose."""
    errors = validate(task, catalog)
    base: dict[str, Any] = {
        "schema": "agialpha.obligation-report.v1",
        "capability_version": VERSION,
        "task_id": task.get("id") if isinstance(task, dict) else None,
        "scope": "documented-source-screen",
        "original_purpose": task.get("purpose") if isinstance(task, dict) else None,
        "input_errors": errors,
        "source_coverage": {},
        "supply_coverage": {},
        "host": {
            "required": task.get("required_host") if isinstance(task, dict) else None,
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
        return base
    base["mission_digest"] = identity(task)
    base["catalog_digest"] = identity(catalog)
    taxa = {t["id"]: t for t in catalog["taxa"]}
    lots = {lot["id"]: lot for lot in task["lots"]}
    demand: dict[str, int] = defaultdict(int)
    for row in task["rows"]:
        lot = lots.get(row.get("lot_id"))
        if lot is not None and lot["unit"] == row["unit"]:
            demand[row["lot_id"]] += row["quantity"]
    source_ids, supply_ids = set(), set()
    blockers: list[dict[str, Any]] = []
    for index, row in enumerate(task["rows"]):
        taxon = taxa.get(row["taxon"])
        reasons = _source_reasons(taxon, task)
        if not reasons:
            source_ids.add(row["taxon"])
        lot_id = row.get("lot_id")
        lot = lots.get(lot_id)
        if lot is None:
            reasons.append("missing_lot" if not lot_id else "unknown_lot")
        else:
            if lot["taxon"] != row["taxon"]:
                reasons.append("lot_taxon_mismatch")
            if lot["evidence_status"] == "unknown":
                reasons.append("lot_evidence_unknown")
            elif lot["evidence_status"] == "failed":
                reasons.append("lot_evidence_failed")
            if not lot.get("region"):
                reasons.append("region_unknown")
            elif lot["region"] != task["region"]:
                reasons.append("region_mismatch")
            if lot.get("available_week") is None:
                reasons.append("availability_unknown")
            elif lot["available_week"] > task["delivery_week"]:
                reasons.append("unavailable_by_deadline")
            if lot["unit"] != row["unit"]:
                reasons.append("unit_mismatch")
            if row["unit"] == lot["unit"] and demand[lot_id] > lot["quantity"]:
                reasons.append("insufficient_lot_quantity")
        if not reasons:
            supply_ids.add(row["taxon"])
        blockers.extend({"row": index, "code": code, "lot_id": lot_id} for code in sorted(set(reasons)))
    source_coverage, supply_coverage = _coverage(source_ids, taxa, task), _coverage(supply_ids, taxa, task)
    required_host = task.get("required_host")
    source_hosts = sorted(t for t in source_ids if required_host in taxa[t]["hosts"]) if required_host else []
    supply_hosts = sorted(t for t in supply_ids if required_host in taxa[t]["hosts"]) if required_host else []
    host_ok = required_host is None or bool(supply_hosts)
    unmet = [
        {
            "kind": "seasonal",
            "season": season,
            "required": row["required"],
            "qualified": row["count"],
            "gap": row["gap"],
        }
        for season, row in supply_coverage.items()
        if row["gap"] > 0
    ]
    if not host_ok:
        unmet.append({"kind": "host", "host": required_host})
    base.update(
        {
            "source_coverage": source_coverage,
            "supply_coverage": supply_coverage,
            "host": {
                "required": required_host,
                "source_taxa": source_hosts,
                "supply_taxa": supply_hosts,
                "pass": host_ok,
            },
            "blockers": blockers,
            "original_unmet_obligations": unmet,
            "source_screen_pass": not unmet and not blockers,
            "evidence_limit": "Correct documentary screen does not establish ecological performance, current market supply or commercial acceptance.",
        }
    )
    return base


def structural_repairs(task: dict[str, Any], catalog: dict[str, Any], max_additions: int = 3) -> dict[str, Any]:
    """Enumerate source-only additions without inventing inventory or approval."""
    report = audit(task, catalog)
    if report["input_errors"]:
        return {"status": "invalid-input", "plans": [], "production_authorized": False}
    if type(max_additions) is not int or not 0 <= max_additions <= 4:
        raise ValueError("max_additions must be an integer from zero to four")
    taxa = {t["id"]: t for t in catalog["taxa"]}
    present = {t for t in taxa if any(row["taxon"] == t for row in task["rows"]) and not _source_reasons(taxa[t], task)}
    candidates = sorted(t for t in taxa if t not in present and not _source_reasons(taxa[t], task))
    host = task.get("required_host")
    tried = 0
    for size in range(max_additions + 1):
        plans = []
        for addition in itertools.combinations(candidates, size):
            tried += 1
            if tried > 10_000:
                return {
                    "status": "search-budget-exhausted",
                    "plans": [],
                    "combinations_examined": 10_000,
                    "supply_qualified": False,
                    "production_authorized": False,
                }
            ids = present | set(addition)
            coverage = _coverage(ids, taxa, task)
            if any(c["gap"] for c in coverage.values()):
                continue
            if host and not any(host in taxa[t]["hosts"] for t in ids):
                continue
            plans.append(list(addition))
        if plans:
            return {
                "status": "source-only-candidates",
                "plans": plans,
                "minimum_additions": size,
                "combinations_examined": tried,
                "supply_qualified": False,
                "production_authorized": False,
                "required_next_evidence": [
                    "site suitability",
                    "qualified lot provenance",
                    "production feasibility",
                    "current price and capacity",
                    "counterparty acceptance",
                    "cash timing",
                ],
            }
    return {
        "status": "no-supported-repair-in-declared-catalog",
        "plans": [],
        "combinations_examined": tried,
        "supply_qualified": False,
        "production_authorized": False,
    }


def purchase_projection(task: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose the deliberate information loss of a purchase-only record."""
    return [{k: row[k] for k in ("taxon", "quantity", "unit")} for row in task["rows"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repairs", action="store_true")
    args = parser.parse_args()
    task, catalog = json.loads(args.task.read_text()), json.loads(args.catalog.read_text())
    report = audit(task, catalog)
    if args.repairs:
        report["structural_repair_search"] = structural_repairs(task, catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "task_id": report["task_id"],
                "source_screen_pass": report["source_screen_pass"],
                "blockers": len(report["blockers"]),
                "unmet": len(report["original_unmet_obligations"]),
            }
        )
    )


if __name__ == "__main__":
    main()
