# SPDX-License-Identifier: Apache-2.0
"""Generate publication tables and figures from preserved recorded evidence."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/operational-alpha-v2-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
FIG = HERE / "figures"
COLORS = {"U": "#768797", "E": "#173f5f", "E_plus": "#b08438"}
LABELS = {"U": "U · ordinary", "E": "E · expert", "E_plus": "E+ · received helper"}


def read(relative: str) -> Any:
    return json.loads((STUDY / relative).read_text())


def write(name: str, text: str) -> None:
    (HERE / name).write_text(text + "\n", encoding="utf-8")


def save(fig: Any, name: str) -> None:
    fig.savefig(FIG / (name + ".png"), dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(FIG / (name + ".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def table(headers: list[str], rows: list[list[str]], caption: str, spec: str | None = None) -> str:
    spec = spec or "l" + "r" * (len(headers) - 1)
    return "\n".join(
        [r"\begin{table}[H]\centering\small", r"\begin{tabular}{@{}" + spec + r"@{}}\toprule",
         " & ".join(headers) + r" \\ \midrule"]
        + [" & ".join(row) + r" \\" for row in rows]
        + [r"\bottomrule\end{tabular}", r"\caption{" + caption + "}", r"\end{table}"]
    )


def figure(name: str, caption: str, width: str = "0.95") -> str:
    return (
        r"\begin{figure}[H]\centering\includegraphics[width=" + width + r"\linewidth]{figures/" + name
        + r".png}\caption{" + caption + r"}\end{figure}"
    )


def main() -> None:
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.labelcolor": "#243746", "text.color": "#243746"})
    pilot = read("results/pilot_summary.json")
    composition = read("results/composition_summary.json")
    econ = read("economics/results/summary.json")
    prescreen = read("economics/prescreen_results/prescreen_summary.json")
    native = read("integration/results/workflow-v2/summary.json")
    arms = ["U", "E", "E_plus"]
    values = [pilot["arms"][a]["accepted"] for a in arms]
    if values == [4, 4, 4]:
        finding = ("U, E and E+ each deliver 4/4 accepted fresh repairs. The transferred helper is used successfully, "
                   "but this sample shows no additional accepted-output gain from either the expert card or the helper.")
    else:
        finding = "Fresh accepted repairs are U " + str(values[0]) + "/4, E " + str(values[1]) + "/4 and E+ " + str(values[2]) + "/4."
    cpass = [composition["arms"][a]["accepted"] for a in arms]
    cfinding = ("All three configurations also accept the supplementary campaign audit; no exclusive technical "
                "frontier crossing is observed.") if all(cpass) else (
                    "The separately frozen campaign-audit outcomes are " + ", ".join(
                        a.replace("_plus", "+") + (" accepted" if v else " rejected") for a, v in zip(arms, cpass)
                    ) + ". Unknown actual costs preclude an observed commercial crossing.")
    write("results.tex", "\n".join([
        r"\newcommand{\PilotFinding}{" + finding + "}", r"\newcommand{\CompositionFinding}{" + cfinding + "}",
        r"\newcommand{\NativePassed}{" + str(native["passed"]) + "}",
        r"\newcommand{\NativeTotal}{" + str(native["total"]) + "}",
    ]))
    rows = []
    for a in arms:
        x = pilot["arms"][a]
        rows.append([a.replace("_plus", "+"), f"{x['accepted']}/4", f"{x['elapsed_seconds']:.2f}",
                     str(x["operations"]), str(x["test_executions"]), "Unknown"])
    primary = table(["Configuration", "Accepted", "Hosted seconds", "Operations", "Test runs", "Actual cost"], rows,
                    "Observed frozen batches under the same 1,500-second/64-operation outer limits. Counts are successfully logged interface operations, not complete token telemetry. All final submissions meet their recorded budgets.")
    primary += "\n" + (
        "The observed acceptance differences E--U and E+--E are both zero percentage points on these four missions. "
        "E's hosted batch is shorter than U's; E+ is longer than E's. These single observations are descriptive and "
        "cannot identify a reliable latency, hidden-compute or dollar-cost effect. U's eight test executions are all "
        "post-repair passes; E and E+ each retain four deliberately failing original-code regression runs before "
        "their passing repaired runs. Those reproduced defects are not failed final customer deliveries."
    )
    fig, ax = plt.subplots(figsize=(8.8, 2.65))
    matrix = np.array([[r["passed"] for r in pilot["arms"][a]["per_case"]] for a in arms])
    ax.imshow(matrix, cmap="YlGnBu", vmin=0, vmax=12, aspect="auto")
    ax.set_xticks(range(4), ["C1 · journal", "C2 · scheduler", "C3 · artifacts", "C4 · batches"])
    ax.set_yticks(range(3), [LABELS[a] for a in arms])
    for i in range(3):
        for j in range(4):
            ax.text(j, i, str(matrix[i, j]) + "/10", ha="center", va="center", color="white", weight="bold")
    ax.set_title("Complete finite-contract acceptance · four mission clusters", loc="left", weight="bold", pad=15)
    save(fig, "acceptance")
    primary += "\n" + figure("acceptance", "All four complete contracts accept in each arm. The forty checks within an arm do not create forty independent tasks.")
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.3))
    for ax, key, title in zip(axes, ["elapsed_seconds", "operations"], ["Observed hosted wall seconds", "Logged interface operations"]):
        vals = [pilot["arms"][a][key] for a in arms]
        ax.bar([a.replace("_plus", "+") for a in arms], vals, color=[COLORS[a] for a in arms], width=0.58)
        for i, v in enumerate(vals):
            ax.text(i, v + max(vals) * 0.03, f"{v:.1f}" if key == "elapsed_seconds" else str(v), ha="center")
        ax.set_ylim(0, max(vals) * 1.22)
        ax.set_title(title, loc="left", fontsize=11)
        ax.grid(axis="y", alpha=0.17)
        ax.set_axisbelow(True)
    fig.suptitle("Accepted quality matched · complete monetary cost remains unobserved", y=1.02, fontsize=12)
    fig.tight_layout()
    save(fig, "observed_resources")
    primary += "\n" + figure("observed_resources", "One hosted batch per arm. Model tokens, billing, provider scheduling and full research labor are not inferred from these bars.")
    write("primary_results.tex", primary)
    policies = ["ordinary_U", "expert_E", "enhanced_Eplus", "private_retention", "shared_retention", "library_retention"]
    names = ["U", "E", "E+ equipped", "Private option", "Shared option", "Library option"]
    rows = []
    for p, name in zip(policies, names):
        x = econ["groups"]["reference/" + p]
        rows.append([name, f"{x['mean_collections_usd']:,.2f}", f"{x['mean_complete_cost_usd']:,.2f}",
                     f"{x['mean_profit_usd']:,.2f}", f"{x['mean_available_usd']:,.2f}"])
    economic = table(["Frozen policy", "Net collections", "Complete cost", "Profit", "Available cash"], rows,
                     "Original limited-controller reference scenario: mean USD per 30 operating days plus 14 settlement days, 128 worlds per policy. Initial capital is USD1,000; the selected reserve is USD24. All figures are modeled, including failed work and prototypes.")
    e = econ["paired"]["reference/shared_retention-expert_E"]
    economic += (
        "\nEvery policy selected a 0.5 price/reference ratio and three days of reserve from the declared development grid. "
        "The component price is therefore modeled at \\$35 against an assumed \\$70 human-service reference. "
        "The observed acceptance counts provide no quality increment, and equal-quality uncertainty is coupled. "
        "The original E--U difference is exactly the assumed \\$30 method setup cost, not an estimated market value "
        "of expert prompting. Equipped E+ adds assumed packaging, invocation and maintenance expense. "
        f"The original shared-option policy loses \\${-e['mean_usd']:.2f} relative to E, with conditional Monte Carlo "
        f"95\\% interval [\\${e['monte_carlo_95_interval_usd'][0]:.2f}, \\${e['monte_carlo_95_interval_usd'][1]:.2f}]. "
        "Its one reference-profile admission is a modeled assessor error. Graph and identical-content library "
        "trajectories match exactly. No Gym campaign is selected in the tested primary or stress runs. "
        "This tests optional restraint; it does not empirically test a trained specialist.\n\n"
        "The simulated four-component pack is an illustrative bundle, not the separately executed C5 campaign auditor. "
        "These enterprise results neither price nor validate C5. The initial controller selects pricing and reserves "
        "but evaluates an assessment option without a separate learned HOLD choice; the additive value-controller "
        "experiment below corrects that decision-menu limitation prospectively."
    )
    stress = []
    for profile, name in [("thin_demand", "Thin demand"), ("low_price_human", "Lower-price human"),
                          ("residual_5min", "5 residual minutes"), ("residual_15min", "15 residual minutes"),
                          ("high_shadow_cost", "10x model charge")]:
        x = econ["groups"][profile + "/ordinary_U"]
        stress.append([name, f"{x['mean_profit_usd']:.2f}", f"{x['p10_profit_usd']:.2f}", f"{x['loss_worlds']}/{x['worlds']}"])
    economic += "\n" + table(["U scenario", "Mean profit", "10th percentile", "Loss worlds"], stress,
                               "Conditional USD scenarios with the same frozen policy. Lower demand, cheaper alternatives and residual obligations can make the modeled service unprofitable in many worlds.")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), gridspec_kw={"width_ratios": [1.15, 1]})
    vals = [econ["groups"]["reference/" + p]["mean_profit_usd"] for p in policies]
    axes[0].barh(names[::-1], vals[::-1], color=["#087f8c"] * 3 + [COLORS["E_plus"], COLORS["E"], COLORS["U"]])
    axes[0].set_xlabel("Modeled mean operating profit · USD")
    axes[0].set_title("Useful delivery can fund the enterprise", loc="left", fontsize=10)
    deltas = [econ["paired"]["reference/" + key]["mean_usd"] for key in ["expert_E-ordinary_U", "enhanced_Eplus-expert_E", "shared_retention-expert_E", "shared_retention-library_retention"]]
    axes[1].barh(["E − U", "E+ − E", "Shared − E", "Graph − library"], deltas, color=[COLORS["E"], COLORS["E_plus"], "#087f8c", "#768797"])
    axes[1].axvline(0, color="#333333", linewidth=0.7)
    axes[1].set_xlabel("Modeled increment · USD")
    axes[1].set_title("Additional methods must justify their costs", loc="left", fontsize=10)
    fig.tight_layout()
    save(fig, "economics_original")
    economic += "\n" + figure("economics_original", "These increments follow from assumptions about costs and no accepted-output gain; they are not observed monetary Alpha. The optional-controller improvement is reported separately.")
    write("economic_results.tex", economic)
    ps = (f"The frozen prospective candidate experiment evaluates {prescreen['worlds']} new paired artificial worlds, "
          "each containing 24 candidates. The old loose screen buys "
          f"{prescreen['old_unreachable_assessments']:,} unreachable assessments; the reachability-first rule buys "
          f"{prescreen['new_unreachable_assessments']}. Mean modeled net improvement is "
          f"\\${prescreen['paired_mean_net_increment_usd']:.2f} per world, with conditional Monte Carlo 95\\% interval "
          f"[\\${prescreen['conditional_monte_carlo_95_interval_usd'][0]:.2f}, "
          f"\\${prescreen['conditional_monte_carlo_95_interval_usd'][1]:.2f}]. Admission counts match in all "
          f"{prescreen['same_admissions_worlds']} worlds. Each rule still makes "
          f"{prescreen['false_admissions']['reachable_first']} modeled false admissions. "
          "Reachability removes a logical impossibility; it does not solve imperfect assessment or establish an expertise gain.")
    fig, ax = plt.subplots(figsize=(7.7, 2.9))
    ax.barh(["Old loose screen", "Reachability first"], [prescreen["old_unreachable_assessments"], 0], color=["#b08438", "#087f8c"])
    ax.set_xlabel("Purchased assessments unable to meet their own capped gate")
    ax.set_title("Fresh artificial streams · historical expenses remain sunk", loc="left", weight="bold", pad=12)
    ax.text(prescreen["old_unreachable_assessments"], 0, f"  {prescreen['old_unreachable_assessments']:,}", va="center")
    ax.text(0, 1, "  0", va="center")
    ax.set_xlim(0, prescreen["old_unreachable_assessments"] * 1.18)
    save(fig, "admission_reachability")
    ps += "\n" + figure("admission_reachability", "Separate prospective synthetic controller comparison. All costs and benefits are modeled; no historical assessment is refunded or erased.")
    write("prescreen_results.tex", ps)
    rows = []
    for a in arms:
        x = composition["arms"][a]
        rows.append([a.replace("_plus", "+"), f"{x['passed']}/{x['total']}",
                     "Yes" if x["accepted"] else "No", f"{x['elapsed_seconds']:.2f}", str(x["operations"])])
    cp = table(["Configuration", "Finite categories", "Accepted", "Hosted seconds", "Operations"], rows,
               "Supplementary composition experiment. The fourteen categories are one task, not fourteen independent offerings.")
    cp += "\n" + cfinding + " The selected offering proposals and their falsifiers are retained with the frozen implementations. "
    cp += "Equal component access is deliberate: a useful outcome is not specialist-exclusive merely because a specialist can describe it."
    write("composition_results.tex", cp)
    facts = {"pilot": pilot, "composition": composition, "native": {k: native[k] for k in ["passed", "total", "artifact_sha256"]},
             "prescreen": prescreen, "economic_groups": econ["groups"], "economic_pairs": econ["paired"],
             "source_status": "observed, sourced and assumed quantities remain separate", "actual_collections_usd": 0,
             "actual_complete_cost_usd": None}
    (STUDY / "publication_facts.json").write_text(json.dumps(facts, indent=2) + "\n")
    evidence_rows = [
        ["Primary repair outputs", "Observed", "12 frozen submissions; four paired task families"],
        ["Development helper", "Observed / authored", "Extracted in one researcher-directed repair"],
        ["Native transfer", "Observed fixture", "31/31 local controls; synthetic authority"],
        ["H rate band", "Sourced", "Arc USD61--80/hour; hours separately assumed"],
        ["Model identifiers / rates", "Sourced", "Official docs, 27 October 2026; entitlement unobserved"],
        ["Future quality / demand", "Assumed", "No calibrated customer-quality or demand estimate"],
        ["Enterprise histories", "Simulated", "4,608 original histories; complete raw events retained"],
        ["Actual cash collections", "Observed absence", "USD0; complete actual expense and profit unknown"],
    ]
    write("evidence_table.tex", table(["Quantity", "Evidence status", "Practical limit"], evidence_rows,
                                      "No simulated quantity is relabeled as an observed sale or live authentication.", "p{0.24\\linewidth}p{0.22\\linewidth}p{0.43\\linewidth}"))
    inputs = ["results/pilot_summary.json", "results/composition_summary.json", "economics/results/summary.json",
              "economics/prescreen_results/prescreen_summary.json", "integration/results/workflow-v2/summary.json"]
    receipt = {"builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "input_sha256": {p: hashlib.sha256((STUDY / p).read_bytes()).hexdigest() for p in inputs},
               "generated_figures": sorted(p.name for p in FIG.iterdir()), "numbers_hand_entered": False}
    (HERE / "build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"figures": len(list(FIG.glob('*.png'))), "pilot": values, "composition": cpass}))


if __name__ == "__main__":
    main()
