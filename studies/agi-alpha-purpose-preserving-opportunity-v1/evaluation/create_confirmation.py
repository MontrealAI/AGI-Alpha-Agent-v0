# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def proposal(packet: str, number: int, taxa: list[str], minimum: int = 1) -> dict[str, Any]:
    wet = packet == "B"
    identifier = f"{packet}-20261027-{number:02d}"
    region = "fictional-provenance-wetland-B" if wet else "fictional-provenance-upland-A"
    purpose = (
        "Audit documented flowering coverage and a monarch larval host for the declared wet planting context. "
        if wet
        else "Audit documented flowering coverage for the declared dry planting context. "
    )
    purpose += (
        "Retain every requested seasonal and host obligation when a supplied proposal cannot meet it. "
        "Every proposed row must satisfy the requested resource evidence class. "
        "This is a research source screen using fictional lots, not verified planting or field delivery."
    )
    task = {
        "id": identifier,
        "purpose": purpose,
        "habitat": "wet" if wet else "dry",
        "resource_mode": "flower",
        "required_seasons": ["early", "mid", "late"],
        "min_species_per_season": minimum,
        "required_host": "monarch" if wet else None,
        "region": region,
        "delivery_week": 8,
        "rows": [],
        "lots": [],
        "quoted_price_cents": 120000 + 1100 * number,
    }
    for i, taxon in enumerate(taxa):
        lot_id = f"{identifier}-L{i + 1:02d}"
        task["rows"].append({"taxon": taxon, "quantity": 10, "unit": "g", "lot_id": lot_id})
        task["lots"].append(
            {
                "id": lot_id,
                "taxon": taxon,
                "quantity": 20,
                "unit": "g",
                "region": region,
                "available_week": 5,
                "evidence_status": "verified",
            }
        )
    return task


