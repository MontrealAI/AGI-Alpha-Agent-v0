# SPDX-License-Identifier: Apache-2.0
import csv, json, os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/agi-alpha-capsule-mpl")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#C9C1D1",
        "axes.labelcolor": "#352442",
        "text.color": "#352442",
        "xtick.color": "#594C63",
        "ytick.color": "#594C63",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.titleweight": "bold",
        "grid.alpha": 0.18,
        "svg.fonttype": "none",
    }
)
purple = "#482365"
light = "#A28BB5"
green = "#287568"
red = "#AA4861"
summary = json.loads((ROOT / "economics/results/summary.json").read_text())
cases = {s["scenario"]: s for s in summary["scenarios"]}
c = cases["central"]


def save(name):
    plt.savefig(OUT / (name + ".pdf"), bbox_inches="tight")
    plt.savefig(OUT / (name + ".png"), dpi=180, bbox_inches="tight")
    plt.close()


names = [
    "Accepted\nrevenue",
    "Delivery +\npayment",
    "Acquisition",
    "Operations",
    "Additional\nsetup",
    "Full project\nreturn",
]
values = [
    c["accepted_revenue"],
    -c["direct_delivery_cost"] - c["payment_fees"],
    -c["acquisition_cost"],
    -c["fixed_operating_cost"],
    -c["additional_development"],
    c["full_project_return"],
]
fig, ax = plt.subplots(figsize=(9.6, 4.1))
running = 0
for i, v in enumerate(values):
    if i == 0 or i == len(values) - 1:
        bottom = 0
        color = purple
    else:
        bottom = running + v
        color = light
    ax.bar(i, abs(v), bottom=bottom, color=color, width=0.65)
    top = abs(v) + bottom
    ax.text(
        i, top + 1600, ("$" if v >= 0 else "-$") + f"{abs(v) / 1000:.1f}k", ha="center", fontsize=10, fontweight="bold"
    )
    if i < len(values) - 1:
        running += v
ax.set_xticks(range(len(names)), names)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
ax.set_ylim(0, 85000)
ax.set_ylabel("USD / 12-month modeled campaign")
ax.grid(axis="y")
ax.set_axisbelow(True)
ax.set_title("Positive complete economics under explicit commercial assumptions", loc="left", pad=17)
fig.text(
    0.125,
    -0.04,
    "$900 per accepted capsule · 96 attempts/year · 85% final acceptance · no observed sales",
    fontsize=9,
    color="#6A5A75",
)
save("commercial_waterfall")

fig, ax = plt.subplots(figsize=(9.5, 4.4))
pick = ["downside", "low_uptake", "funded_campaign_no_sales", "central", "price_pressure", "favorable"]
labels = [
    "Joint downside",
    "Low uptake",
    "Funded campaign: no sales",
    "Central conditional",
    "Price pressure: $600",
    "Favorable conditional",
]
vals = [cases[x]["full_project_return"] for x in pick]
y = np.arange(len(vals))
ax.barh(y, vals, color=[green if v > 0 else red for v in vals])
ax.set_yticks(y, labels)
ax.invert_yaxis()
ax.axvline(0, color="#352442", lw=0.8)
for j, v in enumerate(vals):
    ax.text(
        v + (1500 if v > 0 else -1500),
        j,
        f"${v:,.0f}",
        va="center",
        ha="left" if v > 0 else "right",
        fontsize=9,
        fontweight="bold",
    )
ax.set_xlim(-50000, 139000)
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"${x / 1000:.0f}k"))
ax.set_xlabel("USD / full modeled project after additional development")
ax.set_title("Demand and delivery quality can reverse the result", loc="left", pad=16)
ax.grid(axis="x")
ax.set_axisbelow(True)
save("scenario_results")

rows = (
    list(csv.DictReader((ROOT / "economics/results/price_volume_acceptance_grid.csv").open()))
    if (ROOT / "economics/results/price_volume_acceptance_grid.csv").exists()
    else []
)
if not rows:
    for p in (ROOT / "economics/results").glob("*grid*.csv"):
        rows = list(csv.DictReader(p.open()))
        break
print("grid fields", list(rows[0]) if rows else [])

