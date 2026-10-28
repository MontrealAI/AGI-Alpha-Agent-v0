# SPDX-License-Identifier: Apache-2.0
"""Insert audited evidence into the complete manuscript without changing frozen science."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "publication"
summary = json.loads((ROOT / "economics/confirmation/summary.json").read_text())
reference = summary["reference"]
tech = json.loads(
    (ROOT / "verification/technical_confirmation_review.json").read_text()
)
circuit = json.loads(
    (ROOT / "verification/circuit_confirmation_v1/summary.json").read_text()
)


def dollars(x):
    return f"USD{x / 100:,.2f}"


labels = {
    "reference": "Reference",
    "low_demand": "Lower demand",
    "same_ai_price_war": "Same-AI price war",
    "supplier_shock": "Supplier shock",
    "payment_deviation": "Strategic payment deviation",
    "rational_buyers": "Rational buyers",
    "high_need": "Higher need",
    "correlated_failure": "Correlated failure",
    "strongest_free": "Strongest free alternative",
    "low_labor": "Lower operating labor",
}
rows = [
    "| Scenario | Mean full-project profit | Mean operating contribution | Accepted packs | Loss histories |",
    "|---|---:|---:|---:|---:|",
]
for name, label in labels.items():
    s = summary[name]
    rows.append(
        f"| {label} | {dollars(s['mean_profit_cents'])} | {dollars(s['mean_operating_contribution_cents'])} | {s['mean_accepted']:.2f} | 128/128 |"
    )
values = {
    "NUMERICAL_RESULTS": f"""All **32 development circuit exports** passed both independent routes under the predeclared absolute tolerance of $10^{{-6}}$. The fresh campaign then executed **{circuit["cases"]} unique circuits** across the 24 constructive fresh cases; all passed, while the twelve proper refusal cases emitted no circuits. Maximum fresh disagreement was $1.80\\times10^{{-14}}$ for the independent ODE against the primary prediction and $8.59\\times10^{{-9}}$ for ngspice against that prediction. The fresh circuit batch took {circuit["elapsed_seconds"]:.3f} seconds. These measurements exclude obtaining dependencies, writing the instrument and reviewing its scientific scope.""",
    "CONFIRMATION_RESULTS": f"""The final source freeze is `e1ccee55bf1269fd3fc0932538782a2eaaa1eeda31cf06880435708fd74e33d7`, binding 22 scientific, checking and economic files. Fresh confirmation passed **42 of 42 cases**: 24 binary cases, 12 six-hypothesis successor cases and six malformed-input controls. The binary cases produced twelve valid constructions and twelve required refusals. All twelve successor portfolios met their specified no-outage, one-experiment-outage or one-terminal-access-outage requirement, and independent enumeration matched feasibility and minimum cost. All 22 frozen file hashes were unchanged afterward.

The 36 actual primary CLI invocations took {tech["cli_seconds_total"]:.2f} seconds in total; their independent finite checks took {tech["independent_seconds_total"]:.2f} seconds. These are local computational measurements, not a full-project productivity ratio. Fourteen pre-freeze analytic and input/export controls also passed. Strict source lint passed. The strict typing attempt remained unqualified because SciPy type stubs were absent; full repository coverage, platform qualification and release checks were not performed in this isolated study.""",
    "SUCCESSOR_RESULTS": f"""The twelve fresh successor tasks all produced independently minimum-cost portfolios, with total declared costs ranging from {min(tech["successor_costs"])} to {max(tech["successor_costs"])} units. An isolated ordinary-library copy containing {tech["ordinary_library_file_count"]} source and predecessor artifact files ({tech["ordinary_library_bytes"]:,} bytes) reproduced every complete successor result exactly. Copying took {tech["ordinary_library_copy_seconds"]:.3f} seconds and the twelve library CLI invocations took {tech["ordinary_library_seconds_total"]:.2f} seconds. Source discovery, semantic integration and long-run upkeep were not empirically timed; the enterprise model charges separate effort estimates. No unplanned user intervention was needed during these frozen deterministic runs, but expert scientific judgment was used to select the family, interpret the obstruction and repair development errors.""",
    "JOINT_RESULTS": """A supplemental shared-commissioning calculation considers three consenting sponsors at an assumed USD4,000 each. Shared integration and coordination cost USD2,250; per-sponsor validation costs USD750, giving USD4,500 for the cohort before the common USD36,200 research investment. Independent 70% consent would produce only 34.3% unanimous participation; a common refusal factor makes it worse. Failed cohorts refund restricted pledges and retain their coordination expense.

