# SPDX-License-Identifier: Apache-2.0
"""Original vector research figures generated only from retained observations."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "paper/figures"
INK, PURPLE, TEAL, GOLD, GRAY = "#151326", "#6236B0", "#087F79", "#AF681E", "#777182"
COLORS = [PURPLE, TEAL, GOLD, "#365BA0"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.titlesize": 12,
                     "axes.titleweight": "bold", "axes.labelsize": 10.5, "axes.labelcolor": INK,
                     "text.color": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#C7C0D2", "grid.color": "#E4DFEA", "grid.linewidth": .6,
                     "pdf.fonttype": 42, "svg.fonttype": "none", "savefig.facecolor": "white"})


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", metadata={"Creator": "Writer 9 reproducible vector figure"})
    plt.close(fig)


def main() -> None:
    n = json.loads((ROOT / "results/numerical_analysis.json").read_text())
    d = json.loads((ROOT / "results/decision-confirmation/decision_summary.json").read_text())
    extra = json.loads((ROOT / "results/decision_analysis.json").read_text())
    names = json.loads((ROOT / "protocol.json").read_text())["matrices_in_order"]
    stats = {(r["matrix"], r["q"], r["method"]): r for r in n["statistics"]}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), gridspec_kw={"width_ratios": [1, 1.1]})
    ax = axes[0]
    methods = [("cold_direct", "Repeated setup", GRAY), ("native_cached", "Conventional reuse", TEAL),
               ("certified_ready", "Certified recipe", PURPLE)]
    for j, (method, label, color) in enumerate(methods):
        ax.barh(np.arange(4) + (j - 1) * .23,
                [1000 * stats[name, 16, method]["total_seconds"] for name in names], height=.21, label=label, color=color)
    ax.set_yticks(range(4), names); ax.invert_yaxis(); ax.set_xscale("log")
    ax.set_xlabel("Full batch wall time (ms, log scale)"); ax.set_title("A  Reuse delivers the speed")
    ax.grid(axis="x", zorder=0); ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(-.12, -.20), fontsize=9, frameon=False, ncol=1)
    ax = axes[1]
    for name, color in zip(names, COLORS):
        cold = [1000 * stats[name, q, "certified_ready"]["total_seconds"] for q in (1, 4, 16)]
        ready = [1000 * stats[name, q, "certified_ready"]["response_seconds"] for q in (1, 4, 16)]
        ax.plot(cold, ready, "o-", color=color, ms=4, label=name)
        for q, x, y in zip((1, 4, 16), cold, ready):
            ax.annotate(str(q), (x, y), xytext=(4, 3), textcoords="offset points", fontsize=9, color=color)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Cold full-batch wall time (ms)")
    ax.set_ylabel("Ready solve + fresh check (ms)")
    ax.set_title("B  Preparation moves the deadline")
    ax.grid(which="major"); ax.legend(fontsize=9, frameon=False, loc="lower right")
    fig.tight_layout(w_pad=2)
    save(fig, "readiness_frontier")

    f = n["forecasts"]
    fig, axes = plt.subplots(1, 2, figsize=(8.7, 3.1), gridspec_kw={"width_ratios": [1.2, 1]})
    ax = axes[0]
    ax.plot([0, 1], [0, 1], "--", color=GRAY, lw=1, label="Perfect reliability")
    bins = f["bins"]
    ax.plot([b["probability"] for b in bins], [b["observed"] for b in bins], color=PURPLE, lw=1)
    ax.scatter([b["probability"] for b in bins], [b["observed"] for b in bins],
               s=[20 + b["n"] * .15 for b in bins], color=PURPLE, edgecolor="white", zorder=3)
    ax.set(xlim=(-.03, 1.03), ylim=(-.04, 1.04), xlabel="Frozen probability", ylabel="Observed local frequency")
    ax.set_title("A  All deadlines: descriptive reliability")
    ax.text(.05, .92, "Point area reflects bin count", transform=ax.transAxes, fontsize=9)
    ax.grid()
    ax = axes[1]
    primary = next(r for r in f["deadline_strata"] if r["primary"])
    ax.barh([1, 0], [primary["base_brier"], primary["brier"]], color=[GRAY, PURPLE], height=.5)
    ax.set_yticks([1, 0], ["Pooled base rate", "Conditional forecast"])
    for y, value in [(1, primary["base_brier"]), (0, primary["brier"])]:
        ax.text(value + .005, y, f"{value:.3f}", va="center", fontsize=9)
    ax.set_xlim(0, .32); ax.set_xlabel("Brier score · lower is better")
    ax.set_title("B  Preregistered primary deadline")
    fig.tight_layout(w_pad=2.5)
    save(fig, "calibration")

    regimes = ["nominal", "uninformative_forecast", "costly_premature", "delayed_demand", "fast_imitation", "distribution_shift"]
    labels = ["Nominal", "Uninformative signal", "Costly construction", "Delayed demand", "Fast imitation", "Reversed signal"]
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    for y, regime in enumerate(regimes):
        r = d["primary_comparisons"][regime]["differences"]["mission_credits"]
        mean = r["mean_difference"]; low, high = r["paired_seed_block_bootstrap_95"]
        color = TEAL if low > 0 else PURPLE if high >= 0 else GOLD
        ax.errorbar(mean, y, xerr=[[mean-low], [high-mean]], fmt="o", color=color, capsize=3, ms=6)
        ax.text(.147, y, f"{mean:+.4f}  [{low:+.4f}, {high:+.4f}]", va="center", fontsize=9, family="DejaVu Sans Mono")
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_yticks(range(6), labels); ax.invert_yaxis()
    ax.set_xlim(-.15, .41); ax.set_xticks([-.10, -.05, 0, .05, .10])
    ax.set_xlabel("Constructive foresight − preregistered comparator (assumed mission credits / episode)")
    ax.set_title("The credible-alternative test", loc="left")
    ax.spines["bottom"].set_bounds(-.15, .14)
    ax.text(.147, -.65, "Mean      95% paired seed-block interval", fontsize=9, color=GRAY)
    fig.tight_layout()
    save(fig, "causal_comparison")

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.25), gridspec_kw={"width_ratios": [1, 1]})
    ax = axes[0]
    records = [("protocol.json", "created_utc"), ("results/calibration/summary.json", "issued_utc"),
               ("results/forecast_freeze.json", "issued_utc"), ("results/confirmation/summary.json", "issued_utc"),
               ("results/confirmation/summary.json", "completed_utc"), ("evidence/decision-calibration-invocation.json", "issued_utc"),
               ("evidence/decision-confirmation-invocation.json", "issued_utc")]
    times = []
    for path, field in records:
        stamp = datetime.fromisoformat(json.loads((ROOT / path).read_text())[field].replace("Z", "+00:00"))
        times.append(stamp.minute + stamp.second / 60 + stamp.microsecond / 60e6)
    tasks = ["Protocol fixed", "Calibration starts", "Forecasts frozen", "Held-out start", "Held-out finish", "Policy calibration", "Policy holdout"]
    ax.plot(times, range(7), "o-", color=PURPLE, ms=5, lw=1)
    ax.set(xlim=(1, 31), ylim=(6.6, -.6), yticks=range(7), yticklabels=tasks,
           xticks=[5, 10, 15, 20, 25, 30], xlabel="Minutes after 02:00 UTC · 24 October 2026")
    ax.tick_params(axis="y", labelsize=9);ax.grid(axis="x")
    ax.set_title("A  Evidence before outcomes", loc="left")
    for side in ["left", "right", "top"]:ax.spines[side].set_visible(False)
    ax = axes[1]
    ax.barh([1, 0], [2.427001, 3.206201], color=PURPLE, height=.52, label="Native execution + retention")
    ax.barh([1, 0], [.00931 + .02586, .00634 + .04420], color=TEAL, height=.52, label="Kernel + separate check (subset)")
    ax.set_yticks([1, 0], ["Initial run", "Restored run"]); ax.set_xlim(0, 3.7);ax.set_ylim(-.65, 1.95)
    ax.set_xlabel("Observed wall seconds")
    ax.set_title("B  Authority also has a cost", loc="left")
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    fig.tight_layout(w_pad=2)
    save(fig, "decision_timeline")

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    ax = axes[0]
    chosen = ["forecast_only", "wait_and_act", "static_expert", "adaptive_nonforecast", "adaptive_same_signal", "constructive_foresight"]
    labels_short = ["Forecast only", "Wait + build", "Fixed rule", "Adaptive, no signal", "Compiled, same signal", "Constructive foresight"]
    index = {(r["regime"], r["policy"]):r for r in d["policy_means"]}
    for y, policy in enumerate(chosen):
        r = index["nominal", policy]
        ax.barh(y, r["accepted"], color=TEAL, height=.55)
        ax.barh(y, -r["accounted_cost_seconds"] / d["clock_seconds"], color=GOLD, height=.55)
        ax.plot(r["mission_credits"], y, "D", color=PURPLE, ms=5)
    ax.axvline(0, color=GRAY, lw=.8); ax.set_yticks(range(6), labels_short); ax.invert_yaxis()
    ax.set_xlabel("Assumed credits per episode")
    ax.set_title("A  Deliveries, costs and net value", loc="left")
    ax.plot([], [], "s", color=TEAL, label="Accepted count");ax.plot([], [], "s", color=GOLD, label="Accounted cost")
    ax.plot([], [], "D", color=PURPLE, label="Net")
    ax.legend(fontsize=9, frameon=False, loc="lower left", bbox_to_anchor=(-.02, -.42), ncol=3)
    ax = axes[1]
    for regime, color, label in [("nominal", PURPLE, "Nominal"), ("delayed_demand", TEAL, "Delayed demand"),
                                 ("distribution_shift", GOLD, "Reversed signal")]:
        group = sorted([r for r in extra["sensitivity"] if r["regime"] == regime], key=lambda r:r["credit_per_accepted"])
        x = [r["credit_per_accepted"] for r in group];y = [r["mean"] for r in group]
        ax.plot(x, y, "o-", color=color, label=label, ms=4)
        ax.fill_between(x, [r["paired_seed_block_95"][0] for r in group], [r["paired_seed_block_95"][1] for r in group], color=color, alpha=.10)
    ax.axhline(0, color=GRAY, lw=.8);ax.set_xticks([.25, .5, .75, 1])
    ax.set_xlabel("Assumed credit per accepted request")
    ax.set_ylabel("CF − fixed-rule net credits")
    ax.set_title("B  A value assumption can erase a gain", loc="left")
    ax.legend(fontsize=9, frameon=False);ax.grid(axis="y")
    fig.tight_layout(w_pad=2)
    save(fig, "value_decomposition")
    print(json.dumps({"figures": 5, "formats": ["PDF", "SVG"], "source": str(Path(__file__).resolve())}))


if __name__ == "__main__":
    main()
