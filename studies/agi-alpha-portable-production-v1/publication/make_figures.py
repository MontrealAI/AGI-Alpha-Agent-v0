# SPDX-License-Identifier: Apache-2.0
"""Render precise study figures from saved geometry and frozen economic results."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import cadquery as cq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)
INK = "#241337"
PURPLE = "#5D2C91"
VIOLET = "#9464C6"
LILAC = "#E7DBF3"
PALE = "#F8F5FC"
MUTED = "#6B6274"
TEAL = "#187B75"
AMBER = "#9A601F"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": "#C7BDD0",
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
    "axes.spines.right": False, "figure.facecolor": "white", "savefig.facecolor": "white",
    "pdf.fonttype": 42,
})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=.15)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", pad_inches=.15,
                metadata={"Title": name, "Author": "AGI ALPHA research study"})
    plt.close(fig)


def header(ax, kicker, title, subtitle=None):
    ax.text(0, 1.10, kicker.upper(), fontsize=9, weight="bold", color=PURPLE,
            transform=ax.transAxes)
    ax.text(0, 1.035, title, fontsize=16, weight="bold", transform=ax.transAxes)
    if subtitle:
        ax.text(0, -.14, subtitle, fontsize=9, color=MUTED, transform=ax.transAxes)


def chain():
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set(xlim=(0, 10), ylim=(0, 5)); ax.axis("off")
    ax.text(.05, 4.90, "THE CAPABILITY HYPOTHESIS", color=PURPLE, fontsize=10, weight="bold")
    ax.text(.05, 4.45, "A passing solid is one link in the productive chain.", fontsize=18, weight="bold")
    boxes = [
        (.05, 2.65, "01  CONSEQUENTIAL NEED", "Transfer work that is\ncurrently uneconomic", False),
        (3.45, 2.65, "02  BINDING LIMIT", "Lost requirements, relations\nand production authority", False),
        (6.85, 2.65, "03  ENABLING CAPABILITY", "Portable, executable\nproduction specification", True),
        (6.85, .80, "04  NEW ACTIVITY", "A recipient can produce\nan accepted outcome", False),
        (3.45, .80, "05  FIRST MILESTONE", "A buyer accepts and pays\nfor the useful instance", False),
        (.05, .80, "06  EXPANSION", "Qualified reuse unlocks\nmore viable work", False),
    ]
    for x,y,k,t,active in boxes:
        ax.add_patch(FancyBboxPatch((x,y), 3.05, 1.35, boxstyle="round,pad=.02,rounding_size=.12",
            linewidth=1.2, edgecolor=PURPLE if active else "#CDC2D8", facecolor=PALE))
        ax.text(x+.15,y+1.05,k,fontsize=8.2,weight="bold",color=PURPLE)
        ax.text(x+.15,y+.66,t,fontsize=10.5,va="center",linespacing=1.55)
        ax.text(x+.15,y+.14,"NOMINAL GEOMETRY: EXECUTED" if active else "NOT ESTABLISHED IN THIS STUDY",
                fontsize=7.7,weight="bold",color=TEAL if active else MUTED)
    for start,end in [((3.12,3.33),(3.40,3.33)),((6.52,3.33),(6.80,3.33)),
                      ((8.37,2.60),(8.37,2.20)),((6.80,1.48),(6.52,1.48)),
                      ((3.40,1.48),(3.12,1.48))]:
        ax.add_patch(FancyArrowPatch(start,end,arrowstyle="-|>",mutation_scale=13,color=VIOLET,lw=1.4))
    ax.text(.05,.18,"The artifact covers a narrow part of link 03. The remaining links cannot be inferred from geometric success.",
            fontsize=9,color=MUTED)
    save(fig,"01_chain")


def geometry():
    fig = plt.figure(figsize=(10.6, 7.4))
    fig.text(.025,.965,"EXECUTED NOMINAL CONSTRUCTION",fontsize=10,weight="bold",color=PURPLE)
    fig.text(.025,.922,"Six inspectable solids. No physical production claim.",fontsize=18,weight="bold",color=INK)
    entries = [
        ("construction_v1_2", "block_002", "Bored block", "Public source · nominal mm"),
        ("construction_v1_2", "pillow_003", "Pillow block", "Public source · nominal mm"),
        ("construction_v1_2", "countersink_019", "Countersink plate", "Public source · units unspecified"),
        ("fresh_confirmation", "fresh_mixed_plate", "Mixed plate", "Fresh request · mm specified"),
        ("fresh_confirmation", "fresh_metric_bracket", "Metric bracket", "Fresh request · mm specified"),
        ("fresh_confirmation", "fresh_thin_shim", "Thin shim", "Fresh request · mm specified"),
    ]
    for i,(group,case,title,subtitle) in enumerate(entries):
        row,col=divmod(i,3)
        ax=fig.add_axes([.02+col*.325,.52-row*.39,.31,.33],projection="3d",computed_zorder=False)
        shape=cq.importers.importStep(str(ROOT/"results"/group/case/"part.step")).val()
        bbox=shape.BoundingBox()
        vertices,triangles=shape.tessellate(max(max(bbox.xlen,bbox.ylen,bbox.zlen)*.001,.0005), .15)
        v=np.array([p.toTuple() for p in vertices]); tris=np.array(triangles)
        polygons=v[tris]
        norm=np.cross(polygons[:,1]-polygons[:,0],polygons[:,2]-polygons[:,0])
        norm=norm/np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12)
        light=np.array([.3,-.4,.85]);light/=np.linalg.norm(light)
        shade=.52+.48*np.abs(norm@light)
        base=np.array([.39,.21,.58]) if row==0 else np.array([.14,.44,.43])
        colors=np.concatenate([base[None,:]*shade[:,None]+(1-shade[:,None])*.28,np.ones((len(tris),1))],axis=1)
        poly=Poly3DCollection(polygons,facecolors=colors,edgecolors="none",linewidths=0,zsort="average")
        ax.add_collection3d(poly)
        spec=json.loads((ROOT/"results"/group/case/"feature_program.json").read_text())
        angle=np.linspace(0,2*np.pi,181)
        for h in spec["holes"]:
            radius=h.get("counterbore_diameter",h.get("countersink_diameter",h["diameter"]))/2
            ax.plot(h["x"]+radius*np.cos(angle),h["y"]+radius*np.sin(angle),
                    np.full_like(angle,bbox.zmax+.001*bbox.zlen),color="#EEE7F6",lw=.85,zorder=20)
        lo=v.min(axis=0);hi=v.max(axis=0);mid=(hi+lo)/2;span=hi-lo;extent=max(span)
        ax.set_xlim(mid[0]-extent*.58,mid[0]+extent*.58)
        ax.set_ylim(mid[1]-extent*.58,mid[1]+extent*.58)
        ax.set_zlim(mid[2]-extent*.28,mid[2]+extent*.28)
        ax.set_box_aspect((1,1,.48));ax.view_init(elev=34,azim=-54);ax.set_axis_off()
        ax.text2D(.5,.96,title,ha="center",transform=ax.transAxes,fontsize=11,weight="bold")
        ax.text2D(.5,.025,subtitle,ha="center",transform=ax.transAxes,fontsize=8.5,color=MUTED)
    fig.text(.025,.055,"Native source and primitive construction share OpenCascade; separate analytic volume checks add arithmetic evidence.",fontsize=8.8,color=MUTED)
    fig.text(.025,.026,"Each panel uses its own scale. Recipes, STEP files, feature tables and preserved failure records are included.",fontsize=8.8,color=MUTED)
    save(fig,"02_geometry")


def economics():
    d=json.loads((ROOT/"economics/results-r1/results.json").read_text())
    scenarios=["public_source_zero_value_control","adverse","central","favorable"]
    actual_scenarios=list(dict.fromkeys(r["scenario"] for r in d["results"]))
    scenarios=actual_scenarios
    def value(s,policy):
        return next(r["expected"]["profit"]["usd"] for r in d["results"]
                    if r["scenario"]==s and r["arrangement"]=="conventional_shared" and r["policy"]==policy)
    a=[value(s,"deliver_first_only") for s in scenarios]
    b=[value(s,"deliver_selectively") for s in scenarios]
    fig,ax=plt.subplots(figsize=(9.6,4.8));fig.subplots_adjust(top=.82,bottom=.22,left=.12,right=.98)
    x=np.arange(4)
    ax.bar(x-.18,a,.34,color=LILAC,label="First delivery only")
    ax.bar(x+.18,b,.34,color=PURPLE,label="Selective continuation")
    ax.axhline(0,color=INK,lw=.9)
    for xs,vals in [(x-.18,a),(x+.18,b)]:
        for xx,y in zip(xs,vals):
            ax.text(xx,y+(9 if y>0 else -14),f"{y:+.2f}",ha="center",va="bottom" if y>0 else "top",fontsize=9,weight="bold")
    ax.set_xticks(x,["Public-source\nzero-value control","Adverse\ncustom-work case","Central\ncustom-work case","Favorable\ncustom-work case"])
    ax.set_ylabel("Prospective expected profit (USD)");ax.set_ylim(-350,230)
    ax.yaxis.grid(True,color="#ECE6F1");ax.set_axisbelow(True)
    ax.legend(frameon=False,loc="upper left",fontsize=9,ncol=2)
    fig.text(.12,.96,"CONDITIONAL DELIVERY POLICIES",fontsize=9,color=PURPLE,weight="bold")
    fig.text(.12,.905,"Shared preparation can help. It creates no AI premium here.",fontsize=15,weight="bold")
    fig.text(.12,.055,"USD1,200 fee · USD2,000 supplied capital · proposed = conventional shared in every matched cell",fontsize=8.5,color=MUTED)
    fig.text(.12,.018,"Stopping returns USD0. Assumptions are uncalibrated; historical build cost is excluded from these prospective values.",fontsize=8.5,color=MUTED)
    save(fig,"03_economics")


def capital():
    fig,ax=plt.subplots(figsize=(9.6,4.9));fig.subplots_adjust(top=.80,bottom=.17,left=.26,right=.78)
    labels=["Acquisition","Commercial preparation","Base construction obligations","One correction","Deposit processing","Failed-refund administration","Minimum unrestricted reserve"]
    amounts=[75,600,540,155,12,10,150]
    y=np.arange(7)
    ax.barh(y,amounts,color=[LILAC,PURPLE,VIOLET,VIOLET,LILAC,LILAC,TEAL],height=.65)
    for i,x in enumerate(amounts):ax.text(x+8,i,f"USD{x:,}",va="center",fontsize=9.5,weight="bold")
    ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlim(0,720);ax.set_xticks([0,200,400,600]);ax.set_xlabel("Reserved cash before the first booked attempt (USD)")
    ax.xaxis.grid(True,color="#EEE8F3");ax.set_axisbelow(True)
    fig.text(.045,.96,"FINANCEABILITY GATE",fontsize=9,color=PURPLE,weight="bold")
    fig.text(.045,.895,"USD1,542 unrestricted capital is required up front.",fontsize=17,weight="bold")
    fig.text(.80,.64,"$600",fontsize=24,color=AMBER,weight="bold")
    fig.text(.80,.54,"Refundable\ncustomer deposit",fontsize=10,color=AMBER,linespacing=1.5)
    fig.text(.80,.36,"RESTRICTED\nNo credit against\nthis requirement",fontsize=9,color=MUTED,linespacing=1.6)
    fig.text(.045,.035,"Frozen cost and reserve assumptions. Initial owner capital is hypothetical; no payment or funding commitment occurred.",fontsize=8.7,color=MUTED)
    save(fig,"04_capital")


def scale():
    ramp=np.array([.005,.01,.02,.04,.07,.1,.15,.2,.25,.3]);population=17163;benefit=250
    x=np.arange(1,11);cum=np.cumsum(ramp)*population*benefit
    required=1e9/cum[-1]
    fig,ax=plt.subplots(figsize=(9.6,4.9));fig.subplots_adjust(top=.80,bottom=.21,left=.10,right=.82)
    ax.plot(x,cum*required/1e6,color=VIOLET,lw=2.5,ls="--")
    ax.plot(x,cum*20/1e6,color=PURPLE,lw=3,marker="o",ms=4)
    ax.fill_between(x,0,cum*20/1e6,color=LILAC)
    ax.axhline(1000,color="#B7A7C6",lw=.8)
    ax.text(10.15,1000,"USD1bn\n203.55 outcomes\nper active shop/year",va="center",fontsize=9,color=VIOLET,linespacing=1.5)
    ax.text(10.15,98.258175,"USD98.26m\n20 outcomes\nper active shop/year",va="center",fontsize=9,color=PURPLE,linespacing=1.5)
    ax.set(xlim=(1,10),ylim=(0,1120),xlabel="Year of the assumed adoption ramp",ylabel="Cumulative net customer benefit (USD million)")
    ax.set_xticks(x);ax.set_yticks([0,250,500,750,1000]);ax.yaxis.grid(True,color="#EEE8F3");ax.set_axisbelow(True)
    fig.text(.10,.96,"SCALE IS A THRESHOLD, NOT A VALUATION",fontsize=9,color=PURPLE,weight="bold")
    fig.text(.10,.895,"Four million accepted outcomes are required at USD250 each.",fontsize=15,weight="bold")
    fig.text(.10,.075,"Population anchor: 17,163 U.S. machine-shop establishments (2022 Census). Eligibility is unvalidated.",fontsize=8.5,color=MUTED)
    fig.text(.10,.035,"Adoption rises from 0.5% to 30% over ten years. All uptake and incremental-value assumptions remain unobserved.",fontsize=8.5,color=MUTED)
    save(fig,"05_scale")


if __name__ == "__main__":
    chain();geometry();economics();capital();scale()
    print(json.dumps({"figures":sorted(p.name for p in OUT.iterdir())}))
