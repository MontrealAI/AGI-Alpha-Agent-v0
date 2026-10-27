# SPDX-License-Identifier: Apache-2.0
"""Prospective reserve-assessment economics; all money and buyer behavior modeled."""

from __future__ import annotations

import argparse
import copy
import hashlib
import heapq
import json
import math
import random
import statistics
import unittest
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/commercial_protocol.json"
RESULTS = ROOT / "results"


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / name).write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def tri(rng: random.Random, values: list[float]) -> float:
    return rng.triangular(values[0], values[2], values[1])


@dataclass(frozen=True)
class Policy:
    family: str
    fee: int = 0
    deposit: float = 0

    @property
    def name(self) -> str:
        return f"{self.family}:{self.fee}:{self.deposit:g}"


def policies(config: dict[str, Any]) -> list[Policy]:
    grid = config["policy_grid"]
    return [Policy("none")] + [
        Policy(f, p, d) for f in grid["families"] for p in grid["fees_usd"] for d in grid["deposit_fractions"]
    ]


def token_budget(config: dict[str, Any]) -> float:
    return float(
        sum(
            (c["input_tokens"] * c["input_usd_per_million"] + c["output_tokens"] * c["output_usd_per_million"]) / 1e6
            for c in config["frontier_tokens"]["components"]
        )
    )


def world(config: dict[str, Any], seed: int) -> dict[str, Any]:
    """Draw one finite world before applying any policy; choices never change its draws."""
    rng = random.Random(seed)
    op, buyer, business, pipeline = (config[k] for k in ("operations", "buyer", "business", "pipeline"))
    n = rng.choices(pipeline["opportunity_counts"], pipeline["count_weights"])[0]
    privacy_share, consent_rate = tri(rng, buyer["privacy_binding_share"]), tri(rng, buyer["consent_rate"])
    result: dict[str, Any] = {
        "seed": seed,
        "startup_cost": tri(rng, config["startup"]["cost_low_central_high_usd"]),
        "startup_days": round(tri(rng, config["startup"]["duration_low_central_high_days"])),
        "readiness_probability": tri(rng, config["startup"]["readiness_probability_low_central_high"]),
        "gate1_draw": rng.random(),
        "gate2_draw": rng.random(),
        "success_probability": tri(rng, op["success_probability"]),
        "monthly_cost": tri(rng, business["monthly_cost_usd"]),
        "insurance": tri(rng, business["insurance_six_month_usd"]),
        "default_probability": tri(rng, config["payments"]["default_probability"]),
        "processing_fraction": tri(rng, config["payments"]["processing_fraction"]),
        "shocks": [rng.random() < op["common_failure_probability"] for _ in range(7)],
        "leads": [],
    }
    for i in range(n):
        arrival = rng.randint(*pipeline["arrivals_days"])
        exposure, changes = tri(rng, buyer["planning_exposure_usd"]), tri(rng, buyer["decision_change_probability"])
        value = tri(rng, buyer["confidence"]) * (
            exposure * changes + tri(rng, buyer["coordination_hours_saved"]) * buyer["owner_hourly_usd"]
        )
        if rng.random() < buyer["zero_information_value_probability"]:
            value = 0
        shares = [rng.uniform(0.5, 1.5) for _ in range(3)]
        shares = [s / sum(shares) for s in shares]
        lead = {
            "id": i,
            "arrival": arrival,
            "decision_day": arrival + round(tri(rng, pipeline["procurement_days"])),
            "acquisition": tri(rng, business["acquisition_per_opportunity_usd"]),
            "value": value,
            "shares": shares,
            "budget": tri(rng, buyer["sponsor_budget_usd"]),
            "privacy_binding": rng.random() < privacy_share,
            "consents": [rng.random() < consent_rate for _ in range(3)],
            "input_costs": [
                tri(rng, buyer["owner_input_hours"]) * buyer["owner_hourly_usd"] + tri(rng, buyer["owner_compute_usd"])
                for _ in range(3)
            ],
            "privacy_burdens": [tri(rng, buyer["owner_privacy_burden_usd"]) for _ in range(3)],
            "broker_cost": tri(rng, buyer["broker_analyst_hours"]) * buyer["owner_hourly_usd"]
            + tri(rng, buyer["broker_governance_hours"]) * buyer["counsel_hourly_usd"]
            + tri(rng, buyer["broker_tools_usd"]),
            "survival_draw": rng.random(),
            "acceptance_draw": rng.random(),
            "default_draw": rng.random(),
            "duration": round(tri(rng, pipeline["delivery_days"])),
            "lateness": rng.choice(config["payments"]["additional_lateness_days"]),
            "token_multiplier": tri(rng, op["token_cost_multiplier"]),
            "retry": tri(rng, op["retry_multiplier"]),
        }
        for key in ("compute_usd", "verification_usd", "packaging_usd", "unknown_extra_usd", "support_usd", "tail_usd"):
            lead[key] = tri(rng, op[key])
        result["leads"].append(lead)
    return result


