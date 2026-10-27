# SPDX-License-Identifier: Apache-2.0
"""Build the complete source/evidence companion as a readable linked PDF."""
from __future__ import annotations

import subprocess
import re
from pathlib import Path

PAPER=Path(__file__).resolve().parent


def main():
    source=(PAPER/"evidence_companion.md").read_text()
    # The PDF title block replaces only the duplicate Markdown H1, not its content.
    body="\n".join(source.splitlines()[1:]).lstrip()
    command=["pandoc","--from=gfm","--to=latex","--standalone","--shift-heading-level-by=-1",
       "--pdf-engine=xelatex","--variable=documentclass:article","--variable=fontsize:10pt",
       "--variable=geometry:margin=22mm","--variable=mainfont:DejaVu Serif",
       "--variable=mainfontoptions:AutoFakeSlant=0.2",
       "--variable=sansfont:DejaVu Sans","--variable=monofont:DejaVu Sans Mono",
       "--variable=colorlinks:true","--variable=linkcolor:RoyalPurple","--variable=urlcolor:RoyalPurple",
       "--include-in-header="+str(PAPER/"companion_header.tex"),
       "--metadata=title:Evidence Companion",
       "--metadata=subtitle:Paid Work. Retained Alpha. Expanding Possibility.",
       "--metadata=author:AGI ALPHA FLYWHEEL research companion",
       "--metadata=date:Evidence checked 26 October 2026",
       "--output="+str(PAPER/"evidence_companion.tex")]
    p=subprocess.run(command,input=body,text=True,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr)
    tex=PAPER/"evidence_companion.tex"
    rendered=tex.read_text()
    # GFM stores no width hints. Replace natural-width text tables with
    # paragraph columns so the complete source register stays on the page.
    rendered=rendered.replace(r"\begin{longtable}[]{@{}lll@{}}",r"\begin{longtable}[]{@{}>{\raggedright\arraybackslash}p{.22\linewidth}>{\raggedright\arraybackslash}p{.37\linewidth}>{\raggedright\arraybackslash}p{.35\linewidth}@{}}")
    rendered=rendered.replace(r"\begin{longtable}[]{@{}lrr@{}}",r"\begin{longtable}[]{@{}>{\raggedright\arraybackslash}p{.50\linewidth}>{\raggedleft\arraybackslash}p{.19\linewidth}>{\raggedleft\arraybackslash}p{.25\linewidth}@{}}")
    def breakable_code(match):
        value=match.group(1).replace(r"\_","_")
        return r"\nolinkurl{"+value+"}" if len(value)>26 else match.group(0)
    rendered=re.sub(r"\\texttt\{([^{}]*)\}",breakable_code,rendered)
    tex.write_text("% SPDX-License-Identifier: Apache-2.0\n"+rendered)
    for iteration in (1,2,3):
        p=subprocess.run(["xelatex","-interaction=nonstopmode","-halt-on-error","evidence_companion.tex"],cwd=PAPER,text=True,capture_output=True)
        (PAPER/f"companion-pass-{iteration}.log").write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(p.stdout[-6000:])
    print(PAPER/"evidence_companion.pdf")


if __name__=="__main__":main()
