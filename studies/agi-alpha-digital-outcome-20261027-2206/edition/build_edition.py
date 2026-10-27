# SPDX-License-Identifier: Apache-2.0
"""Build synchronized LaTeX, PDF, and self-contained browser editions."""
from pathlib import Path
import subprocess,re,json,hashlib
P=Path(__file__).resolve().parent
source=(P/'manuscript.md').read_text()
assert '@@' not in source, 'Resolve economic sections before building final edition.'
# For HTML, use the same prose and SVG figure sources; omit explicit print page breaks.
html=source.replace('\\editionbreak','\n---\n').replace('\\clearpage','\n---\n').replace('figures/construction_time.pdf','figures/construction_time.svg').replace('figures/fresh_confirmation.pdf','figures/fresh_confirmation.svg').replace('figures/economics.pdf','figures/economics.svg')
html=html.replace("subtitle: 'From a numerical failure to a verified digital answer'", "subtitle: 'From a numerical failure to a verified digital answer · Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work'")
(P/'browser_source.md').write_text(html)
# Bibliography is rendered by citeproc into both outputs. TeX remains independently compilable.
common=['--from=markdown+tex_math_dollars','--citeproc','--bibliography=references.bib','--standalone']
subprocess.run(['pandoc','manuscript.md',*common,'--to=latex','--include-in-header=style.tex','--include-before-body=cover.tex','--metadata=title:','--metadata=author:','--metadata=date:','-o','AGI_ALPHA_Flywheel_Digital_R1.tex'],cwd=P,check=True)
tex=(P/'AGI_ALPHA_Flywheel_Digital_R1.tex').read_text().replace('\\usepackage[margin=1in]{geometry}','')
# Pandoc's default title is suppressed by blank metadata; cover owns title and authorship.
(P/'AGI_ALPHA_Flywheel_Digital_R1.tex').write_text(tex)
for _ in range(2):
 r=subprocess.run(['xelatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','AGI_ALPHA_Flywheel_Digital_R1.tex'],cwd=P,capture_output=True,text=True)
 (P/'latex_build.log').write_text(r.stdout+r.stderr)
 if r.returncode:raise SystemExit(r.stdout[-5000:])
subprocess.run(['pandoc','browser_source.md',*common,'--to=html5','--toc','--toc-depth=1','--css=edition.css','--self-contained','--mathml','-o','AGI_ALPHA_Flywheel_Digital_R1.html'],cwd=P,check=True)
subprocess.run(['pandoc','browser_source.md','--from=markdown+tex_math_dollars','--to=gfm','--citeproc','--bibliography=references.bib','-o','browser_reading.md'],cwd=P,check=True)
f=P/'browser_reading.md'; f.write_text('# AGI ALPHA FLYWHEEL — When Capability Creates Opportunity\n\n## From a numerical failure to a verified digital answer\n\n*Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work*\n\n**Vincent Boucher — President of MONTREAL.AI**\n\n27 October 2026 · DIGITAL-20261027-R1 · Research review edition\n\n'+f.read_text())
print('Built synchronized LaTeX/PDF/HTML/GitHub reading editions.')
