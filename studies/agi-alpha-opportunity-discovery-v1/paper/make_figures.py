# SPDX-License-Identifier: Apache-2.0
"""Render figures from executed receipts. No fitted market parameters."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/alpha-flywheel-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "savefig.facecolor": "white"})
COLORS = ["#0b5266", "#ca7928", "#a43d4d", "#567c66"]
data = json.loads((ROOT / "economics/results/conditional-boundaries-v1.json").read_text())

fig, ax = plt.subplots(figsize=(7.4, 3.8), layout="constrained")
n = np.arange(0, 9)
for price, color in zip([500, 800, 1200], COLORS):
    ceiling = .9 * .9 * n * (.95 * price - 325) - 200
    ax.plot(n, ceiling, marker="o", label=f"Assumed price ${price:,}", color=color)
ax.axhline(0, color="#182a3e", lw=.8)
ax.scatter([4], [1209.4], color=COLORS[1], s=65, zorder=4)
ax.annotate("$1,209.40 at four prospects", (4, 1209.4), xytext=(2.9, 2250),
            arrowprops={"arrowstyle": "-", "color": COLORS[1]}, fontsize=9)
ax.set(xlabel="Number of prospective participants (assumed)",
       ylabel="Fixed-cost ceiling (USD)",
       title="Conditional feasibility boundary — demand is unmeasured")
ax.legend(frameon=False, loc="upper left")
ax.grid(axis="y", alpha=.16)
fig.savefig(OUT / "thresholds.pdf")
fig.savefig(OUT / "thresholds.png", dpi=180)
plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.5), layout="constrained", sharey=True)
for name, color in zip(["success", "default", "common-failure", "delay"], COLORS):
    path = next(x for x in data["cash_paths"] if x["shock"] == name)["result"]
    for ax, key in zip(axes, ["cash_cents", "available_cents"]):
        pairs = [(x["event"]["day"], x["state"][key] / 100) for x in path["events"]]
        days = [x[0] for x in pairs] + [42]
        values = [x[1] for x in pairs] + [pairs[-1][1]]
        ax.step(days, values, where="post", label=name.replace("-", " "), color=color,
                linestyle="--" if name == "delay" else "-", lw=1.9)
for ax, title in zip(axes, ["Cash held", "Available after obligations / reserve"]):
    ax.set(xlabel="Scenario day", title=title, xlim=(0, 42), ylim=(0, 4600))
    ax.grid(axis="y", alpha=.16)
axes[0].set_ylabel("US dollars (all values assumed)")
axes[1].legend(frameon=False, fontsize=8, loc="upper left")
fig.savefig(OUT / "cash-timing.pdf")
fig.savefig(OUT / "cash-timing.png", dpi=180)
plt.close(fig)

fig, ax = plt.subplots(figsize=(7.4, 2.8), layout="constrained")
labels = ["Numerical updates", "Unchanged snapshots", "Hold for evidence / scope", "Reject invalid input"]
counts = [20, 4, 36, 4]
bars = ax.barh(labels, counts, color=[COLORS[0], COLORS[3], COLORS[1], COLORS[2]])
ax.bar_label(bars, padding=4)
ax.invert_yaxis()
ax.set(xlabel="Declared v1 conformance cases", xlim=(0, 41),
       title="64 / 64 fixture dispositions — not 64 accepted services")
ax.grid(axis="x", alpha=.15)
fig.savefig(OUT / "conformance.pdf")
fig.savefig(OUT / "conformance.png", dpi=180)
plt.close(fig)
print(json.dumps({"figures": 3, "source": "Executed JSON receipts; hypothetical economics labeled"}))
