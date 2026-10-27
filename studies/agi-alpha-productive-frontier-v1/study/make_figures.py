# SPDX-License-Identifier: Apache-2.0
"""Render publication figures from frozen study evidence without changing it."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="productive-frontier-mpl-"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np


STUDY = Path(__file__).resolve().parent.parent
TECH = STUDY / "study" / "technical"
OUT = STUDY / "paper" / "figures"
NAVY, TEAL, GOLD, RED, GREY = "#20324D", "#087F8C", "#B58A30", "#B44848", "#65748B"
PALE, LIGHT, RULE = "#EDF6F5", "#F8F5EB", "#DCE3E9"
CAPTIONS: dict[str, str] = {}
NUMBERS: dict[str, object] = {}
SOURCES: set[Path] = set()


def read(path: Path) -> dict:
    SOURCES.add(path)
    return json.loads(path.read_text())


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10.5,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "axes.titleweight": "semibold",
            "axes.labelcolor": NAVY,
            "text.color": NAVY,
            "xtick.color": GREY,
            "ytick.color": NAVY,
            "axes.edgecolor": RULE,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.grid": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.dpi": 240,
        }
    )


def save(fig: plt.Figure, name: str, caption: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", pad_inches=0.12)
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    CAPTIONS[name] = caption


def wilson(k: int, n: int) -> tuple[float, float]:
    p, z = k / n, 1.959963984540054
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return float(max(0, center - half)), float(min(1, center + half))


def acceptance() -> None:
    data = read(TECH / "results" / "technical_results.json")["summary"]
    methods = ["schur", "adaptive_krylov", "fixed_krylov48", "work_pod24", "work_pod48", "gym_pod48"]
    labels = ["Direct Schur", "Ordinary adaptive", "Fixed library (48)", "Work24", "Work48", "Gym48"]
    colors = [NAVY, NAVY, GREY, TEAL, TEAL, GOLD]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.7), sharey=True)
    intervals = {}
    for ax, split, title in zip(
        axes, ["confirmation", "shift"], ["In range · 64 fresh cases", "Shifted · 32 fresh cases"]
    ):
        intervals[split] = {}
        for y, method, color in zip(range(6), methods, colors):
            row = data[split][method]
            k, n = row["accepted"], row["n"]
            low, high = wilson(k, n)
            p = k / n
            ax.errorbar(p, y, xerr=[[p - low], [high - p]], fmt="o", color=color, capsize=3, ms=6, lw=1.5)
            ax.text(1.045, y, f"{k}/{n}", va="center", fontsize=10)
            intervals[split][method] = {"accepted": k, "n": n, "wilson95": [low, high]}
        ax.axvline(0.95, color=RED, ls=(0, (3, 3)), lw=1)
        ax.set_xlim(-0.04, 1.22)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0", "25", "50", "75", "100"])
        ax.set_xlabel("Accepted cases (%)")
        ax.set_title(title, pad=12, loc="left")
        ax.set_yticks(range(6), labels)
        ax.grid(axis="x", color=RULE, lw=0.7)
        ax.tick_params(axis="y", length=0, pad=8)
    axes[0].invert_yaxis()
    fig.subplots_adjust(left=0.19, right=0.98, bottom=0.19, top=0.87, wspace=0.14)
    NUMBERS["acceptance_intervals"] = intervals
    save(
        fig,
        "01_acceptance_and_shift",
        "Observed certificate acceptance with 95% Wilson binomial intervals under the synthetic generator. "
        "The red dashed line is the frozen 95% empirical target. Intervals quantify sampling uncertainty under "
        "that generator; they do not establish population reliability, physical validity or a customer SLA. "
        "These are the original protected cases before fallback; hardened revalidation preserved all counts.",
    )


def feasibility() -> None:
    original = read(TECH / "results" / "technical_results.json")["summary"]["confirmation"]
    guarded = read(TECH / "results_validated" / "technical_results.json")["summary"]["confirmation"]
    repaired = read(TECH / "results_validated" / "fallback_results.json")["summary"]["confirmation"]
    methods = ["schur", "adaptive_krylov", "work_pod48", "gym_pod48"]
    names = ["Direct Schur", "Ordinary adaptive", "Work48", "Gym48"]
    repairs = {"adaptive_krylov": "adaptive_fallback", "work_pod48": "work48_fallback", "gym_pod48": "gym48_fallback"}
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    ax.axvspan(0.045, 0.25, color=PALE, zorder=0)
    ax.axvspan(0.25, 5, color=LIGHT, zorder=0)
    for y, method in enumerate(methods):
        for offset, data, marker, color, label in [
            (-0.18, original, "o", NAVY, "Original kernel"),
            (0, guarded, "^", GOLD, "Guarded kernel"),
        ]:
            vals = data[method]["batch32_seconds_observed"]
            ax.scatter(
                vals,
                [y + offset] * len(vals),
                s=42,
                marker=marker,
                color=color,
                label=label if y == 0 else None,
                zorder=3,
            )
        if method in repairs:
            vals = repaired[repairs[method]]["batch32_seconds_observed"]
            ax.scatter(
                vals,
                [y + 0.18] * len(vals),
                s=36,
                marker="s",
                color=TEAL,
                label="Guarded + repair" if y == 1 else None,
                zorder=3,
            )
    for x, label in [(0.25, "Interactive: 0.25 s"), (5, "Standard: 5 s")]:
        ax.axvline(x, color=RED if x == 0.25 else GREY, lw=1.1, ls=(0, (4, 3)))
        ax.text(
            x,
            1.025,
            label,
            transform=ax.get_xaxis_transform(),
            ha="center",
            fontsize=10,
            color=RED if x == 0.25 else GREY,
        )
    ax.set_xscale("log")
    ax.set_xlim(0.045, 6.5)
    ax.set_xticks([0.05, 0.1, 0.25, 0.5, 1, 5], ["0.05", "0.1", "0.25", "0.5", "1", "5"])
    ax.minorticks_off()
    ax.set_ylim(3.55, -0.55)
    ax.set_yticks(range(4), names)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.set_xlabel("Observed time per 32-case batch (seconds; logarithmic scale)")
    ax.grid(axis="x", color=RULE, lw=0.7)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.43), ncol=3, frameon=False, fontsize=10)
    fig.subplots_adjust(left=0.2, right=0.98, top=0.88, bottom=0.27)
    save(
        fig,
        "02_frozen_feasibility_boundaries",
        "Frozen 5 s standard and 0.25 s interactive numerical-core contracts. Each point is one observed 32-case "
        "batch. Original protected timings, guarded exposed-case revalidation and measured guarded fallback "
        "chains are shown separately. Original adaptive batches met 0.25 s, while guarded batches straddled "
        "the boundary. Work48 and Gym48 each refused two original cases; full repair accepted all 64. "
        "These few timing observations do not establish a production SLA, and thresholds were not changed. "
        "The 5 s numerical gate excludes the assumed model and preparation pipeline; end-to-end reservations "
        "of 95/125/182 s for audit/screen/selection are simulated assumptions, not measured latency.",
    )


def proposal() -> None:
    data = read(TECH / "results_final_prototype" / "selection_results.json")["summary"]
    methods = ["adaptive_fallback", "work48_fallback", "gym48_fallback", "schur"]
    names = ["Ordinary adaptive + repair", "Work48 + repair", "Gym48 + repair", "Direct Schur"]
    colors = [NAVY, TEAL, GOLD, GREY]
    fig, ax = plt.subplots(figsize=(7.2, 3.25))
    for y, method, color in zip(range(4), methods, colors):
        row = data[method]
        value = row["seconds_total"]
        ax.barh(y, value, height=0.52, color=color, alpha=0.95)
        suffix = f"  |  {row['selection_refinements']} refinements" if method != "schur" else ""
        ax.text(value + 0.045, y, f"{value:.3f} s{suffix}", va="center", fontsize=10)
    ax.axvline(2, color=RED, ls=(0, (4, 3)), lw=1.2)
    ax.text(2, 1.025, "Frozen 2 s contract", transform=ax.get_xaxis_transform(), ha="center", color=RED, fontsize=10)
    ax.set_ylim(3.6, -0.6)
    ax.set_xlim(0, 2.5)
    ax.set_yticks(range(4), names)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.set_xlabel("Eight-case numerical workflow time (seconds)")
    ax.grid(axis="x", color=RULE, lw=0.7)
    ax.set_axisbelow(True)
    fig.subplots_adjust(left=0.31, right=0.98, bottom=0.2, top=0.86)
    NUMBERS["final_prototype"] = data
    save(
        fig,
        "03_fresh_offering_prototype",
        "Final protected seed 7401: eight damping-selection cases, each with eight distinct gain settings. "
        "Every policy selected the independent oracle optimum in 8/8 cases with zero regret. Times include "
        "numerical matrix preparation, certificates, fallback and ranking refinement; independent audit "
        "solves are excluded. Ordinary adaptive tools already meet the frozen 2 s contract. The retained "
        "work basis is faster, while Gym incurs eight direct ranking refinements. This is an observed "
        "technical comparison on synthetic systems, not a market or frontier-model performance result. The 2 s "
        "gate excludes assumed frontier-model preparation; the 182 s complete selection-service reservation "
        "is simulated and was not measured by this experiment.",
    )


def lineage() -> None:
    read(TECH / "results" / "preconfirmation_freeze.json")
    read(TECH / "results" / "recipient_transfer.json")
    validation = read(STUDY / "evidence" / "adapter_validation.json")
    fig, ax = plt.subplots(figsize=(7.2, 3.65))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    boxes = {
        "origin": (0.15, 0.56, "6 origin solutions", "Synthetic work\nFull covariance solves", NAVY),
        "work": (0.475, 0.77, "Work48", "Retained numerical basis\nRank 48", TEAL),
        "gym": (0.475, 0.31, "Optional Gym48", "20 development probes\n4 extra full solves", GOLD),
        "offer": (0.835, 0.77, "Fresh prototype", "64 candidate settings\n8 optimal decisions", NAVY),
        "recipient": (0.835, 0.31, "Recipient process", "4 fresh inputs\nArtifact hash verified", TEAL),
    }
    w, h = 0.265, 0.26
    for x, y, title, sub, color in boxes.values():
        patch = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.012,rounding_size=0.02", fc="white", ec=color, lw=1.35
        )
        ax.add_patch(patch)
        ax.text(x, y + 0.065, title, ha="center", va="center", fontsize=11, color=color, weight="bold")
        ax.text(x, y - 0.045, sub, ha="center", va="center", fontsize=9.6, linespacing=1.5)

    def arrow(start: tuple[float, float], end: tuple[float, float], color: str, bend: float = 0) -> None:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=12,
                lw=1.35,
                color=color,
                connectionstyle=f"arc3,rad={bend}",
            )
        )

    arrow((0.295, 0.61), (0.33, 0.73), NAVY)
    arrow((0.475, 0.626), (0.475, 0.454), GOLD)
    arrow((0.625, 0.77), (0.685, 0.77), TEAL)
    arrow((0.625, 0.36), (0.77, 0.626), GOLD, 0.1)
    arrow((0.625, 0.31), (0.685, 0.31), TEAL)
    ax.text(
        0.50,
        0.055,
        f"Native authorization/accounting fixtures: {validation['tests']['passed']} tests passed. Live ENS: not executed.",
        ha="center",
        fontsize=9.7,
        color=GREY,
    )
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.98)
    save(
        fig,
        "04_capability_lineage",
        "Observed artifact lineage. Six synthetic origin solutions produce the rank 48 work basis. "
        "Optional Gym selects four additional full solutions from 20 development probes and refits at the "
        "same rank. Work and Gym versions enter the final prototype separately. The Gym artifact is also "
        "loaded by a separate recipient process on four fresh inputs with digest verification. Native "
        "authorization/accounting checks are local fixtures; neither live ENS authentication nor protected "
        "production admission is claimed. No real customer payment is attributed to the origin solves.",
    )


def break_even() -> None:
    data = read(TECH / "results_final_prototype" / "selection_results.json")["summary"]
    saved = data["adaptive_fallback"]["seconds_total"] - data["work48_fallback"]["seconds_total"]
    dollars_per_core_hour = 0.5
    per_service = saved * dollars_per_core_hour / 3600
    budgets = [20, 61]
    thresholds = [b / per_service for b in budgets]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    workloads = np.geomspace(1000, 5_000_000, 300)
    for budget, threshold, color in zip(budgets, thresholds, [TEAL, GOLD]):
        ax.plot(
            workloads / 1e6, workloads * per_service - budget, lw=2, color=color, label=f"${budget} additional cost"
        )
        ax.scatter([threshold / 1e6], [0], color=color, s=40, zorder=4)
        ax.annotate(
            f"{threshold / 1e6:.3f} million",
            (threshold / 1e6, 0),
            xytext=(0, 13 if budget == 20 else -23),
            textcoords="offset points",
            ha="center",
            color=color,
            fontsize=10,
        )
    ax.axhline(0, color=GREY, lw=0.9)
    ax.set_xlim(0, 5)
    ax.set_ylim(-75, 200)
    ax.set_xlabel("Repeated eight-case services (millions)")
    ax.set_ylabel("CPU savings less added cost (USD)")
    ax.grid(color=RULE, lw=0.7)
    ax.legend(loc="upper left", frameon=False)
    fig.subplots_adjust(left=0.14, right=0.98, bottom=0.2, top=0.96)
    NUMBERS["cpu_only_break_even"] = {
        "saved_seconds_per_eight_case_service": saved,
        "assumed_usd_per_core_hour": dollars_per_core_hour,
        "saved_usd_per_service": per_service,
        "additional_budgets_usd": budgets,
        "break_even_service_counts": thresholds,
    }
    save(
        fig,
        "05_cpu_only_break_even",
        "Deliberately favorable, CPU-only sensitivity using the fresh 7401 work-basis saving over ordinary "
        "adaptive tools. The assumed price is $0.50 per core-hour and the hypothetical added budgets are $20 "
        "and $61. The two figures are aggregate added-cost budgets; any upkeep already budgeted is included once. Additional unbudgeted upkeep, failed transfer, obsolescence, opportunity cost and delay are excluded. "
        "The thresholds are therefore optimistic lower bounds for these cost hypotheses, not workload "
        "forecasts or proven commercial payback. No higher selling price or demand is credited to a "
        "capability that did not uniquely enable the service.",
    )


def economics() -> None:
    path = STUDY / "results" / "economics" / "economic_results.json"
    trajectories = STUDY / "results" / "economics" / "economic_paths.json"
    if not path.exists() or not trajectories.exists():
        NUMBERS["economic_figures"] = "Pending economic result files; technical figures complete."
        return
    results = read(path)
    curves = read(trajectories)
    base = curves["competent_beta"]
    days = np.asarray([row["day"] + 1 for row in base])
    base_profit = np.asarray([row["profit"] for row in base])
    policies = ["private_work", "shared_work", "shared_gym", "selective"]
    labels = ["Private work", "Shared work (= library)", "Shared Gym", "Selective"]
    colors = [TEAL, GOLD, RED, NAVY]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for policy, label, color in zip(policies, labels, colors):
        delta = np.asarray([row["profit"] for row in curves[policy]]) - base_profit
        ax.plot(days, delta, label=label, color=color, lw=1.9)
        ax.scatter([days[-1]], [delta[-1]], color=color, s=22, zorder=4)
    ax.axhline(0, color=GREY, lw=0.9, ls=(0, (3, 3)))
    ax.set_xlabel("Simulated operating day")
    ax.set_ylabel("Profit difference vs Beta (USD)")
    ax.set_xlim(0, days[-1] + 2)
    ax.grid(color=RULE, lw=0.7)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.47), ncol=2, frameon=False, fontsize=10)
    fig.subplots_adjust(left=0.14, right=0.98, top=0.97, bottom=0.30)
    save(
        fig,
        "06_cumulative_incremental_profit",
        "Conditional simulated cumulative operating profit relative to an equally resourced competent-Beta "
        "enterprise. Lines average the paired confirmation seeds under the frozen base assumptions. "
        "Revenue, buyer decisions, market prices and commercial overhead are simulated, while numerical "
        "cost differences come from executed technical evidence. Shared work and an ordinary library with "
        "identical contents and permissions have identical outcomes. The graph does not validate demand "
        "or demonstrate earned revenue. Forced investment treatments are explanatory ablations.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6))
    for policy, label, color, linestyle in [
        ("competent_beta", "Competent Beta", NAVY, "-"),
        ("private_work", "Private work", TEAL, "--"),
        ("shared_gym", "Shared Gym", GOLD, ":"),
        ("selective", "Selective", RED, "-."),
    ]:
        axes[0].plot(days, [row["offers"] for row in curves[policy]], color=color, lw=1.7, ls=linestyle, label=label)
    axes[0].set_ylim(0.8, 3.2)
    axes[0].set_yticks([1, 2, 3])
    axes[0].set_ylabel("Mean active offerings")
    axes[0].set_xlabel("Simulated operating day")
    axes[0].set_title("Portfolio qualification", loc="left")
    selective = curves["selective"]
    axes[1].plot(
        days, np.asarray([row["profit"] for row in selective]) / 1000, lw=1.9, color=NAVY, label="Operating profit"
    )
    axes[1].plot(
        days, np.asarray([row["available"] for row in selective]) / 1000, lw=1.9, color=TEAL, label="Available funds"
    )
    axes[1].set_ylabel("Simulated USD (thousands)")
    axes[1].set_xlabel("Simulated operating day")
    axes[1].set_title("Conditional balances", loc="left")
    axes[1].text(0.035, 0.94, "Assumed demand and prices", transform=axes[1].transAxes, fontsize=9, color=GREY)
    if all(np.allclose([row["offers"] for row in curves[p]], [row["offers"] for row in base]) for p in policies):
        axes[0].text(0.04, 0.15, "All policy curves overlap", transform=axes[0].transAxes, fontsize=9.5, color=GREY)
    for ax in axes:
        ax.grid(color=RULE, lw=0.7)
        ax.set_xlim(1, days[-1])
        ax.legend(
            loc="upper center", bbox_to_anchor=(0.5, -0.28), frameon=False, fontsize=9.3, ncol=2 if ax is axes[0] else 1
        )
    fig.subplots_adjust(left=0.085, right=0.98, top=0.87, bottom=0.28, wspace=0.36)
    save(
        fig,
        "07_portfolio_and_available_funds",
        "Conditional simulated portfolio and balances. Left: average active offerings across confirmation "
        "seeds; every enterprise may qualify the same three technically deliverable services. Growth in "
        "this count does not establish a specialist-created frontier crossing or a new market. Right: "
        "the selective policy's operating profit and available funds are distinct. Available funds include "
        "the remaining seed capital and reflect collections, obligations and reserves; seed capital is "
        "not revenue. Market and buyer assumptions remain unvalidated.",
    )
    scenarios = list(results["scenarios"])
    scenario_labels = {
        "base": "Base hypotheses",
        "low_demand": "Low demand",
        "low_wtp": "Low willingness to pay",
        "high_failures": "High failures",
        "high_integration": "High integration costs",
        "poor_transfer": "Poor transfer",
        "capacity_pressure": "Capacity pressure",
        "regime_shift": "Regime shift",
        "slow_collections": "Slow collections",
        "rapid_frontier_progress": "Rapid Beta progress",
        "high_compute_price": "High compute price",
        "growth_financed_by_surplus": "Surplus-funded growth",
    }
    matrix = np.asarray(
        [
            [results["scenarios"][scenario][policy]["incremental_profit_vs_beta"]["mean"] for policy in policies]
            for scenario in scenarios
        ]
    )
    limit = max(1, float(np.max(np.abs(matrix))))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("loss_neutral_gain", [RED, "#FFFFFF", TEAL])
    fig, ax = plt.subplots(figsize=(7.2, 4.9))
    im = ax.imshow(matrix, cmap=cmap, vmin=-limit, vmax=limit, aspect="auto")
    for i in range(len(scenarios)):
        for j in range(len(policies)):
            value = matrix[i, j]
            ax.text(
                j,
                i,
                f"{value:+,.0f}",
                ha="center",
                va="center",
                fontsize=10,
                color="white" if abs(value) > 0.6 * limit else NAVY,
            )
    ax.set_yticks(range(len(scenarios)), [scenario_labels.get(s, s.replace("_", " ")) for s in scenarios])
    ax.set_xticks(range(4), ["Private\nwork", "Shared\nwork", "Shared\nGym", "Selective"])
    ax.tick_params(length=0, pad=7)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.04)
    cbar.set_label("Paired incremental profit vs Beta (simulated USD)")
    fig.subplots_adjust(left=0.30, right=0.94, bottom=0.13, top=0.98)
    save(
        fig,
        "08_economic_stress_frontier",
        "Mean paired incremental profit relative to competent Beta across the frozen stress scenarios. "
        "Cells are conditional simulation outcomes, rounded to the nearest dollar, not forecasts or customer evidence. Parameter changes "
        "stress demand, pricing, failures, integration, transfer, capacity, distribution shift, collection "
        "delays, ordinary-tool progress, compute price and growth financed by available surplus. "
        "Monte Carlo intervals and full assumptions remain in the machine-readable evidence; simulation "
        "precision does not remove uncertainty in those assumptions.",
    )
    NUMBERS["economic_figures"] = {
        "execution_status": results["execution_status"],
        "seeds": results["seeds"],
        "base_incremental_profit": {p: results["scenarios"]["base"][p]["incremental_profit_vs_beta"] for p in policies},
        "base_profit": {p: results["scenarios"]["base"][p]["profit"] for p in ["competent_beta", *policies]},
        "final_portfolio_count": {p: curves[p][-1]["offers"] for p in curves},
    }


def main() -> None:
    style()
    acceptance()
    feasibility()
    proposal()
    lineage()
    break_even()
    economics()
    (OUT / "figure_captions.json").write_text(json.dumps(CAPTIONS, indent=2))
    (OUT / "figure_numbers.json").write_text(json.dumps(NUMBERS, indent=2))
    (OUT / "figure_source_manifest.json").write_text(
        json.dumps(
            {str(p.relative_to(STUDY)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCES)}, indent=2
        )
    )
    print(json.dumps({"figures": list(CAPTIONS), "numbers": NUMBERS.get("cpu_only_break_even")}, indent=2))


if __name__ == "__main__":
    main()
