# SPDX-License-Identifier: Apache-2.0
"""Keep repository-only pilot guides reachable from the rendered documentation."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE_GUIDES = {
    "agent/START_HERE.md": "examples/transformational-intelligence/README.md",
    "agent/RELEASE_NOTES_1.36.0.md": "examples/transformational-source-audit/README.md",
}


def source_guide_links(markdown: str, source: str, commit: str) -> str:
    """Relocate only the two site-external links; retain offline source documents."""
    target = SOURCE_GUIDES.get(source)
    if target is None:
        return markdown
    if re.fullmatch(r"[a-f0-9]{40}", commit) is None or not (ROOT / target).is_file():
        raise ValueError("Source guide requires an actual commit and existing file")
    original = "](../../" + target + ")"
    if markdown.count(original) != 1:
        raise ValueError("Source guide link differs from its reviewed documentation route")
    return markdown.replace(original, f"](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/{commit}/{target})")


def on_page_markdown(markdown, page, **kwargs):
    """Use the actual documentation checkout for the public source link."""
    source = page.file.src_uri
    if source not in SOURCE_GUIDES:
        return markdown
    commit = subprocess.check_output(["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, text=True).strip()
    return source_guide_links(markdown, source, commit)
