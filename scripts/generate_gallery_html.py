#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# This script is a conceptual research prototype.
"""Generate the visual demo gallery HTML files.

This helper reads the Markdown pages under ``docs/demos`` and extracts each
page's title and preview image. It outputs ``docs/index.html`` and
``docs/demos/index.html`` so the GitHub Pages site always lists every demo in a
simple grid. ``docs/gallery.html`` is written as a simple redirect for backward
compatibility.
"""
from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Iterable

H1_RE = re.compile(r"^#\s+(.*)")
DISCLAIMER_HEADING_RE = re.compile(
    r"^#\s+\[See docs/DISCLAIMER_SNIPPET.md\]",
    re.IGNORECASE,
)
PREVIEW_RE = re.compile(r"!\[preview\]\(([^)]+)\)")


def extract_summary(lines: list[str], title: str) -> str:
    """Return the first descriptive paragraph after the preview image."""
    after_preview = False
    paragraph: list[str] = []
    for line in lines:
        if not after_preview:
            if PREVIEW_RE.search(line):
                after_preview = True
            continue
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith("[")
            or stripped.startswith("!")
            or stripped.startswith("---")
            or stripped == title
            or stripped.lower().startswith("each demo package")
            or stripped.startswith("<!--")
            or stripped.startswith("-->")
            or stripped.startswith("<")
            or stripped.startswith("```")
        ):
            continue
        if stripped.startswith(">"):
            stripped = stripped.lstrip("> ")
        stripped = re.sub(r"<[^>]+>", "", stripped)
        paragraph.append(stripped)
        if not stripped or len(paragraph) >= 2:
            break
    return " ".join(paragraph).strip()


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMOS_DIR = REPO_ROOT / "docs" / "demos"
GALLERY_FILE = REPO_ROOT / "docs" / "gallery.html"
DEMOS_INDEX_FILE = REPO_ROOT / "docs" / "demos" / "index.html"
SUBDIR_GALLERY_FILE = REPO_ROOT / "docs" / "alpha_factory_v1" / "demos" / "index.html"
INDEX_FILE = REPO_ROOT / "docs" / "index.html"


def parse_page(md_file: Path) -> tuple[str, str, str, str]:
    """Return ``(title, preview, link, summary)`` for ``md_file``.

    If ``docs/<demo>/index.html`` exists, link directly to that page.
    Otherwise fall back to the Markdown page under ``docs/demos``.
    """
    title: str | None = None
    preview: str | None = None
    lines = md_file.read_text(encoding="utf-8").splitlines()
    for line in lines:
        stripped = line.strip()
        if title is None:
            m = H1_RE.match(stripped)
            if m:
                candidate = m.group(1).strip()
                if DISCLAIMER_HEADING_RE.match(stripped):
                    # Skip the disclaimer heading
                    continue
                title = candidate
        if preview is None:
            m = PREVIEW_RE.search(line)
            if m:
                preview = m.group(1).strip()
        if title and preview:
            break
    if not title:
        title = md_file.stem.replace("_", " ").title()
    if preview:
        preview = preview.lstrip("./").lstrip("../")
        # Automatically switch to a corresponding video preview when available
        candidate = REPO_ROOT / "docs" / preview
        if candidate.suffix.lower() not in {".mp4", ".webm"}:
            for ext in (".mp4", ".webm"):
                alt = candidate.with_suffix(ext)
                if alt.is_file():
                    preview = str(Path(preview).with_suffix(ext))
                    break
    else:
        preview = "alpha_agi_insight_v1/favicon.svg"
    demo_index = REPO_ROOT / "docs" / md_file.stem / "index.html"
    if demo_index.is_file():
        link = f"{md_file.stem}/"
    else:
        link = f"demos/{md_file.stem}/"
    summary = extract_summary(lines, title)
    return title, preview, link, summary


def collect_entries() -> list[tuple[str, str, str, str]]:
    entries: list[tuple[str, str, str, str]] = []
    for page in sorted(DEMOS_DIR.glob("*.md")):
        if page.name.lower() == "readme.md":
            continue
        entries.append(parse_page(page))
    return entries


