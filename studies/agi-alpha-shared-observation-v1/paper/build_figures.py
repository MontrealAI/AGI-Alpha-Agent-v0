# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/figures"
OUT.mkdir(exist_ok=True)
NAVY, TEAL, RED, GOLD, GRAY = "#16324a", "#087f8c", "#b33d46", "#c18b31", "#657587"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.labelcolor": NAVY, "text.color": NAVY,
                     "axes.titleweight": "bold", "savefig.bbox": "tight", "figure.facecolor": "white"})


def save(fig, name):
    fig.savefig(OUT / (name + ".pdf"))
    fig.savefig(OUT / (name + ".png"), dpi=180)
    plt.close(fig)


origin = json.loads((ROOT / "results/origin.json").read_text())
mission = json.loads((ROOT / "data/origin.json").read_text())
summary = json.loads((ROOT / "evaluation/confirmation-v1/summary.json").read_text())
econ = json.loads((ROOT / "results/economics/economic_results.json").read_text())
compact = json.loads((ROOT / "results/economics/summary.json").read_text())

fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"width_ratios": [1.2, 1]})
op = origin["operators"][0]
coast = mission["operators"][0]["actions"][0]["risk_by_state"]
risks = [sum(p * q for p, q in zip(b["posterior"], coast)) for b in op["branches"]]
x = np.arange(3)
axs[0].bar(x - .18, risks, .36, color=GOLD, label="If coast")
axs[0].bar(x + .18, [b["risk"] for b in op["branches"]], .36, color=TEAL, label="Selected action")
axs[0].axhline(.0001, color=RED, ls="--", lw=1.5, label="Original risk limit")
axs[0].set_yscale("log")
axs[0].set_ylim(1e-7, .003)
axs[0].set_xticks(x, ["Clearer\n73.0%", "Closer\n21.8%", "Timeout\n5.2%"])
axs[0].set_ylabel("Conditional probability in the finite model")
axs[0].set_title("Adverse information preserves the fallback")
axs[0].legend(fontsize=8, loc="upper left")
axs[1].bar(np.arange(3) - .18, [o["baseline_cost"] for o in origin["operators"]], .36, color=GRAY, label="Baseline action")
axs[1].bar(np.arange(3) + .18, [o["contingent_cost"] for o in origin["operators"]], .36, color=TEAL, label="Contingent action")
axs[1].set_xticks(np.arange(3), ["Operator 1", "Operator 2", "Operator 3"])
axs[1].set_ylabel("Expected action expense (assumed USD)")
axs[1].set_title("Acquisition and fees are additional")
axs[1].legend(fontsize=8)
fig.tight_layout(w_pad=2.5)
save(fig, "origin")

fig, axs = plt.subplots(1, 2, figsize=(10, 3.7), gridspec_kw={"width_ratios": [1.1, 1]})
cats = list(summary["categories"].values())
labels = ["Shared information", "Zero / negative", "Adverse information", "Deadlines", "Prerequisites", "Withdrawal"]
y = np.arange(6)
axs[0].barh(y, [c["accepted"] for c in cats], color=TEAL, label="Valid plan")
axs[0].barh(y, [c["refused"] for c in cats], left=[c["accepted"] for c in cats], color=RED, label="Correct refusal")
axs[0].set_yticks(y, labels)
axs[0].invert_yaxis()
axs[0].set_xlim(0, 8.6)
axs[0].set_xlabel("Fresh synthetic missions")
axs[0].set_title("48 / 48 match the independent reference")
axs[0].legend(fontsize=8, loc="lower right")
rows = [r for r in summary["rows"] if r["observation_accepted"]]
vals = [r["total_value_of_information"] for r in rows]
axs[1].scatter(range(len(vals)), sorted(vals), c=[TEAL if v > 1e-8 else RED if v < -1e-8 else GRAY for v in sorted(vals)], s=35)
axs[1].axhline(0, color=GRAY, lw=1)
axs[1].set_xlabel("Valid cases, sorted by modeled value")
axs[1].set_ylabel("Gross information value (assumed USD)")
axs[1].set_title("Validity does not imply useful purchase")
fig.tight_layout(w_pad=2.5)
save(fig, "confirmation")