def buyer_choice(
    config: dict[str, Any], lead: dict[str, Any], policy: Policy, scenario: dict[str, float]
) -> dict[str, Any]:
    """Use stated beliefs and observable consent, never future success or cost draws."""
    b, op = config["buyer"], config["operations"]
    quality = b["belief_acceptance"] * (1 - op["common_failure_probability"] * (1 - op["common_failure_multiplier"]))
    value = lead["value"] * scenario.get("value_multiplier", 1)
    if policy.family == "conditional":
        value *= b["conditional_value_multiplier"]
    input_cost = sum(lead["input_costs"])
    privacy = sum(lead["privacy_burdens"])
    financing = (
        policy.fee * policy.deposit * b["cash_opportunity_rate_annual"] * config["pipeline"]["delivery_days"][2] / 365
    )
    agent_utility = quality * (value - policy.fee) - input_cost - privacy - financing
    broker_allowed = not lead["privacy_binding"] or scenario.get("zero_privacy", 0) == 1
    broker_cost = min(lead["broker_cost"], 1500) if scenario.get("zero_privacy", 0) else lead["broker_cost"]
    broker_utility = b["broker_belief_acceptance"] * (value - broker_cost) - input_cost if broker_allowed else -1e100
    member_ok = all(
        quality * value * share >= cost + burden
        for share, cost, burden in zip(lead["shares"], lead["input_costs"], lead["privacy_burdens"], strict=True)
    )
    consent = all(lead["consents"])
    chosen = consent and member_ok and policy.fee <= lead["budget"] and agent_utility >= max(0, broker_utility)
    return {
        "buy": chosen,
        "agent_utility": agent_utility,
        "broker_utility": broker_utility,
        "member_ok": member_ok,
        "all_consent": consent,
    }


def resource_cap(config: dict[str, Any], policy: Policy, scenario: dict[str, float]) -> float:
    """Declared ex-ante maximum; independent of per-job future cost realizations."""
    o = config["operations"]
    attempt = (
        token_budget(config) * o["token_cost_multiplier"][2] * scenario.get("model_price", 1)
        + o["compute_usd"][2]
        + o["verification_usd"][2]
    )
    extra = scenario.get("extra_per_job", 0) + scenario.get("human_hours", 0) * config["buyer"]["owner_hourly_usd"]
    return float(
        attempt * o["retry_multiplier"][2]
        + o["packaging_usd"][2]
        + o["unknown_extra_usd"][2]
        + o["support_usd"][2] * scenario.get("support_multiplier", 1)
        + o["tail_usd"][2]
        + o["failure_recovery_usd"]
        + extra
        + config["payments"]["refund_flat_usd"]
        + policy.fee * config["payments"]["processing_fraction"][2]
    )


def actual_resource_cost(config: dict[str, Any], lead: dict[str, Any], scenario: dict[str, float]) -> float:
    return float(
        (
            token_budget(config) * lead["token_multiplier"] * scenario.get("model_price", 1)
            + lead["compute_usd"]
            + lead["verification_usd"]
        )
        * lead["retry"]
        + lead["packaging_usd"]
        + lead["unknown_extra_usd"]
        + scenario.get("extra_per_job", 0)
        + scenario.get("human_hours", 0) * config["buyer"]["owner_hourly_usd"]
    )


