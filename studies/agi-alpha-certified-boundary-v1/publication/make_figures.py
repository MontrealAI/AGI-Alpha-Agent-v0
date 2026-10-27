# SPDX-License-Identifier: Apache-2.0
"""Rebuild exact-data figures; plotted samples illustrate, never certify, the proof."""
from pathlib import Path
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from numpy.polynomial.chebyshev import chebval
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / 'figures'
OUT.mkdir(exist_ok=True)
PURPLE, TEAL, GOLD, INK, MUTED = '#512575', '#147C80', '#B17828', '#20182D', '#6B6274'
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'axes.titlesize':12,
                     'axes.labelcolor':INK, 'text.color':INK, 'axes.edgecolor':'#C7BED0',
                     'xtick.color':MUTED, 'ytick.color':MUTED, 'axes.spines.top':False,
                     'axes.spines.right':False, 'figure.facecolor':'white', 'axes.facecolor':'white',
                     'svg.fonttype':'none', 'savefig.bbox':'tight'})

def save(fig, name):
    for suffix in ('pdf','svg','png'):
        fig.savefig(OUT/f'{name}.{suffix}', dpi=180)
    plt.close(fig)

raw = json.loads((ROOT/'scout/revised_polynomial.json').read_text())
c = np.zeros(21)
c[::2] = [float(Fraction(s)) for s in raw['coefficients']]
x = np.linspace(0,1,2001)
f = chebval(2*x-1,c)
final=json.loads((ROOT/'certificate/weight.json').read_text())
normalized=np.interp(x,np.linspace(0,1,21),final['heights'])/float(Fraction(final['maximum']))
fig,ax=plt.subplots(figsize=(7.2,3.15))
ax.fill_between(x,0,normalized,color=PURPLE,alpha=.09)
ax.plot(x,normalized,color=PURPLE,lw=2.2,label='Final piecewise-linear weight W / M')
ax.plot(x,f,color=MUTED,lw=1.0,ls=':',label='Earlier polynomial')
ax.axhline(1,color=TEAL,lw=1.2,ls='--',alpha=.8)
ax.set(xlim=(0,1),ylim=(-.02,2.35),xlabel='Normalized interval position x',ylabel='Normalized witness weight')
ax.text(.04,2.21,'A nonuniform accounting weight',weight='bold',color=PURPLE)
ax.text(.04,2.02,'Final integral: 0.9805039606…  Every admissible class is checked.',fontsize=9)
ax.text(.98,1.04,'uniform weight = 1',ha='right',fontsize=8,color=TEAL)
ax.grid(axis='y',color='#EEE9F2',lw=.7)
ax.legend(loc='lower center',fontsize=8,frameon=False)
save(fig,'witness')

fig,ax=plt.subplots(figsize=(7.2,2.55))
prior=np.sqrt(8)-2
I=float(Fraction(final['bound']))
ax.plot([prior,I],[.4,.4],color='#CABBD7',lw=8,solid_capstyle='round')
ax.scatter([prior],[.4],s=90,color=MUTED,zorder=3)
ax.scatter([I],[.4],s=100,color=PURPLE,zorder=4)
ax.axvline(.98,color=GOLD,lw=1.2,ls='--')
ax.text(prior,.66,'Inspected prior universal bound\n√8 − 2 ≈ 0.828427',ha='left',fontsize=10)
ax.text(I,.04,'Final conventional certificate\n0.9805039606…',ha='right',color=PURPLE,fontsize=10,weight='bold')
ax.text(.978,.72,'Question threshold: 0.98',ha='right',color=GOLD,fontsize=9)
ax.set(xlim=(.817,1.002),ylim=(-.25,1.2),xlabel='Heft lower bound')
ax.set_yticks([])
ax.spines['left'].set_visible(False)
ax.text(.818,-.17,'Prior bound: Emanuel (2011), Appendix C. Constant optimality is not claimed.',fontsize=8,color=MUTED)
ax.text(.92,1.08,'Certified gap above 0.98: 0.0005039606…',ha='center',fontsize=9,color=PURPLE)
save(fig,'bound')

econ=json.loads((ROOT/'economics/results.json').read_text())
scenarios=['adverse','central','favorable']
profits=[econ['scenarios'][s]['full_project_profit']/1000 for s in scenarios]
fig,ax=plt.subplots(figsize=(7.2,3.0))
bars=ax.barh(scenarios,profits,color=['#925060',PURPLE,TEAL],height=.52)
ax.axvline(0,color=INK,lw=.8)
for bar,p in zip(bars,profits):
    ax.text(p+(0.45 if p>=0 else -.45),bar.get_y()+bar.get_height()/2,
            f'${p:+,.2f}k',ha='left' if p>=0 else 'right',va='center',weight='bold')
ax.set(xlim=(-26,21),xlabel='Conditional full-project profit, before financing (USD thousands)')
ax.text(.02,1.06,'Assumed $6,000 fee; 2 / 4 / 5 prospective sponsors',transform=ax.transAxes,color=MUTED,fontsize=9)
ax.grid(axis='x',color='#EEE9F2',lw=.7)
ax.set_axisbelow(True)
save(fig,'economics')

rows=list(csv.DictReader((ROOT/'economics/cash_ledger.csv').open()))
rows=[r for r in rows if r['scenario']=='central']
spend=[float(r['spendable_cash_before_new_finance'])/1000 for r in rows]
restricted=[float(r['restricted_refundable_deposits'])/1000 for r in rows]
reserve=[float(r['additional_unrestricted_warranty_reserve'])/1000 for r in rows]
labels=['Research','Deposit','Review','Core\naccepted','Integration','Final\naccepted']
fig,ax=plt.subplots(figsize=(7.2,3.4))
ax.plot(range(6),spend,'o-',color=PURPLE,lw=2,label='Spendable cash before new finance')
ax.plot(range(6),restricted,'s--',color=GOLD,lw=1.5,label='Restricted refundable deposits')
ax.axhline(0,color=INK,lw=.8)
ax.fill_between(range(6),spend,0,where=np.array(spend)<0,color=PURPLE,alpha=.08)
ax.set_xticks(range(6),labels)
ax.set(ylabel='USD thousands',ylim=(-9,12))
ax.annotate('Peak added funding need\n$6,573.20',xy=(2,spend[2]),xytext=(2.55,-7.0),
            arrowprops={'arrowstyle':'->','color':PURPLE},fontsize=9,color=PURPLE)
ax.legend(loc='upper right',fontsize=8,frameon=False)
ax.grid(axis='y',color='#EEE9F2',lw=.7)
save(fig,'cash')
print('Wrote four figures as PDF, SVG and PNG.')
