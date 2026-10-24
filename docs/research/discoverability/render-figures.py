# SPDX-License-Identifier: Apache-2.0
"""Render both retained campaigns; no workload is rerun by this script."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
HERE=Path(__file__).resolve().parent
reports=[json.loads((HERE/"evidence"/name).read_text()) for name in
         ["load-first-report.json","load-qualification-report.json"]]
names=["workbench-inherited","workbench-non-inheriting","centralized-direct"]
rows=[[next(x for x in r["results"] if x["count"]==100 and x["mode"]==n) for n in names] for r in reports]
labels=["Workbench\nwith reuse","Workbench\nfresh construction","Centralized\ndirect solver"]
colors=["#7951ad","#aa93c5","#476b83"]
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,
 "axes.spines.right":False,"axes.labelcolor":"#30243c","text.color":"#30243c","xtick.color":"#30243c",
 "ytick.color":"#62596d","axes.edgecolor":"#c9c1d1","svg.hashsalt":"discoverability-20261022-v1"})
fig,axes=plt.subplots(1,2,figsize=(10.8,4.3),layout="constrained")
vals=[x["compilerLogicalUnits"]/1000 for x in rows[0]]
assert vals==[x["compilerLogicalUnits"]/1000 for x in rows[1]]
bars=axes[0].bar(range(3),vals,color=colors,width=.62,zorder=3)
axes[0].bar_label(bars,labels=[f"{v:,.1f}" for v in vals],padding=5,fontsize=10)
axes[0].set_title("Less counted construction work",loc="left",fontsize=12,fontweight="bold",pad=16)
axes[0].set_ylabel("Compiler logical units (thousands)")
axes[0].set_ylim(0,max(vals)*1.22)
for i,group in enumerate(rows):
 values=[x["elapsedMs"]/1000 for x in group]
 positions=[j+(-.18 if i==0 else .18) for j in range(3)]
 bars=axes[1].bar(positions,values,width=.33,color=colors,alpha=1 if i==0 else .55,
                  hatch=None if i==0 else "//",edgecolor=colors,zorder=3)
 axes[1].bar_label(bars,labels=[f"{v:.2f}" for v in values],padding=4,fontsize=9)
axes[1].set_ylim(0,8.6)
axes[1].set_title("Timing advantage is unstable",loc="left",fontsize=12,fontweight="bold",pad=16)
axes[1].set_ylabel("Elapsed seconds / 100 missions")
axes[1].legend(handles=[Patch(facecolor="#6c6377",label="First campaign"),
                        Patch(facecolor="#b5adbc",edgecolor="#6c6377",hatch="//",label="Source qualification")],
               loc="upper left",frameon=False,fontsize=8)
for ax in axes:
 ax.set_xticks(range(3),labels)
 ax.set_axisbelow(True)
 ax.grid(axis="y",alpha=.2)
fig.suptitle("Same quality target · 34 digital + 33 mixture + 33 network missions",fontsize=12)
out=HERE/"figures"
out.mkdir(exist_ok=True)
fig.savefig(out/"load-results.png",dpi=240,bbox_inches="tight",metadata={"Software":"Discoverability Compiler figure script"})
fig.savefig(out/"load-results.svg",bbox_inches="tight",metadata={"Date":None})
