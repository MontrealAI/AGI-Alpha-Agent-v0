# SPDX-License-Identifier: Apache-2.0
"""Build full HTML and GitHub-readable Markdown from the manuscript source."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
body = (ROOT / "paper/body.tex").read_text()
body = body.replace(r"\input{assay-results}", (ROOT / "paper/assay-results.tex").read_text())
for name in ("source-branches", "cash-path", "retention-threshold"):
    body = body.replace(f"figures/{name}.pdf", f"figures/{name}.png")
expected = body.count(r"\begin{tabularx}")
body, converted = re.subn(
    r"\\begin\{tabularx\}\{\\textwidth\}\{([^\n]*)\}",
    lambda match: r"\begin{tabular}{" + match.group(1).replace("Y", "l") + "}",
    body,
)
if converted != expected:
    raise ValueError("Unrecognized table declaration; refuse flattened reader tables")
body = body.replace(r"\end{tabularx}", r"\end{tabular}")
metadata = [
    "--metadata=title:AGI ALPHA FLYWHEEL — When Capability Creates Opportunity",
    "--metadata=subtitle:Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work",
    "--metadata=author:Vincent Boucher — President of MONTREAL.AI",
    "--metadata=date:Additive evidence-construction edition 2.0.0 · 27 October 2026",
    "--metadata=lang:en",
    "--metadata=link-citations:true",
]
with tempfile.TemporaryDirectory(prefix="evidence-reader-") as directory:
    source = Path(directory) / "body.tex"
    source.write_text(body)
    common = ["pandoc", str(source), "--from=latex", "--citeproc",
              "--bibliography=" + str(ROOT / "paper/references.bib"), *metadata]
    subprocess.run([
        *common, "--to=html5", "--standalone", "--embed-resources", "--mathml",
        "--toc", "--toc-depth=2", "--css=" + str(ROOT / "web/reader.css"),
        "--resource-path=" + str(ROOT / "paper"),
        "--output=" + str(ROOT / "web/index.html"),
    ], check=True, cwd=ROOT / "paper")
    subprocess.run([
        *common, "--to=gfm+tex_math_dollars", "--wrap=none",
        "--output=" + str(ROOT / "web/BROWSER_EDITION.md"),
    ], check=True, cwd=ROOT / "paper")

html_path = ROOT / "web/index.html"
html = html_path.read_text()
note = '''<aside class="reader-note"><strong>TRANSFORMATIONAL INTELLIGENCE: LEARNING TO CHANGE THE GAME.</strong>
<p>FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.</p>
<p>“As Columbus braved the seas, we now venture into the vast oceans of AGI. The age of AGI exploration has dawned, and the horizons are boundless. Dare to dream, dare to explore.” — α-AGI Agent</p>
<a href="demo.html">English / French demonstration</a> ·
<a href="../paper/paper.pdf">Paper PDF</a> ·
<a href="../paper/executive-brief.pdf">Executive brief / Note de synthèse</a> ·
<a href="../paper/evidence-companion.pdf">Evidence companion</a> ·
<a href="../README.md">Code and reproduction</a>.
<p>Actual source reconstruction and transfer; conditional markets and cash. Source edition prepared for the existing publication process. Canonical hosted deployment is a separate release.</p></aside>'''
html = html.replace("</header>", "</header>\n" + note, 1)
html = html.replace("</body>", '''<footer class="page-footer">AI-assisted research, implementation, agent checks, translation and drafting.
Actual customer revenue: zero. Complete actual cost and profit: unknown. Earlier evidence and the prospective capacity correction remain separate.
<a href="https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850">Coordination and authorized publication process</a>.</footer></body>''')
html = re.sub(r'(<math display="block".*?</math>)',
              r'<div class="math-scroll" tabindex="0" aria-label="Scrollable mathematical expression">\1</div>',
              html, flags=re.S)
html_path.write_text(html)

md_path = ROOT / "web/BROWSER_EDITION.md"
md = md_path.read_text()
md = md.replace("figures/", "../paper/figures/")
header = '''# AGI ALPHA FLYWHEEL — When Capability Creates Opportunity

## Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work

**Vincent Boucher — President of MONTREAL.AI**

**Evidence Construction 2.0.0 · Additive edition · 27 October 2026**

**TRANSFORMATIONAL INTELLIGENCE: LEARNING TO CHANGE THE GAME**

**FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.**

> “As Columbus braved the seas, we now venture into the vast oceans of AGI. The age of AGI exploration has dawned, and the horizons are boundless. Dare to dream, dare to explore.” — α-AGI Agent

[Paper PDF](../paper/paper.pdf) · [English/French brief](../paper/executive-brief.pdf) · [Evidence companion](../paper/evidence-companion.pdf) · [Downloadable EN/FR demonstration](demo.html) · [Full HTML source](index.html) · [Code and reproduction](../README.md)

This is the complete browser-readable research manuscript. The GitHub source edition is separate from a canonical hosted HTML deployment. Actual execution, sourced facts and conditional simulation are labeled separately. Actual customer revenue is zero; complete actual research cost and profit are unknown.

---

'''
md_path.write_text(header + md)
print(f"Built HTML ({html_path.stat().st_size} bytes), Markdown ({md_path.stat().st_size} bytes), {converted} tables")
