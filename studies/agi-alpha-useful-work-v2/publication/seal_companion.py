# SPDX-License-Identifier: Apache-2.0
"""Seal exactly a reviewed inventory to a NEW closed, verified companion ZIP.

Linux publisher; no consumer execution. Example (only after inventory approval):
 python publication/seal_companion.py --root . --inventory FINAL/inventory.json \
   --archive /absolute/new/full.zip
For the compact public source/evidence variant add --exclude-wheels and optionally
--exclude-ruff. All omissions are explicit; that variant is NOT_OFFLINE_COMPLETE.
The exact input inventory is embedded verbatim in COMPANION_MANIFEST.json; its
own manifest hash is external in NEW.zip.seal.json. No existing archive/receipt
is overwritten. Temporary artifacts and failure receipts are preserved.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime
import errno
import json
import os
from pathlib import Path
import stat
import sys
import time
import uuid
import zipfile

from verify_companion import (
    MANIFEST_NAME, PREFIX, SCHEMA, CompanionError, absolute_path, identity_at,
    identity_path, inventory_checked, json_bytes, manifest_checked, open_directory,
    read_path, require_identity, select_payload, sha, utc_now, verify_archive,
    write_new_report,
)


def verify_sources(root_fd, rows):
    count, total = 0, 0
    for row in rows:
        actual = identity_at(root_fd, row["path"])
        require_identity(actual, row)
        count += 1
        total += actual["bytes"]
    return {"files_checked": count, "bytes_read": total, "all_inventory_identities_match": True,
            "includes_variant_omissions": True, "no_symlinks_followed": True}


def zip_info(name, size):
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    info.file_size = size
    return info


def no_replace_rename(parent_fd, source, destination):
    """Linux atomic rename with NOREPLACE; never a check-then-overwrite race."""
    if sys.platform != "linux":
        raise CompanionError("ATOMIC_NOREPLACE_RENAME_REQUIRES_LINUX")
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        rename = libc.renameat2
    except AttributeError as exc:
        raise CompanionError("RENAMEAT2_UNAVAILABLE_TEMPORARY_PRESERVED") from exc
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent_fd, os.fsencode(source), parent_fd, os.fsencode(destination), 1) != 0:
        value = ctypes.get_errno()
        if value == errno.EEXIST:
            raise FileExistsError(value, "Destination exists; no archive overwritten", destination)
        raise OSError(value, os.strerror(value), destination)


def seal(args, result):
    root = absolute_path(args.root)
    inventory_path = absolute_path(args.inventory)
    archive_path = absolute_path(args.archive)
    receipt_path = archive_path.with_name(archive_path.name + ".seal.json")
    if archive_path.suffix.lower() != ".zip":
        raise CompanionError("ZIP_DESTINATION_REQUIRED")
    if args.exclude_ruff and not args.exclude_wheels:
        raise CompanionError("EXCLUDE_RUFF_REQUIRES_EXCLUDE_WHEELS")
    parent_fd = open_directory(archive_path.parent)
    root_fd = open_directory(root)
    temporary_name = archive_path.name + ".partial." + uuid.uuid4().hex
    temporary_path = archive_path.parent / temporary_name
    result.update(archive_path=str(archive_path), receipt_path=str(receipt_path),
                  temporary_path=str(temporary_path), archive_committed=False)
    try:
        for name in (archive_path.name, receipt_path.name):
            try:
                os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise FileExistsError("NEW_ARCHIVE_AND_RECEIPT_REQUIRED:" + name)
        inventory_raw = read_path(inventory_path)
        inventory = inventory_checked(inventory_raw)
        files, omissions = select_payload(inventory, args.exclude_wheels, args.exclude_ruff)
        manifest = {
            "schema": SCHEMA, "prefix": PREFIX, "created_at": utc_now(),
            "classification": "NOT_OFFLINE_COMPLETE" if args.exclude_wheels else "OFFLINE_COMPANION_PAYLOAD",
            "variant_exclusions": {"wheels": args.exclude_wheels, "ruff": args.exclude_ruff},
            "files": files, "file_count": len(files), "logical_bytes": sum(x["bytes"] for x in files),
            "omissions": omissions, "source_inventory_sha256": sha(inventory_raw),
            "source_inventory_bytes": len(inventory_raw),
            "source_inventory_json_utf8": inventory_raw.decode("utf-8"),
            "manifest_self_identity": "SHA256 is external in the seal receipt; this manifest does not list itself.",
            "runtime_prerequisites": "Compatible installed Python 3.12/Linux x86_64 and Node are external runtime prerequisites; installed environments are rebuilt from the full companion wheels.",
            "scope": "Exact listed research source/evidence. No consumer execution, new mission, deployment, operator or financial authority is implied.",
        }
        manifest_raw = json_bytes(manifest)
        _, manifest_sha = manifest_checked(manifest_raw)
        result.update(source_inventory_path=str(inventory_path), source_inventory_sha256=sha(inventory_raw),
                      manifest_sha256=manifest_sha, classification=manifest["classification"],
                      payload_files=len(files), payload_bytes=manifest["logical_bytes"],
                      omitted_files=len(omissions), omitted_bytes=sum(x["bytes"] for x in omissions))
        result["source_before"] = verify_sources(root_fd, inventory["files"])
        fd = os.open(temporary_name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent_fd)
        with os.fdopen(fd, "w+b") as stream:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=9, allowZip64=True, strict_timestamps=True) as archive:
                for row in files:
                    info = zip_info(PREFIX + "/" + row["path"], row["bytes"])
                    with archive.open(info, "w", force_zip64=row["bytes"] >= 2**31) as member:
                        actual = identity_at(root_fd, row["path"], sink=member)
                    require_identity(actual, row)
                archive.writestr(zip_info(PREFIX + "/" + MANIFEST_NAME, len(manifest_raw)), manifest_raw)
            stream.flush()
            os.fsync(stream.fileno())
        result["temporary_zip_closed_and_fsynced"] = True
        result["source_after_build"] = verify_sources(root_fd, inventory["files"])
        if read_path(inventory_path) != inventory_raw:
            raise CompanionError("INVENTORY_CHANGED_DURING_SEAL")
        temporary_check = verify_archive(temporary_path, manifest_sha)
        result["closed_temporary_verification"] = temporary_check
        no_replace_rename(parent_fd, temporary_name, archive_path.name)
        os.fsync(parent_fd)
        result["archive_committed"] = True
        result["final_verification"] = verify_archive(archive_path, manifest_sha, temporary_check["archive_sha256"])
        result["source_after_final_verification"] = verify_sources(root_fd, inventory["files"])
        if read_path(inventory_path) != inventory_raw:
            raise CompanionError("INVENTORY_CHANGED_BEFORE_FINAL_RECEIPT")
        result.update(archive_sha256=result["final_verification"]["archive_sha256"],
                      archive_bytes=result["final_verification"]["archive_bytes"],
                      atomic_no_replace_rename=True, valid=True)
        return receipt_path
    finally:
        os.close(root_fd)
        os.close(parent_fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--exclude-wheels", action="store_true")
    parser.add_argument("--exclude-ruff", action="store_true")
    args = parser.parse_args()
    wall, cpu = time.perf_counter(), time.process_time()
    result = {"schema": "closed-companion-seal/v1", "started_at": utc_now(), "valid": False,
              "consumer_execution": False, "new_missions": 0, "money_usd": None,
              "model_tokens": None, "inference_usd": None, "operator_minutes": None,
              "aggregation": "Inclusive seal resources include source checks and both closed-archive verifications. Do not add nested diagnostics again; receipt serialization/fsync follows the measured interval."}
    receipt_path = None
    try:
        result["sealer_identity"] = identity_path(__file__)
        result["verifier_identity"] = identity_path(Path(__file__).with_name("verify_companion.py"))
        receipt_path = seal(args, result)
    except Exception as exc:
        result.update(valid=False, error=f"{type(exc).__name__}:{exc}",
                      preserved_artifacts="Any temporary or committed archive remains; failure does not delete or overwrite it.")
    result.update(ended_at=utc_now(), wall_seconds=time.perf_counter() - wall,
                  process_cpu_seconds=time.process_time() - cpu, child_cpu_seconds=0.0)
    if receipt_path is None:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
        receipt_path = absolute_path(args.archive).with_name(args.archive.name + ".failure." + stamp + "." + uuid.uuid4().hex + ".json")
        result["failure_receipt_path"] = str(receipt_path)
    try:
        write_new_report(receipt_path, result)
    except Exception as exc:
        result.update(valid=False, receipt_write_error=f"{type(exc).__name__}:{exc}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
