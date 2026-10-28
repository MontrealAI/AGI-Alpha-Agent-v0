# SPDX-License-Identifier: Apache-2.0
"""Generate economic publication material from archived confirmation results."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ECONOMICS = STUDY / "economics"
RESULTS = ECONOMICS / "confirmation-v2"
FIGURES = HERE / "figures"
INK = "#102824"
TEAL = "#166D61"
AMBER = "#B96C2E"
MUTED = "#52665F"
PALE = "#E5ECE8"


def usd(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


def math_amount(value: float) -> str:
    return "$" + f"{value:,.2f}".replace(",", "{,}") + "$"


def configure() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "font.size": 9,
            "axes.labelcolor": INK,
            "text.color": INK,
            "axes.edgecolor": MUTED,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.titlesize": 12,
            "axes.labelsize": 9,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.transparent": True,
        }
    )


def save(fig: plt.Figure, filename: str) -> None:
    fig.savefig(
        FIGURES / filename,
        format="pdf",
        bbox_inches="tight",
        pad_inches=0.06,
        metadata={
            "Title": filename.removesuffix(".pdf").replace("_", " "),
            "Author": "MONTREAL.AI",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)


def bridge(base: dict[str, Any]) -> None:
    revenue = float(base["mean_revenue_cents"]) / 100
    contribution = float(base["mean_contribution_cents"]) / 100
    operating = float(base["mean_recurring_operating_profit_cents"]) / 100
    project = float(base["mean_aftertax_project_profit_cents"]) / 100
    variable = revenue - contribution
    recurring = contribution - operating
    startup = operating - project
    fig, ax = plt.subplots(figsize=(6.5, 2.85))
    stages = [
        ("Earned\nrevenue", revenue, False, TEAL),
        ("Direct\ncosts", -variable, False, AMBER),
        ("Total\ncontribution", contribution, True, TEAL),
        ("Recurring\nenterprise costs", -recurring, False, AMBER),
        ("Startup\nexpense", -startup, False, AMBER),
        ("Full-project\nresult", project, True, INK),
    ]
    running = 0.0
    for index, (_, amount, total, color) in enumerate(stages):
        start = 0.0 if total else running
        end = amount if total else running + amount
        ax.bar(index, abs(end - start) / 1000, bottom=min(start, end) / 1000, color=color, width=0.64, zorder=3)
        label = ("−" if amount < 0 else "") + "$" + usd(abs(amount), 0)
        y = max(start, end) / 1000 + 0.7 if amount >= 0 else min(start, end) / 1000 - 1.0
        ax.text(
            index,
            y,
            label,
            ha="center",
            va="bottom" if amount >= 0 else "top",
            fontsize=9,
            fontweight="bold" if total else "normal",
            color=color,
        )
        if index < len(stages) - 1:
            ax.plot(
                [index + 0.32, index + 0.68],
                [end / 1000, end / 1000],
                color=MUTED,
                linewidth=0.7,
                linestyle=(0, (2, 2)),
                zorder=1,
            )
        running = end
    ax.set_xticks(range(len(stages)), [stage[0] for stage in stages], fontsize=8.5)
    ax.tick_params(axis="x", length=0, pad=7)
    ax.set_ylabel("Simulated USD, thousands")
    ax.set_ylim(-32, 11)
    ax.set_yticks([-30, -20, -10, 0, 10])
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.grid(axis="y", color=PALE, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Positive contribution fails to cover the enterprise", loc="left", pad=11)
    fig.tight_layout(pad=0.7)
    save(fig, "economic_cost_bridge.pdf")


def cash_paths() -> None:
    data: dict[str, dict[int, list[float]]] = {
        "qualified_instrument_449": defaultdict(list),
        "commitment_gated_449": defaultdict(list),
    }
    with (RESULTS / "monthly_ledger.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["scenario"] == "base" and row["policy"] in data:
                available = (int(row["cash_close"]) - int(row["custody_close"])) / 100000
                data[row["policy"]][int(row["month"])].append(available)
    fig, ax = plt.subplots(figsize=(6.5, 2.85))
    for policy, color in (("qualified_instrument_449", TEAL), ("commitment_gated_449", AMBER)):
        months = sorted(data[policy])
        means = [float(np.mean(data[policy][month])) for month in months]
        lower = [float(np.quantile(data[policy][month], 0.1)) for month in months]
        upper = [float(np.quantile(data[policy][month], 0.9)) for month in months]
        ax.fill_between(months, lower, upper, color=color, alpha=0.12, linewidth=0)
        ax.plot(months, means, color=color, linewidth=2.1)
    ax.axhline(30, color=MUTED, linewidth=1.0, linestyle=(0, (3, 3)))
    ax.text(17.5, 30.6, "Stop: $30,000 retained", color=MUTED, fontsize=8.5)
    ax.text(16.1, 25.3, "Commitment gate: $26,950", color=AMBER, fontsize=9, fontweight="bold")
    ax.text(16.1, 5.2, "Qualified instrument: $3,602", color=TEAL, fontsize=9, fontweight="bold")
    ax.annotate(
        "$9,600 launch outlay",
        xy=(0, 20.4),
        xytext=(2.8, 22.3),
        fontsize=8.5,
        arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.7},
        color=MUTED,
    )
    ax.axvspan(24, 30, color=PALE, alpha=0.65, zorder=0)
    ax.text(27, 15, "Settlement\nwindow", ha="center", va="center", color=MUTED, fontsize=8)
    ax.set_xlabel("Month from proposed launch")
    ax.set_ylabel("Unrestricted cash, USD thousands")
    ax.set_xlim(-0.4, 30.4)
    ax.set_ylim(0, 33)
    ax.set_xticks([0, 6, 12, 18, 24, 30])
    ax.set_yticks([0, 10, 20, 30])
    ax.grid(axis="y", color=PALE, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_title("How the launch decision changes remaining cash", loc="left", pad=11)
    fig.tight_layout(pad=0.7)
    save(fig, "economic_cash_paths.pdf")


def tex_section(summary: dict[str, Any]) -> str:
    rows = summary["confirmation"]
    lookup = {(row["scenario"], row["policy"]): row for row in rows}
    base = lookup[("base", "qualified_instrument_449")]
    subscription = lookup[("base", "subscription_349")]
    scenarios = [
        ("base", "Base"),
        ("competitive_pressure", "Competitive pressure"),
        ("demand_shortfall", "Demand shortfall"),
        ("supplier_disruption", "Supplier disruption"),
        ("cost_inflation", "Cost inflation"),
        ("late_payments", "Late payments"),
        ("combined_downside", "Combined downside"),
    ]
    policy_names = ["qualified_instrument_449", "subscription_349", "commitment_gated_449"]
    table = "\n".join(
        label
        + " & "
        + " & ".join(
            math_amount(lookup[(scenario, policy)]["mean_aftertax_project_profit_cents"] / 100)
            for policy in policy_names
        )
        + r" \\"
        for scenario, label in scenarios
    )
    return (
        r"""% GENERATED from archived economic results by build_economic_figures.py.
