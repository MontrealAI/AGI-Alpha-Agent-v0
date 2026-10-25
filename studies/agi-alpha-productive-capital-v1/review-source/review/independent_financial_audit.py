"""Audit financial events/ledgers without importing or executing the model.

Amounts are reconstructed as integer millionths of USD from serialized records.
This checks modeled conservation and stated assumptions, not real cash/demand.
"""

from __future__ import annotations
import hashlib, json, math
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "economics/outputs"
checks = 0
failures = []
warnings = []


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def amount(x):
    return int((Decimal(str(x)) * 1000000).to_integral_value(rounding=ROUND_HALF_UP))


def portion(x, r):
    return int((Decimal(x) * Decimal(str(r))).to_integral_value(rounding=ROUND_HALF_UP))


def req(ok, label):
    global checks
    checks += 1
    if not ok:
        failures.append(label)


def near(a, b):
    return abs(float(a) - float(b)) <= 0.00000051


def key(row):
    return (row["scenario"], row["policy_fraction"])


def sum_amount(rows, field):
    return sum(amount(x.get(field, 0)) for x in rows)


cfg = read(ROOT / "protocol/economics_config.json")
summary = read(OUT / "summary.json")
ledger = read(OUT / "ledger.json")["rows"]
families = read(OUT / "family_results.json")["rows"]
events = [json.loads(line) for line in (OUT / "events.jsonl").read_text().splitlines()]
scenarios = {s["id"]: s for s in cfg["scenarios"]}
famnames = list(cfg["families"])
freeze = read(ROOT / "protocol/economics_freeze.json")
req(
    sha(ROOT / "protocol/economics_config.json") == freeze["files"]["protocol/economics_config.json"],
    "assumptions frozen identity",
)
for name, value in read(OUT / "manifest.json")["files"].items():
    req(sha(OUT / name) == value, "economic output manifest " + name)
prov = summary["provenance"]
req(prov["config_sha256"] == sha(ROOT / "protocol/economics_config.json"), "config provenance")
req(prov["bridge_sha256"] == sha(ROOT / "outputs/economics_bridge.json"), "bridge provenance")
req(prov["engine_sha256"] == sha(ROOT / "economics/run_economics.py"), "engine provenance")
req(
    prov["business_outputs"] == "SIMULATED"
    and prov["complete_live_agent_cost_usd"] is None
    and prov["live_paid_transactions"] == "NOT RUN",
    "evidence classification",
)
bridge = read(ROOT / "outputs/economics_bridge.json")
technical = read(ROOT / "outputs/summary.json")
req(bridge["source_summary_sha256"] == sha(ROOT / "outputs/summary.json"), "technical bridge source binding")
req(
    [{k: v for k, v in row.items() if k != "accepted_joint"} for row in bridge["joint_rows"]]
    == technical["joint_rows"],
    "bridge carries exact joint rows plus alias",
)
req(all(row.get("accepted_joint") == row["accepted"] for row in bridge["joint_rows"]), "bridge accepted_joint alias")
tech = {(r["cycle"], r["arm"]): r for r in technical["joint_rows"]}
delta = (
    sum(
        tech[c, "conventional_cache"]["total_cpu_ms"] / tech[c, "conventional_cache"]["projects"]
        - tech[c, "flywheel"]["total_cpu_ms"] / tech[c, "flywheel"]["projects"]
        for c in [2, 3]
    )
    / 2
)
req(
    near(summary["measured_bridge"]["changed_cycle_cpu_saving_ms_per_joint_project_vs_conventional_cache"], delta),
    "CPU saving against strong incumbent",
)
req(summary["measured_bridge"]["quality_or_attention_saving_assumed"] is False, "no unsupported attention benefit")

