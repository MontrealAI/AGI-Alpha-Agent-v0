from pathlib import Path
from datetime import datetime,timezone
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).parent;F=R/'figures';F.mkdir(exist_ok=True)
a=json.loads((R/'data/analysis.json').read_text());d=json.loads((R/'data/derived.json').read_text());e=json.loads((R/'data/first-response.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'earned-turn-results-04'})
P='#5A31A0';T='#007A78';G='#A27B25';M='#5D6577';I='#1C2536';STAMP=datetime(2026,10,24,tzinfo=timezone.utc)
labels={'flywheel':'Flywheel','conventional_reuse':'Conventional reuse','native_refactor':'Native refactor + cache','direct_specialist':'Direct warm CG','parent_rebuilt':'Parent rebuilt','equivalent':'Independent equivalent','no_reinvestment':'No reinvestment'}
order=list(labels)
def save(fig,name):
 fig.savefig(F/(name+'.pdf'),metadata={'CreationDate':STAMP,'ModDate':STAMP,'Title':name,'Author':'Vincent Boucher · MONTREAL.AI'})
 fig.savefig(F/(name+'.svg'),metadata={'Date':STAMP.isoformat(),'Creator':'AGI ALPHA Earned Turn'});plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.0));fig.subplots_adjust(left=.29,right=.94,bottom=.17,top=.87)
for i,k in enumerate(order):ax.barh(i,a['arms'][k]['qualified'],color=P if k=='flywheel' else '#C9BCE3',height=.58);ax.text(500,i,'492 / 492',va='center',fontsize=11,color=I)
ax.set(yticks=range(7),yticklabels=[labels[k] for k in order],xlim=(0,585),xlabel='Qualified useful outcomes under the fixed resource ceilings');ax.invert_yaxis();ax.spines[['left','bottom']].set_color('#C9CBD1');ax.tick_params(axis='y',length=0);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);fig.suptitle('Coverage is complete — and equal.',x=.29,ha='left',fontsize=16,fontweight='bold',color=P);save(fig,'qualified-coverage')
order2=['native_refactor','conventional_reuse','direct_specialist','parent_rebuilt','equivalent','no_reinvestment']
fig,ax=plt.subplots(figsize=(9,4.5));fig.subplots_adjust(left=.32,right=.97,bottom=.2,top=.85);ax.axvspan(.92,.95,color=G,alpha=.10);ax.axvline(.95,color=G,ls='--',lw=1.3);ax.axvline(1,color=I,lw=1);ax.axvline(1.1,color=T,ls=':',lw=1.2)
for i,k in enumerate(order2):
 r=a['comparisons'][k];lo,hi=r['ci95'];ax.errorbar(r['cpu_ratio'],i,xerr=[[r['cpu_ratio']-lo],[hi-r['cpu_ratio']]],fmt='o',capsize=4,color=P if i==0 else T if i==1 else M,markersize=7,lw=2)
ax.set(yticks=range(6),yticklabels=[labels[k] for k in order2],xlim=(.92,1.11),ylim=(-.7,5.7),xlabel='Flywheel CPU / comparator CPU · 95% paired-stream interval');ax.invert_yaxis();ax.grid(axis='x',alpha=.1);ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
fig.suptitle('A local mechanism does not clear the product gate.',x=.07,ha='left',fontsize=16,fontweight='bold',color=P);fig.text(.32,.07,'Gold: primary <0.95 target     Black: parity     Teal: conventional <1.10 guard',fontsize=10.5,color=M);save(fig,'full-cost-comparison')
fig,axs=plt.subplots(1,4,figsize=(9,3.65),sharey=True);fig.subplots_adjust(left=.09,right=.985,bottom=.23,top=.80,wspace=.22)
for ax,g,title in zip(axs,['recurring','rare','wide_change','maintenance'],['Recurring','Rare','Wide change','Maintenance']):
 vals=[a['regimes'][g][k]['cpu_ms']/1000 for k in ['flywheel','native_refactor','direct_specialist']];ax.bar(range(3),vals,color=[P,T,'#AEB6C4'],width=.7);ax.set(xticks=range(3),xticklabels=['Fly','Native','CG'],ylim=(0,2.95),title=title);ax.tick_params(axis='x',labelrotation=30);ax.grid(axis='y',alpha=.12);ax.set_axisbelow(True)
axs[0].set_ylabel('Mean whole-participant CPU (s)');fig.suptitle('Maintenance changes the trade-off.',x=.09,ha='left',fontsize=16,fontweight='bold',color=P);fig.text(.09,.03,'Six independent streams per regime; descriptive means. All treatments qualify the same tasks.',fontsize=10.5,color=M);save(fig,'regime-costs')
fig,ax=plt.subplots(figsize=(7.2,4.4));fig.subplots_adjust(left=.08,right=.88,bottom=.16,top=.85);x=np.array(e['A']).reshape(48,48);m=max(abs(x.min()),abs(x.max()));p=ax.pcolormesh(np.arange(49),np.arange(49),x,cmap='PuOr',vmin=-m,vmax=m,rasterized=False);ax.set_aspect('equal');ax.set(xlabel='Grid column',ylabel='Grid row',xlim=(0,48),ylim=(0,48));cb=fig.colorbar(p,ax=ax,pad=.04);cb.set_label('Computed response · synthetic units');fig.suptitle('The first mission already produces a checked result.',fontsize=14,fontweight='bold',color=P);fig.text(.14,.025,'2,304 nodes · 4,512 edges · relative balance residual 2.44 × 10⁻¹⁵',fontsize=10.5,color=M);save(fig,'first-useful-result')