def insert_back_link(pages: Iterable[Path]) -> None:
    """Ensure a 'Back to Gallery' link exists in each HTML page."""
    for page in pages:
        if not page.is_file():
            continue
        text = page.read_text(encoding="utf-8")
        rel = Path(os.path.relpath(INDEX_FILE, page.parent)).as_posix()
        link = f'<p><a href="{rel}">\u2b05\ufe0f Back to Gallery</a></p>'
        if "Back to Gallery" in text:
            new_text = re.sub(
                r"<p><a href=\"[^\"]+\">\u2b05\ufe0f Back to Gallery</a></p>",
                link,
                text,
            )
            if new_text != text:
                page.write_text(new_text, encoding="utf-8")
            continue
        lines = text.splitlines()
        inserted = False
        for i, line in enumerate(lines):
            if "assets/style.css" in line:
                lines.insert(i, link)
                inserted = True
                break
        if not inserted:
            for i, line in enumerate(lines):
                if "</body>" in line.lower():
                    lines.insert(i, link)
                    inserted = True
                    break
        if not inserted:
            lines.append(link)
        page.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_html(entries: list[tuple[str, str, str, str]], *, prefix: str = "", home_link: bool = True) -> str:
    head = """<!-- SPDX-License-Identifier: Apache-2.0 -->
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Alpha‑Factory Demo Gallery</title>
  <link rel=\"stylesheet\" href=\"{prefix}stylesheets/cards.css\">
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 2rem; background: #f7f7f7; }}
    h1 {{ text-align: center; margin-bottom: 1rem; }}
    p.subtitle {{ text-align: center; margin-bottom: 2rem; }}
    a.demo-card {{ text-decoration: none; color: inherit; }}
    .demo-card h3 {{ margin-top: 0.5rem; text-align: center; }}
    .search-input {{ display: block; margin: 0 auto 1.5rem; padding: 0.5rem; width: min(300px, 80%); font-size: 1rem; }}
  </style>
</head>
<body>
  <h1>Alpha‑Factory Demo Gallery</h1>
  <p class=\"subtitle\">Select a demo to explore detailed instructions and watch it unfold in real time.</p>
  <input id=\"search-input\" class=\"search-input\" type=\"text\" placeholder=\"Search demos...\">
  <div class=\"demo-grid\">"""
    head = head.format(prefix=prefix)
    lines = [head]
    for title, preview, link, summary in entries:
        full_link = f"{prefix}{link}"
        summary_attr = html.escape(summary.lower()) if summary else ""
        title_attr = html.escape(summary or title)
        lines.append(
            '    <a class="demo-card" '
            f'href="{html.escape(full_link)}" target="_blank" '
            'rel="noopener noreferrer" '
            f'data-summary="{summary_attr}" '
            f'title="{title_attr}">'
        )
        preview_path = f"{prefix}{preview}"
        ext = Path(preview).suffix.lower()
        if ext in {".mp4", ".webm"}:
            track_file = (REPO_ROOT / "docs" / Path(preview).with_suffix(".vtt")).resolve()
            track_rel = f"{prefix}{Path(preview).with_suffix('.vtt')}"
            video_tag = (
                f'      <video src="{html.escape(preview_path)}" autoplay loop muted '
                f'playsinline loading="lazy" aria-label="{html.escape(title)}" '
                f'title="{html.escape(title)}">'
            )
            lines.append(video_tag)
            if track_file.is_file():
                lines.append(
                    f'        <track kind="captions" src="{html.escape(track_rel)}" '
                    'srclang="en" label="English" default>'
                )
                lines.append("      </video>")
            else:
                fallback = html.escape(f"Video preview of {title}")
                lines.append(f"        {fallback}</video>")
        else:
            alt_text = title
            if Path(preview).name == "readme_preview.svg":
                alt_text = "Demo Gallery Overview"
            lines.append(
                f'      <img src="{html.escape(preview_path)}" alt="{html.escape(alt_text)}" '
                f'loading="lazy" title="{html.escape(title)}">'
            )
        lines.append(f"      <h3>{html.escape(title)}</h3>")
        if summary:
            lines.append(f"      <p class='demo-desc'>{html.escape(summary)}</p>")
        lines.append("    </a>")
    lines.append("  </div>")
    if home_link:
        home_href = f"{prefix}index.html"
        lines.append(f'  <p><a href="{home_href}">\u2b05\ufe0f Back to Home</a></p>')
    lines.append(f'  <p class="snippet"><a href="{prefix}DISCLAIMER_SNIPPET/">See docs/DISCLAIMER_SNIPPET.md</a></p>')
    lines.append("  <script>")
    lines.append("    const input = document.getElementById('search-input');")
    lines.append("    const cards = document.querySelectorAll('.demo-card');")
    lines.append("    input.addEventListener('input', () => {")
    lines.append("      const term = input.value.toLowerCase();")
    lines.append("      cards.forEach(c => {")
    lines.append(
        "        const text = c.querySelector('h3').textContent.toLowerCase() + ' ' + (c.dataset.summary || '');"
    )
    lines.append("        c.style.display = text.includes(term) ? 'block' : 'none';")
    lines.append("      });")
    lines.append("    });")
    lines.append("  </script>")
    lines.append("</body>\n</html>\n")
    return "\n".join(lines)


def main() -> None:
    entries = collect_entries()

    index_html = build_html(entries, prefix="", home_link=False)
    INDEX_FILE.write_text(index_html, encoding="utf-8")

    gallery_redirect = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n<head>\n"
        "  <meta charset='UTF-8'>\n"
        "  <meta http-equiv='refresh' content='0; url=index.html'>\n"
        "  <title>Alpha‑Factory Demo Gallery</title>\n"
        "</head>\n<body>\n"
        "  <p>Redirecting to the <a href='index.html'>demo gallery</a>...</p>\n"
        "</body>\n</html>\n"
    )
    GALLERY_FILE.write_text(gallery_redirect, encoding="utf-8")

    demos_html = build_html(entries, prefix="../")
    DEMOS_INDEX_FILE.write_text(demos_html, encoding="utf-8")

    subdir_html = build_html(entries, prefix="../../")
    SUBDIR_GALLERY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUBDIR_GALLERY_FILE.write_text(subdir_html, encoding="utf-8")

    # Ensure all demo pages link back to the gallery
    pages = [
        p
        for p in REPO_ROOT.glob("docs/**/index.html")
        if p not in {INDEX_FILE, GALLERY_FILE, DEMOS_INDEX_FILE, SUBDIR_GALLERY_FILE}
        and "DISCLAIMER_SNIPPET" not in p.parts
    ]
    insert_back_link(pages)

    print(
        "Wrote",
        f" {INDEX_FILE.relative_to(REPO_ROOT)},",
        f" {GALLERY_FILE.relative_to(REPO_ROOT)},",
        f" {DEMOS_INDEX_FILE.relative_to(REPO_ROOT)} and",
        f" {SUBDIR_GALLERY_FILE.relative_to(REPO_ROOT)}",
    )


if __name__ == "__main__":
    main()
