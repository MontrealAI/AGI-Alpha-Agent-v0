# SPDX-License-Identifier: Apache-2.0
"""Restore exact executed numerical source into a new isolated directory."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        raise ValueError("Use a new destination; restoration never overwrites an existing directory")
    proof = json.loads((STUDY / "evidence/source_formatting_equivalence.json").read_text())
    shutil.copytree(STUDY / "study/technical", destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for row in proof["records"]:
        relative = Path(row["path_at_execution"]).relative_to("study/technical")
        if ".." in relative.parts:
            raise ValueError("Invalid source path")
        raw = gzip.decompress((STUDY / row["executed_source_gzip"]).read_bytes())
        if hashlib.sha256(raw).hexdigest() != row["executed_sha256"]:
            raise ValueError(f"Executed source digest mismatch: {relative}")
        (destination / relative).write_bytes(raw)
    print(
        json.dumps(
            {
                "destination": str(destination),
                "restored_exact_sources": len(proof["records"]),
                "original_observations_preserved": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
