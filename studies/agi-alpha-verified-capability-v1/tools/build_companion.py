#!/usr/bin/env python3
"""Build and verify a complete, explicitly deduplicated research companion.

The plan command does not create an archive. Build requires an explicit command.
Every excluded file is listed with its original digest and recovery instructions.
The archive stores deliberate symlinks as inert, reversible metadata records.
No production, simulator, browser or publication build is executed here.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import time
import zipfile
import zlib

SCHEMA = "agi-alpha-complete-research-companion/v1"
PREFIX = "AGI_ALPHA_Verified_Capability_Companion"
MANIFEST = "COMPANION_MANIFEST.json"
MANIFEST_HASH = "COMPANION_MANIFEST.sha256"
GUIDE = "COMPANION_README.txt"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
ALREADY_COMPRESSED = {".zip", ".whl", ".gz", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".woff", ".woff2"}
REQUIRED = (
    "README.md", "src/production.py", "src/acceptance.py", "src/run_campaign.mjs",
    "protocol/production-freeze.json", "protocol/market-freeze.json",
    "evidence/production-summary.json", "evidence/production-primary/summary.json",
    "evidence/market-primary/summary.json", "evidence/market-primary/execution.json",
    "evidence/market-primary/complete-worlds.jsonl.gz", "evidence/market-primary/compact-worlds.jsonl",
    "evidence/market-primary/representative-histories.json",
    "heritage/foundations/merkle.pdf", "heritage/foundations/proof_loops.pdf",
    "review/production-reconciliation-02.json", "review/market-reconciliation-01.json",
    "review/reconcile_production.py", "review/reconcile_market.mjs",
    "paper/manuscript.tex", "paper/AGI_ALPHA_Economy_of_Verified_Capability.pdf",
    "demo/index.html", "tools/verify_frozen.py", "tools/reproduce.py", "tools/build_companion.py",
)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def safe_relative(value):
    require(isinstance(value, str) and value and "\\" not in value and "\0" not in value, "UNSAFE_PATH")
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts), "UNSAFE_PATH")
    return path


def contained(root, relative):
    relative = safe_relative(relative)
    path = root.joinpath(*relative.parts)
    require(path.resolve(strict=False).is_relative_to(root), "PATH_ESCAPES_ROOT: " + str(relative))
    return path


def fingerprint(path):
    item = path.lstat()
    return (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns, item.st_ctime_ns)


def inventory(root):
    """Do not follow any symlink, including directory symlinks."""
    entries, empty = [], []
    for directory, directories, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        if not directories and not files and parent != root:
            empty.append(parent.relative_to(root).as_posix())
        links = [name for name in directories if (parent / name).is_symlink()]
        directories[:] = sorted(name for name in directories if name not in links)
        for name in sorted(files + links):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            safe_relative(relative)
            mode = path.lstat().st_mode
            require(stat.S_ISREG(mode) or stat.S_ISLNK(mode), "UNSUPPORTED_NONREGULAR_ENTRY: " + relative)
            entries.append((relative, path, "symlink" if stat.S_ISLNK(mode) else "file"))
    return sorted(entries), sorted(empty)


def guide(prefix):
    return f"""AGI ALPHA — complete verified-capability research companion

This is a research artifact, not an operating deployment or a commercial receipt.
All 72 production decision-packet ZIPs and the complete market history gzip are
retained. There are zero observed customer jobs or collections in this experiment.

Verify after extraction, from the extracted companion directory:
  python3 tools/build_companion.py verify --root .
  python3 tools/verify_frozen.py --root .

Independent evidence audits, without rerunning production or the simulator:
  python3 review/reconcile_production.py --root . --output review/production-reconciliation-NEW.json
  node review/reconcile_market.mjs --root . --output review/market-reconciliation-NEW.json
The production verifier requires its recorded native marker environment and tools.
See README.md and paper/README.md for all scientific scope and environment limits.

