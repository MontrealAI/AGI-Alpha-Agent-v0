# SPDX-License-Identifier: Apache-2.0
"""Generate traceable manuscript result sections and compact publication companions."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import statistics
import re
from typing import Any
from collections.abc import Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = HERE / "generated"
METHODS = {
    "beta_space": "Beta: space filling",
    "beta_dopt": "Beta: D-optimal",
    "beta_adaptive": "Beta: adaptive",
    "beta_direct": "Beta: direct search",
    "v1": "Origin v1",
    "v2": "Gym v2",
    "library_v2": "Identical-content library",
    "wrong_prior": "Unrelated prior",
    "oracle_support": "Oracle support",
}


def read(path: str) -> Any:
    return json.loads((ROOT / path).read_text())


def tex(value: object) -> str:
    text = str(value)
    for a, b in [("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")]:
        text = text.replace(a, b)
    return text


def write(name: str, text: str) -> None:
    (GEN / name).write_text(text.strip() + "\n")


def table(headers: list[str], rows: Sequence[Sequence[object]], spec: str) -> str:
    body = "\n".join(" & ".join(tex(v) for v in row) + r" \\" for row in rows)
    return (
        r"\begin{center}\small\begin{tabular}{"
        + spec
        + "}\n\\toprule\n"
        + " & ".join(headers)
        + r" \\ \midrule"
        + "\n"
        + body
        + "\n\\bottomrule\n\\end{tabular}\\end{center}\n"
    )


def group(rows: list[dict[str, Any]], method: str, budget: int, regime: str = "all") -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if r["method"] == method and r["budget"] == budget and (regime == "all" or r["regime"] == regime)
    ]


def count(rows: list[dict[str, Any]], method: str, budget: int, key: str, regime: str = "all") -> int:
    return sum(bool(r[key]) for r in group(rows, method, budget, regime))


def main() -> None:
    GEN.mkdir(exist_ok=True)
    rows = read("technical/results/confirmation_rows.json")
    robust = read("technical/robust/results/confirmation_rows.json")
    assert len({r["task_id"] for r in rows}) == len({r["task_id"] for r in robust}) == 48
    economy = read("economics/results/summary.json")
    primary = economy["primary"]
    learning = read("technical/results/learning_ledger.json")
    integration = read("integration/results/conformance-v1/summary.json")
    with (ROOT / "economics/results/enterprise_runs.csv").open() as stream:
        runs = list(csv.DictReader(stream))
    beta = primary["beta"]
    narrow = next(
        r for r in economy["summary"] if r["scenario"] == "query_envelope_40" and r["policy"] == "shared_gym_pilot"
    )
    narrow_beta = next(r for r in economy["summary"] if r["scenario"] == "query_envelope_40" and r["policy"] == "beta")

    def mean(record: dict[str, Any], key: str) -> float:
        return float(record[key]["mean"])

    write("macros.tex", "% Generated from recorded results; no model outputs are assumed here.\n")
    write(
        "cover-finding.tex",
        r"\textbf{A real but conditional transfer effect.} On 24 unfamiliar compatible response functions, v2 produced 21 accepted models inside a 24-call candidate budget; the strongest ordinary model arm produced one. In the separately frozen compound mission, v2 delivered 17 of 24 checked plans with 40 total queries, versus seven for the strongest individual conventional arm. A marketed response model also pays for 384 independent acceptance observations. Every accepted compound plan includes sixteen measured context checks. Shift, stronger budgets and simple direct solutions narrow the advantage. The primary economic policy rejects optional learning; no customer revenue or sustained compounding is established.",
    )
    overview = table(
        ["Question", "Evidence in this edition"],
        [
            ["Commercial delivery", "Positive conditional simulations; actual sales = 0"],
            ["Specialist development", "Fresh sparse-representation transfer is observed"],
            ["Network value", "Actual fixture transfer; same-content library parity"],
            ["Productive expansion", "Scoped 40-query compound-outcome crossings"],
            ["Sustained compounding", "Not established by this one-development-cycle study"],
        ],
        "p{0.26\\linewidth}p{0.65\\linewidth}",
    )
    write("results-overview.tex", overview)
    learned = [len(r["learned_nonzero_terms"]) for r in learning["events"]]
    write(
        "learning.tex",
        f"The originating fit consumed {learning['origin_oracle_calls']} observations and 384 separately paid response-accuracy checks. It retained nine terms, including the intercept. Ten optional Gym jobs consumed {learning['gym_oracle_calls']:,} additional fitting observations. Each fitted job retained {min(learned)}--{max(learned)} nonzero terms; their empirical union contains 21 terms. All eleven research characterization fits met the fresh prediction criterion. Those successful fits are not themselves evidence that retention repays its assessment cost. The primary confirmation contains 48 unfamiliar tasks and 1,728 method--budget rows; the independent compound extension adds 48 further tasks and 1,728 rows.",
    )
    tbl = []
    for method in METHODS:
        vals = [
            f"{count(rows, method, b, 'prediction_accepted')}/{count(rows, method, b, 'design_accepted')}"
            for b in [24, 40, 64, 96]
        ]
        tbl.append([METHODS[method], *vals])
    write(
        "technical-results.tex",
        table(["Method", "24", "40", "64", "96"], tbl, "lrrrr")
        + r"Each cell is \emph{accepted response models / accepted operating plans}, each out of 48 tasks. A response model additionally requires 384 independent acceptance observations; the plan's final check is inside the displayed budget. Direct search has no response-model deliverable, so its prediction entry is zero. At 24 queries the compatible-family prediction comparison is v2 21/24 versus adaptive Beta 1/24; v1 and the unrelated prior each score 0/24. Across all families, v2's fresh prediction advantage over the ex-post best ordinary arm is 20 wins and zero losses. Its corresponding operating-plan result is six wins and twelve losses: the positive model effect does not imply a positive action effect. At 96 queries D-optimal Beta accepts 48/48 models, versus v2 47/48. Both accept 44/48 operating plans; four menus have no qualifying plan.\par The identical-content library matches v2 on all 192 task--budget pairs. This is evidence that the effective learned information transfers, and evidence against attributing an additional benefit to the graph representation. Partial and novel families preserve negative transfer: at 40 queries, for example, partial-shift v2 model acceptance is 3/12, versus 7/12 for space-filling Beta.",
    )
    write(
        "frontier-results.tex",
        r"The primary single-plan offering does not establish an overall specialist advantage. At 24 calls, direct search accepts 27/48 operating decisions versus v2 22/48. At 40, the counts are 32/48 and 33/48, but different ordinary arms solve different cases: against the ex-post best conventional envelope, v2 has two unique wins and ten unique losses. Increasing the budget to 96 removes the plan-acceptance difference. These observations preserve commercially useful ordinary delivery while limiting the claim for optional retention.",
    )
    robust_tbl = []
    for method in [
        "beta_space",
        "beta_dopt",
        "beta_adaptive",
        "beta_direct",
        "v1",
        "v2",
        "library_v2",
        "wrong_prior",
        "oracle_support",
    ]:
        robust_tbl.append(
            [
                METHODS[method],
                f"{count(robust, method, 40, 'accepted', 'compatible')}/24",
                f"{count(robust, method, 40, 'accepted')}/48",
                f"{count(robust, method, 64, 'accepted')}/48",
                f"{count(robust, method, 96, 'accepted')}/48",
            ]
        )
    write(
        "robust-results.tex",
        table(["Method", "40, compatible", "40, all", "64, all", "96, all"], robust_tbl, "lrrrr")
        + r"At 40 total observations, v2 accepts 17/24 compatible-family compound plans; direct search, the strongest individual conventional arm on this stratum, accepts 7/24. The ex-post best of four conventional methods accepts 8/24. In the paired comparison v2 has ten unique wins and one unique loss: +37.5 percentage points, with a conditional task-bootstrap 95 percent interval of +12.5 to +58.3 points. Across all three families, v2 accepts 22/48 and that generous conventional envelope accepts 18/48, with eleven unique wins and seven losses: +8.3 points, interval -8.3 to +25.0 points. The intervals are conditional on the synthetic generator and are not corrected for every exploratory comparison. Thus the strong compatible-family result weakens substantially when recipient structure is unfamiliar. By 96 calls, the strongest conventional model arms and v2 each accept 36/48; twelve menus have no qualifying plan. This is a measured, scoped sample-budget crossing, not proof of universal feasibility or a deployment-grade reliability rate.\par The extension was proposed from development experience and confirmed on new seeds beginning at 1,910,000. Its empirical subpopulation labels are diagnostic: a live enterprise would need an observable family-qualification procedure before using the compatible-family result in a customer promise. Its hypothetical prices and customer demand were not validated or folded into the primary economic ledger.",
    )
    write(
        "opportunity-results.tex",
        r"The matched policies select and prototype the diagnostic offering using the same evidence, but an ordinary paired-difference method identifies the single changed interaction in all 48 fresh cases with 32 observations. The retained model is therefore unnecessary for that synthetic diagnosis. The primary enterprise does not count diagnostic sales because field verification and willingness to pay are unestablished; only a separately named market-hypothesis scenario permits them. Prototype development remains charged. This failed additional-Alpha case is preserved alongside the positive compound-plan result rather than replaced by it.",
    )
    assumptions = [
        ["Human service anchor", "USD 80/hour (sourced list rate)"],
        ["Estimated scopes", "12 hours model; 16 hours single-plan design"],
        ["Selected primary quotes", "USD 624 model; USD 832 verified design"],
        ["Simulator tariff / latency", "USD 0.10/call; 30 seconds/call (assumed)"],
        ["Model/tool/service bundle", "USD 9/job before queries/fees (assumed)"],
        ["Horizon / arrivals", "30 days; 4 opportunities/day (assumed)"],
        ["Resources", "3 agents, 8 hours/day each; USD 12,000 seed"],
        ["Collections / reserve floor", "7-day delay; USD 2,000 minimum reserve"],
        ["Replicates / scenarios", "64 matched seeds; 30 frozen scenarios"],
    ]
    write(
        "economic-assumptions.tex",
        table(["Input", "Primary specification"], assumptions, "p{0.34\\linewidth}p{0.58\\linewidth}")
        + r"Every quantity in this table apart from the published rate is an assumption or a policy selection within that assumption set. Model token volumes are not API traces. The USD 9 bundle includes assumed frontier inference, tools, packaging and residual service costs; it imposes no arbitrary human-review minutes. Payment fees, failed deliveries, assessment, optional practice, obligations and reserves are added explicitly. Actual research engineering effort and its complete realized monetary cost remain unknown; native accounting preserves unknown cost fields rather than converting them to zero.",
    )
    econ_tbl = []
    for policy, label in [
        ("beta", "Beta only"),
        ("private", "Private selective"),
        ("shared", "Shared selective"),
        ("shared_gym_pilot", "Controlled Gym pilot"),
    ]:
        r = primary[policy]
        econ_tbl.append(
            [
                label,
                f"{mean(r, 'simulated_revenue'):,.0f}",
                f"{mean(r, 'complete_cost'):,.0f}",
                f"{mean(r, 'profit'):,.0f}",
                f"{mean(r, 'simulated_collections'):,.0f}",
                f"{mean(r, 'available_funds'):,.0f}",
            ]
        )
    paragraph = table(["Policy", "Revenue", "Cost", "Profit", "Collected", "Available"], econ_tbl, "lrrrrr")
    paragraph += f"All entries are mean simulated USD over 30 days. Beta's operating profit is {mean(beta, 'profit'):,.2f}, with conditional seed interval [{beta['profit']['conditional_seed_ci95_low']:,.2f}, {beta['profit']['conditional_seed_ci95_high']:,.2f}]. Its A/B/C costs are {mean(beta, 'cost_A'):,.2f}, {mean(beta, 'cost_B'):,.2f} and {mean(beta, 'cost_C'):,.2f}. Mean collections are {mean(beta, 'simulated_collections'):,.2f}; receivables are {mean(beta, 'receivables'):,.2f}. Cash of {mean(beta, 'cash'):,.2f} includes the separate 12,000 seed capital. Reserves are {mean(beta, 'reserves'):,.2f}; unpaid obligations are {statistics.mean(float(x['obligations']) for x in runs if x['scenario'] == 'primary' and x['policy'] == 'beta'):,.2f}. Available funds are {mean(beta, 'available_funds'):,.2f}; available earned surplus is {mean(beta, 'available_earned_surplus'):,.2f}. These distinct quantities reconcile in every retained run.\n\n"
    paragraph += r"The primary optional policies reject v1 and preserve cash instead of choosing Gym training. They still pay for assessing the candidate and lose delivery capacity while doing so. Their mean profit is USD 2,393.30 below Beta. A controlled Gym-pilot arm deliberately pays for development so that the experiment can test v2; it is not the endogenous optimizer's selected action. That arm rejects v2 at the unrestricted envelope and loses USD 4,910.24 relative to Beta. Rejecting the investment does not erase the cost of discovering that it was unattractive.\par "
    paragraph += f"In the predeclared 40-call fitting-envelope scenario, the controlled Gym pilot has mean conditional profit USD {mean(narrow, 'profit'):,.2f}, versus Beta's {mean(narrow_beta, 'profit'):,.2f}. Its paired increment is {mean(narrow, 'paired_incremental_profit_vs_beta'):,.2f}, interval [{narrow['paired_incremental_profit_vs_beta']['conditional_seed_ci95_low']:,.2f}, {narrow['paired_incremental_profit_vs_beta']['conditional_seed_ci95_high']:,.2f}]. Response-model contracts still pay 384 additional acceptance queries in both arms. This narrow-envelope economic result is separate from the robust-plan supplement and from the primary 96-call scenario. The pilot uses a point-forecast investment rule; the existing lifecycle instead rejects the candidate under its conservative uncertainty rule. The pilot is a controlled counterfactual, not an authorized shared-production outcome passing that gate. It depends on assumed buyer behavior, scarcity, prices and reuse, and does not establish net value from sharing rather than private use."
    write("economic-results.tex", paragraph)
    resource = read("technical/analysis/research_resource_reconciliation.json")
    resource_rows = [[x["phase"], f"{x['subtotal_query_equivalent_units']:,}"] for x in resource["primary_campaigns"]]
    resource_rows.extend(
        [[x["phase"], f"{x['subtotal_query_equivalent_units']:,}"] for x in resource["robust_campaigns"]]
    )
    resource_rows.extend(
        [[x["phase"], f"{x['query_equivalent_units']:,}"] for x in resource["additional_documented_runs"]]
    )
    resource_rows.append(["Documented resource subtotal", f"{resource['documented_campaign_plus_extra_subtotal']:,}"])
    write(
        "research-resources.tex",
        table(["Recorded research phase", "Query-equivalent units"], resource_rows, "lr")
        + r"This is a documented workload subtotal, not a certified complete research cost. It includes deliberate repeated construction and smoke campaigns. The original constructor's audit count is reconstructed from the executed routine rather than a separately preserved audit file. Common audit labels are counted once per task and campaign; literal recomputation of 8,576 already-known robust replay labels would raise the subtotal to 821,504. At the hypothetical USD 0.10 tariff, the two subtotals are USD 81,292.80 and USD 82,150.40. No corresponding invoice was incurred. Engineering effort, plotting, bootstrap, review and ordinary computing costs are unmetered. Paid-origin observations and the Gym already present in a policy's A/C ledger must not be charged again when allocating these study costs. This resource inventory does not justify subtracting the whole campaign mechanically from every simulated enterprise.",
    )
    selected = [
        "half_demand",
        "low_trust",
        "query_price_0_5",
        "query_price_2",
        "validator_correlated",
        "extra_896_verification",
        "query_envelope_40",
        "stronger_beta",
    ]
    stress = []
    for scenario in selected:
        b = next(x for x in economy["summary"] if x["scenario"] == scenario and x["policy"] == "beta")
        s = next(x for x in economy["summary"] if x["scenario"] == scenario and x["policy"] == "shared_gym_pilot")
        stress.append(
            [
                scenario.replace("_", " "),
                f"{mean(b, 'profit'):,.0f}",
                f"{mean(s, 'profit'):,.0f}",
                f"{mean(s, 'paired_incremental_profit_vs_beta'):,.0f}",
            ]
        )
    write(
        "stress-results.tex",
        table(["Scenario", "Beta profit", "Gym pilot profit", "Pilot increment"], stress, "lrrr")
        + r"The USD 0.50 and USD 2 query cases make the assessment campaign unaffordable within the declared reserve constraint; the policy preserves cash after the originating job instead of assuming unlimited financing. Some stressors have no effect because the relevant skill was never admitted. That inactivity is informative and is not a successful stress test of a deployed sharing service. Correlated-error scenarios record mistaken invoices, refund obligations and unrecovered delivery/fee costs. Same-content library profit gaps are zero. Additional capacity is not purchased merely because funds exist when the frozen expansion condition is unmet. The confirmation research audit itself is disclosed separately as 44,544 unique oracle-equivalent observations, or USD 4,454.40 at the primary hypothetical tariff, rather than hidden as free acceptance or repeatedly charged to all enterprises.",
    )
    write(
        "integration-results.tex",
        f"The recorded integration campaign passes {integration['passed']}/{integration['total']} directed controls against 29 unchanged upstream files. It transports the actual 2,753-byte v2 artifact and checks identical retrieval, rights, current fixture membership, revocation, altered bytes, AES-GCM context binding, idempotency and disjoint costs. A separate recipient fits an unfamiliar task from the recovered bytes in 40 observations and delivers an accepted operating decision; the same-content ordinary library produces identical output. That recipient is an integration witness, not an additional independent confirmation sample.\n\n"
        + r"The actual development-evidence admission assay rejects v2 at both tested 96-call and 40-call envelopes. At 96 calls its mean incremental per-use value is USD -6.85; at 40 its positive mean is too uncertain for the gate's conservative bound after assessment and lifecycle costs. Both corresponding production-like research retrievals remain denied. Positive access conformance uses explicitly artificial monetary evidence and never substitutes for an empirical admission. Real measured complete profit remains unknown in the native unknown-cost control.",
    )
    write(
        "conclusion.tex",
        r"The experiment establishes an executable form of experience-trained specialization: a learned interaction representation improves fresh response modeling and, in a separately frozen compound mission, enables more accepted outputs inside a small complete observation budget. It also establishes boundaries. Direct action search can bypass the need for an accurate model; ordinary paired measurements can defeat the proposed diagnostic advantage; unrelated recipients reduce transfer; a larger conventional budget can erase a crossing; and an ordinary library containing the same capability matches the protected research route.\par Commercial simulation is positive for competent delivery under the stated market assumptions. The primary policy declines retention and Gym investment, while a predeclared tighter-envelope pilot shows a conditional economic benefit from the developed representation. The real admission gate still rejects the candidate on uncertainty-adjusted development evidence. No sales, sustained compounding, graph-specific advantage or live frontier-model superiority is established. The next justified step is to test the compound-outcome mechanism on an actual customer's expensive simulator with observed validation costs and a capable live frontier baseline.",
    )
    facts = {
        "main_tasks": 48,
        "main_rows": len(rows),
        "robust_tasks": 48,
        "robust_rows": len(robust),
        "v2_prediction_compatible_24": count(rows, "v2", 24, "prediction_accepted", "compatible"),
        "v2_robust_compatible_40": count(robust, "v2", 40, "accepted", "compatible"),
        "beta_direct_robust_compatible_40": count(robust, "beta_direct", 40, "accepted", "compatible"),
        "economic_histories": len(runs),
        "primary_beta_profit_simulated": mean(beta, "profit"),
        "tight40_gym_increment_simulated": mean(narrow, "paired_incremental_profit_vs_beta"),
        "actual_revenue": 0,
        "integration_checks": [integration["passed"], integration["total"]],
    }
    (ROOT / "publication_facts.json").write_text(json.dumps(facts, indent=2) + "\n")
    preamble = r"""\documentclass[11pt,letterpaper]{article}
