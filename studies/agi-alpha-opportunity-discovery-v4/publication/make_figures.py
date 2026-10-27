# SPDX-License-Identifier: Apache-2.0
"""Exact scientific figures from frozen receipts; no illustrative result invention."""
from pathlib import Path
import json
import textwrap
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'publication/figures';OUT.mkdir(exist_ok=True)
NAVY='#172b45'; TEAL='#087f8c'; GOLD='#c48b24'; RED='#b34548'; LIGHT='#e9eff4'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':NAVY,'text.color':NAVY,'axes.titleweight':'bold','savefig.facecolor':'white'})
def save(fig,name):
 fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight')
 fig.savefig(OUT/(name+'.png'),dpi=190,bbox_inches='tight')
 fig.savefig(OUT/(name+'.svg'),bbox_inches='tight')
 plt.close(fig)
def box(ax,x,y,w,h,label,color=LIGHT,fontsize=10):
 p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012,rounding_size=0.018',fc=color,ec='none');ax.add_patch(p)
 ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=fontsize,wrap=True)
 return (x+w/2,y+h/2)
def arrow(ax,a,b,color=TEAL):
 ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=13,color=color,lw=1.5,shrinkA=10,shrinkB=10))

# Orthographic projection of the actual tessellated public CAD. No generated geometry.
import cadquery as cq
from matplotlib.collections import PolyCollection
shape=cq.importers.importStep(str(ROOT/'data/development/inputs/Plate_AP242.STP')).val()
faces=shape.Faces(); bb=shape.BoundingBox()
center=np.array([(bb.xmin+bb.xmax)/2,(bb.ymin+bb.ymax)/2,(bb.zmin+bb.zmax)/2])
th=np.deg2rad(-15); ph=np.deg2rad(42)
rz=np.array([[np.cos(th),-np.sin(th),0],[np.sin(th),np.cos(th),0],[0,0,1]])
rx=np.array([[1,0,0],[0,np.cos(ph),-np.sin(ph)],[0,np.sin(ph),np.cos(ph)]])
rot=rx@rz
parts=[];colors=[];matched=[];triangle_count=0
for i,f in enumerate(faces):
 vs,ts=f.tessellate(.25)
 if not ts: continue
 v=(np.array([[q.x,q.y,q.z] for q in vs])-center)@rot.T
 tris=v[np.array(ts)]
 highlight=f.geomType()=='CYLINDER' and abs(f._geomAdaptor().Cylinder().Radius()-1.5)<1e-5
 if highlight: matched.append(i)
 normals=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
 shade=.72+.28*np.abs(normals[:,2])
 base=np.array([.035,.50,.55]) if highlight else np.array([.65,.73,.80])
 parts.extend(tris);colors.extend(base*shade[:,None]);triangle_count+=len(ts)
parts=np.array(parts);colors=np.array(colors);order=np.argsort(parts[:,:,2].mean(axis=1));projected=parts[order,:,:2]
fig,ax=plt.subplots(figsize=(10.8,5.2));ax.set_position([.035,.17,.93,.63]);ax.add_collection(PolyCollection(projected,facecolors=colors[order],edgecolors='none',linewidths=0));ax.autoscale_view();ax.set_aspect('equal');ax.axis('off');ax.margins(.01)
fig.text(.04,.955,'An actual instrument, built around actual geometry',fontsize=17,weight='bold')
fig.text(.04,.89,'NIST/MTC Plate · AP242 · 261 faces · three radius-1.5 mm cylindrical surfaces highlighted',fontsize=10)
fig.text(.04,.10,'QIF definition 99 → nominal 100 → characteristic 101 → feature 97 → actual 102',fontsize=11,weight='bold')
fig.text(.04,.04,'3.017 mm satisfies the local interval. The containing inspection still records overall FAIL.',fontsize=10,color=RED)
save(fig,'01_actual_geometry')
(OUT/'geometry_render_receipt.json').write_text(json.dumps({'source':'data/development/inputs/Plate_AP242.STP','faces':len(faces),'triangles':triangle_count,'highlighted_zero_based_faces':matched,'projection':'orthographic rotation of actual tessellation','claim':'geometry illustration; no physical inspection'},indent=2)+'\n')

