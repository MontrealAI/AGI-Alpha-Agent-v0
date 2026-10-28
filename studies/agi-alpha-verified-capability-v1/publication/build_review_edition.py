# SPDX-License-Identifier: Apache-2.0
"""Inventory a bounded public review edition; the complete companion retains raw evidence."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "publication/review-edition.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    frozen = {row["path"] for row in json.loads((ROOT / "protocol/market-freeze.json").read_text())["files"]}
    selected = []
    omitted = []
    inode_hash = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path == OUTPUT:
            continue
        relative = path.relative_to(ROOT).as_posix()
        parts = path.relative_to(ROOT).parts
        if path.is_symlink():
            target = os.readlink(path).encode()
            omitted.append({"path": relative, "bytes": len(target),
                            "sha256": hashlib.sha256(target).hexdigest(),
                            "type": "symbolic-link-target-bytes", "target": os.readlink(path),
                            "reason": "Deliberate development negative-control symlink retained with original target metadata in complete companion"})
            continue
        status = path.stat()
        key = (status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns)
        if key not in inode_hash:
            inode_hash[key] = sha(path)
        row = {"path": relative, "bytes": status.st_size, "sha256": inode_hash[key]}
        reason = None
        if "__pycache__" in parts or path.suffix in {".pyc", ".pyo"}:
            reason = "Interpreter cache; regenerated, not a source or research result"
        elif "selected-wheels" in parts:
            reason = "Redundant staged wheel bytes; canonical47wheel inputs retained in complete companion"
        elif path.suffix == ".whl":
            reason = "Large immutable wheel input retained in complete companion and source manifest"
        elif relative.startswith("paper/build/") or relative.startswith("paper/rendered/"):
            reason = "Temporary publication build or visual-QA image; final PDF/source/receipts retained"
        elif relative.startswith("demo/browser-review/") and path.suffix == ".png":
            reason = "Internal browser visual-QA image; exact-source check receipt retained"
        elif relative == "demo/index.html":
            reason = "Exact self-contained HTML distributed publicly in demo/AGI_ALPHA_Verified_Capability_Demo.zip; uncompressed HTML retained in complete companion"
        elif relative == "evidence/market-primary/complete-worlds.jsonl.gz":
            reason = "Complete raw cash/buyer/competitor histories retained in companion; public hashes and independent reconciliation retained"
        elif relative == "evidence/market-primary/representative-histories.json":
            reason = "Duplicated full-history extract retained in companion; compact all-world data and full favorable trace retained publicly"
        elif relative.startswith("evidence/development/"):
            if len(parts) > 3 and path.name not in {"qualification.json", "review-receipt.json"}:
                reason = "Development staging retained in complete companion; frozen admission dossier, development qualifications and failed-review history retained publicly"
        elif relative.startswith("evidence/") and len(parts) > 2 and parts[1] not in {"catalog", "production-primary", "market-primary"}:
            reason = "Earlier development state retained in complete companion; frozen current catalogue and failure/repair history retained publicly"
        elif relative.startswith("evidence/production-primary/"):
            suffixes = ("/selection.json", "/production/measurement.json", "/payload/packet.json")
            if relative != "evidence/production-primary/summary.json" and not relative.endswith(suffixes):
                reason = "Full production packet member retained in complete companion; summary/measurement/selection/packet header and all18C ZIPs in offline demo retained publicly"
        elif relative.startswith("heritage/second-investment-inputs/release-index/"):
            reason = "Archived source acquisition response retained in companion; exact source/index hashes remain available"
        elif relative == "heritage/foundations/repository-tree.json":
            reason = "Large source-discovery inventory retained in companion; audited implementation/source manifest retained publicly"
        if relative in frozen and path.suffix != ".whl":
            reason = None
        if reason:
            omitted.append({**row, "reason": reason})
        else:
            selected.append(row)
    result = {"schema": "agi-alpha-verified-capability-public-review-edition/v1",
              "scope": "Source-only additive research review; complete companion is required for full archived-evidence reconciliation",
              "remote_prefix": "studies/agi-alpha-verified-capability-v1/",
              "complete_companion": "AGI_ALPHA_Verified_Capability_Companion.zip; accompanying immutable archive receipt supplies its exact hash",
              "frozen_source_manifest": "protocol/production-freeze.json",
              "market_source_manifest": "protocol/market-freeze.json",
              "included_files": selected,
              "included_count_excluding_this_manifest": len(selected),
              "included_bytes_excluding_this_manifest": sum(r["bytes"] for r in selected),
              "omitted_files": omitted,
              "omitted_count": len(omitted),
              "note": "This manifest deliberately does not hash itself. Omissions are edition boundaries, never deleted original research. The standalone EN/FR HTML contains actual packet downloads and recorded outcomes; it is not a deployed service."}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"included_files", "omitted_files"}}))


if __name__ == "__main__":
    main()
