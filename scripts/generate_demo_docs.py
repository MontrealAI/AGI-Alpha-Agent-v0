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
        if m:
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
    if readme_lines and readme_lines[0].startswith("#"):
        readme_lines = readme_lines[1:]

    cleaned: list[str] = []
    skip_section = False
    for line in readme_lines:
        stripped = line.strip()
        if skip_section:
            if stripped.startswith("#") or stripped.startswith("---") or not stripped:
                skip_section = False
            continue
        if "DISCLAIMER_SNIPPET.md" in stripped:
            continue
        if "README.md" in stripped:
            continue
        if "plugins/" in stripped or "scripts/README.md" in stripped or "tests/README.md" in stripped:
            continue
        if ".env.sample" in stripped:
            continue
        if "CONCEPTUAL_FRAMEWORK.md" in stripped:
            continue
        if "adk_bridge.py" in stripped:
            continue
        if "(#" in stripped:
            continue
        if (
            "conceptual research prototype" in stripped
            or "financial advice" in stripped
            or "research and educational purposes" in stripped
            or "trading decisions" in stripped
            or "no liability" in stripped
        ):
            continue
        if stripped.lower().startswith("##") and "disclaimer" in stripped.lower():
            skip_section = True
            continue
        cleaned.append(line)

    readme_text = "\n".join(cleaned).lstrip("\n")

    # Fix relative links that break once the README is moved under docs/demos.
    github_base = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/"
    readme_text = re.sub(r"\(\.\./\.\./\.\./docs/([^)]+)\)", r"(../\1)", readme_text)
    readme_text = re.sub(r"\(\.\./\.\./\.\./\.\./docs/([^)]+)\)", r"(../\1)", readme_text)
    readme_text = re.sub(r"\(\.\./\.\./docs/([^)]+)\)", r"(../\1)", readme_text)
    readme_text = re.sub(
        r"\((?:\.\./)+AGENTS.md([#^)]+)?\)", lambda m: f"({github_base}AGENTS.md{m.group(1) or ''})", readme_text
    )
    readme_text = re.sub(
        r"\((?:\.\./)+alpha_factory_v1/([^)]+)\)",
        lambda m: f"({github_base}alpha_factory_v1/{m.group(1)})",
        readme_text,
    )

    def _rewrite(match: re.Match[str]) -> str:
        url, anchor = match.group(1), match.group(2) or ""
        if url.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)
        target = (demo / url).resolve()
        try:
            rel = target.relative_to(REPO_ROOT)
        except ValueError:
            return match.group(0)

        if target.is_dir():
            index_html = REPO_ROOT / "docs" / target.name / "index.html"
            if index_html.exists():
                return f"(../{target.name}/index.html{anchor})"
        return f"({github_base}{rel.as_posix()}{anchor})"

    readme_text = re.sub(r"\((?!https?://|mailto:|#)([^)#]+)(#[^)]+)?\)", _rewrite, readme_text)

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
