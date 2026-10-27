# SPDX-License-Identifier: Apache-2.0
"""Build a standalone full-text browser edition from the paper's LaTeX body."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
body = (ROOT / "paper/body.tex").read_text()
body = body.replace("figures/conformance.pdf", "figures/conformance.png")
body = body.replace("figures/thresholds.pdf", "figures/thresholds.png")
body = body.replace("figures/cash-timing.pdf", "figures/cash-timing.png")
# Pandoc does not recognize this paper's tabularx/Y column definition. Normalize
# only the temporary reader input: cell content, captions and the PDF source stay exact.
expected_tables = body.count(r"\begin{tabularx}")
body, converted_tables = re.subn(
    r"\\begin\{tabularx\}\{\\textwidth\}\{([^\n]*)\}",
    lambda match: r"\begin{tabular}{" + match.group(1).replace("Y", "l") + "}",
    body,
)
if converted_tables != expected_tables:
    raise ValueError("Unrecognized tabularx declaration; refuse a reader with flattened tables")
body = body.replace(r"\end{tabularx}", r"\end{tabular}")
with tempfile.TemporaryDirectory(prefix="alpha-reader-") as directory:
    source = Path(directory) / "body.tex"
    source.write_text(body)
    subprocess.run([
        "pandoc", str(source), "--from=latex", "--to=html5", "--standalone",
        "--embed-resources", "--mathml", "--citeproc", "--toc", "--toc-depth=2",
        "--bibliography=" + str(ROOT / "paper/references.bib"),
        "--css=" + str(ROOT / "web/reader.css"),
        "--resource-path=" + str(ROOT / "paper"),
        "--metadata=title:AGI ALPHA FLYWHEEL — When Capability Creates Opportunity",
        "--metadata=subtitle:Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work",
        "--metadata=author:Vincent Boucher — President of MONTREAL.AI",
        "--metadata=date:Additive opportunity-discovery edition 1.0.0 · 27 October 2026",
        "--metadata=lang:en", "--metadata=link-citations:true", "--output=" + str(ROOT / "web/index.html"),
    ], check=True, cwd=ROOT / "paper")
path = ROOT / "web/index.html"
text = path.read_text()
note = '''<aside class="reader-note"><strong>FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.</strong>
This is the full research edition, with observed execution separated from assumed markets.
<a href="demo.html">Explore the English / French demonstration</a> ·
<a href="../paper/paper.pdf">Paper PDF</a> ·
<a href="../paper/executive-brief.pdf">Executive brief / Note de synthèse</a> ·
<a href="../paper/evidence-companion.pdf">Evidence companion</a>.
Source proposal only until the repository's authorized public-reader release is qualified.</aside>'''
text = text.replace("</header>", "</header>\n" + note, 1)
text = text.replace("</body>", '<footer class="page-footer">AI-assisted research, implementation, review, translation and drafting. '
                    'Observed customer revenue: zero. Complete actual cost and profit: unknown. '
                    'The original v1 result and subsequent prospective correction remain distinct. '
                    '<a href="https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850">Coordination and publication process</a>.'
                    '</footer></body>')
path.write_text(text)
print(f"Full-text reader built: {path.stat().st_size} bytes")
