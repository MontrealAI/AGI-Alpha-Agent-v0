# SPDX-License-Identifier: Apache-2.0
"""Build edition 2.1 figures and tables from frozen observations and labeled models."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/alpha-opportunity-paper-mpl")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import expm

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
FIG = HERE / "figures"
COLORS = ["#758696", "#153d59", "#ad7e32"]


def read(name: str) -> Any:
    return json.loads((STUDY / name).read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: str) -> None:
    (HERE / name).write_text(value + "\n")


def figure(name: str, caption: str) -> str:
    return (
        r"\begin{figure}[H]\centering\includegraphics[width=0.97\linewidth]{figures/"
        + name
        + r".pdf}\caption{"
        + caption
        + r"}\end{figure}"
    )


def table(headers: list[str], rows: list[list[str]], caption: str, spec: str | None = None) -> str:
    spec = spec or "l" + "r" * (len(headers) - 1)
    return "\n".join(
        [
            r"\begin{table}[H]\centering\small",
            r"\begin{tabular}{@{}" + spec + r"@{}}\toprule",
            " & ".join(headers) + r" \\ \midrule",
        ]
        + [" & ".join(row) + r" \\" for row in rows]
        + [r"\bottomrule\end{tabular}", r"\caption{" + caption + "}", r"\end{table}"]
    )


def save(fig: Any, name: str) -> None:
    fig.savefig(FIG / (name + ".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(FIG / (name + ".png"), bbox_inches="tight", facecolor="white", dpi=220)
    plt.close(fig)


def cumulative_records() -> dict[str, Any]:
    source = STUDY / "economics/value_results/events.jsonl.gz"
    cached = HERE / "cumulative_net_value.json"
    signature = sha(source)
    if cached.exists():
        data: dict[str, Any] = json.loads(cached.read_text())
        if data["events_sha256"] == signature:
            return data
    histories: dict[tuple[str, str, int], dict[int, int]] = {}
    with gzip.open(source, "rb") as stream:
        for line in stream:
            if b'"profile": "reference"' not in line:
                continue
            record = json.loads(line)
            if "cash_cents" not in record:
                continue
            controller, policy = record["controller"], record["policy"]
            if policy not in ("ordinary_U", "expert_E", "shared_retention", "library_retention"):
                continue
            key = (controller, policy, record["seed"])
            days = histories.setdefault(key, {})
            days[record["day"]] = record["cash_cents"]
    aggregates: dict[str, list[list[float]]] = {}
    finals = {
        (x["controller"], x["policy"], x["seed"]): x
        for x in read("economics/value_results/confirmation.json")
        if x["profile"] == "reference"
    }
    for key, records in histories.items():
        last = 100000
        values = []
        for day in range(44):
            last = records.get(day, last)
            values.append((last - 100000) / 100)
        assert abs(values[-1] - finals[key]["profit_cents"] / 100) < 1e-8
        aggregates.setdefault(key[0] + "/" + key[1], []).append(values)
    data = {
        "label": "simulated cash contribution excluding seed; conditional on original assumptions",
        "events_sha256": signature,
        "days": list(range(44)),
        "groups": {k: {"worlds": len(v), "mean_usd": np.mean(v, axis=0).tolist()} for k, v in aggregates.items()},
    }
    cached.write_text(json.dumps(data, indent=2) + "\n")
    return data


def main() -> None:
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.titlepad": 11,
        }
    )
    scientific = read("opportunity/results/confirmation_summary.json")
    names = ("U", "E", "E_plus")
    rows = []
    for name in names:
        x = scientific["arms"][name]
        rows.append(
            [
                name.replace("_plus", "+"),
                f"{x['passed_missions']}/4",
                f"{x['elapsed_seconds']:.2f}",
                str(x["operations"]),
                str(x["logged_python_executions"]),
                "Unknown",
            ]
        )
    rows.append(["Conventional", "4/4", "Not matched", "Not matched", "Not matched", "Unknown"])
    scientific_tex = table(
        ["Configuration", "Accepted", "Hosted seconds", "Operations", "Python calls", "Complete cost"],
        rows,
        "Observed scientific campaign after all three recipients froze. Both request variants pass. Conventional construction was separate; its local function runtime is not compared with a hosted construction turn.",
    )
    scientific_tex += (
        "\nThe observed E--U and E+--E acceptance differences are both zero percentage points. No final mission fails. "
    )
    scientific_tex += (
        "All logged Python executions exit successfully; inspection calls are included in the execution count. "
    )
    scientific_tex += "U, E and E+ add ten, thirteen and twelve tests respectively, beyond the common smoke test. "
    scientific_tex += "Their complete final packets and reports remain frozen. These tests do not create additional independent mission families.\n"

    path = STUDY / "opportunity/instrument/model_reuse.py"
    spec = importlib.util.spec_from_file_location("paper_model_reuse", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    source = STUDY / "opportunity/protocol/public_case/sources/h4"
    model = module.build_generator(source)
    matrix, initial = np.array(model["matrix"]), np.array(model["initial"])
    weights = np.array([0 if n == "x_0ac" else 4 if n == "x_4ac" else n.count("k") for n in model["species"]])
    grid = np.linspace(0, 8, 161)
    curves = {str(c): [float(weights @ expm(c * matrix * t) @ initial) for t in grid] for c in (0.5, 3.0)}
    packet = read("opportunity/conventional/packet.json")
    equilibrium = packet["missions"][0]["mean_acetylation"]
    witness = module.clock_witness(source, scales=(0.5, 3.0), time=1.25)
    facts = {
        "evidence": "computed from supplied nominal model; clock scales are hypothetical",
        "model_time": grid.tolist(),
        "mean_acetylation": curves,
        "stationary_mean": equilibrium,
        "request_time": 1.25,
        "request_witness_max_state_difference": witness["transient_difference_max"],
        "equilibrium_difference": witness["stationary_difference_max"],
        "calibrated": packet["missions"][2],
    }
    write("scientific_figure_data.json", json.dumps(facts, indent=2))
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.55), gridspec_kw={"width_ratios": [1.28, 1]})
    for c, color in zip((0.5, 3.0), ("#153d59", "#ad7e32")):
        axes[0].plot(grid, curves[str(c)], color=color, linewidth=2.5, label=f"Hypothetical clock conversion {c:g}")
    axes[0].axhline(equilibrium, color="#087f8c", linestyle="--", linewidth=1.5, label="Same conditional equilibrium")
    axes[0].axvline(1.25, color="#777777", linestyle=":", linewidth=1)
    axes[0].set(
        xlabel="Requested time coordinate · hypothetical conversion",
        ylabel="Model mean acetylation",
        title="Same observations; different timed responses",
    )
    axes[0].legend(fontsize=7.5, loc="lower right", frameon=False)
    vals = [scientific["arms"][a]["elapsed_seconds"] for a in names]
    axes[1].bar(["U", "E", "E+"], vals, color=COLORS, width=0.55)
    for i, v in enumerate(vals):
        axes[1].text(i, v + 14, f"{v:.1f}s\n4/4 accepted", ha="center", fontsize=9)
    axes[1].set(ylim=(0, 490), ylabel="Observed hosted seconds", title="No accepted-output increment")
    axes[1].text(
        0.5,
        -0.21,
        "One recipient per arm · complete cost unknown",
        ha="center",
        transform=axes[1].transAxes,
        fontsize=8,
    )
    fig.tight_layout(w_pad=2)
    save(fig, "scientific_witness")
    scientific_tex += "\n" + figure(
        "scientific_witness",
        "Source-derived computational witness, not new biology. Clock conversions are hypothetical. At request time 1.25, the maximum state difference is 0.1433168 while the equilibrium agrees to numerical precision. The right panel reports single hosted observations, not a causal latency estimate.",
    )
    scientific_tex += (
        "\nThe accepted nominal model gives mean acetylation 0.3764225583 and a model spectral relaxation scale "
        "of 1.2815393182. Under the explicitly assumed conversion interval [0.4, 1.6] model units per minute, "
        "the propagated relaxation interval is [0.8009620739, 3.2038482954] minutes. It is a deterministic conditional "
        "interval, not measured biological timing or a confidence interval.\n"
    )
    write("scientific_results.tex", scientific_tex)
    write(
        "opportunity_macros.tex",
        r"\newcommand{\ScientificFinding}{U, E, E+ and an independently constructed conventional method each satisfy all four scientific mission requirements. The received instrument is executed correctly, but no incremental accepted-output advantage or complete-cost advantage is established.}",
    )

    timing = read("opportunity/arrangement/results/timing_examples.json")
    timing_rows = []
    labels = {
        "post_acceptance": "After acceptance",
        "refundable_escrow": "Refundable escrow",
        "accepted_milestone_escrow": "Useful accepted milestone",
    }
    for x in timing["cases"]:
        result = x["result"]
        timing_rows.append(
            [
                labels.get(x["mode"], x["mode"].replace("_", " ")),
                str(x["payment_release_delay_days"]),
                f"\\${result['required_opening_cash_cents'] / 100:,.0f}",
                f"\\${result['contribution_cents'] / 100:,.0f}",
            ]
        )
    at = (
        "The executed finite grid has sixty configuration records and 4,320 candidate evaluations. "
        "Its zero-saving reference selects conventional delivery for P2 and P3 at the arbitrary diagnostic "
        "price of \\$300 each with refundable escrow. Supplied scenario weights yield \\$193.50 expected "
        "contribution, \\$300 successful contribution, a \\$40 worst named loss and \\$230 required opening "
        "cash, including a \\$50 reserve. These numbers are accounting-test conditions, not an S3 forecast. "
        "The new instrument is not selected in that reference. All sixty records permit an unrestricted "
        "conventional entrepreneur with the same menu; no technology-exclusive package is established.\n"
    )
    at += table(
        ["Payment arrangement", "Delay (days)", "Opening cash", "Success contribution"],
        timing_rows,
        "Separate post-confirmation arithmetic illustration with fixed successful receipts and costs. A common milestone is assumed independently useful and accepted. Values are not buyer commitments or market estimates.",
    )
    write("arrangement_results.tex", at)
    fig, ax = plt.subplots(figsize=(8.7, 3.35))
    for x, color in zip(
        [case for case in timing["cases"] if case["payment_release_delay_days"] == 0], ["#758696", "#153d59", "#087f8c"]
    ):
        events = x["result"]["events"]
        ordered = [(e["day"], e["available_with_declared_opening_cents"] / 100) for e in events]
        ax.step(
            [p[0] for p in ordered],
            [p[1] for p in ordered],
            where="post",
            color=color,
            linewidth=2,
            label=labels.get(x["mode"], x["mode"]),
        )
    ax.axhline(0, color="#ad7e32", linestyle="--", linewidth=1)
    ax.set(
        xlabel="Diagnostic day",
        ylabel="Available cash after liabilities / reserves · USD",
        title="Payment timing changes the financing burden",
    )
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    save(fig, "cash_timing")
    write(
        "arrangement_results.tex",
        at
        + "\n"
        + figure(
            "cash_timing",
            "Arbitrary successful diagnostic paths with USD500 opening cash. Refundable principal remains unavailable. The separately useful accepted milestone requires less opening cash only when released early; all three arrangements need USD840 under the ten-day release delay. Identical successful contribution does not imply identical liquidity.",
        ),
    )

    rows = [
        ["Conditional H4 equilibrium", "Pass", "Pass", "Pass", "Unknown"],
        ["Uncalibrated physical prediction", "Evidence needed", "Evidence needed", "Evidence needed", "Not qualified"],
        ["Assumed-calibration propagation", "Pass, conditional", "Pass, conditional", "Pass, conditional", "Unknown"],
        ["Fresh Boehm scope decision", "Pass", "Pass", "Pass", "Unknown"],
        ["General nonlinear qualification", "Not tested", "Not tested", "Not tested", "Not established"],
    ]
    write(
        "frontier_results.tex",
        table(
            ["Useful offering / boundary", "U", "E", "E+", "Commercial margin"],
            rows,
            "Observed computational frontier under the frozen envelope. Pass means the scoped packet satisfies acceptance. No positive complete-cost commercial crossing is established. The refused physical prediction is different from the accepted explanation of why evidence is missing.",
            "p{0.29\\linewidth}p{0.145\\linewidth}p{0.145\\linewidth}p{0.145\\linewidth}p{0.15\\linewidth}",
        ),
    )

    value = read("economics/value_results/summary.json")
    pair = value["value_minus_original_same_fresh_worlds"]["reference/shared_retention"]
    hold = (
        "\n\\subsection{An explicit HOLD choice, tested prospectively}\n"
        "The original controller did not separately learn whether to buy a merely reachable assessment. "
        "An additive supplement compares HOLD/continue-E against assessment jointly with price and reserves. "
        "It evaluates 108 development choices over 3,456 histories, freezes the choice, then runs 9,216 fresh "
        "histories: 4,608 selected-controller histories and 4,608 unchanged original-controller controls on "
        "the same fresh worlds. The three optional policies all select HOLD. This preserves the old results "
        "and leaves the operative configuration as E; it is not successful sharing.\n\n"
        f"The fresh reference mean E/HOLD profit is \\${value['value_selected']['groups']['reference/expert_E']['mean_profit_usd']:.5f}. "
        f"Relative to the original sharing policy on those same fresh worlds, HOLD improves modeled mean net value by \\${pair['mean_increment_usd']:.8f}, "
        f"with conditional Monte Carlo 95\\% interval [\\${pair['conditional_monte_carlo_95_interval_usd'][0]:.8f}, \\${pair['conditional_monte_carlo_95_interval_usd'][1]:.8f}]. "
        "This is avoided modeled assessment loss, not additional learned Alpha, new shared revenue or recovered historical profit. "
        "All 2,304 HOLD histories equal the corresponding E histories; 768 graph/library pairs match; the 2,304 "
        "unaffected control histories remain unchanged.\n"
    )
    cumulative = cumulative_records()
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    groups = cumulative["groups"]
    old_controller = next(k.rsplit("/", 1)[0] for k in groups if "original" in k)
    new_controller = "value_selected"
    for policy, color, label in [
        ("ordinary_U", COLORS[0], "Ordinary U"),
        ("expert_E", COLORS[1], "Expert E / selected HOLD"),
        ("shared_retention", COLORS[2], "Original shared-option policy"),
    ]:
        axes[0].plot(
            cumulative["days"], groups[old_controller + "/" + policy]["mean_usd"], color=color, linewidth=2, label=label
        )
    e = np.array(groups[old_controller + "/expert_E"]["mean_usd"])
    old = np.array(groups[old_controller + "/shared_retention"]["mean_usd"])
    new = np.array(groups[new_controller + "/shared_retention"]["mean_usd"])
    axes[1].plot(cumulative["days"], old - e, color=COLORS[2], linewidth=2, label="Original shared option − E")
    axes[1].plot(cumulative["days"], new - e, color="#087f8c", linewidth=2, label="Selected HOLD − E")
    axes[1].axhline(0, color="#777", linewidth=0.7)
    for ax in axes:
        ax.set_xlabel("Simulated day · 30 operating + 14 settlement days")
        ax.grid(axis="y", alpha=0.17)
        ax.legend(frameon=False, fontsize=7.5)
    axes[0].set(ylabel="Mean cumulative cash contribution · USD", title="Modeled delivery accumulates contribution")
    axes[1].set(ylabel="Mean cumulative increment · USD", title="Optional sharing does not compound value")
    fig.tight_layout(w_pad=2)
    save(fig, "cumulative_value")
    hold += figure(
        "cumulative_value",
        "Reconstructed from the retained fresh-reference event stream, 128 worlds per policy. All money is simulated; seed capital is excluded. The right panel isolates incremental net value rather than depicting more work as learning. HOLD equals E because it does not buy the uneconomic option under these assumptions.",
    )
    write("value_results.tex", hold)
    inputs = [
        "opportunity/results/confirmation_summary.json",
        "opportunity/conventional/packet.json",
        "opportunity/arrangement/results/timing_examples.json",
        "opportunity/arrangement/results/reference_selection.json",
        "economics/value_results/summary.json",
        "economics/value_results/events.jsonl.gz",
    ]
    write(
        "opportunity_build_receipt.json",
        json.dumps(
            {
                "inputs": {name: sha(STUDY / name) for name in inputs},
                "builder_sha256": sha(Path(__file__)),
                "generated_figures": ["scientific_witness", "cash_timing", "cumulative_value"],
                "actual_collections_usd": 0,
                "actual_complete_cost_usd": None,
            },
            indent=2,
        ),
    )
    print(
        json.dumps(
            {
                "scientific": {a: scientific["arms"][a]["passed_missions"] for a in names},
                "figures": 3,
                "cumulative_groups": len(groups),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
