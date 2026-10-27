# SPDX-License-Identifier: Apache-2.0
"""Build publication figures from saved evidence, without running any model.

The witness panels show actual local operation counts. Recipient panels show
deterministic, assumption-dependent cost arithmetic. They are intentionally
separate, and no operation count is converted to dollars, time or model tokens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/agi-alpha-matplotlib")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402


INK = "#342657"
PURPLE = "#7657A3"
TEAL = "#187A78"
GOLD = "#A77A31"
GREY = "#6D7785"
LIGHT = "#E8E5ED"
TEXT = "#2D2934"
NEGATIVE = "#A03A48"


def load_evidence(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Evidence must be a JSON object: {path}")
    return data, hashlib.sha256(raw).hexdigest()


def number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Expected a finite numeric evidence value, received {value!r}")
    return float(value)


def style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.titlesize": 10.5,
        "axes.titleweight": "semibold",
        "axes.labelsize": 9.2,
        "axes.edgecolor": GREY,
        "axes.labelcolor": TEXT,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 9.2,
        "xtick.color": GREY,
        "ytick.color": TEXT,
        "text.color": TEXT,
        "legend.fontsize": 8.5,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })


def decorate(ax: Any, *, xgrid: bool = False, ygrid: bool = False) -> None:
    ax.set_axisbelow(True)
    ax.grid(axis="x" if xgrid else "y", color=LIGHT, linewidth=0.65, visible=xgrid or ygrid)
    for spine in ax.spines.values():
        spine.set_linewidth(0.6)
    ax.tick_params(length=3, width=0.6)


def save_figure(fig: Any, name: str, output: Path, title: str, source_note: str) -> list[dict[str, Any]]:
    paths = []
    for extension in ("pdf", "png"):
        target = output / f"{name}.{extension}"
        if extension == "pdf":
            metadata = {"Title": title, "Author": "Independent research edition prepared for MONTREAL.AI",
                        "Subject": source_note, "CreationDate": None, "ModDate": None}
            fig.savefig(target, metadata=metadata)
        else:
            fig.savefig(target, dpi=240, metadata={"Title": title, "Description": source_note})
        raw = target.read_bytes()
        paths.append({"path": str(target), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    plt.close(fig)
    return paths


def witness_figure(data: dict[str, Any], output: Path, digest: str) -> tuple[list, dict]:
    reuse = data["results"]["recipient_reuse"]
    if reuse["all_fresh_queries_match_equal_intelligence_baseline"] is not True:
        raise ValueError("The witness no longer supports the stated identical-output comparison")
    cold = reuse["cold_counts"]
    shared = reuse["shared_counts_including_creator_and_all_receivers"]
    definitions = [
        ("construction_transitions", "A  Construction\ntransitions"),
        ("certificate_inequalities", "B  Certificate\ninequalities"),
        ("certificate_witness_multiplications", "C  Witness\nmultiplications"),
    ]
    figure, axes = plt.subplots(1, 3, figsize=(7.2, 3.6))
    figure.subplots_adjust(left=0.16, right=0.98, bottom=0.37, top=0.68, wspace=0.33)
    figure.text(0.04, 0.95, "Sharing moves work between construction and checking", color=INK,
                fontsize=13, fontweight="semibold", va="top")
    figure.text(0.04, 0.845,
                f"EXECUTED LOCAL SOFTWARE  |  {len(reuse['queries'])} fresh same-family queries; identical outputs",
                color=GREY, fontsize=8.5)
    plotted = {}
    for index, (ax, (key, heading)) in enumerate(zip(axes, definitions)):
        values = [number(cold[key]), number(shared[key])]
        plotted[key] = {"cold": values[0], "shared_including_creator_and_all_recipients": values[1]}
        ax.barh([1, 0], values, color=[GREY, PURPLE], height=0.42)
        ax.set_title(heading, loc="left", pad=11)
        ax.set_yticks([1, 0], ["Reconstruct\nper query", "Shared\nfrontier"] if index == 0 else ["", ""])
        ax.set_ylim(-0.6, 1.6)
        ax.set_xlim(0, max(values) * 1.34)
        ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=3, integer=True))
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda value, _: f"{value / 1000:g}k"))
        ax.set_xlabel("Count in this operation class", labelpad=6, fontsize=8)
        for y, value in zip([1, 0], values):
            ax.text(value + max(values) * 0.035, y, f"{value:,.0f}", va="center", fontsize=9.5)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        decorate(ax, xgrid=True)
    states = int(number(reuse["fresh_selection_states_in_both_arms"]))
    payload = int(number(reuse["recipient_payload_bytes_hashed_in_shared_arm"]))
    figure.text(0.04, 0.18,
                f"Both branches: {states:,} selection states. Shared branch: {payload:,} payload bytes hashed.",
                fontsize=8.3, va="top")
    figure.text(0.04, 0.09,
                "Shared counts include creator and recipients. Full certificate replay is retained.\n"
                "Operation classes are not interchangeable; no net time, token or dollar benefit is established.",
                fontsize=8, color=GREY, va="top", linespacing=1.45)
    return save_figure(figure, "witness", output, "Actual local witness operation counts",
                       f"Mechanism evidence SHA256 {digest}; no monetary calibration."), plotted


def recipient_figure(data: dict[str, Any], output: Path, digest: str) -> tuple[list, dict]:
    if data["evidence_kind"] != "deterministic-modeled-cost-comparison":
        raise ValueError("Recipient panel requires the explicitly modeled evidence category")
    probes = data["frozen_recipient_probes"]
    labels = {
        "competent-frontier-reconstructor": "Competent reconstructor",
        "ordinary-experienced": "Ordinarily experienced",
        "ordinary-specialist": "Ordinary specialist",
        "partial-equivalent": "One equivalent held",
        "already-equivalent": "All equivalents held",
    }
    figure = plt.figure(figsize=(7.2, 6.5))
    grid = figure.add_gridspec(2, 1, height_ratios=[1.45, 1.0], left=0.29, right=0.96,
                              bottom=0.31, top=0.78, hspace=0.90)
    delivery = figure.add_subplot(grid[0])
    threshold = figure.add_subplot(grid[1])
    box = delivery.get_position()
    delivery.set_position([box.x0, box.y0, 0.50, box.height])
    figure.text(0.04, 0.965, "Recipient advantage depends on what Beta already holds", color=INK,
                fontsize=13, fontweight="semibold", va="top")
    figure.text(0.04, 0.91, "MODELED ANALYTICAL PANEL  |  Fixed workloads and declared branch probabilities",
                color=GREY, fontsize=8.4)
    delivery.set_title("A  Paired mission costs at initial Beta", loc="left", pad=26)
    maxima = []
    plotted_probes = []
    for index, probe in enumerate(probes):
        baseline = number(probe["beta"]["cost_usd"])
        retained = number(probe["shared_expected_cost_usd"])
        saving = number(probe["expected_delivery_saving_usd"])
        if not math.isclose(baseline - retained, saving, abs_tol=1e-6):
            raise ValueError("Recipient probe cost/saving arithmetic does not reconcile")
        y = len(probes) - 1 - index
        delivery.plot([retained, baseline], [y, y], color=LIGHT, linewidth=6, solid_capstyle="round", zorder=1)
        delivery.scatter([baseline], [y], color=GREY, marker="o", s=36, zorder=3)
        delivery.scatter([retained], [y], color=TEAL, marker="D", s=29, zorder=4)
        selected = probe["selected_components"]
        label = f"${saving:,.0f} expected\nsaving" if selected else "$0 expected gain;\noptional nonuse"
        delivery.text(1.04, y, label, va="center", ha="left", fontsize=8.4,
                      transform=delivery.get_yaxis_transform(), color=TEAL if selected else GREY)
        maxima += [baseline, retained]
        plotted_probes.append({"recipient": probe["recipient"], "beta_cost": baseline,
                               "shared_expected_cost": retained, "expected_saving": saving,
                               "selected_components": selected})
    delivery.set_yticks(list(reversed(range(len(probes)))), [labels.get(p["recipient"], p["recipient"]) for p in probes])
    delivery.set_xlim(1500, max(maxima) * 1.06)
    delivery.set_ylim(-0.6, len(probes) - 0.35)
    delivery.set_xlabel("Modeled required mission cost (USD)", labelpad=5)
    delivery.xaxis.set_major_locator(mticker.MultipleLocator(500))
    delivery.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    delivery.legend(handles=[
        Line2D([], [], marker="o", linestyle="none", color=GREY, markersize=5, label="Competent Beta"),
        Line2D([], [], marker="D", linestyle="none", color=TEAL, markersize=5, label="Candidate available"),
    ], loc="upper left", bbox_to_anchor=(-0.01, 1.12), ncol=2, borderaxespad=0)
    decorate(delivery, xgrid=True)
    delivery.spines["left"].set_visible(False)
    delivery.tick_params(axis="y", length=0)

    lifecycle = data["lifecycle"]
    new_rd = data["optional_new_rd_comparison"]
    planned = int(number(lifecycle["planned_reuse"]))
    if planned != int(number(new_rd["planned_reuse"])):
        raise ValueError("The compared lifecycle cases must share planned reuse")
    rows = [(lifecycle, "B: retain paid-job asset", TEAL), (new_rd, "B + C: separate new R&D", NEGATIVE)]
    max_threshold = max(number(row[0]["required_reuses_at_declared_lifetime"]) for row in rows)
    threshold.set_title("B  Strict positive-net lifecycle reuse threshold", loc="left", pad=16)
    for y, (result, _, color) in zip([1, 0], rows):
        count = number(result["required_reuses_at_declared_lifetime"])
        threshold.barh(y, count, height=0.32, color=color, alpha=0.9)
        threshold.text(count + 2, y, f"{int(count)} uses", va="center", color=color, fontsize=9)
        net = number(result["project_net"])
        threshold.text(0, y - 0.28, f"Net at {planned} planned uses: {'+' if net >= 0 else '-'}${abs(net):,.0f}",
                       color=color, fontsize=8.3, va="center")
    threshold.axvline(planned, color=GOLD, linestyle=(0, (3, 2)), linewidth=1.2)
    threshold.text(planned + 2, 1.54, f"{planned} planned", color=GOLD, fontsize=8.5)
    threshold.set_yticks([1, 0], [row[1] for row in rows])
    threshold.set_ylim(-0.55, 1.70)
    threshold.set_xlim(0, max_threshold * 1.28)
    threshold.set_xlabel("Uses needed for positive prospective net benefit", labelpad=6)
    threshold.xaxis.set_major_locator(mticker.MultipleLocator(20))
    threshold.spines["left"].set_visible(False)
    threshold.tick_params(axis="y", length=0)
    decorate(threshold, xgrid=True)
    lifetime = int(data["protocol"]["plan"]["useful_lifetime_weeks"])
    figure.text(0.04, 0.20,
                f"Lifecycle panel: {lifetime} weeks; 75% competent reconstructors, 25% already equivalent; moving Beta.\n"
                "Primary retention includes failure and upkeep. Separate R&D includes its stated failed-construction costs.\n"
                "Thresholds hold lifetime and mean saving fixed; they are not observed demand or customer revenue.",
                fontsize=8.1, color=GREY, linespacing=1.5, va="top")
    figure.text(0.04, 0.075,
                "No live frontier missions. No measured Alpha. Zero declared uncertainty allowance; no confidence interval.\n"
                "Source-job A is not supplied in this standalone panel and is not recharged to prospective B/C.",
                fontsize=8.1, color=GREY, linespacing=1.5, va="top")
    plots = {"recipient_probes": plotted_probes,
             "lifecycle_thresholds": [{"case": label, "required_uses": result["required_reuses_at_declared_lifetime"],
                                        "planned_uses": result["planned_reuse"], "project_net": result["project_net"]}
                                       for result, label, _ in rows]}
    return save_figure(figure, "recipients", output, "Modeled heterogeneous recipients and reuse thresholds",
                       f"Recipient evidence SHA256 {digest}; deterministic assumptions, not empirical effects."), plots


def thresholds_figure(data: dict[str, Any], output: Path, digest: str) -> tuple[list, dict]:
    definitions = [
        ("overlap", "A  Existing equivalents", "Recipient population already equivalent", lambda x: f"{x:.0%}"),
        ("validation_overhead", "B  Receiving workload", "Integration/checking workload factor", lambda x: f"{x:g}x"),
        ("frontier_improvement", "C  Moving Beta", "Annual reconstruction improvement", lambda x: f"{x:.0%}"),
    ]
    figure, axes = plt.subplots(1, 3, figsize=(7.2, 3.85), sharey=True)
    figure.subplots_adjust(left=0.09, right=0.98, bottom=0.40, top=0.73, wspace=0.27)
    figure.text(0.04, 0.96, "More overlap or receiving work raises the reuse requirement", color=INK,
                fontsize=12.6, fontweight="semibold", va="top")
    figure.text(0.04, 0.855, "MODELED RETENTION SENSITIVITY  |  One factor varies; no empirical efficacy claim",
                color=GREY, fontsize=8.4)
    planned = int(number(data["lifecycle"]["planned_reuse"]))
    plotted = {}
    for ax, (parameter, heading, xlabel, formatter) in zip(axes, definitions):
        rows = sorted((row for row in data["sensitivity"] if row["parameter"] == parameter),
                      key=lambda row: row["value"])
        if not rows:
            raise ValueError(f"Missing declared sensitivity rows: {parameter}")
        plotted[parameter] = []
        for x, row in enumerate(rows):
            value = row["required_reuses_at_declared_lifetime"]
            plotted[parameter].append({"value": row["value"], "required_uses": value})
            if value is None:
                ax.text(x, 0.38, "None", color=GREY, ha="center", fontsize=8,
                        transform=ax.get_xaxis_transform())
            else:
                count = number(value)
                ax.bar(x, count, width=0.58, color=PURPLE)
                ax.text(x, count + 2, f"{int(count)}", ha="center", fontsize=9)
        ax.axhline(planned, color=GOLD, linestyle=(0, (3, 2)), linewidth=1.0)
        ax.set_xticks(range(len(rows)), [formatter(number(row["value"])) for row in rows])
        ax.set_xlim(-0.55, len(rows) - 0.45)
        ax.set_ylim(0, max(90, planned * 1.13))
        ax.set_title(heading, loc="left", pad=11)
        ax.set_xlabel(xlabel, fontsize=8.3, labelpad=8)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
        decorate(ax, ygrid=True)
    axes[0].set_ylabel("Required reuse count")
    figure.text(0.04, 0.20,
                f"Dashed line: {planned} planned uses. 'None': no finite threshold under the supplied cost assumptions;\n"
                "it is not zero uses. Candidates are optionally unused when they do not improve the competent baseline.",
                fontsize=8.0, color=GREY, linespacing=1.45, va="top")
    figure.text(0.04, 0.085,
                "Fixed 40-week lifecycle allocation; conditional mean savings. A stronger Beta means less reconstruction work,\n"
                "not an assumed intelligence or acceptance multiplier. These are separate analytical scenarios, not selected policies.",
                fontsize=7.9, color=GREY, linespacing=1.45, va="top")
    return save_figure(figure, "recipient_thresholds", output, "Modeled retention reuse-threshold sensitivity",
                       f"Recipient evidence SHA256 {digest}; no measured demand or empirical confidence interval."), plotted


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--witness", type=Path, default=root / "evidence/mechanism_witness.json")
    parser.add_argument("--recipients", type=Path, default=root / "results/recipient_ablation.json")
    parser.add_argument("--output", type=Path, default=root / "paper/figures")
    args = parser.parse_args()
    witness, witness_hash = load_evidence(args.witness)
    recipients, recipient_hash = load_evidence(args.recipients)
    args.output.mkdir(parents=True, exist_ok=True)
    style()
    outputs, values = [], {}
    for name, function, data, digest in (
        ("witness", witness_figure, witness, witness_hash),
        ("recipients", recipient_figure, recipients, recipient_hash),
        ("recipient_thresholds", thresholds_figure, recipients, recipient_hash),
    ):
        artifacts, plotted = function(data, args.output, digest)
        outputs.extend(artifacts)
        values[name] = plotted
    receipt = {
        "operation": "read-only evidence postprocessing; no model or simulation execution",
        "matplotlib_version": matplotlib.__version__,
        "inputs": {str(args.witness): witness_hash, str(args.recipients): recipient_hash},
        "outputs": outputs,
        "plotted_values": values,
        "interpretation": {
            "witness": "actual local finite software operation counts, separate noninterchangeable classes",
            "recipients": "deterministic modeled costs and thresholds; not observed frontier or customer outcomes",
        },
    }
    manifest = args.output / "figure_provenance.json"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": str(manifest), "outputs": outputs,
                      "total_artifact_bytes": sum(item["bytes"] for item in outputs)}, indent=2))


if __name__ == "__main__":
    main()
