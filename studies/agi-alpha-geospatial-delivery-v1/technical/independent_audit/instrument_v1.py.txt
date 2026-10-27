# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pyogrio
import pyproj
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree

TARGET_CRS = "EPSG:32188"
VERSION = "1.0.0"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def identifier(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_collection(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("type") != "FeatureCollection" or not isinstance(value.get("features"), list):
        raise ValueError("Expected a GeoJSON FeatureCollection")
    return value


def declared_crs(collection: dict[str, Any]) -> str:
    entry = collection.get("crs")
    if entry is None:
        return "EPSG:4326"
    if entry.get("type") != "name":
        raise ValueError("Only explicitly named coordinate reference systems are accepted")
    return CRS.from_user_input(entry["properties"]["name"]).to_string()


def projected_geometry(feature: dict[str, Any], source_crs: str) -> tuple[Any, str | None]:
    try:
        geometry = shape(feature.get("geometry"))
        if geometry.is_empty or not geometry.is_valid:
            return None, "invalid_or_empty_geometry"
        bounds = geometry.bounds
        if len(bounds) != 4 or not all(math.isfinite(x) for x in bounds):
            return None, "nonfinite_geometry"
        if CRS.from_user_input(source_crs).is_geographic and not (
            -180 <= bounds[0] <= bounds[2] <= 180 and -90 <= bounds[1] <= bounds[3] <= 90
        ):
            return None, "coordinate_range"
        transformer = Transformer.from_crs(source_crs, TARGET_CRS, always_xy=True)
        projected = transform(transformer.transform, geometry)
        if projected.is_empty or not projected.is_valid or not all(math.isfinite(x) for x in projected.bounds):
            return None, "invalid_transformation"
        return projected, None
    except (ValueError, TypeError, AttributeError, pyproj.exceptions.CRSError, shapely.errors.GEOSException):
        return None, "unreadable_geometry"


def source_record(feature: dict[str, Any], ordinal: int, source_name: str) -> dict[str, Any]:
    props = feature.get("properties") or {}
    return {
        "source_row": f"{source_name}:{ordinal:06d}",
        "source_id": identifier(props.get("OBJECTID")),
        "source_feature_sha256": digest(canonical(feature)),
        "source_properties_json": json.dumps(props, ensure_ascii=False, sort_keys=True),
    }


def reconcile(
    parks: dict[str, Any], facilities: dict[str, Any], selected_boroughs: set[str] | None = None
) -> dict[str, Any]:
    park_crs, facility_crs = declared_crs(parks), declared_crs(facilities)
    park_records, asset_records, exceptions = [], [], []
    valid_geometries, valid_indices = [], []
    logical_ids: set[str] = set()
    invalid_ids: set[str] = set()
    park_counts = collections.Counter(identifier(x.get("properties", {}).get("OBJECTID")) for x in parks["features"])
    asset_counts = collections.Counter(
        identifier(x.get("properties", {}).get("OBJECTID")) for x in facilities["features"]
    )
    for ordinal, feature in enumerate(parks["features"]):
        row = source_record(feature, ordinal, "parks")
        props = feature.get("properties") or {}
        index = identifier(props.get("NUM_INDEX"))
        geometry, error = projected_geometry(feature, park_crs)
        problems = []
        if error:
            problems.append(error)
        if not row["source_id"] or park_counts[row["source_id"]] != 1:
            problems.append("missing_or_duplicate_source_id")
        if not index:
            problems.append("missing_park_index")
        row.update(park_index=index, name=identifier(props.get("Nom")), geometry=geometry)
        row["status"] = "source_exception" if problems else "valid_source_polygon"
        row["reasons"] = ";".join(problems)
        park_records.append(row)
        if index:
            logical_ids.add(index)
        if problems:
            invalid_ids.add(index)
            exceptions.append({"source_row": row["source_row"], "kind": "park", "reason": row["reasons"]})
        else:
            valid_geometries.append(geometry)
            valid_indices.append(index)
    tree = STRtree(valid_geometries)
    for ordinal, feature in enumerate(facilities["features"]):
        props = feature.get("properties") or {}
        borough = identifier(props.get("ARROND"))
        if selected_boroughs is not None and borough not in selected_boroughs:
            continue
        row = source_record(feature, ordinal, "facilities")
        declared = identifier(props.get("INDEX_PARC"))
        geometry, error = projected_geometry(feature, facility_crs)
        row.update(
            borough=borough,
            asset_id=identifier(props.get("ID")),
            name=identifier(props.get("NOM")),
            asset_type=identifier(props.get("TYPE")),
            declared_park=declared,
            geometry=geometry,
        )
        issues = []
        if error:
            issues.append(error)
        if not row["source_id"] or asset_counts[row["source_id"]] != 1:
            issues.append("missing_or_duplicate_source_id")
        candidates = []
        if geometry is not None:
            point = geometry.representative_point()
            candidates = sorted({valid_indices[int(i)] for i in tree.query(point, predicate="intersects")})
        row["geometric_candidates_json"] = json.dumps(candidates, ensure_ascii=False)
        row["confirmed_park"] = ""
        row["suggested_park"] = ""
        if issues:
            status = "invalid_source"
        elif len(candidates) > 1:
            status = "ambiguous_geometry"
        elif declared and candidates == [declared]:
            status = "confirmed"
            row["confirmed_park"] = declared
        elif declared and declared not in logical_ids:
            status = "unknown_declared_park"
            if len(candidates) == 1:
                row["suggested_park"] = candidates[0]
        elif declared and declared in invalid_ids:
            status = "declared_park_has_source_exception"
        elif not declared and len(candidates) == 1:
            status = "geometry_only_suggestion"
            row["suggested_park"] = candidates[0]
        elif declared and len(candidates) == 1:
            status = "identifier_geometry_conflict"
            row["suggested_park"] = candidates[0]
        elif declared:
            status = "declared_without_geometric_support"
        else:
            status = "unassigned"
        row["status"] = status
        row["reasons"] = ";".join(issues) or status
        asset_records.append(row)
        if status != "confirmed":
            exceptions.append({"source_row": row["source_row"], "kind": "facility", "reason": row["reasons"]})
    return {
        "parks": park_records,
        "facilities": asset_records,
        "exceptions": exceptions,
        "summary": {
            "park_source_rows": len(park_records),
            "logical_park_indices": len(logical_ids),
            "facility_source_rows": len(asset_records),
            "park_status_counts": dict(sorted(collections.Counter(x["status"] for x in park_records).items())),
            "facility_status_counts": dict(sorted(collections.Counter(x["status"] for x in asset_records).items())),
            "exception_rows": len(exceptions),
            "source_crs": {"parks": park_crs, "facilities": facility_crs},
            "target_crs": TARGET_CRS,
            "axis_order": "always_xy: longitude/easting, latitude/northing",
        },
    }


def serializable_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in row.items() if k != "geometry"} for row in records]