\usepackage[margin=0.78in]{geometry}
\usepackage[T1]{fontenc}\usepackage{lmodern,microtype,booktabs,array,longtable,xcolor,graphicx}
\usepackage[colorlinks=true,urlcolor=teal]{hyperref}\usepackage{xurl}
\widowpenalty=10000\clubpenalty=10000
\definecolor{teal}{HTML}{087E8B}\setlength{\parindent}{0pt}\setlength{\parskip}{7pt}
\begin{document}
{\sffamily\color{teal}\large AGI ALPHA FLYWHEEL}\par
"""
    brief = (
        preamble
        + r"""{\Huge\bfseries When Capability\\Creates Opportunity}\par
\vspace{0.15in}
{\large Executive brief}\par
\textbf{Vincent Boucher}\quad President of MONTREAL.AI\par
27 October 2026\par
\section*{The result worth acting on}
A reusable representation learned from earlier simulator jobs improves fresh model construction. More consequentially, it helps deliver one operating plan that passes sixteen environmental checks inside a small total observation budget. The effect is strongest when the new work shares the learned structure.
\begin{center}\begin{tabular}{lrr}\toprule
Fresh compatible tasks & Developed v2 & Strong conventional arm\\\midrule
Accurate model, 24-call candidate budget & 21/24 & 1/24\\
Robust plan, 40 total calls & 17/24 & 7/24\\\bottomrule\end{tabular}\end{center}
The candidate budget includes visible validation and any required plan check. The model service additionally pays for 384 independent verification observations. The robust-plan budget already includes all sixteen final context measurements. The latter is a useful, checked output rather than merely a better prediction score.
\section*{Where the advantage disappears}
For one satisfactory operating point, direct search often avoids building a model. Across all families at 24 calls it succeeds in 27/48 cases, versus v2's 22/48. At 96 calls the strongest methods tie on 44/48 single-plan outcomes. The robust-plan gain also weakens under distribution shift and larger budgets. An ordinary library with exactly the same content matches v2. The diagnostic idea is defeated by a simpler paired-measurement baseline.
\section*{What the economics say}
The primary, explicitly simulated 30-day enterprise earns mean operating profit of USD 46,781 using competent Beta delivery under assumed demand and prices. The optional policies reject retention and Gym spending; assessing the candidate still costs money and capacity. A predeclared 40-call fitting-cap scenario gives the controlled Gym pilot a conditional USD 4,439 increment, but that is not the unrestricted primary result and is not earned revenue.
\textbf{Actual customer collections are USD 0.} Human scopes, arrivals, trust, simulator tariffs and token volumes are assumptions. Published external scientific-software rates anchor the price scenarios; they do not establish demand.
\newpage
\section*{What to offer first}
Offer a bounded scientific-software qualification engagement. Obtain a customer's real simulator and freeze the useful outcome, query cost, latency, acceptance and customer effort. Price against matched human delivery and buyer value. Compare the best conventional workflow, the retained representation and direct workarounds. Charge final checking and correction. Preserve the option to deliver profitably with no skill retention.
\section*{The next worthwhile experiment}
Target a compound outcome whose verification requires many conditions and where repeated direct trial becomes expensive. Establish an observable way to identify compatible simulator families; the research's hidden family labels cannot route live work. Test the actual modern frontier tool-use configuration with the same context, code, tools and correction budget. Do not make model training compulsory.
\section*{A cautious investment policy can be successful}
The real development-evidence admission assay rejects v2 in both tested envelopes after uncertainty and lifecycle costs. The protected research transfer passes 29 conformance checks with fixture identities and real bytes; it does not override that rejection. Production scientific execution remains outside the current capsule scope. Existing Jobs validation, governance and settlement are preserved.
\section*{What this edition does not establish}
It does not establish live customer demand, live frontier-model superiority, live ENS authentication, graph-specific value, specialist ASI, autonomous business invention or sustained self-acceleration. Software learning and fresh synthetic outcomes were executed; the market was simulated. The robust offering was researcher proposed from the initial development finding and confirmed on separate fresh seeds.
\textbf{Research is not free.} The compound-offering campaign used 617,544 query-equivalent evaluations. At the hypothetical USD 0.10 tariff, those alone would cost USD 61,754.40. Operating contributions exclude that separately disclosed common research burden; whole-study profitability is not established. Actual observed paid API cash expense was zero, while complete engineering cost remains unknown.
\section*{Inspect the mechanism}
The full paper, LaTeX project, actual learned artifacts, raw results, frozen policies, accounting corrections, integration receipts, source audit and English/French demonstration are included in the research companion. The before/after resource-reservation defect is preserved; corrected economics reserve the whole declared obligation before accessing realized outcomes.
\vfill
\textbf{FIND YOUR ALPHA. BUILD YOUR SUCCESSOR $\Omega$.}\par
AI assistance: source retrieval, implementation, execution, internal review, analysis and drafting. Researcher-authored methods and automatic updates are distinguished throughout.
\end{document}
"""
    )
    (HERE / "executive-brief.tex").write_text(brief)
    evidence = (
        preamble.replace("[11pt,letterpaper]", "[10pt,letterpaper]")
        + r"""{\Huge\bfseries Evidence Companion}\par
