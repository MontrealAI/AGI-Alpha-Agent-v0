# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections
import csv
import hashlib
import json
import random
import sqlite3
from pathlib import Path
from typing import Any

import geopandas as gpd
import pyogrio
import shapely

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def norm(value: Any) -> str:
    return "" if value is None else str(value).strip()


def main() -> None:
    parks_source = json.loads((ROOT / "data/parks.geojson").read_text())
    assets_source = json.loads((ROOT / "data/facilities.geojson").read_text())
    parks = gpd.read_file(ROOT / "data/parks.geojson").to_crs(32188)
    assets = gpd.read_file(ROOT / "data/facilities.geojson").to_crs(32188)
    park_ids = [norm(f["properties"].get("NUM_INDEX")) for f in parks_source["features"]]
    park_objects = [norm(f["properties"].get("OBJECTID")) for f in parks_source["features"]]
    asset_objects = [norm(f["properties"].get("OBJECTID")) for f in assets_source["features"]]
    pc, ac = collections.Counter(park_objects), collections.Counter(asset_objects)
    valid = [
        g is not None
        and not g.is_empty
        and g.is_valid
        and g.geom_type in ("Polygon", "MultiPolygon")
        and bool(park_ids[i])
        and bool(park_objects[i])
        and pc[park_objects[i]] == 1
        for i, g in enumerate(parks.geometry)
    ]
    logical = set(park_ids) - {""}
    invalid = {park_ids[i] for i, v in enumerate(valid) if not v}
    park_geometries = [g for i, g in enumerate(parks.geometry) if valid[i]]
    geometric_ids = [p for i, p in enumerate(park_ids) if valid[i]]
    development = json.loads((ROOT / "technical/partition_freeze.json").read_text())["development_borough"]
    pool = [i for i, f in enumerate(assets_source["features"]) if norm(f["properties"].get("ARROND")) != development]
    selection = sorted(random.Random(2026102752).sample(pool, 128))
    with (ROOT / "technical/delivery/reconciliation.csv").open(newline="", encoding="utf-8") as stream:
        delivered = {r["source_row"]: r for r in csv.DictReader(stream)}
    outcomes = []
    for i in selection:
        original = assets_source["features"][i]
        declared = norm(original["properties"].get("INDEX_PARC"))
        geometry = assets.geometry.iloc[i]
        bits = shapely.covers(park_geometries, geometry.representative_point())
        candidates = sorted({park for park, inside in zip(geometric_ids, bits) if inside})
        if (
            geometry is None
            or geometry.is_empty
            or not geometry.is_valid
            or not asset_objects[i]
            or ac[asset_objects[i]] != 1
        ):
            expected = "invalid_source"
        elif len(candidates) > 1:
            expected = "ambiguous_geometry"
        elif declared and candidates == [declared]:
            expected = "confirmed"
        elif declared and declared not in logical:
            expected = "unknown_declared_park"
        elif declared and declared in invalid:
            expected = "declared_park_has_source_exception"
        elif not declared and len(candidates) == 1:
            expected = "geometry_only_suggestion"
        elif declared and len(candidates) == 1:
            expected = "identifier_geometry_conflict"
        elif declared:
            expected = "declared_without_geometric_support"
        else:
            expected = "unassigned"
        row_id = f"facilities:{i:06d}"
        actual = delivered[row_id]
        outcomes.append(
            {
                "source_row": row_id,
                "expected_status": expected,
                "actual_status": actual["status"],
                "expected_candidates": candidates,
                "actual_candidates": json.loads(actual["geometric_candidates_json"]),
                "passed": expected == actual["status"]
                and candidates == json.loads(actual["geometric_candidates_json"]),
            }
        )
    gpkg = ROOT / "technical/delivery/montreal_asset_onboarding.gpkg"
    reopens = {}
    for layer in ("parks", "facilities"):
        data = pyogrio.read_dataframe(gpkg, layer=layer)
        reopens[layer] = {
            "count": len(data),
            "crs_epsg": data.crs.to_epsg(),
            "unique_source_rows": data.source_row.nunique(),
            "geometry_types": data.geom_type.value_counts(dropna=False).to_dict(),
        }
    with sqlite3.connect(gpkg) as cx:
        sql = {
            "integrity": cx.execute("PRAGMA integrity_check").fetchone()[0],
            "parks": cx.execute("SELECT count(*) FROM parks").fetchone()[0],
            "facilities": cx.execute("SELECT count(*) FROM facilities").fetchone()[0],
            "exceptions": cx.execute("SELECT count(*) FROM exception_queue").fetchone()[0],
            "unqueued_facility_exceptions": cx.execute(
                "SELECT count(*) FROM facilities f LEFT JOIN exception_queue e USING(source_row) WHERE f.status!='confirmed' AND e.source_row IS NULL"
            ).fetchone()[0],
            "confirmed_id_disagreement": cx.execute(
                "SELECT count(*) FROM facilities WHERE status='confirmed' AND confirmed_park!=declared_park"
            ).fetchone()[0],
        }
    reader_pass = (
        sql["integrity"] == "ok"
        and sql["parks"] == len(parks) == reopens["parks"]["count"]
        and sql["facilities"] == len(assets) == reopens["facilities"]["count"]
        and sql["unqueued_facility_exceptions"] == 0
        and sql["confirmed_id_disagreement"] == 0
        and all(v["crs_epsg"] == 32188 and v["unique_source_rows"] == v["count"] for v in reopens.values())
    )
    receipt = {
        "scope": "Competent conventional implementation with the same formulation; independent code/read path, shared Shapely/PROJ libraries; no claim of independent geodetic truth or causal model advantage",
        "instrument_imported": False,
        "sample_seed": 2026102752,
        "sample_count": 128,
        "eligible_nondevelopment_rows": len(pool),
        "matched_decisions": sum(r["passed"] for r in outcomes),
        "outcomes": outcomes,
        "native_reopen": {"gdal": reopens, "sqlite": sql, "passed": reader_pass},
        "source_hashes": {
            n: hashlib.sha256((ROOT / "data" / n).read_bytes()).hexdigest()
            for n in ("parks.geojson", "facilities.geojson")
        },
        "instrument_sha256": hashlib.sha256((ROOT / "src/geodelivery.py").read_bytes()).hexdigest(),
        "control_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "passed": all(r["passed"] for r in outcomes) and reader_pass,
    }
    (OUT / "public_control_results.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "matched": receipt["matched_decisions"],
                "sample": 128,
                "native_reopen": receipt["native_reopen"],
                "passed": receipt["passed"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
