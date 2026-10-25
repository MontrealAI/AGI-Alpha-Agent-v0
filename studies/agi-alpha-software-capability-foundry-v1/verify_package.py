# SPDX-License-Identifier: Apache-2.0
"""Verify the listed package bytes and optional historical evidence boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys


MANIFEST = "MANIFEST.sha256.json"


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def relative_name(value):
    if not isinstance(value, str) or not value:
        raise ValueError("A nonempty relative path is required")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or PureWindowsPath(value).drive
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or "\\" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError("Unsafe or noncanonical relative path: " + repr(value))
    return value


def regular_path(root, name):
    current = root
    parts = relative_name(name).split("/")
    for index, part in enumerate(parts):
        current = current / part
        information = current.lstat()
        if stat.S_ISLNK(information.st_mode):
            raise ValueError("Symlink path component is not permitted")
        if index < len(parts) - 1 and not stat.S_ISDIR(information.st_mode):
            raise ValueError("A parent path component is not a directory")
        if index == len(parts) - 1 and not stat.S_ISREG(information.st_mode):
            raise ValueError("The listed path is not a regular file")
    return current, information


def read_json(root, name):
    path, _ = regular_path(root, name)
    return json.loads(path.read_text(encoding="utf8"), object_pairs_hook=unique_object)


def valid_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def check_file(root, entry):
    name = entry["path"]
    try:
        path, before = regular_path(root, name)
        expected_size = entry.get("bytes")
        if expected_size is not None and before.st_size != expected_size:
            return {"path": name, "kind": "changed-size", "expected": expected_size, "observed": before.st_size}
        sha256, count = hashlib.sha256(), 0
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                return {"path": name, "kind": "changed-during-open"}
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                sha256.update(block)
                count += len(block)
            after = os.fstat(stream.fileno())
        if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns) or count != after.st_size:
            return {"path": name, "kind": "changed-during-read"}
        observed = sha256.hexdigest()
        if observed != entry["sha256"]:
            return {"path": name, "kind": "changed-sha256", "expected": entry["sha256"], "observed": observed}
        return None
    except FileNotFoundError:
        return {"path": name, "kind": "missing"}
    except (OSError, ValueError) as error:
        return {"path": name, "kind": "unsafe-or-unreadable", "detail": str(error)}


def check_entries(root, entries):
    issues = [issue for entry in entries if (issue := check_file(root, entry)) is not None]
    return {"passed": not issues, "files": len(entries), "issues": issues}


def manifest_entries(value):
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("Manifest schema_version must be integer 1")
    entries = value.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Manifest files must be a nonempty list")
    names = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "bytes", "sha256"}:
            raise ValueError("Every manifest entry requires exactly path, bytes and sha256")
        name = relative_name(entry["path"])
        if name == MANIFEST or name in names:
            raise ValueError("Manifest cannot list itself or duplicate a path: " + name)
        names.add(name)
        if type(entry["bytes"]) is not int or entry["bytes"] < 0 or not valid_digest(entry["sha256"]):
            raise ValueError("Invalid byte count or SHA-256 for: " + name)
    return entries


def boundary_entries(value):
    if not isinstance(value, dict) or not value:
        raise ValueError("Boundary file hashes must be a nonempty object")
    entries = []
    for name, checksum in value.items():
        relative_name(name)
        if not valid_digest(checksum):
            raise ValueError("Invalid boundary SHA-256 for: " + name)
        entries.append({"path": name, "sha256": checksum})
    return entries


def optional_boundary(root, record_path, files_key=None, input_prefix=""):
    try:
        regular_path(root, record_path)
    except FileNotFoundError:
        return {"present": False, "passed": None, "files": 0, "issues": []}
    try:
        record = read_json(root, record_path)
        entries = boundary_entries(record[files_key] if files_key else record)
        if input_prefix:
            entries = [{**entry, "path": input_prefix + entry["path"]} for entry in entries]
        result = check_entries(root, entries)
        return {"present": True, **result}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"present": True, "passed": False, "files": 0, "issues": [{"path": record_path, "kind": "invalid-boundary", "detail": str(error)}]}


def verify(root, boundaries=True):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Package root must be a directory")
    entries = manifest_entries(read_json(root, MANIFEST))
    package = check_entries(root, entries)
    result = {"schema": "foundry-package-integrity/v1", "package_root": str(root), "manifest": MANIFEST, "package": package}
    if boundaries:
        result["source_freeze"] = optional_boundary(root, "protocol/FREEZE.json", "files")
        result["protected_inputs"] = optional_boundary(root, "results/confirmation/TASKS_LOCK.json", input_prefix="confirmation/")
    result["passed"] = package["passed"] and all(result[name]["passed"] is not False for name in ("source_freeze", "protected_inputs") if name in result)
    result["scope"] = "Listed bytes and present historical hash boundaries only; unlisted files are ignored; no signature, release authority or scientific replication is implied."
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Verify the package MANIFEST.sha256.json and, when present, the active source freeze and protected-input lock.",
        epilog="Manifest schema: {schema_version: 1, files: [{path: relative POSIX path, bytes: nonnegative integer, sha256: 64 lowercase hex digits}]}. The manifest must exclude itself. No files are written.",
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent, help="Package root (default: directory containing this script)")
    parser.add_argument("--skip-boundaries", action="store_true", help="Check only the package manifest, without optional historical boundary checks")
    parser.add_argument("--json", action="store_true", help="Print the full machine-readable report")
    args = parser.parse_args()
    try:
        result = verify(args.root, boundaries=not args.skip_boundaries)
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"schema": "foundry-package-integrity/v1", "passed": False, "error": "invalid-manifest-or-root", "detail": str(error)}
        if args.json:
            print(json.dumps(result, sort_keys=True, indent=2))
        else:
            print("FAIL: " + result["detail"], file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print(("PASS" if result["passed"] else "FAIL") + f": checked {result['package']['files']} listed package files.")
        for name in ("package", "source_freeze", "protected_inputs"):
            if name not in result:
                continue
            section = result[name]
            if name != "package":
                print(f"{name}: " + (f"{section['files']} files, " + ("PASS" if section["passed"] else "FAIL") if section["present"] else "not present; skipped"))
            for issue in section["issues"]:
                print(f"  {name}: {issue['kind']}: {issue['path']}" + (" — " + issue["detail"] if "detail" in issue else ""))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
