# SPDX-License-Identifier: Apache-2.0
"""Render scientific figures directly from the frozen commercial results."""

from pathlib import Path
import json
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "publication" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
R = ROOT / "economics" / "final_results"
CONF = json.loads((R / "confirmation.json").read_text())
S = CONF["summary"]
PURPLE, TEAL, INK, AMBER, MUTED = "#622dc7", "#088b86", "#211335", "#b35b17", "#6d6479"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.edgecolor": "#d8d0e2",
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": INK,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def finish(fig, name):
    fig.savefig(OUT / (name + ".png"), dpi=180, bbox_inches="tight", pad_inches=0.22)
    fig.savefig(OUT / (name + ".pdf"), bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)


fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.6), gridspec_kw={"width_ratios": [1, 1.12]})
vals = [S["human_reference"]["mean"], S["price"]["mean"], S["complete_cost_per_accepted"]["mean"]]
labels = ["Human-service\nreference", "Selected\nservice price", "Complete cost\nper accepted pack"]
bars = axes[0].bar(range(3), vals, color=["#c6b5e4", PURPLE, TEAL], width=0.6)
axes[0].set_xticks(range(3), labels)
axes[0].set_ylim(0, 1340)
axes[0].set_ylabel("CAD per accepted package")
axes[0].set_title("A scoped service, a substantial modeled spread", loc="left", fontsize=11, pad=20)
for b, v in zip(bars, vals):
    axes[0].text(b.get_x() + b.get_width() / 2, v + 30, f"${v:,.0f}", ha="center", weight="bold", fontsize=13)
parts = [
    ("Delivery & recovery", S["delivery_cost"]["mean"]),
    ("Acquisition", S["acquisition_cost"]["mean"]),
    ("Business overhead", S["fixed_cost"]["mean"]),
    ("Launch & payment fees", S["launch_cost"]["mean"] + S["payment_cost"]["mean"]),
    ("Unpaid invoices", S["bad_debt"]["mean"]),
    ("Operating profit", S["operating_profit"]["mean"]),
]
ys = np.arange(len(parts))
axes[1].barh(ys, [v / 1000 for _, v in parts], color=["#b5a5d4"] * 5 + [PURPLE], height=0.6)
axes[1].set_yticks(ys, [k for k, _ in parts])
axes[1].invert_yaxis()
axes[1].set_xlim(0, 49)
axes[1].set_xlabel("CAD thousands over 12 months")
axes[1].set_title(f"Allocation of ${S['revenue']['mean']:,.0f} earned service revenue", loc="left", fontsize=11, pad=20)
for y, (_, v) in zip(ys, parts):
    axes[1].text(v / 1000 + 0.7, y, f"${v:,.0f}", va="center", fontsize=9)
fig.text(
    0.02,
    -0.025,
    "Conditional simulation; 2,400 fresh worlds. Actual service collections: CAD 0.\nCost includes failed delivery, all invitations, overhead, launch, payment fees and bad debt. Human reference is an estimate.",
    fontsize=9,
    color=MUTED,
)
fig.tight_layout(w_pad=3)
finish(fig, "economics")

policies = json.loads((R / "policy_robustness.json").read_text())["comparisons"]
invoice = [r for r in policies if r["policy"]["arrangement"] == "acceptance_invoice"]
deposit = [r for r in policies if r["policy"]["arrangement"] == "conditional_deposit"]
x = [r["policy"]["price_ratio"] * 100 for r in invoice]
fig, ax = plt.subplots(figsize=(10.5, 4.5))
ax.plot(
    x,
    [r["fresh_conditional"]["operating_profit"]["mean"] / 1000 for r in invoice],
    "o-",
    color=PURPLE,
    lw=2.4,
    label="Central assumptions · payment after acceptance",
)
ax.plot(
    x,
    [r["fresh_conditional"]["operating_profit"]["mean"] / 1000 for r in deposit],
    "s--",
    color="#b9a1e4",
    lw=1.5,
    label="Central assumptions · conditional deposit",
)
ax.plot(
    x,
    [r["uncertain_parameters"]["operating_profit"]["mean"] / 1000 for r in invoice],
    "D-",
    color=TEAL,
    lw=2,
    label="Broader parameter uncertainty · payment after acceptance",
)
ax.axhline(0, color="#c9bfcf", lw=1)
ax.set_xlabel("Service price as a percentage of estimated human-service reference")
ax.set_ylabel("Mean annual operating profit · CAD thousands")
ax.set_xticks(x)
ax.set_ylim(-7, 49)
ax.annotate(
    "Frozen central selection\n80% = CAD 874.35",
    (80, 40.917),
    xytext=(83, 45),
    fontsize=10,
    color=PURPLE,
    arrowprops={"arrowstyle": "-", "color": PURPLE},
    ha="center",
)
ax.annotate(
    "65% performs better under\nthe declared broad priors",
    (65, 18.228),
    xytext=(65, 8),
    fontsize=10,
    color=TEAL,
    arrowprops={"arrowstyle": "-", "color": TEAL},
    ha="center",
)
ax.legend(loc="upper left", fontsize=8.5, frameon=False)
fig.text(
    0.08,
    -0.035,
    "Buyer participation changes with price, perceived reliability, in-house alternatives and budgets.\nThis comparison identifies the best policy within a tested family and assumptions; it does not identify a global market optimum.",
    fontsize=9,
    color=MUTED,
)
fig.tight_layout()
finish(fig, "pricing")