% Actual customers and receipts remain zero; all monetary results below are simulated.

\subsection{Frozen results: the unit contributes, the enterprise loses}

The initial confirmation contains 3,584 worlds; the revised confirmation contains
7,168 worlds, with 256 worlds per policy--scenario cell. The original best active
training policy was the \USD{349} subscription. After the revision, the precommitted
rule still selects \textbf{stop}. The commitment gate is the least-loss spending
policy, but no spending policy qualifies as profitable.

In the fresh base worlds, the \USD{449} instrument produces mean revenue of
\USD{@REVENUE@} and mean total contribution of \USD{@CONTRIBUTION@}. Contribution
per net retained order averages \USD{@UNIT@} across world-level ratios; this is a conditional modeled
commercial margin, not a measured market price. The enterprise delivers only
@ORDERS@ retained orders over @MONTHS@ active months on average. Its recurring
operating result is \(-\)\USD{@OPERATINGLOSS@}; including the launch expense, its
full-project result is \(-\)\USD{@PROJECTLOSS@}. Figure~\ref{fig:economic-bridge}
shows why a large per-order margin is insufficient.

\begin{figure}[htbp]
\centering
\includegraphics[width=\linewidth]{figures/economic_cost_bridge.pdf}
\caption{Mean simulated base-case cost bridge for the qualified \USD{449}
instrument, 256 worlds. Revenue is net of refunds. Direct costs include failed
attempts, retries, processing, support and bad debt. Recurring costs include acquisition and
\USD{1,200} equipment depreciation; the separate \USD{8,400} startup expense
therefore avoids counting equipment twice. Initial startup cash outlay is
\USD{9,600}. Figure labels are rounded; the prose and ledger retain exact cents.}
\label{fig:economic-bridge}
\end{figure}

