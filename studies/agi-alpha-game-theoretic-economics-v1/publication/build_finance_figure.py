# SPDX-License-Identifier: Apache-2.0
"""Cash-source figure for the prospectively selected fresh extension path."""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/"market/deployment-robustness/results-01/predeclared-representative-histories.json"
paired=next(r for r in json.loads(source.read_text())["pairedWorlds"] if r["config"]["investmentCostBasis"]=="adoption-only")
row=paired["arms"]["B"]
cost={}
for bill in row["histories"]["bills"]:
    cost[bill["category"]]=cost.get(bill["category"],0)+bill["amountCents"]
summary=row["summary"]
cash=summary["finalCashCents"]/100
profit=summary["profitCents"]/100
reserve=row["config"]["reserveCents"]/100
available=max(0,min(cash-reserve,profit))
assert round(available*100)==35100
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.spines.top":False,
 "axes.spines.right":False,"axes.edgecolor":"#C2B6CF","text.color":"#292035","pdf.fonttype":42})
fig,(ax,bx)=plt.subplots(1,2,figsize=(8.3,3.7),gridspec_kw={"width_ratios":[1.9,1]},layout="constrained")
labels=["Seed\ncapital","Collected\nreceipts","Delivery","Business","Adoption","Upkeep","Refund","Final\ncash"]
values=[1000,summary["grossCollectionsCents"]/100,-cost["delivery"]/100,-cost["business"]/100,
        -cost["capability"]/100,-cost["maintenance"]/100,-cost.get("refund",0)/100,cash]
colors=["#713EAD","#18776F"]+["#BD8D55"]*5+["#3C2A5B"]
current=0
for i,(v,label,color) in enumerate(zip(values,labels,colors)):
    if i==len(values)-1:
        bottom=0;height=v
    else:
        bottom=min(current,current+v);height=abs(v);current+=v
    ax.bar(i,height,bottom=bottom,color=color,width=.68,zorder=3)
    y=bottom+height
    ax.text(i,y+25,("$" if v>=0 else "−$")+f"{abs(v):,.2f}",ha="center",va="bottom",fontsize=7,rotation=0)
    if i<len(values)-2:
        ax.plot([i+.34,i+.66],[current,current],color="#9C8FA9",lw=.7)
ax.set_xticks(range(len(labels)),labels,fontsize=7.5)
ax.set_ylim(0,1910)
ax.set_ylabel("Simulated USD")
ax.set_title("One enterprise, one reconciled cash history",loc="left",fontsize=10,fontweight="bold")
ax.grid(axis="y",alpha=.15)
bx.axis("off")
bx.text(0,1,"What can fund the next step?",fontsize=10,fontweight="bold",transform=bx.transAxes)
items=[
 ("EXTERNAL START","$1,000.00","#713EAD"),
 ("OPERATING RECEIPTS − COSTS","720.00 − 369.00 USD","#18776F"),
 ("NET GENERATED FUNDS","$351.00","#18776F"),
 ("CASH AFTER ONE $200 RESERVE","$1,151.00","#3C2A5B"),
 ("GENERATED FUNDS BEFORE UNPRICED SEARCH","min(1,151.00, 351.00) = 351.00 USD","#18776F"),
]
for i,(label,value,color) in enumerate(items):
 y=.87-i*.165
 bx.text(0,y,label,fontsize=6.8,color="#796A88",transform=bx.transAxes)
 bx.text(0,y-.06,value,fontsize=10 if i!=4 else 8.5,color=color,transform=bx.transAxes)
bx.text(0,.01,"Unpriced discovery D reduces this ceiling.\nA next asset still needs tested value and cost.",
        fontsize=8,color="#4D405D",transform=bx.transAxes)
fig.supxlabel("Preselected seed 3001 · adoption-only account · week 8 adoption / week 9 availability / 35 later uses\n"
              "Initial seed is external. No additional injection. Full-history profit is −$10.52 after its one historical debit.",
              fontsize=8)
out=ROOT/"publication/figures"
fig.savefig(out/"finance.pdf",bbox_inches="tight")
fig.savefig(out/"finance.png",dpi=170,bbox_inches="tight")
plt.close(fig)
(ROOT/"publication/finance-figure-source.json").write_text(json.dumps({
 "basis":"SIMULATED_EXTENSION_PREDECLARED_PATH_BEFORE_UNPRICED_DISCOVERY",
 "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
 "seed":3001,"new_market_scenarios":0,
 "cash":cash,"operating_generation":profit,"reserve":reserve,"spendable_generated":available,
 "convention":"One liquidity reserve; no historical R&D in prospective operating-generation subtotal; historical cash/fullreturn still charged once."},indent=2)+"\n")
