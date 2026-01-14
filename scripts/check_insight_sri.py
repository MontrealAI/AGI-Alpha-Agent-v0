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

SCRIPT_TAG_PATTERN = re.compile(r"<script[^>]*>", re.IGNORECASE | re.DOTALL)
SRC_ATTR_PATTERN = re.compile(
    r"\bsrc\s*=\s*(?P<quote>['\"]?)(?P<src>[^'\" >]+)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
INTEGRITY_PATTERN = re.compile(r"integrity=['\"]([^'\"]+)['\"]", re.IGNORECASE)


def _hash(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def _candidate_bundle_paths(path: Path) -> list[Path]:
    return sorted(path.glob("**/insight.bundle*.js"))


def _extract_script_srcs(html_text: str) -> list[str]:
    sources: list[str] = []
    for script_tag in SCRIPT_TAG_PATTERN.finditer(html_text):
        src_match = SRC_ATTR_PATTERN.search(script_tag.group(0))
        if src_match:
            sources.append(src_match.group("src"))
    return sources


def _clean_src(src: str) -> str:
    return src.split("?", 1)[0].split("#", 1)[0]


def _resolve_bundle(index_html: Path, root: Path, candidates: list[Path]) -> Path | None:
    html_text = index_html.read_text(encoding="utf-8")
    sources = _extract_script_srcs(html_text)
    candidate_names = {candidate.name for candidate in candidates}
    for src in sources:
        clean_src = _clean_src(src)
        if Path(clean_src).name not in candidate_names:
            continue
        src_path = (root / clean_src.lstrip("./")).resolve()
        if src_path.is_file():
            return src_path
        alt_path = root / clean_src.lstrip("./")
        if alt_path.is_file():
            return alt_path
        for candidate in candidates:
            if candidate.name == Path(clean_src).name:
                return candidate
    return None


def _iter_matches(texts: Iterable[tuple[Path, str]]) -> Iterable[tuple[Path, re.Match[str]]]:
    for html_path, html_text in texts:
        for match in SCRIPT_TAG_PATTERN.finditer(html_text):
            src_match = SRC_ATTR_PATTERN.search(match.group(0))
            if src_match:
                yield html_path, match


def check_directory(path: Path) -> int:
    index_html = path / "index.html"
    if not index_html.is_file():
        print(f"{path}: index.html missing", file=sys.stderr)
        return 1

    candidates = _candidate_bundle_paths(path)
    if not candidates:
        print(f"{path}: insight bundle missing", file=sys.stderr)
        return 1
    bundle = _resolve_bundle(index_html, path, candidates)
    if bundle is None:
        print(f"{index_html}: script tag for insight bundle missing", file=sys.stderr)
        return 1

    html_files = sorted(p for p in path.rglob("*.html") if p.is_file())
    if not html_files:
        print(f"{path}: no HTML files found to verify", file=sys.stderr)
        return 1

    expected = _hash(bundle)
    errors = 0
    candidate_names = {candidate.name for candidate in candidates}
    html_texts = [(html, html.read_text(encoding="utf-8")) for html in html_files]
    for html, match in _iter_matches(html_texts):
        src_match = SRC_ATTR_PATTERN.search(match.group(0))
        if not src_match:
            continue
        src = _clean_src(src_match.group("src"))
        if Path(src).name not in candidate_names:
            continue
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