stresses = {r["name"]: r["result"] for r in json.loads((R / "sensitivity.json").read_text())}
names = [
    ("central", "Central assumptions"),
    ("low_demand_4", "Only 4 qualified invitations/month"),
    ("matched_human_hours_8", "Equivalent incumbent needs 8 hours"),
    ("matched_human_hours_12", "Equivalent incumbent needs 12 hours"),
    ("matched_human_hours_32", "32-hour reference; buyer budgets fixed"),
    ("weak_trust_075", "Buyer confidence falls to 75%"),
    ("quality_075", "Delivery and perceived quality 75%"),
    ("warranty_20pct_at_500", "20% repairs at CAD 500 each"),
    ("all_delivery_costs_3x", "All delivery costs ×3"),
    ("all_delivery_costs_10x", "All delivery costs ×10"),
    ("model_price_10.0x", "Model token prices ×10"),
    ("strong_inhouse_competition", "80% have in-house capability"),
]
fig, ax = plt.subplots(figsize=(10.4, 5.7))
y = np.arange(len(names))
values = [stresses[n]["operating_profit"]["mean"] / 1000 for n, _ in names]
low = [stresses[n]["operating_profit"]["p05"] / 1000 for n, _ in names]
high = [stresses[n]["operating_profit"]["p95"] / 1000 for n, _ in names]
ax.barh(y, values, color=[PURPLE if v >= 0 else AMBER for v in values], height=0.57, alpha=0.9)
ax.hlines(y, low, high, color=INK, lw=1)
ax.plot(low, y, "|", color=INK, ms=5)
ax.plot(high, y, "|", color=INK, ms=5)
ax.set_yticks(y, [label for _, label in names], fontsize=9)
ax.invert_yaxis()
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("Annual operating profit · CAD thousands")
ax.set_xlim(-10, 56)
for yy, v, hi in zip(y, values, high):
    ax.text(max(hi, 0) + 0.8, yy, f"{v:+.1f}", va="center", fontsize=9)
fig.text(
    0.02,
    -0.02,
    "Bars: mean across 600 paired worlds; lines: simulated 5th–95th percentiles. Failures and losing cases are preserved.\nSensitivity keeps the frozen policy; it does not reprice each stress after seeing its outcome.",
    fontsize=9,
    color=MUTED,
)
fig.tight_layout()
finish(fig, "sensitivity")

annual = json.loads((R / "annual_worlds.json").read_text())["operating_profit"]
u = json.loads((R / "parameter_uncertainty.json").read_text())["summary"]["operating_profit"]
fig, ax = plt.subplots(figsize=(9.8, 3.8))
ax.hist(np.array(annual) / 1000, bins=34, color=PURPLE, alpha=0.85)
ax.set_xlabel("Annual operating profit · CAD thousands")
ax.set_ylabel("Simulated worlds")
ax.set_title("Fresh confirmation holds the assumptions fixed", loc="left", fontsize=14, pad=15)
ax.text(
    0.02,
    0.97,
    f"2,400 worlds · 5th–95th percentile\nCAD {S['operating_profit']['p05']:,.0f} to {S['operating_profit']['p95']:,.0f}",
    transform=ax.transAxes,
    va="top",
    fontsize=10,
)
fig.text(
    0.08,
    -0.03,
    f"Changing uncertain quality, demand and cost assumptions widens the range to CAD {u['p05']:,.0f} to {u['p95']:,.0f}.\nThese are scenario distributions, not empirical confidence intervals or probabilities of business success.",
    fontsize=9,
    color=MUTED,
)
fig.tight_layout()
finish(fig, "confirmation")
shutil.copy2(ROOT / "technical" / "delivery" / "asset_map.png", OUT / "asset_map.png")
print(json.dumps({"figures": sorted(p.name for p in OUT.iterdir())}))