\textbf{When Capability Creates Opportunity}\par
Vincent Boucher\quad President of MONTREAL.AI\par
27 October 2026
\section*{Evidence classification}
\begin{longtable}{p{0.18\linewidth}p{0.73\linewidth}}\toprule
Observed & Executed synthetic oracle calls, automatic sparse fits, artifact updates, fresh model/plan outcomes, transfer of actual bytes, native interface checks and resource-accounting identities.\\
Sourced & Official current model references and prices; external scientific-software and experiment-design provider list rates; pinned prior studies and foundation materials.\\
Assumed & Customer scopes and hours, arrivals, trust, willingness to pay, simulator tariffs and latency, token counts, operational overhead, collection delays, reserves and maintenance.\\
Simulated & Enterprise jobs, invoices, collections, profit, capacity allocation, counterparties and authority fixtures.\\
Unknown & Real willingness to pay, realized complete research/engineering cost, API entitlement and throughput, physical validity, live execution/authentication and sustained compounding.\\\bottomrule\end{longtable}
\section*{Core study inventory}
"""
    )
    evidence += table(
        ["Item", "Scope"],
        [
            ["Primary technical confirmation", "48 tasks; 1,728 method/budget rows"],
            ["Compound-offering confirmation", "48 different tasks; 1,728 rows"],
            ["Learning", "1 origin + 10 Gym jobs; v1 9 terms, v2 21"],
            ["Economic confirmation", "11,520 histories: 30 scenarios x 6 policies x 64 seeds"],
            ["Integration", "29 unchanged upstream files; 29 directed controls"],
            ["Customer revenue", "USD 0 observed"],
        ],
        "p{0.38\\linewidth}p{0.53\\linewidth}",
    )
    evidence += r"""
