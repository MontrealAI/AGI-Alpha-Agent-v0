# SPDX-License-Identifier: Apache-2.0
"""Build a complete single-file TeX source with inline vector graphics and refs."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
paper=root/'paper'
def expand(path):
    text=path.read_text()
    return re.sub(r'\\input\{([^}]+)\}',lambda m:expand(paper/m.group(1)),text)
text=expand(paper/'paper.tex')
text=text.replace(r'\usepackage{enumitem,fancyhdr,titlesec,tcolorbox,caption,float,hyperref,needspace}',
                  r'\usepackage{enumitem,fancyhdr,titlesec,tcolorbox,caption,float,hyperref,needspace,pgf}')
text=text.replace(r'\begin{document}',r'\providecommand{\mathdefault}[1]{#1}'+'\n'+r'\begin{document}',1)
text=text.replace(r'\bibliographystyle{plainnat}'+'\n'+r'\bibliography{bibliography}',(paper/'paper.bbl').read_text())
embedded=[]
def figure(m):
    graphic=root/'figures'/Path(m.group(1)).with_suffix('.pgf').name
    data=graphic.read_text()
    # Matplotlib's PGF output is pure vector data for these four figures.
    if '\\pgfimage' in data or '\\includegraphics' in data:
        raise RuntimeError('External raster dependency in PGF figure')
    name='nova-seeds-embedded-'+str(len(embedded)+1)+'.pgf'
    embedded.append('\\begin{filecontents*}[overwrite]{'+name+'}\n'+data+'\n\\end{filecontents*}\n')
    return '\\resizebox{\\textwidth}{!}{\\input{'+name+'}}'
text=re.sub(r'\\includegraphics\[width=\\textwidth\]\{([^}]+)\}',figure,text)
remaining=re.findall(r'\\(?:input|includegraphics|bibliography)\{([^}]+)\}',text)
if remaining != ['nova-seeds-embedded-'+str(i)+'.pgf' for i in range(1,5)]:
    raise RuntimeError('Unexpanded external source dependency')
header='% Nova-Seeds, edition v1. Complete standalone source.\n% Rebuild with pdflatex twice; structured source and original canonical PDF are in the full archive.\n% Embedded vector contents are written locally by TeX; no external assets or downloads are needed.\n% PGF uses TeX text metrics; exact PDF bytes and figure-font metrics may differ from the canonical PDF.\n'
(paper/'nova-seeds-abundance-v1.tex').write_text(header+'\n'.join(embedded)+text)
print('Created standalone paper/nova-seeds-abundance-v1.tex')
