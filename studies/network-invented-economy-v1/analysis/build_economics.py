"""Deterministic publication postprocessing; never executes a simulated world."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("conservative", "central", "favorable")
INK, GOLD, TEAL, RED = "#342657", "#ad8034", "#267e83", "#ae535d"


def ci(values):
    n = len(values)
    avg = statistics.fmean(values)
    half = 1.96 * statistics.stdev(values) / math.sqrt(n) if n > 1 else 0
    return dict(n=n, mean=avg, lower=avg-half, upper=avg+half)


def dollars(value, decimals=0):
    return f"{value:,.{decimals}f}"


def paired(rows, case, treatment="network", control="beta", field="profit"):
    pool = {(r["arm"], r["seed"]): r for r in rows if r["case"] == case}
    seeds = sorted(s for a, s in pool if a == treatment and (control, s) in pool)
    def get(record):
        return record[field] if field in record else record["stats"].get(field, 0)
    return ci([get(pool[treatment, s])-get(pool[control, s]) for s in seeds])


def save_figure(fig, name, folder):
    fig.savefig(folder / f"{name}.pdf", bbox_inches="tight", metadata={"CreationDate": None})
    fig.savefig(folder / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    results, paper = args.results, ROOT / "paper"
    inputs = ["summary.json", "selected_policies.json", "confirmation_runs.jsonl",
              "sensitivity_runs.jsonl", "sensitivity.json", "capacity_policy.json",
              "ablation_runs.json", "recipient_ablation.json", "output_audit.json"]
    for name in inputs:
        if not (results / name).exists():
            raise SystemExit(f"Required completed evidence missing: {name}")
    summary = json.loads((results / "summary.json").read_text())
    rows = [json.loads(line) for line in (results / "sensitivity_runs.jsonl").read_text().splitlines()]
    confirmation = [json.loads(line) for line in (results / "confirmation_runs.jsonl").read_text().splitlines()]
    capacity = json.loads((results / "capacity_policy.json").read_text())
    panel = json.loads((results / "recipient_ablation.json").read_text())
    ablation = json.loads((results / "ablation_runs.json").read_text())
    assert len(confirmation) == 768 and len(rows) == 2736 and len(ablation) == 240
    assert json.loads((results / "output_audit.json").read_text())["checks"]["passed"]
    folder = paper / "figures"
    folder.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.labelcolor": INK,
                         "text.color": INK, "pdf.fonttype": 42})
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.8, 4.0), gridspec_kw={"width_ratios": [1.1, 1]})
    x = np.arange(3)
    for offset, arm, label, color in [(-.18, "beta", "Competent Beta", INK), (.18, "network", "Network policy", GOLD)]:
        stats = [summary["scenarios"][s][arm]["profit"] for s in SCENARIOS]
        ax.bar(x+offset, [v["mean"]/1e6 for v in stats], width=.34, color=color, label=label)
        ax.errorbar(x+offset, [v["mean"]/1e6 for v in stats],
                    yerr=[(v["upper"]-v["mean"])/1e6 for v in stats], fmt="none", ecolor="#292335", capsize=3)
    ax.set_xticks(x, [s.capitalize() for s in SCENARIOS]); ax.set_ylabel("Collected operating surplus (USD million)")
    ax.set_title("Commercial delivery is profitable in the model", fontsize=11)
    ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=.15); ax.set_axisbelow(True)
    for i, s in enumerate(SCENARIOS):
        v = summary["paired"][s]["network-minus-beta"]["profit"]
        bx.errorbar(v["mean"]/1000, i, xerr=(v["upper"]-v["mean"])/1000,
                    fmt="o", color=TEAL if v["lower"]>0 else RED, capsize=4)
    bx.axvline(0, color=INK, linewidth=.8); bx.set_yticks(x, [s.capitalize() for s in SCENARIOS]); bx.invert_yaxis()
    bx.set_xlabel("Paired network − Beta surplus (USD thousand)")
    bx.set_title("Added enterprise Alpha is not established", fontsize=11); bx.grid(axis="x", alpha=.15)
    fig.subplots_adjust(wspace=.42, bottom=.21)
    fig.text(.5, .015, "768 fresh modeled histories · 64 worlds per scenario/arm · intervals are conditional Monte Carlo error", ha="center", fontsize=9)
    save_figure(fig, "economics", folder)

    chosen = [("central-reference", "Central reference"), ("ordinary-learning-certain", "Ordinary learning certain"),
              ("overlap-0.90", "90% initial overlap"), ("retention-effort-10", "Retention effort ×10"),
              ("transfer-0.40", "Transfer success 40%"), ("transfer-0.98", "Transfer success 98%"),
              ("reuse-savings-0", "Zero retained work saving"), ("lifetime-104", "Useful life 104 weeks"),
              ("beta-static", "Static Beta"), ("beta-fast", "Fast Beta improvement"),
              ("copying-fast", "Rapid external copying"), ("validators-4", "Four validators")]
    fig, ax = plt.subplots(figsize=(9.7, 5.0))
    for i, (case, label) in enumerate(chosen):
        v = paired(rows, case+"-retain")
        ax.errorbar(v["mean"]/1000, i, xerr=(v["upper"]-v["mean"])/1000,
                    fmt="o", color=TEAL if v["lower"]>0 else RED, capsize=3)
    ax.set_yticks(range(len(chosen)), [label for _, label in chosen]); ax.invert_yaxis()
    ax.axvline(0, color=INK, linewidth=.8); ax.grid(axis="x", alpha=.15)
    ax.set_xlabel("Paired network retention − Beta surplus (USD thousand)")
    ax.set_title("Retention remains conditional on the operating environment", loc="left", pad=13)
    fig.subplots_adjust(bottom=.19)
    fig.text(.5, .015, "Predeclared stresses · 16 worlds each · retention enabled, separate R&D disabled · frozen central price", ha="center", fontsize=8.8)
    save_figure(fig, "sensitivity", folder)

    demand = [("leads-0.05", .05), ("leads-0.25", .25), ("leads-0.5", .5), ("leads-1", 1),
              ("leads-2", 2), ("central-reference", 4), ("leads-8", 8), ("leads-16", 16)]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.4, 3.8))
    brackets = {}
    for arm, label, color in [("beta", "Beta", INK), ("network", "Network retention", GOLD)]:
        vals = [ci([r["profit"] for r in rows if r["case"] == c+"-retain" and r["arm"] == arm]) for c, _ in demand]
        ax.plot([v for _, v in demand], [z["mean"]/1e6 for z in vals], "o-", label=label, color=color)
        ax.fill_between([v for _, v in demand], [z["lower"]/1e6 for z in vals], [z["upper"]/1e6 for z in vals], color=color, alpha=.12)
        crossings = [[demand[i-1][1], demand[i][1]] for i in range(1,len(vals)) if vals[i-1]["mean"]<=0<vals[i]["mean"]]
        brackets[arm] = crossings
        bvals = [ci([r["stats"].get("validator_wait_weeks",0) for r in rows if r["case"] == c+"-retain" and r["arm"] == arm]) for c, _ in demand]
        bx.plot([v for _, v in demand], [z["mean"] for z in bvals], "o-", label=label, color=color)
    for a in (ax,bx):
        a.set_xscale("log"); a.set_xlabel("Mean initial qualified leads per week"); a.grid(alpha=.15)
    ax.axhline(0, color=INK, linewidth=.7); ax.set_ylabel("Surplus (USD million)"); ax.set_title("Break-even depends on demand", fontsize=11); ax.legend(frameon=False, fontsize=9)
    bx.set_ylabel("Aggregate validator-wait job-weeks"); bx.set_title("Demand eventually encounters capacity", fontsize=11)
    fig.subplots_adjust(wspace=.4,bottom=.21)
    fig.text(.5,.012,"104-week intake + run-off · assumptions held fixed · no precise demand estimate inferred between grid points",ha="center",fontsize=8.8)
    save_figure(fig,"demand",folder)

    lines = [r"\subsection{Incremental value beyond the profitable commercial core}",
             r"The positive Beta commercial result does not depend on the following enhancements. The same 768 confirmation histories separately test whether the shared graph increases enterprise surplus. No primary scenario establishes that additional benefit. Declining retention or continuing with existing frontier capabilities preserves the profitable operating option; it is not a failed enterprise. All values remain conditional model results, not realized margins or empirical demand estimates.",
             r"\begin{table}[H]\centering\small\caption{Same-policy enterprise comparison, USD. The interval is for the paired network-minus-Beta increment.}\label{tab:primary}",
             r"\begin{tabular}{lrrrr}\toprule Scenario & Beta & Network & Increment & 95\% MC interval\\\midrule"]
    for s in SCENARIOS:
        b=summary["scenarios"][s]["beta"]["profit"]["mean"]; n=summary["scenarios"][s]["network"]["profit"]["mean"]
        p=summary["paired"][s]["network-minus-beta"]["profit"]
        lines.append(f"{s.capitalize()} & {dollars(b)} & {dollars(n)} & {dollars(p['mean'])} & [{dollars(p['lower'])}, {dollars(p['upper'])}] \\")
    lines += [r"\bottomrule\end{tabular}\end{table}",
              r"The conservative policy uses the adaptive price rule with zero offset and chooses delivery only; its mean offer is 29.8\% of the scope-matched human reference. Central selection chooses a fixed 55\% price and delivery only. Favorable selection chooses a fixed 75\% price, retention hurdle 1.5, and no separate R\&D. These discounts emerge from the finite search. They were not imposed. Fixed-price selection does not establish that a fixed price is universally best.",
              r"No primary history makes a separate C investment. Network and network-without-C results are therefore identical. Conservative and central policies do not retain graph capabilities; operating the available network still incurs overhead and can shift cash timing. Their small outcome differences cannot be called Alpha. A manager could avoid that unused service by operating the Beta-only configuration; the experiment deliberately reports its cost.",
              r"\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/economics.pdf}\caption{Primary modeled commercial results and their internal increment. Large absolute surplus does not establish a shared-capability advantage.}\end{figure}",
              r"In the favorable condition, the network averages 7.84 retention campaigns, 7.38 admissions and 44.84 useful recipient jobs per world. Those are adoption and activity counts, not added outcomes. Its accepted-useful outcome difference from Beta is $-0.875$ jobs (95\% conditional MC interval $[-4.034,2.284]$). The surplus difference is unresolved and has a negative point estimate. The network-minus-isolated comparison is also unresolved: USD$-51,118$ with interval $[-180,073,77,838]$. Selection on training data does not guarantee a confirmation gain.",
              r"\subsection{Complete costs, cash and the source of retained learning}",
              r"\begin{table}[H]\centering\small\caption{Mean network cost books and collections, USD. Common costs are charged once; B includes graph overhead even without retained skills.}",
              r"\begin{tabular}{lrrrrr}\toprule Scenario & Collections & A jobs & B retention & C new R\&D & Common\\\midrule"]
    for s in SCENARIOS:
        a=summary["scenarios"][s]["network"]
        lines.append(f"{s.capitalize()} & {dollars(a['collections']['mean'])} & {dollars(a['cost_books']['job']['mean'])} & {dollars(a['cost_books']['retention']['mean'])} & {dollars(a['cost_books']['investment']['mean'])} & {dollars(a['cost_books']['common']['mean'])} \\")
    lines += [r"\bottomrule\end{tabular}\end{table}",
              r"Closing obligations average USD471 in central network runs and zero in the other two; they are deducted in surplus. Seed capital is additional cash, not revenue. All 64 network worlds in each scenario have positive surplus and no recorded cash shortfall. Zero shortfalls in 64 worlds still has a 95\% Wilson upper bound of 5.66\%; it is not proof of a sub-5\% real-world risk.",
              r"The independent retained-ledger audit reconciles every one of the 768 confirmation worlds, including expense-book partition, commitments, warranties, collection delays, source-job memos and finite cash. It found no invariant failure. These repeated accounting checks verify the implementation, not the truth of the workload or demand assumptions.",
              r"Across favorable network worlds, 502 B campaigns occur. Of these, 396 are labeled funded from available operating surplus and 106 from seed or mixed funds. Source-job collection often comes after retention: 381 recorded source links collect later, 132 before or at retention, and 9 remain uncollected at closing. A customer order therefore does not imply that its receipt financed the next extraction.",
              r"An illustrative trace uses the prespecified first favorable network world, seed 770001. Source job 9 incurs USD974.32 of direct A cost, including a USD536.53 learning memo that is already inside that cost. Retention reserves USD183.94 at week 5 and spends it at week 6: USD58.94 extraction and USD125 creator bounty. A separate USD51.30 portfolio appraisal occurs in week 5; ongoing maintenance and network service also remain in B. The reserved campaign subtotal is not its full lifecycle cost. Its USD18,996.75 customer collection arrives at week 7. The first useful receiving job in this lineage completes at week 13. This early retention is seed/mixed-funded. No source A amount is charged again. The sequence illustrates the modeled lifecycle; it does not prove that this receiver could not have succeeded with competent reconstruction, and this entire network world earns USD1,062,359 less than its paired Beta world.",
              r"Validation remains imperfect. Conservative, central and favorable network worlds average 5.23, 7.00 and 5.70 false passes respectively. Remediation costs are charged, but these errors and the finite liability assumptions prevent treating modeled profitability as operational service qualification.",
              r"\subsection{A conditional recipient-level Alpha result}",
              r"The separate deterministic recipient panel holds the task and resources fixed. Its five competent recipient profiles yield expected initial delivery savings of USD750.08, USD148.43, zero, USD505.78 and zero. The specialist and already-equivalent recipient decline acquisition; missing a skill file does not imply missing capability. Every declared delivery route remains feasible in this panel, so it demonstrates no newly feasible job.",
              r"At the declared 80 uses, the paid-job-retention panel projects USD34,740.79 less complete delivery cost and USD9,495.70 additional lifecycle cost, leaving USD25,245.09 modeled net Alpha. Remaining upfront B is USD849.84; upkeep, revalidation and reassessment dominate the rest. Historical A is unspecified in this panel, retained as a memo, and never charged again. Its uncertainty allowance is zero; this arithmetic is not a measured or statistically confirmed return.",
              r"The illustrative optional new-R\&D campaign instead projects USD$-5,295.69$. It assumes one failed construction attempt (USD11,617.10 within USD23,234.20 total C construction) and campaign success 0.648, versus 0.90 for retention. This is not a cost-only matched contrast or evidence that new R\&D generally fails. The strict reuse thresholds at the declared lifetime are 22 uses for retention and 97 for new R\&D. These thresholds keep the declared age/task mixture; they are not interchangeable with the enterprise's component-level screening. A first positive projected lifetime of two weeks in the retention panel is a prospective utility threshold, not an observed two-week cash repayment.",
              r"\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/recipients.pdf}\caption{Separate deterministic modeled recipient probes. Existing equivalents and optional nonuse are preserved. These values do not repair the unresolved enterprise comparison.}\end{figure}",
              r"The actual graph adapter admits the positive modeled bundle and rejects optional new R\&D into separate failure memory, using distinct fixture producer, validators and admitter. Six authenticated direct-label fixture members retrieve it; lacking an action permission blocks an execution permit while preserving access. A declared Beta change invalidates its old authority. This establishes a source-bound software lifecycle over modeled evidence, not operational Alpha.",
              r"\subsection{Sensitivity, demand and capacity}",
              r"All 2,736 predeclared sensitivity histories and 240 ablation histories completed. Sensitivities explicitly enable optional B retention under the frozen central pricing rule; they are not the central delivery-only policy relabeled as a success. Separate-C-enabled responses are retained alongside no-C responses. Their finite grids describe conditional mechanisms and parameter sensitivity, not market confidence or a universal optimum. Intervals are pointwise normal Monte Carlo intervals without multiplicity correction.",
              r"\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/sensitivity.pdf}\caption{Selected predeclared stresses. Bars are paired conditional Monte Carlo intervals across 16 independent modeled worlds; all 57 cases remain in the companion.}\end{figure}"]
    stress_table = []
    for case in ["central-reference", "human-price-10pct", "retention-effort-10", "overlap-0.90",
                 "beta-fast", "lifetime-104", "joint-commercial-downside"]:
        v=paired(rows,case+"-retain")
        ns=ci([r["profit"] for r in rows if r["case"]==case+"-retain" and r["arm"]=="network"])
        stress_table.append({"case":case,"network_profit":ns,"paired_profit":v})
        # TeX percent signs in labels are intentionally escaped above.
    lines += [r"\begin{table}[H]\centering\small\caption{Selected conditional stresses, USD mean surplus and paired increment.}",
              r"\begin{tabular}{lrrr}\toprule Stress & Network & Network $-$ Beta & 95\% MC interval\\\midrule"]
    labels=["Central, B enabled",r"Human reference at 10\%",r"B effort $10\times$",r"90\% overlap", "Faster Beta", "104-week useful life", "Joint commercial downside"]
    for label,z in zip(labels,stress_table):
        v=z["paired_profit"]
        lines.append(f"{label} & {dollars(z['network_profit']['mean'])} & {dollars(v['mean'])} & [{dollars(v['lower'])}, {dollars(v['upper'])}] \\")
    lines += [r"\bottomrule\end{tabular}\end{table}",
              r"\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/demand.pdf}\caption{Demand and queueing under unchanged prices and other scenario assumptions. Aggregate waiting sums time across jobs; it can exceed the calendar horizon.}\end{figure}"]
    for arm in ("beta","network"):
        cross=brackets[arm]
        if cross:
            lines.append(f"For {arm.replace('_',' ')} under the demand sweep, the modeled mean-profit sign changes between {cross[0][0]:g} and {cross[0][1]:g} initial qualified leads per week. No precise break-even arrival rate is identified between these grid points.")
        else:
            lines.append(f"The declared demand grid does not bracket a mean-profit sign change for {arm}.")
    for arm,c in capacity["choices"].items():
        v=c["paired_profit_gain"]
        label=c["selected"].replace("-"," ")
        lines.append(f"The split-sample initial-capacity menu selects {label} for {arm}. Its eight fresh test worlds give mean gain USD{dollars(v['mean'])} relative to the central capacity, with conditional interval [{dollars(v['lower'])}, {dollars(v['upper'])}]. This tests the chosen starting configuration, not globally optimal expansion timing.")
    lines += [r"\subsection{Counterfactuals and the moving frontier}",
              r"The component-removal and duplicate controls use the same initial resources and seeds. Central and conservative policies retain no graph capabilities, so component-removal effects there cannot establish a skill mechanism. The deliberately forgetful no-retention diagnostic is not the fair Beta comparator; ordinary competent learning remains in all primary comparisons.",
              r"\begin{table}[H]\centering\small\caption{Favorable component controls: network minus altered network, first 16 confirmation seeds.}",
              r"\begin{tabular}{lrr}\toprule Control & Mean surplus difference (USD) & 95\% MC interval\\\midrule"]
    abvals=[]
    base={r["seed"]:r for r in confirmation if r["scenario"]=="favorable" and r["arm"]=="network"}
    for arm in ("remove_representation","remove_falsifier","remove_composition","duplicate","no_retention"):
        rr=[r for r in ablation if r["scenario"]=="favorable" and r["arm"]==arm]
        v=ci([base[r["seed"]]["profit"]-r["profit"] for r in rr]);abvals.append({"control":arm,**v})
        lines.append(f"{arm.replace('_',' ')} & {dollars(v['mean'])} & [{dollars(v['lower'])}, {dollars(v['upper'])}] \\")
    lines += [r"\bottomrule\end{tabular}\end{table}",
              r"\begin{figure}[H]\centering\includegraphics[width=.95\linewidth]{figures/recipient_thresholds.pdf}\caption{The separate recipient panel exposes how overlap, checking and improved Beta raise the strict reuse threshold. No finite threshold remains a distinct negative result.}\end{figure}",
              r"Large representation and falsifier removal losses are total intervention effects. The removal masks runtime eligibility while prospective appraisal can still value the removed component, allowing futile retention attempts and changed routing or queues. These controls diagnose dependence and policy brittleness; they are not clean estimates of a component's isolated net Alpha and do not overturn the fair Beta comparison. The duplicate control explicitly marks the proposed asset redundant, testing rejection mechanics rather than independently discovering the frequency of redundancy.",
              r"Among the 57 retention-versus-Beta stresses, the only positive paired interval occurs at USD10,000 seed. Both arms suffer cash shortfall in all 16 worlds and retain no capability; the USD334 difference is a smaller failure loss, not Alpha. Fast Beta and rapid copying instead produce negative retention increments. Some optional-C enablement contrasts are positive despite zero C campaigns in those conditions: evaluator overhead and timing can change outcomes without producing a new asset. The complete corpus records three C campaign events in reduced-construction-cost conditions, not three independent invention replications: one seed appears in two alternative conditions. It establishes no separate-R\&D capability feedback loop.",
              r"The commercial core is a positive modeled finding within its stated assumptions. The optional capability result is narrower: paid-job accounting can make remaining retention much less expensive than a new invention campaign, and the executable system can test and enforce a conditional Alpha claim. Full overhead, capacity, adaptation and demand still determine whether that enhancement pays. This edition does not establish a durable moat, a new commercially validated offering unlocked by sharing, an extra-R\&D feedback loop or self-acceleration. None is required for profitable Beta delivery."]
    # A normal Python string ending in backslashes above emits one; ensure every table row has TeX's two.
    lines = [line + "\\" if line.endswith(" \\") and not line.endswith(" \\\\") else line for line in lines]
    (paper / "results_text.tex").write_text("\n\n".join(lines)+"\n")
    (paper / "results_macros.tex").write_text("% Generated from retained evidence; no scientific input changes.\n")
    report={"kind":"publication-postprocessing", "scenarios":summary["paired"], "demand_sign_brackets":brackets,
            "selected_stresses":stress_table,"favorable_ablations":abvals,
            "input_hashes":{name:hashlib.sha256((results/name).read_bytes()).hexdigest() for name in inputs},
            "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (results / "publication_analysis.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"demand_sign_brackets":brackets,"selected_stresses":stress_table,"favorable_ablations":abvals},indent=2))


if __name__ == "__main__":
    main()
