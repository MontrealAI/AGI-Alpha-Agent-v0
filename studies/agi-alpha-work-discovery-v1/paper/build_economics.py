# SPDX-License-Identifier: Apache-2.0
"""Generate paper tables from the one frozen economic campaign."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def load(name: str) -> Any:
    return json.loads((ROOT / "outputs/economics-primary" / name).read_text())


def save(name: str, text: str) -> None:
    (PAPER / name).write_text(text.strip() + "\n")


def main() -> None:
    summary = load("paper-summary.json")
    rows = []
    labels, means, minimums, maximums, colors = [], [], [], [], []
    for cell in summary["cells"]:
        result = cell["policies"]["A"]
        profit = result["simulatedOperatingProfitCents"]
        project = result["simulatedProjectProfitCents"]
        rows.append(
            f"{cell['demand']} & {cell['integrationMinutes']} & {cell['competitorStrength']} & "
            f"{cell['costBundle']} & {result['acceptedJobs']['mean']:.2f} & "
            f"{profit['mean'] / 100:.2f} & {project['mean'] / 100:.2f} \\\\"
        )
        labels.append(
            f"{cell['demand'][:3].title()} / I{cell['integrationMinutes']} / "
            f"{cell['competitorStrength']} / {cell['costBundle'][:3]}"
        )
        means.append(profit["mean"] / 100)
        minimums.append(profit["minimum"] / 100)
        maximums.append(profit["maximum"] / 100)
        colors.append("#64539b" if cell["costBundle"] == "low" else "#60788c")
    save(
        "abstract-results.tex",
        r"""
\begin{abstract}
We searched six materially different job families and executed two scoped offerings before
writing the paper. A REM transit-feed packet passes canonical structural validation and 86
independent reconciliation checks, while retaining 1,565 warnings. Three new API release
questions are accepted in all four compared approaches; three additional planned questions
remain source-acquisition failures. The retained conventional workflow is faster than the
Workbench full index, incremental registry and graph composition. Two competent recipients
reconstruct equivalent methods before receiving the asset. The original transfer control is
content-identical; a separately frozen changed-content follow-up is accepted by the narrow
system workflow but stopped by the second recipient's stricter input validator.

A source-frozen finite-cash simulation uses these measurements and explicitly assumed demand,
attention, competition and cost conditions. Across 384 paired worlds and 1,536 policy histories,
none produces positive ordinary operating surplus or funds a capability investment. The most
favorable cell averages a \$391.55 operating loss and a \$515.97 loss after its modeled opening
costs. Actual collections are zero and complete actual costs remain unknown. The supported
result is useful scoped delivery with preserved reusable engineering and a negative test of
the declared commercial cycle, not automation savings established against timed humans,
scarce transferable capability, graph advantage, modeled self-financing succession or realized
commercial success.
\end{abstract}
""",
    )
    save(
        "economic-methods.tex",
        r"""
\subsection{Frozen buyer-and-competitor experiment}

The source and calibrated inputs were frozen and posted before the first economic run.
There are 24 conditions, from three buyer arrival probabilities (0.025, 0.125 and 0.25 per
buyer-week), two buyer integration conditions (0 and 15 minutes), two competitor conditions
(equal and stronger), and two full-cost bundles (low and reference). Sixteen paired seeds
produce 384 worlds; each contains four separate counterfactual policy histories over 52 weeks. The
24-buyer pool is an assumed simulation population, not an estimated addressable market.

Each enterprise starts with \$1,000 seed capital and a \$200 investment reserve. The reserve
limits discretionary capability investment; it does not prevent ordinary obligations from
exhausting cash. Customer payments arrive two weeks after accepted delivery, with a modeled
0.98 collection probability. Unpaid expenses remain obligations. Receivables, seed and internal
transfers are not operating-generated investment funds. All book money uses integer cents;
investment benefit comparisons retain microdollar precision and conservative cash-rounding effects.

The common 0.5 source-availability condition reflects the six locked questions' 3/6 observed
availability, solely as a scenario calibration. A blocked source incurs acquisition and
five assumed triage minutes, no delivery retry, onboarding, support or invoice. Available
jobs use the observed 3/3 conditional acceptance plus a 0.98 execution-stress assumption
and at most two attempts. These are scenario mechanisms, not estimated population probabilities.
Human-only/public-DIY delivery uses the same assumed 5, 15 or 45 minutes with competent
conventional software. No extra undocumented speed multiplier makes that baseline artificially weak.

