#!/usr/bin/env python3
"""Standard-library-only, finite-horizon, hypothetical same-offering economics.

Commands are deliberately sequential: check -> explore -> confirm -> report.
Exploration writes an immutable policy record before confirmation may run.
"""
import argparse
import copy
import csv
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / "results"
CFG = json.loads((HERE / "config.json").read_text())
MANIFEST = json.loads((ROOT / CFG["model_manifest_path"]).read_text())
PRICES = {x["id"]: x for x in MANIFEST["selected_for_hypothetical_delivery"]}
RATES = {k: v * CFG["employer_compensation_factor"] for k, v in CFG["wages_gross_per_hour"].items()}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite preserved output: {path}")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def write_csv(path, rows):
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite preserved output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def labor(hours, overhead=True):
    base = sum(RATES[k] * v for k, v in hours.items())
    return base * (1 + CFG["shared_overhead_fraction"] if overhead else 1)


def compute_cost():
    w = CFG["compute_workload_per_contract"]
    amount = 0.0
    for model, spec in PRICES.items():
        t = w[model]
        amount += (t["input_tokens"] * spec["input_per_million"] + t["output_tokens"] * spec["output_per_million"]) / 1e6
    costs = MANIFEST["tool_cost_assumptions"]
    amount += w["web_search_calls"] * costs["web_search_per_1000"] / 1000
    amount += w["container_20min_sessions"] * costs["container_1GB_per20min"]
    return amount


def cohort(s, seed):
    rng = random.Random(seed)
    rows = []
    for i in range(s["origins"]):
        rows.append({"id": i, "day": rng.randrange(CFG["horizon_days"]),
                     "complexity": min(2.0, max(0.6, rng.lognormvariate(0, 0.35))),
                     "value_multiplier": rng.lognormvariate(0, 0.55),
                     "minutes_multiplier": rng.lognormvariate(0, 0.45),
                     "fit": rng.random(), "admissible": rng.random(),
                     "decisive": rng.random(), "accept": rng.random(),
                     "refund": rng.random(), "default": rng.random(),
                     "rework": rng.random(), "budget_exhausted": rng.random()})
    return sorted(rows, key=lambda r: (r["day"], r["id"]))


def utilities(origin, s, price, quoted_days=None):
    q_outside = s["source_admissible_probability"] * s["original_query_decisive_probability"] * s["client_acceptance_probability"]
    q = (1 - CFG["budget_exhaustion_probability"]) * q_outside
    c = origin["complexity"]
    value = s["outcome_value_median"] * origin["value_multiplier"]
    source_hours = (s["source_construction_hours"] + s["independent_source_validation_hours"] + 0.08) * c
    # Same domain burden in buyer and supplier; no source-validation saving is asserted.
    human_source_cost = source_hours * RATES["domain"] * (1 + CFG["shared_overhead_fraction"])
    minutes = s["outside_additional_analyst_minutes_median"] * origin["minutes_multiplier"] * c
    outside = human_source_cost + minutes / 60 * CFG["customer_loaded_hour_value"] + CFG["outside_option_buyer_hours"] * CFG["customer_loaded_hour_value"]
    friction = CFG["offer_buyer_hours"] * CFG["customer_loaded_hour_value"]
    if quoted_days is None:
        quoted_days = math.ceil(CFG["base_turnaround_days"] * c)
    liquidity_cost = CFG["deposit_fraction"] * price * CFG["buyer_capital_apr"] * quoted_days / 365
    offer_u = q * (value - price) - friction - liquidity_cost
    outside_u = max(0.0, q_outside * value - outside)
    if s.get("no_buyer_advantage", False):
        # A separately labeled stress case: buyer already has an equivalent free result.
        outside_u = q_outside * value
    return offer_u, outside_u, q, value, outside, q_outside


