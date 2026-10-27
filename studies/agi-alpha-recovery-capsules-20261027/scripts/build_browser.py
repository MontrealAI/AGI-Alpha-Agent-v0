#!/usr/bin/env python3
"""Build and audit the complete, offline browser edition of this study.

From the study directory: python scripts/build_browser.py
Optional responsive rendering: python scripts/build_browser.py --render
Requires Pandoc 3.x and beautifulsoup4; --render also needs Playwright/Chromium.
No network access, model calls, or external assets are used by the build.
"""
from __future__ import annotations

import argparse
import base64
import collections
import copy
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "publication"
OUT = PUB / "browser-edition.html"
QA = ROOT / "evidence" / "browser-qa.json"
TITLE = "AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
SUBTITLE = "Recovery Capsules: Making Stranded Analysis Usable"
AUTHOR = "Vincent Boucher — President of MONTREAL.AI"
STATUS = "Pinned review edition; canonical release pending qualification."


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], stdin: str | None = None) -> str:
    p = subprocess.run(args, input=stdin, text=True, capture_output=True, cwd=PUB)
    if p.returncode:
        raise RuntimeError(f"Command failed: {' '.join(args)}\n{p.stderr}")
    if p.stderr.strip():
        # A dropped formula, missing reference, or unsupported source must be noticed.
        raise RuntimeError(f"Pandoc emitted a diagnostic:\n{p.stderr}")
    return p.stdout


def group(s: str, i: int) -> tuple[str, int]:
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s) or s[i] != "{":
        raise ValueError(f"Expected a brace group near {s[i:i+60]!r}")
    start = i + 1
    depth = 1
    i += 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start:i], i + 1
        i += 1
    raise ValueError("Unterminated brace group")


def plain_columns(spec: str) -> str:
    """Translate only layout directives; preserve every source table cell."""
    cols = []
    i = 0
    while i < len(spec):
        c = spec[i]
        if c.isspace() or c in "|:":
            i += 1
        elif c in "@!><":
            _, i = group(spec, i + 1)
        elif c in "pmb":
            _, i = group(spec, i + 1)
            cols.append("l")
        elif c in "XY":
            cols.append("l")
            i += 1
        elif c in "lcr":
            cols.append(c)
            i += 1
        else:
            raise ValueError(f"Unsupported table layout directive: {spec[i:]}")
    if not cols:
        raise ValueError("Empty table specification")
    return "".join(cols)


def preprocess(source: str) -> tuple[str, list[dict]]:
    changes = []
    marker = r"\begin{tabularx}"
    while marker in source:
        start = source.index(marker)
        width, p = group(source, start + len(marker))
        cols, end = group(source, p)
        replacement = r"\begin{tabular}{" + plain_columns(cols) + "}"
        changes.append({"from": marker + "{" + width + "}{" + cols + "}", "to": replacement})
        source = source[:start] + replacement + source[end:]
    source = source.replace(r"\end{tabularx}", r"\end{tabular}")
    source = re.sub(r"(\\includegraphics(?:\[[^\]]*\])?\{)([^}]+)\.pdf\}", r"\1\2.png}", source)
    return source, changes


def walk(x):
    if isinstance(x, dict):
        if "t" in x:
            yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def inline_text(x) -> str:
    if isinstance(x, list):
        return "".join(inline_text(y) for y in x)
    if not isinstance(x, dict):
        return ""
    t, c = x.get("t"), x.get("c")
    if t == "Str":
        return c
    if t in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if t == "Code":
        return c[1]
    if t in ("Math", "Image", "RawInline"):
        return ""
    if t in ("Cite", "Span", "Link"):
        return inline_text(c[1])
    if isinstance(c, list):
        return inline_text(c)
    return ""


