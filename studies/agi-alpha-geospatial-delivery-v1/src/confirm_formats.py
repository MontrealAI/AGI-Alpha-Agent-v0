# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

from geodelivery import reconcile
from wkt_adapter import adapt


def semantic(result: dict[str, Any]) -> list[dict[str, Any]]:
    fields = ("source_id", "declared_park", "confirmed_park", "suggested_park", "status", "geometric_candidates_json")
    return [{name: row[name] for name in fields} for row in result["facilities"]]


def run(destination: Path, seed: int = 2026102703) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    results = []
    for case in range(32):
        left, bottom = rng.uniform(-73.9, -73.5), rng.uniform(45.45, 45.6)
        parks = {"type": "FeatureCollection", "features": []}
        for k, offset in [("0001", 0.0), ("0002", 0.08)]:
            x = left + offset
            polygon = {
                "type": "Polygon",
                "coordinates": [
                    [[x, bottom], [x + 0.02, bottom], [x + 0.02, bottom + 0.02], [x, bottom + 0.02], [x, bottom]]
                ],
            }
            parks["features"].append(
                {"type": "Feature", "properties": {"OBJECTID": k, "NUM_INDEX": k}, "geometry": polygon}
            )
        assets = {"type": "FeatureCollection", "features": []}
        for i in range(8):
            point = [left + rng.uniform(0.004, 0.016), bottom + rng.uniform(0.004, 0.016)]
            ref = "0001"
            if i == 1:
                ref = "0002"
            elif i == 2:
                ref = ""
            elif i == 3:
                ref = "1"
            elif i == 4:
                point = [left + 0.2, bottom + 0.2]
            elif i == 5:
                point[0] += 0.08
                ref = "0002"
            elif i == 7:
                point = [left, bottom]
            oid = "5" if i == 6 and case % 4 == 0 else str(i)
            assets["features"].append(
                {
                    "type": "Feature",
                    "properties": {
                        "OBJECTID": oid,
                        "ID": f"{case}-{i}",
                        "INDEX_PARC": ref,
                        "ARROND": f"fresh-synthetic-{case}",
                        "NOM": f"Équipement {i}",
                        "TYPE": "practice fixture",
                    },
                    "geometry": {"type": "Point", "coordinates": point},
                }
            )
        crs = ["EPSG:4326", "EPSG:32188", "EPSG:3857"][case % 3]
        delimiter = ";" if case % 2 else ","
        columns = {name: f"field_{case}_{j}" for j, name in enumerate(assets["features"][0]["properties"])}
        binding = {
            "source_crs": crs,
            "delimiter": delimiter,
            "geometry_column": "shape_wkt",
            "property_columns": columns,
        }
        transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        folder = destination / f"case_{case:02d}"
        folder.mkdir(exist_ok=True)
        (folder / "parks.geojson").write_text(json.dumps(parks, ensure_ascii=False) + "\n")
        (folder / "assets.geojson").write_text(json.dumps(assets, ensure_ascii=False) + "\n")
        (folder / "binding.json").write_text(json.dumps(binding, ensure_ascii=False, indent=2) + "\n")
        with (folder / "assets.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=[*columns.values(), "shape_wkt", "unmapped_note"], delimiter=delimiter
            )
            writer.writeheader()
            for feature in assets["features"]:
                row = {target: feature["properties"][source] for source, target in columns.items()}
                row["shape_wkt"] = transform(transformer.transform, shape(feature["geometry"])).wkt
                row["unmapped_note"] = "This original source field must survive normalization."
                writer.writerow(row)
        converted = adapt(folder / "assets.csv", binding)
        expected, observed = semantic(reconcile(parks, assets)), semantic(reconcile(parks, converted))
        mismatches = [
            {"row": i, "geojson": a, "csv_wkt": b} for i, (a, b) in enumerate(zip(expected, observed)) if a != b
        ]
        result = {
            "case": case,
            "source_crs": crs,
            "rows": len(observed),
            "semantic_agreement": not mismatches,
            "mismatches": mismatches,
            "all_extra_fields_preserved": all(
                "unmapped_note" in x["properties"]["_input_fields"] for x in converted["features"]
            ),
            "row_count_preserved": len(converted["features"]) == len(assets["features"]),
        }
        (folder / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        results.append(result)
    report = {
        "seed": seed,
        "missions": len(results),
        "semantic_parity_missions": sum(r["semantic_agreement"] for r in results),
        "complete_row_conservation": all(r["row_count_preserved"] for r in results),
        "unmapped_fields_preserved": all(r["all_extra_fields_preserved"] for r in results),
        "instrument_sha256": hashlib.sha256(Path(__file__).with_name("geodelivery.py").read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(Path(__file__).with_name("wkt_adapter.py").read_bytes()).hexdigest(),
        "scope": "Fresh researcher-generated format missions after instrument freeze; not new customer data or frontier-model trials.",
        "comparison": "Same frozen reconciliation purpose and algorithm; different explicit file/CRS bindings. Ordinary tools with the same adapter can do the same.",
        "results": results,
    }
    (destination / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.out)
    print(json.dumps({k: v for k, v in result.items() if k != "results"}, indent=2))
