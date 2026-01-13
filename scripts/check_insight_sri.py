#!/usr/bin/env python3
"""Verify SRI hash for ``insight.bundle.js``.

The script checks that the ``integrity`` attribute in ``index.html`` matches the
SHA-384 digest of ``insight.bundle.js``. It tolerates query strings and
case-only differences in the script tag. Pass the directory containing the
files as an optional argument. By default it verifies
``docs/alpha_agi_insight_v1``.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
from pathlib import Path

DEFAULT_DIR = Path("docs/alpha_agi_insight_v1")

SCRIPT_TAG_PATTERN = re.compile(
    r"<script[^>]*src=(?P<quote>['\"]?)(?P<src>[^'\" >]*insight\.bundle\.js(?:[?#][^'\" >]+)?)"
    r"(?P=quote)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
INTEGRITY_PATTERN = re.compile(r"integrity=['\"]([^'\"]+)['\"]", re.IGNORECASE)


def _hash(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def check_directory(path: Path) -> int:
    bundle = path / "insight.bundle.js"
    if not bundle.is_file():
        print(f"{path}: insight bundle missing", file=sys.stderr)
        return 1

    index_html = path / "index.html"
    if not index_html.is_file():
        print(f"{path}: index.html missing", file=sys.stderr)
        return 1

    html_files = sorted(p for p in path.rglob("*.html") if p.is_file())
    if not html_files:
        print(f"{path}: no HTML files found to verify", file=sys.stderr)
        return 1

    expected = _hash(bundle)
    found_script = False
    errors = 0
    index_text = index_html.read_text(encoding="utf-8")
    index_matches = list(SCRIPT_TAG_PATTERN.finditer(index_text))
    if not index_matches:
        print(f"{index_html}: script tag for insight.bundle.js missing", file=sys.stderr)
        return 1
    found_script = True
    for match in index_matches:
        sri = INTEGRITY_PATTERN.search(match.group(0))
        if not sri:
            print(f"{index_html}: integrity attribute missing", file=sys.stderr)
            errors += 1
            continue
        if sri.group(1) != expected:
            print(
                f"{index_html}: SRI mismatch: {sri.group(1)} != {expected}",
                file=sys.stderr,
            )
            errors += 1

    for html in html_files:
        if html == index_html:
            continue
        text = html.read_text(encoding="utf-8")
        matches = list(SCRIPT_TAG_PATTERN.finditer(text))
        if not matches:
            continue
        found_script = True
        for match in matches:
            sri = INTEGRITY_PATTERN.search(match.group(0))
            if not sri:
                print(f"{html}: integrity attribute missing", file=sys.stderr)
                errors += 1
                continue
            if sri.group(1) != expected:
                print(
                    f"{html}: SRI mismatch: {sri.group(1)} != {expected}",
                    file=sys.stderr,
                )
                errors += 1

    if errors:
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
