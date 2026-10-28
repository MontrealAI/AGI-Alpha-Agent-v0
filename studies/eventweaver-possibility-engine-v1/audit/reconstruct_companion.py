#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify ordered review parts and reconstruct the exact complete companion ZIP.

Default: local parts alongside manifest.json. Optional --base-url downloads public
parts from an exact 40-hex Git commit under the isolated EventWeaver study path.
No credentials, external writes, extraction, or code execution are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath

BASE_URL = re.compile(
    r"https://raw\.githubusercontent\.com/MontrealAI/AGI-Alpha-Agent-v0/"
    r"[0-9a-f]{40}/studies/eventweaver-possibility-engine-v1/review_transport/?"
)


def validate_manifest(manifest: dict) -> None:
    if manifest.get("schema") != "possibility-engine.review-transport.v1":
        raise ValueError("Unsupported transport manifest schema")
    name = manifest.get("archive_name", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.zip", name):
        raise ValueError("Unsafe or invalid archive name")
    parts = manifest.get("parts", [])
    if not parts or len(parts) > 10_000:
        raise ValueError("Invalid part count")
    total = 0
    seen = set()
    for expected_index, part in enumerate(parts, 1):
        path = PurePosixPath(part["path"])
        if part["index"] != expected_index or path.is_absolute() or ".." in path.parts:
            raise ValueError("Parts must be ordered and use safe relative paths")
        if str(path) in seen or not re.fullmatch(r"parts/[A-Za-z0-9_.-]+\.part[0-9]{4,5}", str(path)):
            raise ValueError("Duplicate or invalid part path")
        if not isinstance(part["bytes"], int) or not 1 <= part["bytes"] < 8_000_000:
            raise ValueError("Invalid part size")
        if not re.fullmatch(r"[0-9a-f]{64}", part["sha256"]):
            raise ValueError("Invalid part digest")
        seen.add(str(path))
        total += part["bytes"]
    if total != manifest.get("archive_bytes") or total >= 2 * 1024**3:
        raise ValueError("Invalid total size")
    if not re.fullmatch(r"[0-9a-f]{64}", manifest.get("archive_sha256", "")):
        raise ValueError("Invalid archive digest")


def reconstruct(manifest_path: Path, output: Path | None, base_url: str | None = None) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    if base_url is not None and BASE_URL.fullmatch(base_url) is None:
        raise ValueError("Remote source must be the exact pinned public EventWeaver review path")
    if output is not None and output.exists():
        raise FileExistsError("Output already exists; choose a new path")
    temporary = None
    stream = None
    complete_hash = hashlib.sha256()
    total = 0
    try:
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            stream = tempfile.NamedTemporaryFile(mode="wb", prefix="companion-", suffix=".partial",
                                                  dir=output.parent, delete=False)
            temporary = Path(stream.name)
        for part in manifest["parts"]:
            if base_url is None:
                path = manifest_path.parent / part["path"]
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"Part is not a regular file: {part['path']}")
                data = path.read_bytes()
            else:
                request = urllib.request.Request(base_url.rstrip("/") + "/" + part["path"],
                                                 headers={"User-Agent": "EventWeaver-Review-Reassembly/1"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    data = response.read(part["bytes"] + 1)
            if len(data) != part["bytes"] or hashlib.sha256(data).hexdigest() != part["sha256"]:
                raise ValueError(f"Part byte count or digest mismatch: {part['path']}")
            header = f"blob {len(data)}\0".encode("ascii")
            if hashlib.sha1(header + data).hexdigest() != part["git_blob_sha1"]:
                raise ValueError(f"Part Git blob identity mismatch: {part['path']}")
            complete_hash.update(data)
            total += len(data)
            if stream is not None:
                stream.write(data)
        if total != manifest["archive_bytes"] or complete_hash.hexdigest() != manifest["archive_sha256"]:
            raise ValueError("Complete companion byte count or digest mismatch")
        if stream is not None:
            stream.close()
            stream = None
            # Hard-link creation refuses an existing destination atomically.
            os.link(temporary, output)
        return {"verified": True, "parts": len(manifest["parts"]), "bytes": total,
                "sha256": complete_hash.hexdigest(),
                "output": str(output) if output is not None else None}
    finally:
        if stream is not None:
            stream.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("manifest.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--base-url", help="Exact 40-hex commit raw URL ending in /review_transport")
    args = parser.parse_args()
    output = None if args.verify_only else args.output
    if not args.verify_only and output is None:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate_manifest(manifest)
        output = Path.cwd() / manifest["archive_name"]
    print(json.dumps(reconstruct(args.manifest, output, args.base_url), indent=2))


if __name__ == "__main__":
    main()
