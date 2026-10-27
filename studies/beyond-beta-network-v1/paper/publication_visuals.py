# SPDX-License-Identifier: Apache-2.0
"""Standalone scientific figures from executed results; no simulation or fitting."""
from __future__ import annotations

import json
import math
import os
import tempfile
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR",str(Path(tempfile.gettempdir())/"beyond-beta-publication-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, MaxNLocator

SCENARIOS=("conservative","central","favorable")
COLORS={"enterprise":"#7e8290","beta":"#7e8290","network":"#6e3c9d","local":"#26967e","same-price-beta":"#7e8290"}
PURPLE="#6e3c9d"
GREEN="#26967e"
RED="#af4f58"
STRESS_NAMES={"humanReference":"Human-team reference", "buyerValueMedian":"Buyer value", "prospectsMonthly":"Monthly prospects", "commonError":"Common error", "tokenMultiplier":"Token-resource factor", "collectionDelayWeeks":"Collection delay, weeks", "retentionCostMultiplier":"B resource factor", "paidLearningProbability":"Candidate probability", "rightsClearedProbability":"Rights-clearance probability", "betaBundleAbsorption":"Beta absorption", "assetLifetimeWeeks":"Useful life, weeks"}


def finish(fig, output, title, subtitle="All economic events simulated; USD. Uncertainty is conditional on the specified model."):
    fig.suptitle(title,fontsize=18,fontweight="bold",x=.06,ha="left",color="#30223f")
    fig.text(.06,.018,subtitle,fontsize=11,color="#64606b",ha="left")
    fig.tight_layout(rect=(.02,.05,.99,.94))
    for suffix in ("pdf","svg","png"):
        fig.savefig(output.with_suffix("."+suffix),dpi=200,bbox_inches="tight",facecolor="white")
    plt.close(fig)


def money_axis(ax, axis="x"):
    def money_tick(x,p):
        if abs(x)<1e-10:return "$0"
        prefix="−" if x<0 else ""
        v=abs(x)
        return prefix+(f"${v/1000:g}M" if v>=1000 else f"${v:g}k" if v>=1 else f"${v*1000:g}")
    formatter=FuncFormatter(money_tick)
    (ax.xaxis if axis=="x" else ax.yaxis).set_major_formatter(formatter)


