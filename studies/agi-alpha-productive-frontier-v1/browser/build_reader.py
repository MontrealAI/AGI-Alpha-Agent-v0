# SPDX-License-Identifier: Apache-2.0
"""Render a no-JavaScript reading edition of exact pagewise PDF text extraction."""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.metadata
import json
import os
from pathlib import Path
import re

import fitz

HERE = Path(__file__).resolve().parent
DEFAULT_PDF = HERE.parent / "paper" / "Making_the_Next_Opportunity_Possible.pdf"

STYLE = """
:root{--navy:#0b1c31;--ink:#192d41;--muted:#536477;--mint:#b2e6d4;--line:#d8dfdf;--paper:#f7f7f2}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 Arial,Helvetica,sans-serif}
a{color:inherit;text-underline-offset:4px}a:focus-visible,summary:focus-visible{outline:3px solid #b87b18;outline-offset:4px}
.wrap{max-width:1130px;margin:auto;padding:0 34px}.skip{position:absolute;left:12px;top:-80px;background:white;padding:8px;z-index:20}.skip:focus{top:10px}
.hero{background:var(--navy);color:#f8faf7;padding:27px 0 44px}.brand{font-size:12px;font-weight:bold;letter-spacing:2px;border-bottom:1px solid #ffffff30;padding-bottom:20px;margin-bottom:30px}.brand b{color:var(--mint);font-size:23px;margin-right:10px}
.eyebrow{font-size:11px;letter-spacing:1.6px;font-weight:bold;text-transform:uppercase;color:var(--mint)}h1{font:400 clamp(33px,4.5vw,58px)/1.12 Georgia,'Times New Roman',serif;max-width:950px;letter-spacing:-1.4px;margin:18px 0 24px}.byline{font-size:14px;color:#dbe5e9}.links{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}.links a{border:1px solid #a2b3ba;border-radius:3px;padding:9px 14px;font-size:13px;font-weight:bold;text-decoration:none}.links a.primary{background:var(--mint);color:var(--navy);border-color:var(--mint)}
.intro{padding:34px 0 25px;max-width:850px}.intro p{margin:0 0 17px}.note{font-size:13px;color:var(--muted)}.boundary{border-left:3px solid #347b67;padding:12px 18px;background:#edf3ef;font-size:14px}.boundary strong{display:block;margin-bottom:4px}
details{border:1px solid var(--line);padding:13px 17px;background:white;margin:20px 0;font-size:12px}summary{cursor:pointer;font-weight:bold}.hash{display:block;font:11px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;margin-top:10px}
.contents{background:#edf2ef;border:1px solid var(--line);padding:20px 24px;margin-bottom:36px}.contents h2{font-size:14px;margin:0 0 13px}.contents ol{display:flex;flex-wrap:wrap;gap:8px;list-style:none;margin:0;padding:0}.contents a{display:inline-flex;align-items:center;justify-content:center;min-width:39px;min-height:39px;background:white;border:1px solid #c7d2ce;border-radius:3px;text-decoration:none;font-size:13px}.contents a:hover{background:#dceee5}
.page{background:white;border:1px solid var(--line);margin:0 0 28px;padding:26px 34px 31px;scroll-margin-top:15px}.page-head{display:flex;align-items:center;justify-content:space-between;gap:18px;border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:24px}.page-head h2{font-size:13px;letter-spacing:.3px;margin:0}.page-head a{font-size:12px;color:var(--muted)}
.page-text{white-space:pre-wrap;overflow-wrap:anywhere;font:17px/1.7 Georgia,'Times New Roman',serif;margin:0;tab-size:4;max-width:100%;color:#223143}.page-foot{display:flex;gap:20px;flex-wrap:wrap;border-top:1px solid var(--line);padding-top:18px;margin-top:27px;font-size:12px;color:var(--muted)}
footer{padding:12px 0 40px;font-size:12px;color:var(--muted)}footer p{margin:12px 0}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:650px){.wrap{padding:0 20px}.hero{padding-bottom:30px}.page{padding:20px 21px}.page-text{font-size:16px;line-height:1.7}.page-head{align-items:flex-start}.page-head h2{font-size:12px}.page-head a{font-size:11px}.contents{padding:18px}.intro{padding-top:25px}h1{letter-spacing:-.8px}}
@media(max-width:360px){.wrap{padding:0 14px}.page{padding:18px 16px}.page-head{gap:10px}.links a{font-size:12px}.page-text{font-size:15px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{.hero{background:white;color:var(--ink);padding:0}.hero .byline,.eyebrow{color:var(--ink)}.contents,.links,.page-head a,.page-foot,.intro details{display:none}.page{border:0;break-before:page;padding:0;margin:0}.page-text{font-size:11pt}.wrap{max-width:none;padding:0}}
"""


