# SPDX-License-Identifier: Apache-2.0
"""Build the complete offline HTML and editable LaTeX/PDF editions."""
from pathlib import Path
import base64
import html
import json
import re
import subprocess
import argparse

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
EDITORIAL=json.loads((HERE/"editorial.json").read_text())


def pandoc(text, target):
    return subprocess.run(["pandoc","--from=markdown","--to="+target,"--wrap=none",
                          "--lua-filter="+str(HERE/"inline-code.lua")],
        input=text,capture_output=True,text=True,check=True).stdout


def content(brief=False):
    raw=(HERE/("EXECUTIVE_BRIEF.md" if brief else "PAPER.md")).read_text()
    return raw[raw.index("## Decision" if brief else "## Executive finding"):]


def cover(brief=False):
    if brief:
        return r"""\thispagestyle{empty}
{\sffamily\color{AlphaPurple}\small\bfseries AGI ALPHA FLYWHEEL\hfill EXECUTIVE BRIEF\par}
\vspace{13pt}
{\sffamily\color{AlphaInk}\fontsize{27}{31}\selectfont\bfseries When Capability\\Creates Opportunity\par}
\vspace{10pt}
{\sffamily\small\bfseries Vincent Boucher — President of MONTREAL.AI\par}
{\sffamily\small\color{AlphaMuted}27 October 2026 · Portable production study · Edition 01\par}
\vspace{9pt}\textcolor{AlphaPurple}{\rule{\linewidth}{1pt}}
"""
    return r"""\begin{titlepage}
\thispagestyle{empty}
\begin{tikzpicture}[remember picture,overlay]
\fill[AlphaInk] (current page.south west) rectangle (current page.north east);
\draw[AlphaPurple,line width=25pt,opacity=.45] ([xshift=2cm,yshift=-3cm]current page.north east) circle (7.7cm);
\draw[AlphaViolet,line width=.6pt,opacity=.45] ([xshift=2cm,yshift=-3cm]current page.north east) circle (6.7cm);
\draw[AlphaViolet,line width=.5pt,opacity=.25] ([xshift=2cm,yshift=-3cm]current page.north east) circle (8.7cm);
\draw[AlphaViolet,line width=.4pt,opacity=.18] ([xshift=2cm,yshift=-3cm]current page.north east) circle (10.7cm);
\end{tikzpicture}
\color{white}\sffamily
\vspace*{.1in}
{\small\bfseries\color{AlphaViolet}MONTREAL.AI\quad /\quad RESEARCH EDITION 01\par}
\vspace{.78in}
{\fontsize{36}{39}\selectfont\bfseries AGI ALPHA\\FLYWHEEL\par}
\vspace{.25in}
{\fontsize{26}{31}\selectfont When Capability\\Creates Opportunity\par}
\vspace{.42in}
{\fontsize{13}{20}\selectfont\color{AlphaViolet}Transformational Intelligence, Experience-Trained\\Specialists and the Expanding Frontier\\of Profitable Work\par}
\vspace{.55in}
{\large\bfseries Vincent Boucher\par}
{\normalsize President of MONTREAL.AI\par}
\vfill
\textcolor{AlphaViolet}{\rule{\linewidth}{.6pt}}\par
\vspace{10pt}
{\small\bfseries A CONSTRUCTED ARTIFACT. A STOPPED FLAGSHIP.\par}
\vspace{5pt}
{\small Six nominal solids, preserved failures and a complete conditional\\decision model. No accepted commercial production capability is claimed.\par}
\vspace{17pt}
{\footnotesize\color{AlphaViolet}27 October 2026\hfill FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.\par}
\vspace{.1in}
\end{titlepage}
"""


