# SPDX-License-Identifier: Apache-2.0
"""Corrected V2 independent-stream paired economics for a 20-day roster/care coordination package.

All buyer behavior, model usage, operating prices and service success are explicit
assumptions. This program simulates service delivery, not physical child care.
It never moves funds. Human R&D resource estimates are not used as market prices.
"""

from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/economic_config_v2.json"
OUT = ROOT / "economics_v2"


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(xs, p):
    ys = sorted(xs)
    index = (len(ys) - 1) * p
    lo = int(index)
    hi = min(lo + 1, len(ys) - 1)
    return ys[lo] + (ys[hi] - ys[lo]) * (index - lo)


def unit_cost(c):
    """Token amounts include invisible reasoning and all indicated review stages."""
    rows = []
    for row in c["inference"]:
        usd = row["input_mtokens"] * row["input_usd_per_mtoken"] + row["output_mtokens"] * row["output_usd_per_mtoken"]
        rows.append({**row, "usd": usd, "cad": usd * c["usd_cad"]})
    inference = sum(x["cad"] for x in rows)
    non_inference = sum(c["delivery_non_inference_cad"].values())
    # Expected correction/failure costs are inside A, not charged again to B/C.
    recovery = (
        c["retry_probability"] * c["retry_cost_cad"]
        + c["postaccept_correction_probability"] * c["postaccept_correction_cost_cad"]
    )
    return {
        "inference": rows,
        "inference_cad": inference,
        "non_inference_cad": non_inference,
        "expected_recovery_cad": recovery,
        "per_attempt_cad": inference + non_inference + recovery,
        "preflight_refusal_cad": c["preflight_refusal_cad"],
        "measured_api_expenditure": None,
        "status": "Assumed usage at documented unit prices; not metered expenditure",
    }


def make_world(seed, i, c, overrides=None, broad=False):
    r = random.Random(f"{seed}:{i}:roster-care-v1")
    d = dict(c["central"])
    if broad:
        # Deliberately broad modeling priors; frequencies are conditional on them.
        d.update(
            {
                "qualified_leads_month": r.choice([4, 8, 12, 16, 20]),
                "acquisition_per_lead_cad": r.triangular(8, 120, 30),
                "value_scale": r.triangular(0.45, 1.6, 0.95),
                "competition_haircut": r.uniform(0.05, 0.65),
                "technical_eligibility": r.uniform(0.4, 0.9),
                "semantic_acceptance": r.uniform(0.7, 0.97),
                "cost_multiplier": r.triangular(0.7, 3.5, 1.2),
                "overhead_month_cad": r.uniform(250, 800),
                "provider_absence_probability": r.uniform(0.01, 0.15),
                "payment_default_probability": r.uniform(0, 0.08),
            }
        )
    if overrides:
        d.update(overrides)
    q = d["semantic_acceptance"]
    quality_rng = random.Random(f"{seed}:{i}:quality-v2")
    d["world_acceptance"] = quality_rng.betavariate(max(0.01, q * 40), max(0.01, (1 - q) * 40))
    # A shared supply/organizational shock lowers eligibility in the same quarter
    # for every pricing policy. It is not independent per-job model agreement.
    common_shock = random.Random(f"{seed}:{i}:common-v2").random() < d["annual_common_shock_probability"]
    jobs = []
    for month in range(c["selling_months"]):
        month_jobs = []
        for j in range(d["qualified_leads_month"]):
            job_rng = random.Random(f"{seed}:{i}:job-v2:{month}:{j}")
            employer_values = []
            for _ in range(2):
                prevented_shifts = job_rng.choice([2, 4, 6, 8, 10, 12])
                contribution = job_rng.uniform(140, 260)
                employer_values.append(prevented_shifts * contribution * d["value_scale"])
            month_jobs.append(
                {
                    "eligibility_u": job_rng.random(),
                    "acceptance_u": job_rng.random(),
                    "parent_participation_u": job_rng.random(),
                    "employer_value_cad": employer_values,
                    "default_u": job_rng.random(),
                    "order_u": job_rng.random(),
                }
            )
        jobs.append(sorted(month_jobs, key=lambda x: x["order_u"]))
    return {"i": i, "params": d, "common_shock": common_shock, "jobs": jobs}


