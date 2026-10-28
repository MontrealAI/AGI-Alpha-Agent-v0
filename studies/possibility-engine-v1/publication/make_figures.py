# SPDX-License-Identifier: Apache-2.0
"""Render scientific figures directly from the preserved evidence."""
from __future__ import annotations
import json
import math
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from engine import interval,DEFAULT_BOX

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.labelcolor':'#19354b','text.color':'#19354b',
                     'axes.edgecolor':'#c2ccd5','xtick.color':'#526477','ytick.color':'#526477',
                     'savefig.facecolor':'white'})
TEAL='#087f8c';BLUE='#284d83';RED='#b3574c';INK='#142b42'

def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=230,bbox_inches='tight')
    fig.savefig(ROOT/'figures'/f'{name}.pdf',bbox_inches='tight')
    plt.close(fig)


def main():
    witness=json.loads((ROOT/'verification/independent_graphs.json').read_text())
    fig=plt.figure(figsize=(10.2,6.1));gs=fig.add_gridspec(2,2,height_ratios=[2.8,1.0],hspace=.38)
    for idx,model in enumerate(witness['models']):
        ax=fig.add_subplot(gs[0,idx]);a=np.array(model['adjacency'])
        theta=np.pi/2-2*np.pi*np.arange(16)/16
        xy=np.column_stack((1.6*np.cos(theta),1.6*np.sin(theta)))
        for i in range(16):
            for j in range(i+1,16):
                if a[i,j]:ax.plot(xy[[i,j],0],xy[[i,j],1],color='#adc0ce',lw=.8,zorder=1)
        if a[15,13]:ax.plot(xy[[15,13],0],xy[[15,13],1],color=RED,lw=3,zorder=2)
        for i,(x,y) in enumerate(xy):
            col=TEAL if i==0 else RED if i in [15,13] else BLUE
            ax.scatter([x],[y],s=200,color=col,edgecolor='white',linewidth=1.1,zorder=3)
            ax.text(x,y,str(i),color='white',ha='center',va='center',fontsize=8.5,zorder=4)
        ax.set_xlim(-2,2);ax.set_ylim(-2,2);ax.set_aspect('equal');ax.axis('off')
        ax.set_title(('Rook graph · 8 four-cliques' if idx==0 else 'Shrikhande graph · 0 four-cliques'),fontsize=12,pad=12)
    ax=fig.add_subplot(gs[1,:]);names=['Original port','Add actuators','Add sensors','Joint addition']
    values=[0,0,0,.036330357311783]
    ax.barh(names[::-1],values[::-1],height=.48,color=[TEAL,'#aab8c5','#aab8c5','#aab8c5'])
    ax.set_xlim(0,.043);ax.set_xlabel('Robust separating margin (normalized output)')
    for i,v in enumerate(values[::-1]):ax.text(v+.0008,i,f'{v:.5f}' if v else '0 · exact ambiguity',va='center',fontsize=9)
    ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('The missing observable requires both new capabilities',fontsize=15,fontweight='bold',y=1.01)
    save(fig,'complementarity')
    t=np.linspace(.02,.65,400)
    fig,ax=plt.subplots(figsize=(9.1,4.8))
    for kind,label,col in [(1,'Adjacent pair hypothesis',BLUE),(0,'Nonadjacent pair hypothesis',TEAL)]:
        bands=np.array([interval(kind,float(x),DEFAULT_BOX) for x in t]);ax.fill_between(t,bands[:,0],bands[:,1],alpha=.19,color=col)
        ax.plot(t,bands.mean(axis=1),color=col,lw=2,label=label)
    time=.168;hi0=interval(0,time,DEFAULT_BOX)[1];lo1=interval(1,time,DEFAULT_BOX)[0]
    ax.axvline(time,color=INK,lw=1,ls='--');ax.annotate('',(time,hi0),(time,lo1),arrowprops={'arrowstyle':'<->','color':RED,'lw':2})
    ax.text(.19,.040,'Gap 0.03633\nat t = 0.168',color=RED,fontweight='bold')
    ax.set_xlabel('Observation time (normalized units)');ax.set_ylabel('Output including bounded measurement error')
    ax.set_title('A new experiment yields disjoint uncertainty ranges',loc='left',fontweight='bold',pad=15)
    ax.legend(frameon=False,loc='upper left');ax.grid(alpha=.16)
    ax.text(0,-.23,'Rate 0.8–1.2 · leakage 0.05–0.15 · gain 0.95–1.05 · error ±0.005\nParameters may differ independently between the alternative hypotheses.',transform=ax.transAxes,fontsize=9,color='#526477')
    save(fig,'response_bands')
    d=json.loads((ROOT/'evidence/development/successor/result.json').read_text())
    data=np.array([e['kinds'] for e in d['selected']]).T
    fig,ax=plt.subplots(figsize=(8.8,4.5))
    from matplotlib.colors import ListedColormap
    ax.imshow(data,cmap=ListedColormap(['#d8eaec',BLUE]),vmin=0,vmax=1,aspect='auto')
    names=['Rook','Shrikhande','Variant 0','Variant 1','Variant 2','Variant 3']
    ax.set_yticks(range(6),names);ax.set_xticks(range(5),[f"{e['actuator']} → {e['sensor']}\ncost {e['cost_units']}" for e in d['selected']])
    for i in range(6):
        for j in range(5):ax.text(j,i,'adjacent' if data[i,j] else 'nonadjacent',ha='center',va='center',color='white' if data[i,j] else INK,fontsize=9)
    ax.set_title('One instrument, a harder successor mission',loc='left',fontweight='bold',pad=18)
    ax.set_xlabel('Selected actuation → readout pairs; total minimum cost 66 units',labelpad=12)
    ax.text(0,-.29,'Every pair of hypotheses remains distinguishable after any one terminal-access outage.\nIndependent exhaustive construction finds the same optimum.',transform=ax.transAxes,fontsize=9,color='#526477')
    ax.tick_params(length=0);save(fig,'successor')
    summary_path=ROOT/'economics/confirmation/summary.json'
    if summary_path.exists():
        s=json.loads(summary_path.read_text())
        names=['reference','low_demand','same_ai_price_war','supplier_shock','payment_deviation','rational_buyers','high_need','correlated_failure','strongest_free','lower_labor','no_launch']
        names=[n for n in names if n in s]
        labels={'reference':'Reference','low_demand':'Lower demand','same_ai_price_war':'Same-AI price war','supplier_shock':'Supplier shock','payment_deviation':'Payment deviation','rational_buyers':'Rational buyers','high_need':'Higher need','correlated_failure':'Correlated failure','strongest_free':'Strongest free alternative','lower_labor':'Lower operating labor','no_launch':'Stop after research'}
        for n in s:
            if n not in names and isinstance(s[n],dict) and 'mean_profit_cents' in s[n] and 'conventional' not in n:names.append(n)
        vals=[s[n]['mean_profit_cents']/100000 for n in names]
        low=[(s[n]['mean_profit_cents']-s[n].get('profit_p05_cents',s[n]['mean_profit_cents']))/100000 for n in names]
        high=[(s[n].get('profit_p95_cents',s[n]['mean_profit_cents'])-s[n]['mean_profit_cents'])/100000 for n in names]
        fig,ax=plt.subplots(figsize=(10.5,5.8));y=np.arange(len(names))
        ax.barh(y,vals,color=[TEAL if 'no_launch' in n else RED for n in names],alpha=.88,height=.63)
        ax.errorbar(vals,y,xerr=[np.maximum(low,0),np.maximum(high,0)],fmt='none',ecolor=INK,capsize=3,lw=1)
        ax.set_yticks(y,[labels.get(n,n.replace('_',' ').title()) for n in names]);ax.invert_yaxis()
        for i,v in enumerate(vals):ax.text(-.6,i,f'−${abs(v):.1f}k',ha='right',va='center',color='white',fontweight='bold',fontsize=9)
        ax.set_xlim(-76,0);ax.set_xlabel('Simulated full-project profit (USD thousands; negative is a loss)')
        ax.set_title('Complete-project economics after all obligations close',loc='left',fontweight='bold',pad=15)
        ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
        ax.text(0,-.22,'128 fresh histories per scenario. Whiskers: conditional 5th–95th world percentiles.\nThey measure variation under assumed inputs, not confidence in market demand.',transform=ax.transAxes,fontsize=9,color='#526477')
        save(fig,'economics')


if __name__=='__main__':main()
