# SPDX-License-Identifier: Apache-2.0
"""Regenerate vector research figures from the packaged, recorded data only."""
import json
from pathlib import Path
import matplotlib.pyplot as plt
from make_figures import save,INK,PURPLE,TEAL,GOLD,MUTED,ROSE
ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/'plot-data.json').read_text())
s=DATA['study'];load=DATA['load']
labels={'portfolio':'Strong portfolio','workflow':'Saved workflow','learner':'Conventional learner','flywheel':'Selective flywheel'}
colors={'portfolio':INK,'workflow':GOLD,'learner':TEAL,'flywheel':PURPLE}
markers={'portfolio':'s','workflow':'D','learner':'^','flywheel':'o'}
fig,ax=plt.subplots(figsize=(8.7,4.4))
for arm in ['portfolio','workflow','learner','flywheel']:
 rows=sorted([r for r in s['arms'] if r['arm']==arm],key=lambda r:r['budget'])
 ax.plot([r['budget']/1e6 for r in rows],[r['mean_qualified'] for r in rows],label=labels[arm],color=colors[arm],marker=markers[arm],markersize=7,lw=1.8,linestyle='--' if arm=='learner' else '-')
ax.set(xlabel='Cumulative cap per stream · million declared work units',ylabel='Mean qualified missions / 72 offered',xticks=[.25,1,2],ylim=(0,72))
ax.grid(alpha=.15);ax.set_axisbelow(True)
ax.set_title('Opportunity coverage includes the cost of obtaining it',loc='left',color=INK,fontweight='bold',pad=14)
ax.legend(frameon=False,ncol=2,loc='upper left',bbox_to_anchor=(0,-.19),fontsize=10)
fig.tight_layout();save(fig,'opportunity-coverage')

fig,ax=plt.subplots(figsize=(8.7,4.1))
arms=['portfolio','workflow','learner','flywheel'];categories=[('Delivery','mission',PURPLE),('Discovery','discovery',ROSE),('Qualification','qualification',TEAL),('Control + evidence','control',GOLD)]
y=list(range(len(arms)))[::-1];left=[0.0]*len(arms)
for label,key,color in categories:
 values=[]
 for arm in arms:
  r=next(r for r in s['arms'] if r['arm']==arm and r['budget']==1000000);c=r['cost_breakdown']
  mission=c.get('mission',0);discovery=c.get('discovery',0);qual=c.get('qualification',0)+c.get('qualification-reference',0)
  total={'mission':mission,'discovery':discovery,'qualification':qual,'control':sum(c.values())-mission-discovery-qual}[key]
  values.append(total/r['streams']/1e6)
 ax.barh(y,values,left=left,color=color,height=.55,label=label)
 left=[a+b for a,b in zip(left,values)]
for yi,arm,total in zip(y,arms,left):
 r=next(r for r in s['arms'] if r['arm']==arm and r['budget']==1000000)
 ax.text(total+.012,yi,f"{r['qualified']}/{r['offered']} qualified",va='center',fontsize=9,color=INK)
ax.set_yticks(y,[labels[a] for a in arms]);ax.tick_params(axis='y',length=0,pad=8)
ax.set(xlim=(0,1.30),xlabel='Mean charged work per stream · millions · primary cap 1M')
ax.spines['left'].set_visible(False);ax.grid(axis='x',alpha=.13);ax.set_axisbelow(True)
ax.set_title('The method must repay discovery, checks and upkeep',loc='left',color=INK,fontweight='bold',pad=14)
ax.legend(frameon=False,ncol=2,loc='upper left',bbox_to_anchor=(0,-.21),fontsize=10)
fig.tight_layout();save(fig,'full-cost-comparison')

fig,ax=plt.subplots(figsize=(8.7,3.9))
rows=s['diagnostic'];names={'inherited':'Retained ancestry','removed':'Parent removed','rebuild':'Ancestry rebuilt','equivalent':'Equivalent replacement'}
values=[r['mean_work']/1e6 for r in rows];y=list(range(4))[::-1]
ax.barh(y,values,color=[PURPLE,MUTED,ROSE,TEAL],height=.55)
for yi,r,v in zip(y,rows,values):
 ax.text(v+.03,yi,f"{r['complete_three_stage_chains']}/{r['streams']} typed lineages",va='center',fontsize=9,color=INK)
ax.set_yticks(y,[names[r['treatment']] for r in rows]);ax.tick_params(axis='y',length=0,pad=8)
ax.set(xlabel='Mean full diagnostic work · million declared units',xlim=(0,max(values)+1.25))
ax.spines['left'].set_visible(False);ax.grid(axis='x',alpha=.13);ax.set_axisbelow(True)
ax.set_title('Constructive ancestry has a measurable price',loc='left',color=INK,fontweight='bold',pad=14)
fig.tight_layout();save(fig,'ancestry-interventions')

fig,axes=plt.subplots(1,2,figsize=(8.7,3.5))
b=load['batches'];names=[str(x['offered']) for x in b]
axes[0].bar(names,[x['throughput_per_second'] for x in b],color=PURPLE,width=.6)
axes[0].set(ylabel='Completed tasks / second',xlabel='Offered batch size')
axes[1].plot(names,[x['latency_p50_ms'] for x in b],color=TEAL,marker='o',label='Median')
axes[1].plot(names,[x['latency_p95_ms'] for x in b],color=ROSE,marker='s',label='95th percentile')
axes[1].set(ylabel='Enqueue-to-durable latency · ms',xlabel='Offered batch size');axes[1].legend(frameon=False,fontsize=9)
for ax in axes:ax.grid(axis='y',alpha=.13);ax.set_axisbelow(True)
fig.suptitle('Finite local load: throughput and waiting time',x=.075,ha='left',color=INK,fontweight='bold',fontsize=13)
fig.tight_layout();save(fig,'finite-load')