fig, ax = plt.subplots(figsize=(9.5, 3.7))
items = [("Fees\ncollected", compact["factorial"]["T1_A1_joint"]["service_collections"]),
         ("Quote", -compact["expected_A_components"]["quotes_all_invitations"]),
         ("Construct /\ncorrect", -compact["expected_A_components"]["construction_preparation_correction"]),
         ("Deliver", -compact["expected_A_components"]["per_operator_delivery"]),
         ("Reject /\nhandle", -compact["expected_A_components"]["failed_or_rejected_handling"]),
         ("Support", -compact["expected_A_components"]["support"]),
         ("Shared\nfailure", -compact["expected_A_components"]["common_failure_sunk_acquisition"])]
running = 0
for i, (label, value) in enumerate(items):
    ax.bar(i, abs(value), bottom=running if value >= 0 else running + value, color=TEAL if value >= 0 else GRAY, width=.7)
    running += value
    ax.text(i, max(running, running - value) + 3, f"{value:+.2f}", ha="center", fontsize=9)
ax.bar(len(items), running, color=GOLD, width=.7)
ax.text(len(items), running + 3, f"{running:.2f}", ha="center", fontsize=9)
ax.set_xticks(range(len(items) + 1), [x[0] for x in items] + ["Operating\nprofit"])
ax.set_ylim(0, 185)
ax.set_ylabel("Expected USD per offered originating cohort")
ax.set_title("Complete cash operating costs leave a narrow conditional margin")
fig.tight_layout()
save(fig, "economics")

prices = sorted({r["package_fee"] for r in econ["sensitivity"]})
acq = sorted({r["acquisition"] for r in econ["sensitivity"]})
matrix = np.array([[next(r["profit"] for r in econ["sensitivity"] if r["acquisition"] == k and r["package_fee"] == f) for f in prices] for k in acq])
fig, ax = plt.subplots(figsize=(7.5, 4.0))
im = ax.imshow(matrix, cmap="RdYlGn", vmin=-160, vmax=320, aspect="auto")
for i in range(len(acq)):
    for j in range(len(prices)):
        cell = next(r for r in econ["sensitivity"] if r["acquisition"] == acq[i] and r["package_fee"] == prices[j])
        text = f"${matrix[i,j]:.0f}" if cell["launch_probability"] else "Decline\n−$6 quote"
        ax.text(j, i, text, ha="center", va="center", fontsize=10, color=NAVY)
ax.set_xticks(range(len(prices)), [f"${f:.0f}" for f in prices])
ax.set_yticks(range(len(acq)), [f"${k:.0f}" for k in acq])
ax.set_xlabel("Fee per participating operator (assumed)")
ax.set_ylabel("Shared acquisition cost (assumed)")
ax.set_title("Both the provider margin and voluntary participation must hold")
fig.colorbar(im, ax=ax, label="Expected operating profit, before B / C")
fig.tight_layout()
save(fig, "feasibility")

fig, ax = plt.subplots(figsize=(8.5, 3.6))
path = compact["all_commit_accept_pay_branch"]["cash_path"]
ax.plot(range(5), [r["cash"] for r in path], "o-", color=NAVY, label="Cash balance")
ax.plot(range(5), [r["available_funds"] for r in path], "s-", color=TEAL, label="Available after obligations / reserves")
ax.axhline(1500, color=GRAY, ls=":", label="Seed capital, not revenue")
ax.set_xticks(range(5), ["Quote", "Deposits", "Acquire /\nprepare", "Accept /\nsettle", "Support\nsettled"])
ax.set_ylabel("USD in the all-accept / all-pay illustration")
ax.set_ylim(0, 2400)
ax.set_title("Refundable deposits do not become freely spendable profit")
ax.legend(fontsize=8, loc="upper right")
fig.tight_layout()
save(fig, "liquidity")

fig, ax = plt.subplots(figsize=(8, 3.5))
gains = [5, 10, 20, 30]
for c, color, label in [(0, TEAL, "B = $180"), (240, GOLD, "B + optional C = $420")]:
    values = [next(r["minimum_uses_for_strict_positive_increment"] for r in compact["retention_thresholds"] if r["assumed_cash_saving_per_fresh_use"] == g and r["C_optional"] == c) for g in gains]
    ax.plot(gains, values, "o-", color=color, label=label)
    for g, v in zip(gains, values):
        ax.annotate(str(v), (g, v), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=9)
ax.set_xticks(gains, [f"${g}" for g in gains])
ax.set_xlabel("Assumed cash saving per compatible fresh mission, before $2 upkeep")
ax.set_ylabel("Uses for strictly positive incremental value")
ax.set_title("Retention depends on measured reuse savings")
ax.legend(fontsize=9)
fig.tight_layout()
save(fig, "retention")
print("Generated six scientific figures as PDF and PNG.")
