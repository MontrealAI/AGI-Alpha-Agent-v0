# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
TITLE = "🌌♾️ AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
AUTHOR = "Vincent Boucher — President of MONTREAL.AI"
PUBLIC_BASE = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/research/flywheel-novelty-frontier-20261027/studies/agi-alpha-flywheel-novelty-frontier-v1"
PUBLIC_RAW = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/raw/refs/heads/research/flywheel-novelty-frontier-20261027/studies/agi-alpha-flywheel-novelty-frontier-v1"

CSS = """
:root{--purple:#301356;--violet:#8051c9;--ink:#241b30;--muted:#6c6276;--line:#e5dced}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f7f4fb;color:var(--ink);font:17px/1.7 Georgia,serif}
a{color:#673ba3;text-underline-offset:3px}header{position:relative;overflow:hidden;background:radial-gradient(ellipse at 85% 30%,#54238155,transparent 50%),#160b29;color:white;padding:64px max(6vw,24px) 60px}
.stars{position:absolute;inset:0;opacity:.4;background-image:radial-gradient(1px 1px at 7% 12%,#fff 90%,transparent),radial-gradient(1px 1px at 73% 24%,#fff 90%,transparent),radial-gradient(1px 1px at 43% 72%,#fff 90%,transparent);background-size:260px 190px;pointer-events:none}
header .inside{position:relative;max-width:1160px;margin:auto}.brand{font:700 12px/1.4 Arial,sans-serif;letter-spacing:.2em;color:#c9b1e8}
header h1{font:700 clamp(36px,5vw,64px)/1.1 Arial,sans-serif;letter-spacing:-.04em;max-width:950px;margin:28px 0 22px}
header h1 span{display:block;font-weight:400;font-size:.58em;letter-spacing:-.02em;margin-top:14px}
.subtitle{color:#d6c5eb;max-width:820px;font:18px/1.65 Arial,sans-serif}.author{font:600 15px/1.6 Arial,sans-serif;margin-top:26px}
.status{display:inline-block;border:1px solid #9b75ca66;padding:9px 14px;border-radius:30px;font:13px/1.5 Arial,sans-serif;color:#deceef;margin:20px 0 0}
.actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}.button{display:inline-block;padding:11px 18px;border-radius:7px;background:#b893eb;color:#170c29;text-decoration:none;font:700 14px/1.4 Arial,sans-serif}.secondary{background:transparent;color:#e8d9fa;border:1px solid #825ba7}
nav{background:#fff;border-bottom:1px solid var(--line);padding:12px 24px;font:13px/1.5 Arial,sans-serif;display:flex;gap:22px;justify-content:center;flex-wrap:wrap}
main{max-width:1080px;margin:0 auto;padding:50px 64px;background:white;box-shadow:0 8px 50px #30135608}
main h1{font:700 31px/1.25 Arial,sans-serif;color:var(--purple);margin:44px 0 18px}
h2{font:700 27px/1.3 Arial,sans-serif;color:var(--purple);margin:48px 0 18px;border-top:1px solid var(--line);padding-top:28px}
h3{font:700 20px/1.35 Arial,sans-serif;color:var(--purple);margin:30px 0 12px}h4{font:700 17px/1.4 Arial,sans-serif;color:var(--purple)}
p{margin:14px 0}blockquote{border-left:3px solid #9b75ca;margin:28px 0;padding:14px 22px;background:#f6f0fb}blockquote p{margin:7px 0}
table{border-collapse:collapse;width:100%;margin:24px 0;font:14px/1.55 Arial,sans-serif}th{text-align:left;background:#eee6f7;color:var(--purple);border-top:2px solid #8051c9}th,td{padding:12px 13px;vertical-align:top;border-bottom:1px solid #e5dced}tr:nth-child(even)td{background:#fbf9fd}
img{display:block;max-width:100%;height:auto;margin:30px auto 14px}code{font:13px/1.6 'DejaVu Sans Mono',monospace;background:#f4eff8;padding:2px 4px;overflow-wrap:anywhere}pre{background:#211530;color:#eadcf7;padding:20px;border-radius:8px;overflow:auto;font:13px/1.65 monospace}pre code{background:transparent;color:inherit;padding:0}
li{margin:6px 0}.toc{background:#faf7fd;padding:20px 28px;border:1px solid var(--line);font:14px/1.6 Arial,sans-serif}.toc ul{padding-left:20px}.toc>ul{margin:0}
math[display="block"]{overflow-x:auto;max-width:100%;display:block}main a{overflow-wrap:anywhere}.math.display{display:block;overflow-x:auto;max-width:100%}
footer{max-width:1080px;margin:auto;padding:35px 64px;color:var(--muted);font:13px/1.7 Arial,sans-serif}.math{overflow:auto}hr{border:0;border-top:1px solid var(--line);margin:34px 0}
@media(max-width:720px){main{padding:26px 20px}table{display:block;overflow:auto;font-size:12px}header{padding-top:38px}footer{padding:26px 20px}nav{justify-content:flex-start;gap:14px}h2{font-size:24px}}
@media print{header,nav,.actions,footer{display:none}main{padding:0;box-shadow:none}h2{break-after:avoid}table,img{break-inside:avoid}body{background:white}}
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def browser(source: str, output: Path) -> None:
    renderer = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"])
    body_source = source[source.index("## Abstract"):]
    quote = re.search(r"^> .+$", source, re.MULTILINE)
    if quote:
        body_source = quote.group(0) + "\n\n" + body_source
    renderer.convert(body_source)
    rendered = subprocess.run(
        ["pandoc", "--from=markdown+tex_math_dollars+tex_math_single_backslash-implicit_figures",
         "--to=html5", "--mathml"], input=body_source, capture_output=True, text=True, check=True
    )
    body = rendered.stdout
    toc_rows = []
    for level, target, label in re.findall(r'<h([23]) id="([^"]+)">(.*?)</h[23]>', body):
        toc_rows.append(f'<li style="margin-left:{"16px" if level == "3" else "0"}"><a href="#{target}">{label}</a></li>')
    toc = "<ul>" + "".join(toc_rows) + "</ul>"
    for image_path in (ROOT / "figures").glob("*.png"):
        uri = "data:image/png;base64," + base64.b64encode(image_path.read_bytes()).decode()
        body = body.replace("../figures/" + image_path.name, uri)
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="An executable AGI ALPHA discovery study: exact constructions, strong conventional controls, conditional economics and a preserved no-flagship verdict.">
<meta name="author" content="{html.escape(AUTHOR)}"><title>{html.escape(TITLE)}</title><style>{CSS}</style></head>
<body><header><div class="stars"></div><div class="inside"><div class="brand">MONTREAL.AI · RESEARCH EDITION 01</div>
<h1>AGI ALPHA FLYWHEEL<span>When Capability Creates Opportunity</span></h1>
<p class="subtitle">Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work</p>
<p class="author">{html.escape(AUTHOR)}</p><div class="status">Executed exploratory study · No flagship selected · 27 October 2026</div>
<div class="actions"><a class="button" href="{PUBLIC_RAW}/paper/AGI_ALPHA_FLYWHEEL.pdf">Download the paper</a><a class="button secondary" href="{PUBLIC_BASE}/paper/EXECUTIVE_BRIEF.md">Executive brief</a><a class="button secondary" href="{PUBLIC_BASE}/README.md">Reproduce the study</a></div></div></header>
<nav><a href="#abstract">Abstract</a><a href="#reader-contents">Contents</a><a href="{PUBLIC_BASE}/discovery/order-memory/discovery_record.json">Discovery record</a><a href="{PUBLIC_BASE}/results/economics-results.json">Economic results</a></nav>
<main><details class="toc" id="reader-contents"><summary>Explore the paper</summary>{toc}</details>{body}</main>
<footer>Source-draft research edition. Finite computations and scenario economics retain their stated scope.
Cryptographic provenance does not establish novelty, physical performance, customer acceptance or authority.
The canonical software release and Pages publication remain under the repository's existing process.</footer></body></html>"""
    output.write_text(document, encoding="utf-8")


