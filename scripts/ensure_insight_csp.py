#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Ensure the Insight demo HTML includes a CSP meta tag with inline hashes."""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
from pathlib import Path

DEFAULT_DIR = Path("docs/alpha_agi_insight_v1")

CSP_META_RE = re.compile(r"<meta[^>]*http-equiv=[\"']Content-Security-Policy[\"'][^>]*>", re.IGNORECASE)
INLINE_SCRIPT_RE = re.compile(r"<script(?![^>]*src)[^>]*>([\s\S]*?)</script>", re.IGNORECASE)


def _hash_snippet(snippet: str) -> str:
    digest = hashlib.sha384(snippet.encode()).digest()
    return "'sha384-" + base64.b64encode(digest).decode() + "'"


def _build_base() -> str:
    ipfs_origin = os.environ.get("IPFS_GATEWAY", "")
    otel_origin = os.environ.get("OTEL_ENDPOINT", "")
    base = "default-src 'self'; connect-src 'self' https://api.openai.com"
    if ipfs_origin:
        base += f" {ipfs_origin}"
    if otel_origin:
        base += f" {otel_origin}"
    return base


def _build_csp(html: str) -> str:
    hashes = [_hash_snippet(match) for match in INLINE_SCRIPT_RE.findall(html)]
    return (
        f"{_build_base()}; script-src 'self' 'wasm-unsafe-eval' {' '.join(hashes)}; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    )


def ensure_csp(directory: Path) -> bool:
    """Return True if the HTML was updated with the correct CSP."""
    index_html = directory / "index.html"
    if not index_html.is_file():
        raise FileNotFoundError("index.html missing")

    html = index_html.read_text(encoding="utf-8")
    csp = _build_csp(html)
    meta_tag = f'<meta http-equiv="Content-Security-Policy" content="{csp}" />'

    if CSP_META_RE.search(html):
        updated = CSP_META_RE.sub(meta_tag, html, count=1)
    elif "</head>" in html:
        updated = html.replace("</head>", f"  {meta_tag}\n</head>", 1)
    else:
        updated = meta_tag + "\n" + html

    if updated != html:
        index_html.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_DIR,
        help="Directory containing index.html",
    )
    args = parser.parse_args()
    changed = ensure_csp(Path(args.path))
    print("Insight CSP updated" if changed else "Insight CSP already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