At these assumptions, twelve committed sponsors cover the simplified subtotal for shared research, integration, coordination and validation. That is a necessary arithmetic threshold, not a complete enterprise profit result: acquisition, financing, support, warranty and exit would raise it. No twelve sponsors have been identified. The same conventional arrangement receives identical rights and costs and ties by assumption. Open-source availability permits a waiting or free-riding outcome, so technical complementarity does not guarantee coordinated demand.""",
    "ECONOMIC_METHODS": """The original grid tested prices of USD6,000, USD8,000 and USD10,000, with two deposit fractions and two capacities. Because those prices could make the test unnecessarily unfavorable against internal and free options, one bounded redesign added USD3,000, USD4,500 and USD6,000. The two grids contain 24 policy entries and 20 unique parameter combinations. Both were scored under the corrected common model on twelve development seeds and six disclosed design-weighted scenarios; the original source and results remain archived. Demand and buyer values were not increased to rescue the offer.

The selected attempted offer quotes **USD4,500**, holds a **50% restricted deposit**, permits **two new contracts per month**, and applies the frozen stop rule from month five. Its policy and all assumptions were fixed before confirmation. Confirmation ran 128 fresh histories in each of ten scenarios, plus 128 same-seed conventional counterparts and 128 stop-after-research counterparts. All **1,536 complete trajectories** are retained, with **385,682 journal events** and **1,828 contracts**. Separate reconstruction checked every account and 228 aggregate statistics. The supplementary raw reference records were saved after their original summaries, using unchanged frozen functions and the identical seed bank; their summaries matched exactly.""",
    "ECONOMIC_RESULTS": "\n".join(rows)
    + f"""

The reference mean full-project return is **{dollars(reference["mean_profit_cents"])}**, including **{dollars(reference["mean_operating_contribution_cents"])}** operating contribution. Mean recognized revenue is {dollars(reference["mean_revenue_cents"])}, gross collections are {dollars(reference["mean_collections_cents"])}, and total project cost is {dollars(reference["mean_total_project_cost_cents"])}. Collections and revenue differ because deposits, refunds and bad debts have different timing and recognition. Every terminal deposit, receivable and support/refund obligation is zero after runoff.

The reference fifth-to-ninety-fifth world percentile range is **{dollars(reference["profit_p05_cents"])} to {dollars(reference["profit_p95_cents"])}**. Its mean's Monte Carlo standard error is {dollars(reference["profit_sampling_se_cents"])}; this is sampling precision conditional on the model. The estimated conditional loss rate is 100% (128/128) in each scenario, not a measured probability about a real market. Mean reference peak funding need is **{dollars(reference["mean_cash_requirement_cents"])}**; the largest observed requirement across all scenarios is **USD70,241.74**. The worst observed full-project loss is **USD68,654.39**.

The reference world averages 70.75 leads, 38.55 qualified prospects, 1.91 negotiations, 1.70 signed contracts and 1.62 accepted packs. It averages 0.336 correction events, 0.086 failed deliveries and 0.141 withheld invoices. Modeled human effort is 512.75 hours, including 304 startup hours; operational verification accounts for 7.48 hours. All reference histories stop new sales in month five. No renewal or successor investment occurs. A modeled increase in leads can worsen losses when paid qualification grows faster than accepted work.

