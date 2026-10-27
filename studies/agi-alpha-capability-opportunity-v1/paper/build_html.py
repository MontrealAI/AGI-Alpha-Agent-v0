#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build complete, self-contained browser editions from the current LaTeX.

Run ``python paper/build_html.py`` from any directory after build_report.py and
build_figures.py (including the witness figure). Requires Pandoc and Beautiful
Soup. The source documents, generated inputs and figure files are read only.

Native MathML needs no external renderer. All figure PNGs are embedded. The
report printed to stdout and embedded in each document records static checks;
it deliberately makes no claim about browser viewport validation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DOCUMENTS = {
    "paper": "When Capability Creates Opportunity",
    "evidence-companion": "Evidence Companion",
    "executive-brief": "Executive Brief",
}

CSS = r"""
:root{--ink:#142b3a;--teal:#087e8b;--muted:#526773;--paper:#fff;
--cream:#f7f5ed;--mint:#dceee7;--line:#d8e0dc;--serif:Georgia,'Times New Roman',serif}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}
body{margin:0;color:var(--ink);background:var(--cream);font:16px/1.72 var(--serif)}
a{color:#076d79;text-underline-offset:3px}a:hover{color:#064b54}
a:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid #bd8527;outline-offset:4px}
.topbar{background:var(--ink);color:white;padding:20px 30px;font:12px/1.5 ui-sans-serif,system-ui,sans-serif}
.topbar-inner{max-width:1270px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:22px}
.brand{letter-spacing:.12em;font-weight:750;color:#d3eee3}.document-links{display:flex;gap:18px;flex-wrap:wrap}
.document-links a{color:#e2efee;text-decoration:none}.document-links a[aria-current=page]{color:#a7e3cf;text-decoration:underline}
.layout{max-width:1270px;margin:0 auto;padding:35px 30px 70px;display:grid;grid-template-columns:240px minmax(0,1fr);gap:35px}
aside{font:12px/1.6 ui-sans-serif,system-ui,sans-serif}.contents{position:sticky;top:24px;max-height:calc(100vh - 48px);overflow:auto}
.contents summary{font-size:12px;letter-spacing:.1em;text-transform:uppercase;font-weight:750;cursor:pointer;margin-bottom:14px;color:var(--teal)}
.contents ol{padding:0;list-style:none;margin:0}.contents li{margin:0 0 10px}.contents li.subsection{padding-left:13px;font-size:11px;line-height:1.5}
.contents a{color:var(--muted);text-decoration:none}.contents a:hover{color:var(--teal)}
.contents .toc-note{font-size:11px;border-top:1px solid var(--line);padding-top:14px;margin-top:20px;color:var(--muted)}
article{min-width:0;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:42px 46px;box-shadow:0 7px 28px #173b3e05}
.titlepage{border-bottom:1px solid var(--line);padding-bottom:26px;margin-bottom:35px}.titlepage p{margin:13px 0}
.titlepage .series{font:700 12px/1.5 ui-sans-serif,system-ui,sans-serif;letter-spacing:.14em;color:var(--teal)}
.titlepage h1{font:400 clamp(35px,4vw,51px)/1.12 var(--serif);letter-spacing:-.035em;margin:17px 0 21px;text-wrap:balance}
.titlepage h1 strong{font-weight:400}.titlepage .subtitle{font-size:19px;line-height:1.45;color:var(--muted)}
.titlepage .subtitle br{display:none}.titlepage p:nth-of-type(3),.titlepage p:nth-of-type(4){font-size:16px}
h2,h3,h4{font-family:ui-sans-serif,system-ui,sans-serif;line-height:1.3;scroll-margin-top:25px}
h2{font-size:23px;letter-spacing:-.02em;margin:42px 0 18px;padding-top:10px;border-top:1px solid var(--line)}
h3{font-size:17px;color:var(--teal);margin:30px 0 13px}h4{font-size:15px;margin:23px 0 10px}
p{margin:15px 0;overflow-wrap:break-word}strong{font-weight:700}em{font-style:italic}
.findingbox{border-left:4px solid var(--teal);background:#edf5f2;padding:17px 20px;margin:24px 0;font-size:15px;line-height:1.65}
.findingbox p{margin:0}.findingbox p>span:first-child{display:block;font:700 11px/1.5 ui-sans-serif,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--teal);margin-bottom:8px}
.table-scroll{overflow-x:auto;margin:24px -10px;padding:0 10px 5px;scrollbar-color:#8ba6a1 #eef1ea}
table{width:100%!important;border-collapse:collapse;font:12px/1.55 ui-sans-serif,system-ui,sans-serif;margin:0;min-width:540px}
table th{background:#e7f1ec;text-align:left;color:#234f50;font-size:10px;text-transform:uppercase;letter-spacing:.035em;font-weight:750;border-bottom:2px solid #a8c7bc}
table th,table td{padding:11px 10px;border-bottom:1px solid #dce5de;vertical-align:top;overflow-wrap:anywhere}
table tbody tr:nth-child(even){background:#f7f9f4}table tbody tr:last-child td{border-bottom:2px solid #bfd0c6}
.table-scroll:after{content:'Tables scroll horizontally on small screens.';display:block;color:var(--muted);font:10px/1.6 ui-sans-serif,system-ui,sans-serif;margin-top:7px}
figure{margin:32px -12px;background:#fbfcf8;border:1px solid #dce6dd;border-radius:6px;padding:15px}
figure img{display:block;width:100%;height:auto;max-width:100%;margin:auto;object-fit:contain}
figcaption{font:12px/1.6 ui-sans-serif,system-ui,sans-serif;color:var(--muted);margin:13px 3px 2px}
.figure-number{font-weight:750;color:#285b5e}
code{font:11px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;background:#f0f4ed;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow:auto;font-size:12px;padding:15px;background:#f0f4ed}
math{font-size:1.03em}math[display=block]{display:block;overflow-x:auto;padding:19px 12px;margin:22px 0;background:#f8faf5;border:1px solid #e0e8dd;border-radius:4px}
.citation{white-space:nowrap;font:11px/1.5 ui-sans-serif,system-ui,sans-serif}.citation a{text-decoration:none;font-weight:700}
.references{font:12px/1.65 ui-sans-serif,system-ui,sans-serif;padding-left:25px}.references li{padding-left:6px;margin:0 0 16px;overflow-wrap:anywhere}
.references p{margin:0}.references a{overflow-wrap:anywhere}
.edition-footer{border-top:1px solid var(--line);padding-top:22px;margin-top:38px;font:11px/1.65 ui-sans-serif,system-ui,sans-serif;color:var(--muted)}
.edition-footer a{white-space:nowrap}.skip{position:absolute;left:-10000px}.skip:focus{position:fixed;left:12px;top:12px;background:white;padding:12px;z-index:10}
@media(max-width:1000px){.layout{grid-template-columns:185px minmax(0,1fr);gap:22px;padding:28px 20px}article{padding:32px}.titlepage h1{font-size:40px}}
@media(max-width:760px){.layout{display:block;padding:20px 13px}.topbar{padding:17px}.topbar-inner{display:block}.document-links{margin-top:13px;gap:11px;font-size:11px}aside{margin-bottom:20px}.contents{position:static;max-height:none;border:1px solid var(--line);padding:13px 16px;background:#edf2e9;border-radius:5px}.contents summary{margin:0}.contents ol{margin-top:17px}.contents .toc-note{display:none}article{padding:26px 22px}.titlepage h1{font-size:36px}h2{font-size:21px;margin-top:34px}figure{margin:26px -10px;padding:10px}.table-scroll{margin-left:-8px;margin-right:-8px}body{font-size:15px}}
@media print{body{background:white;font-size:11pt}.topbar,aside,.edition-footer,.skip{display:none}.layout{display:block;padding:0;max-width:none}article{padding:0;border:0;box-shadow:none}.titlepage{break-after:page}h2,h3,figcaption{break-after:avoid}figure,table{break-inside:avoid}a{color:inherit;text-decoration:none}.table-scroll{overflow:visible}.table-scroll:after{display:none}table{min-width:0;font-size:9pt}math[display=block]{overflow:visible}}
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expand_inputs(path: Path, sources: dict[str, str], chain: tuple[Path, ...] = ()) -> str:
    path = path.resolve()
    if path in chain:
        raise ValueError(f"Recursive LaTeX input: {path}")
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Input outside the paper directory: {path}")
    sources[str(path.relative_to(ROOT))] = sha256(path)
    source = path.read_text()

    def replace(match: re.Match[str]) -> str:
        target = Path(match.group(1))
        if not target.suffix:
            target = target.with_suffix(".tex")
        # TeX compilation in this project resolves inputs from the paper cwd.
        child = ROOT / target
        if not child.exists():
            child = path.parent / target
        return expand_inputs(child, sources, (*chain, path))

    return re.sub(r"\\input\s*\{([^}]+)\}", replace, source)


def pandoc(source: str) -> str:
    result = subprocess.run(
        ["pandoc", "--from=latex", "--to=html5", "--mathml", "--wrap=none"],
        input=source,
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=True,
    )
    if result.stderr.strip():
        raise RuntimeError("Pandoc reported a conversion warning:\n" + result.stderr)
    return result.stdout


def prepare_source(source: str, images: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    # texmath accepts modern math font commands. This preserves the text and
    # mathematical semantics of the source's three legacy {\rm ...} forms.
    source = re.sub(r"\{\\rm\s+([^{}]*)\}", r"{\\mathrm{\1}}", source)

    def image_replace(match: re.Match[str]) -> str:
        relative = Path(match.group(2))
        if relative.suffix.lower() == ".pdf":
            relative = relative.with_suffix(".png")
        candidate = (ROOT / relative).resolve()
        if not candidate.is_relative_to(ROOT) or not candidate.is_file():
            raise FileNotFoundError(f"Build the matching figure PNG first: {candidate}")
        images[str(candidate.relative_to(ROOT))] = sha256(candidate)
        return "\\includegraphics" + (match.group(1) or "") + "{" + str(relative) + "}"

    source = re.sub(r"\\includegraphics(\[[^]]*\])?\{([^}]+)\}", image_replace, source)
    entries: list[tuple[str, str]] = []
    bibliography = re.search(
        r"\\begin\{thebibliography\}\{[^}]*\}(.*?)\\end\{thebibliography\}",
        source,
        flags=re.S,
    )
    if bibliography:
        pieces = re.split(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}", bibliography.group(1))
        entries = [(pieces[index], pieces[index + 1].strip()) for index in range(1, len(pieces), 2)]
        source = source[: bibliography.start()] + "\n" + source[bibliography.end() :]
    return source, entries


def normalize(text: str) -> str:
    return re.sub(r"[^\w]+", "", text, flags=re.UNICODE).casefold()


def render(name: str, pandoc_version: str) -> dict[str, Any]:
    source_hashes: dict[str, str] = {}
    figure_hashes: dict[str, str] = {}
    expanded = expand_inputs(ROOT / f"{name}.tex", source_hashes)
    prepared, references = prepare_source(expanded, figure_hashes)
    expected_sections = re.findall(r"\\(?:sub)*section\*?\{([^}]+)\}", expanded)
    expected_urls = re.findall(r"\\(?:url|href)\{(https?://[^}]+)\}", expanded)
    soup = BeautifulSoup(pandoc(prepared), "html.parser")

    # A real bibliography is preserved rather than accepting Pandoc's empty
    # citation spans and unnumbered run-on conversion of thebibliography.
    reference_numbers = {key: index for index, (key, _) in enumerate(references, 1)}
    for citation in soup.select(".citation[data-cites]"):
        keys = citation["data-cites"].split()
        citation.clear()
        citation.append("[")
        for position, key in enumerate(keys):
            if key not in reference_numbers:
                raise ValueError(f"Unresolved citation in {name}: {key}")
            if position:
                citation.append(", ")
            anchor = soup.new_tag("a", href=f"#ref-{key}")
            anchor.string = str(reference_numbers[key])
            citation.append(anchor)
        citation.append("]")

    if references:
        heading = soup.new_tag("h1", id="references")
        heading.string = "References"
        soup.append(heading)
        listing = soup.new_tag("ol", attrs={"class": "references"})
        for key, text in references:
            entry = soup.new_tag("li", id=f"ref-{key}")
            converted = BeautifulSoup(pandoc(text), "html.parser")
            for child in list(converted.contents):
                entry.append(child)
            listing.append(entry)
        soup.append(listing)

    # Keep the complete source title matter. Companion documents use ordinary
    # paragraphs in place of a titlepage environment; group those paragraphs.
    titlepage = soup.select_one(".titlepage")
    if titlepage is None:
        titlepage = soup.new_tag("div", attrs={"class": "titlepage"})
        frontmatter = []
        for child in list(soup.contents):
            if getattr(child, "name", None) in {"h1", "h2", "h3"}:
                break
            frontmatter.append(child)
        for child in frontmatter:
            titlepage.append(child.extract())
        soup.insert(0, titlepage)

    for heading in soup.find_all(re.compile(r"^h[1-5]$")):
        heading.name = "h" + str(int(heading.name[1]) + 1)
    paragraphs = titlepage.find_all("p", recursive=False)
    if paragraphs:
        paragraphs[0]["class"] = ["series"]
    if len(paragraphs) > 1:
        paragraphs[1].name = "h1"
    if len(paragraphs) > 2:
        paragraphs[2]["class"] = ["subtitle"]

    for index, figure in enumerate(soup.find_all("figure"), 1):
        caption = figure.find("figcaption")
        if caption:
            prefix = soup.new_tag("span", attrs={"class": "figure-number"})
            prefix.string = f"Figure {index}. "
            caption.insert(0, prefix)
        for image in figure.find_all("img"):
            if not image.get("alt") and caption:
                image["alt"] = caption.get_text(" ", strip=True)
    for image in soup.find_all("img"):
        candidate = (ROOT / image["src"]).resolve()
        if not candidate.is_relative_to(ROOT):
            raise ValueError("External figure path is not allowed")
        image["src"] = "data:image/png;base64," + base64.b64encode(candidate.read_bytes()).decode()
        image["loading"] = "lazy"
        image["decoding"] = "async"
    for table in soup.find_all("table"):
        wrapper = soup.new_tag(
            "div",
            attrs={"class": "table-scroll", "tabindex": "0", "role": "region", "aria-label": "Research results table"},
        )
        table.wrap(wrapper)

    toc = []
    for heading in soup.find_all(["h2", "h3"]):
        identifier = heading.get("id")
        if not identifier:
            raise ValueError(f"Missing heading identifier: {heading}")
        toc.append(
            '<li class="'
            + ("subsection" if heading.name == "h3" else "section")
            + '"><a href="#'
            + html.escape(identifier, quote=True)
            + '">'
            + html.escape(heading.get_text(" ", strip=True))
            + "</a></li>"
        )

    check_soup = BeautifulSoup(str(soup), "html.parser")
    for annotation in check_soup.find_all("annotation"):
        annotation.decompose()
    visible = check_soup.get_text(" ", strip=True)
    normalized_visible = normalize(visible)
    missing_sections = [section for section in expected_sections if normalize(section) not in normalized_visible]
    if missing_sections:
        raise ValueError(f"Missing source sections in {name}: {missing_sections}")
    if soup.select("span.math") or re.search(
        r"\\(?:begin|end|input|includegraphics|textbf|texttt|mathcal|widehat|frac|cite)\b", visible
    ):
        raise ValueError(f"Visible unconverted TeX remains in {name}")
    found_urls = {link.get("href") for link in soup.find_all("a")}
    missing_urls = [url for url in expected_urls if url not in found_urls]
    if missing_urls:
        raise ValueError(f"Missing source URLs in {name}: {missing_urls}")
    source_ids = {tag.get("id") for tag in soup.find_all(id=True)}
    broken_internal = [
        link["href"]
        for link in soup.find_all("a", href=True)
        if link["href"].startswith("#") and link["href"][1:] not in source_ids
    ]
    if broken_internal:
        raise ValueError(f"Unresolved internal citations: {broken_internal}")
    if any(not image.get("src", "").startswith("data:") for image in soup.find_all("img")):
        raise ValueError("Unembedded image remains")
    if soup.find_all(["script", "iframe", "embed"]):
        raise ValueError("Unexpected external execution or embedded PDF")
    for relative, original_hash in source_hashes.items():
        if sha256(ROOT / relative) != original_hash:
            raise RuntimeError("LaTeX changed during export; rerun after editing finishes")

    validation = {
        "status": "PASS_STATIC_CONVERSION",
        "source": f"{name}.tex",
        "pandoc_version": pandoc_version,
        "source_sha256": source_hashes,
        "figure_sha256": figure_hashes,
        "core_section_titles_preserved": len(expected_sections),
        "source_urls_preserved": len(expected_urls),
        "bibliography_entries": len(references),
        "tables": len(soup.find_all("table")),
        "embedded_images": len(soup.find_all("img")),
        "native_mathml_expressions": len(soup.find_all("math")),
        "visible_raw_tex": False,
        "external_assets": 0,
        "javascript_required": False,
        "viewport_validation": "NOT_RUN: local browser navigation was blocked by the cloud URL security policy; no workaround used.",
    }
    nav = []
    for document, title in DOCUMENTS.items():
        current = ' aria-current="page"' if document == name else ""
        nav.append(
            f'<a href="{document}.html"{current}>{html.escape(title if document != "paper" else "Full paper")}</a>'
        )
    nav.append('<a href="../browser/index.html">EN / FR demonstration</a>')
    nav.append(f'<a href="{name}.pdf">Download PDF</a>')
    validation_json = json.dumps(validation, sort_keys=True).replace("</", "<\\/")
    document_html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Complete browser edition of {html.escape(DOCUMENTS[name])}, by Vincent Boucher, President of MONTREAL.AI. Executed synthetic evidence and explicitly conditional economics.">
<meta name="author" content="Vincent Boucher, President of MONTREAL.AI">
<title>{html.escape(DOCUMENTS[name])} | AGI ALPHA FLYWHEEL</title><style>{CSS}</style></head>
<body id="top"><a class="skip" href="#article">Skip to the complete document</a>
<header class="topbar"><div class="topbar-inner"><div class="brand">AGI ALPHA FLYWHEEL / MONTREAL.AI</div><nav class="document-links" aria-label="Research editions">{"".join(nav)}</nav></div></header>
<div class="layout"><aside><details class="contents" open><summary>Contents</summary><ol>{"".join(toc)}</ol><p class="toc-note">Complete LaTeX-derived edition. Figures, styles and mathematical notation are included in this file. No JavaScript or external assets are required.</p></details></aside>
<article id="article">{str(soup)}<footer class="edition-footer"><p>Vincent Boucher · President of MONTREAL.AI · Research edition, 27 October 2026.</p><p>This browser edition preserves the current LaTeX text, generated tables, references and figures. The reported experiments use synthetic environments; the commercial accounts remain conditional simulations. Actual customer revenue is zero.</p><p><a href="#top">Back to top</a> · <a href="{name}.tex">LaTeX source</a> · <a href="{name}.pdf">PDF edition</a></p></footer></article></div>
<script type="application/json" id="build-validation">{validation_json}</script>
</body></html>'''
    (ROOT / f"{name}.html").write_text(document_html)
    validation["output_bytes"] = len(document_html.encode())
    return validation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", nargs="+", choices=DOCUMENTS, default=list(DOCUMENTS))
    arguments = parser.parse_args()
    version = subprocess.run(["pandoc", "--version"], text=True, capture_output=True, check=True).stdout.splitlines()[0]
    reports = [render(name, version) for name in arguments.documents]
    print(json.dumps({"status": "PASS", "documents": reports}, indent=2))


if __name__ == "__main__":
    main()
