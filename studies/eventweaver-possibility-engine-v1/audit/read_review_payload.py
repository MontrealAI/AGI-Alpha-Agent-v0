#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Emit one bounded local public-review payload to the orchestration runtime.

Call from functions.exec and parse the result there; do not print base64 into chat.
This helper reads one explicit regular file and performs no upload.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=524_286)
    parser.add_argument("--encoding", choices=["base64", "utf-8"], default="base64")
    args = parser.parse_args()
    if args.path.is_symlink() or not args.path.is_file():
        raise ValueError("Payload must be a regular file")
    if args.offset < 0 or not 1 <= args.limit <= 524_286:
        raise ValueError("Invalid offset or unverified local read size")
    with args.path.open("rb") as stream:
        stream.seek(args.offset)
        data = stream.read(args.limit)
    content = base64.b64encode(data).decode("ascii") if args.encoding == "base64" else data.decode("utf-8")
    result = {"path": str(args.path), "offset": args.offset, "bytes": len(data),
              "file_bytes": args.path.stat().st_size, "encoding": args.encoding,
              "sha256": hashlib.sha256(data).hexdigest(),
              "git_blob_sha1": hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest(),
              "content": content}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
