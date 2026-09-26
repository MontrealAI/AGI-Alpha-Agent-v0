#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the visual demo gallery HTML files.

This helper reads the Markdown pages under ``docs/demos`` and extracts each
page's title and preview image. It outputs ``docs/index.html`` and
``docs/demos/index.html`` so the GitHub Pages site always lists every demo in a
simple grid. ``docs/gallery.html`` is written as a simple redirect for backward
compatibility.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable

try:
    from alpha_factory_v1.utils.disclaimer import DISCLAIMER
except Exception:  # pragma: no cover - fallback when package not installed
    _DOCS_PATH = Path(__file__).resolve().parents[1] / "docs" / "DISCLAIMER_SNIPPET.md"
    DISCLAIMER = _DOCS_PATH.read_text(encoding="utf-8").strip()

H1_RE = re.compile(r"^#\s+(.*)")
DISCLAIMER_HEADING_RE = re.compile(
    r"^#\s+\[See docs/DISCLAIMER_SNIPPET.md\]",
    re.IGNORECASE,
)
PREVIEW_RE = re.compile(r"!\[preview\]\(([^)]+)\)")


def clean_text(text: str) -> str:
    """Return *text* with markdown emphasis and HTML tags stripped."""
    # Unescape HTML entities first
    text = html.unescape(text)
    # Drop HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove emphasis markers such as *, _, ** and backticks
    text = re.sub(r"\*\*|__|[*_`]", "", text)
    return text.strip()


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
    return clean_text(" ".join(paragraph).strip())


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
    catalog_path = REPO_ROOT / "alpha_factory_v1" / "demos" / "catalog.json"
    if catalog_path.is_file():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        entry = next((entry for entry in catalog["entries"] if entry["id"] == md_file.stem), None)
        if entry:
            title = entry["title"]
            summary = entry["mode"] + ": " + entry["summary"]
    return title, preview, link, summary


def collect_entries() -> list[tuple[str, str, str, str]]:
    entries: list[tuple[str, str, str, str]] = []
    for page in sorted(DEMOS_DIR.glob("*.md")):
        if page.name.lower() in {"readme.md", "terms_and_conditions.md"}:
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


def build_html(
    entries: list[tuple[str, str, str, str]],
    *,
    prefix: str = "",
    home_link: bool = True,
    subdir_link: str | None = None,
) -> str:
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
  <p class=\"subtitle\">Choose a demo below. Legacy charts replay bundled samples;
    each guide explains what runs locally.</p>
  {subdir}
    <input id=\"search-input\" class=\"search-input\" type=\"text\"
           placeholder=\"Search demos...\" aria-label=\"Search demos\">
  <p id=\"result-count\" role=\"status\" aria-live=\"polite\"></p>
  <p id=\"no-results\" hidden>No matching demos. Clear the search to see all entries.</p>
  <main class=\"demo-grid\">"""
    subdir_html = (
        f'<p class="subtitle"><a href="{prefix}alpha_factory_v1/demos/index.html">Open Subdirectory Gallery</a></p>'
        if subdir_link
        else ""
    )
    head = head.format(prefix=prefix, subdir=subdir_html)
    lines = [head]
    for title, preview, link, summary in entries:
        full_link = f"{prefix}{link}"
        clean_title = clean_text(title)
        clean_summary = clean_text(summary) if summary else ""
        summary_parts = [clean_title.lower()]
        if clean_summary:
            summary_parts.append(clean_summary.lower())
        summary_attr = html.escape(" ".join(summary_parts))
        title_attr = html.escape(summary or title)
        lines.append(
            '    <a class="demo-card" '
            f'href="{html.escape(full_link)}" '
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
            alt_text = clean_title
            if Path(preview).name == "readme_preview.svg":
                alt_text = "Demo Gallery Overview"
            lines.append(
                f'      <img src="{html.escape(preview_path)}" alt="{html.escape(alt_text)}" '
                f'loading="lazy" title="{html.escape(title)}">'
            )
        lines.append(f"      <h3>{html.escape(title)}</h3>")
        if summary:
            lines.append(f"      <p class='demo-desc'>{html.escape(summary)}</p>")
        lines.append("      <span class='launch'>Open demo and guide</span>")
        lines.append("    </a>")
    lines.append("  </main>")
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
    lines.append("        c.hidden = !text.includes(term);")
    lines.append("      });")
    lines.append("      const count = [...cards].filter(card => !card.hidden).length;")
    lines.append("      document.getElementById('result-count').textContent = `${count} of ${cards.length} entries`;")
    lines.append("      document.getElementById('no-results').hidden = count !== 0;")
    lines.append("    });")
    lines.append("    input.dispatchEvent(new Event('input'));")
    lines.append("  </script>")
    lines.append("  <script>")
    lines.append("    if ('serviceWorker' in navigator) {")
    lines.append(
        f"      navigator.serviceWorker.register('{prefix}service-worker.js')"
        ".catch(() => console.warn('Service worker registration failed'));"
    )
    lines.append("    }")
    lines.append("  </script>")
    lines.append("</body>\n</html>\n")
    html_out = "\n".join(lines)
    return html_out


def main() -> None:
    print(DISCLAIMER, file=sys.stderr)
    entries = collect_entries()

    gallery = build_html(entries, home_link=False)
    cards = gallery.split('  <main class="demo-grid">', 1)[1].split("  </main>", 1)[0]
    template = (REPO_ROOT / "scripts" / "templates" / "portal.html").read_text(encoding="utf-8")
    version = json.loads((REPO_ROOT / "alpha_factory_v1/demos/catalog.json").read_text())["release"]
    index_html = template.replace("{{GALLERY}}", '<div class="demo-grid">' + cards + "</div>")
    index_html = index_html.replace("{{VERSION}}", version)
    examples = {
        kind: json.loads((REPO_ROOT / f"examples/missions/{kind}.json").read_text())
        for kind in ("allocation", "research", "schedule", "forecast")
    }
    (REPO_ROOT / "docs/assets/portal/examples.json").write_text(json.dumps(examples, indent=2) + "\n")
    INDEX_FILE.write_text(index_html, encoding="utf-8")
    ascension = REPO_ROOT / "docs/ascension/index.html"
    ascension.parent.mkdir(parents=True, exist_ok=True)
    ascension.write_text(
        (REPO_ROOT / "scripts/templates/ascension.html").read_text(encoding="utf-8").replace("{{VERSION}}", version),
        encoding="utf-8",
    )
    insight = REPO_ROOT / "docs/insight/index.html"
    insight.parent.mkdir(parents=True, exist_ok=True)
    insight.write_text(
        (REPO_ROOT / "scripts/templates/insight.html").read_text(encoding="utf-8").replace("{{VERSION}}", version),
        encoding="utf-8",
    )
    # Publish the unchanged original paper, without maintaining a second binary source.
    shutil.copyfile(
        REPO_ROOT / "whitepaper_v0.1.0-alphav15.pdf", REPO_ROOT / "docs/assets/whitepaper_v0.1.0-alphav15.pdf"
    )

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
