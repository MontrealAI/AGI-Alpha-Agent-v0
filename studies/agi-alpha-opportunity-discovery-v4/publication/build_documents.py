# SPDX-License-Identifier: Apache-2.0
"""Build editable TeX and passive PDFs from the evidence-derived manuscripts."""
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
TITLE='AGI ALPHA FLYWHEEL — When Capability Creates Opportunity'
SUB='Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work'
AUTHOR='Vincent Boucher — President of MONTREAL.AI'
ABSTRACT='''# Abstract

We investigate whether expert frontier-AI operation can discover an opportunity,
construct a reusable instrument and a viable offering, and leave a successor
better equipped for useful work. A bounded opportunity portfolio precedes a
manufacturing inspection-evidence experiment on actual NIST/MTC sources.
The constructed instrument combines exact QIF semantics, CAD witnesses,
permutation-invariant record reasoning and source-specific acquisition plans.
The original frozen version passes 5/8 independent scoped audits; a separate
recipient's actual executable transfer passes, with no physical acceptance and
no advantage over an identical-content ordinary library. A separately versioned
repair passes 4/4 prospectively frozen new missions on the same historical data.
A small hosted same-model trial yields U4/4, E4/4 and E+3/4 strict accepted jobs;
a lenient E+ reading yields parity, and complete costs remain unknown.
A frozen conditional economic experiment finds no new feasibility crossing
against the expert baseline across eleven stresses and rejects the proposed
six-horizon retention investment. A subsequent contractual audit exposes a
milestone-refund contingency missing from the original financing model.
The contribution is an executable, inspectable lineage and a disciplined limit:
numerical invariance can equip new evidence questions, while physical identity,
current authority, participation and financing still require their own evidence.
No autonomous market creation, earned commercial Alpha, specialist ASI or
commercial compounding is established. All original failures and source versions
are preserved.

**Keywords:** transformational intelligence; Operational Alpha; inspection
evidence; QIF; STEP; selective inheritance; market design; cash timing.

'''

def main():
    sections='\n\n'.join(p.read_text() for p in sorted((HERE/'sections').glob('*.md')))
    replacements={
        '## Exact units change the answer':'![Actual Plate geometry and the local-result/overall-status distinction. The geometry is computed from the public AP242 source, not generated imagery.](figures/01_actual_geometry.png)\n\n## Exact units change the answer',
        '## Transformation witnesses':'![The transformation preserves the exact record question. Hypothetical unit repair does not supply physical coverage or permission.](figures/02_transformation_witness.png)\n\n## Transformation witnesses',
        '# Operational Alpha: a proportionate actual test':'![Capability, current mission, authority and commercial arrangement remain linked but separately checked.](figures/03_lineage_and_offering.png)\n\n# Operational Alpha: a proportionate actual test',
        '## Retention can be rejected without denying useful capability':'![One explicitly selected simulated cash path. Advances, unearned obligations and reserves are separate from earned contribution.](figures/04_cash_timing.png)\n\n## Retention can be rejected without denying useful capability',
        '# What becomes possible next':'![A forced-construction diagnostic after prospective rejection; it does not recover or admit profit.](figures/05_cumulative_net_value.png)\n\n![The modeled productive frontier remains unchanged against the expert alternative.](figures/06_productive_frontier.png)\n\n# What becomes possible next'
    }
    for old,new in replacements.items():
        if old not in sections: raise ValueError('missing figure insertion point '+old)
        sections=sections.replace(old,new,1)
    body=ABSTRACT+sections+'\n\n'+(HERE/'REFERENCES.md').read_text()
    (HERE/'PAPER_BODY.md').write_text(body)
    (HERE/'PAPER.md').write_text(f'# {TITLE}\n\n## {SUB}\n\n**{AUTHOR}**\n\n**Additive opportunity-discovery edition v4 · 27 October 2026**\n\n**FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.**\n\n'+body)
    docs=[('PAPER_BODY.md','AGI_ALPHA_FLYWHEEL_v4',True),('EXECUTIVE_BRIEF.md','AGI_ALPHA_FLYWHEEL_v4_Executive_Brief',False),('EVIDENCE_COMPANION.md','AGI_ALPHA_FLYWHEEL_v4_Evidence_Companion',False)]
    for source,stem,cover in docs:
        args=['pandoc',source,'--standalone','--from=markdown+tex_math_dollars','--to=latex','--include-in-header=style.tex','--top-level-division=section','-V','documentclass=article','-V','fontsize='+('11pt' if cover else '10pt'),'-V','geometry:margin=0.78in','-V','mainfont=DejaVu Serif','-V','sansfont=DejaVu Sans','-V','monofont=DejaVu Sans Mono','-V','linestretch=1.03','-o',stem+'.tex']
        if cover: args+=['--include-before-body=cover.tex','--number-sections']
        subprocess.run(args,cwd=HERE,check=True)
        path=HERE/(stem+'.tex');tex=path.read_text().replace('.png}', '.pdf}')
        def wrapcode(m):
            raw=m.group(1)
            if re.fullmatch(r'[0-9a-f]{24,}',raw):
                raw='\\allowbreak{}'.join(raw[i:i+8] for i in range(0,len(raw),8))
            value=raw.replace('\\_','\\_\\allowbreak{}')
            value=re.sub(r'([/.-])',r'\1\\allowbreak{}',value)
            return '\\texttt{'+value+'}'
        tex=re.sub(r'\\texttt\{([^{}]+)\}',wrapcode,tex)
        path.write_text(tex)
        for _ in range(2):
            subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error',stem+'.tex'],cwd=HERE,check=True,stdout=subprocess.DEVNULL)
        print(stem+'.pdf')

if __name__=='__main__': main()
