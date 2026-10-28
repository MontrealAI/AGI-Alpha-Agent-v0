# SPDX-License-Identifier: Apache-2.0
"""Restore byte-identical large CSV evidence from the GitHub-friendly gzip copies.

The complete downloadable ZIP already includes the originals. Existing matching
files are verified and left unchanged; a different existing file is never replaced.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    records = json.loads((ROOT / "compressed_artifacts.json").read_text())["files"]
    for record in records:
        target, source = ROOT / record["path"], ROOT / record["gzip_path"]
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError(f"Refusing to overwrite differing evidence: {target}")
            print(f"Verified existing {record['path']}")
            continue
        if hashlib.sha256(source.read_bytes()).hexdigest() != record["gzip_sha256"]:
            raise ValueError(f"Compressed evidence digest mismatch: {source}")
        data = gzip.decompress(source.read_bytes())
        if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(f"Restored evidence differs: {target}")
        with target.open("xb") as handle:
            handle.write(data)
        print(f"Restored {record['path']}")


if __name__ == "__main__":
    main()