def evaluate(world, policy, c):
    p = policy["price_cad"]
    deferred = policy["deferred_fraction"]
    d = world["params"]
    cost = unit_cost(c)
    cash = c["opening_finance_cad"] - c["launch_operating_cost_cad"]
    minimum_cash = cash
    minimum_month_end_cash = cash
    revenue = collections = baddebt = 0.0
    delivery = c["launch_operating_cost_cad"]
    acquisition = overhead = 0.0
    accepted = attempted = refused = qualified = interested = capacity_declines = cash_declines = 0
    pending = []
    records = []
    wind_down = False
    customer_funds = 0.0
    for m in range(c["selling_months"] + 1):
        for amount, default in pending:
            if default:
                baddebt += amount
            else:
                cash += amount
                collections += amount
        pending = []
        if m == c["selling_months"]:
            records.append({"month": m + 1, "runoff": True, "cash": round(cash, 4)})
            break
        if wind_down:
            records.append({"month": m + 1, "wind_down": True, "cash": round(cash, 4)})
            continue
        if cash < d["overhead_month_cad"] + c["minimum_business_reserve_cad"]:
            wind_down = True
            records.append({"month": m + 1, "wind_down": True, "cash": round(cash, 4)})
            continue
        cash -= d["overhead_month_cad"]
        overhead += d["overhead_month_cad"]
        minimum_cash = min(minimum_cash, cash)
        available = max(0, cash - c["minimum_business_reserve_cad"])
        n = min(len(world["jobs"][m]), int(available // d["acquisition_per_lead_cad"]))
        acquisition += n * d["acquisition_per_lead_cad"]
        cash -= n * d["acquisition_per_lead_cad"]
        minimum_cash = min(minimum_cash, cash)
        qualified += n
        cash_declines += len(world["jobs"][m]) - n
        worked = 0
        month_accepted = 0
        for job in world["jobs"][m][:n]:
            # Parents pay the same fixed capped care contribution at every price.
            # Employers must EACH gain and EACH remain within the funded ceiling.
            expected_employer_pass = (
                c["operating_days"] * c["daily_pass_consumption_cad"] - c["monthly_parent_care_contribution_cad"]
            ) / 2
            expected_backup = (
                c["operating_days"] * c["daily_backup_reserve_cad"] * d["provider_absence_probability"] / 2
            )
            capital_charge = c["operating_days"] * c["daily_backup_reserve_cad"] * c["monthly_capital_rate"] / 2
            employer_intake = c["buyer_hr_hours_each"] * c["buyer_hr_wage_cad"] * c["buyer_composite_load"]
            private_cost = expected_employer_pass + expected_backup + capital_charge + employer_intake
            # Outside options/competition reduce incremental value. Deferred terms
            # relax the assumed liquidity discount only; the price cap stays fixed.
            liquidity = 1 - d["upfront_liquidity_discount"] * (1 - deferred)
            willingness = [
                max(0, (d["buyer_outcome_confidence"] * v - private_cost) * (1 - d["competition_haircut"]) * liquidity)
                for v in job["employer_value_cad"]
            ]
            if (
                p > c["maximum_monthly_service_fee_cad"]
                or p / 2 > min(willingness)
                or job["parent_participation_u"] > d["parent_participation_probability"]
            ):
                continue
            interested += 1
            eligible = d["technical_eligibility"] * (0.5 if world["common_shock"] and 3 <= m < 6 else 1)
            if job["eligibility_u"] >= eligible:
                refusal_cost = cost["preflight_refusal_cad"] * d["cost_multiplier"]
                if cash - c["minimum_business_reserve_cad"] < refusal_cost:
                    cash_declines += 1
                    continue
                cash -= refusal_cost
                delivery += refusal_cost
                refused += 1
                minimum_cash = min(minimum_cash, cash)
                continue
            if worked >= c["attempt_capacity_month"]:
                capacity_declines += 1
                continue
            ac = cost["per_attempt_cad"] * d["cost_multiplier"]
            if cash - c["minimum_business_reserve_cad"] < ac:
                cash_declines += 1
                continue
            cash -= ac
            delivery += ac
            attempted += 1
            worked += 1
            minimum_cash = min(minimum_cash, cash)
            if job["acceptance_u"] >= d["world_acceptance"]:
                continue
            accepted += 1
            month_accepted += 1
            revenue += p
            immediate = p * (1 - deferred)
            # Payment-on-acceptance: no revenue or advance from refused attempts.
            # Immediate payment is collected before package release. Default risk
            # applies only to genuinely deferred receivables.
            cash += immediate
            collections += immediate
            pending.append((p * deferred, job["default_u"] < d["payment_default_probability"]))
            customer_funds += c["operating_days"] * c["daily_pass_maximum_cad"]
        minimum_cash = min(minimum_cash, cash)
        minimum_month_end_cash = min(minimum_month_end_cash, cash)
        records.append({"month": m + 1, "accepted": month_accepted, "cash": round(cash, 4)})
    complete_a = delivery + acquisition + overhead
    profit = revenue - baddebt - complete_a
    assert abs(cash - (c["opening_finance_cad"] + profit)) < 1e-6
    return {
        "world": world["i"],
        "policy": policy,
        "accepted": accepted,
        "attempted": attempted,
        "preflight_refusals": refused,
        "qualified_leads": qualified,
        "interested": interested,
        "capacity_declines": capacity_declines,
        "cash_declines": cash_declines,
        "service_revenue_cad": revenue,
        "collected_service_cash_cad": collections,
        "bad_debt_cad": baddebt,
        "A_delivery_and_launch_cad": delivery,
        "A_acquisition_cad": acquisition,
        "A_business_overhead_cad": overhead,
        "A_complete_operating_cost_cad": complete_a,
        "operating_profit_cad": profit,
        "contribution_before_fixed_business_cost_cad": revenue
        - baddebt
        - (delivery - c["launch_operating_cost_cad"])
        - acquisition,
        "closing_company_cash_cad": cash,
        "minimum_company_cash_cad": minimum_cash,
        "minimum_month_end_cash_cad": minimum_month_end_cash,
        "company_reserve_cad": c["minimum_business_reserve_cad"],
        "available_growth_cash_cad": max(0, cash - c["minimum_business_reserve_cad"]),
        "customer_pass_funding_separate_cad": customer_funds,
        "assumed_unsettled_customer_obligations_at_runoff_cad": 0,
        "unsettled_receivables_at_runoff_cad": 0,
        "wind_down": wind_down,
        "common_shock": world["common_shock"],
        "actual_receipts_cad": 0,
        "monthly": records,
    }


def summary(rows):
    keys = [
        "accepted",
        "attempted",
        "preflight_refusals",
        "qualified_leads",
        "interested",
        "capacity_declines",
        "cash_declines",
        "service_revenue_cad",
        "collected_service_cash_cad",
        "bad_debt_cad",
        "A_delivery_and_launch_cad",
        "A_acquisition_cad",
        "A_business_overhead_cad",
        "A_complete_operating_cost_cad",
        "operating_profit_cad",
        "contribution_before_fixed_business_cost_cad",
        "closing_company_cash_cad",
        "minimum_company_cash_cad",
        "minimum_month_end_cash_cad",
        "available_growth_cash_cad",
        "customer_pass_funding_separate_cad",
    ]
    result = {"worlds": len(rows), "means": {k: statistics.mean(r[k] for r in rows) for k in keys}}
    ps = [r["operating_profit_cad"] for r in rows]
    result.update(
        {
            "profit_p05_cad": quantile(ps, 0.05),
            "profit_p50_cad": quantile(ps, 0.5),
            "profit_p95_cad": quantile(ps, 0.95),
            "profit_mean_mc_standard_error_cad": statistics.stdev(ps) / math.sqrt(len(ps)) if len(ps) > 1 else None,
            "probability_positive_operating_profit": statistics.mean(x > 0 for x in ps),
            "wind_down_fraction": statistics.mean(r["wind_down"] for r in rows),
            "range_interpretation": "Conditional simulation variation, not an empirical confidence interval or probability of actual market success.",
        }
    )
    return result


def policies(c):
    return [
        {"price_cad": p, "deferred_fraction": d, "name": f"{p}-" + ("acceptance" if d == 0 else "half-30days")}
        for p in c["candidate_prices_cad"]
        for d in [0, 0.5]
    ]


def selection(c):
    worlds = [make_world(c["selection_seed"], i, c) for i in range(c["selection_worlds"])]
    table = []
    for pol in policies(c):
        s = summary([evaluate(w, pol, c) for w in worlds])
        table.append({"policy": pol, **s})
    # Optimize available funds above the fixed seed, with early wind-down penalty.
    for row in table:
        row["selection_score_cad"] = (
            row["means"]["operating_profit_cad"] - c["wind_down_penalty_cad"] * row["wind_down_fraction"]
        )
    best = max(table, key=lambda x: (x["selection_score_cad"], -x["policy"]["price_cad"]))
    data = {
        "policy_family": "Six fee levels × two explicit payment arrangements. No observed human price is used for a novel offering.",
        "seed": c["selection_seed"],
        "results": table,
        "selected": best["policy"],
        "objective": "Mean operating profit minus CAD500 per simulated early wind-down; finite capacity and financing are inside every world.",
        "status": "Development selection, not fresh confirmation",
    }
    dump(OUT / "POLICY_SELECTION.json", data)
    freeze = {
        "schema": "agi-alpha.economic-freeze.v2",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": digest(Path(__file__)),
        "configuration_sha256": digest(CONFIG),
        "selection_sha256": digest(OUT / "POLICY_SELECTION.json"),
        "selected_policy": best["policy"],
        "confirmation_seed": c["confirmation_seed"],
        "confirmation_worlds": c["confirmation_worlds"],
        "broad_seed": c["broad_seed"],
        "broad_worlds": c["broad_worlds"],
        "confirmation_executed_at_freeze": False,
        "interpretation": "A prospective software freeze within this research session; no external timestamp attestation.",
    }
    dump(OUT / "POLICY_FREEZE.json", freeze)
    return data


def check_freeze():
    f = json.loads((OUT / "POLICY_FREEZE.json").read_text())
    if f["script_sha256"] != digest(Path(__file__)) or f["configuration_sha256"] != digest(CONFIG):
        raise ValueError("Frozen script/config changed; preserve version and register a new prospective test")
    if f["selection_sha256"] != digest(OUT / "POLICY_SELECTION.json"):
        raise ValueError("Selection changed")
    return f


def confirmation(c):
    f = check_freeze()
    p = f["selected_policy"]
    worlds = [make_world(c["confirmation_seed"], i, c) for i in range(c["confirmation_worlds"])]
    rows = [evaluate(w, p, c) for w in worlds]
    dump(OUT / "FRESH_WORLDS.json", rows)
    comparison = [{"policy": x, **summary([evaluate(w, x, c) for w in worlds])} for x in policies(c)]
    result = {
        "seed": c["confirmation_seed"],
        "policy_frozen": p,
        **summary(rows),
        "policy_family_confirmation": comparison,
        "cost": unit_cost(c),
        "actual_service_receipts_cad": 0,
        "opening_finance_is_not_revenue": c["opening_finance_cad"],
        "B_assessment_cad": c["B_assessment_cad"],
        "historical_C_planning_estimate_cad": c["historical_C_planning_estimate_cad"],
        "profit_after_B_and_C_planning_estimate_cad": statistics.mean(r["operating_profit_cad"] for r in rows)
        - c["B_assessment_cad"]
        - c["historical_C_planning_estimate_cad"],
    }
    dump(OUT / "COMMERCIAL_RESULT.json", result)
    cases = [
        ("central", {}),
        ("leads4", {"qualified_leads_month": 4}),
        ("leads8", {"qualified_leads_month": 8}),
        ("leads20", {"qualified_leads_month": 20}),
        ("acquisition60", {"acquisition_per_lead_cad": 60}),
        ("acquisition120", {"acquisition_per_lead_cad": 120}),
        ("half_value", {"value_scale": 0.5}),
        ("competition60", {"competition_haircut": 0.6}),
        ("quality75", {"semantic_acceptance": 0.75}),
        ("quality97", {"semantic_acceptance": 0.97}),
        ("eligibility40", {"technical_eligibility": 0.4}),
        ("cost3x", {"cost_multiplier": 3}),
        ("backup15", {"provider_absence_probability": 0.15}),
        ("zero_operational_gain", {"semantic_acceptance": c["central"]["semantic_acceptance"]}),
        ("model_upgrade_half_cost", {"cost_multiplier": 0.5}),
    ]
    sensitivity = []
    for name, ov in cases:
        ww = [make_world(c["confirmation_seed"], i, c, overrides=ov) for i in range(c["confirmation_worlds"])]
        rr = [evaluate(w, p, c) for w in ww]
        sensitivity.append(
            {
                "name": name,
                "overrides": ov,
                **summary(rr),
                "paired_profit_delta_cad": statistics.mean(
                    b["operating_profit_cad"] - a["operating_profit_cad"] for a, b in zip(rows, rr)
                ),
            }
        )
    dump(OUT / "SENSITIVITY.json", sensitivity)
    broad_worlds = [make_world(c["broad_seed"], i, c, broad=True) for i in range(c["broad_worlds"])]
    broad_rows = [evaluate(w, p, c) for w in broad_worlds]
    dump(OUT / "BROAD_WORLDS.json", broad_rows)
    broad_policy = [{"policy": x, **summary([evaluate(w, x, c) for w in broad_worlds])} for x in policies(c)]
    dump(
        OUT / "BROAD_UNCERTAINTY.json",
        {
            "seed": c["broad_seed"],
            "selected_policy": p,
            **summary(broad_rows),
            "prior_description": "Explicit broad ranges in make_world; they are neither measured distributions nor probability forecasts.",
            "all_policies": broad_policy,
            "best_in_this_sensitivity_family": max(broad_policy, key=lambda x: x["means"]["operating_profit_cad"])[
                "policy"
            ],
        },
    )
    # Operational Alpha is a sensitivity, not an inferred gain from a prompt.
    alpha = []
    for uq in [0.75, 0.85, 0.9, 0.95]:
        uu = [
            evaluate(make_world(c["confirmation_seed"], i, c, {"semantic_acceptance": uq}), p, c)
            for i in range(c["confirmation_worlds"])
        ]
        alpha.append(
            {
                "ordinary_assumed_acceptance": uq,
                "expert_assumed_acceptance": c["central"]["semantic_acceptance"],
                "paired_E_minus_U_profit_cad": statistics.mean(
                    e["operating_profit_cad"] - u["operating_profit_cad"] for u, e in zip(uu, rows)
                ),
                "assumed_not_measured": True,
            }
        )
    retention = []
    for uses in [4, 12, 24, 48, 72]:
        for saving in [0, 5, 15, 30]:
            for monthly_maintenance in [0, 15, 40]:
                b = c["B_assessment_cad"] + c["B_extraction_cad"] + 12 * monthly_maintenance
                net = uses * (saving - c["B_invocation_cad"]) - b
                retention.append(
                    {
                        "uses": uses,
                        "gross_saving_per_use_cad": saving,
                        "monthly_maintenance_cad": monthly_maintenance,
                        "B_total_fixed_cad": b,
                        "net_retained_alpha_cad": net,
                        "break_even_uses": math.ceil(b / (saving - c["B_invocation_cad"]))
                        if saving > c["B_invocation_cad"]
                        else None,
                    }
                )
    dump(
        OUT / "ALPHA_RESULTS.json",
        {
            "operational": {
                "measured_effect": None,
                "same_frontier_model_controlled_repeated_trials": 0,
                "default_no_gain": True,
                "sensitivity": alpha,
                "interpretation": "Observed discovery runs do not identify mission delivery success. The zero-gain assumption leaves the service economics unchanged.",
            },
            "retained": {
                "decision": "HOLD paid network admission pending measured incremental reuse benefit and real demand.",
                "same_information_library_control": "Identical executable information must receive identical technical results; network provenance is not an economic advantage.",
                "B_rejected_assessment_cad": c["B_assessment_cad"],
                "grid": retention,
                "central_forward_case": {
                    "expected_uses": 24,
                    "saving_per_use_cad": 15,
                    "invocation_cad": c["B_invocation_cad"],
                    "extraction_cad": c["B_extraction_cad"],
                    "annual_maintenance_cad": 180,
                    "net_forward_excluding_sunk_assessment_cad": 24 * (15 - c["B_invocation_cad"])
                    - c["B_extraction_cad"]
                    - 180,
                },
            },
            "C": {
                "gym_training_expenditure_measured": None,
                "additional_training_committed": False,
                "historical_research_planning_estimate_cad": c["historical_C_planning_estimate_cad"],
                "actual_complete_research_cost": "Unmetered; no claim of paid-job learning.",
            },
        },
    )
    dump(
        OUT / "VERIFICATION.json",
        {
            "all_worlds_preserved": True,
            "worlds": len(rows),
            "broad_worlds": len(broad_rows),
            "cash_conservation_each_world": True,
            "separate_quality_and_job_random_streams": True,
            "intramonth_minimum_tracked": True,
            "separate_customer_funds": True,
            "actual_collections_zero": True,
            "frozen_inputs_valid": True,
            "policy_not_reselected_on_confirmation": True,
            "infeasible_prices": {
                "above_monthly_cap": 1400,
                "price1500_must_have_zero_accepted": all(
                    x["means"]["accepted"] == 0 for x in comparison if x["policy"]["price_cad"] == 1500
                ),
            },
        },
    )
    return result


def main():
    a = argparse.ArgumentParser()
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--select", action="store_true")
    g.add_argument("--confirm", action="store_true")
    g.add_argument("--verify", action="store_true")
    args = a.parse_args()
    c = json.loads(CONFIG.read_text())
    if args.select:
        if (OUT / "POLICY_FREEZE.json").exists():
            raise RuntimeError("Selection already frozen; preserve it")
        r = selection(c)
        print(json.dumps({"selected": r["selected"]}, indent=2))
    elif args.confirm:
        r = confirmation(c)
        print(
            json.dumps(
                {
                    "selected": r["policy_frozen"],
                    "means": r["means"],
                    "p05": r["profit_p05_cad"],
                    "p95": r["profit_p95_cad"],
                },
                indent=2,
            )
        )
    else:
        print(
            json.dumps(
                {
                    "freeze_valid": bool(check_freeze()),
                    "verification": json.loads((OUT / "VERIFICATION.json").read_text()),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