def pdf(source: str) -> dict[str, object]:
    paper = ROOT / "paper"
    lines = source.splitlines()
    while lines and not lines[0].startswith("## "):
        lines.pop(0)
    cleaned = "\n".join(lines) + "\n"
    quote = re.search(r"^> .+$", source, re.MULTILINE)
    if quote:
        cleaned = quote.group(0) + "\n\n" + cleaned
    cleaned = cleaned.replace("🌌♾️ ", "").replace("🌌", "").replace("♾️", r"$\infty$")
    cleaned = re.sub(r"(!\[[^\]]*\]\(\.\./figures/[^)]+)\.png(\))", r"\1.pdf\2", cleaned)
    temporary = paper / "PDF_BODY.md"
    temporary.write_text(cleaned, encoding="utf-8")
    command = [
        "pandoc", str(temporary), "--from=markdown+tex_math_dollars+tex_math_single_backslash-implicit_figures", "--to=latex", "--standalone",
        "--top-level-division=section", "--shift-heading-level-by=-1",
        "--variable=documentclass:article", "--variable=fontsize:11pt",
        "--variable=geometry:letterpaper,margin=0.78in", "--variable=colorlinks:true",
        "--include-in-header=" + str(paper / "style.tex"),
        "--include-before-body=" + str(paper / "cover.tex"),
        "--resource-path=" + str(paper) + ":" + str(ROOT),
        "--output=" + str(paper / "AGI_ALPHA_FLYWHEEL.tex"),
    ]
    result = subprocess.run(command, cwd=paper, capture_output=True, text=True)
    (paper / "pandoc-build.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    result.check_returncode()
    tex_path = paper / "AGI_ALPHA_FLYWHEEL.tex"
    latex = tex_path.read_text()
    latex = latex.replace(r"\begin{longtable}", "\\begingroup\\small\n" + r"\begin{longtable}")
    latex = latex.replace(r"\end{longtable}", r"\end{longtable}" + "\n\\endgroup")
    def break_code(match: re.Match[str]) -> str:
        raw = match.group(1).replace(r"\_", "_")
        if "/" in raw or re.fullmatch(r"[0-9a-f]{40,64}", raw):
            return r"\nolinkurl{" + raw + "}"
        return match.group(0)
    latex = re.sub(r"\\texttt\{([^{}]+)\}", break_code, latex)
    def space_table(match: re.Match[str]) -> str:
        table = match.group(0)
        markers = {"Development estimate": 165, "Confirmation scenario": 160,
                   "Favorable-case account": 350, "Exact model": 180,
                   "Reproduction entry point": 180, "Link in the example": 250}
        for marker, points in markers.items():
            if marker in re.sub(r"\s+", " ", table):
                return "\\Needspace{" + str(points) + "pt}\n" + table
        return table
    latex = re.sub(r"\\begingroup\\small\n\\begin\{longtable\}.*?\\end\{longtable\}\n\\endgroup", space_table, latex, flags=re.S)
    latex = latex.replace(r"\section{References and source scope}", r"\section{References and source scope}" + "\n\\small")
    latex = latex.replace(r"\hypertarget{references-and-source-scope}", "\\small\n" + r"\hypertarget{references-and-source-scope}")
    tex_path.write_text(latex)
    for run in [1, 2]:
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape",
             "AGI_ALPHA_FLYWHEEL.tex"], cwd=paper, capture_output=True, text=True
        )
        (paper / f"xelatex-build-{run}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        result.check_returncode()
    return {"pandoc": subprocess.check_output(["pandoc", "--version"], text=True).splitlines()[0],
            "xelatex": subprocess.check_output(["xelatex", "--version"], text=True).splitlines()[0],
            "pdf_sha256": digest(paper / "AGI_ALPHA_FLYWHEEL.pdf")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()
    path = ROOT / "paper/PAPER.md"
    source = path.read_text(encoding="utf-8")
    if TITLE not in source or AUTHOR not in source:
        raise ValueError("The exact requested title and author line must be present")
    browser(source, ROOT / "paper/Browser_Edition.html")
    receipt = ROOT / "results/publication-build.json"
    report: dict[str, object] = json.loads(receipt.read_text()) if args.html_only and receipt.exists() else {}
    report.update({"manuscript_sha256": digest(path), "html_sha256": digest(ROOT / "paper/Browser_Edition.html")})
    if not args.html_only:
        report.update(pdf(source))
        report["pdf_manuscript_sha256"] = digest(path)
    (ROOT / "results/publication-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