\section*{Claim-to-evidence map}
\begin{longtable}{p{0.38\linewidth}p{0.53\linewidth}}\toprule
Claim & Companion evidence\\\midrule
Learning and source freeze & \texttt{technical/results/FREEZE.json}; \texttt{learning\_ledger.json}; \texttt{technical/artifacts/}\\
Fresh primary outcomes & \texttt{technical/results/confirmation\_rows.json}, CSV and paired analysis\\
New robust offering & \texttt{technical/robust/PROTOCOL.json}; PREDECLARED, FREEZE and fresh results\\
Conditional economics & \texttt{economics/scenario.json}; \texttt{policy\_freeze.json}; \texttt{results/enterprise\_runs.csv} and summary\\
Auditable event histories & Six complete representative seed-0 ledgers, matched events and deterministic replay for every retained per-seed outcome\\
Admission / controlled transfer & \texttt{integration/results/development-admission-v1/}; conformance and recipient replay receipts\\
Source history & \texttt{source\_audit.md}; \texttt{integration/source\_manifest.json}; \texttt{sources/source\_dossier.md}\\
Independent internal review & \texttt{validation/independent\_review.md} and JSON; resource reservation probes\\\bottomrule\end{longtable}
\section*{What was corrected and preserved}
The original economic implementation accessed the realized stopping cost of a fresh direct search before deciding whether the job fit remaining cash and capacity. Boundary probes reproduced the error. Corrected code reserves the declared maximum first, accesses protected outcomes only after commitment and releases unused resources afterward. Original source and original policy freeze remain in the history; development-selected prices, routes and decisions were not retuned on confirmation. The final results explicitly report that execution uses an amended source.

