# SPDX-License-Identifier: Apache-2.0
"""Generate publication figures from the audited data, without network access."""

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = Path(__file__).resolve().parent
D = json.loads((P / "data/audited.json").read_text())


def save(fig, name):
    fig.tight_layout()
    fig.savefig(P / f"figures/{name}.pdf", bbox_inches="tight")
    fig.savefig(P / f"figures/{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


labels = ["Full LP", "Selection only", "Invalid criticism", "Verified correction"]
keys = ["strong_lp", "selection_only", "irrelevant_criticism", "corrective"]
x = np.arange(4)
fig, ax = plt.subplots(figsize=(7.4, 3.8))
w = 0.34
for i, v in enumerate(["pilot-v1", "pilot-v2"]):
    y = [D["raw_reaggregated"][v][k]["accepted"] for k in keys]
    bars = ax.bar(x + (i - 0.5) * w, y, w, label=("First version", "Revised version")[i])
    ax.bar_label(bars, padding=3)
ax.set_xticks(x, labels)
ax.set_ylim(0, 42)
ax.set_ylabel("Accepted schedules / 36 fixed tasks")
ax.legend(loc="upper center", ncol=2)
save(fig, "acceptance")
fig, ax = plt.subplots(figsize=(7.4, 3.6))
y = [D["raw_reaggregated"]["pilot-v2"][k]["deployment_cpu_per_attempt"] for k in keys]
bars = ax.barh(labels, y)
ax.bar_label(bars, fmt="%.4f", padding=4)
ax.set_xlim(0, max(y) * 1.24)
ax.invert_yaxis()
ax.set_xlabel("Measured deployment CPU proxy per attempted task (seconds)")
save(fig, "cpu")
rows = D["cost_reconciliation"]["rows"]["instrument"]
b = D["budget_repair"]
snapshots = [rows["before"], rows["after"], b["after"]]
labels2 = ["Earlier checkpoint", "Late-cost reconciliation", "Budget-repair receipt"]
fig, ax = plt.subplots(figsize=(7.4, 3.8))
x = np.arange(3)
profits = [v["profit"] / 1e6 for v in snapshots]
bar = ax.bar(x, profits)
ax.bar_label(bar, fmt="%.6f", padding=4)
ax.axhline(0, linewidth=0.8)
ax.set_xticks(x, labels2)
ax.set_ylabel("Instrument operating result (SIM USD)")
ax.set_ylim(-10.2, 2)
save(fig, "profit-bridge")
fig, ax = plt.subplots(figsize=(7.4, 4.1))
for key, label in [
    ("cash", "Cash"),
    ("available", "Available after restrictions"),
    ("unrestrictedEarned", "Unrestricted earned"),
]:
    ax.plot(range(3), [s[key] / 1e6 for s in snapshots], marker="o", label=label)
ax.plot(
    range(3),
    [(s["tailReserve"] + s["workingCapital"]) / 1e6 for s in snapshots],
    marker="s",
    linestyle="--",
    label="Tail reserve + working capital",
)
ax.set_xticks(range(3), labels2)
ax.set_ylabel("SIM USD; dated ledger checkpoints")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
save(fig, "cash")
fig, ax = plt.subplots(figsize=(7.4, 3.8))
for mode, label in [
    ("cumulative", "Cumulative"),
    ("frozen", "Frozen"),
    ("reset", "Reset"),
    ("retrieval", "Ordinary retrieval"),
]:
    vals = [r for r in D["learning-checkpoints"] if r["mode"] == mode]
    ax.plot([int(r["checkpoint"]) for r in vals], [float(r["mean_cpu_seconds"]) for r in vals], marker="o", label=label)
ax.set_xlabel("Reported development checkpoint (not independent source-episode count)")
ax.set_ylabel("Reported deployment CPU proxy (seconds)")
ax.set_xticks([0, 1, 2, 3])
ax.legend(ncol=2)
save(fig, "historical-learning")
fig, ax = plt.subplots(figsize=(7.4, 3.5))
r = D["learning-final-contrasts"]
y = np.arange(3)
vals = np.array([float(q["estimate"]) for q in r])
lo = np.array([float(q["lower"]) for q in r])
hi = np.array([float(q["upper"]) for q in r])
ax.errorbar(vals, y, xerr=[vals - lo, hi - vals], fmt="o", capsize=4)
ax.axvline(0, linestyle="--", linewidth=0.8)
ax.set_yticks(y, ["Frozen − cumulative", "Reset − cumulative", "Retrieval − cumulative"])
ax.invert_yaxis()
ax.set_xlabel("Reported final-panel CPU difference (seconds); intervals cross zero")
save(fig, "historical-intervals")
# Exact workflow diagram: arrows encode implemented data flow, not achieved economics.
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.set_axis_off()
boxes = [
    (0.16, 0.84, "Candidate schedule\nexisting task + typed rows"),
    (0.50, 0.84, "Failure witness\nscenario, time, units"),
    (0.84, 0.84, "Read-only adjudication\nrecompute scalar violation"),
    (0.84, 0.46, "Constraint compiler\nlinear_le operation"),
    (0.50, 0.46, "Re-solve + regression\nunchanged service contract"),
    (0.16, 0.46, "Independent acceptance\ntrajectory, quality, resources"),
    (0.16, 0.12, "Native local evidence pack\nHOLD; no settlement"),
    (0.57, 0.12, "Economic and experience gates\nremain unestablished"),
]
for a, b, text in boxes:
    ax.text(a, b, text, ha="center", va="center", fontsize=9, bbox={"boxstyle": "round,pad=.6", "fill": False})
for i, j in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7)]:
    a, b, _ = boxes[i]
    c, d, _ = boxes[j]
    dx, dy = c - a, d - b
    start = (a + 0.095 * np.sign(dx), b + 0.055 * np.sign(dy))
    end = (c - 0.095 * np.sign(dx), d - 0.055 * np.sign(dy))
    ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.1})
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
save(fig, "mechanism")
print("Generated seven figures from data/audited.json")