by_cycle = defaultdict(list)
by_group = defaultdict(list)
family_by = defaultdict(list)
event_counts = Counter()
balances = {}
end_balances = {}
scheduled_collection = defaultdict(int)
scheduled_default = defaultdict(int)
scheduled_returns = defaultdict(int)
investment_dates = defaultdict(list)
columns = ["cash", "receivable", "collateral", "capital_asset", "payable"]
operating_events = {"fixed_business_setup_and_maintenance", "delivery_business_cost", "conversion_and_volatility_cost"}
for n, e in enumerate(events):
    group = key(e)
    cycle = e["cycle"]
    label = f'event {n} {e["event"]}'
    by_cycle[group + (cycle,)].append(e)
    by_group[group].append(e)
    event_counts[e["event"]] += 1
    b = balances.setdefault(group, [0] * 5)
    a = amount(e["amount_usd"])
    d = [amount(e[c + "_delta_usd"]) for c in columns]
    for i in range(5):
        b[i] += d[i]
    req(min(b) >= 0, label + " nonnegative accounts")
    req(b[0] == amount(e["cash_balance_usd"]), label + " running cash")
    req(e["evidence_class"] == "SIMULATED", label + " classification")
    end_balances[group + (cycle,)] = b.copy()
    kind = e["event"]
    expected = None
    if kind == "external_initial_capital":
        expected = [a, 0, 0, 0, 0]
        req(cycle == 0 and a == amount(cfg["initial_external_capital_usd"]), label + " financing source")
    elif kind == "invoice_worker_entitlement":
        expected = [0, a, 0, 0, 0]
        req(
            a + amount(e["other_participant_allocation_usd"]) == amount(e["customer_gross_invoice_usd"]),
            label + " customer/worker separation",
        )
        s = scenarios[group[0]]
        route = cfg["routes"][s["route"]]
        price = cfg["families"][e["family"]]["price_usd"] * s.get("price_multiplier", 1)
        req(
            amount(e["customer_gross_invoice_usd"]) == amount(price)
            and a == portion(amount(price), route["worker_entitlement_fraction"]),
            label + " configured entitlement",
        )
        default = portion(a, cfg["business"]["default_fraction"])
        collectible = a - default
        weights = s.get("collection_weights", cfg["business"]["receivable_collection_weights"])
        allocated = 0
        for lag, w in enumerate(weights):
            due = collectible - allocated if lag == len(weights) - 1 else portion(collectible, w)
            allocated += due
            scheduled_collection[group + (cycle + lag, e["family"])] += due
        scheduled_default[group + (cycle + len(weights) - 1, e["family"])] += default
    elif kind == "external_worker_collection":
        expected = [a, -a, 0, 0, 0]
    elif kind == "customer_refund":
        expected = [-a, 0, 0, 0, 0]
    elif kind == "receivable_default_writeoff":
        expected = [0, -a, 0, 0, 0]
    elif kind == "worker_collateral_locked":
        expected = [-a, 0, a, 0, 0]
        s = scenarios[group[0]]
        route = cfg["routes"][s["route"]]
        scheduled_returns[group + (cycle + max(1, route["collateral_lock_cycles"]),)] += a
    elif kind == "collateral_principal_return":
        expected = [a, 0, -a, 0, 0]
    elif kind == "bounded_productive_investment":
        expected = [-a, 0, 0, a, 0]
        investment_dates[group].append((cycle, e["project"]))
    elif kind in ["capital_depreciation_non_cash", "expired_capability_writeoff"]:
        expected = [0, 0, 0, -a, 0]
    elif kind == "prior_operating_payable_payment":
        expected = [-a, 0, 0, 0, -a]
    elif kind in operating_events:
        expected = [d[0], 0, 0, 0, a + d[0]]
        req(-a <= d[0] <= 0, label + " payment/obligation split")
    else:
        req(False, label + " unknown event type")
    req(d == expected, label + " account classification")
for f in families:
    family_by[key(f) + (f["cycle"],)].append(f)


