# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote

FACTS = frozenset(
    (
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
)
STRUCTURAL = frozenset(("properties", "items", "additionalProperties", "allOf", "$ref", "x-nullable"))
ANNOTATIONS = frozenset(("title", "description", "example", "examples", "externalDocs", "xml"))
LIMIT = 100000


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def normalize(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in value.items()}
    return value


def token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def load(path: Path) -> dict[str, Any]:
    text = path.read_text()
    if text.lstrip().startswith("{"):
        value = json.loads(text)
    else:
        import yaml

        value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError("SPEC_OBJECT_REQUIRED")
    return cast(dict[str, Any], normalize(value))


def inventory(doc: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    resolved: dict[str, Any] = {}

    def warning(response: str, address: list[str], pointer: str, reason: str) -> None:
        warnings.append({"responseId": response, "address": address, "sourcePointer": pointer, "reason": reason})

    def lookup(ref: str) -> Any:
        if ref in resolved:
            return resolved[ref]
        if not ref.startswith("#"):
            raise ValueError("EXTERNAL_REF")
        fragment = unquote(ref[1:])
        if fragment and not fragment.startswith("/"):
            raise ValueError("INVALID_LOCAL_REF")
        value: Any = doc
        for part in fragment.split("/")[1:]:
            key = part.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        resolved[ref] = value
        return value

    def walk(node: Any, response: str, address: list[str], pointer: str, refs: list[str]) -> None:
        if len(rows) + len(warnings) >= LIMIT or len(address) > 64:
            raise ValueError("INVENTORY_LIMIT")
        if not isinstance(node, dict):
            warning(response, address, pointer, "NON_OBJECT_SCHEMA")
            return
        if "$ref" in node:
            ref = node["$ref"]
            if not isinstance(ref, str):
                warning(response, address, pointer, "INVALID_REF")
                return
            if any(key != "$ref" for key in node):
                warning(response, address, pointer, "REF_SIBLINGS_IGNORED")
            if ref in refs:
                warning(response, address, pointer, "REF_CYCLE:" + ref)
                return
            try:
                target = lookup(ref)
            except (KeyError, IndexError, ValueError, TypeError) as error:
                warning(response, address, pointer, "UNRESOLVED_REF:" + ref + ":" + type(error).__name__)
                return
            walk(target, response, address, ref, refs + [ref])
            return
        facts = {key: normalize(node[key]) for key in sorted(FACTS & node.keys())}
        if "nullable" not in facts and isinstance(node.get("x-nullable"), bool):
            facts["nullable"] = node["x-nullable"]
        if "required" in facts and isinstance(facts["required"], list):
            facts["required"] = sorted(facts["required"])
        if "enum" in facts and isinstance(facts["enum"], list):
            facts["enum"] = sorted(facts["enum"], key=canonical)
        if isinstance(node.get("additionalProperties"), bool):
            facts["additionalProperties"] = node["additionalProperties"]
        rows.append(
            {"responseId": response, "address": address, "facts": facts, "sourcePointer": pointer, "refChain": refs}
        )
        for key in sorted(node):
            if key not in FACTS | STRUCTURAL | ANNOTATIONS:
                warning(response, address, pointer, "UNASSESSED_KEYWORD:" + key)
        properties = node.get("properties", {})
        if isinstance(properties, dict):
            for key in sorted(properties):
                walk(properties[key], response, address + ["p:" + key], pointer + "/properties/" + token(key), refs)
        else:
            warning(response, address, pointer, "INVALID_PROPERTIES")
        if "items" in node:
            walk(node["items"], response, address + ["i:"], pointer + "/items", refs)
        if isinstance(node.get("additionalProperties"), dict):
            walk(node["additionalProperties"], response, address + ["a:"], pointer + "/additionalProperties", refs)
        if "allOf" in node:
            if isinstance(node["allOf"], list):
                for index, branch in enumerate(node["allOf"]):
                    walk(branch, response, address + ["allOf:" + str(index)], pointer + "/allOf/" + str(index), refs)
            else:
                warning(response, address, pointer, "INVALID_ALLOF")

    for path, item in sorted(doc.get("paths", {}).items()):
        if not isinstance(item, dict) or not isinstance(item.get("get"), dict):
            continue
        operation = item["get"]
        for status, response in sorted(operation.get("responses", {}).items(), key=lambda pair: str(pair[0])):
            status = str(status)
            if not (status.upper() == "2XX" or (status.isdigit() and 200 <= int(status) <= 299)):
                continue
            response_id = f"GET {path} {status}"
            pointer = "#/paths/" + token(path) + "/get/responses/" + token(status)
            if not isinstance(response, dict):
                warning(response_id, [], pointer, "NON_OBJECT_RESPONSE")
                continue
            response_refs: list[str] = []
            while "$ref" in response:
                ref = response["$ref"]
                if not isinstance(ref, str) or ref in response_refs:
                    warning(response_id, [], pointer, "INVALID_OR_CYCLIC_RESPONSE_REF")
                    response = {}
                    break
                response_refs.append(ref)
                try:
                    response = lookup(ref)
                    pointer = ref
                except (KeyError, IndexError, ValueError, TypeError):
                    warning(response_id, [], pointer, "UNRESOLVED_RESPONSE_REF:" + str(ref))
                    response = {}
                    break
            schema = response.get("schema")
            schema_pointer = pointer + "/schema"
            json_media = True
            if "content" in response:
                content = response["content"]
                if not isinstance(content, dict):
                    warning(response_id, [], pointer, "INVALID_CONTENT")
                    continue
                for media in sorted(content):
                    if media != "application/json":
                        warning(response_id, [], pointer, "UNASSESSED_MEDIA:" + media)
                schema = content.get("application/json", {}).get("schema")
                schema_pointer = pointer + "/content/application~1json/schema"
            else:
                produces = operation.get("produces", doc.get("produces"))
                if produces is None:
                    warning(response_id, [], pointer, "UNDECLARED_MEDIA")
                elif "application/json" not in produces:
                    warning(response_id, [], pointer, "NON_JSON_RESPONSE")
                    json_media = False
            responses.append(
                {
                    "responseId": response_id,
                    "operationId": operation.get("operationId"),
                    "sourcePointer": pointer,
                    "hasSchema": schema is not None,
                }
            )
            if not json_media:
                continue
            if schema is None:
                warning(response_id, [], pointer, "NO_RESPONSE_SCHEMA")
            else:
                walk(schema, response_id, [], schema_pointer, response_refs)
    rows.sort(key=lambda row: canonical([row["responseId"], row["address"]]))
    warnings.sort(key=canonical)
    responses.sort(key=lambda row: row["responseId"])
    return {"rows": rows, "warnings": warnings, "responses": responses}


def make_dossier(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    old, new = inventory(before), inventory(after)
    indexes = [{canonical([row["responseId"], row["address"]]): row for row in item["rows"]} for item in [old, new]]
    changes = []
    for key in sorted(indexes[0].keys() | indexes[1].keys()):
        left, right = indexes[0].get(key), indexes[1].get(key)
        if left is not None and right is not None and canonical(left["facts"]) == canonical(right["facts"]):
            continue
        changes.append(
            {
                "key": json.loads(key),
                "kind": "ADDED" if left is None else "REMOVED" if right is None else "CHANGED",
                "before": left,
                "after": right,
            }
        )
    return {
        "schema": "api-response-surface-dossier/v1",
        "scope": "Every GET 2xx response, structural schema facts only; not a compatibility certificate",
        "before": old,
        "after": new,
        "changes": changes,
        "decision": "REVIEW_CHANGED_SURFACES" if changes else "NO_SCOPED_SURFACE_CHANGE",
        "unassessed": bool(old["warnings"] or new["warnings"]),
        "limitations": [
            "No server execution or consumer acceptance",
            "Structural allOf branch order is retained, not normalized for logical equivalence",
            "Only application/json is traversed in OpenAPI 3 content",
            "Unsupported keywords, missing schemas and reference cycles stay unassessed",
            "Optional property removal is not automatically a breaking change",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    started, cpu = time.perf_counter(), time.process_time()
    dossier = make_dossier(load(args.before), load(args.after))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dossier, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    metadata = {
        "elapsed_seconds": time.perf_counter() - started,
        "cpu_seconds": time.process_time() - cpu,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "before_sha256": hashlib.sha256(args.before.read_bytes()).hexdigest(),
        "after_sha256": hashlib.sha256(args.after.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "changes": len(dossier["changes"]),
        "before_nodes": len(dossier["before"]["rows"]),
        "after_nodes": len(dossier["after"]["rows"]),
        "warnings": len(dossier["before"]["warnings"]) + len(dossier["after"]["warnings"]),
    }
    args.output.with_suffix(".measurement.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
