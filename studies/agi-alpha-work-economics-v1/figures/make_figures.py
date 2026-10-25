#!/usr/bin/env python3
"""Editable, data-derived scientific figures. Does not rerun experiments."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import textwrap
from io import BytesIO
os.environ.setdefault('MPLCONFIGDIR', '/tmp/agi-alpha-economics-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
analysis = json.loads((ROOT / 'raw/ANALYSIS.json').read_text())
primary = json.loads((ROOT / 'raw/primary/results.json').read_text())['records']
scale = json.loads((ROOT / 'raw/scale/results.json').read_text())
economics = json.loads((ROOT / 'economics_post/measured_resource_economics.json').read_text())
PURPLE, INK, TEAL, GOLD = '#55258A', '#221A36', '#16756C', '#AB7F32'
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10,
    'axes.spines.top':False, 'axes.spines.right':False, 'axes.labelcolor':INK,
    'xtick.color':INK, 'ytick.color':INK, 'text.color':INK,
    'pdf.fonttype':42, 'ps.fonttype':42, 'svg.fonttype':'none', 'svg.hashsalt':'alpha-work-economics-v1'})
FIXED = datetime(2026,10,25,11,15,50,tzinfo=timezone.utc)

def save(fig, name):
    formats = [('pdf', {'metadata':{'Title':name.replace('_',' '),'Author':'MONTREAL.AI',
                                    'CreationDate':FIXED,'ModDate':FIXED}}),
               ('svg', {'metadata':{'Date':FIXED.isoformat()}}), ('png', {'dpi':180})]
    for suffix, options in formats:
        buffer = BytesIO()
        fig.savefig(buffer, format=suffix, bbox_inches='tight', **options)
        content = buffer.getvalue()
        if suffix == 'pdf' and not content.rstrip().endswith(b'%%EOF'):
            raise ValueError(f'Incomplete PDF figure: {name}')
        temporary = OUT / (name+'.'+suffix+'.tmp')
        with temporary.open('wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(OUT / (name+'.'+suffix))
    plt.close(fig)

fig, ax = plt.subplots(figsize=(7.4,4.8))
fig.subplots_adjust(left=.02,right=.98,bottom=.06,top=.98)
ax.set(xlim=(0,10),ylim=(0,7)); ax.axis('off')
def card(x,y,n,title,stat,detail):
    ax.add_patch(FancyBboxPatch((x,y),4.40,2.14,boxstyle='round,pad=.10,rounding_size=.15',
                               facecolor='#F2EDF8',edgecolor='#D7C9E8',linewidth=.8))
    ax.text(x+.20,y+1.72,f'{n}  {title}',fontweight='bold',fontsize=11,color=PURPLE)
    ax.text(x+.20,y+1.11,stat,fontweight='bold',fontsize=13.2,color=INK)
    wrapped='\n'.join(textwrap.fill(line,width=42) for line in detail.split('\n'))
    ax.text(x+.20,y+.46,wrapped,fontsize=8.5,linespacing=1.35,va='center')
card(.15,4.35,'01','Work delivered','135 paths · 16 changes',
     'Exact release-inventory exception package\nIndependent machine acceptance')
card(5.25,4.35,'02','Capability retained','A reusable executable',
     'Byte-identified successor-tool.mjs\nExisting methods; construction not priced')
card(.15,1.45,'04','Productive capacity','132 → 332 / minute',
     'Accepted outputs, one → four processes\nNine finite batches; no service guarantee')
card(5.25,1.45,'03','Subsequent work','36 / 36 accepted',
     'Fresh inputs · four contexts · three levels\n0.301 s median process turnaround')
for p,q in [((4.75,5.42),(5.10,5.42)),((7.45,4.17),(7.45,3.77)),((5.10,2.52),(4.75,2.52))]:
    ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=15,color=PURPLE,lw=1.8))
ax.add_patch(FancyBboxPatch((.15,.15),9.50,.73,boxstyle='round,pad=.10',facecolor='#FFF9EC',edgecolor=GOLD,lw=.8))
ax.text(4.90,.53,'Employer value depends on cost, quality and attention',ha='center',fontsize=10.4,fontweight='bold',color=INK)
ax.text(4.90,-.18,'Attention, investment allocation and human duration remain explicit economic inputs.',ha='center',fontsize=9,color=INK)
save(fig,'signature')

fig,ax=plt.subplots(figsize=(6.9,3.4))
colors=[TEAL,PURPLE,GOLD]
for i,(level,c) in enumerate(zip(['low','medium','high'],colors)):
    rows=[r for r in primary if r['complexity']==level]
    vals=np.array([r['process_turnaround_seconds'] for r in rows])
    jitter=np.linspace(-.16,.16,len(vals))
    ax.scatter(np.full(len(vals),i)+jitter,vals,c=c,s=32,edgecolor='white',linewidth=.5,zorder=3)
    med=float(np.median(vals)); ax.hlines(med,i-.26,i+.26,color=c,lw=2.5)
    ax.text(i,1.46,f'{med:.3f} s median',ha='center',color=c,fontweight='bold',fontsize=10)
ax.set_xticks([0,1,2],['Low\n80 base rows','Medium\n360 base rows','High\n1,200 + duplicates'])
ax.set_ylabel('Process turnaround (seconds)'); ax.set_ylim(0,1.58)
ax.set_title('Every fresh job, including verification and packaging',loc='left',fontsize=12,fontweight='bold',pad=12)
ax.grid(axis='y',alpha=.20); ax.set_axisbelow(True)
fig.text(.5,-.01,'12 jobs per level · 36 / 36 machine accepted · controlled task portfolio',ha='center',fontsize=9)
fig.tight_layout();save(fig,'job_times')

fig,ax=plt.subplots(figsize=(6.9,3.8))
x=np.linspace(0,60,600);w=35.96;cpu=analysis['primary_cpu_seconds']['median']/3600
for k,c in [(1,TEAL),(5,PURPLE),(20,GOLD)]:
    h=x-60*(k+cpu)/w
    ax.plot(x,np.where(h>=0,h,np.nan),color=c,lw=2.2,label=f'USD{k} other cost / attempt')
ax.plot(x,x,color='#AAA4B4',lw=1,ls=':',label='Equal effort, zero other cost')
ax.scatter([30],[5],s=65,color=PURPLE,zorder=6)
ax.annotate('Illustration: 30 → 5 min\nUSD17.98 → USD4.00',xy=(30,5),xytext=(35,10),
            fontsize=9,arrowprops={'arrowstyle':'-','color':PURPLE},color=PURPLE,
            bbox={'facecolor':'white','edgecolor':'none','pad':2.2,'alpha':1})
ax.text(24,31,'Below a line:\nlower modeled cost',fontsize=10,color=TEAL,ha='center')
ax.set(xlim=(0,60),ylim=(0,60),xlabel='Traditional human work per attempt (minutes)',
       ylabel='Maximum affordable system attention (minutes)')
ax.set_title('How much employer attention can the system afford?',loc='left',fontsize=12,fontweight='bold',pad=12)
ax.grid(alpha=.16);ax.legend(loc='upper left',frameon=False,fontsize=8.4)
fig.tight_layout();save(fig,'attention_frontier')

fig,axes=plt.subplots(1,2,figsize=(7.1,3.4))
for i,c in enumerate([1,2,4]):
    values=[b['accepted_per_minute'] for b in scale['batches'] if b['concurrency']==c]
    axes[0].scatter([i-.05,i,i+.05],values,s=45,c=PURPLE,edgecolor='white',linewidth=.5,zorder=4)
    med=float(np.median(values));axes[0].hlines(med,i-.2,i+.2,color=PURPLE,lw=2)
    axes[0].text(i,max(values)+16,f'{med:.0f}',ha='center',fontsize=10,color=PURPLE,fontweight='bold')
lat=[analysis['scale'][str(c)]['submit_to_delivery_seconds']['p95'] for c in [1,2,4]]
axes[1].plot([0,1,2],lat,color=TEAL,marker='o',lw=2,ms=7)
for i,v in enumerate(lat): axes[1].text(i,v+.20,f'{v:.2f} s',ha='center',color=TEAL,fontsize=9.5)
for ax in axes:
    ax.set_xticks([0,1,2],['1','2','4']);ax.set_xlabel('Concurrent local processes');ax.grid(axis='y',alpha=.2);ax.set_xlim(-.4,2.4)
axes[0].set_ylim(0,410);axes[0].set_ylabel('Accepted deliveries / minute');axes[0].set_title('Throughput: all nine batches',loc='left',fontsize=10.5,fontweight='bold')
axes[1].set_ylim(0,6.4);axes[1].set_ylabel('p95 submission-to-delivery seconds');axes[1].set_title('Queued delivery latency',loc='left',fontsize=10.5,fontweight='bold')
fig.text(.5,-.015,'108 accepted attempts · 12 mixed jobs per batch · one shared host',ha='center',fontsize=9)
fig.tight_layout(w_pad=2.0);save(fig,'capacity')

names=['Equal effort','15-minute workflow','30-minute workflow','Low attention','Heavy review','Short job, heavy review']
rows=[]
for name,r in zip(names,economics['main_us_office_scenarios']):
    vals=[name,str(r['human_minutes_assumed']),str(r['alpha_attention_minutes_assumed']),
          f"{r['allocation_per_attempt_assumed']:.0f}",f"{r['human_cost']:.2f}",
          f"{r['alpha_cost']:.2f}",f"{r['cost_ratio']:.2f}"]
    rows.append(' & '.join(vals)+r' \\')
(ROOT/'paper/economics-rows.tex').write_text('\n'.join(rows)+'\n')
print('Created four editable SVG/PDF figures and modeled economic table.')
