#!/usr/bin/env python3
"""Reproduce the negative-edition research cost scenarios using only stdlib.

No market revenue, success rate, actual AI bill, or profit is estimated here.
Run: python3 model.py
Inputs/outputs are adjacent to this script; no network or external mutations.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS = ("low", "central", "high")

def money(value):
    return round(value, 2)

def compute(config):
    count = config["edition"]["serious_candidates"]
    hc = config["human_comparator"]
    human = {}
    technical_loaded_central = None
    for case in SCENARIOS:
        details = []
        raw_wages = 0.0
        hours_total = 0.0
        for role, spec in hc["roles"].items():
            hours = count * spec["hours_per_candidate"][case] + spec["fixed_hours"][case]
            wage_rate = spec["annual_wage_anchor_usd"] / hc["annual_hour_divisor_assumed"] * spec["wage_multiplier"][case]
            wages = hours * wage_rate
            benefits = wages * hc["benefits_rate_on_wages"][case]
            overhead = (wages + benefits) * hc["overhead_rate_on_compensation"][case]
            loaded_rate = wage_rate * (1 + hc["benefits_rate_on_wages"][case]) * (1 + hc["overhead_rate_on_compensation"][case])
            details.append({"role": role, "label": spec["label"], "hours": hours,
                            "base_wage_per_hour_usd": money(wage_rate),
                            "base_wages_usd": money(wages), "benefits_usd": money(benefits),
                            "overhead_usd": money(overhead), "loaded_labor_usd": money(wages + benefits + overhead),
                            "loaded_rate_per_hour_usd": money(loaded_rate),
                            "evidence_label": "assumed role allocation/rate; source-anchored, not observed work"})
            raw_wages += wages
            hours_total += hours
            if case == "central" and role == "technical":
                technical_loaded_central = loaded_rate
        benefits = raw_wages * hc["benefits_rate_on_wages"][case]
        compensation = raw_wages + benefits
        overhead = compensation * hc["overhead_rate_on_compensation"][case]
        tools = hc["tools_allocation_usd"][case]
        human[case] = {"person_hours": hours_total, "roles": details,
                       "base_wages_usd": money(raw_wages), "benefits_usd": money(benefits),
                       "total_compensation_usd": money(compensation), "overhead_usd": money(overhead),
                       "tools_allocation_usd": tools, "total_cost_usd": money(compensation + overhead + tools)}
    ap = config["automated_planning"]
    automated = {}
    for case, spec in ap["scenarios"].items():
        input_cost = spec["assumed_input_tokens"] / 1_000_000 * ap["input_usd_per_million"]
        output_cost = spec["assumed_output_tokens"] / 1_000_000 * ap["output_usd_per_million"]
        total = input_cost + output_cost + spec["assumed_tool_allowance_usd"] + spec["assumed_execution_storage_allowance_usd"]
        automated[case] = {**spec, "input_token_cost_usd": money(input_cost),
                           "output_token_cost_usd": money(output_cost), "modeled_inference_usd": money(input_cost + output_cost),
                           "mandatory_human_review_usd": 0, "mandatory_onboarding_usd": 0,
                           "planning_total_usd": money(total), "actual_billing_usd": None,
                           "evidence_label": "assumption-only scenario, not a receipt or estimated actual usage"}
    optional = {}
    for case, hours in config["optional_specialist_review"]["hour_cases"].items():
        cost = hours * technical_loaded_central
        optional[case] = {"assumed_hours": hours, "loaded_hourly_rate_usd": money(technical_loaded_central),
                          "optional_research_cost_usd": money(cost),
                          "central_automated_plus_optional_usd": money(automated["central"]["planning_total_usd"] + cost),
                          "current_charged_usd": 0, "mandatory": False,
                          "evidence_label": "prospective optional research budget, not observed expense"}
    voi = []
    C = config["next_research_voi"]["cost_cap_usd"]
    for item in config["next_research_voi"]["scenarios"]:
        p, V = item["assumed_p"], item["assumed_V_usd"]
        expected_benefit = p * V
        threshold = C / V if V > 0 else None
        voi.append({**item, "assumed_C_usd": C, "assumed_expected_benefit_usd": money(expected_benefit),
                    "assumed_expected_net_value_usd": money(expected_benefit - C),
                    "strict_probability_threshold_C_over_V": threshold,
                    "threshold_met_under_invented_assumptions": expected_benefit > C,
                    "no_positive_cost_pass_possible": V == 0,
                    "evidence_label": "invented decision scenario; not measured probability or venture forecast"})
    result = {
        "schema": "agialpha.negative-edition.economics.results.v1",
        "as_of_date": config["as_of_date"], "currency": config["currency"],
        "edition": config["edition"], "observed_financial_status": config["observed_financial_status"],
        "classification": config["classification"], "commercial_status": config["commercial_status"],
        "human_comparator_scenarios": human, "automated_planning_scenarios": automated,
        "optional_specialist_review_scenarios": optional, "next_research_voi_scenarios": voi,
        "cost_formulas": {
            "role_hours": "candidate_count * per_candidate_hours + fixed_hours",
            "role_wage_rate": "annual_wage_anchor / 2080 * assumed_seniority_multiplier",
            "human_total": "sum(role_hours * wage_rate) * (1 + benefits_rate) * (1 + overhead_rate) + tools",
            "automated_planning": "assumed_input_tokens / 1e6 * 10 + assumed_output_tokens / 1e6 * 50 + tool_allowance + execution_storage_allowance",
            "optional_review": "assumed_hours * central_loaded_technical_rate",
            "voi": "assumed_p * assumed_V - assumed_C; proceed only if positive and assumptions are defensible"},
        "claim_boundaries": [
            "Human numbers are task-scope planning estimates; no actual human comparison or outcome equivalence was tested.",
            "AI planning scenarios are not actual bills; actual total cost and profit remain unknown.",
            "No sale price or market demand is supplied because no offering was selected.",
            "All current exploratory unpaid work is Category C; no A paid jobs or qualified B investment.",
            "Human specialist review is optional future research expenditure, not a mandatory automation charge.",
            "VOI cases are invented thresholds, not profitable venture forecasts or estimates of actual success probability.",
            "No prior profit or customer results are carried into this edition.",
            "No robust profitable launch region has been established."],
        "source_ids": [s["id"] for s in config["sources"]],
        "rounding": "Compute at full float precision, round displayed money to cents. Rounded role components can differ from rounded totals by pennies."
    }
    assert result["commercial_status"]["selected_offering"] is None
    assert result["commercial_status"]["accepted_customer_outcomes"] == 0
    assert result["commercial_status"]["profit_usd"] is None
    assert result["observed_financial_status"]["actual_total_cost_usd"] is None
    assert result["classification"]["paid_job_A_count"] == 0
    assert result["classification"]["qualified_investment_B_count"] == 0
    assert all(automated[c]["mandatory_human_review_usd"] == 0 for c in SCENARIOS)
    assert [human[c]["person_hours"] for c in SCENARIOS] == [46, 84, 154]
    assert not voi[0]["threshold_met_under_invented_assumptions"]
    assert not voi[3]["threshold_met_under_invented_assumptions"]
    return result

def render_readme(config, result):
    lines = [
        "NEGATIVE RESEARCH EDITION: COST AND INVESTMENT RECORD",
        "As of " + config["as_of_date"] + " | USD | North American planning context",
        "",
        "RESULT AND OBSERVATIONS",
        "The scan closed with 12 serious candidates and no selected flagship. Accepted customer outcomes: 0.",
        "Observed customer collections: $0. Newly executed purchase transactions: 0 ($0 transaction value).",
        "Actual metered inference, tools, runtime/storage, human effort/review, total cost, and profit: UNKNOWN.",
        "No billing receipt or human-time ledger was available. No new purchase transaction is not the same as no cost.",
        "No prior profits or customer results are imported. No offering, sale price, or demand was established.",
        "No robust profitable launch region was established. This is a cost record, not a venture forecast.",
        "Current work: Category C exploratory unpaid work. Category A paid jobs: 0. Qualified Category B investments: 0.",
        "The 12 Category C entries are candidate assessments, not 12 jobs or delivered customer outcomes.",
        "",
        "HUMAN-LED TASK-SCOPE COMPARISON (ASSUMED; NO HUMAN TRIAL)",
        config["human_comparator"]["scope"],
        "U.S. BLS wage observations anchor a North American USD planning model; no continental wage survey is claimed.",
        "May 2025 annual median anchors: research scientists $140,300; developers $135,980; technical writers $90,390.",
        "Divide annual wages by an assumed 2,080 hours, then apply explicit seniority multipliers in config.json.",
        "These are base salary-equivalent wage rates, not consultant bills. No October 2026 inflation extrapolation.",
        "Central benefits/wages = $14.07 / $32.82 = 42.87%, from June 2026 private-industry compensation.",
        "Low/central/high benefits rates: 30% / 42.87% / 55%. Additional overhead: 10% / 20% / 35% of compensation.",
        "Overhead excludes separately listed tools and profit. Low/high burdens are assumptions, not BLS quantiles.",
        "Tools allocations: $25 / $100 / $300. Public access can avoid new fees; these are allocated resource scenarios.",
        "Low/central/high cases jointly vary staffing effort and rate assumptions; they are not confidence intervals.",
        "Person-hours are not elapsed time. Roles may be filled by the same person without overlapping hour entries.",
        "",
        "Hours per role = 12 * candidate-specific hours + fixed portfolio hours:",
        "Role                  Low             Central          High",
    ]
    for role, spec in config["human_comparator"]["roles"].items():
        cells = []
        for case in SCENARIOS:
            per, fixed = spec["hours_per_candidate"][case], spec["fixed_hours"][case]
            cells.append(f"12*{per:g}+{fixed:g}={12*per+fixed:g}h")
        lines.append(f"{role:20s}  {cells[0]:16s}{cells[1]:17s}{cells[2]}")
    lines += ["", "Role justifications:"]
    for spec in config["human_comparator"]["roles"].values():
        lines.append(spec["label"] + ": " + spec["justification"])
    lines += ["", "Costs: wages + benefits + overhead + tools (USD):"]
    for case in SCENARIOS:
        h = result["human_comparator_scenarios"][case]
        lines.append(f"{case:7s}: {h['person_hours']:g}h; ${h['base_wages_usd']:,.2f} + ${h['benefits_usd']:,.2f} + ${h['overhead_usd']:,.2f} + ${h['tools_allocation_usd']:,.2f} = ${h['total_cost_usd']:,.2f}")
    lines += [
        "",
        "AUTOMATED CONFIGURATION: SCENARIOS ONLY, ACTUAL BILL UNKNOWN",
        "Official GPT-6 Astra standard rates: $10 input / $50 output per million tokens [S_API].",
        config["automated_planning"]["pricing_assumptions"],
        "Token quantities and flat tool/runtime allocations below are invented planning allowances, not receipts.",
        "Mandatory human review: 0 hours/$0. Mandatory human onboarding: 0 hours/$0.",
        "This configuration imposes neither charge; actual unmetered owner effort remains unknown.",
    ]
    for case in SCENARIOS:
        a = result["automated_planning_scenarios"][case]
        lines.append(f"{case:7s}: {a['assumed_input_tokens']:,} input + {a['assumed_output_tokens']:,} output tokens -> inference ${a['modeled_inference_usd']:,.2f}; tools ${a['assumed_tool_allowance_usd']:,.2f}; execution/storage ${a['assumed_execution_storage_allowance_usd']:,.2f}; total ${a['planning_total_usd']:,.2f}.")
    lines += [
        "Do not infer observed AI savings or an actual human/AI cost ratio from these unrelated assumptions.",
        "",
        "OPTIONAL HUMAN SPECIALIST REVIEW (SEPARATE FUTURE RESEARCH ALLOCATION)",
        "Unperformed and unpurchased. Not an automation prerequisite and not a currently qualified Category B investment.",
        "Uses the central technical-role wage plus central benefits and overhead, without extra tools.",
    ]
    for case, o in result["optional_specialist_review_scenarios"].items():
        lines.append(f"{case}: {o['assumed_hours']} hours at ${o['loaded_hourly_rate_usd']:,.2f}/h = ${o['optional_research_cost_usd']:,.2f}; central automated scenario plus this optional review = ${o['central_automated_plus_optional_usd']:,.2f}.")
    lines += [
        "",
        "BOUNDED NEXT-RESEARCH VALUE OF INFORMATION: p*V > C",
        "C is an invented $1,500 total allocation cap for one further mechanism/falsifier investigation.",
        "p is the invented chance of a useful decision change, not an estimated chance of a successful venture.",
        "V is invented incremental decision value conditional on that change, net of downstream costs and before C.",
        "It can be avoided research waste; it is not sale revenue. No realized avoided cost is claimed.",
        "A positive example passes arithmetic only: it does not establish p, V, or investment qualification.",
    ]
    for v in result["next_research_voi_scenarios"]:
        threshold = "none: V=0" if v["strict_probability_threshold_C_over_V"] is None else f"p > {v['strict_probability_threshold_C_over_V']:.1%}"
        lines.append(f"{v['name']}: p={v['assumed_p']:.1%}, V=${v['assumed_V_usd']:,.0f}, C=${v['assumed_C_usd']:,.0f}; pV-C=${v['assumed_expected_net_value_usd']:,.0f}; threshold {threshold}; passes invented case={v['threshold_met_under_invented_assumptions']}.")
    lines += [
        "At V=0 no positive-cost research passes. At exact equality the strict decision rule does not pass.",
        "Actual p and V are unknown. No follow-on research commitment is authorized by this arithmetic.",
        "The downside is capped only if the cap is enforced. No current mechanism is selected by this model.",
        "",
        "REPRODUCTION",
        "Run: python3 " + str(ROOT / "model.py"),
        "model.py reads adjacent config.json and writes adjacent results.json and README.txt. Python standard library only.",
        "Money is computed unrounded and displayed to cents; summed rounded components may differ by pennies.",
        "config.json contains every role/hour/rate assumption, source observation, scope boundary, and VOI input.",
        "results.json preserves unknowns as null and assumptions as labeled scenarios.",
        "",
        "SOURCES (OFFICIAL, RETRIEVED 2026-10-27)",
    ]
    for s in config["sources"]:
        lines.append(s["id"] + " | " + s["title"] + " | " + s["url"])
    return "\n".join(lines) + "\n"

def main():
    config = json.loads((ROOT / "config.json").read_text())
    result = compute(config)
    (ROOT / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "README.txt").write_text(render_readme(config, result))
    print(json.dumps({
        "human_cost_scenarios_usd": {c: result["human_comparator_scenarios"][c]["total_cost_usd"] for c in SCENARIOS},
        "human_person_hours": {c: result["human_comparator_scenarios"][c]["person_hours"] for c in SCENARIOS},
        "automated_planning_totals_usd": {c: result["automated_planning_scenarios"][c]["planning_total_usd"] for c in SCENARIOS},
        "optional_review_costs_usd": {k: v["optional_research_cost_usd"] for k,v in result["optional_specialist_review_scenarios"].items()},
        "actual_ai_billing_usd": None, "selected_offering": None, "accepted_customer_outcomes": 0,
        "actual_profit_usd": None, "category": "C", "outputs": [str(ROOT / "results.json"), str(ROOT / "README.txt")]
    }, indent=2))

if __name__ == "__main__":
    main()
