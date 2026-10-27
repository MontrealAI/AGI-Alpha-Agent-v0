#!/usr/bin/env python3
"""Render already-preserved economics outputs; never rerun selection or campaigns."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE / "results"
cfg = json.loads((HERE / "config.json").read_text())
policy = json.loads((HERE / "policy_frozen.json").read_text())
confirmation = json.loads((R / "confirmation.json").read_text())["rows"]
by_name = {r["scenario"]: r for r in confirmation}
explore = json.loads((R / "exploratory.json").read_text())["rows"]


def csv_rows(name):
    with (R / name).open() as f:
        return list(csv.DictReader(f))


def money(x):
    return f"${float(x):,.2f}"


def number(x):
    return f"{float(x):,.2f}"


def pct(x):
    return f"{100 * float(x):.1f}%"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + ["| " + " | ".join(map(str, row)) + " |" for row in rows])


base = by_name["baseline"]
primary = [by_name[k] for k in ["low", "baseline", "high"]]
robust = csv_rows("robust_profitable_region.csv")
valid = [r for r in robust if r["robust_over_declared_grid"] == "True"]
sections = [
    "# Final conditional economics results — v2.1\n",
    f"The frozen exploratory quote is **{money(policy['price'])} per useful accepted original-query package**. It is a scenario-selected quote, not an observed service-market price. The exploratory launch gate is **{policy['exploratory_launch_recommendation']}**. Final fresh confirmation gives baseline mean 90-day operating profit **{money(base['operating_profit'])}**, with modeled operating-loss frequency **{pct(base['loss_probability_modeled'])}**. The robust profitable region contains **{len(valid)} of {len(robust)} declared cells**. No live launch is justified by these unvalidated assumptions.\n",
    "**Actual collections and actual revenue: USD 0. Actual authoring/hosted-model costs: unknown.** All amounts below are modeled USD. These simulations do not calibrate real mission success, willingness to pay, or scientific source coverage. E, U, and the identical-content ordinary library have identical operating economics by the primary attribution-null assumption.\n",
    "## Fresh confirmation: 90-day campaigns\n",
    table(["Scenario", "Origins", "Willing", "Contracts", "Useful accepted by day 90", "Earned revenue", "Operating profit", "Loss frequency"],
          [[r["scenario"], number(r["origins"]), number(r["willing_origins"]), number(r["contracts"]), number(r["useful_accepted_deliveries"]), money(r["earned_modeled_revenue"]), money(r["operating_profit"]), pct(r["loss_probability_modeled"])] for r in primary]),
    "\nEach row averages 600 campaigns under a fresh seed. Finite horizon and open work matter: accepted deliveries by day 90 are not the assumed eventual technical-success probability. High-case capacity rejections average " + number(by_name["high"]["capacity_rejections"]) + "; open contracts at day 90 average " + number(by_name["high"]["open_contracts"]) + ".\n",
    f"The baseline mean-profit Monte Carlo interval is {money(base['profit_mean_ci95_low'])} to {money(base['profit_mean_ci95_high'])}; its 10th–90th percentile campaign outcome is {money(base['profit_p10'])} to {money(base['profit_p90'])}. These describe simulation noise/outcomes under fixed assumptions, not empirical confidence in a business.\n",
    "## Contribution reconciles to operating profit\n",
    table(["Scenario", "Net earned revenue", "Bad debt", "Direct variable A cost", "Contribution", "Fixed cost incl. overhead", "Finance", "Operating profit"],
          [[r["scenario"], money(r["earned_modeled_revenue"]), money(r["bad_debt"]), money(r["direct_variable_A_cost"]), money(r["contribution_before_fixed_and_finance"]), money(r["fixed_campaign_cost_including_overhead"]), money(r["financing_cost"]), money(r["operating_profit"])] for r in primary]),
    "\nDirect variable A costs include channel acquisition, all-origin intake, failed work, domain construction/validation, bounded rework, compute, delivery/refusal, support, fees, and variable overhead. Fixed compensation and its overhead are deducted once. Refunds are revenue reversals or returned deposit liabilities, not duplicate costs. Sunk development C and optional retention B remain separate.\n",
    "## Expected amount per originating opportunity\n",
    table(["Scenario", "Contract probability", "Accepted by day 90/origin", "Gross cash collected", "Earned revenue", "All A expense", "Bad debt + finance", "Operating profit"],
          [[r["scenario"], pct(r["contracts"] / r["origins"]), pct(r["useful_accepted_deliveries"] / r["origins"]), money(r["collected_modeled_cash"] / r["origins"]), money(r["earned_modeled_revenue"] / r["origins"]), money(r["operating_expense_before_finance"] / r["origins"]), money((r["bad_debt"] + r["financing_cost"]) / r["origins"]), money(r["operating_profit"] / r["origins"])] for r in primary]),
    "\nThe primary cash channel assumption is $5 per origin. Non-buyers and unsupported sources still incur it, plus intake labor. Origination volumes are explicit opportunity-pool assumptions, not guaranteed demand.\n",
    "## Cash, obligations, reserves and free funds at day 90\n",
    table(["Item", "Low", "Baseline", "High"],
          [[label] + [money(r[key]) for r in primary] for key, label in [
              ("collected_modeled_cash", "Gross customer cash collected"),
              ("cash_refunds", "Cash refunded"),
              ("net_customer_cash_collected", "Net customer cash collected"),
              ("earned_modeled_revenue", "Earned modeled revenue"),
              ("cash_at_day90", "Cash on hand, including owner funding"),
              ("restricted_deposits", "Unaccepted/refundable deposits"),
              ("refund_cash_reserve", "Full fee reserve during refund windows"),
              ("accrued_payables", "Accrued unpaid costs"),
              ("pending_payment_fees_subset_of_payables", "Pending payment fees, subset of payables"),
              ("completion_reserve", "Remaining maximum completion budget"),
              ("conditional_fee_reserve", "Additional conditional fee buffer"),
              ("debt_at_day90", "Outstanding borrowing"),
              ("free_funds", "Free funds after all listed restrictions and debt")]]),
    "\nPending payment fees are already in payables and are not subtracted twice. Free funds include remaining initial owner capital of $5,000; they are not profit. Full refundable deposits and fee reserves cannot finance unrestricted spending. The model accrues accepted-but-unsettled collection fees and imminent refusal-refund fees, and reserves potential additional fees.\n",
    f"Baseline 95th-percentile temporary borrowing requirement is {money(base['peak_debt_p95'])}; modeled credit-limit breach frequency is {pct(base['liquidity_limit_breach'])}. Borrowing is costed at an assumed 12% APR. The first confirmation campaign's unselected full cash ledger is preserved; all campaign cash identities are checked.\n",
    "## Outside-option and acquisition stress cases\n",
    table(["Case", "Cash acquisition/origin", "Contracts", "Earned revenue", "Operating profit", "Loss frequency"],
          [[name, money(0 if name == "warm_inbound_acquisition_zero" else 15 if name == "acquisition_15_per_origin" else 50 if name == "acquisition_50_per_origin" else 5), number(by_name[name]["contracts"]), money(by_name[name]["earned_modeled_revenue"]), money(by_name[name]["operating_profit"]), pct(by_name[name]["loss_probability_modeled"])] for name in ["warm_inbound_acquisition_zero", "baseline", "acquisition_15_per_origin", "acquisition_50_per_origin", "competent_human_fast", "no_buyer_advantage"]]),
    "\nThe competent-human-fast case uses 10 median additional analysis minutes and preserves the source burden. The no-buyer-advantage case supplies the buyer with an equivalent free answer. These are distinct from E=U: a zero E-versus-U gain does not itself imply zero outsourcing demand.\n",
    "## Preserved price exploration\n",
    table(["Success fee", "Expected contracts", "Expected accepted deliveries", "Mean operating profit", "Modeled loss frequency"],
          [[money(r["price"]), number(r["contracts"]), number(r["useful_accepted_deliveries"]), money(r["operating_profit"]), pct(r["loss_probability_modeled"])] for r in explore]),
    "\nThe seven quotes were compared on 200 baseline campaigns with a common exploration seed. The best quote was frozen before the untouched confirmation seed was used. The launch gate rejects a negative best mean; the quote remains available solely for the conditional comparison. No confirmation outcome changed the price.\n",
    "## Robust profitable region\n",
    table(["Source construction + validation hours", "Outside extra minutes", "Worst-corner mean profit", "Worst lower MC mean bound", "Robust in declared grid?"],
          [[number(r["source_hours"]), number(r["outside_additional_minutes"]), money(r["min_corner_mean_profit"]), money(r["min_corner_profit_mean_ci95_low"]), r["robust_over_declared_grid"]] for r in robust]),
    "\nEvery cell includes baseline, lower source admissibility/decisiveness, higher refunds/defaults, lower outcome value, and a combined adverse corner at the frozen quote. Every corner is retained. An empty region means the stated grid supplies no robust-profit claim; widening or repricing it after confirmation would be a new exploratory study.\n",
    "## Buyer break-even avoided minutes\n",
    "The buyer comparison retains q_H for the human alternative and separately reduces q_offer for the provider's budget-exhaustion risk. At median complexity, the required extra human minutes depend on source burden and outcome value through `(q_H − q_offer) × value`. These are participation thresholds, not measured savings, and supplier profit must independently pass.\n",
    table(["Source hours", "Outcome value", "q_offer", "q_H", "Extra human minutes needed", "Minimum outcome value vs doing nothing"],
          [[number(r["source_hours_same_for_buyer_and_supplier"]), money(r["assumed_outcome_value"]), f"{float(r['assumed_q_offer']):.4f}", f"{float(r['assumed_q_human']):.4f}", number(r["buyer_outside_additional_minutes_needed_at_median_complexity"]), money(r["minimum_decisive_outcome_value_for_offer_vs_do_nothing"])] for r in csv_rows("buyer_break_even_minutes.csv")]),
    "\nThe table assumes zero queue wait and a 10-day quoted turnaround; the campaign uses each actual quoted wait plus turnaround. Higher source effort can make outsourcing attractive while simultaneously destroying supplier profitability.\n",
    "## Optional retention B: unknown gain can reject it\n",
    table(["Assumed fresh uses", "Avoidable minutes/use", "Modeled net B", "Break-even minutes/use", "Reject?"],
          [[r["assumed_fresh_uses"], r["assumed_avoidable_minutes_per_use"], money(r["modeled_net_B"]), number(r["break_even_minutes"]), r["reject_retention"]] for r in csv_rows("optional_retention_B.csv")]),
    "\nNo avoidable minutes were measured. At zero gain every retention option loses money. Identical-content ordinary-library parity is zero incremental gain before special packaging costs; the assumed generic reuse benefit does not establish a special memory mechanism. B is not added to primary campaign profit.\n",
    "## Human-led development and sunk C\n",
    table(["Scope", "Assumed hours", "Gross wage cost", "Employer compensation", "Internal cost incl. assumed overhead"],
          [[r["scope"], r["hours"], money(r["gross_wage_cost"]), money(r["employer_compensation_cost"]), money(r["internal_cost_with_assumed_overhead"])] for r in csv_rows("human_development_scope_comparison.csv")]),
    "\nThe 30/80/180-hour finite demonstrator covers small exact code, an independent oracle, tests and documentation. It does not certify historical sources. The 250/700/1,600-hour deployment includes source-family and admissibility work, representative archives and operational validation. These are scoped planning assumptions, not timed human results or vendor quotes. Existing methods may reduce the work. Neither comparator is used as customer value or price.\n",
    table(["Sunk C", "Low first-campaign profit", "Baseline first-campaign profit", "High first-campaign profit"],
          [[money(c)] + [money(r["operating_profit"] - c) for r in primary] for c in cfg["development_sunk_cost_sensitivity"]]),
    "\n## Corrections and evidence boundary\n",
    "1. The initial scheduling look-ahead defect was corrected before the first confirmation; full old code, policy and outcomes remain in `results_superseded_scheduling_v1/`.\n2. V1 confirmation completed, but its zero-event formatter failed. Raw results and the reporting-only completion are preserved in `versions/v1_before_acquisition/`.\n3. Independent audit identified missing acquisition cash, quoted queue finance, pending fees and bounded rework. V1's +$466.82 baseline was incomplete and was not relabeled as a full-cost result. V2 used new seeds.\n4. Before v2 confirmation, independent audit corrected the provider-specific budget failure being applied to the human comparator. That paired exploratory result is preserved in `versions/v2_before_outside_option_correction/`; final v2.1 confirmation remained untouched until its freeze.\n",
    "The retained failures and adverse scenarios limit the conclusion. This is a transparent cost-and-participation construction for a conditional service; it establishes neither a market nor a causal expert/agent improvement. A source-verified pilot, measured customer alternative, channel cost, and actual paid acceptance would be required to replace the assumptions.\n"
]

output = HERE / "RESULTS.md"
if output.exists():
    raise RuntimeError("Refusing to overwrite preserved RESULTS.md")
output.write_text("\n".join(sections) + "\n")
print(json.dumps({"report": str(output), "baseline_profit": base["operating_profit"],
                  "loss_frequency": base["loss_probability_modeled"], "robust_cells": len(valid)}))