def latex(brief=False):
    raw=content(brief)
    # Markdown level two is the principal manuscript heading, not a subsection.
    raw=re.sub(r"(?m)^(#{2,4}) ",lambda m:m.group(1)[1:]+" ",raw)
    raw=raw.replace(".png)",".pdf)")
    body=pandoc(raw,"latex")
    body=body.replace("\\\\\n\\end{longtable}","\\\\*\n\\end{longtable}")
    # Avoid floating a figure far away from its evidentiary context.
    body=body.replace(r"\begin{figure}",r"\begin{figure}[!htbp]")
    toc="" if brief else r"""\setcounter{page}{1}
{\sffamily\color{AlphaPurple}\large\bfseries READING GUIDE\par}
\vspace{8pt}
\colorbox{AlphaPale}{\parbox{\dimexpr\linewidth-2\fboxsep}{\vspace{8pt}\small\sffamily
\textbf{Research status: no transformational flagship admitted.} This edition reports an executed supporting nominal-CAD artifact and conditional economics. It supplies no customer acceptance, sale, physical qualification or measured Alpha.\vspace{8pt}}}
{\sffamily\small\setstretch{1.15}\tableofcontents}
\vfill
{\small\sffamily\color{AlphaMuted}The complete browser edition includes the full manuscript and a local economic-scenario explorer. Code, inputs, failures and exact results accompany this paper.}\par
\newpage
"""
    template=(HERE/"paper-template.tex").read_text()
    if brief:
        template=template.replace("[11pt,letterpaper]","[10pt,letterpaper]")
        template=template.replace(r"\setstretch{1.13}",r"\setstretch{1.04}")
        template=template.replace(r"\setlength{\parskip}{7pt plus 1pt minus 1pt}",r"\setlength{\parskip}{5pt plus 1pt minus 1pt}")
        template=template.replace(r"\titlespacing*{\section}{0pt}{23pt}{10pt}",r"\titlespacing*{\section}{0pt}{17pt}{7pt}")
        body=body.replace(r"\begin{longtable}",r"\Needspace{170pt}"+"\n"+r"\begin{longtable}")
    text=template.replace("@@COVER@@",cover(brief)).replace("@@CONTENTS@@",toc).replace("@@BODY@@",body)
    name="AGI_ALPHA_Executive_Brief" if brief else "AGI_ALPHA_FLYWHEEL"
    (HERE/(name+".tex")).write_text(text)
    for _ in range(3):
        p=subprocess.run(["xelatex","-interaction=nonstopmode","-halt-on-error",name+".tex"],cwd=HERE,capture_output=True,text=True)
        if p.returncode:
            raise RuntimeError(p.stdout[-10000:]+p.stderr[-2000:])
    return name+".pdf"


def economic_explorer():
    data=json.loads((ROOT/"economics/results-r1/results.json").read_text())
    scenarios=list(dict.fromkeys(r["scenario"] for r in data["sensitivity"]))
    labels=["Public-source zero-value control","Adverse custom-work assumptions","Central custom-work assumptions","Favorable custom-work assumptions"]
    options="".join(f'<option value="{s}"'+(' selected' if i==2 else '')+f'>{labels[i]}</option>' for i,s in enumerate(scenarios))
    records=[{k:r[k] for k in ["scenario","price_cents","capital_cents","expected","prospective_loss_probability","finance_refusal_probability"]} for r in data["sensitivity"]]
    block='''<section class="explorer" aria-labelledby="explorer-title"><h3 id="explorer-title">Inspect the conditional decision model</h3>
<p>Selective continuation with shared preparation. Each selection reads one exact precomputed scenario; changing controls does not create evidence of demand. The proposed and conventional shared providers receive identical capabilities.</p>
<div class="controls"><label>Assumption set<select id="scenario">'''+options+'''</select></label>
<label>Accepted fee (USD)<select id="price"><option value="90000">900</option><option value="120000" selected>1,200</option><option value="150000">1,500</option></select></label>
<label>Owner capital (USD)<select id="capital"><option value="100000">1,000</option><option value="150000">1,500</option><option value="200000" selected>2,000</option><option value="300000">3,000</option></select></label></div>
<div class="metrics" aria-live="polite"><div class="metric"><span>Expected prospective profit</span><strong id="profit">—</strong></div><div class="metric"><span>Probability of prospective loss</span><strong id="loss">—</strong></div><div class="metric"><span>Expected customer net benefit</span><strong id="benefit">—</strong></div><div class="metric"><span>Probability of financing refusal</span><strong id="finance">—</strong></div></div>
<p class="note">Stopping returns USD0 incrementally. Values exclude the separate illustrative USD2,400 historical build charge. Restricted deposits cannot supply owner capital. Commercial admission remains HOLD in every cell.</p>
<noscript><p class="nojs">The full static tables and figures remain available without JavaScript.</p></noscript></section>'''
    script='''<script>
"use strict";
const economicCells=DATA;
const money=new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",minimumFractionDigits:2,maximumFractionDigits:2});
function updateEconomics(){
 const s=document.getElementById("scenario").value;
 const p=Number(document.getElementById("price").value);
 const c=Number(document.getElementById("capital").value);
 const r=economicCells.find(x=>x.scenario===s&&x.price_cents===p&&x.capital_cents===c);
 if(!r) throw new Error("Unrecognized frozen scenario");
 document.getElementById("profit").textContent=money.format(r.expected.profit.usd);
 document.getElementById("loss").textContent=(100*r.prospective_loss_probability.decimal).toFixed(2)+"%";
 document.getElementById("benefit").textContent=money.format(r.expected.customer_benefit.usd);
 document.getElementById("finance").textContent=(100*r.finance_refusal_probability.decimal).toFixed(2)+"%";
}
for(const id of ["scenario","price","capital"])document.getElementById(id).addEventListener("change",updateEconomics);
updateEconomics();
</script>'''.replace("DATA",json.dumps(records,separators=(",",":")))
    return block,script


