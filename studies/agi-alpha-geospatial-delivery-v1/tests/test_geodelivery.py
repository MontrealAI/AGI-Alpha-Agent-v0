# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from geodelivery import acceptance_checks, identifier, reconcile


def collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def park(oid: str, index: str, left: float = -73.70) -> dict:
    return {
        "type": "Feature",
        "properties": {"OBJECTID": oid, "NUM_INDEX": index, "Nom": "Fixture park"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[left, 45.5], [left + 0.02, 45.5], [left + 0.02, 45.52], [left, 45.52], [left, 45.5]]],
        },
    }


def asset(oid: str = "1", index: str | None = "0001", x: float = -73.69, y: float = 45.51) -> dict:
    return {
        "type": "Feature",
        "properties": {"OBJECTID": oid, "ID": oid, "INDEX_PARC": index, "ARROND": "Fixture", "NOM": "Asset"},
        "geometry": {"type": "Point", "coordinates": [x, y]},
    }


class AcceptanceTests(unittest.TestCase):
    def test_agreement_is_confirmed(self) -> None:
        result = reconcile(collection([park("p1", "0001")]), collection([asset()]))
        self.assertEqual(result["facilities"][0]["status"], "confirmed")
        self.assertTrue(all(acceptance_checks(result, 1, 1).values()))

    def test_disagreement_is_not_repaired(self) -> None:
        result = reconcile(
            collection([park("p1", "0001"), park("p2", "0002", -73.60)]), collection([asset(index="0002")])
        )
        row = result["facilities"][0]
        self.assertEqual(row["status"], "identifier_geometry_conflict")
        self.assertEqual(row["confirmed_park"], "")
        self.assertEqual(row["declared_park"], "0002")

    def test_geometric_suggestion_is_not_administrative_confirmation(self) -> None:
        result = reconcile(collection([park("p1", "0001")]), collection([asset(index=None)]))
        row = result["facilities"][0]
        self.assertEqual(row["status"], "geometry_only_suggestion")
        self.assertEqual(row["confirmed_park"], "")
        self.assertEqual(row["suggested_park"], "0001")

    def test_overlap_preserves_ambiguity(self) -> None:
        result = reconcile(collection([park("p1", "0001"), park("p2", "0002")]), collection([asset()]))
        self.assertEqual(result["facilities"][0]["status"], "ambiguous_geometry")

    def test_multiple_polygons_of_one_park_are_one_candidate(self) -> None:
        result = reconcile(collection([park("p1", "0001"), park("p2", "0001")]), collection([asset()]))
        self.assertEqual(result["facilities"][0]["status"], "confirmed")

    def test_leading_zero_identity_is_preserved(self) -> None:
        self.assertNotEqual(identifier("0001"), identifier("1"))
        result = reconcile(collection([park("p1", "0001")]), collection([asset(index="1")]))
        self.assertEqual(result["facilities"][0]["status"], "unknown_declared_park")

    def test_duplicates_cannot_confirm(self) -> None:
        result = reconcile(collection([park("p1", "0001")]), collection([asset(), asset()]))
        self.assertEqual(len(result["facilities"]), 2)
        self.assertTrue(all(r["status"] == "invalid_source" for r in result["facilities"]))
        self.assertTrue(all(acceptance_checks(result, 1, 2).values()))

    def test_impossible_coordinates_queued(self) -> None:
        result = reconcile(collection([park("p1", "0001")]), collection([asset(y=200)]))
        self.assertEqual(result["facilities"][0]["status"], "invalid_source")
        self.assertIn("coordinate_range", result["facilities"][0]["reasons"])

    def test_unknown_crs_refused(self) -> None:
        assets = collection([asset()])
        assets["crs"] = {"type": "name", "properties": {"name": "EPSG:9999999"}}
        with self.assertRaises(Exception):
            reconcile(collection([park("p1", "0001")]), assets)

    def test_source_attributes_unchanged(self) -> None:
        parks, assets = collection([park("p1", "0001")]), collection([asset()])
        original = copy.deepcopy(assets)
        result = reconcile(parks, assets)
        self.assertEqual(assets, original)
        self.assertEqual(
            json.loads(result["facilities"][0]["source_properties_json"]), original["features"][0]["properties"]
        )

    def test_invalid_polygon_quarantined(self) -> None:
        value = park("p1", "0001")
        value["geometry"]["coordinates"] = [
            [[-73.7, 45.5], [-73.68, 45.52], [-73.68, 45.5], [-73.7, 45.52], [-73.7, 45.5]]
        ]
        result = reconcile(collection([value]), collection([asset()]))
        self.assertEqual(result["parks"][0]["status"], "source_exception")
        self.assertNotEqual(result["facilities"][0]["status"], "confirmed")

    def test_unassigned_record_is_still_delivered(self) -> None:
        result = reconcile(collection([park("p1", "0001")]), collection([asset(index=None, x=-74)]))
        self.assertEqual(result["facilities"][0]["status"], "unassigned")
        self.assertEqual(len(result["exceptions"]), 1)

    def test_null_facility_properties_is_queued(self) -> None:
        value = asset()
        value["properties"] = None
        result = reconcile(collection([park("p1", "0001")]), collection([value]))
        self.assertEqual(result["facilities"][0]["status"], "invalid_source")
        self.assertEqual(result["facilities"][0]["source_properties_json"], "null")

    def test_null_park_properties_is_queued(self) -> None:
        value = park("p1", "0001")
        value["properties"] = None
        result = reconcile(collection([value]), collection([asset()]))
        self.assertEqual(result["parks"][0]["status"], "source_exception")

    def test_point_cannot_be_a_park_polygon(self) -> None:
        value = park("p1", "0001")
        value["geometry"] = asset()["geometry"]
        result = reconcile(collection([value]), collection([asset()]))
        self.assertEqual(result["parks"][0]["status"], "source_exception")
        self.assertNotEqual(result["facilities"][0]["status"], "confirmed")

    def test_shared_axis_swap_refused(self) -> None:
        value, point = park("p1", "0001"), asset()
        value["geometry"]["coordinates"][0] = [list(reversed(pair)) for pair in value["geometry"]["coordinates"][0]]
        point["geometry"]["coordinates"] = list(reversed(point["geometry"]["coordinates"]))
        result = reconcile(collection([value]), collection([point]))
        self.assertEqual(result["facilities"][0]["status"], "invalid_source")
        self.assertIn("outside_target_area_of_use", result["facilities"][0]["reasons"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