def build(pdf: Path, output: Path, expected_sha256: str | None = None) -> dict:
    """Escape every extracted character and bind the edition to the original PDF."""
    pdf = pdf.resolve()
    raw = pdf.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("PDF bytes differ from the frozen original")
    with fitz.open(pdf) as document:
        if document.is_encrypted:
            raise ValueError("The reading edition requires an unencrypted PDF")
        pages = [page.get_text("text", sort=True) for page in document]
        metadata = document.metadata
    if not pages or any(not page.strip() for page in pages):
        raise ValueError("Every PDF page must provide selectable text")
    title = metadata.get("title") or "Making the Next Opportunity Possible"
    author = metadata.get("author") or "Vincent Boucher, President of MONTREAL.AI"
    edition_match = re.search(r"Research\s+edition\s+([0-9]+\.[0-9]+\.[0-9]+)", pages[0], re.IGNORECASE)
    edition = edition_match.group(1) if edition_match else None
    edition_label = f"English full text · Edition {edition}" if edition else "English reading edition"
    pdf_href = Path(os.path.relpath(pdf, output.resolve().parent)).as_posix()
    version = importlib.metadata.version("PyMuPDF")
    escape = html.escape
    page_records = [
        {"page": number, "characters": len(text), "sha256": hashlib.sha256(text.encode()).hexdigest()}
        for number, text in enumerate(pages, 1)
    ]
    navigation = "\n".join(
        f'<li><a href="#page-{number}" aria-label="Read PDF page {number}">{number}</a></li>'
        for number in range(1, len(pages) + 1)
    )
    sections = []
    for number, text in enumerate(pages, 1):
        links = ['<a href="#contents">Page navigation</a>']
        if number > 1:
            links.append(f'<a href="#page-{number - 1}">Previous page</a>')
        if number < len(pages):
            links.append(f'<a href="#page-{number + 1}">Next page</a>')
        sections.append(
            f'<article class="page" id="page-{number}" aria-labelledby="page-{number}-heading">'
            f'<header class="page-head"><h2 id="page-{number}-heading">PDF page {number} of {len(pages)}</h2>'
            f'<a href="{escape(pdf_href, quote=True)}#page={number}">View original PDF page {number}</a></header>'
            f'<pre class="page-text" data-page="{number}">{escape(text)}</pre>'
            f'<footer class="page-foot">{"".join(links)}</footer></article>'
        )
    markup = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="source-pdf-sha256" content="{digest}"><meta name="description" content="The complete English paper, extracted page by page from its frozen PDF. Local numerical evidence and conditional commercial simulation.">
<title>{escape(title)} — Full text</title><style>{STYLE}</style></head>
<body id="top"><a class="skip" href="#paper-text">Skip to the paper text</a>
<header class="hero"><div class="wrap"><div class="brand"><b>∞</b> AGI ALPHA FLYWHEEL</div>
<span class="eyebrow">{escape(edition_label)} · {len(pages)} PDF pages</span><h1>{escape(title)}</h1>
<p class="byline">{escape(author)}</p><div class="links"><a class="primary" href="{escape(pdf_href, quote=True)}">Read the original PDF</a><a href="index.html">English / French demonstration</a><a href="../evidence_companion.md">Evidence companion</a></div></div></header>
<main class="wrap"><div class="intro"><p>The complete text below is extracted directly from the accompanying PDF, page by page. It reads without JavaScript or an embedded PDF viewer.</p>
<p class="boundary"><strong>Research evidence boundary</strong>Local numerical experiments and explicitly conditional commercial simulation. The paper records its methods, failures and limitations.</p>
<p class="note">The PDF preserves the original visual layout, figures and mathematical notation. This text edition preserves the extraction output, including line breaks; equations and chart labels may read differently from their visual arrangement.</p>
<details><summary>Source identity and extraction</summary><p>Original PDF: {len(raw):,} bytes · {len(pages)} pages. Extractor: PyMuPDF {escape(version)}, page text in positional reading order. This edition introduces no translated or rewritten paper text.</p><span class="hash">PDF SHA-256: {digest}</span></details></div>
<nav class="contents" id="contents" aria-labelledby="contents-heading"><h2 id="contents-heading">Go to a PDF page</h2><ol>{navigation}</ol></nav>
<div id="paper-text">{"".join(sections)}</div></main>
<footer class="wrap"><p><a href="#top">Return to the title</a> · <a href="index.html">English / French demonstration</a> · <a href="{escape(pdf_href, quote=True)}">Original PDF</a></p><p>Source HTML research edition. Publication requires the repository's full qualification process.</p></footer></body></html>
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markup, encoding="utf-8")
    record = {
        "schema": "productive-frontier-pdf-reading-edition/v1",
        "source_pdf": pdf_href,
        "source_pdf_sha256": digest,
        "source_pdf_bytes": len(raw),
        "pages": len(pages),
        "edition": edition,
        "extractor": f"PyMuPDF {version}",
        "extraction": 'page.get_text("text", sort=True); all content escaped with html.escape',
        "javascript_required": False,
        "page_text": page_records,
        "html_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "qualification": "NEW_SOURCE_HTML_REQUIRES_FULL_QUALIFICATION; NOT_PASSIVE_PAPER_LANE",
    }
    (output.parent / "paper_reader_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--output", type=Path, default=HERE / "paper.html")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    result = build(args.pdf, args.output, args.expected_sha256)
    print(json.dumps({key: value for key, value in result.items() if key != "page_text"}, indent=2))
