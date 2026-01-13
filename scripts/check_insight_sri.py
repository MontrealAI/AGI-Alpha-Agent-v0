#!/usr/bin/env python3
"""Verify SRI hash for the Insight browser bundle.

The script checks that the ``integrity`` attribute in ``index.html`` matches the
SHA-384 digest of the Insight browser bundle referenced by the HTML. It
tolerates query strings and case-only differences in the script tag. Pass the
directory containing the files as an optional argument. By default it verifies
``docs/alpha_agi_insight_v1``.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_DIR = Path("docs/alpha_agi_insight_v1")

SCRIPT_TAG_PATTERN = re.compile(
    r"<script[^>]*src=(?P<quote>['\"]?)(?P<src>[^'\" >]*insight(?:[\w.-]+)?\.bundle\.js(?:[?#][^'\" >]+)?)"
    r"(?P=quote)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
INTEGRITY_PATTERN = re.compile(r"integrity=['\"]([^'\"]+)['\"]", re.IGNORECASE)


def _hash(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def _candidate_bundle_paths(path: Path) -> list[Path]:
    return sorted(path.glob("**/insight*.bundle.js"))


def _resolve_bundle(index_html: Path, root: Path) -> Path | None:
    html_text = index_html.read_text(encoding="utf-8")
    matches = list(SCRIPT_TAG_PATTERN.finditer(html_text))
    if not matches:
        return None
    src = matches[0].group("src")
    src = src.split("?", 1)[0].split("#", 1)[0]
    src_path = (root / src.lstrip("./")).resolve()
    if src_path.is_file():
        return src_path
    alt_path = root / src.lstrip("./")
    if alt_path.is_file():
        return alt_path
    for candidate in _candidate_bundle_paths(root):
        if candidate.name == Path(src).name:
            return candidate
    return None


def _iter_matches(texts: Iterable[tuple[Path, str]]) -> Iterable[tuple[Path, re.Match[str]]]:
    for html_path, html_text in texts:
        for match in SCRIPT_TAG_PATTERN.finditer(html_text):
            yield html_path, match


def check_directory(path: Path) -> int:
    index_html = path / "index.html"
    if not index_html.is_file():
        print(f"{path}: index.html missing", file=sys.stderr)
        return 1

    bundle = _resolve_bundle(index_html, path)
    if bundle is None:
        print(f"{index_html}: script tag for insight bundle missing", file=sys.stderr)
        return 1
    if not bundle.is_file():
        print(f"{path}: insight bundle missing", file=sys.stderr)
        return 1

    html_files = sorted(p for p in path.rglob("*.html") if p.is_file())
    if not html_files:
        print(f"{path}: no HTML files found to verify", file=sys.stderr)
        return 1

    expected = _hash(bundle)
    errors = 0
    html_texts = [(html, html.read_text(encoding="utf-8")) for html in html_files]
    for html, match in _iter_matches(html_texts):
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

    print(f"{path}: insight bundle integrity verified ({bundle.name})")
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
