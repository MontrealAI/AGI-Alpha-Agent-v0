#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Ensure the Insight demo HTML includes the correct service worker hash."""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
from pathlib import Path

DEFAULT_DIR = Path("docs/alpha_agi_insight_v1")
SW_HASH_RE = re.compile(r"SW_HASH\s*=\s*['\"]sha384-[^'\"]+['\"]")


def _hash(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def ensure_sw_hash(directory: Path) -> bool:
    """Return True if the HTML was updated with the correct service worker hash."""
    index_html = directory / "index.html"
    service_worker = directory / "service-worker.js"
    if not index_html.is_file():
        raise FileNotFoundError("index.html missing")
    if not service_worker.is_file():
        raise FileNotFoundError("service-worker.js missing")

    html = index_html.read_text(encoding="utf-8")
    new_hash = _hash(service_worker)
    if not SW_HASH_RE.search(html):
        raise ValueError("SW_HASH not found in index.html")
    updated = SW_HASH_RE.sub(f"SW_HASH = 'sha384-{new_hash.split('sha384-', 1)[1]}'", html, count=1)
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
        help="Directory containing index.html and service-worker.js",
    )
    args = parser.parse_args()
    changed = ensure_sw_hash(Path(args.path))
    print("Insight SW hash updated" if changed else "Insight SW hash already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
