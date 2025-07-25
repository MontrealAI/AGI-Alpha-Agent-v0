#!/usr/bin/env python3
"""Verify SRI hash for ``insight.bundle.js``.

The script checks that the ``integrity`` attribute in ``index.html`` matches the
SHA-384 digest of ``insight.bundle.js``. Pass the directory containing the files
as an optional argument. By default it verifies ``docs/alpha_agi_insight_v1``.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
from pathlib import Path

DEFAULT_DIR = Path("docs/alpha_agi_insight_v1")


def _hash(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def check_directory(path: Path) -> int:
    bundle = path / "insight.bundle.js"
    html = path / "index.html"
    if not bundle.is_file() or not html.is_file():
        print(f"{path}: insight bundle or index.html missing", file=sys.stderr)
        return 1
    text = html.read_text()
    match = re.search(r"<script[^>]*src=['\"]insight.bundle.js['\"][^>]*>", text)
    if not match:
        print(f"{path}: script tag for insight.bundle.js missing", file=sys.stderr)
        return 1
    sri = re.search(r"integrity=['\"]([^'\"]+)['\"]", match.group(0))
    if not sri:
        print(f"{path}: integrity attribute missing", file=sys.stderr)
        return 1
    expected = _hash(bundle)
    if sri.group(1) != expected:
        print(
            f"{path}: SRI mismatch: {sri.group(1)} != {expected}",
            file=sys.stderr,
        )
        return 1
    print(f"{path}: insight bundle integrity verified")
    return 0


def main(directory: Path) -> int:
    return check_directory(directory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_DIR,
        help="Directory containing insight.bundle.js and index.html",
    )
    args = parser.parse_args()
    raise SystemExit(main(Path(args.path)))