Every omitted staging wheel is byte-identical to a retained inputs/wheels file.
Its original path, size, SHA-256 and canonical recovery path appear in the manifest.
Restore exact staged wheel bytes only if needed (about the recorded omitted bytes):
  python3 tools/build_companion.py restore-wheels --root .

Deliberate test symlinks are inert COMPANION_LINKS records by default. Original
target bytes are preserved as base64 with their SHA-256; arbitrary targets are
never followed. Optional internal rebasing is explicit and keeps the raw record:
  python3 tools/build_companion.py restore-links --root .

Excluded bytecode, temporary LaTeX build files and internal browser/page PNGs have
individual omission records. Regeneration is documented; original transient-byte
identity is not promised. Original foundation papers, licenses, working sources,
all unique research outputs, prior review failures, ledgers and full cash histories
remain included. No unknown scientific result is replaced by a regenerated value.

Repack this exact verified payload into a fresh directory without recreating caches:
  python3 tools/build_companion.py repack --root . --delivery ../repacked
ZIP paths, order, timestamps and permissions are normalized. Byte-identical ZIP
repacking requires the same recorded Python/zipfile/zlib implementation; payload
SHA-256 verification is independent of compression implementation.

COMPANION_MANIFEST.json lists every payload file and every omission. Its checksum
is in COMPANION_MANIFEST.sha256. The external {prefix}.sha256 also binds the ZIP
and the external identical manifest. Hashes establish integrity, not truth, live
signer authentication, technical scope beyond the certificates, or economic value.
""".encode("utf-8")


def omission_reason(relative, root):
    parts = PurePosixPath(relative).parts
    if "__pycache__" in parts:
        path = PurePosixPath(relative)
        stem = re.split(r"\.(?:cpython-|pypy)", path.name, maxsplit=1)[0]
        source = path.parent.parent / (stem + ".py")
        recovery = source.as_posix() if (root / source).is_file() else "tools/reproduce.py"
        return "GENERATED_PYTHON_BYTECODE", recovery, {
            "kind": "regenerate_cache", "command": ["python3", "-m", "compileall", "-q", recovery],
            "byte_identity_guaranteed": False,
            "note": "Transient bytecode depends on interpreter and source timestamps; source and original omitted digest are retained.",
        }
    if relative.startswith("paper/build/"):
        return "TEMPORARY_PUBLICATION_BUILD", "paper/build.py", {
            "kind": "regenerate_publication_build", "command": ["python3", "paper/build.py"],
            "byte_identity_guaranteed": False,
            "note": "Working LaTeX/compiler/cache material; final PDF, source, figures and build receipts are retained.",
        }
    if relative.startswith("paper/rendered/"):
        return "INTERNAL_PUBLICATION_VISUAL_QA", "paper/AGI_ALPHA_Economy_of_Verified_Capability.pdf", {
            "kind": "rerender_pdf", "command": ["pdftoppm", "-png", "-r", "144", "paper/AGI_ALPHA_Economy_of_Verified_Capability.pdf", "page"],
            "byte_identity_guaranteed": False,
            "note": "Internal page/contact-sheet render; prior pixel hash retained. Exact historical rendering is not asserted recoverable.",
        }
    if relative.startswith("demo/browser-review/") and relative.lower().endswith(".png"):
        return "INTERNAL_BROWSER_VISUAL_QA", "demo/index.html", {
            "kind": "rerender_browser", "recipe": "demo/test_browser.mjs",
            "checks": "demo/browser-review/checks.json", "byte_identity_guaranteed": False,
            "note": "Internal browser screenshot. HTML, browser checks, viewport evidence and original screenshot digest are retained.",
        }
    return None


def make_plan(root, prefix):
    require(re.fullmatch(r"[A-Za-z0-9_-]+", prefix), "UNSAFE_ARCHIVE_PREFIX")
    require(not (root / MANIFEST).exists(), "PACKAGED_TREE: use repack to preserve its exact manifest")
    entries, empty = inventory(root)
    by_path = {relative: (path, kind) for relative, path, kind in entries}
    require(all(name in by_path for name in REQUIRED), "MISSING_REQUIRED_DELIVERABLE: " + ", ".join(name for name in REQUIRED if name not in by_path))
    cache, snapshots, source_rows = {}, {}, []

    def hashed(path):
        before = fingerprint(path)
        if before not in cache:
            cache[before] = file_digest(path)
        require(fingerprint(path) == before, "SOURCE_CHANGED_DURING_HASH: " + str(path))
        return cache[before], before

    wheels = {}
    for relative, path, kind in entries:
        if kind == "file" and relative.startswith("inputs/wheels/") and relative.endswith(".whl"):
            value, before = hashed(path)
            wheels.setdefault((before[3], value), []).append(relative)
    require(len(wheels) >= 47, "COMPLETE_CANONICAL_WHEEL_SET_REQUIRED")
    payload, included, omitted, links = {}, [], [], []
    for relative, path, kind in entries:
        before = fingerprint(path)
        snapshots[relative] = before
        source_mode = stat.S_IMODE(before[2])
        mode = 0o755 if source_mode & 0o111 else 0o644
        if kind == "symlink":
            raw = os.readlink(os.fsencode(path))
            value = digest(raw)
            row = {"path": relative, "kind": "symlink", "bytes": len(raw), "sha256": value, "source_mode": source_mode}
            source_rows.append(row)
            target = path.parent / os.fsdecode(raw)
            lexical = Path(os.path.abspath(target))
            canonical = lexical.relative_to(root).as_posix() if lexical.is_relative_to(root) else None
            target_entry = by_path.get(canonical) if canonical else None
            target_hash = hashed(target_entry[0])[0] if target_entry and target_entry[1] == "file" else None
            record_path = "COMPANION_LINKS/" + digest(relative.encode()) + ".json"
            record = {**row, "original_target_base64": base64.b64encode(raw).decode("ascii"),
                "original_target_display": os.fsdecode(raw), "canonical_recovery_path": canonical,
                "canonical_target_sha256": target_hash, "representation": "INERT_SYMLINK_RECORD",
                "restoration": "Explicit restore-links may create a safe internal relative link only; raw original target bytes remain unchanged in this record."}
            data = json_bytes(record)
            payload[record_path] = data
            included.append({"path": record_path, "bytes": len(data), "sha256": digest(data), "mode": 0o644, "origin": "inert_original_symlink_record"})
            links.append({**record, "archive_record": record_path, "archive_record_sha256": digest(data)})
            continue
        value, before = hashed(path)
        source = {"path": relative, "kind": "file", "bytes": before[3], "sha256": value, "source_mode": source_mode}
        source_rows.append(source)
        reason = omission_reason(relative, root)
        if reason is None and relative.endswith(".whl") and not relative.startswith("inputs/wheels/"):
            matches = wheels.get((before[3], value), [])
            # Only identical bytes, not wheel names or version strings, authorize omission.
            if matches:
                canonical = sorted(matches)[0]
                reason = ("BYTE_IDENTICAL_STAGED_WHEEL_COPY", canonical, {
                    "kind": "byte_copy", "path": canonical, "sha256": value, "byte_identity_guaranteed": True,
                    "command": "python3 tools/build_companion.py restore-wheels --root .",
                })
        if reason:
            why, canonical, recovery = reason
            omitted.append({**source, "reason": why, "canonical_recovery_path": canonical, "recovery": recovery})
        else:
            payload[relative] = path
            included.append({"path": relative, "bytes": before[3], "sha256": value, "mode": mode, "origin": "study_file"})
    generated_guide = guide(prefix)
    payload[GUIDE] = generated_guide
    included.append({"path": GUIDE, "bytes": len(generated_guide), "sha256": digest(generated_guide), "mode": 0o644, "origin": "generated_companion_guide"})
    included.sort(key=lambda row: row["path"])
    included_paths = {row["path"] for row in included}
    for row in omitted:
        require(row["canonical_recovery_path"] in included_paths, "RECOVERY_SOURCE_NOT_INCLUDED: " + row["path"])
    frozen_checks = []
    for frozen_path in ("protocol/production-freeze.json", "protocol/market-freeze.json"):
        frozen = load(root / frozen_path)
        for row in frozen["files"]:
            require(row["path"] in included_paths, "FROZEN_FILE_EXCLUDED: " + row["path"])
            current = next(item for item in included if item["path"] == row["path"])
            require(current["sha256"] == row["sha256"] and current["bytes"] == row["bytes"], "FROZEN_FILE_CHANGED: " + row["path"])
        frozen_checks.append({"path": frozen_path, "sha256": hashed(root / frozen_path)[0], "files": len(frozen["files"]), "unchanged": True})
    packet_zips = sorted(name for name in included_paths if name.startswith("evidence/production-primary/") and name.endswith("/decision-packet.zip"))
    require(len(packet_zips) == 72, "ALL_72_PRODUCTION_DECISION_PACKET_ZIPS_REQUIRED")
    market = load(root / "evidence/market-primary/execution.json")
    gzip_row = next(row for row in included if row["path"] == "evidence/market-primary/complete-worlds.jsonl.gz")
    require(market["complete"] and market["completedWorlds"] == 1152 and gzip_row["sha256"] == market["compressedWorldsSHA256"], "COMPLETE_MARKET_HISTORY_IDENTITY_REQUIRED")
    manifest = {
        "schema": SCHEMA, "archive_root": prefix,
        "source_tree_sha256": digest(json_bytes(sorted(source_rows, key=lambda row: row["path"]))),
        "included_files": included, "omissions": omitted, "symbolic_links": links,
        "original_empty_directories": empty,
        "inventory": {"source_entries": len(source_rows), "source_regular_files": len(source_rows) - len(links),
            "source_symlinks": len(links), "original_logical_bytes": sum(row["bytes"] for row in source_rows),
            "included_payload_files": len(included), "included_payload_bytes": sum(row["bytes"] for row in included),
            "omitted_files": len(omitted), "omitted_logical_bytes": sum(row["bytes"] for row in omitted),
            "omissions_by_reason": dict(sorted(Counter(row["reason"] for row in omitted).items()))},
        "zip_policy": {"entry_order": "lexicographic POSIX path", "timestamp": list(ZIP_TIME),
            "regular_modes": "0644 or0755 according to source executable bits", "symlinks": "inert reversible JSON records; never followed",
            "compression": "DEFLATE level9 for text; STORED for already compressed suffixes", "stored_suffixes": sorted(ALREADY_COMPRESSED),
            "python": sys.version.split()[0], "zlib": zlib.ZLIB_VERSION, "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
            "byte_repacking_scope": "Identical payload and manifest with the same compression implementation produce the same ZIP bytes."},
        "preservation": {"frozen_checks": frozen_checks, "production_decision_packet_zips": packet_zips,
            "complete_market_gzip_sha256": gzip_row["sha256"], "paired_worlds": 1152, "enterprise_histories": 3456,
            "original_foundation_papers": [row for row in included if row["path"] in {"heritage/foundations/merkle.pdf", "heritage/foundations/proof_loops.pdf"}],
            "observed_customer_jobs": 0, "actual_collections": 0},
        "hash_boundary": "Manifest and its checksum are excluded from their own file list. The external SHA256 file binds the archive and identical external manifest. Hashes prove integrity only.",
        "recovery_boundary": "Only staging-wheel omissions promise exact byte recovery. Transient cache/build/render omissions retain their original digest and reproducible recipe but may regenerate different bytes. All unique retained research data and prior findings are included.",
    }
    return manifest, payload, snapshots


def metadata(relative, mode, method):
    info = zipfile.ZipInfo(relative, ZIP_TIME)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = method
    info._compresslevel = 9
    return info


def write_archive(archive_path, manifest, payload):
    prefix = manifest["archive_root"]
    manifest_data = json_bytes(manifest)
    wrappers = {MANIFEST: manifest_data, MANIFEST_HASH: (digest(manifest_data) + "  " + MANIFEST + "\n").encode()}
    rows = {row["path"]: row for row in manifest["included_files"]}
    with zipfile.ZipFile(archive_path, "x", allowZip64=True) as archive:
        directories = {directory + "/" for directory in manifest["original_empty_directories"]}
        for relative in sorted(set(payload) | set(wrappers) | directories):
            if relative in directories:
                info = zipfile.ZipInfo(prefix + "/" + relative, ZIP_TIME)
                info.create_system = 3
                info.external_attr = (stat.S_IFDIR | 0o755) << 16
                archive.writestr(info, b"")
                continue
            data = wrappers.get(relative)
            row = rows.get(relative)
            mode = row["mode"] if row else 0o644
            method = zipfile.ZIP_STORED if PurePosixPath(relative).suffix.lower() in ALREADY_COMPRESSED else zipfile.ZIP_DEFLATED
            info = metadata(prefix + "/" + relative, mode, method)
            if data is None:
                source = payload[relative]
                data = source.read_bytes() if isinstance(source, Path) else source
                require(len(data) == row["bytes"] and digest(data) == row["sha256"], "PAYLOAD_CHANGED_DURING_ARCHIVE: " + relative)
            archive.writestr(info, data)
    return manifest_data


def verify_archive(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "DUPLICATE_ZIP_MEMBER")
        manifests = [name for name in names if name.endswith("/" + MANIFEST)]
        require(len(manifests) == 1, "SINGLE_COMPANION_MANIFEST_REQUIRED")
        raw = archive.read(manifests[0])
        manifest = json.loads(raw)
        require(manifest["schema"] == SCHEMA, "UNSUPPORTED_MANIFEST")
        prefix = manifest["archive_root"]
        require(manifests[0] == prefix + "/" + MANIFEST, "MANIFEST_ROOT_MISMATCH")
        expected = {prefix + "/" + row["path"] for row in manifest["included_files"]} | {prefix + "/" + MANIFEST, prefix + "/" + MANIFEST_HASH}
        expected |= {prefix + "/" + directory + "/" for directory in manifest["original_empty_directories"]}
        require(set(names) == expected, "ARCHIVE_INVENTORY_MISMATCH")
        require(archive.read(prefix + "/" + MANIFEST_HASH).decode() == digest(raw) + "  " + MANIFEST + "\n", "MANIFEST_CHECKSUM_MISMATCH")
        for row in manifest["included_files"]:
            safe_relative(row["path"])
            data = archive.read(prefix + "/" + row["path"])
            require(len(data) == row["bytes"] and digest(data) == row["sha256"], "ARCHIVED_PAYLOAD_IDENTITY: " + row["path"])
        # archive.read checks each CRC while every listed payload is hashed above.
    return manifest


def verify_extracted(root):
    raw = (root / MANIFEST).read_bytes()
    manifest = json.loads(raw)
    require(manifest["schema"] == SCHEMA, "UNSUPPORTED_MANIFEST")
    require((root / MANIFEST_HASH).read_text() == digest(raw) + "  " + MANIFEST + "\n", "MANIFEST_CHECKSUM_MISMATCH")
    for row in manifest["included_files"]:
        path = contained(root, row["path"])
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == row["bytes"]
                and file_digest(path) == row["sha256"], "EXTRACTED_PAYLOAD_IDENTITY: " + row["path"])
    for row in manifest["symbolic_links"]:
        record = load(contained(root, row["archive_record"]))
        target_bytes = base64.b64decode(record["original_target_base64"], validate=True)
        require(digest(target_bytes) == row["sha256"] and len(target_bytes) == row["bytes"], "ORIGINAL_LINK_RECORD_CHANGED")
    return manifest


def save_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def emit_build(root, delivery, prefix, manifest, payload, snapshots=None):
    delivery.mkdir(parents=True, exist_ok=True)
    archive = delivery / (prefix + ".zip")
    manifest_path = delivery / (prefix + ".manifest.json")
    sums = delivery / (prefix + ".sha256")
    receipt_path = delivery / (prefix + ".build.json")
    temporary = delivery / (prefix + ".partial.zip")
    require(all(not p.exists() for p in [archive, manifest_path, sums, receipt_path, temporary]), "PRESERVE_EXISTING_DELIVERY_FILES")
    started, cpu_started = time.perf_counter(), time.process_time()
    try:
        raw_manifest = write_archive(temporary, manifest, payload)
        verify_archive(temporary)
        if snapshots is not None:
            current, _ = inventory(root)
            require({relative for relative, _, _ in current} == set(snapshots), "SOURCE_INVENTORY_CHANGED_DURING_BUILD")
            for relative, path, _ in current:
                require(fingerprint(path) == snapshots[relative], "SOURCE_CHANGED_DURING_BUILD: " + relative)
        require(not archive.exists(), "PRESERVE_EXISTING_ARCHIVE")
        temporary.rename(archive)
        save_new(manifest_path, raw_manifest)
        archive_hash = file_digest(archive)
        save_new(sums, (archive_hash + "  " + archive.name + "\n" + digest(raw_manifest) + "  " + manifest_path.name + "\n").encode())
        receipt = {"schema": "agi-alpha-companion-build-receipt/v1", "complete": True,
            "archive": archive.name, "archive_sha256": archive_hash, "archive_bytes": archive.stat().st_size,
            "manifest_sha256": digest(raw_manifest), "source_tree_sha256": manifest["source_tree_sha256"],
            "inventory": manifest["inventory"], "all_payload_members_verified": True,
            "production_decision_packet_zips": len(manifest["preservation"]["production_decision_packet_zips"]),
            "market_histories_retained": manifest["preservation"]["enterprise_histories"],
            "resources": {"elapsed_seconds": time.perf_counter() - started, "cpu_seconds": time.process_time() - cpu_started},
            "source_modified": False, "production_or_simulator_executions": 0}
        save_new(receipt_path, json_bytes(receipt))
        return receipt
    except Exception as error:
        failure = {"schema": "agi-alpha-companion-build-failure/v1", "complete": False,
            "error": type(error).__name__ + ": " + str(error), "partial_archive": temporary.name if temporary.exists() else None,
            "automatic_retry": False, "original_sources_modified": False}
        failure_path = delivery / (prefix + ".failed.json")
        if not failure_path.exists():
            save_new(failure_path, json_bytes(failure))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "build", "repack", "verify", "verify-archive", "extract", "restore-wheels", "restore-links"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--delivery", type=Path)
    parser.add_argument("--prefix", default=PREFIX)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command in {"plan", "build", "repack"}:
        delivery = (args.delivery or root.parent / "delivery").resolve()
        require(not delivery.is_relative_to(root), "DELIVERY_MUST_BE_OUTSIDE_STUDY_ROOT")
        started, cpu_started = time.perf_counter(), time.process_time()
        if args.command == "repack":
            manifest = verify_extracted(root)
            require(manifest["zip_policy"]["python"] == sys.version.split()[0]
                    and manifest["zip_policy"]["zlib_runtime"] == zlib.ZLIB_RUNTIME_VERSION,
                    "EXACT_REPACK_REQUIRES_RECORDED_PYTHON_AND_ZLIB")
            payload = {row["path"]: contained(root, row["path"]) for row in manifest["included_files"]}
            result = emit_build(root, delivery, manifest["archive_root"], manifest, payload)
        else:
            manifest, payload, snapshots = make_plan(root, args.prefix)
            if args.command == "plan":
                report_path = (args.report or delivery / (args.prefix + ".preflight.json")).resolve()
                require(not report_path.is_relative_to(root), "PREFLIGHT_REPORT_MUST_BE_OUTSIDE_STUDY")
                report = {"schema": "agi-alpha-companion-preflight/v1", "archive_created": False,
                    "final_build_reenumerates_and_rechecks": True, "source_tree_sha256": manifest["source_tree_sha256"],
                    "manifest": manifest, "resources": {"elapsed_seconds": time.perf_counter() - started, "cpu_seconds": time.process_time() - cpu_started}}
                save_new(report_path, json_bytes(report))
                result = {"archive_created": False, "report": str(report_path), "inventory": manifest["inventory"],
                    "production_decision_packet_zips": len(manifest["preservation"]["production_decision_packet_zips"]),
                    "complete_market_history_retained": True, "resources": report["resources"]}
            else:
                result = emit_build(root, delivery, args.prefix, manifest, payload, snapshots)
        print(json.dumps(result, indent=2))
        return
    if args.command == "verify-archive":
        require(args.archive is not None, "--archive REQUIRED")
        manifest = verify_archive(args.archive.resolve())
        print(json.dumps({"verified": True, "payload_files": len(manifest["included_files"]), "archive_sha256": file_digest(args.archive)}))
        return
    if args.command == "extract":
        require(args.archive is not None and args.destination is not None, "--archive AND --destination REQUIRED")
        manifest = verify_archive(args.archive.resolve())
        destination = args.destination.resolve()
        require(not destination.exists(), "FRESH_EXTRACTION_DESTINATION_REQUIRED")
        destination.mkdir(parents=True)
        prefix = manifest["archive_root"]
        with zipfile.ZipFile(args.archive) as archive:
            for info in archive.infolist():
                safe_relative(info.filename.rstrip("/"))
                target = contained(destination, info.filename.rstrip("/"))
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as handle:
                        handle.write(archive.read(info))
                    target.chmod((info.external_attr >> 16) & 0o777)
        verify_extracted(destination / prefix)
        print(json.dumps({"extracted_and_verified": True, "root": str(destination / prefix), "symlinks": "inert records only"}))
        return
    manifest = verify_extracted(root)
    restored = []
    if args.command == "restore-wheels":
        for row in manifest["omissions"]:
            if row["recovery"]["kind"] != "byte_copy":
                continue
            source = contained(root, row["canonical_recovery_path"])
            target = contained(root, row["path"])
            require(file_digest(source) == row["sha256"], "CANONICAL_WHEEL_CHANGED")
            if target.exists():
                require(not target.is_symlink() and file_digest(target) == row["sha256"], "PRESERVE_DIFFERENT_EXISTING_WHEEL")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            require(file_digest(target) == row["sha256"], "RESTORED_WHEEL_IDENTITY")
            restored.append(row["path"])
    elif args.command == "restore-links":
        for row in manifest["symbolic_links"]:
            canonical = row["canonical_recovery_path"]
            require(canonical is not None and row["canonical_target_sha256"] is not None, "NO_VERIFIED_INTERNAL_LINK_RECOVERY")
            source = contained(root, canonical)
            target = root.joinpath(*safe_relative(row["path"]).parts)
            require(not target.exists() and not target.is_symlink(), "PRESERVE_EXISTING_LINK_PATH")
            require(file_digest(source) == row["canonical_target_sha256"], "LINK_RECOVERY_TARGET_CHANGED")
            target.parent.mkdir(parents=True, exist_ok=True)
            relative_target = os.path.relpath(source, target.parent)
            os.symlink(relative_target, target)
            restored.append({"path": row["path"], "safe_relative_target": relative_target,
                "original_target_record_preserved": row["archive_record"], "raw_original_target_record_changed": False,
                "restored_target_is_explicitly_rebased": True})
    print(json.dumps({"verified": True, "payload_files": len(manifest["included_files"]), "restored": restored,
        "omissions_documented": len(manifest["omissions"]), "original_link_records": len(manifest["symbolic_links"])}, indent=2))


if __name__ == "__main__":
    main()