def campaign(s, price, seed, retain_ledger=False):
    horizon = CFG["horizon_days"]
    expense_events, pay_events, receipt_events, refund_events = [], [], [], []
    jobs = []
    stats = defaultdict(float, {k: 0.0 for k in ["contracts", "capacity_rejections", "willing_origins", "source_fit_origins", "unsupported_origins", "budget_exhausted_refusals", "bounded_rework_events"]})
    used = defaultdict(float, CFG["fixed_campaign_hours"])
    slots = [0] * CFG["max_parallel_contracts"]
    categories = defaultdict(float)
    current_job_id = None
    for k, v in CFG["intake_hours_per_origin"].items():
        used[k] += s["origins"] * v

    def expense(day, category, amount, payroll=False, cash_day=None):
        day = int(day)
        if cash_day is None:
            cash_day = int(math.ceil((day + 1) / 7) * 7 - 1) if payroll else day
        expense_events.append((day, amount, category, current_job_id))
        pay_events.append((cash_day, amount, category))

    def labor_event(day, category, hours, cash_day=None):
        wage = labor(hours, overhead=False)
        expense(day, category, wage, payroll=True, cash_day=cash_day)
        overhead_category = "A_fixed_overhead" if category == "A_fixed_campaign" else "A_variable_overhead"
        expense(day, overhead_category, wage * CFG["shared_overhead_fraction"], payroll=True, cash_day=cash_day)

    def receipt(day, amount):
        receipt_events.append((day, amount))
        expense(day, "A_payment_fees", amount * CFG["payment_fee_fraction"] + CFG["payment_fixed_fee"])

    def refund(day, amount, accrual_day=None):
        refund_events.append((day, amount))
        expense(day if accrual_day is None else accrual_day, "A_payment_fees", CFG["refund_transfer_fee"], cash_day=day)

    # Fixed maintenance/account management is a real campaign cost, not per-case markup.
    for day in range(horizon):
        labor_event(day, "A_fixed_campaign", {k: v / horizon for k, v in CFG["fixed_campaign_hours"].items()})

    for origin in cohort(s, seed):
        current_job_id = None
        stats["origins"] += 1
        day, c = origin["day"], origin["complexity"]
        labor_event(day, "A_origin_intake", CFG["intake_hours_per_origin"])
        expense(day, "A_cash_channel_acquisition", s.get("cash_acquisition_per_origin", CFG["cash_acquisition_per_origin"]))
        if origin["fit"] >= s["source_fit_probability"]:
            stats["unsupported_origins"] += 1
            continue
        stats["source_fit_origins"] += 1
        construction = {"domain": s["source_construction_hours"] * c}
        validation = {"domain": s["independent_source_validation_hours"] * c}
        ingest = {k: v * c for k, v in CFG["ingest_hours_per_contract"].items()}
        budget = defaultdict(float)
        for h in [ingest, construction, validation, CFG["rework_hours"], CFG["execution_hours_if_admissible"], CFG["delivery_hours_per_decision"], CFG["support_hours_per_accepted_delivery"]]:
            for k, v in h.items():
                budget[k] += v
        slot = min(range(len(slots)), key=slots.__getitem__)
        start = max(day, slots[slot])
        duration = max(5, int(math.ceil(CFG["base_turnaround_days"] * c)))
        quoted_days = start - day + duration
        offer_u, outside_u, q, value, outside, q_outside = utilities(origin, s, price, quoted_days)
        if offer_u < outside_u:
            continue
        stats["willing_origins"] += 1
        if any(used[k] + v > CFG["capacity_hours"][k] for k, v in budget.items()) or start - day > CFG["maximum_start_wait_days"]:
            stats["capacity_rejections"] += 1
            continue
        for k, v in budget.items():
            used[k] += v
        current_job_id = origin["id"]
        source_day = start + max(2, int(math.ceil(duration * 0.6)))
        complete_day = start + duration
        budget_exhausted = origin["budget_exhausted"] < CFG["budget_exhaustion_probability"]
        rework = origin["rework"] < CFG["rework_probability"]
        admissible = (not budget_exhausted) and origin["admissible"] < s["source_admissible_probability"]
        decisive = admissible and origin["decisive"] < s["original_query_decisive_probability"]
        accepted = decisive and origin["accept"] < s["client_acceptance_probability"]
        decision_day = complete_day if admissible else source_day
        # Booking cannot use an unobserved future source-refusal outcome.
        # Conservatively retain the full promised slot even after an early refusal.
        slots[slot] = complete_day
        guarantee_end = decision_day + CFG["guarantee_days"]
        deposit = price * CFG["deposit_fraction"]
        balance = price - deposit
        balance_day = decision_day + CFG["balance_settlement_days"]
        default = accepted and origin["default"] < s["default_probability"]
        guarantee_refund = accepted and origin["refund"] < s["refund_probability"]
        refund_day = guarantee_end if guarantee_refund else (decision_day + 1 if not accepted else None)
        receipt(day, deposit)
        if accepted:
            if not default:
                receipt_events.append((balance_day, balance))
            # Accrue expected fees when earned; settle actual attempt/collection fees
            # three days later, retaining the unfavorable fee on a failed attempt.
            expected_fee = (1 - s["default_probability"]) * balance * CFG["payment_fee_fraction"] + CFG["payment_fixed_fee"]
            actual_fee = (0 if default else balance * CFG["payment_fee_fraction"]) + CFG["payment_fixed_fee"]
            expense_events.append((decision_day, expected_fee, "A_payment_fees", current_job_id))
            expense_events.append((balance_day, actual_fee - expected_fee, "A_payment_fees", current_job_id))
            pay_events.append((balance_day, actual_fee, "A_payment_fees"))
        if refund_day is not None:
            refund(refund_day, deposit + (balance if accepted and not default else 0), accrual_day=None if accepted else decision_day)
        labor_event(start + 1, "A_scope_ingest", ingest)
        expense(start + 1, "A_source_access", CFG["cash_source_cost_per_contract"])
        labor_event(source_day, "A_source_admissibility_construction", construction)
        labor_event(source_day, "A_independent_domain_source_validation", validation)
        expense(source_day, "A_model_tools_compute", compute_cost())
        if rework:
            labor_event(source_day, "A_bounded_rework", CFG["rework_hours"])
            expense(source_day, "A_model_tools_compute", compute_cost())
            if source_day < horizon:
                stats["bounded_rework_events"] += 1
        if budget_exhausted and decision_day < horizon:
            stats["budget_exhausted_refusals"] += 1
        if admissible:
            labor_event(complete_day, "A_exact_execution_witness_QA", CFG["execution_hours_if_admissible"])
        labor_event(decision_day, "A_delivery_or_refusal", CFG["delivery_hours_per_decision"])
        if accepted:
            support_pay_day = int(math.ceil((decision_day + CFG["support_days"] + 1) / 7) * 7 - 1)
            # Accrue the promised support once at acceptance, even if paid after day 90.
            labor_event(decision_day, "A_promised_support", CFG["support_hours_per_accepted_delivery"], cash_day=support_pay_day)
        jobs.append({"origin": origin["id"], "order_day": day, "start_day": start,
                     "booked_slot": slot, "booked_finish_day": complete_day,
                     "quoted_wait_plus_turnaround_days": quoted_days,
                     "budget_exhausted": budget_exhausted, "rework_rounds": int(rework),
                     "decision_day": decision_day, "accepted": accepted, "admissible": admissible,
                     "decisive": decisive, "refund_day": refund_day, "guarantee_end": guarantee_end,
                     "guarantee_refund": guarantee_refund, "balance_day": balance_day,
                     "default": default, "deposit": deposit, "balance": balance,
                     "price": price, "budget_hours": dict(budget), "q_assumed": q,
                     "q_outside_assumed": q_outside,
                     "budget_cost": labor(budget) + 2 * compute_cost() + CFG["cash_source_cost_per_contract"] + price * CFG["payment_fee_fraction"] + 2 * CFG["payment_fixed_fee"] + CFG["refund_transfer_fee"],
                     "buyer_outcome_value": value, "buyer_outside_cost": outside})
        stats["contracts"] += 1

    stats["decision_completed"] = sum(j["decision_day"] < horizon for j in jobs)
    stats["source_admissibility_failures"] = sum(j["decision_day"] < horizon and not j["admissible"] for j in jobs)
    stats["unresolved_original_queries"] = sum(j["decision_day"] < horizon and j["admissible"] and not j["decisive"] for j in jobs)
    stats["decisive_but_not_accepted"] = sum(j["decision_day"] < horizon and j["decisive"] and not j["accepted"] for j in jobs)
    accepted_jobs = [j for j in jobs if j["decision_day"] < horizon and j["accepted"]]
    stats["useful_accepted_deliveries"] = len(accepted_jobs)
    stats["open_contracts"] = len(jobs) - stats["decision_completed"]
    stats["gross_accepted_revenue"] = len(accepted_jobs) * price
    stats["accepted_refunds_contra_revenue"] = sum(price for j in accepted_jobs if j["guarantee_refund"] and j["refund_day"] < horizon)
    stats["expected_unexpired_refund_allowance"] = sum(price * s["refund_probability"] for j in accepted_jobs if j["guarantee_end"] >= horizon)
    stats["earned_modeled_revenue"] = stats["gross_accepted_revenue"] - stats["accepted_refunds_contra_revenue"] - stats["expected_unexpired_refund_allowance"]
    # Credit/default reversals prevent counting a refunded invoice as both lost revenue and bad debt.
    stats["bad_debt"] = sum(j["balance"] * (1 - s["refund_probability"] if j["guarantee_end"] >= horizon else 1) for j in accepted_jobs if j["default"] and j["balance_day"] < horizon and not (j["guarantee_refund"] and j["refund_day"] < horizon))
    stats["bad_debt"] += sum(j["balance"] * s["default_probability"] * (1 - s["refund_probability"]) for j in accepted_jobs if j["balance_day"] >= horizon)
    stats["accounts_receivable_gross"] = sum(j["balance"] for j in accepted_jobs if j["balance_day"] >= horizon)
    stats["collected_modeled_cash"] = sum(a for d, a in receipt_events if d < horizon)
    stats["cash_refunds"] = sum(a for d, a in refund_events if d < horizon)
    stats["net_customer_cash_collected"] = stats["collected_modeled_cash"] - stats["cash_refunds"]
    for day, amount, category, _ in expense_events:
        if day < horizon:
            categories[category] += amount
    stats["operating_expense_before_finance"] = sum(categories.values())
    stats["cash_operating_payments"] = sum(a for d, a, _ in pay_events if d < horizon)

    cash = CFG["owner_initial_cash"]
    debt = draws = repayments = interest_total = peak_debt = 0.0
    daily = []
    receipt_by_day, refund_by_day, paid_by_day, expense_by_day = [defaultdict(float) for _ in range(4)]
    job_expense_by_day = defaultdict(list)
    job_incurred = defaultdict(float)
    for d, a in receipt_events:
        receipt_by_day[d] += a
    for d, a in refund_events:
        refund_by_day[d] += a
    for d, a, _ in pay_events:
        paid_by_day[d] += a
    for d, a, _, job_id in expense_events:
        expense_by_day[d] += a
        if job_id is not None:
            job_expense_by_day[d].append((job_id, a))
    cumulative_expense = cumulative_paid = 0.0
    for day in range(horizon):
        cash += receipt_by_day[day]
        cash -= refund_by_day[day]
        cash -= paid_by_day[day]
        cumulative_expense += expense_by_day[day]
        cumulative_paid += paid_by_day[day]
        for job_id, amount in job_expense_by_day[day]:
            job_incurred[job_id] += amount
        interest = debt * CFG["borrowing_apr"] / 365
        cash -= interest
        interest_total += interest
        deposit_liability = 0.0
        guarantee_reserve = 0.0
        completion_reserve = 0.0
        pending_payment_fee_obligation = 0.0
        conditional_fee_reserve = 0.0
        for j in jobs:
            if j["order_day"] > day:
                continue
            if j["decision_day"] > day:
                completion_reserve += max(0, j["budget_cost"] - job_incurred[j["origin"]])
            if (j["decision_day"] > day or not j["accepted"]) and (j["refund_day"] is None or j["refund_day"] > day):
                deposit_liability += j["deposit"]
            if j["accepted"] and j["decision_day"] <= day < j["guarantee_end"]:
                guarantee_reserve += j["deposit"] + (j["balance"] if not j["default"] and j["balance_day"] <= day else 0)
                conditional_fee_reserve += CFG["refund_transfer_fee"]
            if j["accepted"] and j["decision_day"] <= day < j["balance_day"]:
                pending_payment_fee_obligation += (1 - s["default_probability"]) * j["balance"] * CFG["payment_fee_fraction"] + CFG["payment_fixed_fee"]
                conditional_fee_reserve += s["default_probability"] * j["balance"] * CFG["payment_fee_fraction"]
            if not j["accepted"] and j["decision_day"] <= day < j["refund_day"]:
                pending_payment_fee_obligation += CFG["refund_transfer_fee"]
        payable = cumulative_expense - cumulative_paid
        # Reserve the remaining maximum cost of signed, unfinished contracts.
        # Do not anticipate future contracts or use their deposits before arrival.
        available = cash - deposit_liability - guarantee_reserve - payable - completion_reserve - conditional_fee_reserve
        if available < 0:
            draw = -available
            debt += draw
            draws += draw
            cash += draw
            available = 0.0
        elif debt > 0:
            repayment = min(available, debt)
            debt -= repayment
            repayments += repayment
            cash -= repayment
            available -= repayment
        peak_debt = max(peak_debt, debt)
        daily.append({"day": day, "cash": cash, "debt": debt, "restricted_deposits": deposit_liability,
                      "refund_cash_reserve": guarantee_reserve, "accrued_payables": payable,
                      "completion_reserve": completion_reserve,
                      "pending_payment_fees_subset_of_payables": pending_payment_fee_obligation,
                      "conditional_fee_reserve": conditional_fee_reserve,
                      "available_working_cash": available, "free_funds_after_debt": available - debt})
    final = daily[-1]
    stats.update({"cash_at_day90": cash, "loan_draws": draws, "loan_repayments": repayments,
                  "debt_at_day90": debt, "peak_debt": peak_debt, "financing_cost": interest_total,
                  "liquidity_limit_breach": float(peak_debt > CFG["credit_limit"]),
                  "restricted_deposits": final["restricted_deposits"],
                  "refund_cash_reserve": final["refund_cash_reserve"],
                  "accrued_payables": final["accrued_payables"],
                  "completion_reserve": final["completion_reserve"],
                  "pending_payment_fees_subset_of_payables": final["pending_payment_fees_subset_of_payables"],
                  "conditional_fee_reserve": final["conditional_fee_reserve"],
                  "free_funds": final["free_funds_after_debt"]})
    stats["fixed_campaign_cost_including_overhead"] = categories["A_fixed_campaign"] + categories["A_fixed_overhead"]
    stats["direct_variable_A_cost"] = stats["operating_expense_before_finance"] - stats["fixed_campaign_cost_including_overhead"]
    stats["contribution_before_fixed_and_finance"] = stats["earned_modeled_revenue"] - stats["bad_debt"] - stats["direct_variable_A_cost"]
    stats["operating_profit"] = stats["earned_modeled_revenue"] - stats["bad_debt"] - stats["operating_expense_before_finance"] - interest_total
    stats["cash_reconciliation_error"] = cash - (CFG["owner_initial_cash"] + stats["collected_modeled_cash"] + draws - stats["cash_refunds"] - stats["cash_operating_payments"] - repayments - interest_total)
    stats["no_success_fee_on_unresolved"] = 1.0
    for k, v in used.items():
        stats[f"reserved_capacity_hours_{k}"] = v
    for k, v in categories.items():
        stats[k] = v
    if abs(stats["cash_reconciliation_error"]) > 1e-6:
        raise AssertionError("Cash identity failed")
    if retain_ledger:
        return dict(stats), {"jobs": jobs, "daily_cash": daily, "expense_events": expense_events, "cash_payment_events": pay_events, "receipts": receipt_events, "refunds": refund_events}
    return dict(stats)