def reconstruct_plan(row, n):
    """Stated conservative order plan, independently from serialized config/bridge."""
    group = key(row)
    cycle = row["cycle"]
    s = scenarios[group[0]]
    route = cfg["routes"][s["route"]]
    biz = cfg["business"]
    rates = cfg["rates"]
    a = s.get("attention_multiplier", 1)
    op = amount(biz["fixed_operating_usd_per_cycle"]) + amount(
        biz["fixed_administration_minutes_per_cycle"] * rates["operator_usd_per_hour"] / 60
    )
    capacity = s.get("provider_attempt_limit", cfg["provider_attempt_limit"])
    existing_maint = 0
    existing_minutes = 0
    for bought, name in investment_dates[group]:
        p = cfg["projects"][name]
        if bought <= cycle < bought + p["life_cycles"]:
            if name == "extra-execution-block":
                capacity += p["extra_provider_attempts_per_cycle"]
            if name != cfg["next_cycle_plan"]["new_capability"]:
                existing_maint += amount(
                    p.get("maintenance_cash_usd_per_cycle", 0)
                    + p.get("maintenance_engineer_hours_per_cycle", 0) * rates["software_engineer_usd_per_hour"]
                )
                existing_minutes += p.get("maintenance_engineer_hours_per_cycle", 0) * 60
    op += existing_maint
    mins = biz["fixed_administration_minutes_per_cycle"] + existing_minutes
    coll = 0
    cpu = (
        tech[min(cycle - 1, 3), "conventional_cache"]["total_cpu_ms"]
        / tech[min(cycle - 1, 3), "conventional_cache"]["projects"]
        / 3
    )
    for f in famnames:
        x = cfg["families"][f]
        price = x["price_usd"] * s.get("price_multiplier", 1)
        per_attempt = amount(
            (
                x["supervision_minutes_per_attempt"] * a * rates["operator_usd_per_hour"]
                + x["verification_minutes_per_attempt"] * a * rates["reviewer_usd_per_hour"]
            )
            / 60
            + x["model_tool_usd_per_attempt"]
            + biz["storage_usd_per_attempt"]
            + cpu / 3600000 * biz["kernel_compute_usd_per_cpu_hour"]
        )
        per_order = amount(
            x["setup_minutes_per_order"] * a * rates["operator_usd_per_hour"] / 60
            + biz["acquisition_usd_per_order"]
            + s.get("gas_usd_per_order", route["gas_usd_per_order"])
        )
        retry = amount(x["retry_correction_minutes"] * a * rates["software_engineer_usd_per_hour"] / 60)
        support = amount(
            x["support_minutes_per_accepted"] * a * rates["operator_usd_per_hour"] / 60
            + biz["delivery_usd_per_accepted"]
            + biz["processing_fee_usd_per_accepted"]
            + price * biz["processing_fee_fraction"]
        )
        op += n * (per_order + 2 * per_attempt + retry + support)
        coll += n * amount(price * route["collateral_fraction"])
        mins += (
            n
            * a
            * (
                x["setup_minutes_per_order"]
                + 2 * (x["supervision_minutes_per_attempt"] + x["verification_minutes_per_attempt"])
                + x["retry_correction_minutes"]
                + x["support_minutes_per_accepted"]
            )
        )
    p = cfg["projects"][cfg["next_cycle_plan"]["new_capability"]]
    construction = amount(
        p.get("construction_cash_usd", 0)
        + p.get("construction_engineer_hours", 0) * rates["software_engineer_usd_per_hour"]
        + p.get("construction_verification_hours", 0) * rates["reviewer_usd_per_hour"]
        + p.get("construction_model_tool_usd", 0)
    )
    maint = amount(
        p.get("maintenance_cash_usd_per_cycle", 0)
        + p.get("maintenance_engineer_hours_per_cycle", 0) * rates["software_engineer_usd_per_hour"]
    )
    buildmins = 60 * (p.get("construction_engineer_hours", 0) + p.get("construction_verification_hours", 0))
    maintmins = 60 * p.get("maintenance_engineer_hours_per_cycle", 0)
    mins += buildmins + maintmins
    attempts = 2 * n * len(famnames)
    elapsed = (
        attempts * biz["elapsed_hours_per_attempt"]
        + (biz["fixed_administration_minutes_per_cycle"] + buildmins + maintmins + existing_minutes) / 60
    )
    tests = {
        "service_cash_budget": op + maint <= amount(cfg["per_cycle_cash_spend_budget_usd"]),
        "human_minutes": mins <= cfg["human_attention_budget_minutes"],
        "elapsed_hours": elapsed <= cfg["elapsed_budget_hours"],
        "provider_attempts": attempts <= capacity,
    }
    return {
        "op": op,
        "construction": construction,
        "coll": coll,
        "maint": maint,
        "total": op + construction + coll + maint,
        "minutes": mins,
        "elapsed": elapsed,
        "attempts": attempts,
        "capacity": capacity,
        "existing_maint": existing_maint,
        "checks": tests,
        "feasible": all(tests.values()),
    }


