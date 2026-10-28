# SPDX-License-Identifier: Apache-2.0
"""Build the complete LaTeX, PDF and offline browser reading editions."""
from __future__ import annotations
import base64
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import yaml

P=Path(__file__).resolve().parent
HTML_ONLY='--html-only' in sys.argv


def run(args):
    if HTML_ONLY and (args[0]=='xelatex' or args[-1].endswith('.tex')):
        return
    subprocess.run(args,cwd=P,check=True,capture_output=True,text=True)


def main():
    common=['--citeproc','--bibliography=references.bib','--csl=numeric.csl']
    paper=['pandoc','PAPER.md',*common,'--standalone','--number-sections','--toc','--toc-depth=1',
           '-V','documentclass=article','-V','fontsize=11pt','-V','geometry:margin=0.82in',
           '-V','colorlinks=true','-V','linkcolor=ink','-V','urlcolor=teal',
           '-V','mainfont=DejaVu Serif','-V','sansfont=DejaVu Sans','-V','monofont=DejaVu Sans Mono',
           '-H','header.tex','-o','AGI_ALPHA_FLYWHEEL.tex']
    run(paper)
    tex=P/'AGI_ALPHA_FLYWHEEL.tex'
    if not HTML_ONLY:
        tex.write_text(tex.read_text().replace(
            r'\hypertarget{why-the-old-instrument-cannot-answer}',
            r'\Needspace{7\baselineskip}'+'\n'+r'\hypertarget{why-the-old-instrument-cannot-answer}'))
    for _ in range(3):run(['xelatex','-interaction=nonstopmode','-halt-on-error','AGI_ALPHA_FLYWHEEL.tex'])
    run(['pandoc','EXECUTIVE_BRIEF.md','--standalone','-V','documentclass=article','-V','fontsize=10pt',
         '-V','geometry:margin=0.76in','-V','mainfont=DejaVu Serif','-H','brief_header.tex',
         '-o','EXECUTIVE_BRIEF.tex'])
    for _ in range(2):run(['xelatex','-interaction=nonstopmode','-halt-on-error','EXECUTIVE_BRIEF.tex'])
    run(['pandoc','PAPER.md',*common,'--number-sections','--section-divs','--mathml','-t','html5','-o','body.html'])
    run(['pandoc','PAPER.md',*common,'-t','gfm','--wrap=none','-o','READING_EDITION.md'])
    metadata=yaml.safe_load((P/'PAPER.md').read_text().split('---',2)[1])
    full_abstract=metadata['abstract'].strip()
    reading=P/'READING_EDITION.md'
    reading.write_text('# AGI ALPHA FLYWHEEL — The Possibility Engine\n\n'
        '**Vincent Boucher · President of MONTREAL.AI · 28 October 2026**\n\n'
        '## Abstract\n\n'+full_abstract+'\n\n'+reading.read_text())
    body=(P/'body.html').read_text()
    body=re.sub(r'<p>(<math[^>]*display="block".*?</math>)</p>',
                r'<div class="math-scroll" tabindex="0" aria-label="Scrollable equation">\1</div>',body,flags=re.S)
    def embed(m):
        path=(P/m.group(1)).resolve()
        if not path.is_file():raise ValueError(f'Missing image {path}')
        return 'src="data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()+'"'
    body=re.sub(r'src="([^"]+\.png)"',embed,body)
    headings=re.findall(r'<section\s+id="([^"]+)"\s+class="level1[^"]*"[^>]*>\s*<h1[^>]*>(.*?)</h1>',body,re.S)
    toc=''.join(f'<a href="#{anchor}">{re.sub("<[^>]+>","",label)}</a>' for anchor,label in headings)
    abstract=html.escape(full_abstract)
    widget='''<aside class="widget" aria-label="Interactive explanation of complementary access"><h2>Explore the missing observable</h2><p>Choose the available capabilities, then increase the bounded measurement error. The scientific purpose stays fixed.</p><div class="controls"><div><label for="access">Available interface</label><select id="access"><option value="old">Original port</option><option value="actuator">Add actuators only</option><option value="sensor">Add sensors only</option><option value="joint" selected>Joint actuator + sensor</option></select></div><div><label for="noise">Measurement error ±<output id="noise-value">0.005</output></label><input id="noise" aria-label="Bounded measurement error" type="range" min="0" max="40" step="1" value="5"></div></div><svg viewBox="0 0 650 180" role="img" aria-label="Two model response intervals" id="interval-chart"><g id="bands"></g></svg><p class="verdict" id="verdict" aria-live="polite"></p><p class="fineprint">Analytical explainer at t = 0.168, rate 0.8–1.2, leakage 0.05–0.15 and gain 0.95–1.05. The original-port view uses the diagonal response; single-sided views use a root-neighbor channel. Equality holds for all allowed single-sided channels. This widget is not the qualified command-line constructor or a physical measurement. Full methods and frozen evidence follow.</p><noscript><p>The interactive plot requires JavaScript. The complete results and paper below remain readable.</p></noscript></aside>'''
    script='''const access=document.getElementById('access'),noise=document.getElementById('noise');function intervals(kind,t,e){let z=[Math.exp(-4*1.2*t),Math.exp(-4*.8*t)];if(kind===1&&z[0]<=1/3&&z[1]>=1/3)z.push(1/3);let f=z.map(v=>kind===2?(1+6*v+9*v*v)/16:kind===1?(1+2*v-3*v*v)/16:(1-v)**2/16);return [.95*Math.exp(-.15*t)*Math.min(...f)-e,1.05*Math.exp(-.05*t)*Math.max(...f)+e];}function update(){let e=Number(noise.value)/1000;document.getElementById('noise-value').textContent=e.toFixed(3);let a=intervals(access.value==='old'?2:1,.168,e),b=access.value==='joint'?intervals(0,.168,e):a.slice(),gap=access.value==='joint'?a[0]-b[1]:0;let lo=Math.min(a[0],b[0])-.015,hi=Math.max(a[1],b[1])+.015;let mobile=window.matchMedia('(max-width:600px)').matches;document.getElementById('interval-chart').setAttribute('viewBox',mobile?'0 0 320 180':'0 0 650 180');let x=v=>(mobile?10:160)+(v-lo)/(hi-lo)*(mobile?300:450);let g='';[a,b].forEach((d,i)=>{let y=mobile?40+i*65:45+i*58;g+=`<text x="0" y="${mobile?y-20:y+5}" font-size="13" fill="#142b42">Hypothesis ${i+1}</text><line x1="${x(d[0])}" y1="${y}" x2="${x(d[1])}" y2="${y}" stroke="${i?'#087f8c':'#284d83'}" stroke-width="17" stroke-linecap="round"/><text x="${x((d[0]+d[1])/2)}" y="${y+30}" text-anchor="middle" font-size="12" fill="#526477">[${d[0].toFixed(5)}, ${d[1].toFixed(5)}]</text>`;});g+=`<text x="${mobile?10:160}" y="174" font-size="12" fill="#526477">Normalized possible output</text>`;document.getElementById('bands').innerHTML=g;let v=document.getElementById('verdict');v.textContent=access.value!=='joint'?'The two models have identical response families.':gap>0?'Distinguishable · separating margin '+gap.toFixed(5):'No guaranteed distinction at this error bound.';v.style.color=access.value==='joint'&&gap>0?'#087f8c':'#a9493e';}access.addEventListener('change',update);noise.addEventListener('input',update);window.addEventListener('resize',update);update();'''
    css=(P/'reader.css').read_text()
    doc=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="The Possibility Engine: an executed construction of complementary observability and a complete conditional enterprise decision."><title>AGI ALPHA FLYWHEEL — The Possibility Engine</title><style>{css}</style></head><body><a class="skip" href="#paper">Skip to the complete paper</a><header class="hero" id="top"><div class="eyebrow">MONTREAL.AI · RESEARCH EDITION 01 · 28 OCTOBER 2026</div><div class="motto">AGI ALPHA FLYWHEEL</div><h1><span>The possibility</span><span>engine.</span></h1><p class="motto">INVENT WHAT BECOMES POSSIBLE.</p><p class="subtitle">Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work</p><div class="byline"><strong>Vincent Boucher</strong><br>President of MONTREAL.AI</div></header><div class="topline"><span class="tag">42/42 fresh technical checks</span><span class="tag">336/336 circuit exports verified</span><span class="tag">Conventional and library parity</span><span class="tag">Decision: stop the tested paid launch</span></div><div class="layout"><nav class="toc" aria-label="Contents"><strong>The complete paper</strong>{toc}</nav><main id="paper"><section class="abstract"><h2>Abstract</h2><p>{abstract}</p></section>{widget}{body}</main></div><footer class="footer">Complete offline reading edition. All figures, mathematics and text are included in this file. Technical scope: declared synthetic models and circuit-software execution. Commercial scope: conditional simulation. The companion includes LaTeX, runnable source, raw evidence, independent audits and preserved failures.<br>Scientific freeze: e1ccee55bf1269fd3fc0932538782a2eaaa1eeda31cf06880435708fd74e33d7.<br>© 2026 Vincent Boucher / MONTREAL.AI. Source code under Apache-2.0. No social post or production deployment is implied.</footer><a class="backtop" href="#top">Back to top ↑</a><script>{script}</script></body></html>'''
    (P/'BROWSER_EDITION.html').write_text(doc)
    print(json.dumps({'paper_pdf_bytes':(P/'AGI_ALPHA_FLYWHEEL.pdf').stat().st_size,'browser_bytes':len(doc.encode()),'sections':len(headings)}))


if __name__=='__main__':main()