def summarize(s, price, seed, repetitions):
    rows = [campaign(s, price, seed + i * 1000003) for i in range(repetitions)]
    keys = set().union(*(r.keys() for r in rows))
    mean = {k: statistics.mean(r.get(k, 0.0) for r in rows) for k in keys}
    p = sorted(r["operating_profit"] for r in rows)
    se = statistics.stdev(p) / math.sqrt(repetitions) if repetitions > 1 else 0.0
    mean.update({"repetitions": repetitions, "price": price, "profit_se": se,
                 "profit_mean_ci95_low": mean["operating_profit"] - 1.96 * se,
                 "profit_mean_ci95_high": mean["operating_profit"] + 1.96 * se,
                 "profit_p10": p[int(0.10 * (repetitions - 1))],
                 "profit_p90": p[int(0.90 * (repetitions - 1))],
                 "loss_probability_modeled": sum(x < 0 for x in p) / repetitions,
                 "peak_debt_p95": sorted(r["peak_debt"] for r in rows)[int(0.95 * (repetitions - 1))]})
    return mean


def hashes():
    return {"runner_sha256": digest(__file__), "config_sha256": digest(HERE / "config.json"),
            "construction_protocol_sha256": digest(ROOT / CFG["protocol_path"]),
            "model_manifest_sha256": digest(ROOT / CFG["model_manifest_path"])}


