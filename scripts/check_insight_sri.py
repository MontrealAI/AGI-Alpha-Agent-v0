#!/usr/bin/env python3
"""Verify SRI hash for insight.bundle.js."""
from __future__ import annotations

import base64
import hashlib
import re
import sys
from pathlib import Path

DOCS_DIR = Path("docs/alpha_agi_insight_v1")
BUNDLE = DOCS_DIR / "insight.bundle.js"
INDEX = DOCS_DIR / "index.html"


def _sha384(path: Path) -> str:
    return base64.b64encode(hashlib.sha384(path.read_bytes()).digest()).decode()


def main() -> int:
    if not BUNDLE.is_file() or not INDEX.is_file():
        print("insight bundle or index.html missing", file=sys.stderr)
        return 1
    html = INDEX.read_text()
    match = re.search(r"integrity=['\"]([^'\"]+)['\"]", html)
    if not match:
        print("integrity attribute missing", file=sys.stderr)
        return 1
    expected = "sha384-" + _sha384(BUNDLE)
    if match.group(1) != expected:
        print(f"SRI mismatch: {match.group(1)} != {expected}", file=sys.stderr)
        return 1
    print("insight bundle integrity verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
