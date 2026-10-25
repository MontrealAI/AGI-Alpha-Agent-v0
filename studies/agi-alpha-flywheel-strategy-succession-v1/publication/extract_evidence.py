#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify and extract the public raw-evidence archives without replacing changed files.

This is publication tooling, outside the frozen scientific implementation. It
does not execute archived code or grant proof/authority. The local destination
must not be concurrently modified by another process during extraction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

SCHEMA = "agi-alpha-strategy-raw-evidence/v1"
PREFIXES = (
    "results/confirmation-v1/", "development/", "browser/development-failures/", "review/results/",
    "operations/load-results/",
    "browser/screenshot-", "publication/verification/recorded-",
)
MAX_INDEX_BYTES = 8_000_000
MAX_ARCHIVE_BYTES = 128_000_000
MAX_EXPANDED_BYTES = 512_000_000
MAX_MEMBER_BYTES = 64_000_000
MAX_MEMBERS = 20_000


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.\-/]+", value):
        raise ValueError("Evidence path contains unsupported characters")
    if value.startswith("/") or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Evidence path is not a bounded relative path")
    result = PurePosixPath(value)
    if not any(value.startswith(prefix) for prefix in PREFIXES):
        raise ValueError(f"Evidence path outside the declared raw-data prefixes: {value}")
    return result


def checked_target(root: Path, relative: PurePosixPath) -> Path:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symbolic-link destination is refused: {relative}")
        if current.exists() and current != root / relative and not current.is_dir():
            raise ValueError(f"Non-directory parent is refused: {relative}")
    return root / relative


def load_index(root: Path, index_path: Path) -> dict:
    if index_path.is_symlink() or not index_path.is_file() or index_path.stat().st_size > MAX_INDEX_BYTES:
        raise ValueError("Missing, linked or oversized archive index")
    result = json.loads(index_path.read_text(encoding="utf-8"))
    if result.get("schema") != SCHEMA or not isinstance(result.get("archives"), list):
        raise ValueError("Unsupported archive index")
    if len(result["archives"]) > 128:
        raise ValueError("Archive-count bound exceeded")
    return result


