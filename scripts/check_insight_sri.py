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

    html_files = sorted(p for p in path.rglob("*.html") if p.is_file())
    if not html_files:
        print(f"{path}: no HTML files found to verify", file=sys.stderr)
        return 1

    expected = _hash(bundle)
    found_script = False
    errors = 0
    for html in html_files:
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

    if not found_script:
        scanned = ", ".join(str(p.relative_to(path)) for p in html_files)
        print(
            f"{path}: script tag for insight.bundle.js missing in [{scanned}]",
            file=sys.stderr,
        )
        return 1
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