The enterprise and equal AI-assisted competitor use the same prospective cost function and
tariff rule. The tariff is the smallest member of a labor-equivalent grid that covers expected
collected-job cost at three intended orders per week. That cost includes source rejection,
execution, correction, support, allocated onboarding, weekly business/maintenance/tools, ordinary
setup and compute. A neutral paired draw resolves equal paid offers. The stronger competitor
has an explicit 0.6 labor-efficiency assumption. At week 20 competitors can copy, reduce effort
and cut prices subject to their prospective cost floor. Buyers can self-serve or decline;
orders, delivered jobs, customer avoided labor and collected revenue remain separate.

The low bundle assumes two residual provider minutes per attempt, 0.5 support minutes per order,
five provider-onboarding minutes, five weekly business minutes, two weekly maintenance minutes
and \$1 weekly tools. The reference bundle uses five, two, fifteen, fifteen and five minutes,
respectively, and \$5 weekly tools. Their modeled historical discovery/setup openings cost
\$124.42 and \$502.63. These labor and inference allocations are not observed invoices.
Candidate construction performed in the research remains an unknown actual historical cost;
the counterfactual enterprise pays the candidate's modeled incremental cost once only if
it purchases that asset. Adding omitted nonnegative historical research costs cannot improve
the negative recovery results.

All policies begin with retained conventional A. Policy A makes no purchase; B permits A to B;
C permits A to B to C; D permits A to B to D, with graph costs itemized in its second asset.
The second purchase cannot bypass its first prerequisite. Investments have a 26-week useful
life, an eight-week lookback and earliest investment week eight. Forecasts discount observed
reuse and are bounded by remaining useful life. These operating policies are distinct from
the separately reported prebuilt A/B/C/D engineering comparison.

Before outcomes, synthetic and independent review corrected asymmetric tariff treatment,
unmatched DIY time, acquisition sharing, source-blocked costs and cash rounding. The initial
drafts and failed signed-zero control are retained. No simulated profit was used to tune these
changes. All 26 final synthetic controls passed; there was one primary market run and no
favorable substitute campaign.
""",
    )
    save(
        "economic-results.tex",
        r"""
\subsection{The ordinary service fails before the investment loop}

\textbf{No world produces positive ordinary operating surplus.} Across all 384 worlds,
available earned investment funds remain exactly zero in every week. No first or second
capability is acquired, and no succession repays. The four policy results are identical
because every policy retains A. This is an operating-demand/cost failure before a capability
funding event, not a claim that graph execution caused the losses.

\begin{longtable}{@{}llllrrr@{}}
\caption{All 24 primary economic conditions, 16 seeds each. Mean accepted jobs and USD results.
Policies A/B/C/D coincide because no purchase is admitted. I is buyer integration minutes.}\\
\toprule Demand & I & Competitor & Cost & Jobs & Operating & Project\\ \midrule\endfirsthead
\toprule Demand & I & Competitor & Cost & Jobs & Operating & Project\\ \midrule\endhead
"""
        + "\n".join(rows)
        + r"""
\bottomrule\end{longtable}

The most favorable cell mean is high arrival, 15-minute buyer integration, equal competition
and low operating cost: 9.75 accepted jobs, \$153.28 simulated collections, \$391.55 operating
loss and \$515.97 modeled project loss. This is a post-run descriptive maximum, not a newly
selected confirmatory condition. Even the best individual world loses \$233.97 operating
and \$358.39 after opening costs: \$408.75 collected versus \$642.72 accrued operating costs
and \$124.42 opening costs. Its cash is \$655.70, unpaid obligations \$14.09 and receivables
\$32.70. Positive cash includes remaining seed and is not profit.

All reference-cost conditions exhaust cash and become insolvent at week 20. Their 19 charged
weeks accrue \$509.20 operating cost, in addition to \$502.63 opening cost, leaving \$11.83
unpaid. All low-cost/strong-competitor conditions collect nothing and lose \$448.76 in recurring
operation, or \$573.18 including opening costs. The model makes refusal, competition and
finite capital consequential rather than replacing missing sales with assumed transfers.

\begin{figure}[htbp]\centering
\includegraphics[width=0.95\linewidth]{figures/economic-cells.pdf}
\caption{All predeclared cells. Dots show mean operating outcome across 16 paired seeds; lines
show the full minimum--maximum range, not confidence intervals. Labels show demand, integration,
competition and cost bundle. Every range remains below zero. Reference-cost runs stop after
insolvency; they do not receive an extra seed injection.}
\end{figure}

