#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inventory the additive public source selection without network or repository writes.

This is a distribution inventory, not scientific execution, qualification or publication.
The default only records exact current bytes. --stage copies into a new empty directory.
It never edits a frozen file and excludes raw trial bodies and private transport machinery.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "studies/agi-alpha-flywheel-earned-turn-v1"
FREEZE = "0c9c3ad04ab99a992e0746c2416eb657a46ddfae99176e26d7d7245ea0e2280d"
SKIP_PARTS = {"__pycache__", "node_modules", ".venv", ".git", "helpers", "checkpoints", "deliverables"}
SOURCE_SUFFIXES = {".py", ".mjs", ".js", ".html", ".css", ".json", ".md", ".txt", ".log", ".sh", ".sol"}
PRIVATE_PATTERNS = (
    re.compile(rb"https?://(?:www\.)?chatgpt\.com/library\?", re.I),
    re.compile(b"oai-" + b"library://", re.I),
    re.compile(b"library-" + b"file:", re.I),
    re.compile(rb"(?:file-inline-)?libfile_[A-Za-z0-9_-]{8,}", re.I),
    re.compile(rb"https?://[^\s\"<>]+(?:X-Amz-Signature=|[?&]sig=)", re.I),
)
PUBLICATION_FILES = {
    "ADDITIVE_HANDOFF.md", "SOURCE_EVIDENCE_SPLIT.md", "CURRENT_OWNER_SNAPSHOT.json",
    "PUBLICATION_SNAPSHOT_UPDATE.json", "OWNER_COMMENTS.json", "POLICY_SOURCE_VERIFICATION.json",
    "PREFERRED_EDITION02_READBACK.json", "RAW_EVIDENCE_MANIFEST.json", "RAW_ARCHIVE_IDENTITY.json",
    "RAW_ARCHIVE_VERIFICATION.json", "PDF_REBUILD_VERIFICATION.json", "PAPER_ARCHIVE_IDENTITY.json",
    "build_paper_archive.py", "build_companion_archive.py", "EXTRACTOR_VERIFICATION.json",
    "PUBLIC_PROJECTIONS.json",
    "FREEZE_COMMENT.md", "prepare_source_selection.py", "DRAFT_PR_DESCRIPTION.md", "DRAFT_PR_TITLE.txt",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ordinary(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"Non-ordinary source: {path}")
    data = path.read_bytes()
    if len(data) > 8_000_000:
        raise ValueError(f"Source-file ceiling exceeded; use the research companion: {path}")
    return data


def category(relative: Path) -> str | None:
    parts = relative.parts
    if any(part in SKIP_PARTS for part in parts):
        return None
    if str(relative) == "audit/prior-strategy-lab/HISTORICAL_STRATEGY_LAB_AUDIT.md":
        return None  # Original private custody is preserved; distinctly named public projection is included.
    folder, suffix = parts[0], relative.suffix
    if len(parts) == 1 and relative.name in {
        "README.md", "REPRODUCE.md", "DOC_PACKAGE_CONTENTS.md", "requirements.txt", "LICENSE", "NOTICE",
        "unpack_evidence.py",
        "EVIDENCE_DOCKET.json", "EVIDENCE_DOCKET.md", "VERIFICATION.json",
    }:
        return "root-guide-and-final-evidence"
    if folder == "companion" and len(parts) == 2 and suffix == ".py":
        return "companion-source"
    if folder == "runtime":
        if parts[1] == "vendor" and (suffix in SOURCE_SUFFIXES or relative.name in {"LICENSE", "NOTICE"}):
            return "unchanged-upstream-closure"
        if len(parts) == 2 and suffix in SOURCE_SUFFIXES:
            return "runtime-source-and-component-evidence"
    if folder == "browser" and suffix in SOURCE_SUFFIXES:
        return "browser-source-and-textual-evidence"
    if folder == "paper":
        if len(parts) == 2 and suffix in {".tex", ".bib", ".pdf", ".py", ".sh", ".md"}:
            return "paper-source-and-author-pdf"
        if len(parts) == 3 and parts[1] == "figures" and suffix in {".pdf", ".svg"}:
            return "editable-vector-figures"
        if len(parts) == 3 and parts[1] == "data" and suffix == ".json":
            return "exact-figure-input-data"
        if "qa" in parts and suffix in {".json", ".md"}:
            return "textual-pdf-review"
    if folder == "protocol" and len(parts) == 2 and suffix in {".json", ".py", ".md"}:
        return "frozen-protocol-and-interventions"
    if folder == "development" and len(parts) == 2 and suffix in {".json", ".py", ".md"}:
        return "development-source-and-failure-summaries"
    if folder == "results" and len(parts) == 3 and parts[1] == "confirmation-v1" and suffix == ".json":
        return "confirmation-summaries"
    if folder == "review" and suffix in SOURCE_SUFFIXES:
        return "independent-review-and-regressions"
    if folder == "audit" and relative.name != "alpha-tree-observed.json":
        if parts[1] == "foundations":
            return "foundation-identities-and-roles" if suffix in {".json", ".md", ".bib"} else None
        if suffix in SOURCE_SUFFIXES:
            return "source-interface-and-policy-audit"
    if folder == "operations" and len(parts) == 3 and relative.name in {
        "PROCESS_RECOVERY.json", "READ_ONLY_VERIFICATION.json", "process-calls.json", "probe-config.json",
    }:
        return "actual-process-recovery-summary"
    if folder == "publication":
        if len(parts) == 2 and relative.name in PUBLICATION_FILES:
            return "publication-handoff"
        if len(parts) >= 3 and parts[1] == "retrieval" and suffix == ".md":
            return "exact-publication-policy-sources"
        if "pdf-qa" in parts and suffix in {".json", ".md"}:
            return "textual-pdf-review"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, help="Copy only to a nonexistent local destination; no Git action.")
    args = parser.parse_args()
    freeze = json.loads((ROOT / "protocol/FREEZE.json").read_text())
    if freeze["freeze_sha256"] != FREEZE or len(freeze["files"]) != 32:
        raise ValueError("Unexpected scientific freeze")
    for name, expected in freeze["files"].items():
        if digest(ordinary(ROOT / name)) != expected:
            raise ValueError(f"Frozen scientific source changed: {name}")
    rows = []
    omitted = Counter()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        kind = category(rel)
        if kind is None:
            omitted[rel.parts[0]] += 1
            continue
        data = ordinary(path)
        if any(pattern.search(data) for pattern in PRIVATE_PATTERNS):
            raise ValueError(f"Private transport locator in selected bytes; explicit projection required: {rel}")
        rows.append({"path":str(rel), "target":str(Path(NAMESPACE)/rel), "bytes":len(data),
                     "sha256":digest(data), "category":kind})
    selected = {row["path"] for row in rows}
    missing = sorted(set(freeze["files"]) - selected)
    if missing:
        raise ValueError(f"Selection omits frozen files: {missing}")
    vendors = json.loads((ROOT / "runtime/vendor/WORKBENCH_MANIFEST.json").read_text())
    for entry in vendors["files"]:
        rel = "runtime/vendor/" + entry["path"]
        if rel not in selected or digest(ordinary(ROOT / rel)) != entry["sha256"]:
            raise ValueError(f"Missing or changed upstream source: {rel}")
    inventory_digest = digest(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode())
    result = {
        "schema":"earned-turn-public-source-selection/v1", "namespace":NAMESPACE,
        "status":"PREPARED_CURRENT_BYTES_NOT_PUBLICATION_OR_QUALIFICATION",
        "source_freeze":FREEZE, "all_32_frozen_files_present_unchanged":True,
        "upstream_files_verified":len(vendors["files"]), "files":rows, "file_count":len(rows),
        "bytes":sum(row["bytes"] for row in rows), "selection_sha256":inventory_digest,
        "excluded_path_counts_by_top_level":dict(omitted),
        "selection_rules":"Explicit whitelist in prepare_source_selection.py; source-only distribution. Raw records remain indexed separately.",
        "finality":"Regenerate after final PDF, archives and QA; neither current hashes nor --stage creates a PR or a release.",
        "new_public_links":[],
    }
    inventory_path = ROOT / "publication/SOURCE_SELECTION.json"
    inventory_path.write_text(json.dumps(result, indent=2) + "\n")
    if args.stage:
        if args.stage.exists():
            raise ValueError("Staging destination must not already exist")
        args.stage.mkdir(parents=True)
        for row in rows:
            dst = args.stage / row["target"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / row["path"], dst)
            if digest(dst.read_bytes()) != row["sha256"]:
                raise ValueError(f"Staged bytes differ: {row['path']}")
        target_inventory = args.stage / NAMESPACE / "publication/SOURCE_SELECTION.json"
        shutil.copyfile(inventory_path, target_inventory)
    print(json.dumps({k:result[k] for k in ["status","file_count","bytes","selection_sha256",
                                            "all_32_frozen_files_present_unchanged","upstream_files_verified"]}, indent=2))


if __name__ == "__main__":
    main()