def build() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    a: list[dict[str, Any]] = []
    b: list[dict[str, Any]] = []
    rationale: dict[str, str] = {}

    def keep(task: dict[str, Any], description: str) -> None:
        (a if task["id"].startswith("A-") else b).append(task)
        rationale[task["id"]] = description

    t = proposal("A", 1, ["coreopsis_lanceolata", "oligoneuron_rigidum"])
    keep(t, "Positive: one documented taxon covers early and mid; another covers late.")
    t = proposal("A", 2, ["zizia_aurea", "dalea_purpurea", "symphyotrichum_laeve"])
    t["delivery_week"] = 0
    t["quoted_price_cents"] = 0
    for lot in t["lots"]:
        lot["available_week"] = 0
        lot["quantity"] = 10
    keep(t, "Positive boundary: zero reference week, exact deadline and stock, nonnegative zero quote.")
    t = proposal(
        "A", 3,
        ["zizia_aurea", "coreopsis_lanceolata", "monarda_fistulosa", "liatris_ligulistylis", "oligoneuron_rigidum"],
        2,
    )
    keep(t, "Positive: minimum two distinct taxa per requested season, unequal surplus across seasons.")
    t = proposal("A", 4, ["coreopsis_lanceolata", "oligoneuron_rigidum"])
    t["rows"][0]["quantity"] = 4
    extra = copy.deepcopy(t["rows"][0])
    extra["quantity"] = 6
    t["rows"].insert(1, extra)
    t["lots"][0]["quantity"] = 10
    keep(t, "Positive: duplicate taxon/lot rows consume aggregate stock but count as one species.")
    t = proposal("A", 5, ["asclepias_tuberosa", "oligoneuron_rigidum"])
    keep(t, "Valid negative: the proposal leaves early flowering demand unmet despite valid supplied lots.")
    t = proposal("A", 6, ["baptisia_alba", "monarda_fistulosa", "symphyotrichum_laeve"])
    keep(t, "Valid negative: an early species lacks documented dry-context support; no suitability inference.")
    t = proposal("A", 7, ["zizia_aurea", "dalea_purpurea", "oligoneuron_rigidum"])
    t["resource_mode"] = "nectar"
    t["purpose"] = t["purpose"].replace("flowering coverage", "nectar-evidence coverage for every proposed taxon")
    keep(t, "Valid negative: all nectar fields are null; no nectar support is invented from flowering.")
    t = proposal("A", 8, ["tradescantia_ohiensis", "symphyotrichum_laeve"])
    t["resource_mode"] = "nectar"
    t["purpose"] = t["purpose"].replace("flowering coverage", "nectar-evidence coverage for every proposed taxon")
    keep(t, "Valid negative: explicit pollen-only evidence and unknown nectar are distinct findings.")
    t = proposal("A", 9, ["coreopsis_lanceolata", "oligoneuron_rigidum"])
    t["rows"][0]["quantity"] = 6
    t["rows"].insert(1, copy.deepcopy(t["rows"][0]))
    t["lots"][0]["quantity"] = 10
    keep(t, "Valid negative: each duplicate row is below stock but their shared-lot total is above stock.")
    t = proposal("A", 10, ["unresolved_taxon_42", "coreopsis_lanceolata", "oligoneuron_rigidum"])
    t["rows"][1]["lot_id"] = "A-20261027-10-NOT-LISTED"
    t["rows"][2]["lot_id"] = None
    keep(t, "Valid negative: unknown taxon, unknown lot, and missing lot remain separate audit findings.")
    t = proposal("A", 11, ["coreopsis_lanceolata", "oligoneuron_rigidum"])
    t["rows"][0]["quantity"] = 10.0
    keep(t, "Invalid input: integral-looking JSON float must not be accepted as integer quantity.")
    t = proposal("A", 12, ["coreopsis_lanceolata", "oligoneuron_rigidum"])
    t["rows"][0]["quantity"] = True
    t["lots"].append(copy.deepcopy(t["lots"][0]))
    keep(t, "Invalid input: boolean quantity and ambiguous duplicate lot IDs must not pass.")

    standard_b = ["zizia_aurea", "asclepias_incarnata", "helenium_autumnale"]
    t = proposal("B", 1, standard_b)
    keep(t, "Positive transfer: wet context, documented monarch host, and different required provenance.")
    t = proposal(
        "B", 2,
        ["zizia_aurea", "tradescantia_ohiensis", "asclepias_incarnata", "eupatorium_perfoliatum",
         "symphyotrichum_novae_angliae", "helenium_autumnale"],
        2,
    )
    keep(t, "Positive: pollen-only taxon qualifies for flower mode; two taxa per season and host are required.")
    t = proposal("B", 3, ["zizia_aurea", "asclepias_incarnata", "asclepias_incarnata", "helenium_autumnale"])
    keep(t, "Positive: same host taxon in different valid lots does not inflate seasonal or host diversity.")
    t = proposal("B", 4, ["asclepias_incarnata", "eupatorium_perfoliatum"])
    t["required_seasons"] = ["late", "mid"]
    t["purpose"] += " Only the explicitly requested mid and late seasons are within this task contract."
    t["delivery_week"] = 7
    for lot in t["lots"]:
        lot["available_week"] = 7
    keep(t, "Positive: noncanonical season order, a subset of seasons, and exact delivery deadline.")
    t = proposal("B", 5, ["zizia_aurea", "monarda_fistulosa", "helenium_autumnale"])
    keep(t, "Valid negative: flowering coverage survives a substitution but the monarch-host obligation does not.")
    t = proposal("B", 6, ["zizia_aurea", "asclepias_tuberosa", "monarda_fistulosa", "helenium_autumnale"])
    keep(t, "Valid negative: substitute is a documented host elsewhere but lacks the requested wet context.")
    t = proposal("B", 7, standard_b)
    t["lots"][0]["evidence_status"] = "unknown"
    t["lots"][1]["evidence_status"] = "failed"
    keep(t, "Valid negative: source coverage remains visible while unknown/failed lot evidence blocks supply.")
    t = proposal("B", 8, standard_b)
    t["lots"][0]["region"] = None
    t["lots"][1]["region"] = "fictional-provenance-upland-A"
    t["lots"][1]["available_week"] = None
    t["lots"][2]["available_week"] = t["delivery_week"] + 1
    keep(t, "Valid negative: unknown provenance, mismatched region, missing date, and delay are all preserved.")
    t = proposal("B", 9, standard_b)
    t["rows"][0]["unit"] = "kg"
    t["lots"][1]["taxon"] = "monarda_fistulosa"
    keep(t, "Valid negative: no unauthorized unit conversion and no silent taxon substitution in a lot.")
    t = proposal("B", 10, [])
    keep(t, "Valid negative: an empty order does not erase original flowering or host demand.")
    t = proposal("B", 11, standard_b)
    t["lots"][1]["quantity"] = 0
    keep(t, "Valid negative: zero available stock is valid data, not missing data; host supply fails.")
    t = proposal("B", 12, standard_b)
    t["rows"][0]["quantity"] = 0
    t["delivery_week"] = -1
    keep(t, "Invalid input: zero requested quantity and a negative delivery week cannot pass.")
    return a, b, rationale