def check():
    s = copy.deepcopy(CFG["scenarios"]["baseline"])
    a = campaign(s, 450, 881)
    b = campaign(s, 450, 881)
    assert a == b, "Determinism/parity failed"
    _, ledger = campaign(s, 450, 881, retain_ledger=True)
    slot_ends = defaultdict(int)
    for job in ledger["jobs"]:
        assert job["start_day"] >= slot_ends[job["booked_slot"]]
        slot_ends[job["booked_slot"]] = job["booked_finish_day"]
        assert job["accepted"] is False or job["decisive"] is True
        assert job["rework_rounds"] <= CFG["max_rework_rounds"]
        assert not job["budget_exhausted"] or not job["accepted"]
    assert all(a[f"reserved_capacity_hours_{role}"] <= cap + 1e-9 for role, cap in CFG["capacity_hours"].items())
    s["no_buyer_advantage"] = True
    z = campaign(s, 450, 881)
    assert z.get("contracts", 0) == 0 and z["earned_modeled_revenue"] == 0
    s = copy.deepcopy(CFG["scenarios"]["baseline"])
    s["original_query_decisive_probability"] = 0
    z = campaign(s, 150, 881)
    assert z["earned_modeled_revenue"] == 0
    assert compute_cost() > 0
    print(json.dumps({"checks": "passed", "compute_per_contract": compute_cost(), "loaded_compensation_rates": RATES}))


