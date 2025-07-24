#!/usr/bin/env python3
"""Verify that insight.bundle.js matches the integrity attribute in index.html."""
from __future__ import annotations
import argparse
import base64
import hashlib
import re
from pathlib import Path


def compute_hash(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def check_directory(directory: Path) -> int:
    bundle = directory / "insight.bundle.js"
    html = directory / "index.html"
    if not bundle.exists():
        print(f"{directory}: insight.bundle.js missing")
        return 1
    if not html.exists():
        print(f"{directory}: index.html missing")
        return 1
    text = html.read_text()
    match = re.search(r"<script[^>]*src=['\"]insight.bundle.js['\"][^>]*>", text)
    if not match:
        print(f"{directory}: script tag for insight.bundle.js missing")
        return 1
    tag = match.group(0)
    sri = re.search(r"integrity=['\"]([^'\"]+)['\"]", tag)
    if not sri:
        print(f"{directory}: integrity attribute missing")
        return 1
    expected = compute_hash(bundle)
    if sri.group(1) != expected:
        print(f"{directory}: hash mismatch: expected {expected}, found {sri.group(1)}")
        return 1
    return 0


def main(path: Path) -> int:
    return check_directory(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default="docs/alpha_agi_insight_v1",
        help="Directory containing insight.bundle.js and index.html",
    )
    args = parser.parse_args()
    raise SystemExit(main(Path(args.path)))
