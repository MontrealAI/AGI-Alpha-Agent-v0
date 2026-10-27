# SPDX-License-Identifier: Apache-2.0
"""Render exact observed source branches and explicitly modeled economic figures."""

from pathlib import Path
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.labelcolor": "#132c43", "text.color": "#132c43",
                     "axes.titleweight": "bold", "savefig.facecolor": "white"})


def save(fig: plt.Figure, name: str) -> None:
    """Save matching shareable and browser forms."""
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Read frozen data rather than re-estimating paper results."""
    branches = json.loads((ROOT / "results/development/constructed-delivery.json").read_text())["branches"]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    labels = ["S4 count branch", "Main-table mean branch", "Inconsistent printed marginal"]
    for y, branch, color in [(0, branches[2], "#0b5266"), (1, branches[1], "#b7752d")]:
        lo, hi = branch["lower"], branch["upper"]
        ax.plot([lo, hi], [y, y], color=color, linewidth=9, solid_capstyle="butt")
        ax.text((lo + hi) / 2, y + .17, f"{lo:.6f}–{hi:.6f}", ha="center", fontsize=10, color=color)
    ax.plot(8.68, 2, marker="x", color="#a23835", markersize=11, markeredgewidth=2)
    ax.text(8.68, 2.17, "8.68 · unsupported as a corrected result", ha="right", color="#a23835", fontsize=9)
    ax.set_yticks(range(3), labels)
    ax.set_xlim(7.35, 8.83)
    ax.set_ylim(-.4, 2.5)
    ax.set_xlabel("Retrieval minus non-retrieval, percentage points")
    ax.set_title("Preserve the source conflict; inspect conditional reconstructions", loc="left", pad=17)
    ax.grid(axis="x", alpha=.18)
    fig.text(.13, -.11, "Ranges reflect source rounding and declared hypotheses. They are not confidence intervals.", fontsize=9)
    save(fig, "source-branches")

    paths = json.loads((ROOT / "economics/results-v1/paths.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    for ax, key, title in zip(axes, ["E+success", "E+payment-delay"], ["On-time collection", "Collection after the next-order window"]):
        daily = {}
        for item in paths[key]["events"]:
            daily[item["event"]["day"]] = item["state"]
        days = sorted(daily)
        for field, label, color in [("cash_cents", "Cash", "#132c43"), ("available_cents", "After obligations and reserve", "#0b5266")]:
            ax.step(days, [daily[d][field] / 100 for d in days], where="post", label=label, color=color, linewidth=2)
            ax.plot(days, [daily[d][field] / 100 for d in days], "o", color=color, markersize=3)
        ax.axhline(1000, color="#888888", linestyle="--", linewidth=1, label="Original seed")
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xlabel("Modeled day")
        ax.grid(alpha=.15)
    axes[0].set_ylabel("USD · simulated cash")
    handles, legends = axes[0].get_legend_handles_labels()
    fig.legend(handles, legends, loc="lower center", ncol=3, fontsize=9, bbox_to_anchor=(.5, -.08))
    fig.suptitle("Collections finance fresh work; receivables do not", x=.07, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, .02, 1, .93))
    save(fig, "cash-path")

    fig, ax = plt.subplots(figsize=(8, 3.9))
    uses = np.arange(1, 13)
    ax.plot(uses, 60 * 60 / (125 * uses), "o-", color="#0b5266", label="Additional B only · $60")
    ax.plot(uses, 185 * 60 / (125 * uses), "s-", color="#b7752d", label="Core plus B · $185")
    ax.axhline(20, color="#64798c", linestyle="--", label="Reference assumption · 20 minutes")
    ax.annotate("4 uses: >7.2 minutes", xy=(4, 7.2), xytext=(4.5, 32), arrowprops={"arrowstyle": "->", "color": "#0b5266"}, fontsize=9)
    ax.annotate("5 uses: >17.76 minutes", xy=(5, 17.76), xytext=(6.5, 49), arrowprops={"arrowstyle": "->", "color": "#b7752d"}, fontsize=9)
    ax.set_xlabel("Compatible uses, known or forecast separately")
    ax.set_ylabel("Required saving per use (minutes)")
    ax.set_title("What must transfer save to justify its additional cost?", loc="left", pad=15)
    ax.set_xticks(uses)
    ax.set_ylim(0, 94)
    ax.grid(alpha=.15)
    ax.legend(fontsize=9, loc="upper right")
    fig.text(.12, -.11, "At $125/hour; equal accepted quality and no extra serving cost. Actual savings remain unmeasured.", fontsize=9)
    save(fig, "retention-threshold")


if __name__ == "__main__":
    main()