The subscription has a higher mean number of retained orders (@SUBORDERS@), but
still loses \USD{@SUBLOSS@} over the full project. The instrument's simulated
acquisition cost, including allocated sales labor, averages \USD{@CAC@} per buyer,
against \USD{@LTV@} lifetime contribution within the observed \emph{simulated}
history. Neither model produces enough accepted demand to absorb the complete
enterprise cost. Every operating confirmation history loses money; none repays startup or
continues for the entire 24-month operating window.

\subsection{Stress outcomes and the meaning of survival}

\begin{table}[htbp]
\centering\small
\begin{tabularx}{\linewidth}{@{}Yrrr@{}}
\toprule
Scenario & \shortstack{Qualified\\\USD{449}} & \shortstack{Subscription\\\USD{349}} & \shortstack{Commitment gate\\\USD{449}} \\
\midrule
@SCENARIOS@
\bottomrule
\end{tabularx}
\caption{Mean simulated full-project profit in USD after all stated costs and
the assumed tax treatment. Each cell contains 256 fresh worlds. The stop policy,
omitted from the table, preserves initial capital and earns zero. No table entry
is realized revenue, a buyer quote, or evidence of willingness to pay.}
\label{tab:economic-stress}
\end{table}

All spending policies lose in every reported world, including the gate's search
expense when it does not launch. Insolvency frequency is zero: the operating
policies shut down before exhausting their reserve, and the revised gate does not
launch. This is loss containment, not sustainable cash generation. Cost inflation
can cause a smaller total loss by forcing earlier closure and fewer deliveries;
it does not improve the business. Late payment leaves the prepaid subscription
unchanged, making clear that invoice timing is not its binding commercial defect.

The base instrument's tenth percentile of profit is \(-\)\USD{@P10LOSS@};
its ninetieth percentile is \(-\)\USD{@P90LOSS@}. These percentiles describe
variation inside the authored economy. They cannot quantify uncertainty about
whether the assumed customer population or preferences exist.

\subsection{The revision improves the decision without inventing customers}

At the frozen base costs, the launch condition requires 57 simultaneous qualifying
commitments. The revised search obtains a mean peak of 4.32 and a maximum of 11
across the 256 base worlds. It launches in \textbf{0/256} worlds, earns no revenue,
and spends \USD{2,850} on search plus \USD{200} on closeout. Its unconditional
project loss is therefore \USD{3,050}; profit conditional on launch is
\texttt{null}, because the conditioning event never occurs.

\begin{figure}[H]
\centering
\includegraphics[width=\linewidth]{figures/economic_cash_paths.pdf}
\caption{Base-case unrestricted cash: means with pointwise tenth--ninetieth
percentile bands across the 256 synthetic worlds. The narrow gate path reflects
the same bounded search expenditure in every base world. The qualified offer
closes after a mean @MONTHS@ active months; its terminal mean cash is
\USD{@CASH@}. The final six months settle outstanding obligations. No refundable
customer custody is spent on operations.}
\label{fig:economic-cash}
\end{figure}