def reconciliation_digest(result: dict[str, Any]) -> str:
    return digest(canonical(serializable_records(result["facilities"])))


def acceptance_checks(result: dict[str, Any], source_parks: int, source_assets: int) -> dict[str, bool]:
    facilities, parks, exceptions = result["facilities"], result["parks"], result["exceptions"]
    exception_keys = {row["source_row"] for row in exceptions}
    rows = parks + facilities
    return {
        "all_parks_preserved": len(parks) == source_parks,
        "all_selected_facilities_preserved": len(facilities) == source_assets,
        "source_row_identities_unique": len({r["source_row"] for r in rows}) == len(rows),
        "all_rows_have_source_hashes": all(len(row["source_feature_sha256"]) == 64 for row in rows),
        "confirmed_require_id_and_unique_geometry": all(
            row["confirmed_park"] == row["declared_park"]
            and json.loads(row["geometric_candidates_json"]) == [row["declared_park"]]
            for row in facilities
            if row["status"] == "confirmed"
        ),
        "unconfirmed_have_no_confirmed_assignment": all(
            not row["confirmed_park"] for row in facilities if row["status"] != "confirmed"
        ),
        "all_facility_exceptions_queued": all(
            row["source_row"] in exception_keys for row in facilities if row["status"] != "confirmed"
        ),
        "all_park_exceptions_queued": all(
            row["source_row"] in exception_keys for row in parks if row["status"] == "source_exception"
        ),
        "no_duplicate_exception_entries": len(exception_keys) == len(exceptions),
        "status_conservation": sum(result["summary"]["facility_status_counts"].values()) == source_assets,
    }


