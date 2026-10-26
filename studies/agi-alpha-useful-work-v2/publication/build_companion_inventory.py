# SPDX-License-Identifier: Apache-2.0
"""Inventory public companion inputs and exact wheel notices without execution.

This postfreeze publication helper does not change experimental sources, select
missions, install dependencies, or evaluate consumer behavior. It writes to a
fresh output directory so each inclusion snapshot remains inspectable.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRECTORIES = {
    ".git", ".cache", ".ruff_cache", ".pytest_cache", ".mypy_cache",
    "__pycache__", "venv", "site", "screenshots", "extracted-verification",
    ".local-browsers", "chrome-linux", "chrome-linux64", "chrome-headless-shell-linux64",
}
SKIP_SUFFIXES = {".doc", ".docx", ".pyc", ".pyo", ".zip"}
PRIVATE_RECORD = "discovery/guidance.json"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def private_identifiers():
    """Read only redistribution identifiers; never emit them into an inventory."""
    path = ROOT / PRIVATE_RECORD
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [item["library_file_id"].encode() for item in data.get("source_documents", [])
            if isinstance(item, dict) and isinstance(item.get("library_file_id"), str)]


def scan(out, public_pdfs):
    identifiers = private_identifiers()
    included, excluded, blocked = [], [], []
    for folder, directories, names in os.walk(ROOT):
        directory = Path(folder)
        kept = []
        for name in sorted(directories):
            candidate = directory / name
            relative = candidate.relative_to(ROOT).as_posix()
            if candidate == out or name in SKIP_DIRECTORIES or candidate.is_symlink():
                excluded.append({"path": relative + "/", "reason": "runtime-cache-or-inventory-output"})
            elif relative.startswith("publication/companion-inventory-"):
                excluded.append({"path": relative + "/", "reason": "earlier-inventory-snapshot"})
            elif relative.startswith("publication/tree-batches"):
                excluded.append({"path": relative + "/", "reason": "duplicated-publication-transport"})
            elif relative.startswith(("publication/render", "publication/screenshots")):
                excluded.append({"path": relative + "/", "reason": "presentation-qa-rendering"})
            elif relative.startswith(("support/browser", "support/chromium", "support/playwright")):
                excluded.append({"path": relative + "/", "reason": "external-visual-qa-browser-cache"})
            else:
                kept.append(name)
        directories[:] = kept
        for name in sorted(names):
            path = directory / name
            relative = path.relative_to(ROOT).as_posix()
            reason = None
            if path.is_symlink():
                reason = "symlink-not-portable-payload"
            elif relative == PRIVATE_RECORD:
                reason = "private-guidance-identifiers-not-redistributable"
            elif (relative.startswith("publication/v1-companion-correction/")
                  and name not in {"README-correction.md", "corrected-verification.json", "independent-final-readback.json"}):
                reason = "prior-study-recovery-separate-deliverable"
            elif path.suffix.lower() in SKIP_SUFFIXES and relative != "history/control-tools-before-format.zip":
                reason = "private-document-cache-or-nested-archive"
            elif path.suffix.lower() == ".pdf" and relative not in public_pdfs:
                reason = "pdf-requires-explicit-public-artifact-allowlist"
            elif relative.startswith("publication/") and path.suffix.lower() in {".aux", ".out", ".toc", ".synctex"}:
                reason = "reconstructable-latex-auxiliary"
            if reason:
                excluded.append({"path": relative, "reason": reason})
                continue
            raw = path.read_bytes()
            if any(identifier in raw for identifier in identifiers):
                blocked.append({"path": relative, "reason": "private-source-identifier"})
                continue
            included.append({"path": relative, "bytes": len(raw), "sha256": sha(raw),
                             "category": "exact-wheel" if path.suffix == ".whl" else relative.split("/")[0]})
    return included, excluded, blocked


def wheel_rights(included):
    by_hash = collections.defaultdict(list)
    for row in included:
        by_hash[row["sha256"]].append(row["path"])
    metadata = collections.defaultdict(list)
    for row in included:
        name = row["path"]
        if not name.endswith(".json") or not any(part in name for part in (
                "/metadata/", "release-metadata/", "development-bridge-metadata/", "wheel-metadata/")):
            continue
        data = json.loads((ROOT / name).read_text())
        info = data.get("info", {})
        for item in data.get("urls", []):
            digest = item.get("digests", {}).get("sha256")
            if digest and item.get("filename", "").endswith(".whl"):
                metadata[digest].append({"path": name, "metadata_sha256": row["sha256"],
                                         "project": info.get("name"), "version": info.get("version"),
                                         "filename": item["filename"], "url": item.get("url"),
                                         "license_expression": info.get("license_expression")})
    wheels = {}
    for row in included:
        if not row["path"].endswith(".whl"):
            continue
        if row["sha256"] in wheels:
            wheels[row["sha256"]]["included_copies"].append(row["path"])
            continue
        path = ROOT / row["path"]
        notices = []
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                base = Path(member.filename).name.lower()
                if (member.is_dir() or ".dist-info/" not in member.filename
                        or not base.startswith(("license", "copying", "notice"))):
                    continue
                if member.file_size > 1_000_000:
                    raise ValueError("NOTICE_MEMBER_BOUND: " + path.name)
                raw = archive.read(member)
                digest = sha(raw)
                notices.append({"wheel_member": member.filename, "bytes": len(raw), "sha256": digest,
                                "included_extracted_copies": by_hash.get(digest, []),
                                "also_preserved_inside_exact_wheel": True})
        if not notices:
            raise ValueError("WHEEL_NOTICE_NOT_FOUND: " + path.name)
        sources = [item for item in metadata[row["sha256"]] if item["filename"] == path.name]
        if not sources:
            raise ValueError("OFFICIAL_WHEEL_METADATA_NOT_FOUND: " + path.name)
        wheels[row["sha256"]] = {"filename": path.name, "sha256": row["sha256"],
                                  "bytes": row["bytes"], "included_copies": [row["path"]],
                                  "official_metadata": sources, "notices": notices}
    return sorted(wheels.values(), key=lambda row: row["filename"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--public-pdf", action="append", default=[])
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists():
        raise ValueError("FRESH_STUDY_LOCAL_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    included, excluded, blocked = scan(out, set(args.public_pdf))
    frozen = json.loads((ROOT / "protocol/source-freeze.json").read_text())
    index = {row["path"]: row for row in included}
    freeze_checks = [{"path": row["path"], "included_unchanged": index.get(row["path"]) is not None
                      and index[row["path"]]["sha256"] == row["sha256"]
                      and index[row["path"]]["bytes"] == row["bytes"]} for row in frozen["files"]]
    wheels = wheel_rights(included)
    result = {"schema": "public-companion-inclusion-inventory/v1",
              "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "helper_sha256": sha(Path(__file__).read_bytes()),
              "root": "useful-work-v2", "snapshot_not_sealed_archive": True,
              "files": included, "excluded": excluded, "blocked": blocked,
              "file_count": len(included), "logical_bytes": sum(row["bytes"] for row in included),
              "frozen_source_checks": freeze_checks,
              "all_frozen_sources_included_unchanged": all(row["included_unchanged"] for row in freeze_checks),
              "unique_wheel_count": len(wheels), "exact_wheels_and_notices": wheels,
              "private_identifiers_emitted": False,
              "public_pdf_allowlist": args.public_pdf,
              "consumer_execution": False,
              "notes": ["All exact wheels retain their original license members.",
                        "Extracted notice copies are indexed by byte identity, including duplicate environment copies.",
                        "Virtual environments, installation caches, screenshots and private guidance are omitted.",
                        "The archive builder must verify these hashes again when sealing and include this inventory separately."]}
    write(out / "inventory.json", result)
    if blocked or not result["all_frozen_sources_included_unchanged"]:
        raise ValueError("COMPANION_IDENTITY_OR_PRIVACY_BLOCK")
    print(json.dumps({key: result[key] for key in ("file_count", "logical_bytes", "unique_wheel_count",
                                                  "all_frozen_sources_included_unchanged")}))


if __name__ == "__main__":
    main()
