# SPDX-License-Identifier: Apache-2.0
"""Verify a closed companion ZIP and/or a clean extracted root; never execute it.

Use --manifest-sha256 from the external seal receipt to check external identity.
Without it, validity means consistency with the embedded manifest, not a trusted
origin. --root accepts the agi-alpha-useful-work-v2 directory itself. Write any
--report outside the extracted root, since exact payload verification rejects
unlisted files. Only standard-library modules are used.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
import zipfile

PREFIX = "agi-alpha-useful-work-v2"
MANIFEST_NAME = "COMPANION_MANIFEST.json"
SCHEMA = "agi-alpha-useful-work-companion/v1"
INVENTORY_SCHEMA = "public-companion-inclusion-inventory/v1"
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
CHUNK = 1024 * 1024
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK


class CompanionError(ValueError):
    """A concrete archive, path or identity requirement failed."""


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CompanionError("DUPLICATE_JSON_KEY:" + key)
            result[key] = value
        return result

    def constant(value):
        raise CompanionError("NONFINITE_JSON_VALUE:" + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise CompanionError("INVALID_PAYLOAD_PATH")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise CompanionError("UNSAFE_PAYLOAD_PATH:" + value)
    return parts


def absolute_path(value):
    path = Path(value)
    if ".." in path.parts:
        raise CompanionError("PARENT_TRAVERSAL_NOT_ALLOWED")
    return Path(os.path.abspath(path))


def open_directory(value):
    """Open each directory component without following a symlink."""
    path = absolute_path(value)
    current = os.open(path.anchor, DIRECTORY_FLAGS)
    try:
        for part in path.parts[1:]:
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def open_relative_file(root_fd, relative):
    parts = relative_path(relative)
    current = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=current)
            os.close(current)
            current = child
        result = os.open(parts[-1], FILE_FLAGS, dir_fd=current)
    finally:
        os.close(current)
    if not stat.S_ISREG(os.fstat(result).st_mode):
        os.close(result)
        raise CompanionError("REGULAR_FILE_REQUIRED:" + relative)
    return result


def open_absolute_file(path):
    path = absolute_path(path)
    parent = open_directory(path.parent)
    try:
        return open_relative_file(parent, path.name)
    finally:
        os.close(parent)


def fingerprint(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def stream_identity(stream, sink=None, limit=None):
    before = os.fstat(stream.fileno())
    if not stat.S_ISREG(before.st_mode):
        raise CompanionError("REGULAR_FILE_REQUIRED")
    digest, total = hashlib.sha256(), 0
    while True:
        block = stream.read(CHUNK)
        if not block:
            break
        total += len(block)
        if limit is not None and total > limit:
            raise CompanionError("READ_SIZE_BOUND")
        digest.update(block)
        if sink is not None:
            sink.write(block)
    if fingerprint(before) != fingerprint(os.fstat(stream.fileno())):
        raise CompanionError("FILE_CHANGED_WHILE_READING")
    if total != before.st_size:
        raise CompanionError("READ_LENGTH_MISMATCH")
    return {"bytes": total, "sha256": digest.hexdigest()}


def identity_at(root_fd, relative, sink=None):
    with os.fdopen(open_relative_file(root_fd, relative), "rb") as source:
        return stream_identity(source, sink=sink)


def identity_path(path):
    with os.fdopen(open_absolute_file(path), "rb") as source:
        return stream_identity(source)


def read_path(path, limit=MAX_MANIFEST_BYTES):
    with os.fdopen(open_absolute_file(path), "rb") as source:
        before = os.fstat(source.fileno())
        if before.st_size > limit:
            raise CompanionError("READ_SIZE_BOUND")
        raw = source.read(limit + 1)
        if len(raw) > limit or len(raw) != before.st_size:
            raise CompanionError("READ_LENGTH_BOUND")
        if fingerprint(before) != fingerprint(os.fstat(source.fileno())):
            raise CompanionError("FILE_CHANGED_WHILE_READING")
        return raw


def rows_checked(rows):
    if not isinstance(rows, list):
        raise CompanionError("FILE_LIST_REQUIRED")
    paths = set()
    for row in rows:
        if not isinstance(row, dict):
            raise CompanionError("FILE_ROW_REQUIRED")
        path = row.get("path")
        relative_path(path)
        if path == MANIFEST_NAME or path in paths:
            raise CompanionError("DUPLICATE_OR_RESERVED_PAYLOAD_PATH:" + path)
        paths.add(path)
        if type(row.get("bytes")) is not int or row["bytes"] < 0:
            raise CompanionError("NONNEGATIVE_INTEGER_SIZE_REQUIRED:" + path)
        if not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise CompanionError("SHA256_REQUIRED:" + path)
        if not isinstance(row.get("category"), str):
            raise CompanionError("CATEGORY_REQUIRED:" + path)
    return rows


def inventory_checked(raw):
    data = strict_json(raw)
    if not isinstance(data, dict) or data.get("schema") != INVENTORY_SCHEMA:
        raise CompanionError("INVENTORY_SCHEMA")
    if data.get("blocked") != [] or data.get("all_frozen_sources_included_unchanged") is not True:
        raise CompanionError("INVENTORY_IDENTITY_OR_PRIVACY_BLOCK")
    files = rows_checked(data.get("files"))
    if type(data.get("file_count")) is not int or data["file_count"] != len(files):
        raise CompanionError("INVENTORY_FILE_COUNT")
    if type(data.get("logical_bytes")) is not int or data["logical_bytes"] != sum(x["bytes"] for x in files):
        raise CompanionError("INVENTORY_BYTE_COUNT")
    return data


def select_payload(inventory, exclude_wheels=False, exclude_ruff=False):
    files, omissions = [], []
    for row in inventory["files"]:
        reason = None
        if exclude_wheels and row["path"].lower().endswith(".whl"):
            reason = "source-evidence-variant-excludes-wheel"
        elif exclude_ruff and row["path"].startswith("support/ruff"):
            reason = "source-evidence-variant-excludes-ruff-tooling"
        if reason:
            omissions.append({**row, "reason": reason})
        else:
            files.append(row)
    return files, omissions


def manifest_checked(raw, expected_sha256=None):
    if len(raw) > MAX_MANIFEST_BYTES:
        raise CompanionError("MANIFEST_SIZE_BOUND")
    digest = sha(raw)
    if expected_sha256 is not None and digest != expected_sha256:
        raise CompanionError("EXTERNAL_MANIFEST_HASH_MISMATCH")
    data = strict_json(raw)
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or data.get("prefix") != PREFIX:
        raise CompanionError("MANIFEST_SCHEMA_OR_PREFIX")
    text = data.get("source_inventory_json_utf8")
    if not isinstance(text, str):
        raise CompanionError("EXACT_SOURCE_INVENTORY_REQUIRED")
    inventory_raw = text.encode("utf-8")
    if data.get("source_inventory_sha256") != sha(inventory_raw):
        raise CompanionError("SOURCE_INVENTORY_HASH")
    if type(data.get("source_inventory_bytes")) is not int or data["source_inventory_bytes"] != len(inventory_raw):
        raise CompanionError("SOURCE_INVENTORY_BYTES")
    inventory = inventory_checked(inventory_raw)
    exclusions = data.get("variant_exclusions", {})
    if set(exclusions) != {"wheels", "ruff"} or any(type(x) is not bool for x in exclusions.values()):
        raise CompanionError("VARIANT_EXCLUSIONS")
    if exclusions["ruff"] and not exclusions["wheels"]:
        raise CompanionError("RUFF_EXCLUSION_REQUIRES_SOURCE_EVIDENCE_VARIANT")
    expected_files, expected_omissions = select_payload(inventory, exclusions["wheels"], exclusions["ruff"])
    files = rows_checked(data.get("files"))
    if files != expected_files or data.get("omissions") != expected_omissions:
        raise CompanionError("PAYLOAD_NOT_EXACT_INVENTORY_SELECTION")
    classification = "NOT_OFFLINE_COMPLETE" if any(exclusions.values()) else "OFFLINE_COMPANION_PAYLOAD"
    if data.get("classification") != classification:
        raise CompanionError("VARIANT_CLASSIFICATION")
    if type(data.get("file_count")) is not int or data["file_count"] != len(files):
        raise CompanionError("MANIFEST_FILE_COUNT")
    if type(data.get("logical_bytes")) is not int or data["logical_bytes"] != sum(x["bytes"] for x in files):
        raise CompanionError("MANIFEST_BYTE_COUNT")
    return data, digest


def require_identity(actual, row):
    if actual["bytes"] != row["bytes"] or actual["sha256"] != row["sha256"]:
        raise CompanionError("PAYLOAD_IDENTITY_MISMATCH:" + row["path"])


def verify_archive(path, expected_manifest_sha256=None, expected_archive_sha256=None):
    path = absolute_path(path)
    with os.fdopen(open_absolute_file(path), "rb") as stream:
        before = os.fstat(stream.fileno())
        with zipfile.ZipFile(stream, "r") as archive:
            infos = archive.infolist()
            names = [x.filename for x in infos]
            if len(names) != len(set(names)):
                raise CompanionError("DUPLICATE_ZIP_MEMBER")
            manifest_path = PREFIX + "/" + MANIFEST_NAME
            if manifest_path not in names:
                raise CompanionError("MANIFEST_MEMBER_MISSING")
            info = archive.getinfo(manifest_path)
            if info.file_size > MAX_MANIFEST_BYTES:
                raise CompanionError("MANIFEST_SIZE_BOUND")
            raw = archive.read(info)
            manifest, manifest_sha = manifest_checked(raw, expected_manifest_sha256)
            expected = {PREFIX + "/" + row["path"]: row for row in manifest["files"]}
            if set(names) != set(expected) | {manifest_path}:
                raise CompanionError("EXTRA_OR_MISSING_ZIP_MEMBER")
            for info in infos:
                mode = info.external_attr >> 16
                if info.is_dir() or stat.S_IFMT(mode) != stat.S_IFREG or info.flag_bits & 1:
                    raise CompanionError("REGULAR_UNENCRYPTED_ZIP_FILE_REQUIRED:" + info.filename)
            for name, row in expected.items():
                info = archive.getinfo(name)
                if info.file_size != row["bytes"]:
                    raise CompanionError("ZIP_DECLARED_SIZE_MISMATCH:" + name)
                digest, total = hashlib.sha256(), 0
                with archive.open(info) as source:
                    while True:
                        block = source.read(CHUNK)
                        if not block:
                            break
                        total += len(block)
                        if total > row["bytes"]:
                            raise CompanionError("ZIP_MEMBER_SIZE_OVERFLOW:" + name)
                        digest.update(block)
                require_identity({"bytes": total, "sha256": digest.hexdigest()}, row)
            bad = archive.testzip()
            if bad is not None:
                raise CompanionError("ZIP_CRC_FAILURE:" + bad)
        stream.seek(0)
        archive_identity = stream_identity(stream)
        if fingerprint(before) != fingerprint(os.fstat(stream.fileno())):
            raise CompanionError("ARCHIVE_CHANGED_DURING_VERIFICATION")
    if expected_archive_sha256 is not None and archive_identity["sha256"] != expected_archive_sha256:
        raise CompanionError("EXTERNAL_ARCHIVE_HASH_MISMATCH")
    return {"kind": "archive", "path": str(path), "valid": True,
            "archive_sha256": archive_identity["sha256"], "archive_bytes": archive_identity["bytes"],
            "manifest_sha256": manifest_sha, "external_manifest_hash_checked": expected_manifest_sha256 is not None,
            "external_archive_hash_checked": expected_archive_sha256 is not None,
            "payload_files": len(manifest["files"]), "payload_bytes": manifest["logical_bytes"],
            "classification": manifest["classification"], "omitted_files": len(manifest["omissions"]),
            "central_directory_read": True, "testzip_passed": True, "every_entry_sha256_and_size_verified": True}


def tree_files(root_fd, prefix=""):
    paths = []
    for name in sorted(os.listdir(root_fd)):
        relative = prefix + name
        relative_path(relative)
        info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            child = os.open(name, DIRECTORY_FLAGS, dir_fd=root_fd)
            try:
                paths.extend(tree_files(child, relative + "/"))
            finally:
                os.close(child)
        elif stat.S_ISREG(info.st_mode):
            paths.append(relative)
        else:
            raise CompanionError("NONREGULAR_EXTRACTED_ENTRY:" + relative)
    return paths


def verify_root(path, expected_manifest_sha256=None):
    path = absolute_path(path)
    root_fd = open_directory(path)
    try:
        with os.fdopen(open_relative_file(root_fd, MANIFEST_NAME), "rb") as stream:
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
        manifest, digest = manifest_checked(raw, expected_manifest_sha256)
        expected = {row["path"] for row in manifest["files"]} | {MANIFEST_NAME}
        if set(tree_files(root_fd)) != expected:
            raise CompanionError("EXTRA_OR_MISSING_EXTRACTED_FILE")
        for row in manifest["files"]:
            require_identity(identity_at(root_fd, row["path"]), row)
        require_identity(identity_at(root_fd, MANIFEST_NAME),
                         {"path": MANIFEST_NAME, "bytes": len(raw), "sha256": digest})
    finally:
        os.close(root_fd)
    return {"kind": "extracted-root", "path": str(path), "valid": True,
            "manifest_sha256": digest, "external_manifest_hash_checked": expected_manifest_sha256 is not None,
            "payload_files": len(manifest["files"]), "payload_bytes": manifest["logical_bytes"],
            "classification": manifest["classification"], "omitted_files": len(manifest["omissions"]),
            "every_entry_sha256_and_size_verified": True, "no_symlinks_followed": True}


def write_new_report(path, value):
    path = absolute_path(path)
    parent = open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(parent)
    finally:
        os.close(parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--archive-sha256")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.archive is None and args.root is None:
        parser.error("Provide --archive and/or --root")
    if args.archive_sha256 and args.archive is None:
        parser.error("--archive-sha256 requires --archive")
    start, cpu = time.perf_counter(), time.process_time()
    result = {"schema": "closed-companion-verification/v1", "started_at": utc_now(),
              "checks": [], "errors": [], "consumer_execution": False, "new_missions": 0,
              "money_usd": None}
    for kind, value in (("archive", args.archive), ("root", args.root)):
        if value is None:
            continue
        try:
            check = (verify_archive(value, args.manifest_sha256, args.archive_sha256)
                     if kind == "archive" else verify_root(value, args.manifest_sha256))
            result["checks"].append(check)
        except Exception as exc:
            result["errors"].append({"kind": kind, "path": str(value), "error": f"{type(exc).__name__}:{exc}"})
    if len({x["manifest_sha256"] for x in result["checks"]}) > 1:
        result["errors"].append({"error": "ARCHIVE_AND_ROOT_MANIFEST_DIFFER"})
    result.update(valid=not result["errors"], ended_at=utc_now(),
                  wall_seconds=time.perf_counter() - start, process_cpu_seconds=time.process_time() - cpu,
                  child_cpu_seconds=0.0,
                  scope="Integrity against the exact manifest; external origin authenticated only by separately trusted hashes. No consumer or release qualification.")
    if args.report:
        try:
            write_new_report(args.report, result)
        except Exception as exc:
            result["valid"] = False
            result["errors"].append({"error": "REPORT_WRITE_FAILED:" + str(exc)})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
