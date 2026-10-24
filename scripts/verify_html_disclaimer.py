#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Fail if docs index pages omit the disclaimer snippet."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SNIPPET = "docs/DISCLAIMER_SNIPPET.md"
PUBLIC_NOTICES = {
    "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/" + SNIPPET,
    "https://montrealai.github.io/AGI-Alpha-Agent-v0/DISCLAIMER_SNIPPET/",
}


class _Links(HTMLParser):
    """Collect actual anchors, excluding comments and script text."""

    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.targets.extend(value for key, value in attrs if key == "href" and value)


def references_disclaimer(text: str, page: Path, docs_dir: Path) -> bool:
    """Require a link to the source notice or its published documentation page."""
    links = _Links()
    links.feed(text)
    local_notices = {
        (docs_dir / "DISCLAIMER_SNIPPET.md").resolve(),
        (docs_dir / "DISCLAIMER_SNIPPET").resolve(),
        (docs_dir / "DISCLAIMER_SNIPPET/index.html").resolve(),
    }
    for target in links.targets:
        try:
            parsed = urlsplit(target)
        except ValueError:
            continue
        if parsed.scheme or parsed.netloc:
            if parsed._replace(query="", fragment="").geturl() in PUBLIC_NOTICES:
                return True
        elif parsed.path and not parsed.path.startswith("/"):
            if (page.parent / unquote(parsed.path)).resolve() in local_notices:
                return True
    return False


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    docs_dir = repo_root / "docs"
    missing: list[Path] = []

    for html in sorted(docs_dir.rglob("index.html")):
        if html.parent.name == "DISCLAIMER_SNIPPET":
            continue
        text = html.read_text(encoding="utf-8", errors="ignore")
        if not references_disclaimer(text, html, docs_dir):
            missing.append(html.relative_to(repo_root))

    if missing:
        print("Missing HTML disclaimer link:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
