#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Update the Insight demo HTML with the correct bundle SRI."""
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
    r"(?P=quote)[^>]*>\s*</script>",
    re.IGNORECASE | re.DOTALL,
)


def compute_sri(path: Path) -> str:
    """Return a sha384 SRI string for the given file."""
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def build_script_tag(src: str, integrity: str) -> str:
    """Build the canonical script tag for the Insight bundle."""
    return (
        f'<script type="module" src="{src}" integrity="{integrity}" '
        'crossorigin="anonymous"></script>'
    )


def ensure_script_tag(html: str, integrity: str) -> str:
    """Ensure the Insight bundle script tag exists with the correct SRI."""
    match = SCRIPT_TAG_PATTERN.search(html)
    if match:
        src = match.group("src")
        updated = build_script_tag(src, integrity)
        return SCRIPT_TAG_PATTERN.sub(updated, html, count=1)

    insertion = build_script_tag("insight.bundle.js", integrity)
    if "</head>" in html:
        return html.replace("</head>", f"{insertion}\n</head>")
    if "</body>" in html:
        return html.replace("</body>", f"{insertion}\n</body>")
    return f"{html}\n{insertion}\n"


def main(directory: Path) -> int:
    bundle = directory / "insight.bundle.js"
    index_html = directory / "index.html"
    if not bundle.is_file():
        print(f"{bundle}: bundle missing", file=sys.stderr)
        return 1
    if not index_html.is_file():
        print(f"{index_html}: index.html missing", file=sys.stderr)
        return 1

    integrity = compute_sri(bundle)
    html = index_html.read_text(encoding="utf-8")
    updated = ensure_script_tag(html, integrity)
    if updated != html:
        index_html.write_text(updated, encoding="utf-8")
        print(f"{index_html}: updated bundle SRI")
    else:
        print(f"{index_html}: bundle SRI already up to date")
    return 0


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