def browser(brief=False):
    raw=content(brief);body=pandoc(raw,"html5")
    # Embed all figure bytes: this reading edition performs no initial network fetches.
    body=re.sub(r'src="figures/([^"]+)"',lambda m:'src="data:image/png;base64,'+base64.b64encode((HERE/"figures"/m.group(1)).read_bytes()).decode()+'"',body)
    body=body.replace("<table>",'<div class="table-wrap"><table>').replace("</table>","</table></div>")
    headings=re.findall(r'<h2 id="([^"]+)">(.*?)</h2>',body,re.S)
    toc=''.join(f'<li><a href="#{hid}">{name}</a></li>' for hid,name in headings)
    script=""
    if not brief:
        block,script=economic_explorer()
        marker=re.search(r'<h2 id="[^"]+">10\. Profitability',body)
        if not marker:raise ValueError("Economic explorer insertion point missing")
        body=body[:marker.start()]+block+body[marker.start():]
    subtitle=html.escape(EDITORIAL["subtitle"])
    status='''<div class="status"><p><strong>No transformational flagship is admitted.</strong></p><p>This edition constructs a working supporting nominal-CAD artifact and a reproducible conditional decision model. It does not demonstrate a newly feasible commercially accepted production activity.</p></div>'''
    name="AGI_ALPHA_Executive_Brief" if brief else "AGI_ALPHA_FLYWHEEL"
    other="AGI_ALPHA_FLYWHEEL.html" if brief else "AGI_ALPHA_Executive_Brief.html"
    otherlabel="Complete paper" if brief else "Executive brief"
    text='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="A bounded AGI ALPHA discovery study: executed nominal CAD construction, preserved failures and complete conditional economics.">
<title>'''+html.escape(EDITORIAL["title"])+( " — Executive brief" if brief else "")+'''</title><style>'''+(HERE/"reading.css").read_text()+'''</style></head><body class="'''+("brief" if brief else "paper")+'''">
<a class="skip" href="#paper">Skip to paper</a><header class="hero"><div class="hero-inner"><div class="eyebrow">MONTREAL.AI / '''+("Executive brief" if brief else "Research edition 01")+'''</div>
<h1>AGI ALPHA FLYWHEEL <span>— When Capability Creates Opportunity</span></h1><p class="subtitle">'''+subtitle+'''</p><p class="byline">Vincent Boucher — President of MONTREAL.AI</p><div class="edition">27 October 2026 · Portable production study · Research draft for review</div>
<div class="hero-links"><a href="'''+name+'''.pdf">PDF edition</a><a href="'''+other+'''">'''+otherlabel+'''</a><a href="../README.md">Evidence and replay guide</a><a href="../SAMPLE_DELIVERABLE.md">Working sample</a></div></div></header>
<div class="layout"><aside class="sidebar"><nav aria-label="Contents"><h2>Reading guide</h2><ul>'''+toc+'''</ul><details class="toc-toggle"><summary>Reading guide</summary><ul>'''+toc+'''</ul></details></nav></aside>
<main id="paper">'''+status+body+'''</main></div><footer class="footer"><strong>FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.</strong><br>Author attribution requested by the commissioning user. Research and publication preparation were AI assisted. This record is not peer review, deployment, customer acceptance or physical qualification. The full paper and evidence package preserve the limitations and corrections.</footer>'''+script+'''</body></html>'''
    (HERE/(name+".html")).write_text(text)
    return name+".html"


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--html-only",action="store_true");args=parser.parse_args()
    outputs=[]
    for brief in (False,True):
        outputs.append(browser(brief))
        if not args.html_only:outputs.append(latex(brief))
    print(json.dumps({"outputs":outputs}))