The original protocol's portfolio prose mentioned lowest-cost/global-regret quality even though the operational acceptance required a feasible checked plan. A separate deliverable sentence over-specified a response model for direct-search delivery. Companion clarifications retain the original text and specify the actual implemented contract. The paper never attributes optimality or an accurate model to the direct baseline.

\section*{Research costs and validation}
The primary model service charges 384 extra acceptance labels per customer delivery. The simple-plan service includes its final observation inside the displayed budget. The compound mission includes sixteen final observations inside its whole budget. Protected model and full-menu audits are research work, counted separately and shared across comparator scoring where applicable. The primary confirmation uses 44,544 unique oracle-equivalent audit observations, worth USD 4,454.40 only under the assumed USD 0.10 tariff. The separate compound-offering campaign uses 617,544 query-equivalent evaluations, including development, confirmation, full-menu audits and the illustrative replay. At the same hypothetical tariff, its common research expense alone is USD 61,754.40. Its operating sensitivity rows exclude this disclosed research burden; they are not whole-study profit. Actual observed paid API cash expense is zero. CPU time and unmeasured engineering monetary costs remain distinct. Whole-study payback is not established.

\section*{Statistical interpretation}
The main and robust experiments each contain 24 compatible, 12 partially shifted and 12 novel-family tasks. Bootstrap or binomial uncertainty describes this generator, not market truth. A post-hoc best-of-conventional envelope is a generous diagnostic and cannot be dispatched without additional information. The real policies use development outcomes only. No isolated positive case establishes high-reliability operation; infeasible menus and failed transfers remain in their original denominators.

