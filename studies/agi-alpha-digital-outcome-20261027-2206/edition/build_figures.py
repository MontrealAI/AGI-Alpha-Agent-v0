# SPDX-License-Identifier: Apache-2.0
"""Render exact, source-backed figures for the research edition."""

from pathlib import Path
import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "figures"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "axes.labelcolor": "#301356",
        "text.color": "#231b33",
        "figure.facecolor": "white",
    }
)
results = json.loads((ROOT / "experiment/comparison_results.json").read_text())["primary_results"]
fig, ax = plt.subplots(figsize=(8.7, 3.35))
for i, r in enumerate(results):
    ax.barh(i, r["numeric_and_endpoint_accepted"], color="#6c39b7", label="Numerical / endpoints" if i == 0 else None)
    ax.barh(i, r["correct_refusals"], left=56, color="#c4a8f0", label="Required refusals" if i == 0 else None)
    ax.text(65, i, f"{r['accepted']}/64", va="center", weight="bold", color="#301356")
ax.set(
    yticks=range(3),
    yticklabels=["Ordinary competent", "Expert operation", "Conventional workflow"],
    xlim=(0, 75),
    xticks=[0, 16, 32, 48, 64],
    xlabel="Fresh checks accepted (one implementation trial per workflow)",
)
ax.invert_yaxis()
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.23), ncol=2)
ax.grid(axis="x", alpha=0.16)
ax.set_axisbelow(True)
fig.tight_layout()
for ext in ["svg", "pdf"]:
    fig.savefig(OUT / f"fresh_confirmation.{ext}", bbox_inches="tight")
plt.close(fig)
fig, ax = plt.subplots(figsize=(8.7, 3.5))
labels = ["Ordinary competent", "Expert operation", "Conventional workflow"]
seconds = [609.38656, 819.368824, 493.06]
ax.barh(labels, [s / 60 for s in seconds], color=["#9270bf", "#6c39b7", "#301356"])
for i, s in enumerate(seconds):
    ax.text(s / 60 + 0.15, i, f"{s / 60:.2f} min", va="center")
ax.axvline(15, ls="--", color="#8b617d", lw=1)
ax.text(14.85, 2.5, "15-minute construction ceiling", ha="right", fontsize=9)
ax.set(xlim=(0, 17), xlabel="Recorded construction wall time; not billable model usage")
ax.invert_yaxis()
fig.tight_layout()
for ext in ["svg", "pdf"]:
    fig.savefig(OUT / f"construction_time.{ext}", bbox_inches="tight")
plt.close(fig)
print("Rendered fresh confirmation and construction-time figures.")