The intervention succeeds at preserving more of the \USD{30,000} initial equity.
It does not establish a profitable commercial opening. The frozen rule's stop
decision is economically preferable to paying for a presale search that the
current assumptions predict will fail; neither decision satisfies Proof~II.

\subsection{Sensitivity and the limits of the economic evidence}

The static qualified-product calculation allocates construction, recurring costs,
requalification and closeout into about \USD{3,431.67} per month. At a nominal
\USD{449}, its expected contribution is \USD{345.81} per retained order, versus
the dynamic histories' mean of \USD{@UNIT@}; the fixed-volume calculation omits
strategic price erosion and negotiated discounts. Approximately ten retained
orders per month would cover its burden, yielding only about \USD{634} pretax
over 24 months under constant-volume arithmetic. At \USD{349} the threshold
rises to fourteen orders, and at \USD{249}
to twenty-three. These are conditional thresholds, not jointly demonstrated
price--volume possibilities. Dynamic competition, acquisition, refunds and scope
refusal prevent the executed economy from reaching them.

A separate 40/80/160-hour replacement-construction sensitivity uses 32 new worlds
per policy and cost level. Both original operating policies continue to lose and
the commitment gate still refuses launch. Its control of timing helps preserve
capital without improving the unobserved willingness-to-pay premise. A large,
fully aware synthetic cohort was used only to exercise the simulator's launch
and positive-profit code branches; it is not an economic success scenario.

The corrected Decimal audit performs \textbf{3,512,320} monetary checks on the
revised confirmation and passes again under optimized Python. Twenty-one
archived participant traces replay exactly, and unchanged native AGI ALPHA code
agrees on 21 aggregate cash bridges. An original counter incorrectly included a
prior-month check in month zero; the original records and an explicit correction
are retained. Only that audit counter changed after confirmation, verified by an
AST comparison; no policy, outcome or money path changed. These checks establish
reproducible accounting within the model, not empirical demand or actual profit.

""".replace("@SCENARIOS@", table)
        .replace("@REVENUE@", usd(base["mean_revenue_cents"] / 100))
        .replace("@CONTRIBUTION@", usd(base["mean_contribution_cents"] / 100))
        .replace("@UNIT@", usd(base["mean_contribution_per_net_accepted_order_cents"] / 100))
        .replace("@ORDERS@", f"{base['mean_net_accepted_orders']:.2f}")
        .replace("@MONTHS@", f"{base['mean_active_months']:.2f}")
        .replace("@OPERATINGLOSS@", usd(-base["mean_recurring_operating_profit_cents"] / 100))
        .replace("@PROJECTLOSS@", usd(-base["mean_aftertax_project_profit_cents"] / 100))
        .replace("@SUBORDERS@", f"{subscription['mean_net_accepted_orders']:.2f}")
        .replace("@SUBLOSS@", usd(-subscription["mean_aftertax_project_profit_cents"] / 100))
        .replace("@CAC@", usd(base["mean_simulated_customer_acquisition_cost_cents"] / 100))
        .replace("@LTV@", usd(base["mean_simulated_lifetime_contribution_per_buyer_cents"] / 100))
        .replace("@P10LOSS@", usd(-base["profit_p10_cents"] / 100))
        .replace("@P90LOSS@", usd(-base["profit_p90_cents"] / 100))
        .replace("@CASH@", usd(base["mean_cash_end_cents"] / 100))
    )


def main() -> None:
    configure()
    FIGURES.mkdir(exist_ok=True)
    summary = json.loads((RESULTS / "SUMMARY.json").read_text())
    base = next(
        row
        for row in summary["confirmation"]
        if row["scenario"] == "base" and row["policy"] == "qualified_instrument_449"
    )
    bridge(base)
    cash_paths()
    (HERE / "generated_economics.tex").write_text(tex_section(summary))
    print("Generated generated_economics.tex, economic_cost_bridge.pdf, economic_cash_paths.pdf")


if __name__ == "__main__":
    main()
