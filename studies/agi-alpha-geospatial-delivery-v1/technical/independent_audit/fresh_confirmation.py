# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Point, Polygon, mapping

from audit import ROOT, OUT, collection, feature, poly, X, Y


def fixtures(seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    cases = []
    for index in range(6):
        dx, dy, size = rng.randrange(500, 2000), rng.randrange(500, 2000), rng.randrange(20, 80)
        a = feature("park-a", "A", poly(dx, dy, size, size), True)
        b = feature("park-b", "B", poly(dx + size, dy, size, size), True)
        c = feature("park-c", "C", poly(dx + size / 2, dy, size, size), True)
        cases.extend(
            [
                {
                    "id": f"interior-{index}",
                    "parks": collection([a, b]),
                    "assets": collection([feature("asset", "A", Point(X + dx + size / 3, Y + dy + size / 3))]),
                    "status": "confirmed",
                    "candidates": ["A"],
                },
                {
                    "id": f"boundary-{index}",
                    "parks": collection([a, b]),
                    "assets": collection([feature("asset", "A", Point(X + dx + size, Y + dy + size / 3))]),
                    "status": "ambiguous_geometry",
                    "candidates": ["A", "B"],
                },
                {
                    "id": f"overlap-{index}",
                    "parks": collection([a, c]),
                    "assets": collection([feature("asset", "A", Point(X + dx + 3 * size / 4, Y + dy + size / 3))]),
                    "status": "ambiguous_geometry",
                    "candidates": ["A", "C"],
                },
                {
                    "id": f"unknown-id-{index}",
                    "parks": collection([a, b]),
                    "assets": collection(
                        [feature("asset", f"missing-{index}", Point(X + dx + size / 3, Y + dy + size / 3))]
                    ),
                    "status": "unknown_declared_park",
                    "candidates": ["A"],
                },
            ]
        )
        hole = poly(dx + size / 3, dy + size / 3, size / 3, size / 3)
        donut = Polygon(poly(dx, dy, size, size).exterior.coords, [hole.exterior.coords])
        cases.append(
            {
                "id": f"hole-{index}",
                "parks": collection([feature("park-d", "D", donut, True)]),
                "assets": collection([feature("asset", None, Point(X + dx + size / 2, Y + dy + size / 2))]),
                "status": "unassigned",
                "candidates": [],
            }
        )
        line = LineString([(X + dx, Y + dy), (X + dx + size, Y + dy)])
        cases.append(
            {
                "id": f"park-line-{index}",
                "parks": collection([feature("park-line", "L", line, True)]),
                "assets": collection([feature("asset", "L", Point(X + dx + size / 2, Y + dy))]),
                "status": "declared_park_has_source_exception",
                "candidates": [],
                "park_status": "source_exception",
            }
        )
        missing = feature("asset", "A", Point(X + dx + size / 2, Y + dy + size / 2))
        missing["properties"] = None
        cases.append(
            {
                "id": f"null-properties-{index}",
                "parks": collection([a]),
                "assets": collection([missing]),
                "status": "invalid_source",
                "candidates": ["A"],
            }
        )
        lat, lon = 45.5 + rng.uniform(-0.03, 0.03), -73.57 + rng.uniform(-0.03, 0.03)
        swapped = Polygon(
            [
                (lat - 0.001, lon - 0.001),
                (lat + 0.001, lon - 0.001),
                (lat + 0.001, lon + 0.001),
                (lat - 0.001, lon + 0.001),
            ]
        )
        cases.append(
            {
                "id": f"shared-axis-swap-{index}",
                "parks": collection([feature("park-wrong", "W", swapped, True)], "EPSG:4326"),
                "assets": collection([feature("asset", "W", Point(lat, lon))], "EPSG:4326"),
                "status": "invalid_source",
                "candidates": [],
                "park_status": "source_exception",
            }
        )
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--expected-hash", required=True)
    parser.add_argument("--seed", type=int, default=2026102751)
    args = parser.parse_args()
    source = ROOT / "src" / "geodelivery.py"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != args.expected_hash:
        raise RuntimeError(f"Freeze mismatch {source_hash}")
    target = OUT / f"fresh_{args.label}.json"
    if target.exists():
        raise FileExistsError(target)
    freeze = {
        "instrument_sha256": source_hash,
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "seed": args.seed,
        "frozen_before_fixture_generation": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (OUT / f"fresh_freeze_{args.label}.json").write_text(json.dumps(freeze, indent=2) + "\n")
    cases = fixtures(args.seed)
    (OUT / f"fresh_fixtures_{args.label}.json").write_text(json.dumps(cases, indent=2) + "\n")
    spec = importlib.util.spec_from_file_location("fresh_geodelivery", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load frozen source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results = []
    for case in cases:
        try:
            result = module.reconcile(case["parks"], case["assets"])
            row = result["facilities"][0]
            checks = {
                "expected_status": row["status"] == case["status"],
                "expected_candidates": json.loads(row["geometric_candidates_json"]) == case["candidates"],
                "conserved_rows": len(result["facilities"]) == 1
                and len(result["parks"]) == len(case["parks"]["features"]),
                "exception_complete": all(module.acceptance_checks(result, len(case["parks"]["features"]), 1).values()),
            }
            if "park_status" in case:
                checks["expected_park_disposition"] = result["parks"][0]["status"] == case["park_status"]
            results.append(
                {
                    "id": case["id"],
                    "passed": all(checks.values()),
                    "checks": checks,
                    "actual_status": row["status"],
                    "reasons": row["reasons"],
                }
            )
        except Exception as exc:
            results.append({"id": case["id"], "passed": False, "error": f"{type(exc).__name__}: {exc}"})
    output = {
        "scope": "Fresh authored synthetic missions after correction freeze; same research team, not outside validation or frontier-model trial",
        "freeze": freeze,
        "cases": results,
        "accepted_cases": sum(x["passed"] for x in results),
        "case_count": len(results),
        "passed": all(x["passed"] for x in results),
    }
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "accepted": output["accepted_cases"],
                "total": len(results),
                "failed": [x for x in results if not x["passed"]],
                "output": str(target),
            }
        )
    )


if __name__ == "__main__":
    main()