def validate_archives(root: Path, index: dict, archive_root: Path | None = None) -> list[tuple[Path, dict, list[dict]]]:
    """Read and check all selected bytes and all existing targets before writing."""
    archive_root = (archive_root or root).resolve(strict=True)
    planned = []
    all_paths = set()
    expanded = 0
    for record in index["archives"]:
        name = record.get("path", "")
        if not re.fullmatch(r"evidence/archives/[a-z0-9_-]+\.zip", name):
            raise ValueError("Archive index points outside its bounded archive directory")
        archive = archive_root / name
        for ancestor in [archive, *archive.parents]:
            if ancestor == archive_root:
                break
            if ancestor.is_symlink():
                raise ValueError("Linked archive path is refused")
        if not archive.is_file() or archive.stat().st_size != record.get("bytes"):
            raise ValueError(f"Archive size mismatch: {name}")
        if archive.stat().st_size > MAX_ARCHIVE_BYTES or digest_file(archive) != record.get("sha256"):
            raise ValueError(f"Archive size/hash bound failed: {name}")
        members = record.get("members")
        if not isinstance(members, list) or len(all_paths) + len(members) > MAX_MEMBERS:
            raise ValueError("Evidence member-count bound exceeded")
        expected = {}
        for member in members:
            relative = relative_path(member["path"])
            if str(relative) in all_paths:
                raise ValueError("Duplicate evidence destination across archives")
            all_paths.add(str(relative))
            count = member.get("bytes")
            if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= MAX_MEMBER_BYTES:
                raise ValueError("Evidence member-size bound exceeded")
            if not re.fullmatch(r"[a-f0-9]{64}", member.get("sha256", "")):
                raise ValueError("Invalid evidence member digest")
            expanded += count
            if expanded > MAX_EXPANDED_BYTES:
                raise ValueError("Aggregate evidence expansion bound exceeded")
            expected[str(relative)] = member
            target = checked_target(root, relative)
            if target.exists():
                if not target.is_file() or target.stat().st_size != count or digest_file(target) != member["sha256"]:
                    raise ValueError(f"Refusing different existing bytes: {relative}")
        manifest = "".join(f"{value['sha256']}  {key}\n" for key, value in sorted(expected.items())).encode()
        if hashlib.sha256(manifest).hexdigest() != record.get("manifest_sha256"):
            raise ValueError("Archive member manifest does not match the index")
        with zipfile.ZipFile(archive) as zipped:
            entries = zipped.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)) or set(names) != set(expected) | {"SHA256SUMS.txt"}:
                raise ValueError(f"Archive inventory mismatch: {name}")
            for entry in entries:
                mode = (entry.external_attr >> 16) & 0o170000
                if entry.is_dir() or mode not in {0, stat.S_IFREG} or entry.flag_bits & 1:
                    raise ValueError("Linked, special, directory or encrypted ZIP entry is refused")
                if entry.filename == "SHA256SUMS.txt":
                    if entry.file_size != len(manifest) or zipped.read(entry) != manifest:
                        raise ValueError("Embedded archive manifest differs")
                    continue
                member = expected[entry.filename]
                if entry.file_size != member["bytes"]:
                    raise ValueError("ZIP member size differs from its index")
                value = hashlib.sha256()
                count = 0
                with zipped.open(entry) as stream:
                    for chunk in iter(lambda: stream.read(1 << 20), b""):
                        count += len(chunk)
                        if count > member["bytes"]:
                            raise ValueError("Expanded member exceeded its declared size")
                        value.update(chunk)
                if count != member["bytes"] or value.hexdigest() != member["sha256"]:
                    raise ValueError("Evidence member hash mismatch")
        planned.append((archive, record, members))
    return planned


def extract(root: Path, index: dict, archive_root: Path | None = None) -> dict:
    root = root.resolve(strict=True)
    planned = validate_archives(root, index, archive_root)
    written = 0
    retained = 0
    for archive, _record, members in planned:
        with zipfile.ZipFile(archive) as zipped:
            for member in members:
                relative = relative_path(member["path"])
                target = checked_target(root, relative)
                if target.exists():
                    if digest_file(target) != member["sha256"]:
                        raise ValueError("Destination changed after preflight")
                    retained += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                checked_target(root, relative)
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                flags |= getattr(os, "O_NOFOLLOW", 0)
                fd = os.open(target, flags, 0o644)
                value = hashlib.sha256()
                count = 0
                with os.fdopen(fd, "wb") as output, zipped.open(str(relative)) as stream:
                    for chunk in iter(lambda: stream.read(1 << 20), b""):
                        count += len(chunk)
                        if count > member["bytes"]:
                            raise ValueError("Archive changed after preflight")
                        value.update(chunk)
                        output.write(chunk)
                if count != member["bytes"] or value.hexdigest() != member["sha256"]:
                    raise ValueError("Archive changed after preflight; inspect newly created partial evidence")
                written += 1
    return {"schema": "public-evidence-extraction/v1", "status": "PASS", "written": written,
            "identical_existing_retained": retained, "archives": len(planned),
            "scope": "Local data extraction only; no scientific code, proof or authority is executed or granted."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--index", type=Path)
    parser.add_argument("--archive-root", type=Path,
                        help="Extracted evidence-handoff root containing evidence/archives; defaults to --root")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    index_path = args.index or root / "evidence/ARCHIVE_INDEX.json"
    index = load_index(root, index_path)
    if args.check_only:
        checked = validate_archives(root, index, args.archive_root)
        report = {"status": "PASS", "scope": "Read-only archive and destination preflight", "archives": len(checked)}
    else:
        report = extract(root, index, args.archive_root)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
