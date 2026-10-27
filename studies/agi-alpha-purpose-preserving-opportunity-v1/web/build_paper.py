#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Render the complete manuscript with Pandoc; preserve source text and references."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

WEB = Path(__file__).resolve().parent
PAPER = WEB.parent / "paper"
TITLE = "AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
SUBTITLE = "Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work"
AUTHOR = "Vincent Boucher — President of MONTREAL.AI"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert() -> None:
    source = (PAPER / "agi-alpha-flywheel.tex").read_text()
    bibliography = (PAPER / "references.tex").read_text()
    refs = re.findall(r"\\bibitem\{([^}]+)\}\s*(.*?)(?=\\bibitem\{|\\end\{thebibliography\})", bibliography, flags=re.S)
    assert len(refs) == 22, "Bibliography changed: review the conversion contract."
    numbers = {key: i + 1 for i, (key, _) in enumerate(refs)}
    macros = "\n".join(
        [
            r"\newcommand{\editiontitle}{" + TITLE + "}",
            r"\newcommand{\editionsubtitle}{" + SUBTITLE + "}",
            r"\newcommand{\editionauthor}{" + AUTHOR + "}",
            r"\newcommand{\evidence}[1]{\textbf{[#1]}}",
            r"\newcommand{\file}[1]{\texttt{#1}}",
        ]
    )
    text = source.replace(r"\usepackage{edition}", macros)
    text = text.replace(r"\hfill — $\alpha$-AGI Agent", r"\hfill — $\alpha$-AGI Agent\par")
    reference_text = r"\section*{References}" + "\n\n"
    for key, content in refs:
        reference_text += (
            r"\hypertarget{ref-" + key + r"}{\textbf{[" + str(numbers[key]) + "]} " + content.strip() + "}\n\n"
        )
    text = text.replace(r"\input{references.tex}", reference_text)
    text = re.sub(
        r"\\cite\{([^}]+)\}",
        lambda m: " ".join(r"\href{\#ref-" + key + "}{[" + str(numbers[key]) + "]}" for key in m.group(1).split(",")),
        text,
    )
    text = text.replace(r"\ref{tab:candidates}", r"\href{\#tab:candidates}{1}")
    text = re.sub(
        r"\\begin\{(finding|boundary)\}(?:\[title=([^\]]*)\])?",
        lambda m: r"\begin{quote}" + ("\n" + r"\textbf{" + m.group(2) + "}\n\n" if m.group(2) else "\n"),
        text,
    )
    text = text.replace(r"\end{finding}", r"\end{quote}").replace(r"\end{boundary}", r"\end{quote}")
    # Pandoc does not know the edition's custom Y column. Map these six exact
    # presentation declarations to ordinary left-aligned cells; content is intact.
    columns = {
        r"\begin{tabularx}{\textwidth}{@{}lY Y@{}}": r"\begin{tabular}{lll}",
        r"\begin{tabularx}{\textwidth}{@{}p{27mm}Y Y@{}}": r"\begin{tabular}{lll}",
        r"\begin{tabularx}{\textwidth}{@{}p{35mm}Y@{}}": r"\begin{tabular}{ll}",
        r"\begin{tabularx}{\textwidth}{@{}p{41mm}Y@{}}": r"\begin{tabular}{ll}",
        r"\begin{tabularx}{\textwidth}{@{}p{14mm}Y Y@{}}": r"\begin{tabular}{lll}",
        r"\begin{tabularx}{\textwidth}{@{}lYYY@{}}": r"\begin{tabular}{llll}",
    }
    for old, new in columns.items():
        assert old in text, old
        text = text.replace(old, new)
    text = text.replace(r"\end{tabularx}", r"\end{tabular}")
    text = re.sub(r"\{figures/([^}]+)\.pdf\}", r"{../paper/figures/\1.svg}", text)
    text = text.replace(r"\tableofcontents", "")
    ast_run = subprocess.run(
        ["pandoc", "--from=latex", "--to=json"], input=text, text=True, capture_output=True, check=True
    )
    ast: Any = json.loads(ast_run.stdout)
    counts: dict[str, int] = {}
    raw_nodes: list[Any] = []

    def inspect(node: Any) -> None:
        if isinstance(node, dict):
            kind = node.get("t")
            if kind:
                counts[kind] = counts.get(kind, 0) + 1
                if kind in {"RawBlock", "RawInline"}:
                    raw_nodes.append(node)
            for child in node.values():
                inspect(child)
        elif isinstance(node, list):
            for child in node:
                inspect(child)

    inspect(ast)
    assert counts.get("Table") == 7, counts
    assert counts.get("Figure") == 4, counts
    assert counts.get("Header") == 36, counts
    assert not raw_nodes, raw_nodes
    command = [
        "pandoc",
        "--from=json",
        "--to=html5",
        "--standalone",
        "--mathml",
        "--toc",
        "--toc-depth=2",
        "--shift-heading-level-by=1",
        "--template=" + str(WEB / "paper-template.html"),
        "--metadata=title:" + TITLE,
        "--metadata=lang:en",
    ]
    html_run = subprocess.run(command, input=ast_run.stdout, text=True, capture_output=True, check=True)
    soup = BeautifulSoup(html_run.stdout, "html.parser")
    titlepage = soup.select_one(".titlepage")
    assert isinstance(titlepage, Tag)
    title = titlepage.find_all("p", recursive=False)[1]
    title.name = "h1"
    title["id"] = "paper-title"
    title["class"] = ["paper-title"]
    for table in list(soup.find_all("table")):
        wrapper = soup.new_tag(
            "div",
            attrs={
                "class": "table-scroll",
                "tabindex": "0",
                "role": "region",
                "aria-label": "Manuscript data table; scroll horizontally on small screens",
            },
        )
        table.wrap(wrapper)
    for equation in list(soup.find_all("math", attrs={"display": "block"})):
        equation.wrap(
            soup.new_tag(
                "span",
                attrs={
                    "class": "math-scroll",
                    "tabindex": "0",
                    "role": "region",
                    "aria-label": "Display equation; scroll horizontally on small screens",
                },
            )
        )
    all_refs = [soup.find(id="ref-" + key) for key, _ in refs]
    assert all(all_refs), "Lost reference anchor."
    assert len(soup.find_all("table")) == 7
    assert len(soup.find_all("figure")) == 4
    for figure in soup.find_all("figure"):
        image = figure.find("img")
        caption = figure.find("figcaption")
        assert isinstance(image, Tag) and isinstance(caption, Tag)
        image["alt"] = caption.get_text(" ", strip=True)
    result = str(soup)
    result = result.replace("__PAPER_CSS__", (WEB / "paper.css").read_text())
    (WEB / "paper.html").write_text(result)
    record = {
        "schema": "agialpha.browser-manuscript.v1",
        "sources": {f: digest(PAPER / f) for f in ["agi-alpha-flywheel.tex", "references.tex"]},
        "converter": subprocess.check_output(["pandoc", "--version"], text=True).splitlines()[0],
        "source_sections": len(re.findall(r"\\section\*?\{", source)),
        "source_subsections": len(re.findall(r"\\subsection\*?\{", source)),
        "rendered_heading_count_excluding_title": counts["Header"],
        "table_count": 7,
        "figure_count": 4,
        "references": [key for key, _ in refs],
        "reference_count": len(refs),
        "math_count": counts.get("Math", 0),
        "raw_unconverted_nodes": raw_nodes,
        "figure_files": [str(x.get("src")) for x in soup.select("figure img")],
        "mapping": "Custom title/evidence/file macros expanded; finding/boundary callouts mapped to blockquotes; six custom Y-column layouts mapped to ordinary tabular; citations preserve original22-item order with linked numeric references; PDF figures replaced by existing SVG siblings. No manuscript text summarized.",
        "output_sha256": digest(WEB / "paper.html"),
        "warnings": [ast_run.stderr, html_run.stderr],
    }
    (WEB / "qa" / "paper-conversion.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k not in {"references", "sources", "mapping"}}, indent=2))


if __name__ == "__main__":
    convert()