previous = {}
cumul = defaultdict(lambda: defaultdict(int))
group_rows = defaultdict(list)
resource_omissions = []
feasibility_diagnostics = []
for r in ledger:
    group = key(r)
    cycle = r["cycle"]
    tag = f"{group} c{cycle}"
    es = by_cycle[group + (cycle,)]
    fs = family_by[group + (cycle,)]
    group_rows[group].append(r)
    old = previous.get(group, [amount(cfg["initial_external_capital_usd"]), 0, 0, 0, 0])
    end = end_balances[group + (cycle,)]
    req(amount(r["opening_cash_usd"]) == old[0], tag + " opening cash")
    for i, name in enumerate(
        [
            "closing_cash_usd",
            "closing_receivables_usd",
            "closing_collateral_usd",
            "productive_asset_book_value_usd",
            "closing_payables_usd",
        ]
    ):
        req(amount(r[name]) == end[i], tag + " " + name)

    def ev(kind):
        return [e for e in es if e["event"] == kind]

    def total(kind, field="amount_usd"):
        return sum_amount(ev(kind), field)

    operating = [e for e in es if e["event"] in operating_events]
    paid = -sum_amount(operating, "cash_delta_usd") + total("prior_operating_payable_payment")
    incurred = sum_amount(operating, "amount_usd")
    collections = total("external_worker_collection")
    refund = total("customer_refund")
    invest = total("bounded_productive_investment")
    deposits = total("worker_collateral_locked")
    returns = total("collateral_principal_return")
    invoices = total("invoice_worker_entitlement")
    defaults = total("receivable_default_writeoff")
    dep = total("capital_depreciation_non_cash") + total("expired_capability_writeoff")
    amounts = {
        "gross_worker_collections_usd": collections,
        "refunds_usd": refund,
        "productive_investment_usd": invest,
        "collateral_deposit_usd": deposits,
        "collateral_return_usd": returns,
        "worker_entitlement_invoiced_usd": invoices,
        "default_writeoffs_usd": defaults,
        "paid_operating_cost_usd": paid,
        "incurred_operating_cost_usd": incurred,
        "noncash_depreciation_usd": dep,
        "customer_gross_invoiced_usd": sum_amount(ev("invoice_worker_entitlement"), "customer_gross_invoice_usd"),
    }
    for name, value in amounts.items():
        req(amount(r[name]) == value, tag + " event aggregate " + name)
    req(
        end[0] == old[0] + collections + returns - refund - paid - invest - deposits,
        tag + " cash conservation independently computed",
    )
    req(end[1] == old[1] + invoices - collections - defaults, tag + " receivable conservation independently computed")
    req(
        end[2] == old[2] + deposits - returns and end[3] == old[3] + invest - dep,
        tag + " collateral and capital conservation",
    )
    req(returns == scheduled_returns[group + (cycle,)], tag + " collateral lock duration")
    c = cumul[group]
    c["net_external"] += collections - refund
    c["operating_paid"] += paid
    c["invested"] += invest
    req(
        amount(r["cumulative_net_external_collections_usd"]) == c["net_external"]
        and amount(r["cumulative_operating_cash_paid_usd"]) == c["operating_paid"]
        and amount(r["cumulative_productive_investment_usd"]) == c["invested"],
        tag + " cumulative totals",
    )
    earned = c["net_external"] - c["operating_paid"] - (c["invested"] - invest) - end[4]
    reserve = portion(
        max(0, c["net_external"] - c["operating_paid"] - end[4]),
        cfg["business"]["cash_profit_obligation_reserve_fraction"],
    )
    available = max(
        0,
        min(
            earned - reserve, end[0] + invest - end[4] - reserve - amount(cfg["business"]["contingency_cash_floor_usd"])
        ),
    )
    budget = portion(available, group[1])
    req(
        amount(r["cumulative_earned_cash_before_reserves_usd"]) == earned,
        tag + " earned excludes seed and prior investment",
    )
    req(
        amount(r["obligation_cash_reserve_usd"]) == reserve
        and amount(r["available_preallocation_operating_surplus_usd"]) == available,
        tag + " reserves and available surplus",
    )
    req(
        amount(r["policy_budget_usd"]) == budget
        and amount(r["unspent_policy_budget_usd"]) == budget - invest
        and invest <= budget,
        tag + " bounded allocation",
    )
    plan_total = sum(
        amount(r[k])
        for k in [
            "next_plan_construction_usd",
            "next_plan_operating_working_capital_usd",
            "next_plan_new_collateral_usd",
            "next_plan_one_cycle_maintenance_usd",
        ]
    )
    req(plan_total == amount(r["next_plan_cash_need_usd"]), tag + " next plan components once")
    req(
        near(r["full_surplus_next_plan_coverage"], available / plan_total)
        and near(r["policy_next_plan_coverage"], budget / plan_total),
        tag + " financing coverage arithmetic",
    )
    req(
        near(r["construction_only_coverage"], available / amount(r["next_plan_construction_usd"])),
        tag + " construction-only coverage",
    )
    target = cfg["next_cycle_plan"]["accepted_sets"]
    plan = reconstruct_plan(r, target)
    req(
        plan["op"] == amount(r["next_plan_operating_working_capital_usd"])
        and plan["construction"] == amount(r["next_plan_construction_usd"])
        and plan["coll"] == amount(r["next_plan_new_collateral_usd"])
        and plan["maint"] == amount(r["next_plan_one_cycle_maintenance_usd"]),
        tag + " independently costed next plan",
    )
    req(
        r["next_plan_target_orders_per_family"] == target and r["next_plan_acceptance_guaranteed"] is False,
        tag + " order target not guaranteed accepted work",
    )
    req(
        r["next_plan_budget_checks"] == plan["checks"] and r["next_plan_budget_feasible"] == plan["feasible"],
        tag + " plan resource feasibility",
    )
    req(
        near(r["next_plan_estimated_human_minutes"], plan["minutes"])
        and near(r["next_plan_estimated_elapsed_hours"], plan["elapsed"])
        and r["next_plan_provider_attempts"] == plan["attempts"],
        tag + " full next plan time/attempts",
    )
    req(
        r["next_plan_available_provider_attempts"] == plan["capacity"]
        and amount(r["next_plan_existing_capacity_maintenance_usd"]) == plan["existing_maint"],
        tag + " surviving next-cycle capacity and maintenance",
    )
    req(
        r["next_plan_cash_coverage_is_executable_plan"] == (plan["feasible"] and available >= plan["total"]),
        tag + " financing separated from execution constraints",
    )
    feasible = [n for n in range(target + 1) if reconstruct_plan(r, n)["feasible"]]
    maximum = max(feasible) if feasible else None
    req(r["maximum_budget_feasible_target_orders_per_family"] == maximum, tag + " maximal smaller finite target")
    if maximum is not None:
        small = reconstruct_plan(r, maximum)
        req(
            amount(r["budget_feasible_smaller_plan_cash_need_usd"]) == small["total"]
            and near(r["budget_feasible_smaller_plan_surplus_coverage"], available / small["total"]),
            tag + " smaller-plan funding arithmetic",
        )
    req(
        set(r["purchased_projects"]) == {e["project"] for e in ev("bounded_productive_investment")},
        tag + " purchased offers",
    )
    for offer in r["offers"]:
        req(amount(offer["cost_usd"]) == offer["cost"], tag + " offer units " + offer["id"])
        if offer["purchased"]:
            req(
                offer["admissible"] and offer["policy_funding_eligible"] and offer["cost"] <= budget,
                tag + " investment admitted and budgeted " + offer["id"],
            )
            req(
                offer["npv_usd"] >= 0 or (group[0] == "compelled_research" and offer["id"] == "dependency-repair-v1"),
                tag + " negative-return research is explicit",
            )
        if offer["id"] == "discovery-process-pilot":
            req(
                not offer["purchased"] and not offer["admissible"] and offer["npv_usd"] is None,
                tag + " unknown discovery return remains hold",
            )
        if offer["id"] == "dependency-repair-v1" and group[0] != "compelled_research":
            req(not offer["admissible"], tag + " observed negative child return held")
    s = scenarios[group[0]]
    route = dict(cfg["routes"][s["route"]])
    route.update({k: s[k] for k in ["conversion_spread_fraction", "volatility_haircut_fraction"] if k in s})
    for family in famnames:
        family_events = [e for e in es if e.get("family") == family]
        got = sum_amount([e for e in family_events if e["event"] == "external_worker_collection"], "amount_usd")
        bad = sum_amount([e for e in family_events if e["event"] == "receivable_default_writeoff"], "amount_usd")
        req(
            got == scheduled_collection[group + (cycle, family)] and bad == scheduled_default[group + (cycle, family)],
            tag + " collection/default cohort " + family,
        )
        expected_refund = sum(
            portion(amount(e["amount_usd"]), cfg["business"]["refund_fraction_of_collections"])
            for e in family_events
            if e["event"] == "external_worker_collection"
        )
        req(
            sum_amount([e for e in family_events if e["event"] == "customer_refund"], "amount_usd") == expected_refund,
            tag + " refund " + family,
        )
        conversion = 0
        for e in family_events:
            if e["event"] == "external_worker_collection":
                x = amount(e["amount_usd"])
                haircut = portion(x, route["volatility_haircut_fraction"])
                conversion += haircut + portion(x - haircut, route["conversion_spread_fraction"])
        req(
            sum_amount([e for e in family_events if e["event"] == "conversion_and_volatility_cost"], "amount_usd")
            == conversion,
            tag + " conversion " + family,
        )
        f = next(f for f in fs if f["family"] == family)
        orders = sum(e["event"] == "delivery_business_cost" for e in family_events)
        accepted = sum(e["event"] == "invoice_worker_entitlement" for e in family_events)
        req(
            f["started_orders"] == orders and f["accepted"] == accepted and f["failed_orders"] == orders - accepted,
            tag + " family order/acceptance " + family,
        )
        req(
            orders <= f["attempts"] <= 2 * orders and f["failed_attempts"] == f["attempts"] - accepted,
            tag + " failed work accounting " + family,
        )
        req(
            r["accepted_by_family"][family] == accepted and r["attempts_by_family"][family] == f["attempts"],
            tag + " family ledger aggregate " + family,
        )
        if accepted:
            cost = amount(f["allocated_business_cost_usd"]) / 1000000 / accepted
            req(
                near(f["cost_per_accepted_usd"], cost)
                and near(f["internal_human_break_even_minutes"], 60 * cost / f["traditional_hourly_rate_usd"]),
                tag + " internal break-even " + family,
            )
        rate = cfg["rates"][cfg["families"][family]["traditional_rate_key"]]
        req(f["traditional_hourly_rate_usd"] == rate, tag + " sourced rate scenario " + family)
        buy = (
            cfg["families"][family]["price_usd"] * s.get("price_multiplier", 1)
            + cfg["families"][family]["customer_review_minutes_per_accepted"]
            * s.get("attention_multiplier", 1)
            * cfg["rates"]["operator_usd_per_hour"]
            / 60
        )
        req(near(f["customer_all_in_usd"], buy), tag + " customer full price " + family)
        req(near(f["customer_human_break_even_minutes"], 60 * buy / rate), tag + " customer break-even " + family)
        for q in f["customer_human_time_sensitivity"]:
            req(
                near(q["traditional_cost_usd"], q["traditional_minutes"] * rate / 60)
                and near(q["customer_saving_usd"], q["traditional_minutes"] * rate / 60 - buy),
                tag + " customer sensitivity " + family,
            )
        req(
            f["live_agent_cost_usd"] is None and f["evidence_class"] == "SIMULATED",
            tag + " family unknowns/classification " + family,
        )
    expected_conversion = 0
    for e in ev("invoice_worker_entitlement"):
        fraction = (1 - cfg["business"]["default_fraction"]) * (
            route["volatility_haircut_fraction"]
            + (1 - route["volatility_haircut_fraction"]) * route["conversion_spread_fraction"]
        )
        expected_conversion += portion(amount(e["amount_usd"]), fraction)
    req(
        sum_amount(fs, "allocated_business_cost_usd")
        == incurred - total("conversion_and_volatility_cost") + dep + expected_conversion,
        tag + " full-cost allocation conserved",
    )
    req(r["provider_attempts"] == sum(f["attempts"] for f in fs), tag + " provider budget counter")
    req(
        r["estimated_human_minutes"] <= cfg["human_attention_budget_minutes"]
        and r["estimated_elapsed_hours"] <= cfg["elapsed_budget_hours"],
        tag + " stated resource bounds",
    )
    req(r["evidence_class"] == "SIMULATED" and r["live_agent_cost_usd"] is None, tag + " ledger classification")
    base_attention = (
        sum(f["estimated_human_minutes"] for f in fs) + cfg["business"]["fixed_administration_minutes_per_cycle"]
    )
    extra = (
        60
        * (
            cfg["business"]["initial_integration_engineer_hours"]
            + cfg["business"]["unsuccessful_build_engineer_hours"]
            + cfg["business"]["initial_verification_hours"]
        )
        if cycle == 1
        else 0
    )
    extra += sum(
        cfg["projects"][p].get("maintenance_engineer_hours_per_cycle", 0) * 60 for p in r["active_capabilities"]
    )
    extra += sum(
        (
            cfg["projects"][p].get("construction_engineer_hours", 0)
            + cfg["projects"][p].get("construction_verification_hours", 0)
        )
        * 60
        for p in r["purchased_projects"]
    )
    if not math.isclose(r["estimated_human_minutes"], base_attention + extra, abs_tol=0.001):
        resource_omissions.append(
            {
                "scenario": group[0],
                "policy": group[1],
                "cycle": cycle,
                "reported": r["estimated_human_minutes"],
                "fully_specified_minutes": base_attention + extra,
            }
        )
    req(
        near(
            r["estimated_elapsed_hours"],
            r["provider_attempts"] * cfg["business"]["elapsed_hours_per_attempt"]
            + (cfg["business"]["fixed_administration_minutes_per_cycle"] + extra) / 60,
        ),
        tag + " specified elapsed allocation including construction",
    )
    if (
        r["next_plan_operating_working_capital_usd"] + r["next_plan_one_cycle_maintenance_usd"]
        > cfg["per_cycle_cash_spend_budget_usd"]
    ):
        feasibility_diagnostics.append(
            {
                "scenario": group[0],
                "policy": group[1],
                "cycle": cycle,
                "service_cash_required": r["next_plan_operating_working_capital_usd"]
                + r["next_plan_one_cycle_maintenance_usd"],
                "service_cash_ceiling": cfg["per_cycle_cash_spend_budget_usd"],
                "coverage": r["full_surplus_next_plan_coverage"],
            }
        )
    previous[group] = end
