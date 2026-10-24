# SPDX-License-Identifier: Apache-2.0
"""Export existing vector figures as inlineable PGF without changing source code.

Presentation only. The structured manuscript uses the original PDF figures.
The standalone manuscript embeds PGF and its bibliography, so it needs no
external source/figure files. Standard TeX packages remain prerequisites.
"""
from pathlib import Path
import runpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.figure
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]
matplotlib.rcParams.update({'pgf.texsystem':'pdflatex','pgf.rcfonts':False})
original=matplotlib.figure.Figure.savefig
def export(self,filename,*args,**kwargs):
    path=Path(filename)
    if path.suffix=='.pdf':
        original(self,path.with_suffix('.pgf'),*args,**kwargs)
matplotlib.figure.Figure.savefig=export
runpy.run_path(str(root/'src/make_concept_figure.py'),run_name='__main__')
runpy.run_path(str(root/'publication/make_results_figures.py'),run_name='__main__')
print('Exported four PGF vector figures; original PDF/SVG/PNG assets unchanged.')
