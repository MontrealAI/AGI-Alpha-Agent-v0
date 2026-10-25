# SPDX-License-Identifier: Apache-2.0
"""Typeset exact saved results; does not rerun or tune the financial model."""
from __future__ import annotations
import json, hashlib
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
GEN = PAPER / "generated"
FIG = PAPER / "figures"
FAMILIES = ["release_assurance", "rollout_planning", "bilingual_dossier"]
LABELS = ["Source assurance", "Rollout planning", "Bilingual dossier"]
COLORS = ["#693bb1", "#177b69", "#b27a32"]


def read(f):
    return json.loads((ROOT / f).read_text())


def put(n, t):
    (GEN / n).write_text(t + "\n")


def money(x):
    return f"{x:,.2f}"


def tex(x):
    return str(x).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def table(headers, rows, caption, fmt=None):
    fmt = fmt or "l" + "r" * (len(headers) - 1)
    s = r"\begin{table}[H]\small\centering\begin{tabular}{" + fmt + r"}\toprule" + "\n"
    s += " & ".join(headers) + r" \\\midrule" + "\n"
    s += "\n".join(" & ".join(map(str, row)) + r" \\" for row in rows)
    return s + "\n" + r"\bottomrule\end{tabular}\caption{" + caption + r"}\end{table}" + "\n"


