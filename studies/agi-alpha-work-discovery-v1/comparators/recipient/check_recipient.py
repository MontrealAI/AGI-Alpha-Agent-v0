"""Independent recipient's construction checks; these are not fresh transfer tests."""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any

from recipient_inventory import at, diff, inventory


def base(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "swagger": "2.0", "info": {"title": "Fixture", "version": "1"},
        "paths": {"/records/{id}": {"get": {"responses": {"200": {"description": "OK", "schema": schema}, "404": {"description": "missing", "schema": {"type": "string"}}}}}},
        "definitions": {},
    }


def check() -> None:
    started = time.perf_counter()
    assertions = 0

    def require(ok: bool, description: str) -> None:
        nonlocal assertions
        if not ok:
            raise AssertionError(description)
        assertions += 1

    schema: dict[str, Any] = {"type": "object", "required": ["z", "a"], "additionalProperties": False, "properties": {
        "a": {"type": "array", "minItems": 1, "maxItems": 7, "uniqueItems": True, "items": {"$ref": "#/definitions/T"}},
        "map": {"additionalProperties": {"type": "number", "minimum": -2, "maximum": 20, "exclusiveMaximum": True, "multipleOf": 0.5}},
        "p:/~": {"type": "string", "minLength": 2, "maxLength": 9, "pattern": "[a-z]+", "enum": ["z", "a"], "x-nullable": True},
        "composition": {"allOf": [{"$ref": "#/definitions/T"}, {"properties": {"b": {"type": "boolean", "nullable": False, "x-nullable": True}}}]},
    }}
    doc = base(schema)
    doc["definitions"]["T"] = {"type": "string", "format": "uuid"}
    original = copy.deepcopy(doc)
    before = inventory(doc)
    require(doc == original, "inventory must not mutate public source")
    indexed = {tuple(node["address"]): node for node in before["nodes"]}
    require(indexed[()]["facts"]["required"] == ["a", "z"], "required sorted")
    require(indexed[()]["facts"]["additionalProperties"] is False, "false additionalProperties preserved")
    require(indexed[("p:p:/~",)]["facts"]["enum"] == ["a", "z"], "enum sorted")
    require(indexed[("p:p:/~",)]["facts"]["nullable"] is True, "x-nullable mapped")
    require(indexed[("p:composition", "allOf:1", "p:b")]["facts"]["nullable"] is False, "nullable takes priority")
    require(indexed[("p:a", "i:")]["facts"] == {"type": "string", "format": "uuid"}, "array reference traversed")
    require(indexed[("p:map", "a:")]["facts"]["multipleOf"] == 0.5, "additional property schema traversed")
    require(indexed[("p:a", "i:")]["sourcePointer"] == "#/definitions/T", "reference target provenance")
    require("#/paths/~1records~1{id}/get/responses/200/schema/properties/a/items/$ref" in indexed[("p:a", "i:")]["sourceChain"], "reference use provenance")
    require(indexed[("p:map",)]["facts"] == {}, "missing type never inferred")
    require(len(before["responses"]) == 1, "non-2xx ignored")
    require(all(node["responseId"] == "GET /records/{id} 200" for node in before["nodes"]), "stable response identity")
    for node in before["nodes"]:
        require(isinstance(at(doc, node["sourcePointer"]), dict), "all source pointers resolve")
    after_doc = copy.deepcopy(doc)
    after_doc["definitions"]["T"]["maxLength"] = 40
    after = inventory(after_doc)
    changes = diff(before, after)
    require(len(changes) == 2, "shared schema modification expands both affected uses")
    reorder = copy.deepcopy(doc)
    reorder["paths"]["/records/{id}"]["get"]["responses"]["200"]["schema"]["required"].reverse()
    reorder["paths"]["/records/{id}"]["get"]["responses"]["200"]["schema"]["properties"]["p:/~"]["enum"].reverse()
    require(diff(before, inventory(reorder)) == [], "enum/required order is immaterial")
    annotation = copy.deepcopy(doc)
    annotation["definitions"]["T"]["description"] = "Changed annotation"
    require(diff(before, inventory(annotation)) == [], "description change excluded from structural inventory")
    cycle = base({"$ref": "#/definitions/Loop"})
    cycle["definitions"]["Loop"] = {"type": "object", "properties": {"child": {"$ref": "#/definitions/Loop"}}}
    require(inventory(cycle)["limitations"][0]["reason"] == "cyclic-reference", "cycle explicitly limited")
    external = base({"$ref": "https://example.invalid/spec.json#/T"})
    require(inventory(external)["limitations"][0]["reason"] == "external-or-invalid-reference", "external reference never fetched")
    unsupported = base({"oneOf": [{"type": "string"}, {"type": "number"}]})
    require(inventory(unsupported)["limitations"][0]["reason"] == "unsupported-schema-keyword", "unsupported schema flagged")
    mime = base({"type": "string"})
    mime["produces"] = ["text/plain"]
    require(inventory(mime)["nodes"] == [], "non-JSON excluded")
    require(inventory(mime)["responses"][0]["assessment"] == "unassessed-non-json", "exclusion made explicit")
    mime["paths"]["/records/{id}"]["get"]["produces"] = ["application/json"]
    require(len(inventory(mime)["nodes"]) == 1, "operation produces overrides root")
    global_response = base({"type": "number"})
    global_response["responses"] = {"Shared": global_response["paths"]["/records/{id}"]["get"]["responses"]["200"]}
    global_response["paths"]["/records/{id}"]["get"]["responses"]["200"] = {"$ref": "#/responses/Shared"}
    require(inventory(global_response)["nodes"][0]["sourcePointer"] == "#/responses/Shared/schema", "global response reference traversed")
    missing = base({"$ref": "#/definitions/Missing"})
    require(inventory(missing)["limitations"][0]["reason"] == "unresolved-reference", "missing reference explicit")
    result = {"kind": "construction-fixtures-not-fresh-confirmation", "assertions": assertions, "passed": True, "elapsedSeconds": time.perf_counter() - started}
    Path(__file__).with_name("construction-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    check()