fig,ax=plt.subplots(figsize=(11,6));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
ax.text(.02,.96,'Transformation witness: preserve the question',fontsize=17,weight='bold')
box(ax,.02,.65,.27,.20,'Original purpose\nAll selected records\nsatisfy interval I?')
box(ax,.365,.65,.27,.20,'Constructed instrument\nExact units + references\nUniversal check / counterexample')
box(ax,.71,.65,.27,.20,'Original-purpose answer\nInvariant under permutation\nOnly for the same record set')
arrow(ax,(.29,.75),(.365,.75));arrow(ax,(.635,.75),(.71,.75))
box(ax,.02,.30,.27,.20,'Box · hypothetical mm\n76 values, [3.246, 3.536]\nDestination [3.1, 3.5]',color='#f7e5e5')
box(ax,.365,.30,.27,.20,'Cover · hypothetical mm\n400 values, [4.523, 4.537]\nDestination [4.2, 4.8]',color='#e0f0ef')
box(ax,.71,.30,.27,.20,'A different question\nWhich hole? Which specimen?\nCan the part be released?',color='#fff1d7')
ax.text(.155,.20,'REFUTED\nConcrete recorded violation',ha='center',va='center',color=RED,weight='bold')
ax.text(.5,.20,'RECORD STATEMENT SUPPORTED\nPhysical family still unproved',ha='center',va='center',color=TEAL,weight='bold',fontsize=9)
ax.text(.845,.20,'FRESH EVIDENCE REQUIRED\nNo inherited permission',ha='center',va='center',color=GOLD,weight='bold',fontsize=9)
ax.text(.02,.04,'Formal FAIR units default to meters. Millimeter interpretation is an explicit research counterfactual, never an automatic repair.',fontsize=9)
save(fig,'02_transformation_witness')

fig,ax=plt.subplots(figsize=(11,6.5));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
ax.text(.02,.96,'One lineage; separate evidence and authority',fontsize=17,weight='bold')
box(ax,.03,.69,.25,.16,'Plate construction\nReaders • proof rules • geometry')
box(ax,.375,.69,.25,.16,'Frozen executable identity\nCode • schema • dependencies')
box(ax,.72,.69,.25,.16,'Existing protected lifecycle\nActual bytes + provenance')
arrow(ax,(.28,.77),(.375,.77));arrow(ax,(.625,.77),(.72,.77))
box(ax,.03,.39,.25,.17,'Fresh mission inputs\nExact source revisions\nPurpose + acceptance')
box(ax,.375,.39,.25,.17,'New recipient execution\nCurrent signed grant\nIndependent source checker')
box(ax,.72,.39,.25,.17,'Useful acquisition audit\nAccepted in reserved mission\nNo physical release',color='#e0f0ef')
arrow(ax,(.845,.69),(.5,.56));arrow(ax,(.28,.475),(.375,.475));arrow(ax,(.625,.475),(.72,.475))
box(ax,.03,.08,.25,.16,'Potential private buyers\nOutside options + rights\nMay decline or withdraw',color='#fff1d7')
box(ax,.375,.08,.25,.16,'Joint offering proposal\nPrice • milestones • refunds\nCash + capacity limits',color='#fff1d7')
box(ax,.72,.08,.25,.16,'Separate admission decision\nProduce, retain, explore or stop\nNo automatic reinvestment',color='#fff1d7')
arrow(ax,(.28,.16),(.375,.16),GOLD);arrow(ax,(.625,.16),(.72,.16),GOLD);arrow(ax,(.5,.39),(.5,.24),GOLD)
save(fig,'03_lineage_and_offering')

p=ROOT/'economics/confirmation'; examples=json.loads((p/'cash_examples.json').read_text())
x=next(x for x in examples if x['seed']==21001 and x['plan']['arm']=='retained_arranged')
y=next(x for x in examples if x['seed']==21001 and x['plan']['arm']=='retained_standard')
fig,axs=plt.subplots(1,2,figsize=(11,4.3),gridspec_kw={'width_ratios':[1.2,1]})
for z,label,col in [(x,'Commission arrangement',TEAL),(y,'Payment on acceptance',NAVY)]:
 ledger=z['realization']['ledger']; days=sorted(set(a['day'] for a in ledger)); cash=[next(a['cash'] for a in reversed(ledger) if a['day']==d) for d in days]
 axs[0].step([0]+days,[6000]+cash,where='post',label=label,color=col,lw=2)
