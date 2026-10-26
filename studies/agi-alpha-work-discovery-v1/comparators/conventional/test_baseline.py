# SPDX-License-Identifier: Apache-2.0
import copy
import json
import unittest
from typing import Any

from conventional import make_dossier
from verify_dossier import verify


def document(schema: dict[str, Any], definitions: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "swagger": "2.0",
        "produces": ["application/json"],
        "paths": {"/resource": {"get": {"operationId": "Read", "responses": {"200": {"schema": schema}}}}},
        "definitions": definitions or {},
    }


class BaselineControls(unittest.TestCase):
    def test_type_change(self) -> None:
        a, b = document({"type": "string"}), document({"type": "integer"})
        report = make_dossier(a, b)
        self.assertEqual(len(report["changes"]), 1)
        self.assertTrue(verify(a, b, report)["accepted"])

    def test_reference_relocation(self) -> None:
        a = document({"$ref": "#/definitions/A"}, {"A": {"type": "string"}})
        b = document({"$ref": "#/definitions/B"}, {"B": {"type": "string"}})
        report = make_dossier(a, b)
        self.assertEqual(report["changes"], [])
        self.assertTrue(verify(a, b, report)["accepted"])

    def test_enum_reordering(self) -> None:
        a = document({"type": "string", "enum": ["b", "a"]})
        b = document({"type": "string", "enum": ["a", "b"]})
        self.assertEqual(make_dossier(a, b)["changes"], [])

    def test_array_map_conjunction(self) -> None:
        a = document(
            {
                "allOf": [
                    {"type": "object", "properties": {"a": {"type": "array", "items": {"type": "integer"}}}},
                    {"additionalProperties": {"type": "boolean"}},
                ]
            }
        )
        report = make_dossier(a, a)
        self.assertEqual(len(report["before"]["rows"]), 6)
        self.assertTrue(verify(a, a, report)["accepted"])

    def test_cycle(self) -> None:
        a = document(
            {"$ref": "#/definitions/A"}, {"A": {"type": "object", "properties": {"next": {"$ref": "#/definitions/A"}}}}
        )
        report = make_dossier(a, a)
        self.assertTrue(report["unassessed"])
        self.assertTrue(verify(a, a, report)["accepted"])

    def test_missing_reference(self) -> None:
        a = document({"$ref": "#/definitions/missing"})
        report = make_dossier(a, a)
        self.assertTrue(report["unassessed"])
        self.assertEqual(report["before"]["rows"], [])
        self.assertTrue(verify(a, a, report)["accepted"])

    def test_external_reference(self) -> None:
        a = document({"$ref": "https://example.invalid/schema"})
        report = make_dossier(a, a)
        self.assertTrue(report["unassessed"])
        self.assertTrue(verify(a, a, report)["accepted"])

    def test_union_unassessed(self) -> None:
        a = document({"oneOf": [{"type": "string"}, {"type": "integer"}]})
        self.assertTrue(make_dossier(a, a)["unassessed"])

    def test_ref_siblings_unassessed(self) -> None:
        a = document({"$ref": "#/definitions/A", "minimum": 5}, {"A": {"type": "integer"}})
        report = make_dossier(a, a)
        self.assertEqual(report["before"]["rows"][0]["facts"], {"type": "integer"})
        self.assertTrue(report["unassessed"])
        self.assertTrue(verify(a, a, report)["accepted"])

    def test_omitted_change_rejected(self) -> None:
        a, b = document({"type": "string"}), document({"type": "integer"})
        report = make_dossier(a, b)
        report["changes"] = []
        with self.assertRaises(ValueError):
            verify(a, b, report)

    def test_omitted_inventory_rejected(self) -> None:
        a = document({"type": "object", "properties": {"a": {"type": "integer"}}})
        report = make_dossier(a, a)
        report["before"]["rows"].pop()
        with self.assertRaises(ValueError):
            verify(a, a, report)

    def test_forged_provenance_rejected(self) -> None:
        a = document({"type": "string"})
        report = make_dossier(a, a)
        report["before"]["rows"][0]["sourcePointer"] = "#/made-up"
        with self.assertRaises(ValueError):
            verify(a, a, report)

    def test_hidden_unsupported_rejected(self) -> None:
        a = document({"oneOf": [{"type": "string"}]})
        report = make_dossier(a, a)
        report["unassessed"] = False
        with self.assertRaises(ValueError):
            verify(a, a, report)

    def test_duplicate_inventory_rejected(self) -> None:
        a = document({"type": "string"})
        report = make_dossier(a, a)
        report["before"]["rows"].append(copy.deepcopy(report["before"]["rows"][0]))
        with self.assertRaises(ValueError):
            verify(a, a, report)

    def test_source_json_portability(self) -> None:
        a = document({"type": "number", "minimum": 1.0})
        self.assertTrue(verify(a, a, json.loads(json.dumps(make_dossier(a, a))))["accepted"])

    def test_swagger_nullable(self) -> None:
        a, b = document({"type": "string"}), document({"type": "string", "x-nullable": True})
        report = make_dossier(a, b)
        self.assertEqual(report["changes"][0]["after"]["facts"], {"type": "string", "nullable": True})
        self.assertTrue(verify(a, b, report)["accepted"])

    def test_non_json_not_traversed(self) -> None:
        a = document({"type": "string"})
        a["produces"] = ["text/plain"]
        report = make_dossier(a, a)
        self.assertEqual(report["before"]["rows"], [])
        self.assertTrue(report["unassessed"])
        self.assertTrue(verify(a, a, report)["accepted"])


if __name__ == "__main__":
    unittest.main()
