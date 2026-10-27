# SPDX-License-Identifier: Apache-2.0
"""Restore exact compact study evidence and the historical v3 fixture safely.

Uses only the Python standard library. No downloads, dependency installation,
scientific execution, authentication, or fresh-confirmation claim occurs here.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any
import argparse
import gzip
import hashlib
import json
import os
import stat
import tempfile
import zipfile

STUDY = Path(__file__).resolve().parent
ALLOWED_PREFIXES = (
    "studies/agi-alpha-economic-construction-v3/",
    "studies/agi-alpha-opportunity-discovery-v4/",
)


def digest(data: bytes) -> str:
    """Return exact byte identity."""
    return hashlib.sha256(data).hexdigest()


def relative_name(value: str) -> PurePosixPath:
    """Reject absolute, ambiguous and traversal-bearing archive/target paths."""
    path = PurePosixPath(value)
    if not value or not path.parts or "\\" in value or ":" in value or path.is_absolute():
        raise ValueError("Unsafe path")
    if any(part in {"", ".", ".."} for part in path.parts) or path.as_posix() != value:
        raise ValueError("Noncanonical or traversing path")
    return path


def ordinary_path(root: Path, relative: str, *, destination: bool = False) -> Path:
    """Reject symlink ancestors and require the permitted study target scope."""
    parts = relative_name(relative).parts
    if destination and not relative.startswith(ALLOWED_PREFIXES):
        raise ValueError("Restoration target is outside the two declared studies")
    cursor = root
    if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
        raise ValueError("Symlink root is unsupported")
    for index, part in enumerate(parts):
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Refuse symlink source or destination: " + relative)
        if index < len(parts) - 1 and cursor.exists() and not cursor.is_dir():
            raise ValueError("A required directory is an existing user file: " + relative)
    return cursor


def verify_bytes(raw: bytes, record: dict[str, Any]) -> None:
    """Require the complete size and SHA256 of an unchanged file."""
    if len(raw) != record["bytes"] or digest(raw) != record["sha256"]:
        raise ValueError("Size or SHA256 mismatch: " + record.get("path", record.get("member", "file")))


def payloads() -> tuple[str, dict[str, tuple[bytes, int]]]:
    """Verify all explicit package bytes before changing any destination."""
    manifest_path = STUDY / "reproduction/RESTORE_MANIFEST.json"
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest.get("schema") != "agi-alpha-reproduction-restore/v1":
        raise ValueError("Unsupported restoration manifest")
    output: dict[str, tuple[bytes, int]] = {}

    def retain(record: dict[str, Any], raw: bytes) -> None:
        relative_name(record["path"])
        if not record["path"].startswith(ALLOWED_PREFIXES):
            raise ValueError("Unexpected target scope")
        verify_bytes(raw, record)
        mode = record.get("mode", 0o644)
        if mode not in {0o644, 0o755}:
            raise ValueError("Unsupported restored file mode")
        previous = output.get(record["path"])
        if previous is not None and previous != (raw, mode):
            raise ValueError("Conflicting explicit target members")
        output[record["path"]] = (raw, mode)

    for package in manifest["archives"]:
        member_manifest_path = ordinary_path(STUDY, package["manifest"])
        raw_members = member_manifest_path.read_bytes()
        if digest(raw_members) != package["manifest_sha256"]:
            raise ValueError("Archive member manifest changed")
        member_manifest = json.loads(raw_members)
        if member_manifest.get("schema") != "lossless-explicit-zip-members/v1":
            raise ValueError("Unsupported archive member manifest")
        archive_path = ordinary_path(STUDY, package["archive"])
        archive_raw = archive_path.read_bytes()
        if len(archive_raw) != package["archive_bytes"] or digest(archive_raw) != package["archive_sha256"]:
            raise ValueError("Archive identity changed: " + package["archive"])
        entries = member_manifest["entries"]
        expected = {entry["member"]: entry for entry in entries}
        if len(expected) != len(entries) or len(entries) != package["members"]:
            raise ValueError("Duplicated or incomplete archive manifest")
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if len(infos) != len(expected) or {i.filename for i in infos} != set(expected):
                raise ValueError("Archive contains missing, extra or duplicated members")
            for info in infos:
                relative_name(info.filename)
                mode = stat.S_IFMT(info.external_attr >> 16)
                if info.is_dir() or mode not in {0, stat.S_IFREG}:
                    raise ValueError("Nonregular archive member")
                record = expected[info.filename]
                if info.file_size != record["bytes"] or info.file_size > 64_000_000:
                    raise ValueError("Unexpected or oversized archive member")
                retain(record, archive.read(info))
    decompressed: dict[str, bytes] = {}
    for record in manifest["compressed_files"]:
        compressed_path = ordinary_path(STUDY, record["gzip"])
        if record["gzip"] not in decompressed:
            packed = compressed_path.read_bytes()
            if len(packed) != record["gzip_bytes"] or digest(packed) != record["gzip_sha256"]:
                raise ValueError("Compressed evidence changed: " + record["gzip"])
            if record["bytes"] > 64_000_000:
                raise ValueError("Unexpectedly large generated evidence")
            with gzip.open(compressed_path, "rb") as stream:
                raw = stream.read(record["bytes"] + 1)
                if stream.read(1):
                    raise ValueError("Expanded evidence exceeds declared size")
            decompressed[record["gzip"]] = raw
        retain(record, decompressed[record["gzip"]])
    if sum(len(value[0]) for value in output.values()) > 512_000_000:
        raise ValueError("Unexpected total restoration size")
    return digest(raw_manifest), output


def restore(destination: Path, *, verify_only: bool = False) -> dict[str, Any]:
    """Preflight every collision, then atomically create only absent exact files."""
    if destination.is_symlink():
        raise ValueError("Refuse symlink destination root")
    destination = destination.absolute()
    for ancestor in [destination, *destination.parents]:
        if ancestor.is_symlink():
            raise ValueError("Refuse symlink destination ancestor")
    manifest_hash, data = payloads()
    missing = []
    existing = 0
    for relative, (raw, mode) in sorted(data.items()):
        target = ordinary_path(destination, relative, destination=True)
        if target.exists():
            if not target.is_file() or target.read_bytes() != raw:
                raise ValueError("Refuse to overwrite differing user file: " + relative)
            existing += 1
        else:
            if verify_only:
                raise FileNotFoundError("Expected restored file is absent: " + relative)
            missing.append((relative, raw, mode))
    if not verify_only:
        for relative, raw, mode in missing:
            target = ordinary_path(destination, relative, destination=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            ordinary_path(destination, relative, destination=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(prefix=".restore-", dir=target.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(raw)
                temporary.chmod(mode)
                # Same-directory hard-link creation is exclusive: an intervening
                # user file or symlink is never replaced by an atomic rename.
                os.link(temporary, target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    return {
        "schema": "exact-study-restoration/v1",
        "restore_manifest_sha256": manifest_hash,
        "verified_files": len(data),
        "verified_raw_bytes": sum(len(x[0]) for x in data.values()),
        "restored_files": len(missing) if not verify_only else 0,
        "already_identical_files": existing,
        "verify_only": verify_only,
        "overwritten_differing_files": 0,
        "original_package_mutations": 0,
        "scientific_experiments_executed": 0,
        "scope": "Exact restoration of known evidence; any subsequent rerun is reproduction, not fresh confirmation",
    }


def main() -> int:
    """Restore into a repository or verify an already restored repository."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-repo", type=Path, default=STUDY.parents[1])
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        result = restore(args.target_repo, verify_only=args.verify_only)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}", "scientific_experiments_executed": 0}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
