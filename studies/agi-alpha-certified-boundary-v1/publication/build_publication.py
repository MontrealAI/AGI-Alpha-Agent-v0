# SPDX-License-Identifier: Apache-2.0
"""Build matching LaTeX/PDF, self-contained HTML and GitHub-readable editions."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parent


def run(command):
    done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                          env={**os.environ, 'TEXMFVAR':'/tmp/agi-alpha-tex-cache'}, check=False)
    (ROOT/'qa'/('build_'+command[0]+'.log')).write_text(done.stdout+done.stderr)
    if done.returncode:
        print((done.stdout+done.stderr)[-6000:])
        raise SystemExit(done.returncode)
    if done.stderr:
        print(done.stderr[-1500:])


def main():
    (ROOT/'qa').mkdir(exist_ok=True)
    for name in ['paper','executive_brief']:
        source=ROOT/f'{name}.md'
        text=source.read_text()
        if 'PLACEHOLDER' in text:
            raise ValueError(f'Unresolved manuscript placeholder: {name}')
        common=['pandoc',f'{name}.md','--standalone','--citeproc','--bibliography=references.bib']
        run(common+['--to=latex','--lua-filter=layout.lua','--template=paper_template.tex',f'--output={name}.tex'])
        run(['pdflatex','-interaction=nonstopmode','-halt-on-error',f'{name}.tex'])
        run(['pdflatex','-interaction=nonstopmode','-halt-on-error',f'{name}.tex'])
        html_input=ROOT/f'{name}_html_input.md'
        html_input.write_text(text.replace('figures/bound.pdf','figures/bound.svg')
                                  .replace('figures/witness.pdf','figures/witness.svg')
                                  .replace('figures/economics.pdf','figures/economics.svg')
                                  .replace('figures/cash.pdf','figures/cash.svg'))
        run(['pandoc',html_input.name,'--standalone','--citeproc','--bibliography=references.bib',
             '--mathml','--embed-resources','--template=html_template.html','--css=style.css',f'--output={name}.html'])
        run(common+['--to=gfm+tex_math_dollars',f'--output={name.upper()}.md'])
        reader=ROOT/f'{name.upper()}.md'
        heading=('# AGI ALPHA FLYWHEEL — When Capability Creates Opportunity\n\n'
                 '**The Certified Boundary Edition · Research-review edition v1 · 27 October 2026**\n\n'
                 'Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work\n\n'
                 'Vincent Boucher — President of MONTREAL.AI\n\n')
        reader.write_text(heading+reader.read_text().replace('figures/bound.pdf','figures/bound.svg')
                         .replace('figures/witness.pdf','figures/witness.svg')
                         .replace('figures/economics.pdf','figures/economics.svg')
                         .replace('figures/cash.pdf','figures/cash.svg'))
        html_input.unlink()
    manifest={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
              ['paper.md','paper.tex','paper.pdf','paper.html','executive_brief.md','executive_brief.pdf',
               'references.bib','paper_template.tex','html_template.html','style.css','make_figures.py',
               'build_publication.py','layout.lua']}
    (ROOT/'build_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built both PDFs, complete HTML editions, LaTeX sources and reading Markdown.')


if __name__=='__main__':
    main()
