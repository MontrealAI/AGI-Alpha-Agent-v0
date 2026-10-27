# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/agi-alpha-mplconfig")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.labelcolor':'#364152','text.color':'#251343'})
s=json.loads((ROOT/'results/independent-followup-audit/summary.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(7.5,3.55),gridspec_kw={'width_ratios':[1,1.35]})
labels=['A · incumbent','B · model intake','C2 · ordinary'];colors=['#8E7B9B','#0B9C9A','#B88632'];ys=np.arange(3)
vals=[s['byArm'][a]['completeHandoffAccepted'] for a in ['A','B','C']]
axes[0].barh(ys,vals,color=colors,height=.52);axes[0].set_yticks(ys,labels);axes[0].invert_yaxis();axes[0].set_xlim(0,4.65);axes[0].set_xticks([0,1,2,3,4]);axes[0].set_xlabel('Accepted customer reports · 4 tasks');axes[0].set_title('Fresh handoffs',loc='left',fontweight='bold',pad=14)
for y,v in enumerate(vals):axes[0].text(v+.08,y,f'{v} / 4',va='center',fontsize=10)
axes[1].barh(ys,[6,6,6],color='#0B9C9A',height=.52,label='Conditional preserved')
axes[1].barh(ys,[6,6,6],left=[6,6,6],color='#C2B8CA',height=.52,label='Required unresolved')
axes[1].barh(ys,[0,0,2],left=[12,12,12],color='#BC4862',height=.52,label='Spurious inclusion')
axes[1].set_yticks(ys,['A','B','C2']);axes[1].invert_yaxis();axes[1].set_xlim(0,14.4);axes[1].set_xticks([0,6,12,14]);axes[1].set_xlabel('Call observations · not additional tasks');axes[1].set_title('Required evidence and extra calls',loc='left',fontweight='bold',pad=14)
axes[1].legend(loc='upper center',bbox_to_anchor=(.5,-.24),ncol=2,frameon=False,fontsize=8)
fig.tight_layout(w_pad=2);fig.subplots_adjust(bottom=.25)
fig.savefig(ROOT/'publication/production-comparison.png',dpi=220,bbox_inches='tight');plt.close(fig)
print('production-comparison.png')

market=json.loads((ROOT/'market/accepted-ab-diagnostic/results/summary.json').read_text())
groups={}
for row in market['summaries']:
 key=row['assumptions']['assumptions']['stress'];choice=row['assumptions']['shared']['choiceModel']
 groups.setdefault(key,{})[choice]=row['arms']['A']['profitCents']['mean']/100
names={'reference':'Reference','zero-demand':'Zero demand','low-demand':'Low demand','target-10-dollars':'$10 target','target-5-dollars':r'\$5 target → \$6 floor','strong-cheap-ai':'Stronger / cheaper AI','cheap-human':'Cheaper human','price-war':'Price response','slow-collections':'Delayed collections','quality-failures':'Quality failures','maintenance-shock':'Maintenance shock','cash-and-capacity':'Cash / capacity'}
fig,ax=plt.subplots(figsize=(7.4,4.65))
y=np.arange(len(groups));a=[x['deterministic'] for x in groups.values()];b=[x['logit'] for x in groups.values()]
ax.barh(y-.17,a,height=.32,color='#8E7B9B',label='Deterministic choice');ax.barh(y+.17,b,height=.32,color='#0B9C9A',label='Logit choice')
ax.set_yticks(y,[names[k] for k in groups]);ax.invert_yaxis();ax.axvline(0,color='#251343',lw=.8);ax.set_xlim(-335,12);ax.set_xticks([-300,-200,-100,0]);ax.set_xlabel('Mean modeled operating profit (USD) · A and B identical')
ax.set_title('Zero justified B investment in all 192 paired worlds',loc='left',fontweight='bold',fontsize=11,pad=12)
ax.legend(loc='upper left',frameon=False,fontsize=9);fig.tight_layout();fig.savefig(ROOT/'publication/market-diagnostic.png',dpi=220,bbox_inches='tight');plt.close(fig)