def explore():
    if (HERE / "policy_frozen.json").exists():
        raise RuntimeError("Policy already frozen; preserve this exploration and use a versioned new study for changes")
    rows = []
    for price in CFG["prices"]:
        row = summarize(CFG["scenarios"]["baseline"], price, CFG["exploration_seed"], CFG["exploration_campaigns"])
        rows.append(row)
    best = max(rows, key=lambda r: (r["operating_profit"], -r["price"]))
    write_json(RESULTS / "exploratory.json", {"phase": "exploration", "seed": CFG["exploration_seed"], "rows": rows, "all_outcomes_preserved": True, **hashes()})
    write_csv(RESULTS / "exploratory.csv", rows)
    policy = {"phase": "frozen_after_exploration_before_confirmation", "price": best["price"],
              "exploratory_launch_recommendation": best["operating_profit"] > 0,
              "selection_rule": CFG["price_selection"], "exploration_seed": CFG["exploration_seed"],
              "confirmation_seed": CFG["confirmation_seed"], "confirmation_used_for_selection": False,
              "exploration_file_sha256": digest(RESULTS / "exploratory.json"), **hashes()}
    write_json(HERE / "policy_frozen.json", policy)
    print(json.dumps({"frozen_price": best["price"], "exploratory_profit": best["operating_profit"], "launch_recommendation": policy["exploratory_launch_recommendation"]}))


