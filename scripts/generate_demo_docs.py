#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate documentation pages for each demo in docs/demos.

This utility scans the ``alpha_factory_v1/demos`` directory for subpackages
containing ``README.md`` files and creates matching Markdown pages under
``docs/demos``. Each generated page embeds the project disclaimer,
links back to the original README and optionally displays a preview
image found under ``docs/<demo>/assets/preview.*``.

Run this script whenever a new demo is added or READMEs change so the
GitHub Pages gallery stays up to date.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMOS_DIR = REPO_ROOT / "alpha_factory_v1" / "demos"
DOCS_DIR = REPO_ROOT / "docs" / "demos"
DEFAULT_PREVIEW = "../alpha_agi_insight_v1/favicon.svg"
DISCLAIMER_LINK = "[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)"

TITLE_RE = re.compile(r"^#(?!#)\s*(.+)")


def extract_title(readme: Path) -> str:
    """Return a reasonable title for the given README."""
    lines = readme.read_text(encoding="utf-8").splitlines()
    # Search the first 50 lines for a level-one heading
    for line in lines[:50]:
        m = TITLE_RE.match(line.strip())
        if m and "DISCLAIMER_SNIPPET.md" not in m.group(1):
            return m.group(1).strip()
    # Fallback to folder name if no heading found early in the file
    return readme.parent.name.replace("_", " ").title()


def build_page(demo: Path) -> str:
    """Return Markdown text for the given demo subdirectory."""
    title = extract_title(demo / "README.md")
    assets_dir = REPO_ROOT / "docs" / demo.name / "assets"
    preview = None
    if assets_dir.is_dir():
        for ext in ("gif", "png", "jpg", "jpeg", "svg"):
            candidate = assets_dir / f"preview.{ext}"
            if candidate.exists():
                preview = f"../{demo.name}/assets/{candidate.name}"
                break
    if not preview:
        preview = DEFAULT_PREVIEW

    launch_link = None
    demo_index = REPO_ROOT / "docs" / demo.name / "index.html"
    if demo_index.is_file():
        launch_link = f"[Launch Demo](../{demo.name}/index.html){{.md-button}}"

    readme_path = demo / "README.md"
    readme_lines = readme_path.read_text(encoding="utf-8").splitlines()
    explicit_anchors = set(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', "\n".join(readme_lines)))
    if readme_lines and readme_lines[0].startswith("#"):
        readme_lines = readme_lines[1:]

    # Preserve commands, diagrams and prose. Rewrite Markdown link destinations
    # only, outside code fences; parentheses in Python and shell are not links.
    github_base = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/"
    cleaned: list[str] = []
    fence: str | None = None
    removed_title = False
    for line in readme_lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = None if fence == marker else marker if fence is None else fence
            cleaned.append(line)
            continue
        if fence is not None:
            cleaned.append(line)
            continue
        if "DISCLAIMER_SNIPPET.md" in stripped:
            continue
        if not removed_title and TITLE_RE.match(stripped):
            removed_title = True
            continue

        def rewrite(match: re.Match[str]) -> str:
            url = match.group(2)
            if url.startswith("#"):
                if url[1:] in explicit_anchors:
                    return match.group(0)
                anchor = unicodedata.normalize("NFKD", url[1:]).encode("ascii", "ignore").decode().lower()
                anchor = re.sub(r"[^\w\s-]", "", anchor)
                anchor = re.sub(r"[-\s]+", "-", anchor).strip("-")
                return match.group(1) + "#" + anchor + ")"
            if url.startswith(("https://", "http://", "mailto:", "data:")):
                return match.group(0)
            path, sep, anchor = url.partition("#")
            target = (demo / path).resolve()
            try:
                rel = target.relative_to(REPO_ROOT)
            except ValueError:
                return match.group(0)
            return match.group(1) + github_base + rel.as_posix() + (sep + anchor if sep else "") + ")"

        cleaned.append(re.sub(r"(\]\()([^\s)]+)\)", rewrite, line))
    readme_text = "\n".join(cleaned).lstrip("\n")

    content = [
        DISCLAIMER_LINK,
        "",
        f"# {title}",
        "",
        f"![preview]({preview}){{.demo-preview}}",
    ]
    if launch_link:
        content.extend(["", launch_link, ""])
    content.extend(
        [
            readme_text,
            "",
            f"[View README on GitHub]({github_base}alpha_factory_v1/demos/{demo.name}/README.md)",
            "",
        ]
    )

    return "\n".join(content)


def generate_docs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for entry in sorted(DEMOS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("__", ".")):
            continue
        readme = entry / "README.md"
        if not readme.is_file():
            continue
        page_content = build_page(entry)
        output = DOCS_DIR / f"{entry.name}.md"
        output.write_text(page_content, encoding="utf-8")
        print(f"Generated {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    generate_docs()
