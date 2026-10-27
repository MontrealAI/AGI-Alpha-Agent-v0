# SPDX-License-Identifier: Apache-2.0
"""Render publication figures from recorded study outcomes without running the experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np


HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
OUT = HERE / "figures"
COLORS = {
    "beta_space": "#526477",
    "beta_dopt": "#879BA7",
    "beta_adaptive": "#332E69",
    "beta_direct": "#C85B45",
    "v1": "#CB9D3D",
    "v2": "#087E8B",
    "library_v2": "#6E9B56",
    "wrong_prior": "#B97CA2",
    "oracle_support": "#111827",
}
LABELS = {
    "beta_space": "Beta: sparse + space filling",
    "beta_dopt": "Beta: full-library design",
    "beta_adaptive": "Beta: adaptive design",
    "beta_direct": "Beta: direct plan search",
    "v1": "Origin artifact v1",
    "v2": "Gym artifact v2",
    "library_v2": "Same-content library",
    "wrong_prior": "Unrelated prior",
    "oracle_support": "Oracle support (unavailable)",
}


def read(path: str) -> Any:
    return json.loads((STUDY / path).read_text())


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", dpi=190)
    plt.close(fig)


def configure() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": "#142B3A",
            "text.color": "#142B3A",
            "axes.titleweight": "bold",
            "axes.titlesize": 10,
            "figure.facecolor": "white",
            "axes.grid": True,
            "grid.alpha": 0.14,
            "pdf.fonttype": 42,
        }
    )
    OUT.mkdir(parents=True, exist_ok=True)


def lineage() -> None:
    fig, ax = plt.subplots(figsize=(9.1, 3.5))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    boxes = [
        (0.15, 2.3, "Originating work", "128 fitting observations\n384 paid acceptance checks"),
        (2.6, 2.3, "Artifact v1", "9 empirical terms\nnew coefficients on reuse"),
        (5.05, 2.3, "Optional Gym -> v2", "10 additional jobs\n21 empirical terms"),
        (7.5, 2.3, "Fresh recipient", "Actual protected bytes\nrefit + paid output check"),
        (2.6, 0.25, "Strong alternatives", "Adaptive sparse fitting\ndirect search / differencing"),
        (5.05, 0.25, "New offering tests", "Response model / design\nrobust-operation supplement"),
        (7.5, 0.25, "Enterprise decision", "Deliver, retain, reject\ncash and complete costs"),
    ]
    for x, y, title, detail in boxes:
        face = "#EFF6F6" if title not in {"Strong alternatives", "Enterprise decision"} else "#F8F0E9"
        ax.add_patch(
            FancyBboxPatch(
                (x, y), 2.2, 1.15, boxstyle="round,pad=0.04", facecolor=face, edgecolor="#9BAFB8", linewidth=0.8
            )
        )
        ax.text(x + 0.12, y + 0.88, title, weight="bold", fontsize=9)
        ax.text(x + 0.12, y + 0.45, detail, va="center", fontsize=8, linespacing=1.55)
    for a, b in [
        ((2.4, 2.87), (2.55, 2.87)),
        ((4.85, 2.87), (5.0, 2.87)),
        ((7.3, 2.87), (7.45, 2.87)),
        ((8.6, 2.25), (6.15, 1.5)),
        ((4.85, 0.82), (5.0, 0.82)),
        ((7.3, 0.82), (7.45, 0.82)),
    ]:
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, color="#087E8B"))
    ax.text(
        0.15, 1.25, "OBSERVED\nSynthetic software\nlearning and transfer", fontsize=8, color="#087E8B", linespacing=1.5
    )
    ax.text(
        0.15, 0.1, "CONDITIONAL\nDemand, prices, latency\nand collections", fontsize=8, color="#C85B45", linespacing=1.5
    )
    save(fig, "lineage")


def technical(rows: list[dict[str, Any]]) -> None:
    budgets = [24, 40, 64, 96]
    fig, axes = plt.subplots(1, 2, figsize=(9.1, 3.6), sharey=True)
    for ax, metric, title in zip(
        axes, ["prediction_accepted", "design_accepted"], ["Fresh response model", "Fresh checked operating plan"]
    ):
        for method in ["beta_space", "beta_dopt", "beta_adaptive", "beta_direct", "v1", "v2"]:
            if method == "beta_direct" and metric == "prediction_accepted":
                continue
            values = []
            for budget in budgets:
                group = [
                    r for r in rows if r["regime"] == "compatible" and r["budget"] == budget and r["method"] == method
                ]
                values.append(100 * np.mean([r[metric] for r in group]))
            ax.plot(
                budgets, values, marker="o", lw=2 if method == "v2" else 1.4, color=COLORS[method], label=LABELS[method]
            )
        ax.set_title(title)
        ax.set_xticks(budgets)
        ax.set_xlabel("Candidate / decision query budget")
        ax.set_ylim(-4, 104)
    axes[0].set_ylabel("Accepted outcomes, compatible family (%)")
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.13))
    fig.tight_layout()
    save(fig, "learning-transfer")

    fig, axes = plt.subplots(1, 2, figsize=(9.1, 3.7), sharey=True)
    methods = ["beta_dopt", "beta_adaptive", "v1", "v2", "library_v2", "wrong_prior"]
    regimes = ["compatible", "partial_shift", "novel_family"]
    names = ["Compatible", "Partial shift", "Novel family"]
    for ax, metric, title in zip(
        axes, ["prediction_accepted", "design_accepted"], ["Response model: 40 queries", "Operating plan: 40 queries"]
    ):
        for i, method in enumerate(methods):
            values = []
            for regime in regimes:
                group = [r for r in rows if r["regime"] == regime and r["budget"] == 40 and r["method"] == method]
                values.append(100 * np.mean([r[metric] for r in group]))
            ax.bar(np.arange(3) + (i - 2.5) * 0.125, values, width=0.12, color=COLORS[method], label=LABELS[method])
        ax.set_xticks(np.arange(3), names)
        ax.set_ylim(0, 108)
        ax.set_title(title)
    axes[0].set_ylabel("Accepted outcomes (%)")
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        loc="lower center",
        ncol=3,
        frameon=False,
        fontsize=8,
        bbox_to_anchor=(0.5, -0.12),
    )
    fig.tight_layout()
    save(fig, "causal-controls")

    fig, axes = plt.subplots(1, 2, figsize=(9.1, 3.8))
    for ax, metric, title in zip(
        axes,
        ["prediction_accepted", "design_accepted"],
        ["Model acceptance includes 384 extra checks", "Decision acceptance includes final check"],
    ):
        for method in ["beta_dopt", "beta_direct", "v2"]:
            if method == "beta_direct" and metric == "prediction_accepted":
                continue
            values = [sum(r[metric] for r in rows if r["budget"] == b and r["method"] == method) for b in budgets]
            ax.plot(budgets, values, marker="o", color=COLORS[method], label=LABELS[method], lw=2)
        ax.set_xticks(budgets)
        ax.set_xlabel("Declared candidate / decision budget")
        ax.set_title(title, fontsize=9)
        ax.set_ylim(-1, 50)
        ax.legend(loc="lower right", fontsize=7.5, frameon=False)
    axes[0].set_ylabel("Accepted cases / 48 generated tasks")
    fig.tight_layout()
    save(fig, "frontier")


def learning_progress(rows: list[dict[str, Any]]) -> None:
    events = read("technical/results/learning_ledger.json")["events"]
    union: set[int] = set()
    cumulative = []
    for event in events:
        union.update(event["learned_nonzero_terms"])
        cumulative.append(len(union))
    fig, axes = plt.subplots(1, 2, figsize=(9.1, 3.3))
    axes[0].plot(range(11), cumulative, marker="o", color=COLORS["v2"], lw=2)
    axes[0].set(
        xlabel="Additional Gym jobs after origin",
        ylabel="Empirically retained terms",
        title="What the update retained",
        xticks=[0, 2, 4, 6, 8, 10],
        ylim=(0, 24),
    )
    axes[0].annotate("v1: 9", (0, 9), xytext=(0.7, 6.2), fontsize=8)
    axes[0].annotate("v2: 21", (10, 21), xytext=(7, 22.2), fontsize=8)
    methods = ["beta_adaptive", "v1", "v2", "wrong_prior"]
    counts = [
        sum(
            r["prediction_accepted"]
            for r in rows
            if r["method"] == m and r["budget"] == 24 and r["regime"] == "compatible"
        )
        for m in methods
    ]
    bars = axes[1].bar(
        ["Adaptive\nBeta", "Origin\nv1", "Developed\nv2", "Unrelated\nprior"],
        counts,
        color=[COLORS[m] for m in methods],
        width=0.65,
    )
    for b, value in zip(bars, counts):
        axes[1].text(b.get_x() + b.get_width() / 2, value + 0.6, f"{value}/24", ha="center", fontsize=8)
    axes[1].set(
        ylabel="Accepted fresh compatible models", title="Fresh transfer at 24-call candidate budget", ylim=(0, 25)
    )
    fig.text(
        0.5,
        -0.02,
        "All 11 learning-job fits passed their audit; training success alone does not establish fresh transfer.\nA marketed model also pays for 384 independent acceptance observations.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout()
    save(fig, "learning-progress")


def main() -> None:
    configure()
    lineage()
    rows = read("technical/results/confirmation_rows.json")
    learning_progress(rows)
    technical(rows)
    robust = read("technical/robust/results/confirmation_rows.json")
    fig, axes = plt.subplots(1, 2, figsize=(9.1, 3.7))
    for ax, regime, title in zip(
        axes, ["compatible", "all"], ["Compatible family (24 tasks)", "All three families (48 tasks)"]
    ):
        for method in ["beta_space", "beta_dopt", "beta_adaptive", "beta_direct", "v1", "v2"]:
            counts = []
            for b in [24, 40, 64, 96]:
                subset = [
                    r
                    for r in robust
                    if r["method"] == method and r["budget"] == b and (regime == "all" or r["regime"] == regime)
                ]
                counts.append(sum(r["accepted"] for r in subset))
            ax.plot(
                [24, 40, 64, 96],
                counts,
                color=COLORS[method],
                marker="o",
                lw=2 if method == "v2" else 1.4,
                label=LABELS[method],
            )
        ax.set_title(title)
        ax.set_xticks([24, 40, 64, 96])
        ax.set_xlabel("Complete budget, including 16 final checks")
    axes[0].set_ylabel("Accepted robust operating plans")
    axes[0].set_ylim(-1, 25)
    axes[1].set_ylim(-1, 49)
    fig.legend(
        *axes[1].get_legend_handles_labels(),
        loc="lower center",
        ncol=3,
        frameon=False,
        fontsize=8,
        bbox_to_anchor=(0.5, -0.13),
    )
    fig.tight_layout()
    save(fig, "robust-frontier")

    summary = read("economics/results/summary.json")
    fig, axes = plt.subplots(1, 2, figsize=(9.1, 3.8))
    for policy, label, color in [
        ("beta", "Beta only", "#526477"),
        ("shared", "Private / shared selective", "#087E8B"),
        ("shared_gym_pilot", "Controlled Gym pilot", "#C85B45"),
    ]:
        ledger = read(f"economics/results/ledger_{policy}_seed0.json")
        daily = [x for x in ledger if x.get("kind") == "day_close"]
        axes[0].plot([x["day"] for x in daily], [x["profit"] / 1000 for x in daily], lw=2, color=color, label=label)
    axes[0].set_title("One matched simulated history (seed 0)")
    axes[0].set_ylabel("Cumulative operating profit (USD thousands)")
    axes[0].set_xlabel("Day")
    axes[0].legend(fontsize=7.5, frameon=False)
    for i, policy in enumerate(["shared", "shared_gym_pilot"]):
        entries = [
            next(x for x in summary["summary"] if x["scenario"] == s and x["policy"] == policy)
            for s in ["primary", "query_envelope_40"]
        ]
        vals = [x["paired_incremental_profit_vs_beta"]["mean"] / 1000 for x in entries]
        errs = (
            np.array(
                [
                    [
                        x["paired_incremental_profit_vs_beta"]["mean"]
                        - x["paired_incremental_profit_vs_beta"]["conditional_seed_ci95_low"]
                        for x in entries
                    ],
                    [
                        x["paired_incremental_profit_vs_beta"]["conditional_seed_ci95_high"]
                        - x["paired_incremental_profit_vs_beta"]["mean"]
                        for x in entries
                    ],
                ]
            )
            / 1000
        )
        axes[1].bar(
            np.arange(2) + (i - 0.5) * 0.32,
            vals,
            width=0.3,
            color=["#087E8B", "#C85B45"][i],
            yerr=errs,
            capsize=3,
            label=["Selective shared", "Controlled Gym pilot"][i],
        )
    axes[1].axhline(0, color="#526477", lw=0.8)
    axes[1].set_xticks([0, 1], ["Primary: up to 96", "40-call fitting cap"])
    axes[1].set_ylabel("Incremental profit vs Beta (USD thousands)")
    axes[1].set_title("Conditional mean across 64 matched seeds")
    axes[1].legend(fontsize=7.5, frameon=False)
    fig.tight_layout()
    save(fig, "economics")


if __name__ == "__main__":
    main()