def frozen_policy():
    policy = json.loads((HERE / "policy_frozen.json").read_text())
    for k, v in hashes().items():
        if policy[k] != v:
            raise RuntimeError(f"Frozen input changed: {k}")
    if policy["exploration_file_sha256"] != digest(RESULTS / "exploratory.json"):
        raise RuntimeError("Exploratory record changed")
    return policy


def confirm():
    policy = frozen_policy()
    price = policy["price"]
    rows = []
    scenarios = copy.deepcopy(CFG["scenarios"])
    scenarios["competent_human_fast"] = {**scenarios["baseline"], "outside_additional_analyst_minutes_median": 10}
    scenarios["no_buyer_advantage"] = {**scenarios["baseline"], "no_buyer_advantage": True}
    scenarios["warm_inbound_acquisition_zero"] = {**scenarios["baseline"], "cash_acquisition_per_origin": 0}
    scenarios["acquisition_15_per_origin"] = {**scenarios["baseline"], "cash_acquisition_per_origin": 15}
    scenarios["acquisition_50_per_origin"] = {**scenarios["baseline"], "cash_acquisition_per_origin": 50}
    for name, s in scenarios.items():
        row = summarize(s, price, CFG["confirmation_seed"], CFG["confirmation_campaigns"])
        row["scenario"] = name
        rows.append(row)
    write_json(RESULTS / "confirmation.json", {"phase": "fresh_seed_confirmation", "seed": CFG["confirmation_seed"], "policy": policy, "rows": rows, "no_price_retuning": True})
    write_csv(RESULTS / "confirmation.csv", rows)
    per_origin = []
    for r in rows:
        per_origin.append({"scenario": r["scenario"], "price": price, **{k: r[k] / r["origins"] for k in ["contracts", "useful_accepted_deliveries", "collected_modeled_cash", "earned_modeled_revenue", "operating_expense_before_finance", "bad_debt", "financing_cost", "operating_profit"]}})
    write_csv(RESULTS / "expected_per_origin.csv", per_origin)
    detail, ledger = campaign(CFG["scenarios"]["baseline"], price, CFG["confirmation_seed"], retain_ledger=True)
    write_json(RESULTS / "first_confirmation_campaign_ledger.json", {"summary": detail, "ledger": ledger, "not_selected_for_favorability": True})
    write_csv(RESULTS / "cost_categories.csv", [{"scenario": r["scenario"], **{k: v for k, v in r.items() if k.startswith("A_")}, "bad_debt": r["bad_debt"], "financing_cost": r["financing_cost"]} for r in rows])
    parity = [{"scenario": r["scenario"], "E_profit": r["operating_profit"], "U_profit": r["operating_profit"], "ordinary_library_profit": r["operating_profit"], "E_minus_U": 0, "E_minus_identical_content_library": 0, "basis": "declared identical economics; no measured operational advantage"} for r in rows]
    write_csv(RESULTS / "attribution_null_and_library_parity.csv", parity)
    print(json.dumps([{k: r[k] for k in ["scenario", "price", "contracts", "useful_accepted_deliveries", "operating_profit", "profit_mean_ci95_low", "peak_debt_p95"]} for r in rows], indent=2))


