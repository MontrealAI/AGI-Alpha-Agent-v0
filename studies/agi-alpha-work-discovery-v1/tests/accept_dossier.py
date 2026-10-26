# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import resource
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, cast

STUDY = Path(__file__).resolve().parents[1]
COMPARATOR = STUDY / "comparators/conventional"
FROZEN_CAPSULE_SHA256 = "245cbe8ba69b49862b9d56d5291862bab49f2f6cb1fb8a124939f69df677f4e4"


def module(name: str, path: Path) -> ModuleType:
    manifest_bytes = (COMPARATOR / "SOURCE_FREEZE.json").read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != FROZEN_CAPSULE_SHA256:
        raise ValueError("ORACLE_CAPSULE_IDENTITY")
    identities = {row["path"]: row for row in json.loads(manifest_bytes)["files"]}
    expected = identities[path.name]
    source = path.read_bytes()
    if len(source) != expected["bytes"] or hashlib.sha256(source).hexdigest() != expected["sha256"]:
        raise ValueError("ORACLE_SOURCE_IDENTITY")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("ORACLE_IMPORT")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


oracle = module("independent_bfs", COMPARATOR / "verify_dossier.py")
conventional = module("independent_baseline", COMPARATOR / "conventional.py")


def stable(value: Any) -> str:
    return cast(str, oracle.stable(value))