for s in summary["scenario_results"]:
    group = key(s)
    rs = group_rows[group]
    last = rs[-1]
    fs = [f for f in families if key(f) == group]
    for f in famnames:
        accepted = sum(x["accepted"] for x in fs if x["family"] == f)
        cost = sum_amount([x for x in fs if x["family"] == f], "allocated_business_cost_usd")
        req(
            s["accepted_by_family"][f] == accepted
            and s["attempts_by_family"][f] == sum(x["attempts"] for x in fs if x["family"] == f),
            "scenario family totals " + str(group) + " " + f,
        )
        req(
            (s["full_cost_per_accepted_by_family"][f] is None and not accepted)
            or near(s["full_cost_per_accepted_by_family"][f], cost / 1000000 / accepted),
            "scenario full cost " + str(group) + " " + f,
        )
    req(
        s["closing_cash_usd"] == last["closing_cash_usd"]
        and s["closing_receivables_usd"] == last["closing_receivables_usd"],
        "scenario account totals " + str(group),
    )
    req(
        s["available_operating_surplus_usd"] == last["available_preallocation_operating_surplus_usd"],
        "scenario surplus " + str(group),
    )
    req(
        s["self_financing_demonstrated"] is False
        and s["self_acceleration_demonstrated"] is False
        and s["live_agent_cost_usd"] is None,
        "scenario empirical limits " + str(group),
    )