def main() -> None:
    freeze = json.loads((ROOT / "METHOD_FREEZE.json").read_text())
    for relative, item in freeze["files"].items():
        if digest(ROOT / relative) != item["sha256"]:
            raise RuntimeError(f"Frozen file changed before confirmation creation: {relative}")
    for file in (HERE / "packets" / "packet_a.json", HERE / "packets" / "packet_b.json"):
        if file.exists():
            raise RuntimeError("Confirmation packets already exist; refusing to regenerate")
    spec = importlib.util.spec_from_file_location("independent_oracle", HERE / "oracle.py")
    assert spec is not None and spec.loader is not None
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    catalog = json.loads((ROOT / "data/catalog.json").read_text())
    a, b, rationale = build()
    created = datetime.now(timezone.utc).isoformat()
    expected_a = [oracle.reference_report(task, catalog) for task in a]
    expected_b = [oracle.reference_report(task, catalog) for task in b]
    metadata = {
        "evidence_class": "researcher_constructed_confirmation_fixtures",
        "source_taxa": "data/catalog.json",
        "lots_prices_dates_regions_and_missions": "fictional; not observations of customers or inventory",
        "source_scope": "guide-documented contexts, not exclusive botanical suitability",
        "reported_status_verified": "fixture value only; not live authentication or certification",
    }
    write(HERE / "packets/packet_a.json", {"packet": "A", "metadata": metadata, "tasks": a})
    write(HERE / "packets/packet_b.json", {"packet": "B", "metadata": metadata, "tasks": b})
    write(HERE / "protected/expected_a.json", {"reports": expected_a})
    write(HERE / "protected/expected_b.json", {"reports": expected_b})
    write(
        HERE / "protected/case_provenance.json",
        {
            "created_at_utc": created,
            "method_freeze_at_utc": freeze["frozen_at_utc"],
            "construction": "independent evaluator wrote cases after method freeze without inspecting core code",
            "selection": "purposeful boundary/failure coverage, not random sampling or a natural population",
            "no_post_confirmation_tuning": True,
            "rationale": rationale,
        },
    )
    paths = [
        HERE / "create_confirmation.py",
        HERE / "packets/packet_a.json",
        HERE / "packets/packet_b.json",
        HERE / "protected/expected_a.json",
        HERE / "protected/expected_b.json",
        HERE / "protected/case_provenance.json",
    ]
    manifest = {
        "schema": "agialpha.protected-confirmation.v1",
        "created_at_utc": created,
        "method_freeze_at_utc": freeze["frozen_at_utc"],
        "method_freeze_sha256": digest(ROOT / "METHOD_FREEZE.json"),
        "catalog_sha256": digest(ROOT / "data/catalog.json"),
        "oracle_sha256": digest(HERE / "oracle.py"),
        "case_count": {"A": len(a), "B": len(b)},
        "files": {str(p.relative_to(ROOT)): {"sha256": digest(p), "bytes": p.stat().st_size} for p in paths},
        "protection": "procedural isolation: trial agents receive packets and approved instructions only; shared filesystem is not a security boundary",
        "instructions_to_trial_agents": "Do not read evaluation/protected, create_confirmation.py, oracle.py, result files, or other condition outputs.",
        "no_core_results_inspected": True,
    }
    write(HERE / "CONFIRMATION_FREEZE.json", manifest)
    summary = {
        "created_at_utc": created,
        "counts": {"A": len(a), "B": len(b)},
        "expected_source_screen_positive": {"A": sum(r["source_screen_pass"] for r in expected_a),
                                            "B": sum(r["source_screen_pass"] for r in expected_b)},
        "malformed_inputs": {"A": sum(bool(r["input_errors"]) for r in expected_a),
                             "B": sum(bool(r["input_errors"]) for r in expected_b)},
        "manifest": str(HERE / "CONFIRMATION_FREEZE.json"),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
