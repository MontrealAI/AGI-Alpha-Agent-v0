# SPDX-License-Identifier: Apache-2.0
"""Build the concise brief from the same verified edition facts."""
from pathlib import Path
import subprocess
p=Path(__file__).resolve().parent
subprocess.run(['pandoc','executive_brief.md','--from=markdown+tex_math_dollars','--standalone','--to=latex','--include-in-header=style.tex','-o','AGI_ALPHA_Flywheel_Digital_R1_Brief.tex'],cwd=p,check=True)
f=p/'AGI_ALPHA_Flywheel_Digital_R1_Brief.tex';s=f.read_text();s=s.replace('\\begin{document}','\\begin{document}\n\\renewcommand{\\maketitle}{\\begin{center}{\\sffamily\\Large\\bfseries\\color{DeepPurple}AGI ALPHA FLYWHEEL\\par}\\vspace{4pt}{\\sffamily Executive brief | From a numerical failure to a verified digital answer\\par}\\vspace{5pt}{\\small Vincent Boucher --- President of MONTREAL.AI\\par 27 October 2026 | DIGITAL-20261027-R1}\\end{center}\\vspace{5pt}}');f.write_text(s)
for _ in range(2):
 r=subprocess.run(['xelatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error',f.name],cwd=p,capture_output=True,text=True)
 (p/'brief_build.log').write_text(r.stdout+r.stderr)
 if r.returncode:raise SystemExit(r.stdout[-4000:])
print('Built executive brief.')