def normalize(s: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", s.casefold(), re.UNICODE))


def meta_string(value: str) -> dict:
    return {"t": "MetaString", "c": value}


def dependency_versions() -> dict:
    result = {"python": platform.python_version(), "pandoc": subprocess.run(["pandoc", "--version"], capture_output=True, text=True).stdout.splitlines()[0]}
    for package in ("beautifulsoup4", "playwright"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "not installed; required only for optional rendering" if package == "playwright" else "not installed"
    return result


TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="Pandoc with the study's audited offline builder">
<meta name="author" content="Vincent Boucher — President of MONTREAL.AI">
<meta name="description" content="Four verified analytical recovery cases and complete conditional commercial economics. Research review edition; no customer sales demonstrated.">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'">
<title>$pagetitle$</title>
<style>__EDITION_CSS__
/* Browser-specific layout; the source edition.css remains unchanged. */
.kicker{font:700 .82rem/1.5 Arial,sans-serif;letter-spacing:.13em;text-transform:uppercase;color:var(--mid)}
.author{font-weight:700!important;color:var(--ink)!important}.series{font-size:1rem;max-width:760px}
.status{font-size:.88rem!important;border-top:1px solid var(--rule);padding-top:16px}
.vision{margin:25px 0;font:700 .83rem/1.7 Arial,sans-serif;color:var(--mid);letter-spacing:.025em}
.epigraph{font-size:.94rem;color:var(--muted);border-left:2px solid var(--rule);padding-left:20px;margin:25px 0}
.abstract>h2{font-size:1.25rem;border:0;margin:0;padding:0}.abstract p{font-size:1rem}
.table-scroll{overflow-x:auto;max-width:100%;margin:25px 0;scrollbar-color:var(--mid) var(--pale)}
.table-scroll:focus{outline:2px solid var(--mid);outline-offset:3px}.table-scroll table{margin:0}
caption{caption-side:bottom;padding:8px 0}.table-caption{font:14px/1.5 Arial,sans-serif;color:var(--muted);margin-top:-12px;margin-bottom:25px}.header-section-number{color:var(--mid);margin-right:.3em}
math{font-family:"STIX Two Math","Cambria Math",serif}math[display=block]{max-width:100%;padding:8px 0}
figure img{width:100%;height:auto}.csl-entry a{overflow-wrap:anywhere}a,td,th{overflow-wrap:anywhere}
td[style*="text-align: right"],th[style*="text-align: right"]{white-space:nowrap;overflow-wrap:normal;font-variant-numeric:tabular-nums}
.figure-scroll{overflow-x:auto;max-width:100%}.figure-zoom-toggle{position:absolute;opacity:0;width:1px;height:1px}.figure-zoom-label{display:none}.figure-zoom-toggle:focus-visible+.figure-zoom-label{outline:2px solid var(--purple)}
.source-note{display:block;font:13px/1.5 Arial,sans-serif;color:var(--muted);margin-top:5px}.source-url{display:block;margin-top:4px}
footer{border-top:2px solid var(--purple);margin-top:55px;padding-top:20px;font:14px/1.6 Arial,sans-serif;color:var(--muted)}
@media(max-width:650px){.subtitle{font-size:1.35rem}header{padding-top:10px}.table-scroll table{display:table;font-size:14px}.table-scroll table.wide-table{min-width:580px}.table-scroll td,.table-scroll th{padding:9px 8px}math[display=block]{font-size:.9rem}.abstract p{font-size:1rem}.figure-zoom-label{display:block;font:14px/1.5 Arial,sans-serif;color:var(--purple);background:var(--pale);padding:8px 10px;margin-bottom:8px;cursor:pointer}.figure-zoom-toggle:checked~.figure-scroll img{min-width:850px}}
</style>
</head>
<body>
<header id="title-block-header">
<p class="kicker">MONTREAL.AI · Research edition 1.0 · 27 October 2026</p>
<h1>$title$</h1>
<p class="subtitle">$subtitle$</p>
<p class="series">Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work</p>
<p class="author">$author$</p>
<p class="status"><strong>Pinned review edition; canonical release pending qualification.</strong> This is a complete offline reading edition, not a deployed customer service or a merged canonical release.</p>
</header>
<aside class="callout" aria-label="Commercial result and evidence boundary">
<strong>THE COMMERCIAL DELIVERY LANE COMES FIRST</strong>
<p>Four prospective analytical notebooks were recovered and independently checked: 133 code cells, 38 distinct numerical and semantic checks, two clean reruns.</p>
<p>The central twelve-month scenario returns <strong>$$36,309 after $$4,000 additional development</strong>, at $$900 per accepted outcome, eight attempts per month and 85% final acceptance. Demand and paid acceptance are assumptions. Actual collections are $$0; actual complete study cost is unknown.</p>
</aside>
<div class="vision">TRANSFORMATIONAL INTELLIGENCE: LEARNING TO CHANGE THE GAME<br>FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.</div>
<blockquote class="epigraph">“As Columbus braved the seas, we now venture into the vast oceans of AGI. The age of AGI exploration has dawned, and the horizons are boundless. Dare to dream, dare to explore.” — α-AGI Agent</blockquote>
$if(abstract)$
<section class="abstract" aria-labelledby="abstract-title"><h2 id="abstract-title">Abstract</h2>$abstract$</section>
$endif$
$if(toc)$
<nav id="TOC" role="doc-toc" aria-label="Contents"><h2>Contents</h2>$toc$</nav>
$endif$
<main id="manuscript">$body$</main>
<footer><strong>Evidence boundary:</strong> executed engineering analogues and a conditional commercial model. No claim of achieved general intelligence, demonstrated paid demand, technical novelty or production qualification. USD throughout. The full manuscript, appendices, equations, figures and bibliography are included; this file requires no network connection to read.</footer>
</body>
</html>
'''


def build() -> dict:
    source = (PUB / "body.tex").read_text()
    prepared, changes = preprocess(source)
    ast = json.loads(run(["pandoc", "--from=latex", "--to=json"], prepared))
    source_nodes = list(walk(ast))
    count = collections.Counter(x["t"] for x in source_nodes)
    expected_tables = len(re.findall(r"\\begin\{(?:tabularx|longtable)\}", source))
    expected_figures = len(re.findall(r"\\includegraphics", source))
    expected_headers = len(re.findall(r"\\(?:subsubsection|subsection|section)\*?\{", source))
    assert count["Table"] == expected_tables, (count["Table"], expected_tables)
    assert count["Figure"] == expected_figures, (count["Figure"], expected_figures)
    assert count["Header"] == expected_headers
    assert ast["meta"].get("abstract"), "Abstract missing"
    source_cites = set()
    for hit in re.findall(r"\\cite[a-zA-Z]*\{([^}]+)\}", source):
        source_cites.update(hit.split(","))
    bib_keys = set(re.findall(r"@\w+\s*\{\s*([^,]+),", (PUB / "references.bib").read_text()))
    assert source_cites <= bib_keys, source_cites - bib_keys
    noncite_raw = [x for x in source_nodes if x["t"] in ("RawInline", "RawBlock") and not re.fullmatch(r"\\cite[a-zA-Z]*\{[^}]+\}", x["c"][1])]
    assert not noncite_raw, noncite_raw
    figure_sources = []
    for node in source_nodes:
        if node["t"] == "Figure":
            caption = inline_text(node["c"][1])
            for image in (x for x in walk(node) if x["t"] == "Image"):
                filename = Path(image["c"][2][0]).name
                path = ROOT / "figures" / filename
                assert path.is_file(), path
                figure_sources.append({"file": f"figures/{filename}", "sha256": sha(path), "bytes": path.stat().st_size})
                image["c"][2][0] = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
                image["c"][1] = [{"t": "Str", "c": caption or filename.replace("_", " ")}]
    # Native Pandoc numbering does not retain LaTeX appendix letters. Prefix the
    # exact logical section sequence once, including A–D, then mark unnumbered.
    pre_appendix_count = len(re.findall(r"\\section\{", source.split(r"\appendix")[0]))
    major = sub = 0
    for node in source_nodes:
        if node["t"] != "Header":
            continue
        level, attr, inlines = node["c"]
        if "unnumbered" not in attr[1]:
            if level == 1:
                major += 1
                sub = 0
            elif level == 2:
                sub += 1
            main = str(major) if major <= pre_appendix_count else chr(64 + major - pre_appendix_count)
            label = main if level == 1 else f"{main}.{sub}"
            node["c"][2] = [{"t": "Span", "c": [["", ["header-section-number"], []], [{"t": "Str", "c": label}]]}, {"t": "Space"}] + inlines
            attr[1].append("unnumbered")
        node["c"][0] = level + 1
    ast["meta"].update({
        "title": meta_string(TITLE), "pagetitle": meta_string(TITLE + " | " + SUBTITLE),
        "subtitle": meta_string(SUBTITLE), "author": meta_string(AUTHOR),
        "lang": meta_string("en"), "reference-section-title": meta_string("References"),
        "link-citations": {"t": "MetaBool", "c": True},
        "nocite": {"t": "MetaInlines", "c": [{"t": "Cite", "c": [[{"citationId": "*", "citationPrefix": [], "citationSuffix": [], "citationMode": {"t": "NormalCitation"}, "citationNoteNum": 0, "citationHash": 0}], []]}]},
    })
    processed = json.loads(run(["pandoc", "--from=json", "--to=json", "--citeproc", "--bibliography", str(PUB / "references.bib")], json.dumps(ast)))
    assert not [x for x in walk(processed) if x["t"] in ("RawInline", "RawBlock")], "Unconverted raw source remains"
    with tempfile.TemporaryDirectory(prefix="recovery-browser-") as temp:
        template = Path(temp) / "template.html"
        template.write_text(TEMPLATE.replace("__EDITION_CSS__", (PUB / "edition.css").read_text()))
        html = run(["pandoc", "--from=json", "--to=html5", "--standalone", "--mathml", "--toc", "--toc-depth=3", "--section-divs", "--template", str(template), "--wrap=none"], json.dumps(processed))
    soup = BeautifulSoup(html, "html.parser")
    # The default CSL style omits BibTeX notes and can prefer DOI over URL.
    # Retain every source note and original URL as part of this full edition.
    bib_records = json.loads(run(["pandoc", str(PUB / "references.bib"), "--from=biblatex", "--to=csljson"]))
    bibliography_notes = 0
    for record in bib_records:
        entry = soup.find(id="ref-" + record["id"])
        assert entry is not None
        if record.get("note"):
            note = soup.new_tag("span", attrs={"class": "source-note"})
            note.string = "Source note: " + record["note"]
            entry.append(note)
            bibliography_notes += 1
        if record.get("URL") and record["URL"] not in [x.get("href") for x in entry.find_all("a")]:
            link = soup.new_tag("a", attrs={"class": "source-url", "href": record["URL"]})
            link.string = record["URL"]
            entry.append(link)
    for i, table in enumerate(soup.find_all("table"), 1):
        if max(len(row.find_all(["td", "th"], recursive=False)) for row in table.find_all("tr")) > 2:
            table["class"] = list(table.get("class", [])) + ["wide-table"]
        wrapper = soup.new_tag("div", attrs={"class": "table-scroll", "tabindex": "0", "role": "region", "aria-label": f"Scrollable table {i}"})
        table.wrap(wrapper)
        caption = table.find("caption", recursive=False)
        if caption:
            caption.extract()
            caption.name = "p"
            caption["class"] = ["table-caption"]
            caption["id"] = f"table-caption-{i}"
            table["aria-describedby"] = caption["id"]
            wrapper.insert_after(caption)
    for i, figure in enumerate(soup.find_all("figure"), 1):
        img = figure.find("img")
        region = soup.new_tag("div", attrs={"class": "figure-scroll", "tabindex": "0", "role": "region", "aria-label": f"Figure {i}; enlarged view scrolls horizontally"})
        img.wrap(region)
        toggle = soup.new_tag("input", attrs={"type": "checkbox", "class": "figure-zoom-toggle", "id": f"figure-zoom-{i}"})
        label = soup.new_tag("label", attrs={"class": "figure-zoom-label", "for": toggle["id"]})
        label.string = "Enlarge / reduce figure · scroll to read details"
        region.insert_before(toggle)
        region.insert_before(label)
    assert len(soup.find_all("table")) == expected_tables
    assert len(soup.find_all("figure")) == expected_figures
    assert len(soup.select("#refs .csl-entry")) == len(bib_keys)
    assert {x["id"][4:] for x in soup.select("#refs .csl-entry")} == bib_keys
    assert len(soup.find_all("math")) == count["Math"]
    annotations = [x.get_text() for x in soup.select('annotation[encoding="application/x-tex"]')]
    expected_math = [x["c"][1] for x in source_nodes if x["t"] == "Math"]
    assert annotations == expected_math, "Math expression content/order changed"
    for img, expected in zip(soup.find_all("img"), figure_sources):
        assert img["src"].startswith("data:image/png;base64,")
        assert hashlib.sha256(base64.b64decode(img["src"].split(",", 1)[1])).hexdigest() == expected["sha256"]
        assert img.get("alt")
    external_assets = []
    for tag in soup.find_all(True):
        for key in ("src", "srcset", "poster"):
            if tag.get(key) and not str(tag[key]).startswith("data:"):
                external_assets.append({"tag": tag.name, "attribute": key, "value": tag[key]})
        if tag.name == "link" and tag.get("href"):
            external_assets.append({"tag": "link", "href": tag["href"]})
    assert not external_assets, external_assets
    assert not soup.find_all("script"), "No JavaScript/CDN is needed by this edition"
    ids = {x["id"] for x in soup.find_all(id=True)}
    broken_anchors = [a.get("href") for a in soup.find_all("a", href=True) if a["href"].startswith("#") and a["href"][1:] not in ids]
    assert not broken_anchors, broken_anchors
    clean = copy.deepcopy(soup)
    for math in clean.find_all("math"):
        math.decompose()
    clean_text = normalize(clean.get_text(" "))
    blocks = [normalize(inline_text(x["c"])) for x in walk(processed) if x["t"] in ("Para", "Plain")]
    missing = [x for x in blocks if x and x not in clean_text]
    assert not missing, f"Paragraph/cell content missing: {missing[:5]}"
    for required in ("actual collections are zero", "free updated edition exists", "customer demand", "complete actual study cost is unknown", "canonical release pending qualification"):
        assert normalize(required) in clean_text, required
    OUT.write_text(str(soup), encoding="utf-8")
    return {
        "schema": "agi-alpha-browser-edition-qa-v1", "status": "PASS_STATIC_CHECKS",
        "edition_status": STATUS, "generated_from": "publication/body.tex; references.bib; edition.css; exact PNG figures",
        "command": "python scripts/build_browser.py --render", "pandoc_version": subprocess.run(["pandoc", "--version"], capture_output=True, text=True).stdout.splitlines()[0],
        "build_dependencies": dependency_versions(),
        "source_sha256": {name: sha(PUB / name) for name in ("body.tex", "paper.tex", "references.bib", "edition.css")},
        "builder_sha256": sha(Path(__file__)), "html_sha256": sha(OUT), "html_bytes": OUT.stat().st_size,
        "layout_normalization": changes,
        "content_checks": {"source_and_html_tables": expected_tables, "source_and_html_figures": expected_figures, "source_section_headers": expected_headers,
            "source_and_html_math_expressions": count["Math"], "exact_math_annotation_match": True, "bibliography_entries": len(bib_keys),
            "cited_unique_sources": len(source_cites), "paragraph_and_cell_blocks_present": len(blocks), "missing_content_blocks": missing,
            "bibliography_source_notes_preserved": bibliography_notes, "all_original_bibliography_urls_present": True,
            "unconverted_raw_source": 0, "broken_internal_anchors": broken_anchors, "external_assets": external_assets, "javascript_required": False,
            "abstract_present": True, "evidence_boundaries_present": True, "png_bytes_preserved": True},
        "figures": figure_sources, "responsive_rendering": {"status": "NOT_RUN", "reason": "Use --render for local Playwright checks."},
    }


def render(report: dict, screenshot_dir: Path):
    from playwright.sync_api import sync_playwright
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    viewports = [{"name": "desktop", "width": 1440, "height": 1000}, {"name": "tablet", "width": 768, "height": 1024}, {"name": "mobile", "width": 390, "height": 844}]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        results = []
        for viewport in viewports:
            page = browser.new_page(viewport={k: viewport[k] for k in ("width", "height")}, device_scale_factor=1)
            requests, errors = [], []
            page.on("request", lambda r: requests.append(r.url) if r.url.startswith(("http://", "https://")) else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(OUT.as_uri(), wait_until="load")
            result = page.evaluate("""() => ({viewport: innerWidth, documentWidth: document.documentElement.scrollWidth,
                documentHeight: document.documentElement.scrollHeight, tables: document.querySelectorAll('table').length,
                figures: document.querySelectorAll('figure').length, math: document.querySelectorAll('math').length,
                loadedImages: [...document.images].filter(x => x.complete && x.naturalWidth > 0).length,
                missingImages: [...document.images].filter(x => !x.complete || x.naturalWidth === 0).map(x => x.alt),
                horizontalTableRegions: [...document.querySelectorAll('.table-scroll')].filter(x => x.scrollWidth > x.clientWidth + 1).length,
                mathSupport: CSS.supports('math-style', 'normal'), title: document.title})""")
            assert result["documentWidth"] <= result["viewport"] + 1, (viewport, result)
            assert result["loadedImages"] == 5 and not result["missingImages"]
            assert result["tables"] == 9 and result["figures"] == 5 and result["math"] == report["content_checks"]["source_and_html_math_expressions"]
            assert result["mathSupport"], "Browser lacks native MathML support"
            assert not requests and not errors, (requests, errors)
            screenshots = []
            for label, selector in [("cover", "#title-block-header"), ("accounting", "#accounting-identities"), ("table", "#the-central-result"), ("figure", "#joint-downside-and-competitive-pressure figure"), ("references", "#refs")]:
                locator = page.locator(selector).first
                if locator.count():
                    locator.evaluate("el => window.scrollTo({top: el.getBoundingClientRect().top + scrollY - 20, behavior: 'instant'})")
                    path = screenshot_dir / f"browser-{viewport['name']}-{label}.png"
                    page.screenshot(path=str(path))
                    screenshots.append({"file": str(path), "sha256": sha(path)})
            if viewport["width"] < 650:
                for toggle in page.locator(".figure-zoom-toggle").all():
                    toggle.evaluate("el => el.click()")
                expanded = page.evaluate("""() => ({widths: [...document.querySelectorAll('figure img')].map(x => x.getBoundingClientRect().width),
                    documentWidth: document.documentElement.scrollWidth, scrollRegions: [...document.querySelectorAll('.figure-scroll')].filter(x => x.scrollWidth > x.clientWidth).length})""")
                assert min(expanded["widths"]) >= 850 and expanded["documentWidth"] <= viewport["width"] + 1 and expanded["scrollRegions"] == 5
                result["expanded_figures"] = expanded
                page.locator("figure").nth(2).evaluate("el => window.scrollTo({top: el.getBoundingClientRect().top + scrollY - 20, behavior: 'instant'})")
                path = screenshot_dir / "browser-mobile-figure-expanded.png"
                page.screenshot(path=str(path))
                screenshots.append({"file": str(path), "sha256": sha(path)})
            results.append({**viewport, **result, "external_requests": requests, "page_errors": errors, "screenshots": screenshots, "status": "PASS"})
            page.close()
        report["responsive_rendering"] = {"status": "PASS", "engine": "Chromium " + browser.version, "network": "Local file only; no HTTP(S) requests", "viewports": results,
            "visual_inspection": {"status": "PENDING", "scope": "Screenshots generated for cover, accounting, table, figure, and references at each viewport; separate image inspection required."}}
        report["build_dependencies"]["chromium"] = browser.version
        report["status"] = "PASS_STATIC_AND_RESPONSIVE_CHECKS"
        browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="Check desktop/tablet/mobile using local Chromium")
    parser.add_argument("--screenshots", type=Path, default=ROOT.parent / "qa" / "browser")
    args = parser.parse_args()
    report = build()
    if args.render:
        try:
            render(report, args.screenshots)
        except Exception as exc:
            report["responsive_rendering"] = {"status": "BLOCKED_OR_FAILED", "exception": type(exc).__name__, "reason": str(exc)}
            QA.write_text(json.dumps(report, indent=2) + "\n")
            raise
    QA.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"html": str(OUT), "qa": str(QA), "status": report["status"], "content_checks": report["content_checks"]}, indent=2))


if __name__ == "__main__":
    main()
