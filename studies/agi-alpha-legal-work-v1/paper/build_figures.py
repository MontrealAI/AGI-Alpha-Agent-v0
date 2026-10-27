# SPDX-License-Identifier: Apache-2.0
"""Generate publication figures directly from the frozen observed results."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/legal-work-matplotlib")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/figures"


def main() -> None:
    """Keep complete acceptance distinct from partial rule correctness."""
    OUT.mkdir(parents=True, exist_ok=True)
    primary = json.loads((ROOT / "evidence/production-summary.json").read_text())["acceptance"]["primary"]
    economics = json.loads((ROOT / "economics/results/primary-v2/campaign.json").read_text())
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )
    arms = ["B", "C1", "C", "D"]
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.2), layout="constrained")
    values = [100 * primary[a]["accepted_deterministic"] / primary[a]["cases"] for a in arms]
    axes[0].bar(arms, values, color=["#77758b", "#8662cf", "#542bbc", "#555e70"], width=0.6)
    axes[0].set(ylabel="Complete packets accepted (%)", ylim=(0, 100), title="Primary outcome: complete acceptance")
    for i, a in enumerate(arms):
        axes[0].text(i, values[i] + 3, f"{primary[a]['accepted_deterministic']}/24", ha="center", fontweight="bold")
    values = [100 * primary[a]["rules_correct"] / primary[a]["rules_total"] for a in arms]
    axes[1].bar(arms, values, color=["#77758b", "#8662cf", "#542bbc", "#555e70"], width=0.6)
    axes[1].set(ylabel="Correct rule statuses (%)", ylim=(0, 100), title="Secondary outcome: individual rules")
    for i, a in enumerate(arms):
        axes[1].text(i, values[i] + 3, f"{primary[a]['rules_correct']}/192", ha="center", fontweight="bold")
    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=0.15)
    fig.savefig(OUT / "primary-acceptance.pdf", bbox_inches="tight")
    fig.savefig(OUT / "primary-acceptance.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    labels = [
        "Reference",
        "15-minute review",
        "CAD 5 price",
        "10-minute correction",
        "No buyer onboarding",
        "Higher repeat demand",
        "Zero demand",
        "Stronger alternative",
        "Higher maintenance",
    ]
    rows = economics["summaries"]
    means = [r["reinvestProfitCents"]["mean"] / 100 for r in rows]
    lows = [r["reinvestProfitCents"]["p10"] / 100 for r in rows]
    highs = [r["reinvestProfitCents"]["p90"] / 100 for r in rows]
    fig, ax = plt.subplots(figsize=(9.4, 4.3), layout="constrained")
    ys = list(range(len(rows)))
    ax.hlines(ys, lows, highs, color="#c5b4e8", linewidth=5)
    ax.scatter(means, ys, color="#542bbc", s=30, zorder=3)
    ax.set_yticks(ys, labels)
    ax.invert_yaxis()
    ax.axvline(0, color="#85909f", linewidth=1)
    ax.set(
        xlabel="Simulated cash net result over 26 weeks (CAD)",
        title="All 216 reinvestment-world outcomes were negative",
    )
    ax.grid(axis="x", alpha=0.15)
    ax.set_axisbelow(True)
    for y, mean in zip(ys, means, strict=True):
        ax.annotate(f"{mean:,.0f}", (mean, y), xytext=(8, 5), textcoords="offset points", fontsize=8)
    fig.savefig(OUT / "economics-sensitivity.pdf", bbox_inches="tight")
    fig.savefig(OUT / "economics-sensitivity.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(
        json.dumps(
            {
                "figures": 2,
                "basis": "Observed research plus declared economic scenarios; no market confidence intervals.",
            }
        )
    )


if __name__ == "__main__":
    main()
