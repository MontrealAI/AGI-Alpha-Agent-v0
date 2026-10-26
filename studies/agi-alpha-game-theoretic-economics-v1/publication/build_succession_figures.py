# SPDX-License-Identifier: Apache-2.0
"""Plot every declared robustness grid row and its preselected stress slice."""
from pathlib import Path
import csv
import hashlib
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"market/deployment-robustness/results-01/summary.json"
summary=json.loads(SOURCE.read_text())
rows=summary["scenarios"]
OUT=ROOT/"publication/figures"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.titlesize":10,
 "axes.labelsize":9,"axes.spines.top":False,"axes.spines.right":False,
 "figure.facecolor":"white","text.color":"#2D203E","pdf.fonttype":42})
integrations=[0,250,500,1000]
arrivals=[.1,.25,.5]
def select(integration,arrival,choice,basis):
    return next(r for r in rows if r["scenario"]==f"robust-main-i{integration}-a{arrival}-{choice}-{basis}")
def profit(r):return r["arms"]["B"]["profitBeforeUnpricedDiscoveryCents"]
def save(fig,name):
    fig.savefig(OUT/(name+".pdf"),bbox_inches="tight")
    fig.savefig(OUT/(name+".png"),dpi=170,bbox_inches="tight")
    plt.close(fig)
fig,axes=plt.subplots(2,2,figsize=(7.4,4.6),layout="constrained")
norm=TwoSlopeNorm(vmin=-550,vcenter=0,vmax=200)
for i,basis in enumerate(["adoption-only","full-history"]):
 for j,choice in enumerate(["deterministic","logit"]):
    ax=axes[i,j]
    matrix=np.array([[profit(select(k,a,choice,basis))["mean"]/100 for k in integrations] for a in arrivals])
    im=ax.imshow(matrix,cmap="PRGn",norm=norm,aspect="auto")
    for (y,x),v in np.ndenumerate(matrix):
        ax.text(x,y,f"{v:,.1f}",ha="center",va="center",color="white" if v < -350 or v>145 else "#271132",fontsize=8.5)
    ax.set_xticks(range(4),["$0","$2.50","$5","$10"])
    ax.set_yticks(range(3),[".10",".25",".50"])
    ax.set_xlabel("Assumed buyer integration cost")
    ax.set_ylabel("New-work arrival / buyer / week")
    ax.set_title(("Prospective" if i==0 else "Full history")+" · "+choice,loc="left",fontweight="bold")
fig.colorbar(im,ax=axes,shrink=.7,pad=.02,label="Mean B profit / simulated USD, before unpriced discovery D")
save(fig,"succession-grid")

variants=[
 ("upkeep-usd2","Upkeep $2/week"),("upkeep-usd5","Upkeep $5/week"),
 ("collections-week6","Collections at 6 weeks"),("collections-week13","Collections at 13 weeks"),
 ("cheap-ai","Cheaper AI"),("cheap-human","Cheaper humans"),("undercut","Undercut rule"),
 ("quality-shock","Quality shock"),("failed-integration","Immediate integration failure"),
 ("dissatisfaction","Dissatisfaction")]
fig,axes=plt.subplots(1,2,figsize=(7.4,4.4),layout="constrained",sharey=True)
for ax,integration in zip(axes,[0,500]):
 selected=[select(integration,.5,"logit","adoption-only")]+[
  next(r for r in rows if r["scenario"]==f"robust-stress-{v}-i{integration}-a0.5-logit-adoption-only")
  for v,_ in variants]
 means=np.array([profit(r)["mean"]/100 for r in selected])
 errors=np.array([(profit(r)["meanInterval95"][1]-profit(r)["mean"])/100 for r in selected])
 colors=["#176C68" if x>0 else "#915B9E" for x in means]
 ax.barh(range(len(selected)),means,color=colors,height=.62,xerr=errors,error_kw={"lw":.7,"capsize":2})
 ax.axvline(0,color="#40304E",lw=.8)
 ax.set_title("Integration USD "+str(integration/100),loc="left",fontweight="bold")
 ax.set_xlabel("Mean B profit / simulated USD\nbefore unknown discovery D")
 ax.set_yticks(range(len(selected)),["Reference"]+[label for _,label in variants],fontsize=8)
 ax.invert_yaxis();ax.grid(axis="x",alpha=.15)
save(fig,"succession-stress")

fields=["scenario","basis","choice","integration_usd","arrival",
 "B_mean_profit_before_D_usd","B_profit_low95","B_profit_high95","B_profitable_worlds",
 "B_minus_A_mean_before_D_usd","B_minus_A_low95","B_minus_A_high95","B_adopted_worlds",
 "terminal_G_mean_before_D_usd","terminal_G_median_before_D_usd","G_positive_worlds",
 "G_positive_during_service_worlds","actual_second_investments"]
csv_path=ROOT/"publication/succession-complete-table.csv"
with csv_path.open("w",newline="") as out:
 w=csv.DictWriter(out,fieldnames=fields);w.writeheader()
 for r in rows:
  c=r["config"];b=r["arms"]["B"];p=profit(r);d=r["causalBeforeUnpricedDiscovery"]["B_minus_A_profitCents"]
  g=b["terminalFundingCeilingBeforeUnpricedDiscoveryCents"]
  w.writerow(dict(zip(fields,[r["scenario"],c["investmentCostBasis"],c["choiceModel"],c["integrationCents"]/100,
   c["arrivalProbability"],p["mean"]/100,*[v/100 for v in p["meanInterval95"]],
   round(b["positiveModeledProfitBeforeUnpricedDiscoveryRate"]*24),
   d["mean"]/100,*[v/100 for v in d["meanInterval95"]],round(b["investmentRate"]*24),
   g["mean"]/100,g["median"]/100,round(b["positiveTerminalFundingCeilingRate"]*24),
   round(b["positiveDuringServiceFundingCeilingRate"]*24),0])))
(ROOT/"publication/succession-figure-manifest.json").write_text(json.dumps({
 "schema":"agi-alpha-succession-publication-inputs/v1",
 "summary_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 "freeze_sha256":summary["freezeSHA256"],
 "figures":[{"file":name,"sha256":hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
            for name in ["succession-grid.pdf","succession-grid.png","succession-stress.pdf","succession-stress.png"]],
 "all_rows_csv_sha256":hashlib.sha256(csv_path.read_bytes()).hexdigest(),
 "no_new_scenarios":True,"cost_boundary":"BEFORE_UNPRICED_SECOND_ASSET_DISCOVERY"},indent=2)+"\n")
print(json.dumps({"configurations":len(rows),"figures":4,"complete_table_rows":len(rows)}))
