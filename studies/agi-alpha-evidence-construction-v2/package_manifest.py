# SPDX-License-Identifier: Apache-2.0
"""Write or verify the exact publication file manifest, without changing evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "MANIFEST.json"
EXCLUDED_DIRS = {"__pycache__", ".ruff_cache", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".aux", ".blg", ".out", ".toc", ".xdv", ".fls", ".fdb_latexmk"}


def inventory() -> list[dict]:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path == MANIFEST or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if path.is_symlink():
            raise ValueError("Publication symlink refused: " + str(relative))
        if not path.is_file():
            continue
        data = path.read_bytes()
        rows.append({"path": relative.as_posix(), "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest(),
                     "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
                     "mode": "100644"})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create/update only the publication manifest")
    args = parser.parse_args()
    rows = inventory()
    if args.write:
        record = {
            "schema": "evidence-construction-publication-manifest/v1",
            "edition": "2.0.0",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "research_parent": "9653febcf751b4fc5a47bef1c1c8494d22f3dc75",
            "runtime_parent": "80b345828f34fd8a6e592977dd17ef37141305f4",
            "scope": "Only studies/agi-alpha-evidence-construction-v2; predecessor dependencies have their own exact manifest",
            "excluded": {"directories": sorted(EXCLUDED_DIRS), "suffixes": sorted(EXCLUDED_SUFFIXES), "self": True},
            "files": rows,
            "claim": "Byte identity, not scientific truth, full source qualification or live authority. External commit receipt binds this manifest without circular hashes.",
        }
        MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    else:
        expected = json.loads(MANIFEST.read_text())["files"]
        if rows != expected:
            old = {x["path"]: x for x in expected}
            new = {x["path"]: x for x in rows}
            changed = [key for key in sorted(old.keys() | new.keys()) if old.get(key) != new.get(key)]
            raise ValueError("Publication manifest mismatch: " + ", ".join(changed))
    print(json.dumps({"files": len(rows), "bytes": sum(x["bytes"] for x in rows), "passed": True,
                      "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