def robustness():
    price = frozen_policy()["price"]
    base = CFG["scenarios"]["baseline"]
    rows = []
    for total_source_hours in [0.5, 1.0, 2.0, 4.0]:
        for minutes in [30, 90, 180]:
            cells = []
            for corner in ["base", "less_decisive", "higher_refunds_defaults", "lower_value", "combined_adverse"]:
                s = copy.deepcopy(base)
                s["source_construction_hours"] = total_source_hours * 0.62
                s["independent_source_validation_hours"] = total_source_hours * 0.38
                s["outside_additional_analyst_minutes_median"] = minutes
                if corner in ("less_decisive", "combined_adverse"):
                    s["source_admissible_probability"] = 0.75
                    s["original_query_decisive_probability"] = 0.45
                if corner in ("higher_refunds_defaults", "combined_adverse"):
                    s["refund_probability"] = 0.08
                    s["default_probability"] = 0.08
                if corner in ("lower_value", "combined_adverse"):
                    s["outcome_value_median"] *= 0.7
                r = summarize(s, price, CFG["robustness_seed"], CFG["robustness_campaigns"])
                r.update({"source_hours": total_source_hours, "outside_additional_minutes": minutes, "corner": corner})
                cells.append(r)
            rows.append({"source_hours": total_source_hours, "outside_additional_minutes": minutes,
                         "frozen_price": price, "min_corner_mean_profit": min(x["operating_profit"] for x in cells),
                         "min_corner_profit_mean_ci95_low": min(x["profit_mean_ci95_low"] for x in cells),
                         "max_corner_peak_debt_p95": max(x["peak_debt_p95"] for x in cells),
                         "robust_over_declared_grid": all(x["profit_mean_ci95_low"] > 0 and x["peak_debt_p95"] <= CFG["credit_limit"] for x in cells)})
            # Retain the losing corners as well as the condensed region.
            write_json(RESULTS / f"robust_cell_source{total_source_hours}_minutes{minutes}.json", cells)
    write_csv(RESULTS / "robust_profitable_region.csv", rows)
    print(json.dumps(rows, indent=2))


