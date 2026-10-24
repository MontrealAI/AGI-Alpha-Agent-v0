# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).resolve().parents[1]
s=json.loads((root/'results/holdout-01/analysis/summary.json').read_text())
lookup={(x['condition'],x['method']):x for x in s['summary']}
out=root/'figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#C6BFD4','axes.labelcolor':'#282039','text.color':'#282039','xtick.color':'#51485F','ytick.color':'#51485F','grid.color':'#E7E1ED','svg.fonttype':'none','pdf.fonttype':42})
colors={'idea':'#B2A5C3','greedy':'#B97927','disclosed':'#79A7BB','verified':'#562392','clone':'#985DCF','expert':'#255C98','adaptive-expert':'#168578'}
names={'idea':'Conservative','greedy':'Greedy + signed evidence','disclosed':'Disclosed planner','verified':'Verified native artifact','clone':'Complete source replica','expert':'Exact expert + evidence','adaptive-expert':'Adaptive expert + evidence'}
def save(fig,name):
 for suffix in ('pdf','svg','png'):fig.savefig(out/f'{name}.{suffix}',dpi=170,bbox_inches='tight',facecolor='white')
 plt.close(fig)
conditions=['ordinary','capacity-doubled','tight-validity','measurement-drift','demand-drift','reliability-failure','cheap-calibration','expensive-evidence']
labels=['Ordinary','Doubled sample capacity','Short calibration validity','Hidden measurement drift','Public demand drift','Shared slot failures','Zero-duration calibration','Repeated verification']
fig,ax=plt.subplots(figsize=(10.6,5.9));methods=['idea','verified','greedy','adaptive-expert'];offset=[-.24,-.08,.08,.24]
for method,dy in zip(methods,offset):
 vals=[lookup[c,method]['utility']['mean'] for c in conditions];cis=np.array([lookup[c,method]['utility']['ci95'] for c in conditions]);label=names[method] if method!='verified' else 'Verified = clone = stationary expert'
 ax.errorbar(vals,np.arange(8)+dy,xerr=[np.array(vals)-cis[:,0],cis[:,1]-np.array(vals)],fmt='o',ms=5,capsize=2,lw=1.3,color=colors[method],label=label)
ax.set_yticks(np.arange(8),labels);ax.invert_yaxis();ax.set_xlabel('True useful output per four-tick mission  |  synthetic utility units')
ax.set_xlim(0,max(x['utility']['ci95'][1] for x in s['summary'])+3);ax.grid(axis='x');ax.set_axisbelow(True)
ax.set_title('Productive benefit can survive while exclusivity disappears',loc='left',fontsize=14,weight='bold',pad=48)
ax.legend(loc='lower left',bbox_to_anchor=(-.01,1.015),ncol=2,frameon=False,fontsize=9)
fig.text(.13,.015,'32 paired seed clusters × 12 epochs; descriptive 95% cluster-bootstrap intervals. All instrument outcomes are simulated.',fontsize=8,color='#655B72')
fig.subplots_adjust(left=.26,bottom=.14,top=.80);save(fig,'condition-outcomes')

fig,axes=plt.subplots(1,2,figsize=(10.8,4.4))
for method in ['idea','verified','greedy','adaptive-expert']:
 rows=[x for x in s['temporal'] if x['condition']=='measurement-drift' and x['method']==method]
 x=[r['epoch']+1 for r in rows]
 axes[0].plot(x,[r['meanUtility'] for r in rows],'-o',color=colors[method],lw=1.8,ms=3,label=names[method])
 axes[1].plot(x,[r['cumulativeMeanUtility'] for r in rows],'-o',color=colors[method],lw=1.8,ms=3)
for ax in axes:
 ax.set_xlabel('Repeated synthetic epoch');ax.set_xticks([1,3,6,9,12]);ax.grid(alpha=.75);ax.set_axisbelow(True);ax.set_ylim(bottom=0)
axes[0].set_title('Delayed diagnostics can change the next decision',loc='left',fontsize=11,weight='bold');axes[0].set_ylabel('Useful output per mission')
axes[1].set_title('A complete horizon retains the loss',loc='left',fontsize=11,weight='bold');axes[1].set_ylabel('Cumulative mean useful output')
fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',ncol=2,frameon=False,fontsize=9,bbox_to_anchor=(.5,-.02))
fig.suptitle('A valid model proof does not make a drifting instrument truthful',fontsize=14,weight='bold',x=.085,ha='left',y=1.03)
fig.subplots_adjust(bottom=.26,wspace=.29,top=.88);save(fig,'drift-and-time')

fig,axes=plt.subplots(1,2,figsize=(10.8,5.0));methods=['idea','disclosed','verified','clone','expert','greedy','adaptive-expert'];short=['Conservative','Disclosed','Verified','Replica','Exact expert','Greedy','Adaptive']
for condition,ax,title in zip(['ordinary','measurement-drift'],axes,['Stationary instrument','Instrument with hidden drift']):
 for method,label in zip(methods,short):
  a=lookup[condition,method];x=a['accountedRowCpuMs']['mean'];y=a['utility']['mean']
  ax.scatter(x,y,color=colors[method],s=42,zorder=3)
  dy={'idea':-14,'disclosed':-14,'verified':14,'clone':-13,'expert':14,'greedy':-14,'adaptive-expert':14}[method]
  if condition=='ordinary' and method=='adaptive-expert':dy=-31
  ax.annotate(label,(x,y),xytext=(1,dy),textcoords='offset points',fontsize=8,color=colors[method],ha='center')
 ax.set_xscale('log');ax.set_xlim(min(lookup[condition,m]['accountedRowCpuMs']['mean'] for m in methods)/1.8,max(lookup[condition,m]['accountedRowCpuMs']['mean'] for m in methods)*1.7);ax.set_ylim(0,max(lookup[c,m]['utility']['mean'] for c in ['ordinary','measurement-drift'] for m in methods)+6)
 ax.set_xlabel('Attributed CPU per mission (ms, logarithmic)');ax.set_title(title,fontsize=12,weight='bold',loc='left');ax.grid(alpha=.8);ax.set_axisbelow(True)
axes[0].set_ylabel('True useful output (synthetic utility units)')
fig.suptitle('The sufficient comparator can be cheaper',fontsize=15,weight='bold',x=.08,ha='left',y=.98)
fig.text(.08,.02,'CPU includes planning, external outcome replay, and signed-service setup where present. Authoring and physical costs remain unknown.',fontsize=8,color='#655B72')
fig.subplots_adjust(top=.86,bottom=.16,wspace=.25);save(fig,'output-compute')
