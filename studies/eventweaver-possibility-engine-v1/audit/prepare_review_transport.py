#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Split a completed companion into exact, independently verifiable review parts.

This creates local staging files only. It neither uploads nor publishes anything.
Keep the output directory outside the companion's input set to avoid recursion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def prepare(archive: Path, output: Path, part_bytes: int) -> dict:
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("Archive must be an existing regular file, not a symlink")
    if archive.suffix != ".zip":
        raise ValueError("The companion must be a .zip file")
    if not 1 <= part_bytes < 8_000_000:
        raise ValueError("Part size must be positive and less than 8,000,000 bytes")
    if output.exists():
        raise FileExistsError("Use a new output directory; existing parts are immutable")
    output.mkdir(parents=True)
    (output / "parts").mkdir()
    complete_hash = hashlib.sha256()
    total = 0
    parts = []
    with archive.open("rb") as stream:
        while data := stream.read(part_bytes):
            index = len(parts) + 1
            relative = f"parts/{archive.name}.part{index:04d}"
            (output / relative).write_bytes(data)
            parts.append({"index": index, "path": relative, "bytes": len(data),
                          "sha256": hashlib.sha256(data).hexdigest(),
                          "git_blob_sha1": blob_sha(data)})
            complete_hash.update(data)
            total += len(data)
    if total <= 0:
        raise ValueError("Empty companion is not a valid review package")
    result = {"schema": "possibility-engine.review-transport.v1",
              "archive_name": archive.name, "archive_bytes": total,
              "archive_sha256": complete_hash.hexdigest(),
              "part_bytes": part_bytes, "parts": parts,
              "scope": "Exact transport of a completed research companion; not a software release or Pages deployment.",
              "canonical_publication": "The existing sole publisher must reconstruct these exact bytes and upload the complete ZIP as the canonical research-release asset, then verify the actual download before catalog linkage."}
    (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(Path(__file__).with_name("reconstruct_companion.py"), output / "reconstruct_companion.py")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--part-bytes", type=int, default=524_286,
                        help="Default fits the verified local tool bridge; no remote size limit is inferred")
    args = parser.parse_args()
    result = prepare(args.archive, args.output, args.part_bytes)
    print(json.dumps({"output": str(args.output), "parts": len(result["parts"]),
                      "archive_bytes": result["archive_bytes"],
                      "archive_sha256": result["archive_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
