#!/usr/bin/env python3
"""Independent bounded Swagger 2 GET JSON response-shape inventory.

Constructed without reading the donor or other baseline implementation.
This reports declaration changes, not runtime compatibility or client impact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

FACTS = (
    "type",
    "format",
    "enum",
    "required",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
    "nullable",
)
UNSUPPORTED = ("oneOf", "anyOf", "not", "patternProperties", "dependencies", "contains", "propertyNames")
ANNOTATIONS = {"title", "description", "example", "examples", "default", "readOnly", "xml", "externalDocs"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def at(document: dict[str, Any], pointer: str) -> Any:
    if not pointer.startswith("#/"):
        raise ValueError("only local JSON Pointer references are supported")
    result: Any = document
    for bit in pointer[2:].split("/"):
        part = bit.replace("~1", "/").replace("~0", "~")
        result = result[int(part)] if isinstance(result, list) else result[part]
    return result


def inventory(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("swagger") != "2.0":
        raise ValueError("this recipient scope is Swagger 2.0 only")
    nodes: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []

    def limitation(response_id: str, address: list[str], pointer: str, reason: str, detail: Any = None) -> None:
        limitations.append(
            {
                "responseId": response_id,
                "address": address,
                "sourcePointer": pointer,
                "reason": reason,
                "detail": detail,
            }
        )

    def follow(
        value: Any, pointer: str, chain: list[str], seen: tuple[str, ...], response_id: str, address: list[str]
    ) -> tuple[Any, str, list[str], tuple[str, ...]] | None:
        while isinstance(value, dict) and "$ref" in value:
            target = value["$ref"]
            siblings = [key for key in value if key != "$ref" and key not in ANNOTATIONS and not key.startswith("x-")]
            if siblings:
                limitation(
                    response_id, address, pointer, "reference-structural-siblings-not-interpreted", sorted(siblings)
                )
            if not isinstance(target, str) or not target.startswith("#/"):
                limitation(response_id, address, pointer, "external-or-invalid-reference", target)
                return None
            if target in seen:
                limitation(response_id, address, pointer, "cyclic-reference", target)
                return None
            try:
                value = at(document, target)
            except (KeyError, IndexError, ValueError, TypeError):
                limitation(response_id, address, pointer, "unresolved-reference", target)
                return None
            chain = chain + [pointer + "/$ref", target]
            pointer = target
            seen = seen + (target,)
        return value, pointer, chain, seen

    def walk(
        value: Any,
        pointer: str,
        address: list[str],
        chain: list[str],
        seen: tuple[str, ...],
        response_id: str,
        depth: int = 0,
    ) -> None:
        if depth > 128:
            limitation(response_id, address, pointer, "depth-budget-exhausted", 128)
            return
        resolved = follow(value, pointer, chain, seen, response_id, address)
        if resolved is None:
            return
        value, pointer, chain, seen = resolved
        if not isinstance(value, dict):
            limitation(response_id, address, pointer, "nonobject-schema", value)
            return
        facts = {key: value[key] for key in FACTS if key in value}
        if "nullable" not in facts and "x-nullable" in value:
            facts["nullable"] = value["x-nullable"]
        for key in ("enum", "required"):
            if key in facts and isinstance(facts[key], list):
                facts[key] = sorted(facts[key], key=canonical)
        if isinstance(value.get("additionalProperties"), bool):
            facts["additionalProperties"] = value["additionalProperties"]
        nodes.append(
            {
                "responseId": response_id,
                "address": address,
                "facts": facts,
                "sourcePointer": pointer,
                "sourceChain": chain + [pointer],
            }
        )
        for key in UNSUPPORTED:
            if key in value:
                limitation(response_id, address, pointer + "/" + key, "unsupported-schema-keyword", key)
        properties = value.get("properties", {})
        if isinstance(properties, dict):
            for name, child in sorted(properties.items()):
                walk(
                    child,
                    pointer + "/properties/" + segment(name),
                    address + ["p:" + name],
                    chain,
                    seen,
                    response_id,
                    depth + 1,
                )
        else:
            limitation(response_id, address, pointer + "/properties", "malformed-properties")
        if "items" in value:
            if isinstance(value["items"], dict):
                walk(value["items"], pointer + "/items", address + ["i:"], chain, seen, response_id, depth + 1)
            else:
                limitation(response_id, address, pointer + "/items", "unsupported-items-form")
        if isinstance(value.get("additionalProperties"), dict):
            walk(
                value["additionalProperties"],
                pointer + "/additionalProperties",
                address + ["a:"],
                chain,
                seen,
                response_id,
                depth + 1,
            )
        if "allOf" in value:
            if isinstance(value["allOf"], list):
                for index, child in enumerate(value["allOf"]):
                    walk(
                        child,
                        pointer + "/allOf/" + str(index),
                        address + ["allOf:" + str(index)],
                        chain,
                        seen,
                        response_id,
                        depth + 1,
                    )
            else:
                limitation(response_id, address, pointer + "/allOf", "malformed-allOf")

    for path, path_item in sorted(document.get("paths", {}).items()):
        if not isinstance(path_item, dict):
            continue
        if "$ref" in path_item:
            limitation(
                "GET " + path + " *",
                [],
                "#/paths/" + segment(path),
                "path-item-reference-not-supported",
                path_item["$ref"],
            )
        operation = path_item.get("get")
        if not isinstance(operation, dict):
            continue
        produces = operation.get("produces", document.get("produces"))
        json_scope = produces is None or "application/json" in produces
        for status, response in sorted(operation.get("responses", {}).items(), key=lambda item: str(item[0])):
            status = str(status)
            if not re.fullmatch(r"2\d\d", status):
                continue
            response_id = "GET " + path + " " + status
            pointer = "#/paths/" + segment(path) + "/get/responses/" + segment(status)
            row: dict[str, Any] = {
                "responseId": response_id,
                "sourcePointer": pointer,
                "produces": produces,
                "assessment": "assessed-json-declarations",
            }
            responses.append(row)
            if not json_scope:
                row["assessment"] = "unassessed-non-json"
                limitation(response_id, [], pointer, "non-json-produces", produces)
                continue
            resolved = follow(response, pointer, [], (), response_id, [])
            if resolved is None:
                row["assessment"] = "unassessed-response-reference"
                continue
            response, pointer, chain, seen = resolved
            if not isinstance(response, dict) or "schema" not in response:
                row["assessment"] = "unassessed-no-schema"
                limitation(response_id, [], pointer, "response-has-no-schema")
                continue
            walk(response["schema"], pointer + "/schema", [], chain, seen, response_id)
    nodes.sort(key=lambda node: (node["responseId"], node["address"]))
    return {
        "responses": responses,
        "nodes": nodes,
        "limitations": limitations,
        "claim": "Declared structural facts only; no runtime, consumer, or compatibility claim.",
    }


def diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    def indexed(inv: dict[str, Any]) -> dict[tuple[str, tuple[str, ...]], dict[str, Any]]:
        return {(node["responseId"], tuple(node["address"])): node for node in inv["nodes"]}

    old, new = indexed(before), indexed(after)
    changes = []
    for key in sorted(old.keys() | new.keys()):
        left, right = old.get(key), new.get(key)
        if left is None or right is None or canonical(left["facts"]) != canonical(right["facts"]):
            changes.append(
                {
                    "responseId": key[0],
                    "address": list(key[1]),
                    "kind": "added" if left is None else "removed" if right is None else "changed",
                    "before": left,
                    "after": right,
                }
            )
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = [path.read_bytes() for path in (args.old, args.new)]
    old, new = [inventory(json.loads(data)) for data in raw]
    changes = diff(old, new)
    output = {
        "schemaVersion": "independent-recipient-1",
        "inputs": [
            {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}
            for path, data in zip((args.old, args.new), raw)
        ],
        "old": old,
        "new": new,
        "changes": changes,
        "summary": {
            "oldNodes": len(old["nodes"]),
            "newNodes": len(new["nodes"]),
            "changes": len(changes),
            "oldLimitations": len(old["limitations"]),
            "newLimitations": len(new["limitations"]),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output["summary"]))


if __name__ == "__main__":
    main()
