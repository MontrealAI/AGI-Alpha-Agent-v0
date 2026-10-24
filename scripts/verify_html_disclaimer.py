#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Fail if docs index pages omit the disclaimer snippet."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

SNIPPET = "docs/DISCLAIMER_SNIPPET.md"


def has_disclaimer(text: str, page: Path, docs_dir: Path) -> bool:
    """Accept the documented marker or an actual link to the same local notice."""
    if SNIPPET in text:
        return True

    class NoticeLinks(HTMLParser):
        found = False

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag != "a":
                return
            for name, value in attrs:
                if name != "href" or value is None:
                    continue
                link = urlsplit(value)
                if not link.scheme and not link.netloc and link.path:
                    target = (page.parent / link.path).resolve()
                    if target == (docs_dir / "DISCLAIMER_SNIPPET.md").resolve():
                        self.found = True

    links = NoticeLinks()
    links.feed(text)
    return links.found


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    docs_dir = repo_root / "docs"
    missing: list[Path] = []

    for html in sorted(docs_dir.rglob("index.html")):
        if html.parent.name == "DISCLAIMER_SNIPPET":
            continue
        text = html.read_text(encoding="utf-8", errors="ignore")
        if not has_disclaimer(text, html, docs_dir):
            missing.append(html.relative_to(repo_root))

    if missing:
        print("Missing HTML disclaimer link:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