def write_delivery(result: dict[str, Any], destination: Path, sources: list[dict[str, Any]]) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    gpkg = destination / "montreal_asset_onboarding.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    for name in ("parks", "facilities"):
        frame = gpd.GeoDataFrame(result[name], geometry="geometry", crs=TARGET_CRS)
        pyogrio.write_dataframe(frame, gpkg, layer=name, driver="GPKG")
    with sqlite3.connect(gpkg) as connection:
        pd.DataFrame(result["exceptions"], columns=["source_row", "kind", "reason"]).to_sql(
            "exception_queue", connection, index=False
        )
        pd.DataFrame(sources).to_sql("source_provenance", connection, index=False)
        connection.execute("CREATE UNIQUE INDEX facility_row_identity ON facilities(source_row)")
        connection.execute("CREATE UNIQUE INDEX park_row_identity ON parks(source_row)")
        connection.execute("UPDATE gpkg_contents SET last_change='2026-10-27T00:00:00.000Z'")
        connection.commit()
        sql = {
            "parks": connection.execute("SELECT count(*) FROM parks").fetchone()[0],
            "facilities": connection.execute("SELECT count(*) FROM facilities").fetchone()[0],
            "exceptions": connection.execute("SELECT count(*) FROM exception_queue").fetchone()[0],
            "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "unaccounted_facilities": connection.execute(
                "SELECT count(*) FROM facilities f LEFT JOIN exception_queue e ON f.source_row=e.source_row "
                "WHERE f.status != 'confirmed' AND e.source_row IS NULL"
            ).fetchone()[0],
            "conflicting_confirmations": connection.execute(
                "SELECT count(*) FROM facilities WHERE status='confirmed' AND confirmed_park!=declared_park"
            ).fetchone()[0],
        }
    gdal_counts = {name: int(pyogrio.read_info(gpkg, layer=name)["features"]) for name in ("parks", "facilities")}
    pd.DataFrame(serializable_records(result["facilities"])).to_csv(destination / "reconciliation.csv", index=False)
    pd.DataFrame(result["exceptions"]).to_csv(destination / "exceptions.csv", index=False)
    (destination / "summary.json").write_text(json.dumps(result["summary"], ensure_ascii=False, indent=2) + "\n")
    (destination / "reader_checks.json").write_text(json.dumps({"sqlite": sql, "gdal": gdal_counts}, indent=2) + "\n")
    return {"sqlite": sql, "gdal": gdal_counts}


def make_map(result: dict[str, Any], destination: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(figsize=(11, 7), facecolor="#100d24")
    axes.set_facecolor("#100d24")
    for row in result["parks"]:
        geometry = row["geometry"]
        if geometry is None:
            continue
        shapes = geometry.geoms if hasattr(geometry, "geoms") else [geometry]
        for polygon in shapes:
            if polygon.geom_type == "Polygon":
                x, y = polygon.exterior.xy
                axes.fill(x, y, color="#45366c", edgecolor="#786999", linewidth=0.15)
    for accepted, color, label in [(True, "#62e6ce", "ID + geometry agree"), (False, "#ffbc73", "Review queue")]:
        points = [
            r["geometry"].representative_point()
            for r in result["facilities"]
            if r["geometry"] is not None and (r["status"] == "confirmed") == accepted
        ]
        if points:
            axes.scatter(
                [p.x for p in points],
                [p.y for p in points],
                s=5,
                c=color,
                label=f"{label} ({len(points):,})",
                alpha=0.8,
            )
    axes.set_aspect("equal")
    axes.tick_params(colors="#c7bddc", labelsize=7)
    axes.set_xlabel("Easting, NAD83 / MTM zone 8 (m)", color="#c7bddc", fontsize=9)
    axes.set_ylabel("Northing (m)", color="#c7bddc", fontsize=9)
    axes.set_title("MONTRÉAL | From public layers to a reviewable asset handoff", color="white", fontsize=13, pad=16)
    axes.legend(facecolor="#211a39", labelcolor="white", fontsize=9, loc="lower right")
    fig.text(
        0.08,
        0.025,
        "Source: Ville de Montréal, CC BY 4.0. Data association only; no cadastral or operational certification.",
        color="#c7bddc",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(destination, dpi=170, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parks", type=Path, required=True)
    parser.add_argument("--facilities", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--borough", action="append")
    parser.add_argument("--sources", type=Path)
    args = parser.parse_args()
    parks, assets = read_collection(args.parks), read_collection(args.facilities)
    selected = set(args.borough) if args.borough else None
    result = reconcile(parks, assets, selected)
    expected_assets = sum(
        selected is None or identifier(x["properties"].get("ARROND")) in selected for x in assets["features"]
    )
    checks = acceptance_checks(result, len(parks["features"]), expected_assets)
    sources = (
        json.loads(args.sources.read_text())
        if args.sources
        else [{"id": p.stem, "file": p.name, "sha256": digest(p.read_bytes())} for p in (args.parks, args.facilities)]
    )
    readers = write_delivery(result, args.out, sources)
    make_map(result, args.out / "asset_map.png")
    receipt = {
        "instrument_version": VERSION,
        "instrument_sha256": digest(Path(__file__).read_bytes()),
        "reconciliation_sha256": reconciliation_digest(result),
        "acceptance": checks,
        "readers": readers,
        "accepted": all(checks.values()) and readers["sqlite"]["integrity_check"] == "ok",
        "software": {"shapely": shapely.__version__, "pyproj": pyproj.__version__, "pyogrio": pyogrio.__version__},
        "measurement_scope": "Executed deterministic public-source onboarding; no model benchmark or customer acceptance",
    }
    (args.out / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"accepted": receipt["accepted"], "summary": result["summary"]}, ensure_ascii=False))
    if not receipt["accepted"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
