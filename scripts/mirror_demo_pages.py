#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Copy demo pages into the alpha_factory_v1/demos/ mirror."""
from __future__ import annotations

import shutil
from pathlib import Path
import os
import re

REPLACEMENTS = {
    "../assets/": "../../../assets/",
    "../README/": "../../README/",
    "../gallery.html": "../../index.html",
    "../DISCLAIMER_SNIPPET/": "../../../DISCLAIMER_SNIPPET/",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
SUBDIR_ROOT = DOCS_DIR / "alpha_factory_v1" / "demos"

EXCLUDE = {
    "stylesheets",
    "assets",
    "utils",
    "alpha_factory_v1",
    "DISCLAIMER_SNIPPET",
    "demos",
}


def fix_paths(target: Path) -> None:
    """Adjust relative links in the mirrored demo."""
    index = target / "index.html"
    if index.exists():
        data = index.read_text()
        for old, new in REPLACEMENTS.items():
            data = data.replace(old, new)
        index.write_text(data)

    script = target / "script.js"
    if script.exists():
        txt = script.read_text()
        txt = txt.replace("../assets/", "../../../assets/")
        script.write_text(txt)

    snippet = DOCS_DIR / "DISCLAIMER_SNIPPET.md"
    for md in target.rglob("*.md"):
        txt = md.read_text()
        rel = os.path.relpath(snippet, md.parent)
        txt = re.sub(r"\((?:\./|\.\./)+DISCLAIMER_SNIPPET\.md\)", f"({rel})", txt)
        md.write_text(txt)


def main() -> None:
    SUBDIR_ROOT.mkdir(parents=True, exist_ok=True)
    for entry in DOCS_DIR.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name in EXCLUDE:
            continue
        if not (entry / "index.html").is_file():
            continue
        target = SUBDIR_ROOT / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(entry, target)
        fix_paths(target)
    print("Mirrored demos to", SUBDIR_ROOT.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
