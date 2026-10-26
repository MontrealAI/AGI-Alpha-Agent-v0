# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote


def stable(value: Any) -> str:
    def numeric(item: Any) -> Any:
        if isinstance(item, dict):
            return {k: numeric(v) for k, v in item.items()}
        if isinstance(item, list):
            return [numeric(v) for v in item]
        return int(item) if isinstance(item, float) and item.is_integer() else item

    return json.dumps(numeric(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def read_document(path: Path) -> dict[str, Any]:
    data = path.read_text()
    if data.lstrip().startswith("{"):
        parsed = json.loads(data)
    else:
        import yaml

        parsed = yaml.safe_load(data)

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return int(value) if isinstance(value, float) and value.is_integer() else value

    return cast(dict[str, Any], clean(parsed))


def independently_enumerate(document: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    include = {
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
    }
    handled = include | {
        "properties",
        "items",
        "additionalProperties",
        "allOf",
        "$ref",
        "title",
        "description",
        "example",
        "examples",
        "externalDocs",
        "xml",
        "x-nullable",
    }
    queue: collections.deque[tuple[Any, str, list[str], str, list[str]]] = collections.deque()
    result: dict[str, Any] = {}
    unassessed = False

    def escape(value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")

    def lookup(reference: str) -> Any:
        if not reference.startswith("#"):
            raise ValueError("external")
        fragment = unquote(reference[1:])
        if fragment and not fragment.startswith("/"):
            raise ValueError("not_pointer")
        cursor: Any = document
        for part in fragment.split("/")[1:]:
            part = part.replace("~1", "/").replace("~0", "~")
            cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
        return cursor

    for path, methods in document.get("paths", {}).items():
        if not isinstance(methods, dict) or not isinstance(methods.get("get"), dict):
            continue
        operation = methods["get"]
        for status, response in operation.get("responses", {}).items():
            status = str(status)
            if status.upper() != "2XX" and not (status.isdigit() and 200 <= int(status) <= 299):
                continue
            identity = "GET " + path + " " + status
            pointer = "#/paths/" + escape(path) + "/get/responses/" + escape(status)
            ancestors: list[str] = []
            if not isinstance(response, dict):
                unassessed = True
                continue
            while "$ref" in response:
                ref = response["$ref"]
                try:
                    if not isinstance(ref, str) or ref in ancestors:
                        raise ValueError("ref")
                    ancestors.append(ref)
                    response = lookup(ref)
                    pointer = ref
                    if not isinstance(response, dict):
                        raise ValueError("response")
                except (ValueError, TypeError, KeyError, IndexError):
                    unassessed = True
                    response = {}
                    break
            if "content" in response:
                content = response["content"]
                if not isinstance(content, dict):
                    unassessed = True
                    continue
                unassessed = unassessed or bool(set(content) - {"application/json"})
                node = content.get("application/json", {}).get("schema")
                pointer += "/content/application~1json/schema"
            else:
                node = response.get("schema")
                pointer += "/schema"
                produces = operation.get("produces", document.get("produces"))
                unassessed = unassessed or produces is None or "application/json" not in produces
                if produces is not None and "application/json" not in produces:
                    continue
            if node is None:
                unassessed = True
            else:
                queue.append((node, identity, [], pointer, ancestors))
    seen = 0
    while queue:
        seen += 1
        if seen > 100000:
            raise ValueError("VERIFIER_LIMIT")
        node, identity, address, pointer, ancestors = queue.popleft()
        if not isinstance(node, dict):
            unassessed = True
            continue
        if "$ref" in node:
            ref = node["$ref"]
            unassessed = unassessed or bool(set(node) - {"$ref"})
            try:
                if not isinstance(ref, str) or ref in ancestors:
                    raise ValueError("ref")
                queue.append((lookup(ref), identity, address, ref, ancestors + [ref]))
            except (ValueError, TypeError, KeyError, IndexError):
                unassessed = True
            continue
        facts: dict[str, Any] = {}
        for key in node:
            if key in include:
                facts[key] = node[key]
        if "nullable" not in facts and isinstance(node.get("x-nullable"), bool):
            facts["nullable"] = node["x-nullable"]
        for key in ["enum", "required"]:
            if key in facts and isinstance(facts[key], list):
                facts[key] = sorted(facts[key], key=stable) if key == "enum" else sorted(facts[key])
        if isinstance(node.get("additionalProperties"), bool):
            facts["additionalProperties"] = node["additionalProperties"]
        key = stable([identity, address])
        if key in result:
            raise ValueError("DUPLICATE_SCHEMA_ADDRESS")
        result[key] = {
            "responseId": identity,
            "address": address,
            "facts": facts,
            "sourcePointer": pointer,
            "refChain": ancestors,
        }
        unassessed = unassessed or bool(set(node) - handled)
        children = node.get("properties", {})
        if not isinstance(children, dict):
            unassessed = True
        else:
            for label, child in children.items():
                queue.append(
                    (child, identity, address + ["p:" + label], pointer + "/properties/" + escape(label), ancestors)
                )
        if "items" in node:
            queue.append((node["items"], identity, address + ["i:"], pointer + "/items", ancestors))
        if isinstance(node.get("additionalProperties"), dict):
            queue.append(
                (node["additionalProperties"], identity, address + ["a:"], pointer + "/additionalProperties", ancestors)
            )
        if "allOf" in node:
            if not isinstance(node["allOf"], list):
                unassessed = True
            else:
                for index, child in enumerate(node["allOf"]):
                    queue.append(
                        (child, identity, address + [f"allOf:{index}"], pointer + f"/allOf/{index}", ancestors)
                    )
    return result, unassessed


def verify(before: dict[str, Any], after: dict[str, Any], dossier: dict[str, Any]) -> dict[str, Any]:
    old, old_warning = independently_enumerate(before)
    new, new_warning = independently_enumerate(after)
    for label, expected in [("before", old), ("after", new)]:
        actual_rows = dossier[label]["rows"]
        actual = {stable([row["responseId"], row["address"]]): row for row in actual_rows}
        if len(actual_rows) != len(actual) or stable(actual) != stable(expected):
            raise ValueError("INCOMPLETE_OR_FALSE_INVENTORY:" + label)
    expected_changes = {}
    for key in set(old) | set(new):
        left, right = old.get(key), new.get(key)
        if left is not None and right is not None and stable(left["facts"]) == stable(right["facts"]):
            continue
        expected_changes[key] = {
            "key": json.loads(key),
            "kind": "ADDED" if left is None else "REMOVED" if right is None else "CHANGED",
            "before": left,
            "after": right,
        }
    actual_changes = {stable(change["key"]): change for change in dossier["changes"]}
    if len(actual_changes) != len(dossier["changes"]) or stable(actual_changes) != stable(expected_changes):
        raise ValueError("INCOMPLETE_OR_FALSE_CHANGES")
    if (old_warning or new_warning) and not dossier.get("unassessed"):
        raise ValueError("UNASSESSED_SCOPE_CONCEALED")
    return {
        "accepted": True,
        "scope": "independent exhaustive structural replay, not live API compatibility",
        "before_nodes": len(old),
        "after_nodes": len(new),
        "changes": len(expected_changes),
        "unassessed": old_warning or new_warning,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("dossier", type=Path)
    args = parser.parse_args()
    result = verify(read_document(args.before), read_document(args.after), json.loads(args.dossier.read_text()))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