An optimistic necessary break-even calculation at the selected USD4,500 price requires about **39.5 signed contracts** over a full year, above the policy's 24-contract capacity. Excluding sunk research still requires about **21.5 contracts** under that calculation's favorable exclusions. At full capacity, its price floor is approximately **USD5,890.08** before discounts, bad debt, collection costs and other adverse factors. A price floor is not evidence that buyers will pay it. The stronger free alternative and deterministic rational-choice scenarios obtain zero sales.

Stopping after the completed research retains its cost and the archive/exit cost: **USD−36,950**. It avoids a further **USD16,237.20** of expected loss relative to the reference attempt. Doing nothing before commissioning any research would have a different, zero-cost baseline. The current decision does not erase the completed study's estimated cost.""",
    "EXPANSION_RESULTS": """The frozen enterprise requires at least twelve accepted deliveries, two renewals, USD12,000 operating contribution and sufficient usable cash before considering a USD4,000 successor experiment. It also requires the lower-bound expected incremental benefit to at least cover the experiment cost. The conservative assumed probability/value pair, 0.2 and USD8,000, gives only USD1,600 expected benefit, so it fails that gate. Neither the probabilities nor the conditional values are empirical findings. A later USD20,000 integration stage stays separate and unfunded. No speculative future value is counted in current profit, and no simulated trajectory funds a successor experiment.

An appropriate redesign would first establish whether an external team's decision actually changes when the hidden topology is known. A subsequent fixture trial would need independently specified nonuniform-component bounds, initialization and readout calibration, incomplete-hypothesis controls and comparison with an unrestricted specialist. Until those conditions are met, the narrow service should not finance a larger mission through assumed sales.""",
    "SCALE_RESULTS": """At an assumed USD2,500 net incremental value per accepted pack, the threshold is 400,000 useful packs over ten years: 40,000 per year and 10,000 active beneficiaries buying four per year. At the current assumed capacity of 24 packs per team per year, that requires about 1,667 delivery teams and 160,000 verification hours annually before acquisition and exceptions. At USD500 net value, the required volume is five times larger; at USD10,000 it is one quarter as large.

No reachable population of 10,000 beneficiaries, relevant adoption rate or incremental value of USD2,500 has been established. The arithmetic is therefore a falsifiable scale requirement, not a forecast or a billion-dollar business claim. The present narrow graph family does not justify that reach. A broader qualified instrument, materially lower total review burden, repeatable customer acquisition and demonstrated beneficiary value would all be necessary.""",
    "DECISION_RESULTS": """**Stop the tested narrow commercial offering; retain the construction and redesign the application bridge before any expansion.** The demonstrated result is a model-family change in scientific answerability, supported by independent finite checks and actual circuit-software execution. The complete conditional enterprise model favors not launching the selected offer after the completed research. The strongest free alternative makes the commercially relevant problem especially clear.

The campaign has therefore not established a commercially consequential physical flagship. It also does not reject the broader possibility of intelligence constructing useful instruments. It identifies the specific next burden of proof: a beneficiary problem that needs the new observable, a practical permitted realization, and delivery economics that survive equally equipped alternatives. A new theorem or exclusive algorithm is unnecessary; evidence that this combination changes a real productive activity is necessary.""",
}
s = (
    (P / "manuscript.md")
    .read_text()
    .replace(
        "Two nonisomorphic diffusion networks",
        "Two nonisomorphic synthetic diffusion-network models",
    )
    .replace("a finite stochastic game", "a finite-horizon stochastic game")
)
for key, value in values.items():
    s = s.replace("{{" + key + "}}", value)
assert "{{" not in s
(P / "PAPER.md").write_text(s)
(P / "result_insertions.json").write_text(json.dumps(values, indent=2) + "\n")
print("complete manuscript words", len(s.split()))
