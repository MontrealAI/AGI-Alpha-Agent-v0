# SPDX-License-Identifier: Apache-2.0
"""Explicit, source-bound LF repair for the reviewed 1.38.0 capability checkout.

No Git command, index/configuration change or generator runs here. Unexpected
content refuses the entire plan; original raw bytes stay in a private backup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "docs/successor/capabilities/sources.json"
SOURCE_HASH = "644258ac21cc938aff861d02ad728e8f3c9716f6ea78700acc35e4d7400eebf2"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
# Reviewed canonical bytes. The catalogue digest authenticates all 41 source
# paths/hashes, so an edited catalogue cannot choose its own repair targets.
EXTRA_FILES = {
    "examples/successor-capability/discovery-lab-reproduce.mjs": (
        7903,
        "21aabff4e543789f6ddbc074fcf7e0a3ea706cada55345f680f4edcb7afac894",
    ),
    "docs/successor/capabilities/index.html": (
        782569,
        "7ce110be53cf4c699984c0cfd20e0e7d7434c463a676fe1dfb9498589e5319d3",
    ),
    "docs/successor/capabilities/sources.json": (
        5416,
        "9cddd00ed38a3500efeaac8977bf3db46363face0cfe56e713ec91750662e09a",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/index.html": (
        782651,
        "bb8013b57a00134ef6c80b3ba840b013ec9dca76ec1ed14e2738a9a5bbc6cc9a",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/sources.json": (
        5416,
        "9cddd00ed38a3500efeaac8977bf3db46363face0cfe56e713ec91750662e09a",
    ),
    "docs/service-worker.js": (23275, "fb8fd61467254b4af045443aa5f0575259b26129290958bf667c67a7deda75bb"),
    "docs/assets/service-worker.js": (23707, "d2b72a7115364078ab7c2212fab53c43452e8af6d644d1a16926c61a594619b0"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "0b067ee54afeea5a22b7737deb752168d5d2ff6a4d7404a406579ea3f79df247",
    ),
}


class Record(TypedDict):
    path: str
    raw: bytes
    canonical: bytes
    status: os.stat_result


class RefreshResult(TypedDict):
    schema: str
    sourceHash: str
    checked: int
    needsRefresh: list[str]
    applied: bool
    backupDirectory: str | None


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(root: Path, name: str) -> tuple[bytes, os.stat_result]:
    parts = PurePosixPath(name).parts
    if not parts or name != "/".join(parts) or any(p in {"", ".", ".."} for p in parts) or "\\" in name:
        raise ValueError("Invalid fixed capability path")
    if PurePosixPath(name).is_absolute():
        raise ValueError("Absolute capability path")
    path = root
    for part in parts[:-1]:
        path /= part
        if not stat.S_ISDIR(path.lstat().st_mode):
            raise ValueError("Capability parent must be a direct directory: " + name)
    path /= parts[-1]
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
        raise ValueError("Capability input must be a bounded regular file: " + name)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("Capability input changed while opening: " + name)
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Capability input exceeds repair bound: " + name)
    return raw, opened


def _canonical(raw: bytes, expected: str, size: int | None, name: str) -> bytes:
    canonical = raw.replace(b"\r\n", b"\n")
    if b"\r" in canonical or _hash(canonical) != expected or size is not None and len(canonical) != size:
        raise ValueError("Private or unexpected capability bytes; nothing refreshed: " + name)
    if raw not in {canonical, canonical.replace(b"\n", b"\r\n")}:
        raise ValueError("Mixed line endings require manual review; nothing refreshed: " + name)
    return canonical


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_mode, value.st_uid, value.st_gid)


def _unchanged(root: Path, records: list[Record]) -> None:
    for record in records:
        raw, status = _read(root, record["path"])
        if raw != record["raw"] or _fingerprint(status) != _fingerprint(record["status"]):
            raise ValueError("Checkout changed during repair; stop and retain backup: " + record["path"])


def refresh(root: Path = ROOT, *, apply: bool = False, backup_parent: Path | None = None) -> RefreshResult:
    """Check the complete closed49 before any backup or canonical-byte replacement."""
    root = root.resolve(strict=True)
    catalog_raw, _ = _read(root, CATALOG)
    catalog_bytes = _canonical(catalog_raw, EXTRA_FILES[CATALOG][1], EXTRA_FILES[CATALOG][0], CATALOG)
    catalog = json.loads(catalog_bytes)
    sources = catalog["sources"]
    if (
        catalog["schema"] != "successor-capability-source/v1"
        or len(sources) != 41
        or catalog["sourceHash"] != SOURCE_HASH
        or _hash(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()) != SOURCE_HASH
    ):
        raise ValueError("Unsupported capability source identity")
    expected: dict[str, tuple[int | None, str]] = {name: (None, digest) for name, digest in sources.items()}
    expected.update(EXTRA_FILES)
    if len(expected) != 49:
        raise ValueError("Unsupported capability repair closure")
    records: list[Record] = []
    for name, (size, digest) in sorted(expected.items()):
        raw, status = _read(root, name)
        canonical = _canonical(raw, digest, size, name)
        records.append({"path": name, "raw": raw, "canonical": canonical, "status": status})
    if sum(len(r["raw"]) for r in records) > MAX_TOTAL_BYTES:
        raise ValueError("Capability repair exceeds total bound")
    changed = [r for r in records if r["raw"] != r["canonical"]]
    result: RefreshResult = {
        "schema": "capability-lf-checkout-refresh/v1",
        "sourceHash": SOURCE_HASH,
        "checked": 49,
        "needsRefresh": [r["path"] for r in changed],
        "applied": False,
        "backupDirectory": None,
    }
    if not apply or not changed:
        result["applied"] = apply
        return result
    parent = (backup_parent or Path(tempfile.gettempdir())).resolve(strict=True)
    if not parent.is_dir() or parent == root or parent.is_relative_to(root):
        raise ValueError("Choose an existing backup parent outside the checkout")
    _unchanged(root, records)
    backup = Path(tempfile.mkdtemp(prefix="capability-lf-backup-", dir=parent))
    backup.chmod(0o700)
    backup_files: list[dict[str, str | int]] = []
    manifest = {"schema": "capability-lf-original-backup/v1", "sourceHash": SOURCE_HASH, "files": backup_files}
    # Every original is retained before staging or replacing any checkout file.
    for record in records:
        destination = backup / "files" / record["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(record["raw"])
        destination.chmod(0o600)
        backup_files.append(
            {
                "path": record["path"],
                "bytes": len(record["raw"]),
                "sha256": _hash(record["raw"]),
                "mode": stat.S_IMODE(record["status"].st_mode),
            }
        )
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    staged: list[tuple[Record, Path]] = []
    applied: list[str] = []
    try:
        _unchanged(root, records)
        for record in changed:
            target = root / record["path"]
            descriptor, temporary = tempfile.mkstemp(prefix="." + target.name + ".lf-", dir=target.parent)
            staged.append((record, Path(temporary)))
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(record["canonical"])
                stream.flush()
                os.fsync(stream.fileno())
                if hasattr(os, "fchmod"):
                    os.fchmod(stream.fileno(), stat.S_IMODE(record["status"].st_mode))
            if not hasattr(os, "fchmod"):
                Path(temporary).chmod(stat.S_IMODE(record["status"].st_mode))
        _unchanged(root, records)
        for record, temporary in staged:
            raw, status = _read(root, record["path"])
            if raw != record["raw"] or _fingerprint(status) != _fingerprint(record["status"]):
                raise ValueError("Checkout changed during repair: " + record["path"])
            os.replace(temporary, root / record["path"])
            applied.append(record["path"])
    except (OSError, ValueError) as error:
        (backup / "result.json").write_text(json.dumps({"applied": applied, "complete": False}) + "\n")
        raise RuntimeError("Refresh stopped; original bytes retained at " + str(backup)) from error
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)
    (backup / "result.json").write_text(json.dumps({"applied": applied, "complete": True}) + "\n")
    result.update(applied=True, backupDirectory=str(backup))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--apply", action="store_true", help="Explicitly refresh only prevalidated CRLF capability files"
    )
    parser.add_argument(
        "--backup-parent", type=Path, help="Existing external directory for a new private retained backup"
    )
    arguments = parser.parse_args()
    print(json.dumps(refresh(arguments.root, apply=arguments.apply, backup_parent=arguments.backup_parent), indent=2))
