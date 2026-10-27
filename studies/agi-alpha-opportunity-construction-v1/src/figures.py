# SPDX-License-Identifier: Apache-2.0
"""Draw original publication figures from the recorded study, without generative imagery."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PURPLE, LILAC, INK, PALE, GOLD = "#4D287A", "#CDB9EC", "#22113E", "#F3EFF8", "#B58C39"


def box(ax: plt.Axes, x: float, y: float, width: float, height: float, text: str, dark: bool = False) -> None:
    """Draw a measured, readable labeled panel."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            facecolor=PURPLE if dark else PALE,
            edgecolor=LILAC,
            linewidth=1,
        )
    )
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=11,
        color="white" if dark else INK,
        linespacing=1.5,
    )


def mechanism() -> None:
    """Explain the data boundary and the exact finite answer."""
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("white")
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.text(
        0.02,
        0.96,
        "A useful joint answer without a central raw inventory",
        fontsize=17,
        fontweight="bold",
        color=INK,
        va="top",
    )
    for index, x in enumerate((0.03, 0.365, 0.70), 1):
        box(ax, x, 0.64, 0.27, 0.20, f"Owner {index}\n2 distinct asset slots\nPrivate eligibility + state")
        ax.add_patch(
            FancyArrowPatch(
                (x + 0.135, 0.62), (x + 0.135, 0.48), arrowstyle="-|>", mutation_scale=15, color=PURPLE, linewidth=1.4
            )
        )
    box(
        ax,
        0.03,
        0.28,
        0.94,
        0.19,
        "Three owners jointly execute the secret-shared circuit\n"
        "For EVERY declared scenario: can EACH demand receive a DIFFERENT usable asset?",
        True,
    )
    ax.text(
        0.5,
        0.535,
        "Local inputs become secret shares; fixed public dimensions and scenario family",
        ha="center",
        color=INK,
        fontsize=10,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 3},
    )
    ax.add_patch(
        FancyArrowPatch((0.5, 0.26), (0.5, 0.19), arrowstyle="-|>", mutation_scale=15, color=PURPLE, linewidth=1.4)
    )
    box(ax, 0.21, 0.05, 0.58, 0.13, "One aggregate bit + public scope and execution evidence")
    ax.text(
        0.5,
        0.004,
        "Research: three localhost processes, passive threshold 1 of 3. No physical certification or dispatch right.",
        ha="center",
        color="#675E73",
        fontsize=9,
    )
    fig.savefig(ROOT / "figures/mechanism.png", dpi=180, bbox_inches="tight")
    fig.savefig(ROOT / "figures/mechanism.pdf", bbox_inches="tight")
    plt.close(fig)


def technical() -> None:
    """Plot all fresh cases, preserving both positive and negative answers."""
    labels = ["Original mission\n21 scenarios", "Successor mission\n41 scenarios"]
    records = [
        json.loads((ROOT / "results" / f"{name}_confirmation.json").read_text()) for name in ("origin", "successor")
    ]
    for name, record in zip(("origin", "successor"), records, strict=True):
        library = json.loads((ROOT / "results" / f"{name}_confirmation_ordinary_library.json").read_text())
        assert library["execution"]["answer"] == record["execution"]["answer"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), gridspec_kw={"width_ratios": [1.4, 1]})
    x = [0, 1]
    feasible = [d["feasible"] for d in records]
    infeasible = [d["infeasible"] for d in records]
    axes[0].bar(x, feasible, color=PURPLE, label="Supplied pool certified feasible")
    axes[0].bar(x, infeasible, bottom=feasible, color=LILAC, label="Supplied pool not certified")
    for i, record in enumerate(records):
        axes[0].text(i, feasible[i] / 2, str(feasible[i]), ha="center", color="white", fontweight="bold")
        axes[0].text(i, feasible[i] + infeasible[i] / 2, str(infeasible[i]), ha="center", color=INK, fontweight="bold")
    axes[0].set_xticks(x, labels)
    axes[0].set_ylabel("Independent synthetic input worlds")
    axes[0].set_ylim(0, 130)
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), fontsize=8.5, frameon=False)
    axes[0].set_title("Both outcomes are valid assessment answers", color=INK, fontsize=12)
    axes[1].axis("off")
    total = sum(d["n"] for d in records)
    matched = sum(d["oracle_agreement"] for d in records)
    axes[1].text(0.5, 0.79, f"{matched}/{total}", ha="center", fontsize=36, color=PURPLE, fontweight="bold")
    axes[1].text(
        0.5, 0.60, "Exact agreement with the\nindependent cleartext oracle", ha="center", fontsize=12, color=INK
    )
    axes[1].text(
        0.5, 0.34, "Ordinary identical library:\nsame computation and answers", ha="center", fontsize=11, color=INK
    )
    axes[1].text(
        0.5,
        0.08,
        "Software evidence within a finite synthetic scope.\nNot a measured utility deployment success rate.",
        ha="center",
        fontsize=9,
        color="#675E73",
    )
    for spine in ("top", "right"):
        axes[0].spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/technical.png", dpi=180, bbox_inches="tight")
    fig.savefig(ROOT / "figures/technical.pdf", bbox_inches="tight")
    plt.close(fig)


def economics() -> None:
    """Separate whole-venture scenario profit from per-delivery contribution."""
    data = json.loads((ROOT / "results/economics_plot_data.json").read_text())
    indexed = {row["policy"]: row for row in data["policy_rows"]}
    order = ["direct", "conditional", "no_launch"]
    names = ["Direct offer\n$12,000; full deposit", "Original conditional tie*", "No launch\nSelected policy"]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for position, name in enumerate(order):
        row = indexed[name]
        mean, low, high = [row[key] / 1000 for key in ("profit_mean_usd", "profit_p05_usd", "profit_p95_usd")]
        ax.errorbar(
            mean,
            position,
            xerr=[[mean - low], [high - mean]],
            fmt="o",
            color=PURPLE,
            capsize=5,
            markersize=8,
            linewidth=2,
        )
        ax.annotate(
            f"${mean:,.1f}k",
            (mean, position),
            xytext=(0, 13),
            textcoords="offset points",
            ha="center",
            fontsize=11,
            color=INK,
            fontweight="bold",
        )
    ax.axvline(0, color=GOLD, linewidth=1.2)
    ax.set_yticks([0, 1, 2], names)
    ax.set_xlim(-46, 5)
    ax.set_ylim(-0.65, 2.7)
    ax.set_xlabel("180-day full-venture operating profit (thousands of modeled USD)")
    ax.set_title("Financing the opportunity: the tested launch decision", color=INK, fontsize=16, pad=15)
    ax.grid(axis="x", color="#E9E1F1", linewidth=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    fig.text(
        0.52,
        0.025,
        "Means and 5th–95th scenario percentiles, 1,000 fresh modeled worlds.\n"
        "*Grid-order tie after development; all nine conditional policies receive a separate prospective follow-up.",
        ha="center",
        fontsize=8.5,
        color="#675E73",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(ROOT / "figures/economics.png", dpi=180, bbox_inches="tight")
    fig.savefig(ROOT / "figures/economics.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    (ROOT / "figures").mkdir(exist_ok=True)
    mechanism()
    if (ROOT / "results/successor_confirmation.json").exists():
        technical()
    if (ROOT / "results/economics_plot_data.json").exists():
        economics()