def input_digests(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    completed = subprocess.run(
        ["node", str(Path(__file__).with_name("source_digests.mjs"))],
        input=json.dumps([before, after], ensure_ascii=False, allow_nan=False),
        text=True,
        capture_output=True,
        timeout=60,
        check=True,
    )
    values = json.loads(completed.stdout)
    if (
        not isinstance(values, list)
        or len(values) != 2
        or not all(isinstance(value, str) and len(value) == 64 for value in values)
    ):
        raise ValueError("DIGEST_HELPER_OUTPUT")
    return cast(list[str], values)


def response_ids(document: dict[str, Any]) -> set[str]:
    result = set()
    for path, methods in document.get("paths", {}).items():
        if not isinstance(methods, dict) or not isinstance(methods.get("get"), dict):
            continue
        for status in methods["get"].get("responses", {}):
            status = str(status)
            if status.upper() == "2XX" or (status.isdigit() and 200 <= int(status) <= 299):
                result.add("GET " + path + " " + status)
    return result


def read_dossier(directory: Path) -> tuple[dict[str, Any], list[Path]]:
    direct = directory / "response-dossier.json"
    index_path = directory / "response-dossier-index.json"
    if direct.exists() and index_path.exists():
        raise ValueError("AMBIGUOUS_DOSSIER")
    if direct.is_file():
        if direct.is_symlink():
            raise ValueError("DOSSIER_SYMLINK")
        return json.loads(direct.read_text()), [direct]
    if not index_path.is_file() or index_path.is_symlink():
        raise ValueError("DOSSIER_NOT_FOUND")
    index = json.loads(index_path.read_text())
    if set(index) != {"encoding", "digest", "parts"} or index["encoding"] != "utf8-json-fragments":
        raise ValueError("FRAGMENT_INDEX_SCHEMA")
    parts = index["parts"]
    if not isinstance(parts, list) or not 1 <= len(parts) <= 9 or len(set(parts)) != len(parts):
        raise ValueError("FRAGMENT_PARTS")
    if not isinstance(index["digest"], str) or not re.fullmatch(r"[a-f0-9]{64}", index["digest"]):
        raise ValueError("FRAGMENT_DIGEST_SCHEMA")
    files, pieces = [index_path], []
    for name in parts:
        if not isinstance(name, str) or not re.fullmatch(r"dossier-part-[1-9]\.txt", name):
            raise ValueError("FRAGMENT_FILENAME")
        path = directory / name
        if not path.is_file() or path.is_symlink() or path.resolve().parent != directory.resolve():
            raise ValueError("FRAGMENT_CUSTODY")
        text = path.read_text()
        if len(text.encode("utf-16-le")) // 2 > 175000:
            raise ValueError("FRAGMENT_SIZE")
        files.append(path)
        pieces.append(text)
    joined = "".join(pieces)
    if hashlib.sha256(joined.encode()).hexdigest() != index["digest"]:
        raise ValueError("FRAGMENT_DIGEST_MISMATCH")
    return json.loads(joined), files


def accept(before: dict[str, Any], after: dict[str, Any], dossier: dict[str, Any]) -> dict[str, Any]:
    old, old_unassessed = oracle.independently_enumerate(before)
    new, new_unassessed = oracle.independently_enumerate(after)
    digests = input_digests(before, after)
    if dossier.get("schema") != "alpha-response-dossier/v1":
        raise ValueError("DOSSIER_SCHEMA")
    if [dossier.get("oldSourceDigest"), dossier.get("newSourceDigest")] != digests:
        raise ValueError("INPUT_DIGEST_MISMATCH")
    expected = {}
    for key in set(old) | set(new):
        left, right = old.get(key), new.get(key)
        if left is not None and right is not None and stable(left["facts"]) == stable(right["facts"]):
            continue
        identity, address = json.loads(key)
        expected[key] = {
            "key": key,
            "responseId": identity,
            "address": address,
            "kind": "ADDED" if left is None else "REMOVED" if right is None else "CHANGED",
            "oldFacts": None if left is None else left["facts"],
            "newFacts": None if right is None else right["facts"],
            "oldPointer": None if left is None else left["sourcePointer"],
            "newPointer": None if right is None else right["sourcePointer"],
            "oldRefChain": [] if left is None else left["refChain"],
            "newRefChain": [] if right is None else right["refChain"],
        }
    changes = dossier.get("changes")
    if not isinstance(changes, list) or any(not isinstance(row, dict) or "key" not in row for row in changes):
        raise ValueError("CHANGES_SCHEMA")
    actual = {row["key"]: row for row in changes}
    if len(changes) != len(actual) or stable(actual) != stable(expected):
        raise ValueError("INCOMPLETE_FALSE_OR_DUPLICATE_CHANGE")
    old_responses, new_responses = response_ids(before), response_ids(after)
    if dossier.get("addedResponses") != sorted(new_responses - old_responses):
        raise ValueError("ADDED_RESPONSES_MISMATCH")
    if dossier.get("removedResponses") != sorted(old_responses - new_responses):
        raise ValueError("REMOVED_RESPONSES_MISMATCH")
    counts = dossier.get("counts", {})
    for side, expected_count, responses in [("old", len(old), old_responses), ("new", len(new), new_responses)]:
        if counts.get(side, {}).get("nodes") != expected_count or counts.get(side, {}).get("responses") != len(
            responses
        ):
            raise ValueError("INVENTORY_COUNT_MISMATCH:" + side)
    if counts.get("changes") != len(expected):
        raise ValueError("CHANGE_COUNT_MISMATCH")
    warnings = dossier.get("unassessed")
    if not isinstance(warnings, list) or ((old_unassessed or new_unassessed) and not warnings):
        raise ValueError("UNASSESSED_SCOPE_CONCEALED")
    for side in ["old", "new"]:
        if counts.get(side, {}).get("warnings") != sum(row.get("side") == side for row in warnings):
            raise ValueError("WARNING_COUNT_MISMATCH:" + side)
    for side, document in [("old", before), ("new", after)]:
        warning_locations = set()
        for row in warnings:
            if row.get("side") != side:
                continue
            pointer = row.get("pointer")
            warning_locations.add(stable([row.get("responseId"), row.get("address"), pointer]))
            if row.get("code") == "NO_JSON_SCHEMA" and isinstance(pointer, str) and pointer.endswith("/schema"):
                warning_locations.add(stable([row.get("responseId"), row.get("address"), pointer[:-7]]))
        for row in conventional.inventory(document)["warnings"]:
            location = stable([row["responseId"], row["address"], row["sourcePointer"]])
            if location not in warning_locations:
                raise ValueError("UNASSESSED_LOCATION_OMITTED:" + side + ":" + location)
    return {
        "accepted": True,
        "scope": "Exhaustive independent response-surface and source-binding replay; not server or customer compatibility acceptance",
        "oldNodes": len(old),
        "newNodes": len(new),
        "changes": len(expected),
        "oldResponses": len(old_responses),
        "newResponses": len(new_responses),
        "sourceDigests": digests,
        "unassessed": old_unassessed or new_unassessed,
        "conventionalSourceUnchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    started, cpu = time.perf_counter(), time.process_time()
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    before, after = oracle.read_document(args.before), oracle.read_document(args.after)
    dossier, files = read_dossier(args.output_directory)
    result = accept(before, after, dossier)
    pack_file = args.output_directory / "workbench-pack.json"
    if pack_file.is_file():
        pack = json.loads(pack_file.read_text())
        if stable(json.loads(pack["spec"]["inputs"]["oldSpec"])) != stable(before) or stable(
            json.loads(pack["spec"]["inputs"]["newSpec"])
        ) != stable(after):
            raise ValueError("WORKBENCH_INPUT_MISMATCH")
        artifacts = {row["name"]: row["content"] for row in pack["result"]["artifacts"]}
        for path in files:
            if artifacts.get(path.name) != path.read_text():
                raise ValueError("WORKBENCH_ARTIFACT_MISMATCH:" + path.name)
    child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    result.update(
        {
            "elapsedSeconds": time.perf_counter() - started,
            "cpuSeconds": time.process_time()
            - cpu
            + child_end.ru_utime
            + child_end.ru_stime
            - child_start.ru_utime
            - child_start.ru_stime,
            "inputRawSha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in [args.before, args.after]],
            "dossierFiles": [
                {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in files
            ],
            "actualHumanSeconds": None,
            "actualMonetaryCost": None,
        }
    )
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.write_text(output)
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