def simulate(
    config: dict[str, Any],
    w: dict[str, Any],
    policy: Policy,
    scenario: dict[str, float] | None = None,
    assessment: bool = False,
    forced_retention: bool = False,
    keep_ledger: bool = False,
) -> dict[str, Any]:
    """Accrual/cash ledger with restricted deposits and finite own working funds."""
    s = scenario or {}
    horizon = config["horizon_days"]
    seed = config["seed_capital_usd"] * s.get("seed_multiplier", 1)
    cash = float(seed)
    revenue = receivables = credit_allowance = unearned = support_payable = processing_payable = accounts_payable = 0.0
    costs = {
        name: 0.0
        for name in (
            "A_startup",
            "A_delivery",
            "business",
            "acquisition",
            "insurance",
            "processing",
            "credit_loss",
            "B",
            "C",
            "incident",
        )
    }
    counts = {
        name: 0
        for name in (
            "qualified",
            "screened",
            "interested",
            "committed",
            "withdrawn",
            "booked",
            "accepted",
            "failed",
            "capacity_waits",
            "finance_waits",
            "unserved",
        )
    }
    status, start_day, ready_day, next_stage = "not_started", None, None, 0
    startup_spent = 0.0
    startup_cap = config["startup"]["approved_spend_cap_usd"] * s.get("startup_multiplier", 1)
    events: list[tuple[int, int, str, dict[str, Any]]] = []
    event_number = 0
    pending: list[dict[str, Any]] = []
    jobs: dict[int, dict[str, Any]] = {}
    bookings_by_month: dict[int, int] = {}
    seen, decisions, cancelled = set(), set(), set()
    ledger: list[dict[str, Any]] = []
    launch_evidence: dict[str, Any] | None = None
    insolvent = False
    leads = [] if s.get("zero_demand", 0) else w["leads"]
    if s.get("thin_pipeline", 0):
        leads = leads[:3]
    counts["qualified"] = len(leads) if policy.family != "none" else 0

    def log(day: int, kind: str, amount: float = 0.0, **detail: Any) -> None:
        if keep_ledger:
            ledger.append({"day": day, "event": kind, "amount_usd": amount, **detail})

    def pay(amount: float) -> None:
        nonlocal cash, accounts_payable, insolvent
        available_cash = max(0.0, cash - unearned)
        paid = min(amount, available_cash)
        cash -= paid
        accounts_payable += amount - paid
        if amount - paid > 1e-7:
            insolvent = True

    def charge(amount: float, bucket: str, day: int, kind: str) -> None:
        costs[bucket] += amount
        pay(amount)
        log(day, kind, amount)

    def schedule(day: int, kind: str, record: dict[str, Any]) -> None:
        nonlocal event_number
        event_number += 1
        heapq.heappush(events, (day, event_number, kind, record))

    def reservations(day: int) -> dict[str, float]:
        campaign = 0.0
        if policy.family != "none" and day <= config["pipeline"]["arrivals_days"][1]:
            campaign = (
                max(0, max(config["pipeline"]["opportunity_counts"]) - counts["screened"])
                * config["business"]["acquisition_per_opportunity_usd"][2]
                * s.get("acquisition_multiplier", 1)
            )
        startup = max(0.0, startup_cap - startup_spent) if status == "building" else 0.0
        insurance = config["business"]["insurance_six_month_usd"][2] if status == "building" else 0.0
        operating = (
            config["business"]["reserve_months"] * config["business"]["monthly_cost_usd"][2]
            if status in ("building", "ready") and day <= horizon
            else 0.0
        )
        return {
            "delivery_commitments": sum(j["cap"] for j in jobs.values()),
            "startup_commitments": startup,
            "insurance_reservation": insurance,
            "campaign_reservation": campaign,
            "operating_reserve": operating,
        }

    def available(day: int) -> float:
        return (
            cash - unearned - support_payable - processing_payable - accounts_payable - sum(reservations(day).values())
        )

    def begin(day: int, evidence: dict[str, Any]) -> bool:
        nonlocal status, start_day, launch_evidence
        required = (
            startup_cap
            + config["business"]["insurance_six_month_usd"][2]
            + config["business"]["reserve_months"] * config["business"]["monthly_cost_usd"][2]
        )
        if available(day) + 1e-8 < required:
            return False
        status, start_day, launch_evidence = "building", day, evidence
        log(day, "readiness_started", 0, **evidence)
        return True

    def snapshot(day: int) -> dict[str, Any]:
        expense = sum(costs.values())
        profit = revenue - expense
        equity = (
            cash + receivables - credit_allowance - unearned - support_payable - processing_payable - accounts_payable
        )
        if abs(equity - seed - profit) > 1e-6:
            raise AssertionError(f"Financial conservation failed: {equity - seed - profit}")
        if (
            cash < -1e-7
            or cash - unearned < -1e-7
            or min(receivables, credit_allowance, unearned, support_payable, processing_payable, accounts_payable)
            < -1e-6
        ):
            raise AssertionError("Negative or spent restricted balance")
        contribution = revenue - costs["A_delivery"] - costs["processing"] - costs["credit_loss"]
        return {
            "day": day,
            "revenue": revenue,
            "total_cost": expense,
            "operating_profit": profit,
            "service_contribution": contribution,
            "cash": cash,
            "receivables": receivables,
            "credit_allowance": credit_allowance,
            "unearned_deposits": unearned,
            "support_payable": support_payable,
            "processing_payable": processing_payable,
            "accounts_payable": accounts_payable,
            **reservations(day),
            "available_funds": available(day),
            "available_gain_excluding_seed": available(day) - seed,
            "costs": dict(costs),
            "counts": dict(counts),
            "startup_status": status,
            "ready_day": ready_day,
            "insolvent": insolvent,
            "financial_conservation_error": equity - seed - profit,
        }

    if policy.family == "direct":
        begin(0, {"family": "direct", "committed_customers": 0})
    report: dict[str, Any] | None = None
    for day in range(horizon + config["tail_days"] + 1):
        while events and events[0][0] <= day:
            _, _, kind, item = heapq.heappop(events)
            if kind == "support":
                support_payable -= item["amount"]
                pay(item["amount"])
                log(day, "support_settled", item["amount"])
            elif kind == "invoice":
                amount, fee, allowance = item["amount"], item["fee"], item["allowance"]
                receivables -= amount
                credit_allowance -= allowance
                costs["credit_loss"] -= allowance
                processing_payable -= fee
                if item["default"]:
                    costs["credit_loss"] += amount
                    costs["processing"] -= fee
                    log(day, "invoice_default_fee_released", amount, fee_released=fee)
                else:
                    cash += amount
                    pay(fee)
                    log(day, "invoice_collected", amount, fee=fee)
            elif kind == "delivery":
                job = jobs.pop(item["id"])
                lead = job["lead"]
                charge(actual_resource_cost(config, lead, s), "A_delivery", day, "actual_delivery_resources")
                month = min(job["book_day"] // 30, len(w["shocks"]) - 1)
                success = s.get("acceptance_probability", w["success_probability"])
                success *= config["operations"]["common_failure_multiplier"] if w["shocks"][month] else 1
                accepted = lead["acceptance_draw"] < success
                deposit = policy.fee * policy.deposit
                unearned -= deposit
                if accepted:
                    counts["accepted"] += 1
                    revenue += policy.fee
                    support = lead["support_usd"] * s.get("support_multiplier", 1)
                    support_payable += support
                    costs["A_delivery"] += support
                    schedule(day + config["operations"]["support_due_days"], "support", {"amount": support})
                    charge(lead["tail_usd"], "A_delivery", day, "prepaid_settlement_archive")
                    balance = policy.fee - deposit
                    receivables += balance
                    fee = balance * w["processing_fraction"]
                    processing_payable += fee
                    costs["processing"] += fee
                    allowance = balance * config["payments"]["declared_credit_loss_allowance"]
                    credit_allowance += allowance
                    costs["credit_loss"] += allowance
                    if balance:
                        schedule(
                            day + config["payments"]["invoice_due_days"] + lead["lateness"],
                            "invoice",
                            {
                                "amount": balance,
                                "fee": fee,
                                "allowance": allowance,
                                "default": lead["default_draw"] < w["default_probability"],
                            },
                        )
                    log(day, "accepted_revenue", policy.fee, bit_outcome_not_a_delivery_failure=True)
                    if counts["accepted"] == 1 and (assessment or forced_retention):
                        charge(config["retention"]["assessment_usd"], "B", day, "rejected_retention_assessment")
                        if forced_retention:
                            charge(
                                config["retention"]["extraction_usd"]
                                + 6 * config["retention"]["monthly_maintenance_usd"],
                                "B",
                                day,
                                "forced_null_gain_retention_release_and_maintenance",
                            )
                else:
                    counts["failed"] += 1
                    cash -= deposit
                    charge(config["payments"]["refund_flat_usd"], "processing", day, "refund_processing")
                    charge(config["operations"]["failure_recovery_usd"], "A_delivery", day, "failed_delivery_recovery")
                    log(day, "deposit_refunded_no_revenue", deposit)
        if status == "building" and start_day is not None:
            stage_days = [start_day, start_day + w["startup_days"] // 2, start_day + w["startup_days"]]
            while next_stage < 3 and day >= stage_days[next_stage] and status == "building":
                expected_stage = (
                    w["startup_cost"]
                    * s.get("startup_multiplier", 1)
                    * config["startup"]["stage_fractions"][next_stage]
                )
                amount = min(expected_stage, max(0.0, startup_cap - startup_spent))
                charge(amount, "A_startup", day, "readiness_stage")
                startup_spent += amount
                if amount + 1e-7 < expected_stage:
                    status = "failed_budget"
                elif next_stage == 0 and w["gate1_draw"] >= config["startup"]["first_gate_probability"]:
                    status = "failed_specification"
                elif (
                    next_stage == 1
                    and w["gate2_draw"] >= w["readiness_probability"] / config["startup"]["first_gate_probability"]
                ):
                    status = "failed_qualification"
                elif next_stage == 2:
                    status, ready_day = "ready", day
                    charge(w["insurance"], "insurance", day, "underwriting_premium")
                next_stage += 1
        if policy.family != "none" and day <= horizon:
            for lead in leads:
                if lead["arrival"] <= day and lead["id"] not in seen:
                    seen.add(lead["id"])
                    counts["screened"] += 1
                    charge(
                        lead["acquisition"] * s.get("acquisition_multiplier", 1),
                        "acquisition",
                        day,
                        "qualified_opportunity_screening",
                    )
                if lead["decision_day"] <= day and lead["id"] not in decisions:
                    decisions.add(lead["id"])
                    if buyer_choice(config, lead, policy, s)["buy"]:
                        counts["interested"] += 1
                        pending.append(lead)
                        if policy.family == "conditional":
                            counts["committed"] += 1
                            log(day, "conditional_commitment_non_cash", 0, lead=lead["id"])
            if (
                policy.family == "conditional"
                and status == "not_started"
                and day <= config["commitments"]["launch_deadline_day"]
            ):
                cm = config["commitments"]
                expected_collected = (
                    len(pending)
                    * policy.fee
                    * cm["conservative_acceptance"]
                    * cm["conservative_collection"]
                    * cm["survival_probability"]
                    * (1 - cm["conservative_processing_fraction"])
                )
                forecast = (
                    config["startup"]["cost_low_central_high_usd"][1]
                    * s.get("startup_multiplier", 1)
                    * cm["startup_forecast_multiplier"]
                    + cm["fixed_forecast_months"] * config["business"]["monthly_cost_usd"][1]
                    + config["business"]["insurance_six_month_usd"][1]
                    + costs["acquisition"]
                    + len(pending)
                    * (
                        cm["delivery_forecast_usd_per_commitment"]
                        + s.get("extra_per_job", 0)
                        + s.get("human_hours", 0) * config["buyer"]["owner_hourly_usd"]
                    )
                )
                if pending and expected_collected >= forecast:
                    begin(
                        day,
                        {
                            "family": "conditional",
                            "committed_customers": len(pending),
                            "expected_collected_net_processing": expected_collected,
                            "conservative_total_cost_forecast": forecast,
                        },
                    )
            if status == "ready":
                for lead in list(pending):
                    if lead["id"] in cancelled:
                        continue
                    if lead["survival_draw"] >= config["commitments"]["survival_probability"]:
                        pending.remove(lead)
                        cancelled.add(lead["id"])
                        counts["withdrawn"] += 1
                        continue
                    if day + config["pipeline"]["delivery_days"][2] > horizon:
                        continue
                    month = day // 30
                    if (
                        len(jobs) >= config["pipeline"]["max_concurrent"]
                        or bookings_by_month.get(month, 0) >= config["pipeline"]["max_bookings_per_30_days"]
                    ):
                        counts["capacity_waits"] += 1
                        continue
                    cap = resource_cap(config, policy, s)
                    deposit_fee = policy.fee * policy.deposit * config["payments"]["processing_fraction"][2]
                    invocation = (
                        config["retention"]["invocation_usd"] if forced_retention and counts["accepted"] > 0 else 0
                    )
                    if available(day) + 1e-8 < cap + deposit_fee + invocation:
                        counts["finance_waits"] += 1
                        continue
                    pending.remove(lead)
                    counts["booked"] += 1
                    bookings_by_month[month] = bookings_by_month.get(month, 0) + 1
                    deposit = policy.fee * policy.deposit
                    cash += deposit
                    unearned += deposit
                    charge(deposit * w["processing_fraction"], "processing", day, "deposit_processing")
                    if invocation:
                        charge(invocation, "B", day, "optional_retention_invocation")
                    jobs[lead["id"]] = {"lead": lead, "cap": cap, "book_day": day}
                    schedule(day + lead["duration"], "delivery", {"id": lead["id"]})
                    log(day, "booking_deposit_restricted", deposit, lead=lead["id"], reserved_cap=cap)
                charge(w["monthly_cost"] / 30, "business", day, "fixed_operating_cost")
            if s.get("incident_loss", 0) and day == 120 and status == "ready":
                charge(s["incident_loss"], "incident", day, "common_operating_incident")
                status = "suspended_incident"
        snapshot(day)
        if day == horizon:
            counts["unserved"] = len(pending)
            report = snapshot(day)
    if events or jobs:
        raise AssertionError("Settlement tail did not close all jobs/invoices/support")
    if report is None:
        raise AssertionError("Missing reporting snapshot")
    settled = snapshot(horizon + config["tail_days"])
    return {
        "seed": w["seed"],
        "policy": asdict(policy),
        "launch_evidence": launch_evidence,
        "day180": report,
        "settled": settled,
        "ledger": ledger if keep_ledger else None,
    }


def distribution(values: list[float]) -> dict[str, float]:
    values = sorted(values)

    def quantile(p: float) -> float:
        i = p * (len(values) - 1)
        lo, hi = math.floor(i), math.ceil(i)
        return values[lo] + (values[hi] - values[lo]) * (i - lo)

    mean = statistics.mean(values)
    se = statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0.0
    return {
        "mean": mean,
        "p05": quantile(0.05),
        "median": quantile(0.5),
        "p95": quantile(0.95),
        "positive_fraction": sum(x > 0 for x in values) / len(values),
        "mean_mc95_low": mean - 1.96 * se,
        "mean_mc95_high": mean + 1.96 * se,
    }


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    stages: dict[str, Any] = {}
    for stage in ("day180", "settled"):
        records = [r[stage] for r in runs]
        keys = (
            "revenue",
            "total_cost",
            "operating_profit",
            "service_contribution",
            "cash",
            "receivables",
            "credit_allowance",
            "unearned_deposits",
            "support_payable",
            "processing_payable",
            "accounts_payable",
            "delivery_commitments",
            "startup_commitments",
            "insurance_reservation",
            "campaign_reservation",
            "operating_reserve",
            "available_funds",
            "available_gain_excluding_seed",
        )
        data: dict[str, Any] = {key: distribution([float(r[key]) for r in records]) for key in keys}
        data["counts_mean"] = {k: statistics.mean(r["counts"][k] for r in records) for k in records[0]["counts"]}
        data["costs_mean"] = {k: statistics.mean(r["costs"][k] for r in records) for k in records[0]["costs"]}
        data["readiness_fraction"] = sum(r["ready_day"] is not None for r in records) / len(records)
        data["insolvent_fraction"] = sum(r["insolvent"] for r in records) / len(records)
        accepted = sum(r["counts"]["accepted"] for r in records)
        data["full_cost_per_accepted_ratio"] = sum(r["total_cost"] for r in records) / accepted if accepted else None
        ready = [r for r in records if r["ready_day"] is not None]
        data["conditional_on_readiness"] = {
            "worlds": len(ready),
            "mean_service_contribution": statistics.mean(r["service_contribution"] for r in ready) if ready else None,
            "mean_full_venture_profit": statistics.mean(r["operating_profit"] for r in ready) if ready else None,
            "mean_accepted": statistics.mean(r["counts"]["accepted"] for r in ready) if ready else None,
        }
        stages[stage] = data
    return {"worlds": len(runs), **stages}


def develop(config: dict[str, Any]) -> None:
    seeds = config["seeds"]
    worlds = [
        world(config, seed)
        for seed in range(seeds["development_start"], seeds["development_start"] + seeds["development_count"])
    ]
    rows: list[dict[str, Any]] = []
    for p in policies(config):
        rows.append(
            {"policy": asdict(p), "name": p.name, "summary": summarize([simulate(config, w, p) for w in worlds])}
        )

    def objective(row: dict[str, Any]) -> float:
        return float(row["summary"]["day180"]["available_gain_excluding_seed"]["mean"])

    selected = {
        f: max([r for r in rows if r["policy"]["family"] == f], key=objective)["policy"]
        for f in ("direct", "conditional")
    }
    overall = max(rows, key=objective)["policy"]
    exploration = {
        "evidence": "Modeled development; every candidate retained",
        "seed_start": seeds["development_start"],
        "worlds": len(worlds),
        "policies": rows,
        "selected_by_family": selected,
        "overall_selected": overall,
    }
    write("economics_development.json", exploration)
    freeze = {
        "source_sha256": sha(Path(__file__)),
        "protocol_sha256": sha(CONFIG),
        "proposal_sha256": sha(ROOT / "evidence/commercial_design_proposal.json"),
        "development_sha256": sha(RESULTS / "economics_development.json"),
        "selected_by_family": selected,
        "overall_selected": overall,
        "confirmation_seed_start": seeds["confirmation_start"],
        "confirmation_worlds": seeds["confirmation_count"],
        "confirmation_opened": False,
        "optional_retention_decision": "reject; expected incremental benefit zero; assessment-only result reported separately",
        "freeze_rule": "Fresh outcome access requires these exact bindings; corrections must preserve old artifacts and use new seeds.",
    }
    write("economics_freeze.json", freeze)
    print(
        json.dumps(
            {
                "selected_by_family": selected,
                "overall_selected": overall,
                "development_means": [
                    {
                        "policy": r["name"],
                        "profit": r["summary"]["day180"]["operating_profit"]["mean"],
                        "funds_gain": objective(r),
                        "accepted": r["summary"]["day180"]["counts_mean"]["accepted"],
                    }
                    for r in rows
                ],
            },
            indent=2,
        )
    )


def confirm(config: dict[str, Any]) -> None:
    frozen = read(RESULTS / "economics_freeze.json")
    for key, path in (
        ("source_sha256", Path(__file__)),
        ("protocol_sha256", CONFIG),
        ("proposal_sha256", ROOT / "evidence/commercial_design_proposal.json"),
        ("development_sha256", RESULTS / "economics_development.json"),
    ):
        if sha(path) != frozen[key]:
            raise ValueError("Freeze mismatch: " + key)
    start, n = frozen["confirmation_seed_start"], frozen["confirmation_worlds"]
    worlds = [world(config, seed) for seed in range(start, start + n)]
    chosen = {family: Policy(**p) for family, p in frozen["selected_by_family"].items()}
    chosen["no_launch"] = Policy("none")
    runs = {label: [simulate(config, w, p) for w in worlds] for label, p in chosen.items()}
    summaries = {label: summarize(values) for label, values in runs.items()}
    compact_columns = [
        "seed",
        "profit",
        "revenue",
        "cost",
        "accepted",
        "booked",
        "cash",
        "available_funds",
        "ready",
        "launched",
    ]
    compact = {
        label: [
            [
                r["seed"],
                r["day180"]["operating_profit"],
                r["day180"]["revenue"],
                r["day180"]["total_cost"],
                r["day180"]["counts"]["accepted"],
                r["day180"]["counts"]["booked"],
                r["day180"]["cash"],
                r["day180"]["available_funds"],
                r["day180"]["ready_day"] is not None,
                r["launch_evidence"] is not None,
            ]
            for r in values
        ]
        for label, values in runs.items()
    }
    write(
        "economics_confirmation.json",
        {
            "evidence": "All modeled; actual collections zero; not a paid customer experiment",
            "freeze_sha256": sha(RESULTS / "economics_freeze.json"),
            "seed_start": start,
            "worlds": n,
            "policies": {k: asdict(v) for k, v in chosen.items()},
            "overall_selected": frozen["overall_selected"],
            "summaries": summaries,
            "compact_world_columns": compact_columns,
            "all_worlds": compact,
        },
    )
    scenarios: dict[str, dict[str, float]] = {
        "zero_privacy_value_cheaper_broker": {"zero_privacy": 1},
        "zero_opportunities": {"zero_demand": 1},
        "three_opportunities": {"thin_pipeline": 1},
        "half_value": {"value_multiplier": 0.5},
        "model_price_4x": {"model_price": 4},
        "model_price_10x": {"model_price": 10},
        "acceptance_065": {"acceptance_probability": 0.65},
        "startup_at_human_central_ratio": {"startup_multiplier": 91445.77 / 25907.73},
        "unknown_extra_2000": {"extra_per_job": 2000},
        "unknown_extra_5000": {"extra_per_job": 5000},
        "expert_8h": {"human_hours": 8},
        "expert_24h": {"human_hours": 24},
        "acquisition_3x": {"acquisition_multiplier": 3},
        "support_3x": {"support_multiplier": 3},
        "incident_25000": {"incident_loss": 25000},
        "incident_100000": {"incident_loss": 100000},
        "seed_40000": {"seed_multiplier": 2 / 3},
    }
    sensitivity: dict[str, Any] = {}
    for name, scenario in scenarios.items():
        sensitivity[name] = {}
        for family in ("direct", "conditional"):
            trial = summarize([simulate(config, w, chosen[family], scenario) for w in worlds])
            sensitivity[name][family] = {
                "profit": trial["day180"]["operating_profit"],
                "funds_gain": trial["day180"]["available_gain_excluding_seed"],
                "accepted_mean": trial["day180"]["counts_mean"]["accepted"],
                "ready_fraction": trial["day180"]["readiness_fraction"],
                "insolvent_fraction": trial["day180"]["insolvent_fraction"],
            }
    write(
        "economics_sensitivity.json",
        {
            "status": "Prospectively declared parameter stresses; same fresh seeds, no retuning",
            "scenarios": scenarios,
            "results": sensitivity,
        },
    )
    retained = {}
    for family in ("direct", "conditional"):
        base = runs[family]
        assessed = [simulate(config, w, chosen[family], assessment=True) for w in worlds]
        forced = [simulate(config, w, chosen[family], forced_retention=True) for w in worlds]
        retained[family] = {
            "assessment_then_reject": summarize(assessed),
            "forced_zero_gain_retention": summarize(forced),
            "assessment_paired_profit_delta": distribution(
                [
                    a["day180"]["operating_profit"] - b["day180"]["operating_profit"]
                    for a, b in zip(assessed, base, strict=True)
                ]
            ),
            "forced_paired_profit_delta": distribution(
                [
                    a["day180"]["operating_profit"] - b["day180"]["operating_profit"]
                    for a, b in zip(forced, base, strict=True)
                ]
            ),
        }
    write(
        "economics_retention.json",
        {
            "primary": "Reuse of paid-for A product, no additional B or C; same-information ordinary library ties by construction. No newly learned algorithm or measured E+ gain.",
            "comparison": retained,
            "break_even_saving_per_use": {str(n): 50 + 3200 / n for n in (3, 6, 12)},
            "negative_benefit_scenario": "Any negative incremental benefit worsens the forced-retention case; no positive transfer gain has been measured.",
            "operational_alpha": "Same-model U/E and E+/E mission performance unmeasured; no numerical gain assigned.",
        },
    )
    example = next(
        (w for w, r in zip(worlds, runs["direct"], strict=True) if r["day180"]["counts"]["accepted"] > 0), worlds[0]
    )
    write("economics_example_ledger.json", simulate(config, example, chosen["direct"], keep_ledger=True))
    summary = {
        "overall_selected": frozen["overall_selected"],
        "family_policies": frozen["selected_by_family"],
        "results": summaries,
        "actual_customer_collections_usd": 0,
        "actual_complete_research_cost_usd": None,
        "mandatory_scope": "Conditional-on-readiness service contribution and full startup-inclusive venture results are distinct.",
        "sensitivity_means": {
            name: {family: x["profit"]["mean"] for family, x in families.items()}
            for name, families in sensitivity.items()
        },
        "retention_break_even_saving_per_use": {str(n): 50 + 3200 / n for n in (3, 6, 12)},
        "frontier_gain": "Unmeasured",
    }
    write("economics_summary.json", summary)
    print(
        json.dumps(
            {
                "overall_selected": frozen["overall_selected"],
                "family_results": {
                    family: {
                        "profit": data["day180"]["operating_profit"],
                        "accepted": data["day180"]["counts_mean"]["accepted"],
                        "readiness": data["day180"]["readiness_fraction"],
                        "conditional_on_readiness": data["day180"]["conditional_on_readiness"],
                    }
                    for family, data in summaries.items()
                },
            },
            indent=2,
        )
    )


class AccountingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = read(CONFIG)
        self.w = world(self.config, 42)
        self.w.update(
            startup_cost=0,
            startup_days=0,
            readiness_probability=0.9,
            gate1_draw=0,
            gate2_draw=0,
            monthly_cost=0,
            insurance=0,
            success_probability=1,
            default_probability=0,
            processing_fraction=0.005,
            shocks=[False] * 7,
        )
        lead = self.w["leads"][0]
        lead.update(
            id=0,
            arrival=0,
            decision_day=0,
            acquisition=0,
            value=1e6,
            budget=1e6,
            privacy_binding=True,
            consents=[True] * 3,
            input_costs=[0] * 3,
            privacy_burdens=[0] * 3,
            survival_draw=0,
            acceptance_draw=0,
            default_draw=1,
            duration=2,
            lateness=60,
            token_multiplier=0,
            retry=1,
            compute_usd=0,
            verification_usd=0,
            packaging_usd=0,
            unknown_extra_usd=0,
            support_usd=30,
            tail_usd=0,
        )
        self.w["leads"] = [lead]
        self.policy = Policy("direct", 12000, 0.5)

    def test_token_envelope(self) -> None:
        self.assertEqual(token_budget(self.config), 180)

    def test_acceptance_and_settlement_conservation(self) -> None:
        result = simulate(self.config, self.w, self.policy)
        self.assertEqual(result["settled"]["counts"]["accepted"], 1)
        self.assertAlmostEqual(result["settled"]["operating_profit"], 12000 - 60 - 30)
        self.assertAlmostEqual(result["settled"]["receivables"], 0)

    def test_late_invoice_fee_accrual(self) -> None:
        self.config["payments"]["declared_credit_loss_allowance"] = 0
        self.w["leads"][0]["arrival"] = self.w["leads"][0]["decision_day"] = 150
        result = simulate(self.config, self.w, self.policy)
        self.assertEqual(result["day180"]["receivables"], 6000)
        self.assertEqual(result["day180"]["processing_payable"], 30)
        self.assertAlmostEqual(result["day180"]["operating_profit"], result["settled"]["operating_profit"])

    def test_default_releases_unpaid_processing_fee(self) -> None:
        self.w["default_probability"] = 1
        self.w["leads"][0]["default_draw"] = 0
        result = simulate(self.config, self.w, self.policy)
        self.assertAlmostEqual(result["settled"]["costs"]["processing"], 30)
        self.assertAlmostEqual(result["settled"]["costs"]["credit_loss"], 6000)

    def test_full_failure_refunds_deposit(self) -> None:
        self.w["success_probability"] = 0
        result = simulate(self.config, self.w, Policy("direct", 12000, 1))
        self.assertEqual(result["settled"]["revenue"], 0)
        self.assertEqual(result["settled"]["unearned_deposits"], 0)
        self.assertAlmostEqual(result["settled"]["cash"], 60000 - 60 - 25 - 100)

    def test_deposits_cannot_fund_launch(self) -> None:
        self.config["seed_capital_usd"] = 1
        result = simulate(self.config, self.w, Policy("direct", 18000, 1))
        self.assertEqual(result["settled"]["counts"]["booked"], 0)
        self.assertIsNone(result["launch_evidence"])

    def test_no_launch_is_zero_new_spend(self) -> None:
        result = simulate(self.config, self.w, Policy("none"))
        self.assertEqual(result["day180"]["operating_profit"], 0)
        self.assertEqual(result["day180"]["available_gain_excluding_seed"], 0)

    def test_assessment_is_charged_once(self) -> None:
        result = simulate(self.config, self.w, self.policy, assessment=True, keep_ledger=True)
        self.assertEqual(result["settled"]["costs"]["B"], 500)
        self.assertEqual(sum(r["event"] == "rejected_retention_assessment" for r in result["ledger"]), 1)
        absent = simulate(self.config, self.w, Policy("none"), assessment=True)
        self.assertEqual(absent["settled"]["costs"]["B"], 0)

    def test_failed_readiness_gate_stops_after_sixty_percent(self) -> None:
        self.w.update(startup_cost=10000, readiness_probability=0.45, gate2_draw=0.99)
        result = simulate(self.config, self.w, self.policy)
        self.assertEqual(result["settled"]["costs"]["A_startup"], 6000)
        self.assertEqual(result["settled"]["startup_status"], "failed_qualification")

    def test_cost_cap_does_not_inspect_future_cost_draw(self) -> None:
        low = copy.deepcopy(self.w)
        high = copy.deepcopy(self.w)
        high["leads"][0].update(
            token_multiplier=700 / 180,
            retry=2,
            compute_usd=400,
            verification_usd=240,
            packaging_usd=180,
            unknown_extra_usd=2000,
        )
        a = simulate(self.config, low, self.policy, keep_ledger=True)
        b = simulate(self.config, high, self.policy, keep_ledger=True)
        self.assertEqual(
            [r for r in a["ledger"] if r["event"] == "booking_deposit_restricted"],
            [r for r in b["ledger"] if r["event"] == "booking_deposit_restricted"],
        )
        self.assertNotEqual(a["settled"]["operating_profit"], b["settled"]["operating_profit"])

    def test_non_cash_commitments_and_failed_threshold_cost(self) -> None:
        self.w["leads"][0]["acquisition"] = 500
        result = simulate(self.config, self.w, Policy("conditional", 6000, 0.5), keep_ledger=True)
        self.assertEqual(result["settled"]["counts"]["committed"], 1)
        self.assertIsNone(result["launch_evidence"])
        self.assertEqual(result["settled"]["operating_profit"], -500)
        self.assertEqual(result["settled"]["cash"], 59500)

    def test_price_can_remove_purchase(self) -> None:
        lead = copy.deepcopy(self.w["leads"][0])
        lead["value"] = 15000
        self.assertTrue(buyer_choice(self.config, lead, Policy("direct", 12000, 0.5), {})["buy"])
        self.assertFalse(buyer_choice(self.config, lead, Policy("direct", 18000, 0.5), {})["buy"])
        lead["privacy_binding"] = False
        lead["broker_cost"] = 1500
        self.assertFalse(buyer_choice(self.config, lead, Policy("direct", 6000, 0.5), {})["buy"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("self-test", "develop", "confirm"))
    args = parser.parse_args()
    config = read(CONFIG)
    if args.stage == "self-test":
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(AccountingTests)
        )
        if not result.wasSuccessful():
            raise SystemExit(1)
    elif args.stage == "develop":
        develop(config)
    else:
        confirm(config)


if __name__ == "__main__":
    main()
