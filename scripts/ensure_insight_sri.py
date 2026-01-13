#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Ensure the Insight demo HTML includes a bundle script tag with valid SRI."""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
from pathlib import Path

DEFAULT_DIR = Path("docs/alpha_agi_insight_v1")

SCRIPT_TAG_PATTERN = re.compile(
    r"<script[^>]*\bsrc=(?P<quote>['\"]?)(?P<src>[^'\" >]*insight(?:[\w.-]+)?\.bundle\.js(?:[?#][^'\" >]+)?)"
    r"(?P=quote)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
INTEGRITY_PATTERN = re.compile(r"\bintegrity=['\"]([^'\"]+)['\"]", re.IGNORECASE)


def _hash(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def _ensure_tag(html: str, sri: str, src: str) -> tuple[str, bool]:
    match = SCRIPT_TAG_PATTERN.search(html)
    if match:
        tag = match.group(0)
        if INTEGRITY_PATTERN.search(tag):
            new_tag = INTEGRITY_PATTERN.sub(f'integrity="{sri}"', tag)
        else:
            insert = f' integrity="{sri}"'
            new_tag = tag.replace(">", f"{insert}>", 1)
        if new_tag == tag:
            return html, False
        return html[:match.start()] + new_tag + html[match.end():], True

    script_tag = f'<script type="module" src="{src}" integrity="{sri}" crossorigin="anonymous"></script>'
    if "</head>" in html:
        return html.replace("</head>", f"{script_tag}\n</head>", 1), True
    if "</body>" in html:
        return html.replace("</body>", f"{script_tag}\n</body>", 1), True
    return html + f"\n{script_tag}\n", True


def _resolve_bundle(directory: Path, html: str) -> Path:
    match = SCRIPT_TAG_PATTERN.search(html)
    if match:
        src = match.group("src").split("?", 1)[0].split("#", 1)[0]
        src_path = (directory / src.lstrip("./")).resolve()
        if src_path.is_file():
            return src_path
        alt_path = directory / src.lstrip("./")
        if alt_path.is_file():
            return alt_path
    bundle = directory / "insight.bundle.js"
    if bundle.is_file():
        return bundle
    candidates = sorted(directory.glob("**/insight*.bundle.js"))
    if candidates:
        return candidates[0]
    raise FileNotFoundError("insight bundle missing")


def ensure_sri(directory: Path) -> bool:
    """Return True if the HTML was updated with the correct SRI."""
    index_html = directory / "index.html"
    if not index_html.is_file():
        raise FileNotFoundError("index.html missing")

    html = index_html.read_text(encoding="utf-8")
    bundle = _resolve_bundle(directory, html)
    sri = _hash(bundle)
    src = bundle.relative_to(directory).as_posix()
    updated, changed = _ensure_tag(html, sri, src)
    if changed:
        index_html.write_text(updated, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_DIR,
        help="Directory containing insight.bundle.js and index.html",
    )
    args = parser.parse_args()
    changed = ensure_sri(Path(args.path))
    print("Insight SRI updated" if changed else "Insight SRI already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