def make_figures(root, protocol, conf, selected, meta, sens, scale, metrics):
    out=root/"paper/figures";out.mkdir(exist_ok=True,parents=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":13,"axes.spines.top":False,"axes.spines.right":False,"axes.labelcolor":"#403749","axes.titleweight":"bold","axes.grid":True,"grid.color":"#e6e1eb","grid.alpha":.7,"axes.axisbelow":True,"pdf.fonttype":42,"svg.fonttype":"none"})
    # A matched cohort: every human reference and quote has the same useful-job weights.
    fig,axes=plt.subplots(1,2,figsize=(10.7,4.3))
    y=np.arange(3)
    for k,label,color,offset in [("human","Human reference","#aaa1b6",-.23),("price","Sale price",PURPLE,0),("cost","Full resource cost",GREEN,.23)]:
        vals=[(metrics[s]["network"][k] or 0)/1000 for s in SCENARIOS]
        axes[0].barh(y+offset,vals,.22,label=label,color=color)
    
    for i,s in enumerate(SCENARIOS):
        if metrics[s]["network"]["cost"] is None:
            axes[0].text(.02,i,"No useful cohort: cost undefined",transform=axes[0].get_yaxis_transform(),fontsize=10,color=RED)
    axes[0].set_yticks(y,[s.title() for s in SCENARIOS]);axes[0].invert_yaxis();axes[0].set_title("Network cohort; logarithmic USD");axes[0].set_xscale("log");axes[0].set_xlim(1,2000);axes[0].set_xticks([1,10,100,1000],["$1k","$10k","$100k","$1M"]);axes[0].legend(fontsize=9,loc="center right")
    for i,s in enumerate(SCENARIOS):
        for j,arm in enumerate(("enterprise","network")):
            d=conf["scenarios"][s]["arms"][arm]["profitCents"]
            axes[1].plot([d["p05"]/1e5,d["p95"]/1e5],[i+j*.16-.16]*2,color=COLORS[arm],lw=2)
            axes[1].plot(d["median"]/1e5,i+j*.16-.16,"o",color=COLORS[arm],ms=5,label=("Selected Beta" if arm=="enterprise" else "Network policy") if i==0 else None)
    axes[1].axvline(0,color=RED,lw=1);axes[1].set_yticks(y,[s.title() for s in SCENARIOS]);axes[1].invert_yaxis();axes[1].set_title("Pre-tax profit: median, 5–95%");money_axis(axes[1]);axes[1].legend(fontsize=10.5)
    finish(fig,out/"economics","Modeled delivery and enterprise economics")
    # Empirical CDFs preserve the full downside distribution.
    fig,axes=plt.subplots(1,3,figsize=(10.7,3.7),sharey=True)
    for ax,s in zip(axes,SCENARIOS):
        for arm in ("enterprise","network"):
            x=np.sort([r["profitCents"]/1e5 for r in conf["rows"] if r["scenario"]==s and r["arm"]==arm]);ax.step(x,np.arange(1,len(x)+1)/len(x),where="post",label="Selected Beta" if arm=="enterprise" else "Network policy",color=COLORS[arm],lw=1.7)
        ax.axvline(0,color=RED,lw=1);ax.set_title(s.title());money_axis(ax);ax.set_xlabel("Fully allocated pre-tax profit");ax.xaxis.set_major_locator(MaxNLocator(3))
    axes[0].set_ylabel("Fraction of independent worlds");axes[-1].legend(fontsize=10.5)
    finish(fig,out/"profit_distribution","Confirmation distributions, including adverse worlds")
    # Price profiles use development observations only. They do not change selection.
    train=json.loads((root/"results/training.json").read_text());policies={p["id"]:p for p in protocol["selection"]["policies"]}
    amendment_path=root/"protocol/beta_symmetry_amendment.json"
    if amendment_path.exists():
        amendment=json.loads(amendment_path.read_text());extra=json.loads((root/"results/beta_symmetry_training.json").read_text())
        train["rows"]=[r for r in train["rows"] if policies[r["policy"]]["allowInvestment"]]+extra["rows"]
        policies={p["id"]:p for p in [*[p for p in policies.values() if p["allowInvestment"]],*amendment["betaPolicies"]]}
    fig,axes=plt.subplots(1,3,figsize=(10.7,3.7))
    for ax,s in zip(axes,SCENARIOS):
        grouped=defaultdict(list)
        for row in train["rows"]:
            if row["scenario"]==s:grouped[row["policy"]].append(row)
        for investment,color,label in [(False,"#7e8290","Beta-only"),(True,PURPLE,"B/C enabled")]:
            profile=[]
            for ratio in sorted(set(p["priceRatio"] for p in policies.values())):
                choices=[]
                for pid,rr in grouped.items():
                    p=policies[pid]
                    if p["allowInvestment"]!=investment or p["priceRatio"]!=ratio:continue
                    z=sorted(r["discountedAccrualProfitCents"] for r in rr);risk=sum(r["insolvent"] for r in rr)/len(rr)
                    score=float(np.mean(z))+.25*float(np.mean(z[:math.ceil(.1*len(z))]));choices.append((risk<=.05,-risk,score,pid,float(np.mean([r["profitCents"] for r in rr]))/1e5))
                feasible=[x for x in choices if x[0]]
                best=sorted(feasible,key=lambda x:(-x[2],-x[1],x[3]))[0] if feasible else sorted(choices,key=lambda x:(-x[1],-x[2],x[3]))[0]
                profile.append((ratio,best[-1]))
            ax.plot([x for x,y in profile],[y for x,y in profile],"o-",color=color,label=label)
        ax.axhline(0,color=RED,lw=1);ax.set_title(s.title());ax.set_xlabel("Base quote / human reference",fontsize=11);money_axis(ax,"y")
    axes[0].set_ylabel("Development mean profit");axes[-1].legend(fontsize=10.5)
    finish(fig,out/"pricing","Price choice is conditional on buyer value, risk and capacity","Development profiles only; best policy within each ratio by the registered objective/risk rule. Confirmation never reselects.")
    fig,axes=plt.subplots(1,2,figsize=(10.7,4.1))
    left=np.zeros(3)
    for key,label,color in [("a_paid_work","A: paid work",PURPLE),("b_retention","B: additional",GREEN),("c_optional_research","C: optional","#c99b55"),("common_business","Common + past","#aaa1b6")]:
        values=np.array([metrics[s]["network"]["accounting"][key]/1000 for s in SCENARIOS]);axes[0].barh(y,values,left=left,label=label,color=color);left+=values
    axes[0].set_yticks(y,[s.title() for s in SCENARIOS]);axes[0].invert_yaxis();axes[0].set_title("Resource expense, charged once");money_axis(axes[0]);axes[0].legend(fontsize=9,loc="upper right")
    for k,label,color,offset in [("paidOriginCandidates","Candidates",PURPLE,-.2),("retentionCampaigns","B attempts",GREEN,0),("paidOriginAdmissions","Paid-origin admission","#c99b55",.2)]:
        axes[1].barh(y+offset,[conf["scenarios"][s]["arms"]["network"][k]["mean"] for s in SCENARIOS],.19,label=label,color=color)
    axes[1].set_yticks(y,[s.title() for s in SCENARIOS]);axes[1].invert_yaxis();axes[1].set_title("Paid work does not guarantee Alpha");axes[1].set_xlabel("Mean events per independent world");axes[1].legend(fontsize=10.5)
    finish(fig,out/"investment","Paid development and optional retention")
    fig,axes=plt.subplots(1,2,figsize=(10.7,5.4))
    for ax,comparators in zip(axes,[("same-price-beta","local"),("no-paid-learning","no-separate-research")]):
        pos=0;labels=[]
        for s in SCENARIOS:
            for comparator in comparators:
                d=conf["scenarios"][s]["contrasts"]["network_minus_"+comparator]["differences"]["profitCents"];lo,hi=d["meanMC95"]
                ax.plot([lo/1e5,hi/1e5],[pos,pos],color=PURPLE,lw=2);ax.plot(d["mean"]/1e5,pos,"o",color=PURPLE)
                labels.append(s.title()+"\nvs "+comparator.replace("same-price-beta","same-price Beta").replace("no-paid-learning","no paid learning").replace("no-separate-research","no separate C"));pos+=1
        ax.set_yticks(range(pos),labels,fontsize=11);ax.invert_yaxis();ax.axvline(0,color=RED,lw=1);money_axis(ax);ax.set_xlabel("Network minus counterfactual profit, MC95")
        if all(conf["scenarios"][s]["contrasts"]["network_minus_"+c]["differences"]["profitCents"]["min"]==0 and conf["scenarios"][s]["contrasts"]["network_minus_"+c]["differences"]["profitCents"]["max"]==0 for s in SCENARIOS for c in comparators):
            ax.set_xlim(-1,1);ax.set_xticks([0]);ax.set_xlabel("Exact zero in all paired records")
    finish(fig,out/"network","Paired policy effects in fresh confirmation")
    fig,axes=plt.subplots(1,2,figsize=(10.7,3.8))
    for i,s in enumerate(SCENARIOS):
        d=conf["scenarios"][s]["contrasts"]["network_minus_static-beta"]["differences"]["profitCents"];lo,hi=d["meanMC95"]
        axes[0].plot([lo/1e5,hi/1e5],[i,i],color=PURPLE,lw=2);axes[0].plot(d["mean"]/1e5,i,"o",color=PURPLE)
    axes[0].set_yticks(y,[s.title() for s in SCENARIOS]);axes[0].invert_yaxis();axes[0].axvline(0,color=RED,lw=1);money_axis(axes[0]);axes[0].set_title("Total moving-versus-static profit effect")
    axes[1].barh(y,[conf["scenarios"][s]["arms"]["network"]["alphaRetired"]["mean"] for s in SCENARIOS],color=GREEN);axes[1].set_yticks(y,[s.title() for s in SCENARIOS]);axes[1].invert_yaxis();axes[1].set_title("Acquired-asset retirements");axes[1].set_xlabel("Mean records per world");axes[1].plot([0,0,0],y,"o",color=GREEN);axes[1].set_xlim(-.5,.5);axes[1].set_xticks([0])
    finish(fig,out/"moving_beta","An assumed Beta upgrade helps delivery; no acquired stock is present","The primary portfolios contain no acquired Alpha. This measures ordinary resource and policy changes, not economic survival of a retained stock.")
    fig,axes=plt.subplots(3,1,figsize=(9.5,7),sharex=True)
    for ax,s in zip(axes,SCENARIOS):
        run=json.loads((root/f"results/examples/{s}_network.json").read_text());b=run["histories"]["balances"]
        ax.plot([x["week"] for x in b],[x["cashCents"]/1e5 for x in b],color=PURPLE,label="Cash")
        ax.plot([x["week"] for x in b],[x["availableCents"]/1e5 for x in b],color=GREEN,label="Available after obligations/reserves")
        ax.axhline(run["config"]["seedCapital"]/1000,color="#aaa1b6",ls=":",label="Initial seed")
        ax.axvline(run["config"]["betaUpgradeWeek"],color="#c99b55",ls=":",lw=1)
        for a in run["assets"]:ax.axvline(a["investWeek"],color=RED,alpha=.3,lw=.7)
        ax.set_title(f"{s.title()}: prespecified first confirmation seed {run['seed']}",fontsize=12);money_axis(ax,"y")
    axes[0].legend(fontsize=10.5,ncol=3);axes[-1].set_xlabel("Week, including collection and recovery runoff")
    finish(fig,out/"cash","Cash and commitments precede retention decisions","One prespecified world per scenario, not a median or success-selected trajectory. Red lines mark B/C commitments; gold marks hypothetical Beta update.")
    fig,axes=plt.subplots(1,2,figsize=(10.7,4))
    ar=meta["amortization"];xs=[a["futureCampaigns"] for a in ar]
    axes[0].plot(xs,[a["expectedNetResourceSavingCents"]/100 for a in ar],"o-",color=PURPLE);axes[0].axhline(0,color=RED,lw=1);axes[0].set_xscale("log",base=4);axes[0].set_xticks(xs,[str(x) for x in xs]);axes[0].set_title("Full optional-C resource return");axes[0].set_ylabel("Net resource saving, USD");axes[0].set_xlabel("Independent future campaigns")
    for key,label,color in [("input","Input quota",PURPLE),("output","Output quota",GREEN),("cpu","CPU quota","#c99b55")]:axes[1].plot(xs,[a["maximumFractionOfLifetimeCapacity"][key] for a in ar],"o-",label=label,color=color)
    axes[1].axhline(1,color=RED,lw=1,label="65-week capacity");axes[1].set_xscale("log",base=4);axes[1].set_xticks(xs,[str(x) for x in xs]);axes[1].set_title("Necessary lifetime quota bound");axes[1].set_xlabel("Independent future campaigns");axes[1].legend(fontsize=10.5)
    finish(fig,out/"campaign","A cheaper experiment can still fail full payback","256 paired campaign draws. Full C lifecycle is charged; aggregate quota feasibility still omits competition from ordinary paid work.")
    selected_stress={"humanReference":7167.1,"buyerValueMedian":15000,"prospectsMonthly":0,"commonError":.2,"tokenMultiplier":50,"collectionDelayWeeks":12,"retentionCostMultiplier":25,"paidLearningProbability":0,"rightsClearedProbability":.25,"betaBundleAbsorption":1,"assetLifetimeWeeks":13}
    cases=[c for c in sens["cases"] if selected_stress.get(c["parameter"])==c["value"]]
    fig,axes=plt.subplots(1,2,figsize=(10.7,6.2))
    yy=np.arange(len(cases));axes[0].barh(yy,[c["summary"]["network"]["profitCents"]["median"]/1e5 for c in cases],color=[RED if c["summary"]["network"]["profitCents"]["median"]<0 else PURPLE for c in cases]);axes[0].set_yticks(yy,[STRESS_NAMES[c["parameter"]]+" = "+f"{c['value']:g}" for c in cases],fontsize=10.5);axes[0].invert_yaxis();money_axis(axes[0]);axes[0].set_title("Central policy:\nadverse/null assumptions");axes[0].axvline(0,color="#403749",lw=.8)
    chosen=scale["capacitySelection"]["selections"]
    for i,(leads,record) in enumerate(sorted(chosen.items(),key=lambda z:int(z[0]))):
        d=record["holdout"]["contrast"]["differences"]["profitCents"];lo,hi=d["meanMC95"]
        axes[1].plot([lo/1e5,hi/1e5],[i,i],color=GREEN,lw=2);axes[1].plot(d["mean"]/1e5,i,"o",color=GREEN)
    axes[1].set_yticks(range(len(chosen)),[f"{leads} prospects/month\n{r['config']['concurrency']} slots; fourfold quotas" for leads,r in sorted(chosen.items(),key=lambda z:int(z[0]))],fontsize=11);axes[1].invert_yaxis();axes[1].axvline(0,color=RED,lw=1);money_axis(axes[1]);axes[1].set_title("Locked capacity choice:\nfresh holdout");axes[1].set_xlabel("Network minus same-price Beta, MC95")
    finish(fig,out/"sensitivity","Fragility and scale remain conditional","Left: fixed predeclared stresses, 20 paired worlds each. Right: 12 fresh holdout worlds per locked capacity choice; development rows excluded.")