fig, ax = plt.subplots(figsize=(9.4, 3.6))
labels = ["Indexing", "Hierarchical", "ML introduction", "Model validation"]
before = [29, 16, 14, 4]
total = [35, 45, 32, 21]
x = np.arange(4)
ax.bar(x - 0.18, before, width=0.34, color=light, label="Unchanged source before first failure")
ax.bar(x + 0.18, total, width=0.34, color=purple, label="Recovered: complete code path")
for i, n in enumerate(total):
    ax.text(i + 0.18, n + 0.9, str(n), ha="center", fontsize=10, fontweight="bold")
ax.set_xticks(x, labels)
ax.set_ylim(0, 54)
ax.set_ylabel("Accounted code cells")
ax.set_title("Four prospective recovery jobs; every code cell retained", loc="left", pad=14)
ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=1)
ax.grid(axis="y")
ax.set_axisbelow(True)
save("delivery_completion")

import importlib.util

spec = importlib.util.spec_from_file_location("economic_model", ROOT / "economics/run_economics.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
data = json.loads((ROOT / "economics/inputs.json").read_text())
central = m.expand_scenarios(data)["central"]
prices = np.linspace(400, 1400, 61)
qualities = np.linspace(0.25, 0.95, 51)
z = np.array(
    [
        [
            m.accounting(data, m.with_acceptance(central | {"price": float(p)}, float(q)))["full_project_return"] / 1000
            for p in prices
        ]
        for q in qualities
    ]
)
fig, ax = plt.subplots(figsize=(9.4, 4.5))
levels = np.linspace(-40, 90, 27)
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

cmap = LinearSegmentedColormap.from_list("surplus", ["#B76A7D", "#FAF7FB", "#482365"])
im = ax.contourf(
    prices, qualities * 100, z, levels=levels, cmap=cmap, extend="both", norm=TwoSlopeNorm(vmin=-40, vcenter=0, vmax=90)
)
line = ax.contour(prices, qualities * 100, z, levels=[0], colors=["#34203F"], linewidths=1.8)
ax.clabel(line, fmt={0: "Full project break-even"}, inline=True, fontsize=9)
ax.scatter([900], [85], c="white", edgecolors=purple, s=75, zorder=5)
ax.annotate(
    "Central assumption", xy=(900, 85), xytext=(990, 88), arrowprops={"arrowstyle": "-", "color": purple}, fontsize=9
)
ax.axhline(44.9, color="#8A324B", ls="--", lw=1)
ax.text(1380, 46.8, "44.9% external broad-corpus challenge", ha="right", fontsize=8, color="#763348")
ax.set_xlabel("Price per finally accepted capsule (USD)")
ax.set_ylabel("Final acceptance after correction / refund (%)")
ax.set_title("Quality and price jointly determine commercial viability", loc="left", pad=14)
fig.colorbar(im, ax=ax, label="Full modeled project return (USD thousands)")
fig.text(
    0.125,
    -0.025,
    "Eight attempted orders/month; acquisition and rejected-job work included. External rate is not a matched estimate.",
    fontsize=8.4,
)
save("commercial_frontier")
cash = list(csv.DictReader((ROOT / "economics/results/central_cash_ledger.csv").open()))
days = sorted({int(x["day"]) for x in cash})
last = {}
for row in cash:
    last[int(row["day"])] = row
fig, ax = plt.subplots(figsize=(9.4, 3.8))
d = [x for x in days if x <= 90]
ax.step(
    d,
    [float(last[x]["cumulative_cash_before_financing"]) + c["minimum_opening_cash"] for x in d],
    where="post",
    label="Cash including customer reserves",
    color=light,
    lw=2,
)
ax.step(
    d,
    [float(last[x]["unrestricted_cash_with_minimum_seed"]) for x in d],
    where="post",
    label="Unrestricted cash",
    color=purple,
    lw=2.2,
)
ax.set_xlabel("Modeled day from setup")
ax.set_ylabel("USD")
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
ax.set_title("Profitable delivery still needs opening cash", loc="left", pad=14)
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.grid(axis="y")
ax.set_axisbelow(True)
fig.text(
    0.125,
    -0.03,
    "Central minimum opening equity $6,760.92. Open-warranty receipts are fully restricted; reserves are not expenses.",
    fontsize=8.5,
)
save("cash_reserves")
print("figures ready")