def supplementary():
    frozen_policy()
    confirmation = json.loads((RESULTS / "confirmation.json").read_text())["rows"]
    dev = []
    for name, hours in CFG["human_development_hours"].items():
        dev.append({"scope": name, "hours": sum(hours.values()), "gross_wage_cost": sum(CFG["wages_gross_per_hour"][k] * v for k, v in hours.items()), "employer_compensation_cost": labor(hours, overhead=False), "internal_cost_with_assumed_overhead": labor(hours), "price_or_quote": False, "effort_evidence": "analyst scope decomposition, not measured human completion time"})
    write_csv(RESULTS / "human_development_scope_comparison.csv", dev)
    sunk = [{"scenario": r["scenario"], "C_sunk_development": c, "operating_profit_before_C": r["operating_profit"], "first_campaign_profit_after_C": r["operating_profit"] - c} for r in confirmation for c in CFG["development_sunk_cost_sensitivity"]]
    write_csv(RESULTS / "sunk_development_sensitivity.csv", sunk)
    retention = []
    spec = CFG["retention"]
    saved_rate = RATES["scientist"] * (1 + CFG["shared_overhead_fraction"])
    for n in spec["fresh_uses"]:
        threshold = 60 * (spec["one_time_retention_cost"] / n + spec["maintenance_per_fresh_use"]) / saved_rate
        for minutes in spec["avoidable_minutes"]:
            gain = n * minutes / 60 * saved_rate - spec["one_time_retention_cost"] - n * spec["maintenance_per_fresh_use"]
            retention.append({"assumed_fresh_uses": n, "assumed_avoidable_minutes_per_use": minutes, "modeled_net_B": gain, "break_even_minutes": threshold, "reject_retention": gain <= 0, "identical_content_library_incremental_minutes": 0, "incremental_B_over_library_before_formatting_cost": 0, "measured_gain": None})
    write_csv(RESULTS / "optional_retention_B.csv", retention)
    price = json.loads((HERE / "policy_frozen.json").read_text())["price"]
    threshold_rows = []
    for source_hours in [0.5, 1.05, 2.0, 4.0]:
        s = CFG["scenarios"]["baseline"]
        q_outside = s["source_admissible_probability"] * s["original_query_decisive_probability"] * s["client_acceptance_probability"]
        q = (1 - CFG["budget_exhaustion_probability"]) * q_outside
        source = (source_hours + 0.08) * RATES["domain"] * (1 + CFG["shared_overhead_fraction"])
        friction_difference = (CFG["outside_option_buyer_hours"] - CFG["offer_buyer_hours"]) * CFG["customer_loaded_hour_value"]
        liquidity = CFG["deposit_fraction"] * price * CFG["buyer_capital_apr"] * CFG["base_turnaround_days"] / 365
        for outcome_value in [900, 1500]:
            minutes = max(0, 60 * (q * price + (q_outside - q) * outcome_value + liquidity - source - friction_difference) / CFG["customer_loaded_hour_value"])
            threshold_rows.append({"source_hours_same_for_buyer_and_supplier": source_hours, "price": price, "assumed_q_offer": q, "assumed_q_human": q_outside, "assumed_outcome_value": outcome_value, "buyer_outside_additional_minutes_needed_at_median_complexity": minutes, "minimum_decisive_outcome_value_for_offer_vs_do_nothing": price + (CFG["offer_buyer_hours"] * CFG["customer_loaded_hour_value"] + liquidity) / q, "quoted_wait_days_for_threshold": 0, "turnaround_days_for_threshold": CFG["base_turnaround_days"], "note": "Participation threshold only; supplier profitability must also pass. Longer actual waits increase the threshold. Value and time are assumptions."})
    write_csv(RESULTS / "buyer_break_even_minutes.csv", threshold_rows)
    print(json.dumps({"supplementary_files": 4, "human_development": dev, "retention_delta_zero_rejects": True}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check", "explore", "confirm", "robustness", "supplementary"])
    args = parser.parse_args()
    {"check": check, "explore": explore, "confirm": confirm, "robustness": robustness, "supplementary": supplementary}[args.command]()


if __name__ == "__main__":
    main()
