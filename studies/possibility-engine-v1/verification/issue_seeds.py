# SPDX-License-Identifier: Apache-2.0
"""Issue confirmation randomness only after checking an immutable source manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import secrets
from pathlib import Path
from typing import Any


def verify_freeze(path: Path) -> dict[str, Any]:
    """Check every frozen byte identity relative to the study root."""
    data = json.loads(path.read_text())
    if data.get("status") != "frozen" or not isinstance(data.get("files"), dict) or not data["files"]:
        raise ValueError("Expected a frozen manifest with a nonempty file/hash mapping")
    root = path.parent.resolve()
    for relative, expected in data["files"].items():
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("Frozen file escapes the study root")
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Frozen source changed: {relative}")
    return data


def main() -> None:
    """Write a new seed document without allowing replacement or silent reseeding."""
    parser = argparse.ArgumentParser()
    parser.add_argument("freeze", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    freeze = verify_freeze(args.freeze)
    document = {
        "schema": "possibility-engine-confirmation-seeds-v1",
        "issued_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "freeze_sha256": hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        "frozen_file_count": len(freeze["files"]),
        "issuer_role": "same-session independent challenger",
        "technical_seed": secrets.randbits(64),
        "economic_seeds": [secrets.randbits(64) for _ in range(128)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"seed_file": str(args.output), "freeze_sha256": document["freeze_sha256"],
                      "frozen_files_verified": len(freeze["files"]), "economic_seed_count": 128}))


if __name__ == "__main__":
    main()