\section*{Access and authority}
The conformance lane uses artificial positive monetary evidence to exercise rights and revocation branches. The actual candidate's development-evidence gate rejects it, and corresponding retrieval attempts remain denied. A separately authorized research replay transports actual bytes and checks a fresh task. Fixture identities are not live ENS resolution. Revocation blocks new mediated access; it cannot erase copies already received. Production scientific scope remains unsupported, and Jobs/governance/settlement authority is unchanged.

\section*{Reproduction and publication}
Start with the companion README and preserve the original evidence before rerunning. The numerical pipeline requires Python with NumPy, SciPy and scikit-learn; charts use Matplotlib; integration uses Node and the pinned vendored interfaces. LaTeX rebuild commands and environment versions accompany the source. Browser evidence is self-contained and bilingual. Full repository CI, flagship Pages deployment and production commissioning remain separate from this experimental research edition.

\textbf{Author and assistance.} Vincent Boucher, President of MONTREAL.AI. AI assistants performed research, code construction, execution, internal review, analysis and drafting. Internal review is not external scientific replication. New source is Apache-2.0; original vendored licenses are preserved.
\end{document}
"""
    evidence = re.sub(r"\\texttt\{([^}]+)\}", lambda m: r"\path{" + m.group(1).replace(r"\_", "_") + "}", evidence)
    evidence = evidence.replace(
        r"\section*{Statistical interpretation}",
        r"\input{generated/research-resources.tex}" + "\n" + r"\section*{Statistical interpretation}",
    )
    (HERE / "evidence-companion.tex").write_text(evidence)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()