\subsection{Cheap computation is not a complete service margin}

Including acquisition, failed source handling at the machine level and driver allocation, the
standalone mechanical CPU per accepted question is 1.547, 2.675, 2.891 and 2.744 seconds for
A/B/C/D. At the \emph{assumed} \$1 per CPU-hour, these are far below a cent. The actual billed
machine and inference costs are not known. Residual attention, low conversion and recurring
operation dominate the declared scenarios.

\begin{table}[htbp]\small
\caption{Prospective costing is not realized utilization. All dollar values below are modeled.}
\begin{tabularx}{\linewidth}{@{}Yrr@{}}
\toprule Quantity & Low bundle & Reference bundle\\ \midrule
Expected full prospective cost per collected job at reference utilization & \$15.48 & \$35.10\\
Resulting fixed grid tariff & \$16.35 & \$65.38\\
Historical discovery/setup opening & \$124.42 & \$502.63\\
First capability A to B, complete fixed incremental cost & \$135.77 & \$449.95\\
Second capability B to C, complete fixed incremental cost & \$119.43 & \$363.24\\
Second capability B to D, including graph increment & \$165.53 & \$509.46\\
\bottomrule\end{tabularx}
\end{table}

The best cell's actual modeled utilization produces approximately \$55.88 accrued recurring
cost per accepted job and \$68.64 including its opening allocations (ratios of cell totals).
Those figures differ from the \$15.48 prospective cost because competition and refusal prevent
the assumed reference utilization from being achieved. The grid's reference tariff jumps from
\$35.10 calculated cost to \$65.38, above the maximum modeled willingness to pay. This coarse
pricing choice contributes to refusal; it is a limitation of the tested policy, not empirical
evidence that a continuously priced offering cannot sell. No alternative price campaign was
introduced after observing these outcomes.

Human-only duration remains unmeasured. For example, the assumed 45-minute competent workflow
costs \$49.04 at the wage anchor; a \$16.35 service plus two buyer-review minutes costs \$18.53
before buyer integration. That conditional \$30.51 avoided cost is not observed savings,
enterprise revenue beyond the tariff, or available surplus. Shorter assumed human workflows
can rationally favor self-service. The diagnostic table varies residual attention over 2, 5 and
10 minutes and retains the unknown actual full-cost category.

\subsection{The proposed upgrades also lack a repayment case}

A to B adds 1.128 measured CPU seconds per available accepted question; B to C adds 0.216;
B to D adds 0.068. These signed deltas supply no positive CPU-only saving even at zero incremental
maintenance. The complete candidate investments therefore have no finite CPU-only break-even
reuse or repayment time. Adding the declared maintenance cannot improve that conclusion.
None was financed.

The separate C-to-D graph diagnostic has a 0.147-second observed CPU difference in the favorable
direction, without an added accepted job or identified planning gain. Even if that single-run
difference were stable and credited at \$1 per CPU-hour, the low \$46.10 graph increment would
require over 1.15 million reuses at zero maintenance with the frozen conservative microdollar credit (about 1.159 million under the conservative
cash-rounding diagnostic). Nonzero declared maintenance removes the finite repayment.
This is a sensitivity calculation, not evidence that the measured timing difference generalizes.

At an illustrative 156 execution reuses in 26 weeks, the low-cost A-to-B investment would need
about 0.90 minutes of additional paid attention avoided per reuse to cover its complete cost
and maintenance. No such saving was observed. This is a concrete measurement target for a
future capability test, not a benefit inserted into the present simulation.
""",
    )
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
    fig, ax = plt.subplots(figsize=(7.8, 7.0), layout="constrained")
    for i, mean in enumerate(means):
        ax.plot([minimums[i], maximums[i]], [i, i], color=colors[i], lw=1.8)
        ax.scatter(mean, i, color=colors[i], s=25, zorder=3)
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlim(-600, 15)
    ax.axvline(0, color="#17213b", lw=1)
    ax.grid(axis="x", alpha=0.16)
    ax.set_xlabel("52-week operating outcome (USD, simulated)")
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.savefig(PAPER / "figures/economic-cells.pdf")
    fig.savefig(PAPER / "figures/economic-cells.png", dpi=180)
    plt.close(fig)
    for name in ["main.tex", "reproduction.tex"]:
        p = PAPER / name
        text = p.read_text().replace("protocol/economic-freeze.json", "protocol/economics-freeze.json")
        text = text.replace("outputs/economics/", "outputs/economics-primary/")
        p.write_text(text)


if __name__ == "__main__":
    main()