def savefig(name, fig):
    fig.tight_layout()
    for ext in ["pdf", "svg", "png"]:
        fig.savefig(FIG / f"{name}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main():
    S = read("economics/outputs/summary.json")
    C = read("protocol/economics_config.json")
    B = S["base"]
    scenarios = {(r["scenario"], r["policy_fraction"]): r for r in S["scenario_results"]}
    L = read("economics/outputs/ledger.json")["rows"]
    F = read("economics/outputs/family_results.json")["rows"]
    base = [r for r in L if r["scenario"] == "base" and r["policy_fraction"] == 0]
    br = {
        f: next(r for r in F if r["scenario"] == "base" and r["policy_fraction"] == 0 and r["family"] == f)
        for f in FAMILIES
    }
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "axes.labelcolor": "#42344f",
        }
    )
    put(
        "abstract_results.tex",
        r"""The original campaign accepted 72/72 joint outputs across six controlled projects, with 24 parent invocations and 12 child invocations. It demonstrates source-bound reuse, but the flywheel consumed 0.9\% more CPU than ordinary caching on fresh changes and expanded no verified same-budget frontier. A separately frozen correction passed 28 finite edge cases after adversarial review found real input-boundary defects. Under explicit U.S. compensation, price and attention assumptions, modeled complete costs are USD28.26--35.16 per accepted service. Customer purchase break-even times are approximately 60, 79 and 57 traditional minutes for the three classes; actual matched durations remain unknown. The six-cycle direct-sale scenario retains USD8,776 of earned cash after its obligation reserve. That amount covers 2.46 times the specified next plan's cash need, but the plan fails the unchanged operating-spend ceiling. A separately labeled smaller-plan diagnostic is feasible. The measured repair capability remains an investment HOLD because the conventional incumbent is cheaper. Self-financing and self-acceleration are not demonstrated.""",
    )
    _correction_audit = read("review/INDEPENDENT_CORRECTION_AUDIT.json")
    put(
        "corrective_results.tex",
        r"""The corrective v1.1 adapter uses path- and provenance-aware content keys, rejects cross-project predecessors, checks immutable construction origin and preserves an accepted child registry for subsequent use. After developmental review, its own freeze bound 36 files at 14:19:54 UTC. A fresh qualification then produced \textbf{25 accepted outputs and three expected refusals}: \textbf{28/28 cases passed}, with 3,265 strengthened Python assertions. A separately authored saved-output audit passed 3,885 assertions. These finite edge cases qualify the correction only within their scope; they do not replace the original 72-run timing campaign or establish general correctness. The browser demo uses v1.1. The economic measurement bridge retains the original scoped timing results without claiming corrected timing superiority.""",
    )
    t = table(
        ["Service", "Full cost", "Price", "Production BE", "Purchase BE"],
        [
            [
                LABELS[i],
                money(B["full_cost_per_accepted_by_family"][f]),
                money(C["families"][f]["price_usd"]),
                f"{60*B['full_cost_per_accepted_by_family'][f]/br[f]['traditional_hourly_rate_usd']:.1f} min",
                f"{br[f]['customer_human_break_even_minutes']:.1f} min",
            ]
            for i, f in enumerate(FAMILIES)
        ],
        "USD and minutes. All Agent costs and prices are modeled, not invoices or observed live costs. Production break-even uses cost; purchase break-even includes price plus assumed customer review. Competent ordinary-tool human duration and matched customer quality remain unmeasured.",
    )
    t += r"""At an assumed 30-minute traditional duration, none of the three customer offers is cheaper. At 60 minutes, source assurance and the dossier are slightly cheaper, while planning remains more expensive. At 120 minutes, all three offers provide modeled customer savings. These are decision thresholds, not measured task-time claims. A small simple case may be faster for a competent worker than its headline occupational wage suggests.

The experiment executes three outputs jointly. The financial model assumes a market in which these classes can be ordered and priced separately, assigning one third of joint native CPU to each class and adding class-specific human attention. This is a commercial packaging assumption, not observed separability or a measured market mix. Native CPU is tiny in the total; attention and setup dominate. The model therefore cannot support a USD0.50 complete-service claim.

\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/commercial.pdf}
\caption{Conditional customer comparison, using sourced compensation and explicitly assumed ordinary-tool duration. The horizontal lines include price and customer review. Intersections are purchase break-even times; no human completion time was observed.}\end{figure}"""
    put("commercial_results.tex", t)
    fig, axs = plt.subplots(1, 3, figsize=(10.7, 3.1), sharey=True)
    for i, (f, ax) in enumerate(zip(FAMILIES, axs)):
        rate = br[f]["traditional_hourly_rate_usd"]
        cost = br[f]["customer_all_in_usd"]
        minutes = np.linspace(5, 150, 120)
        ax.plot(minutes, rate * minutes / 60, color=COLORS[i], lw=2, label="Traditional cost")
        ax.axhline(cost, color="#655b70", ls="--", lw=1.7, label="Offer + review")
        ax.scatter([br[f]["customer_human_break_even_minutes"]], [cost], color=COLORS[i], s=35, zorder=3)
        ax.set_title(LABELS[i], loc="left", fontweight="bold", fontsize=10)
        ax.set_xlabel("Assumed traditional minutes")
        ax.grid(alpha=0.16)
        ax.set_xlim(5, 150)
    axs[0].set_ylabel("Customer cost (USD)")
    axs[1].legend(loc="upper center", bbox_to_anchor=(0.5, 1.38), ncol=2, frameon=False, fontsize=9)
    savefig("commercial", fig)
    t = r"""\begin{table}[H]\small\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{.24\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{.18\linewidth}}\toprule Input & Primary scenario & Classification \\\midrule
Horizon and demand & Six 30-day cycles; 20/40/60/80/80/80 requested orders per class. No empirical demand fit. & Assumed \\
Resource ceilings & USD2,000 service operating spend per cycle; 3,000 human minutes; 160 elapsed hours; 240 attempts. Initial external capital USD2,000. Capital investment separately uses earned surplus. & Assumed \\
Prices & Assurance USD90; planning USD75; dossier USD55. No actual invoices or collections. & Assumed \\
Attention per attempt & Supervision + verification: 6+6, 10+7 and 8+7 minutes by class; order setup 2/3/3; accepted support 2/3/3; retry correction 3/5/4. & Estimated \\
Model/tool allowance & USD1.50/1.10/0.80 per attempt; actual inference charges unavailable. & Estimated \\
Operating envelope & USD120 fixed cost + 60 administration minutes/cycle; storage USD0.10/attempt; delivery USD0.25/acceptance; acquisition USD2.50/order; processing 2\% + USD0.25/acceptance. & Estimated / assumed \\
Failures and collections & 8\% independent attempt failure, at most two attempts/order; 50/35/15\% collection over three cycles; 2\% default and 2\% refund. Deterministic seeded draws, not measured rates. & Assumed \\
Initialization and losses & Two integration-engineer hours, one failed-build engineer hour, one verification hour, USD5 model/tool allowance. First development interruption lacks its original full timing receipt. & Estimated; unknown actuals \\
Reserves & USD200 contingency floor and 20\% of positive cumulative cash operating profit reserved for obligations. No statutory tax claim. & Assumed \\
Local compute & Observed joint CPU, allocated once across three services, at USD0.18/CPU-hour. This rate does not price authorship or human attention. & Observed + assumed \\
Capability & Four engineer + one reviewer hour and USD4 tools; USD439.69 construction. Quarter-hour engineer maintenance/cycle; 100 uses; three-cycle life; zero salvage. & Estimated / assumed \\
Capacity / discovery & USD350 buys 40 extra attempts/cycle for three cycles; USD15 maintenance. Discovery pilot costs USD345.29 but has no measured benefit. No actual purchase. & Assumed / estimated \\\bottomrule\end{tabularx}
\caption{Nonzero complete-cost envelope. Exact values, source links and classifications are in the frozen configuration; unknown live costs remain null.}
\end{table}
The initial economic implementation costed setup, failed construction and maintenance in cash but omitted some of their human/elapsed time from resource admission. A disclosed amendment added that time without changing the original economic assumptions. No original scenario's production count or cash result changed because those additional minutes did not breach its ceiling. The original engine and all original outputs are retained in a hashed history archive. Post-result remediation and bottleneck sensitivities are reported separately."""
    put("assumptions.tex", t)
    last = base[-1]
    surplus = B["available_operating_surplus_usd"]
    need = B["next_plan_cash_need_usd"]
    small = B["budget_feasible_smaller_plan_cash_need_usd"]
    t = rf"""\subsection{{Modeled cash, reserves and the next plan}}
The six-cycle direct-sale base produces {B['accepted_by_family'][FAMILIES[0]]} assurance, {B['accepted_by_family'][FAMILIES[1]]} planning and {B['accepted_by_family'][FAMILIES[2]]} dossier acceptances. These are simulated orders informed by the local execution bridge; they are not additional executed customer jobs. Net external worker collections are USD{money(B['cumulative_net_external_collections_usd'])}; paid operating costs are USD{money(B['cumulative_operating_cash_paid_usd'])}. Closing cash is USD{money(B['closing_cash_usd'])}, including the original USD2,000 financing. Receivables of USD{money(B['closing_receivables_usd'])} are excluded from spendable funds. After cumulative losses are recovered and the obligation reserve is removed, available earned operating surplus is USD{money(surplus)}.

The prespecified next plan targets 20 orders per class, allowing up to two attempts each; acceptance is not guaranteed. Construction is USD{money(last['next_plan_construction_usd'])}, operating working capital USD{money(last['next_plan_operating_working_capital_usd'])}, and one cycle of child maintenance USD{money(last['next_plan_one_cycle_maintenance_usd'])}. Total precollection need is USD{money(need)}. Full-surplus cash coverage is {B['full_surplus_next_plan_coverage']:.2f}$\times$. However, its service cost exceeds the unchanged USD2,000 operating-spend ceiling: \textbf{{cash coverage does not make this plan executable under the study's limits}}.

A \textbf{{post-result feasibility diagnostic}}, without changing the ceilings, finds a largest balanced target of {B['maximum_budget_feasible_target_orders_per_family']} orders per class, costing USD{money(small)} including construction and working capital. Cash coverage is {B['budget_feasible_smaller_plan_surplus_coverage']:.2f}$\times$. This is an illustrative resource-feasible target, not a newly prespecified success or guaranteed acceptance. The child still fails economic admission against ordinary caching.
"""
    t += table(
        ["Allocation", "Earmarked USD", "20/class cash ratio", "12/class cash ratio", "Decision"],
        [
            [
                f"{int(p*100)}\\%",
                money(p * surplus),
                f"{p*surplus/need:.2f}" + r"$\times$",
                f"{p*surplus/small:.2f}" + r"$\times$",
                "HOLD",
            ]
            for p in [0, 0.25, 0.5, 0.75]
        ],
        "Policy scenarios allocate an envelope, not permission to spend. All base policies retain the incumbent. The 20-order plan fails operating-spend admission; the smaller plan fits but its child has negative measured-compute value.",
        "lrrrl",
    )
    t += r"""\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/financing.pdf}
\caption{Modeled earned surplus after obligations, separate from seed cash and receivables. The two horizontal lines show full precollection plan needs. Crossing a cash line establishes neither plan feasibility nor positive investment value.}\end{figure}

\subsection{Admission, losing constructions and delayed benefits}
The measured child changes fresh-slice CPU by approximately $-3.027$ milliseconds of savings per joint request against conventional caching: it is slower. At the assumed compute rate, 100 uses have slightly negative compute value, while construction costs USD439.69 and three maintenance cycles add USD70.05. No human-attention or quality saving is invented to rescue the investment. The incumbent remains the recommended production method. A separately labeled compelled-research scenario can buy the child, but it lowers cash and does not establish payback.

The discovery-process pilot is also HOLD: its productive effect is unmeasured. In the provider-limit scenario, purchased capacity can increase assumed attempts when a provider ceiling actually binds. At 0\% allocation the model accepts 72/71/68 outputs by class; at 50\%, a USD350 capacity block increases them to 101/98/97. This is assumed vendor capacity scaling, not capability improvement. Benefits start the following cycle, expire after three cycles and require maintenance. Neither more cumulative output nor a higher resource ceiling is self-acceleration.
"""
    put("financing_results.tex", t)
    fig, ax = plt.subplots(figsize=(10.7, 3.4))
    x = [r["cycle"] for r in base]
    ax.plot(
        x,
        [r["available_preallocation_operating_surplus_usd"] for r in base],
        color=COLORS[0],
        marker="o",
        lw=2.4,
        label="Available earned surplus",
    )
    ax.axhline(need, color="#b27a32", ls="--", label="20/class plan: cash need; spend-infeasible")
    ax.axhline(small, color=COLORS[1], ls=":", lw=2, label="12/class diagnostic: cash need")
    ax.set_xlabel("Modeled 30-day cycle")
    ax.set_ylabel("USD")
    ax.set_xticks(x)
    ax.grid(axis="y", alpha=0.18)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    savefig("financing", fig)
    t = r"""\subsection{Accepted output under fixed service limits}
The primary financial frontier holds the USD2,000 operating-spend, 3,000 human-minute and 160 elapsed-hour budgets fixed. The first cycle is limited by liquidity; subsequent base cycles hit operating spend. Construction and maintenance time count against the relevant human/elapsed ceilings. Turnaround here is aggregate modeled resource occupancy, not measured end-to-end customer latency. Actual local per-mission wall and CPU records remain separately available.
"""
    rows = []
    for ledger_row in base:
        cycle = ledger_row["cycle"]
        fs = [
            next(
                r
                for r in F
                if r["scenario"] == "base" and r["policy_fraction"] == 0 and r["cycle"] == cycle and r["family"] == f
            )
            for f in FAMILIES
        ]
        rows.append(
            [
                cycle,
                " / ".join(str(ledger_row["accepted_by_family"][f]) for f in FAMILIES),
                " / ".join(f"{r['cost_per_accepted_usd']:.2f}" for r in fs),
                sum(ledger_row["failures_by_family"].values()),
                f"{ledger_row['estimated_human_minutes']:.0f}",
                f"{ledger_row['estimated_elapsed_hours']:.1f}",
            ]
        )
    t += table(
        ["Cycle", "Accepted A/P/D", "Cost each A/P/D (USD)", "Failed orders", "Human min", "Elapsed h"],
        rows,
        "Modeled per-class production, with A=assurance, P=planning, D=dossier. Failed attempts are charged even when an order eventually succeeds; unused reservations are released. Counts are not a composite quality score.",
    )
    t += r"""Every simulated acceptance assumes the scoped technical acceptance and the estimated review effort. There is no customer-quality score hidden in these counts. No new capability is bought in the base policies, so ordinary growth from the initial liquidity constraint is not a capability effect.

\subsection{Stress tests and settlement routes}
"""
    chosen = [
        ("base", "Direct base"),
        ("price_compression", "Prices at 45\\%"),
        ("high_supervision", "Attention $3\\times$"),
        ("failure_stress", "30\\% attempt failures"),
        ("slow_collection", "Slow collection"),
        ("demand_stall", "Demand stops"),
        ("alpha_route", "Alpha route"),
        ("alpha_token_stress", "Alpha token stress"),
        ("manager_route", "Manager / USDC"),
        ("jobs_route", "Jobs illustrative route"),
        ("compelled_research", "Compelled child research"),
    ]
    rows = []
    for key, label in chosen:
        r = scenarios[key, 0.5]
        rows.append(
            [
                label,
                " / ".join(str(r["accepted_by_family"][f]) for f in FAMILIES),
                money(r["closing_cash_usd"]),
                money(r["available_operating_surplus_usd"]),
                money(r["cumulative_investment_usd"]),
            ]
        )
    t += table(
        ["Scenario; 50\\% policy", "Accepted A/P/D", "Closing cash", "Earned surplus", "Investment"],
        rows,
        "USD; six cycles. All rows are modeled. Initial capital remains separate. A route with different participant entitlements is a different business proposition; gross customer price cannot be treated as worker revenue.",
        "lrrrr",
    )
    t += r"""Price compression and tripled attention erase the base financing surplus. Demand can stop while fixed support and administration continue. Low reuse does not make the child attractive; it already fails admission at 100 uses and also fails at five. The Alpha stress combines a 30\% conversion-mark haircut, 5\% spread and USD10 gas per order. The Manager default worker share can make these same prices uneconomic even without speculative volatility. Jobs uses an explicitly configured illustrative worker fraction; no live configuration was read back. Gas, conversion spreads, lock durations and collateral amounts are assumptions, including the Alpha case's nonbinding configurable minimum stake.
"""
    addpath = ROOT / "economics/outputs/addendum.json"
    if addpath.exists():
        add = read("economics/outputs/addendum.json")["results"]
        rem = [r for r in add if r.get("sensitivity_kind") == "remediation_cost"]
        if rem:
            t += r"\subsection{Post-result cost and review sensitivities}" + "\n"
            t += (
                r"""The corrective adapter's actual engineering and model charges are unknown. A separately declared post-result addendum adds remediation engineer hours, proportional review and tool cost to the business envelope, leaving the original scenario intact. These are sensitivity amounts, not a reconstruction of observed expense. The zero-extra row denotes the unchanged original allowance, not zero actual remediation."""
                + "\n"
            )
            t += table(
                ["Extra engineer h", "Extra review h", "Extra cost USD", "Earned surplus USD", "Accepted A/P/D"],
                [
                    [
                        f"{r['extra_engineer_hours']:g}",
                        f"{r['extra_review_hours']:g}",
                        money(r["extra_estimated_cost_usd"]),
                        money(r["available_operating_surplus_usd"]),
                        " / ".join(str(r["accepted_by_family"][f]) for f in FAMILIES),
                    ]
                    for r in rem
                ],
                "Post-result sensitivity; not a prospective primary result. Large up-front remediation can exhaust initial liquidity before demand can be served.",
                "rrrrl",
            )
        t += (
            r"""At 16 additional engineering hours plus four review hours, the prelaunch cash requirement prevents every customer order: zero accepted outputs, zero closing cash and USD1,176.60 of unpaid obligations. This failure must not be canceled by the allocation-only calculation below. The same addendum varies attention at a tighter human-minute ceiling to expose a review bottleneck rather than assuming unlimited supervision. It also varies total initial integration effort. Full assumption files and all losing rows accompany the study. These ranges clarify what must be measured in a real pilot; they are not evidence that the offered durations or staffing ratios are accurate."""
            + "\n"
        )
    reviews = [r for r in add if r.get("sensitivity_kind") == "human_attention_budget"] if addpath.exists() else []
    if reviews:
        t += table(
            ["Human minutes/cycle", "Assurance accepted", "Planning accepted", "Dossier accepted"],
            [[r["full_human_minutes_per_cycle"]] + [r["accepted_by_family"][f] for f in FAMILIES] for r in reviews],
            "Post-result review-capacity scenario; six cycles, all other assumptions retained. More review time stops increasing production once operating spend becomes binding.",
        )
    authpath = ROOT / "economics/outputs/authorship_allocation.json"
    if authpath.exists():
        ar = read("economics/outputs/authorship_allocation.json")["rows"]
        chosen_auth = [
            r
            for r in ar
            if (r["extra_engineer_hours"], r["extra_unmetered_model_tool_bill_usd"])
            in [(4, 50), (16, 250), (40, 250), (80, 1000)]
        ]
        t += (
            r"""A second post-result allocation sensitivity charges additional study authorship and unknown model/tool bills over the 362 assumed accepted outputs. This differs from a liquidity rerun: spreading a sunk cost over successful future work cannot fund prelaunch expense. Both analyses are retained so apparent end-period profitability cannot conceal an unfunded start. Actual study authorship time and model bills remain null."""
            + "\n"
        )
        t += table(
            ["Extra engineer h", "Extra tools USD", "Cost each A/P/D (USD)", "Remaining surplus USD"],
            [
                [
                    r["extra_engineer_hours"],
                    money(r["extra_unmetered_model_tool_bill_usd"]),
                    " / ".join(money(r["allocation_only_cost_per_accepted_by_family"][f]) for f in FAMILIES),
                    money(r["allocation_only_available_surplus_after_20pct_obligation_buffer_usd"]),
                ]
                for r in chosen_auth
            ],
            "Allocation-only sensitivity with additional review at one quarter of engineer hours. It does not rerun demand, staffing or prelaunch liquidity.",
            "rrlr",
        )
    put("frontier_results.tex", t)
    fig, ax = plt.subplots(figsize=(10.7, 3.9))
    select = chosen[:6] + chosen[6:10]
    vals = [scenarios[k, 0.5]["available_operating_surplus_usd"] for k, _ in select]
    labs = [label.replace("\\%", "%").replace("$3\\times$", "×3") for _, label in select]
    ax.barh(range(len(vals)), vals, color=[COLORS[0] if v > 0 else "#a65268" for v in vals])
    ax.set_yticks(range(len(vals)), labs)
    ax.invert_yaxis()
    ax.set_xlabel("Available modeled earned surplus after six cycles (USD)")
    ax.grid(axis="x", alpha=0.16)
    ax.set_axisbelow(True)
    for i, v in enumerate(vals):
        ax.text(v + 80, i, f"{v:,.0f}", va="center", fontsize=9)
    ax.set_xlim(0, max(vals) * 1.16)
    savefig("stress", fig)
    # Exact review counts are loaded, never guessed from prose.
    qa = []
    for path, label, scope in [
        (
            "review/INDEPENDENT_EVIDENCE_AUDIT.json",
            "Primary saved-output audit",
            "72 outputs; 38 frozen files; 14 source bodies",
        ),
        (
            "review/INDEPENDENT_CORRECTION_AUDIT.json",
            "Correction saved-output audit",
            "28 cases; 36 corrective frozen files",
        ),
        (
            "review/INDEPENDENT_FINANCIAL_AUDIT.json",
            "Financial event/ledger audit",
            "52 scenarios/policies; 312 cycles; 936 class rows",
        ),
        (
            "review/INDEPENDENT_SENSITIVITY_AUDIT.json",
            "Post-result addenda audit",
            "13 simulation and 20 allocation cases",
        ),
    ]:
        p = ROOT / path
        if p.exists():
            a = json.loads(p.read_text())
            qa.append(
                [label, format(a.get("checks", a.get("assertions", 0)), ","), tex(a.get("status", "see report")), scope]
            )
    demo = read("demo/VERIFICATION.json")
    qa.append(
        [
            "Local browser workflow",
            str(len(demo["checks"])),
            "PASS" if demo["passed"] else "FAIL",
            "Fresh artifacts, bilingual controls, stress, refusal",
        ]
    )
    t = table(
        ["Check", "Assertions", "Status", "Scope"],
        qa,
        "Separate reviewer implementations; same-session independence limits apply. Financial assertion count measures reconciliation work, not independent customer observations.",
        "p{.26\\linewidth}rp{.1\\linewidth}p{.39\\linewidth}",
    )
    t += r"""The native engine uses Python 3.12.14, NumPy 2.4.6, SciPy 1.17.0 and Node 24.22.1 in this environment. Existing specialist source bytes remain unchanged; the full upstream Node pin and repository-wide release qualification were not rerun. The actual local Chromium demonstration makes no network requests. Source licensing, exact requirements and a non-destructive verification command are included. An unchanged-source re-execution may produce different timings and solver ties; saved-output checks establish the preserved record's identities and constraints. The primary checker and the independent-role checker are distinct implementations, but neither is a commercial customer acceptance panel."""
    put("verification.tex", t)
    put(
        "scorecard.tex",
        r"""\begin{table}[H]\small\begin{tabularx}{\linewidth}{p{.21\linewidth}p{.19\linewidth}X}\toprule Proposition & Status & Practical decision \\\midrule
Scoped useful production & Observed local pass & Inspectable source inventory, constrained plan and bilingual dossier; fresh corrective adapter qualified on finite cases. \\
Traditional-work value & Conditional win & Modeled purchase breaks even at about 60/79/57 traditional minutes. At 30 minutes all offers lose; actual matched durations remain unknown. \\
Complete live cost & Unmeasured & USD28--35 is an economic envelope, not a live bill. Measure attention, model use, revisions and support before quoting a margin. \\
Earned financing capacity & Modeled & USD8,776 surplus covers a smaller resource-feasible plan; capability admission remains HOLD. Original 20/class plan violates the spend ceiling. No paid self-financing demonstration. \\
Child versus incumbent & Lose / HOLD & Ordinary caching matches scope and is slightly faster. Do not charge compute savings that were not observed. \\
Capacity purchase & Conditional modeled win & Provider-limited demand can justify purchased attempts; vendor availability and demand are assumptions. \\
Discovery and frontier & Not established & No previously impractical valuable class becomes feasible at the same budgets; no discovery productivity gain or self-acceleration. \\
Token-holder return & Not established & Utility, worker proceeds, business surplus and holder claims are separate. No automatic 50\% allocation or appreciation thesis. \\\bottomrule\end{tabularx}
\caption{Commercial decisions earned by this edition's evidence. ``Conditional'' always refers to explicit scenario premises, not demonstrated external demand.}\end{table}""",
    )
    (PAPER / "PRESENTATION_INPUTS.json").write_text(
        json.dumps(
            {
                "economic_summary_sha256": hashlib.sha256(
                    (ROOT / "economics/outputs/summary.json").read_bytes()
                ).hexdigest(),
                "economic_ledger_sha256": hashlib.sha256(
                    (ROOT / "economics/outputs/ledger.json").read_bytes()
                ).hexdigest(),
                "scope": "Derived paper sections and figures, no economic retuning",
                "generated_sections": [p.name for p in GEN.glob("*.tex")],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "paper_generated": True,
                "base_costs": B["full_cost_per_accepted_by_family"],
                "surplus": surplus,
                "next_plan": need,
                "budget_feasible": B["next_plan_budget_feasible"],
            }
        )
    )


if __name__ == "__main__":
    main()