ledger=x['realization']['ledger'];days=sorted(set(a['day'] for a in ledger));un=[next(a['unearned'] for a in reversed(ledger) if a['day']==d) for d in days];rv=[next(a.get('refund_reserve',0) for a in reversed(ledger) if a['day']==d) for d in days]
axs[1].step(days,un,where='post',label='Unearned advance',color=GOLD,lw=2);axs[1].step(days,rv,where='post',label='Refund reserve',color=RED,lw=2)
for ax in axs:ax.set_xlabel('Modeled day');ax.set_ylabel('Assumed USD');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8,frameon=False);ax.set_xticks([0,1,5,15,30])
fig.suptitle('Cash timing can change while total contribution stays the same',fontsize=15,weight='bold');fig.text(.06,-.03,'Explicit illustration: seed 21001, three assumed buyers, USD4,000 each, 75% advance, 50% failure refund. No actual sales.',fontsize=9)
fig.tight_layout();save(fig,'04_cash_timing')

line=json.loads((p/'lineage.json').read_text());s=line['summary'];t=[x['stage'] for x in s]
fig,ax=plt.subplots(figsize=(10,4.4));ax.fill_between(t,[x['scenario_p10'] for x in s],[x['scenario_p90'] for x in s],color=LIGHT,label='10th–90th scenario range (20 artificial paths)');ax.plot(t,[x['mean'] for x in s],'-o',color=TEAL,lw=2,label='Mean incremental net value');ax.axhline(0,color=NAVY,ls='--',lw=1);ax.axvline(4,color=GOLD,ls=':',lw=1.5)
ax.text(4.06,-2600,'Fresh-recipient\ntransfer cost',fontsize=9,color=GOLD)
ax.set(xlabel='Fixed-resource contract horizon',ylabel='Assumed cumulative incremental USD',xticks=t);ax.grid(axis='y',alpha=.2);ax.legend(frameon=False,loc='upper left',fontsize=9)
ax.set_title('The retention campaign was rejected before confirmation',loc='left',fontsize=15)
fig.text(.065,-.04,'Forced-construction diagnostic only: initial USD2,800 plus transfer USD150. It is not admitted or retrospectively recovered profit.',fontsize=9)
fig.tight_layout();save(fig,'05_cumulative_net_value')

summ=json.loads((p/'summary.json').read_text());scens=['central_assumptions','low_opening_cash','negative_transfer','efficient_incumbent','quality_obsolescence']; labels=['Central','Low cash','Negative transfer','Efficient incumbent','Quality decline']
fig,ax=plt.subplots(figsize=(10.6,4.7));xx=np.arange(len(scens));w=.19
for i,(arm,name,c) in enumerate([('expert_standard','Expert, standard',NAVY),('retained_standard','Retained, standard','#7c96ac'),('expert_arranged','Expert, arranged',TEAL),('retained_arranged','Retained, arranged',GOLD)]):
 vals=[next(r['financeable_horizons'] for r in summ if r['scenario']==s and r['arm']==arm) for s in scens]
 ax.bar(xx+(i-1.5)*w,vals,w,label=name,color=c)
ax.set(xticks=xx,xticklabels=labels,ylabel='Financeable horizons / 80 assumed scenarios',ylim=(0,87));ax.grid(axis='y',alpha=.2);ax.legend(frameon=False,ncol=2,fontsize=9)
ax.set_title('The frontier did not expand against the available expert baseline',loc='left',fontsize=15)
fig.text(.065,-.025,'Zero combined-versus-expert-standard feasibility crossings across all 11 declared stresses. Counts are model results, not market evidence.',fontsize=9)
fig.tight_layout();save(fig,'06_productive_frontier')
print('Created six source-derived figures; geometry faces',len(faces),'highlighted',matched)
