# SPDX-License-Identifier: Apache-2.0
"""Produce the full Markdown reader and a self-contained HTML edition from LaTeX."""

from __future__ import annotations
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TITLE = "AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
SUBTITLE = "Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work"
AUTHOR = "Vincent Boucher — President of MONTREAL.AI"


def expand(text: str) -> str:
    def include(match: re.Match[str]) -> str:
        path = (HERE / match.group(1)).resolve()
        if path.suffix != ".tex":
            path = path.with_suffix(".tex")
        if not path.is_relative_to(HERE):
            raise ValueError("input outside paper directory")
        return expand(path.read_text())

    return re.sub(r"\\input\{([^}]+)\}", include, text)


def main() -> None:
    full = expand((HERE / "paper.tex").read_text())
    bibliography = full.split(r"\begin{thebibliography}{99}", 1)[1].split(r"\end{thebibliography}", 1)[0]
    entries = re.findall(r"\\bibitem\{([^}]+)\}([\s\S]*?)(?=\\bibitem|\Z)", bibliography)
    targets = {}
    for key, content in entries:
        urls = re.findall(r"\\url\{([^}]+)\}", content)
        targets[key] = urls[0] if urls else "../opportunity/discovery/foundations/synthesis.md"
    body = full[full.index(r"\section*{Abstract}") : full.index(r"\begin{thebibliography}")]
    body = re.sub(
        r"\\cite\{([^}]+)\}",
        lambda m: " ".join(r"\href{" + targets[k] + "}{[" + k + "]}" for k in m.group(1).split(",")),
        body,
    )
    body = re.sub(r"(\\includegraphics(?:\[[^\]]*\])?\{[^}]+)\.pdf\}", r"\1.png}", body)
    references = r"\section*{References}" + "\n" + r"\begin{enumerate}" + "\n"
    for key, content in entries:
        references += r"\item " + r"\textbf{" + key + "}. " + content.strip() + "\n"
    references += r"\end{enumerate}"
    prefix = full[: full.index(r"\begin{document}")]
    temporary = HERE / "reader_expanded.tex"
    temporary.write_text(prefix + r"\begin{document}" + "\n" + body + references + "\n" + r"\end{document}" + "\n")
    result = subprocess.run(
        ["pandoc", "reader_expanded.tex", "-f", "latex", "-t", "gfm+tex_math_dollars", "--wrap=none"],
        cwd=HERE,
        capture_output=True,
        text=True,
        check=True,
    )
    masthead = (
        f"# {TITLE}\n\n## {SUBTITLE}\n\n**{AUTHOR}**\n\n"
        "**FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.**\n\n"
        "> “As Columbus braved the seas, we now venture into the vast oceans of AGI. The age of AGI exploration has dawned, and the horizons are boundless. Dare to dream, dare to explore.” — α-AGI Agent\n\n"
        "**Additive research edition 2.1.0 · 27 October 2026.** This is the complete narrative of the LaTeX paper, with the same evidence and limitations. Prior papers, corrections and study records remain preserved.\n\n"
        "[Paper PDF](paper.pdf) · [Executive brief](executive_brief.pdf) · [Evidence companion](evidence_companion.pdf) · [English/French demonstration](../browser/index.html) · [Reproduction guide](../REPRODUCTION_ALL.md)\n\n"
        "**Result:** U, E, E+ and a conventional construction each pass all four scientific mission requirements. The received instrument works within scope; no incremental accepted-output advantage or positive complete-cost commercial crossing is established. Actual collections are $0; complete actual cost and profit are unknown.\n\n---\n\n"
    )
    converted = re.sub(r"^(#{1,5}) ", lambda m: m.group(1) + "# ", result.stdout, flags=re.M)
    converted = re.sub(r"^\|(?:\s*\|)+\s*$\n?", "", converted, flags=re.M)

    def accessible_figure(match: re.Match[str]) -> str:
        opening, caption, closing = match.group(1), match.group(2), match.group(3)
        plain = re.sub(r"<[^>]+>", "", caption)
        return opening.replace(" />", ' alt="' + html.escape(plain, quote=True) + '" />') + caption + closing

    converted = re.sub(
        r"(<figure>\s*<img[^>]+/>\s*<figcaption>)(.*?)(</figcaption>\s*</figure>)",
        accessible_figure,
        converted,
        flags=re.S,
    )
    reader = masthead + converted
    (HERE / "Browser_Edition.md").write_text(reader)
    css = """html{color-scheme:light}#title-block-header{display:none}body{overflow-wrap:anywhere;max-width:960px;margin:0 auto;padding:3rem 1.5rem;font:18px/1.65 Georgia,serif;color:#263442;background:#fbfcfd}h1,h2,h3,h4{font-family:Arial,sans-serif;color:#153d59;line-height:1.25}h1{font-size:2.3rem;border-bottom:3px solid #ad7e32;padding-bottom:.7rem}h2{margin-top:2.2rem;font-size:1.65rem}h3{font-size:1.2rem}a{color:#087f8c;overflow-wrap:anywhere}p{margin:.9rem 0}blockquote{border-left:4px solid #ad7e32;padding:.5rem 1rem;margin:1.4rem 0;background:#f4f1e9}table{overflow-wrap:normal;border-collapse:collapse;font:14px/1.5 Arial,sans-serif;width:100%;margin:1.5rem 0;display:block;overflow-x:auto}th,td{padding:.65rem;border-bottom:1px solid #ccd6dc;text-align:left;vertical-align:top}th{background:#edf3f6}img{max-width:100%;height:auto}figure{margin:1.5rem 0}figcaption,caption{font:14px/1.5 Arial,sans-serif;color:#52626e;margin:.6rem 0}pre{overflow-x:auto;padding:1rem;background:#eef3f6}code{font-size:.86em;overflow-wrap:anywhere}math[display=block]{overflow-x:auto;margin:1.5rem 0}#TOC{font:15px/1.5 Arial,sans-serif;background:#edf3f6;padding:1rem 1.5rem;border-radius:8px}#TOC ul{padding-left:1.2rem}@media(max-width:600px){body{font-size:17px;padding:1.3rem 1rem}h1{font-size:1.7rem}h2{font-size:1.4rem}table{font-size:12px}}@media print{body{max-width:none;padding:0;font-size:11pt}a{color:inherit}#TOC{break-after:page}h2,h3{break-after:avoid}figure,table{break-inside:avoid}}"""
    (HERE / "reader.css").write_text(css)
    html_result = subprocess.run(
        [
            "pandoc",
            "Browser_Edition.md",
            "-f",
            "gfm+tex_math_dollars",
            "-t",
            "html5",
            "--standalone",
            "--embed-resources",
            "--mathml",
            "--toc",
            "--toc-depth=2",
            "--css=reader.css",
            "--metadata",
            "title=" + TITLE,
            "--metadata",
            "lang=en",
            "-o",
            "Browser_Edition.html",
        ],
        cwd=HERE,
        check=True,
        capture_output=True,
    )
    if b"Could not convert TeX math" in html_result.stderr:
        raise RuntimeError(html_result.stderr.decode())
    files = ["paper.tex", "Browser_Edition.md", "Browser_Edition.html", "reader.css"]
    receipt: dict[str, Any] = {
        "edition": "2.1.0",
        "source": "complete LaTeX narrative expanded before conversion",
        "external_resources_required": False,
        "files": {
            n: {"sha256": hashlib.sha256((HERE / n).read_bytes()).hexdigest(), "bytes": (HERE / n).stat().st_size}
            for n in files
        },
        "citation_targets": targets,
        "pandoc_warnings": result.stderr.strip(),
        "html_warnings": html_result.stderr.decode().strip(),
    }
    (HERE / "reader_build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({n: receipt["files"][n]["bytes"] for n in files}, indent=2))


if __name__ == "__main__":
    main()