counts = summary["counts"]
req(
    counts["events"] == len(events)
    and counts["ledger_rows"] == len(ledger)
    and counts["class_rows"] == len(families)
    and counts["scenario_policy_runs"] == len(by_group),
    "all record counts",
)
req(not resource_omissions, "all specified setup/construction/maintenance human minutes included")
report = {
    "status": "PASS" if not failures else "FAIL",
    "checks": checks,
    "failures": failures[:100],
    "failure_count": len(failures),
    "event_count": len(events),
    "scenario_policy_runs": len(by_group),
    "cycles": len(ledger),
    "family_rows": len(families),
    "engine_sha256": sha(ROOT / "economics/run_economics.py"),
    "config_sha256": sha(ROOT / "protocol/economics_config.json"),
    "results_summary_sha256": sha(OUT / "summary.json"),
    "base": summary["base"],
    "resource_omissions": resource_omissions,
    "next_plan_cash_ceiling_diagnostics": feasibility_diagnostics[:12],
    "cycles_with_next_plan_service_cash_above_ceiling": len(feasibility_diagnostics),
    "independence": "Separate reviewer implementation; imports and executes no economics producer. Same commission/session/model family/shared files. Reconciles serialized modeled events and assumptions; no external demand, real paid collections or full live Agent cost is verified.",
    "verification_scope": [
        "All event account classifications and five-account nonnegativity",
        "Cash, receivables, collateral and capital conservation",
        "Cohort collection/default/refund/conversion arithmetic",
        "Reserve, earned-surplus and bounded allocation identities",
        "Family counts, full-cost allocation, source-rate break-even arithmetic",
        "Observed bridge identity and CPU effect; source and output hashes",
        "Financing coverage arithmetic separated from resource feasibility",
    ],
    "limits": [
        "An event ledger can be conserved while economic assumptions are false.",
        "No independent source-to-bank or chain settlement attestation.",
        "No empirical validation of modeled human time, demand, pricing, collection or capacity vendor offers.",
        "This is an accounting/reconciliation audit, not a proof that all possible engine inputs are correct.",
    ],
}
(ROOT / "review/INDEPENDENT_FINANCIAL_AUDIT.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(
    json.dumps(
        {
            k: v
            for k, v in report.items()
            if k not in ["base", "resource_omissions", "next_plan_cash_ceiling_diagnostics"]
        },
        indent=2,
    )
)
raise SystemExit(0 if not failures else 1)
