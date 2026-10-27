#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Copy demo pages into the alpha_factory_v1/demos/ mirror."""
from __future__ import annotations

import shutil
import hashlib
import json
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
    # A portable source-bound document has one canonical route; rewriting its
    # embedded executable/data strings would invalidate its CSP and identities.
    "transformational-intelligence",
    "try",
    "flywheel",
    "stylesheets",
    "assets",
    "utils",
    "alpha_factory_v1",
    "DISCLAIMER_SNIPPET",
    "demos",
}


def fix_paths(target: Path) -> None:
    """Resolve shared resources from each copied file, including nested JS/CSS."""
    source = DOCS_DIR / target.name
    for copied in target.rglob("*"):
        if not copied.is_file() or copied.suffix not in {".html", ".js", ".css", ".md"}:
            continue
        original = source / copied.relative_to(target)
        text = copied.read_text(encoding="utf-8")

        def rewrite(match: re.Match[str]) -> str:
            quote, url = match.group(1), match.group(2)
            path, sep, fragment = url.partition("#")
            resolved = (original.parent / path).resolve()
            if resolved.is_relative_to(source.resolve()):
                return match.group(0)
            if not resolved.is_relative_to(DOCS_DIR.resolve()):
                return match.group(0)
            rel = Path(os.path.relpath(resolved, copied.parent)).as_posix()
            if not rel.startswith("."):
                rel = "./" + rel
            return quote + rel + (sep + fragment if sep else "") + quote

        text = re.sub(r"([\"'])(\.\.?/[^\"'\s]+)\1", rewrite, text)
        snippet = DOCS_DIR / "DISCLAIMER_SNIPPET.md"
        if copied.suffix == ".md":
            rel = os.path.relpath(snippet, copied.parent)
            text = re.sub(r"\((?:\./|\.\./)+DISCLAIMER_SNIPPET\.md\)", f"({rel})", text)
        copied.write_text(text, encoding="utf-8")
    # A mirrored flagship has rewritten links and therefore different document bytes.
    # Keep the implementation pins intact and bind the mirror's actual generated page.
    for manifest_path in target.rglob("sources.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        page_path = manifest_path.with_name("index.html")
        if manifest.get("schema") == "successor-alpha-source/v1" and page_path.is_file():
            manifest["pageSha256"] = hashlib.sha256(page_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        # This original mirror is a distinct Plotly/tree presentation, not a duplicate.
        if name == "alpha_agi_insight_v1" and (target / "index.html").is_file():
            continue
        shutil.copytree(entry, target, dirs_exist_ok=True)
        fix_paths(target)
    print("Mirrored demos to", SUBDIR_ROOT.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
