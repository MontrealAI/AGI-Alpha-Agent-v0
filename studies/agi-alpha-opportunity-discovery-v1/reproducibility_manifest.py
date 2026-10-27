# SPDX-License-Identifier: Apache-2.0
"""Record or verify exact study, source-paper and inherited integration bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STUDY = Path(__file__).resolve().parent
REPOSITORY = STUDY.parents[1]
SCOPES = [
    "studies/agi-alpha-opportunity-discovery-v1",
    "studies/agi-alpha-capability-opportunity-v1",
    "docs/Transformational_Intelligence.tex",
    "docs/Invent_the_Economy.tex",
    "docs/Autonomous_Enterprises_SUCCESSOR_Omega.tex",
    "AGENTS.md",
]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".blg", ".xdv"}


def row(path: Path, root: Path) -> dict[str, Any]:
    """Record one regular file relative to the package's repository-shaped root."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Manifest inputs must be ordinary files: " + str(path))
    content = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def create(root: Path, out: Path) -> dict[str, Any]:
    """Create a final byte manifest after all deliverables have been written."""
    if out.exists():
        raise FileExistsError("Use a new manifest path to preserve earlier packaging receipts")
    files = []
    for scope in SCOPES:
        path = root / scope
        if not path.exists():
            raise FileNotFoundError("Required packaging scope missing: " + scope)
        candidates = path.rglob("*") if path.is_dir() else [path]
        for candidate in candidates:
            if (
                candidate.is_dir()
                or candidate.resolve() == out.resolve()
                or set(candidate.parts) & EXCLUDED_PARTS
                or candidate.suffix in EXCLUDED_SUFFIXES
            ):
                continue
            files.append(row(candidate, root))
    manifest = {
        "schema": "opportunity-discovery-reproducibility-manifest/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repository_shape_required": True,
        "source_parent": "231834269599d85e49cfe1ca9917a1a874522d44",
        "runtime_parent": "80b345828f34fd8a6e592977dd17ef37141305f4",
        "scopes": SCOPES,
        "excluded": {"directory_names": sorted(EXCLUDED_PARTS), "suffixes": sorted(EXCLUDED_SUFFIXES), "self": True},
        "files": sorted(files, key=lambda item: item["path"]),
        "claim": "Byte integrity only; not scientific validity, full repository qualification, legal clearance or publication.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as output:
        output.write(json.dumps(manifest, indent=2) + "\n")
    return {
        "files": len(files),
        "bytes": sum(item["bytes"] for item in files),
        "manifest_sha256": row(out, out.parent)["sha256"],
    }


def verify(root: Path, manifest_path: Path) -> dict[str, Any]:
    """Verify every listed byte sequence without treating unlisted files as qualified."""
    manifest = json.loads(manifest_path.read_text())
    failures = []
    for expected in manifest["files"]:
        path = root / expected["path"]
        if not path.resolve().is_relative_to(root.resolve()):
            failures.append({"path": expected["path"], "reason": "outside-root"})
            continue
        try:
            actual = row(path, root)
            if actual != expected:
                failures.append({"path": expected["path"], "reason": "bytes-changed"})
        except (OSError, ValueError) as exc:
            failures.append({"path": expected["path"], "reason": str(exc)})
    return {
        "listed_files": len(manifest["files"]),
        "passed": not failures,
        "failures": failures,
        "unlisted_files": "Not covered by this manifest; additions do not inherit qualification",
    }


def main() -> None:
    """Create or verify a package manifest using explicit local paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["create", "verify"])
    parser.add_argument("--root", type=Path, default=REPOSITORY)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = create(args.root, args.manifest) if args.action == "create" else verify(args.root, args.manifest)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get("passed", True) else 1)


if __name__ == "__main__":
    main()
