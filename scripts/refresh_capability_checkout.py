# SPDX-License-Identifier: Apache-2.0
"""Explicit, source-bound LF repair for reviewed capability checkouts.

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
# Reviewed canonical bytes. Each catalogue digest authenticates its closed source
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
ENTERPRISE_PARENT_SOURCE_HASH = "c64f26fac13d73dc4fb4a591ac6c87c314fc3f8e44449307db77ca4c7df2622f"
ENTERPRISE_PARENT_EXTRA_FILES = EXTRA_FILES | {
    "docs/successor/capabilities/index.html": (
        933102,
        "5c55a089546345eea1a9907cf736f437f28a58ab468342e73308a6ac2aee1634",
    ),
    "docs/successor/capabilities/sources.json": (
        6894,
        "0d8207718f1757e2d5c6707909825f034bb79fe7afcc61ac95eb9b6ffe228e5f",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/index.html": (
        933190,
        "364aa919294001c1c9a154289a97c77abbc349be4824a1a34352d35e6397353c",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/sources.json": (
        6894,
        "0d8207718f1757e2d5c6707909825f034bb79fe7afcc61ac95eb9b6ffe228e5f",
    ),
    "docs/service-worker.js": (23275, "095d2b9ab423ff133ff5ba5ae062b2ec471d10a87c6c24b27df9858765641107"),
    "docs/assets/service-worker.js": (23707, "ba23c3e95d420d2792109aea99afa653e9cdd46f9ce645d26c1f3059dffb16d4"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "20e4dbd3e3780a361bff61b9536d3c22548c558bb87e98b9a2a42e165af6a3e9",
    ),
}
ENTERPRISE_SOURCE_HASH = "54769dbfde99ae13708a33292866f0ca7e6b8b7792a7a944f76bf2fbf1de1358"
ENTERPRISE_EXTRA_FILES = ENTERPRISE_PARENT_EXTRA_FILES | {
    "docs/successor/capabilities/index.html": (
        933603,
        "804f83eab8077d45a2e741a334d4c92be5209de1e9781ea865ed9ffc8487d97e",
    ),
    "docs/successor/capabilities/sources.json": (
        6894,
        "d1c3cb9a5c3eb96e9e5eb111b83a713786ec18ed1213a407cd77bbaf018c5adb",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/index.html": (
        933691,
        "0d9235cf4e9050498c470c44cba74223d1c6481b3abcaf209d72ba794417a071",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/sources.json": (
        6894,
        "d1c3cb9a5c3eb96e9e5eb111b83a713786ec18ed1213a407cd77bbaf018c5adb",
    ),
    "docs/service-worker.js": (23275, "7b6204079cd78d5cb92e91a9b6af4bfde99c01e765292697289fcfbff8a83f5d"),
    "docs/assets/service-worker.js": (23707, "0db9a2730d24548c730601bd56a5fae3dab82359df6402736f29c0b87378108c"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "e02eb78e93d637475c5db53a2fe21efcabf85b410fd0ba450f155d7379dd652a",
    ),
}
# The 1.39 edition retains the same scientific catalogue and complete source
# closure. Only these three generated gallery workers have new reviewed bytes.
ENTERPRISE_139_EXTRA_FILES = ENTERPRISE_EXTRA_FILES | {
    "docs/service-worker.js": (23275, "ac2035bc13defd9e1118969eae165106d5eac952ee7d69b54f54c05f0664ff44"),
    "docs/assets/service-worker.js": (23707, "76eb433503202b0020a1df522afed3686b5f6d846634ff481bf57dced64685d6"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "a36cc805ecbbefad9ac5b393c9aa42312f60d952802aa8ae7ff896d536d49549",
    ),
}
# The corrected 1.39 release metadata changes the gallery cache digest. Retain
# the initial edition and admit this complete, separately reviewed byte closure.
ENTERPRISE_139_RELEASE_EXTRA_FILES = ENTERPRISE_139_EXTRA_FILES | {
    "docs/service-worker.js": (23275, "93f8bf1fdab5d1af5cc4940f71617033ba35892cf19f8ea943cd147f877e77ad"),
    "docs/assets/service-worker.js": (23707, "00f8c57a5914aa30e686a72ce1954199262546ecb6ee22e4fb6e33f2b58b278f"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "ec3b9aacbbe712af09575219d9164f5058970c70fa4900c0e0daa2b028e516d0",
    ),
}
# Moving the retained enterprise preview outside the paper renderer's markers
# creates one further exact cache edition; every prior edition stays admitted.
ENTERPRISE_139_PRESENTATION_EXTRA_FILES = ENTERPRISE_139_RELEASE_EXTRA_FILES | {
    "docs/service-worker.js": (23275, "ac1621a5e9efd104e56ff3865c0784e22a968975dc7b8465682b5528e9e967fd"),
    "docs/assets/service-worker.js": (23707, "64654fce9864c5f792e6b7e5bb595d85366ae4491ba179f7595e1bfa24d5e161"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "be9396acf43738b48a233c24517e8a3d06a8b1a36a00448b50be7e8792b7b8a3",
    ),
}
# The complete enterprise-paper catalogue keeps the same scientific source closure.
# Admit its final 1.40 gallery workers as one whole edition; preserve all prior
# editions and reject combinations of their individually valid worker bytes.
FOUNDRY_140_EXTRA_FILES = ENTERPRISE_139_PRESENTATION_EXTRA_FILES | {
    "docs/service-worker.js": (23275, "7d0d5084198377c0c0d0cf55c6d0c7d3c1036d60781dfc8e575f58311d575823"),
    "docs/assets/service-worker.js": (23707, "24e955673e33c603f768a84aa013e446eaa21c80c6d2f5f284f731c8c3e05816"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "4154e0b378cd411eca9e1f9630cd191632f96f06fdc1492a9bfd10d719db0907",
    ),
}
# The three bilingual guides and reconciled Discoverability add four cache inputs.
# Admit only this complete generated worker edition; all older editions remain exact.
RESEARCH_GUIDES_140_EXTRA_FILES = FOUNDRY_140_EXTRA_FILES | {
    "docs/service-worker.js": (23479, "6a7d7a7b226a9fc4cd1293e4de891a120b843024b6ab9ae2dd6fc6cb773f5269"),
    "docs/assets/service-worker.js": (23915, "f0fa0894af4f9388a6a0145d6ab660b394b8250c595c6d6d7c60ff529c83fda2"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26531,
        "857aa6fbb8549585329634c1c57865d2b25045daf9c5baf8fb5e9350841752ae",
    ),
}

# The corrected companion/site presentation advances only the three deterministic
# gallery workers. Admit this one complete 1.41 edition, retaining all eight
# historical editions and refusing mixtures of their otherwise valid bytes.
COMPANION_141_EXTRA_FILES = RESEARCH_GUIDES_140_EXTRA_FILES | {
    "docs/service-worker.js": (23479, "38c6a923ebc6c0ba67f53506ec58f10d16f652510f6fb87fbd0785a3946b20cd"),
    "docs/assets/service-worker.js": (23915, "f59fba7120c017bfabe7f464e24a89b339ff308d07f8ea60e831ee808cedec4e"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26531,
        "e85ca20e82b99cd627843192df78e104391b5b4f169c44f66512a1c2136b437d",
    ),
}

SourceProfile = tuple[str, int, int, dict[str, tuple[int, str]]]


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


def _source_profiles(raw: bytes) -> list[SourceProfile]:
    digest = _hash(raw.replace(b"\r\n", b"\n"))
    profiles = []
    for source_hash, source_count, file_count, extra in (
        (SOURCE_HASH, 41, 49, EXTRA_FILES),
        (ENTERPRISE_PARENT_SOURCE_HASH, 53, 61, ENTERPRISE_PARENT_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, ENTERPRISE_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, ENTERPRISE_139_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, ENTERPRISE_139_RELEASE_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, ENTERPRISE_139_PRESENTATION_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, FOUNDRY_140_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, RESEARCH_GUIDES_140_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, COMPANION_141_EXTRA_FILES),
    ):
        if digest == extra[CATALOG][1]:
            profiles.append((source_hash, source_count, file_count, extra))
    if not profiles:
        raise ValueError("Private or unexpected capability bytes; nothing refreshed: " + CATALOG)
    return profiles


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_mode, value.st_uid, value.st_gid)


def _unchanged(root: Path, records: list[Record]) -> None:
    for record in records:
        raw, status = _read(root, record["path"])
        if raw != record["raw"] or _fingerprint(status) != _fingerprint(record["status"]):
            raise ValueError("Checkout changed during repair; stop and retain backup: " + record["path"])


def _profile_records(root: Path, catalog_raw: bytes, profile: SourceProfile) -> list[Record]:
    """Validate the entire fixed byte edition without writing or accepting a mixture."""
    source_hash, source_count, file_count, extra = profile
    catalog_bytes = _canonical(catalog_raw, extra[CATALOG][1], extra[CATALOG][0], CATALOG)
    catalog = json.loads(catalog_bytes)
    sources = catalog["sources"]
    if (
        catalog["schema"] != "successor-capability-source/v1"
        or len(sources) != source_count
        or catalog["sourceHash"] != source_hash
        or _hash(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()) != source_hash
    ):
        raise ValueError("Unsupported capability source identity")
    expected: dict[str, tuple[int | None, str]] = {name: (None, digest) for name, digest in sources.items()}
    expected.update(extra)
    if len(expected) != file_count:
        raise ValueError("Unsupported capability repair closure")
    records: list[Record] = []
    for name, (size, digest) in sorted(expected.items()):
        raw, status = _read(root, name)
        canonical = _canonical(raw, digest, size, name)
        records.append({"path": name, "raw": raw, "canonical": canonical, "status": status})
    if sum(len(r["raw"]) for r in records) > MAX_TOTAL_BYTES:
        raise ValueError("Capability repair exceeds total bound")
    return records


def refresh(root: Path = ROOT, *, apply: bool = False, backup_parent: Path | None = None) -> RefreshResult:
    """Check one complete exact closure before any backup or canonical-byte replacement."""
    root = root.resolve(strict=True)
    catalog_raw, _ = _read(root, CATALOG)
    failure: ValueError | None = None
    for profile in _source_profiles(catalog_raw):
        try:
            records = _profile_records(root, catalog_raw, profile)
        except ValueError as error:
            failure = error
        else:
            source_hash, _, file_count, _ = profile
            break
    else:
        assert failure is not None
        raise failure
    changed = [r for r in records if r["raw"] != r["canonical"]]
    result: RefreshResult = {
        "schema": "capability-lf-checkout-refresh/v1",
        "sourceHash": source_hash,
        "checked": file_count,
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
    manifest = {"schema": "capability-lf-original-backup/v1", "sourceHash": source_hash, "files": backup_files}
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
