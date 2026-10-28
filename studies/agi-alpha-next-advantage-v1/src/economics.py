# SPDX-License-Identifier: Apache-2.0
"""Matched, non-anticipating enterprise simulation; no live sales are represented."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODES = ("beta", "v1", "v2", "composed", "beta_plus")
OFFERS = ("nominal", "robust")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def uniform(seed: int, *key: Any) -> float:
    return (int.from_bytes(hashlib.sha256(canonical([seed, *key])).digest()[:8], "big") + 0.5) / 2**64


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


@dataclass(frozen=True)
class Policy:
    name: str
    retain: bool = False
    share: bool = False
    gym: bool = False
    compose: bool = False
    new_offering: bool = False
    stronger_beta: bool = False
    library: bool = False
    expand: bool = False


POLICIES = (
    Policy("beta"),
    Policy("private", retain=True, gym=True),
    Policy("shared", retain=True, share=True),
    Policy("shared_gym", retain=True, share=True, gym=True, compose=True),
    Policy("opportunity", retain=True, share=True, gym=True, compose=True, new_offering=True),
    Policy("beta_open", new_offering=True),
    Policy("private_open", retain=True, gym=True, compose=True, new_offering=True),
    Policy("library", retain=True, share=True, gym=True, compose=True, new_offering=True, library=True),
    Policy("beta_upgrade", new_offering=True, stronger_beta=True),
    Policy(
        "opportunity_upgrade", retain=True, share=True, gym=True, compose=True, new_offering=True, stronger_beta=True
    ),
    Policy("surplus_expansion", retain=True, share=True, gym=True, compose=True, new_offering=True, expand=True),
)

DEFAULTS = {
    "days": 90,
    "capital_usd": 8000.0,
    "reserve_usd": 1800.0,
    "daily_capacity_hours": 4.0,
    "daily_overhead_usd": 38.0,
    "lead_cost_usd": 38.0,
    "cad_to_usd_assumed": 0.73,
    "human_reference_cad": {"nominal": 3220.0, "robust": 7217.0},
    "reference_hours": {"nominal": {"intermediate": 16, "senior": 4}, "robust": {"intermediate": 26, "senior": 17}},
    "human_rates_cad": {"intermediate": 154, "senior": 189},
    "price_multipliers": [0.35, 0.5, 0.65, 0.8, 0.95, 1.1],
    "daily_lead_cap": 6,
    "lead_probability_prior": 0.22,
    "robust_fraction_prior": 0.3,
    "buyer_intercept_prior": 1.4,
    "price_sensitivity": 3.0,
    "quality_sensitivity": 1.2,
    "residual_event_probability": 0.1,
    "residual_hours_per_event": 1.5,
    "human_rate_usd": 95,
    "failure_correction_fraction": 0.45,
    "correction_recovery_probability": 0.22,
    "refund_processing_usd": 18.0,
    "collection_delay_days": 7,
    "maintenance_period_days": 21,
    "maintenance_usd": 35.0,
    "obsolete_after_days": 55,
    "decision_margin": 0.5,
    "native_unit": "US dollars; conditional simulation, no actual revenue",
    "frontier_nominal": {
        "astra_input_tokens": 240000,
        "astra_output_tokens": 70000,
        "terra_input_tokens": 150000,
        "terra_output_tokens": 30000,
    },
    "frontier_robust_scale": 2.3,
    "model_prices_usd_per_million": {"astra_input": 10, "astra_output": 50, "terra_input": 1, "terra_output": 5},
    "delivery_tools_usd": {"nominal": 22.0, "robust": 45.0},
    "automated_acceptance_usd": {"nominal": 12.0, "robust": 24.0},
    "production_hours": {"nominal": 0.75, "robust": 1.6},
    "cpu_usd_per_hour": 3.0,
    "investment_costs": {"retain": 120.0, "share": 90.0, "gym": 420.0, "compose": 180.0, "launch": 850.0},
    "investment_hours": {"retain": 0.7, "share": 0.5, "gym": 2.5, "compose": 1.0, "launch": 3.0},
    "offer_validation_usd": 150.0,
    "expansion_usd": 1400.0,
    "expansion_daily_usd": 16.0,
    "common_automation_setup_usd": 2400.0,
    "campaign_success_probability": {"retain": 0.85, "share": 0.95, "gym": 0.65, "compose": 0.75, "launch": 0.85},
    "campaign_probability_basis": "unsupported assumptions; prospective replication/packaging can fail despite the executed research artifact",
    "transfer_reliability": 0.9,
    "systemic_success_prior": 0.975,
    "stop_after_days": 21,
}

SCENARIOS = {
    "central": {
        "lead_probability": 0.22,
        "buyer_intercept": 1.4,
        "cost_scale": 1.0,
        "trust_shift": 0.0,
        "correlated_failure": 0.025,
        "reference_scale": 1.0,
    },
    "thin_demand": {
        "lead_probability": 0.045,
        "buyer_intercept": 0.2,
        "cost_scale": 1.0,
        "trust_shift": -0.5,
        "correlated_failure": 0.025,
        "reference_scale": 1.0,
    },
    "costly_delivery": {
        "lead_probability": 0.22,
        "buyer_intercept": 1.4,
        "cost_scale": 6.0,
        "trust_shift": 0.0,
        "correlated_failure": 0.025,
        "reference_scale": 1.0,
    },
    "adverse_market": {
        "lead_probability": 0.10,
        "buyer_intercept": 0.6,
        "cost_scale": 3.0,
        "trust_shift": -0.7,
        "correlated_failure": 0.10,
        "reference_scale": 0.6,
    },
    "congested": {
        "lead_probability": 0.70,
        "buyer_intercept": 1.4,
        "cost_scale": 1.0,
        "trust_shift": 0.0,
        "correlated_failure": 0.025,
        "reference_scale": 1.0,
    },
    "fast_obsolescence": {
        "lead_probability": 0.22,
        "buyer_intercept": 1.4,
        "cost_scale": 1.0,
        "trust_shift": 0.0,
        "correlated_failure": 0.025,
        "reference_scale": 1.0,
        "obsolete_after_days": 14,
    },
    "fragile_learning": {
        "lead_probability": 0.22,
        "buyer_intercept": 1.4,
        "cost_scale": 1.0,
        "trust_shift": 0.0,
        "correlated_failure": 0.025,
        "reference_scale": 1.0,
        "campaign_probability_scale": 0.4,
        "transfer_reliability": 0.55,
    },
}


def normalize_calibration(raw: dict[str, Any]) -> dict[str, Any]:
    offers = raw.get("offerings", raw.get("offers", raw))
    result: dict[str, Any] = {}
    for offer in OFFERS:
        modes = offers[offer].get("modes", offers[offer])
        result[offer] = {}
        for mode in MODES:
            row = modes[mode]
            records = row["confirmation_records"]
            if not records:
                raise ValueError("Real numerical confirmation evidence is required")
            result[offer][mode] = {
                "development_n": int(row["development_n"]),
                "development_successes": int(row["development_successes"]),
                "confirmation_records": sorted(records, key=lambda x: x["case_id"]),
            }
    return result


def prior(cal: dict[str, Any], offer: str, mode: str) -> tuple[float, float]:
    row = cal[offer][mode]
    p = (row["development_successes"] + 1) / (row["development_n"] + 2)
    return 12 * p, 12 * (1 - p)


def buyer_probability(intercept: float, ratio: float, quality: float, cfg: dict[str, Any]) -> float:
    return logistic(
        intercept + cfg["price_sensitivity"] * (0.75 - ratio) + cfg["quality_sensitivity"] * (quality - 0.75)
    )


def unit_cost(offer: str, cfg: dict[str, Any], cost_scale: float = 1.0) -> dict[str, float]:
    tok = cfg["frontier_nominal"]
    rates = cfg["model_prices_usd_per_million"]
    model = sum(tok[k + "_tokens"] * v / 1e6 for k, v in rates.items())
    model *= cfg["frontier_robust_scale"] if offer == "robust" else 1.0
    return {
        "model": model * cost_scale,
        "tools": cfg["delivery_tools_usd"][offer] * cost_scale,
        "acceptance": cfg["automated_acceptance_usd"][offer] * cost_scale,
        "compute": cfg["production_hours"][offer] * cfg["cpu_usd_per_hour"] * cost_scale,
    }


def best_quote(
    offer: str, p: float, intercept: float, cfg: dict[str, Any], cost_scale: float, reference_scale: float = 1.0
) -> tuple[float, float, float]:
    reference = cfg["human_reference_cad"][offer] * cfg["cad_to_usd_assumed"] * reference_scale
    direct = sum(unit_cost(offer, cfg, cost_scale).values())
    residual = cfg["residual_event_probability"] * cfg["residual_hours_per_event"] * cfg["human_rate_usd"]
    full = (
        direct
        + residual * cost_scale
        + (1 - p) * (direct * cfg["failure_correction_fraction"] + cfg["refund_processing_usd"])
    )
    effective_p = p + (1 - p) * cfg["correction_recovery_probability"]
    candidates = []
    for ratio in cfg["price_multipliers"]:
        price = round(reference * ratio, 2)
        conversion = buyer_probability(intercept, ratio, p, cfg)
        expected = conversion * (effective_p * price - full)
        candidates.append((expected, price, conversion))
    return max(candidates)


def simulate(
    policy: Policy, scenario: dict[str, Any], seed: int, cal: dict[str, Any], cfg: dict[str, Any], record: bool = False
) -> dict[str, Any]:
    """Use past public observations and development priors; hidden outcomes stay outside decisions."""
    cash, collections, earned = cfg["capital_usd"], 0.0, 0.0
    buckets = {"A": 0.0, "B": 0.0, "C": 0.0}
    events: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    pending: list[tuple[int, float]] = []
    flags = {k: False for k in ("retain", "share", "gym", "compose", "launch", "expand")}
    dates: dict[str, int] = {}
    attempts: dict[str, int] = {"nominal": 0, "robust": 0}
    accepted: dict[str, int] = {"nominal": 0, "robust": 0}
    stats = {
        "leads": 0,
        "quoted": 0,
        "buyer_human": 0,
        "buyer_defer": 0,
        "buyer_decline": 0,
        "capacity_declined": 0,
        "unpaid_failures": 0,
        "corrections": 0,
        "human_events": 0,
        "retired": 0,
        "stopped_day": cfg["days"],
        "job_hours": 0.0,
        "investment_hours": 0.0,
        "accepted_source_jobs": 0,
    }
    belief = {(o, m): list(prior(cal, o, m)) for o in OFFERS for m in MODES}
    systemic_belief = [20 * cfg["systemic_success_prior"], 20 * (1 - cfg["systemic_success_prior"])]
    intercept = cfg["buyer_intercept_prior"]
    seen_days = 0
    shadow = 0.0
    sequence = 0
    low_cash = cash

    def charge(day: int, amount: float, bucket: str, activity: str, category: str, job_id: str | None = None) -> None:
        nonlocal cash, sequence
        amount = round(float(amount), 6)
        if amount < 0 or not math.isfinite(amount):
            raise ValueError("Invalid expense")
        cash -= amount
        buckets[bucket] += amount
        sequence += 1
        if record:
            events.append(
                {
                    "event_id": f"{policy.name}:{seed}:{sequence}",
                    "day": day,
                    "bucket": bucket,
                    "amount_usd": amount,
                    "activity": activity,
                    "category": category,
                    "job_id": job_id,
                }
            )

    def probability(offer: str, mode: str) -> float:
        a, b = belief[(offer, mode)]
        return a / (a + b) * systemic_belief[0] / sum(systemic_belief)

    def modes_for(agent: int, offer: str) -> list[str]:
        modes = ["beta_plus" if policy.stronger_beta else "beta"]
        if flags["retain"] and (agent == 0 or flags["share"]):
            modes.append("v1")
            if flags["gym"]:
                modes.append("v2")
            if flags["compose"] and offer == "robust":
                modes.append("composed")
        return modes

    def choose_mode(agent: int, offer: str) -> tuple[str, float, float, float]:
        quotes = [
            (
                m,
                *best_quote(
                    offer, probability(offer, m), intercept, cfg, scenario["cost_scale"], scenario["reference_scale"]
                ),
            )
            for m in modes_for(agent, offer)
        ]
        return max(quotes, key=lambda x: x[1])

    charge(
        0,
        cfg["common_automation_setup_usd"],
        "A",
        "common intake, tooling and verification automation setup",
        "overhead",
    )
    for day in range(cfg["days"]):
        for due, amount in list(pending):
            if due <= day:
                cash += amount
                collections += amount
                pending.remove((due, amount))
        if cash < cfg["reserve_usd"] * 0.25:
            stats["stopped_day"] = day
            break
        if day >= cfg["stop_after_days"]:
            observed_rate = (6 * cfg["lead_probability_prior"] * 10 + stats["leads"]) / (10 + seen_days)
            continuing_value = max(choose_mode(a, "nominal")[1] for a in (0, 1))
            if flags["launch"]:
                continuing_value = max(continuing_value, max(choose_mode(a, "robust")[1] for a in (0, 1)))
            if observed_rate * (max(0.0, continuing_value) - cfg["lead_cost_usd"]) < cfg["daily_overhead_usd"]:
                stats["stopped_day"] = day
                actions.append(
                    {
                        "day": day,
                        "action": "stop",
                        "reason": "posterior continuation value below avoidable operating cost",
                    }
                )
                break
        overhead = cfg["daily_overhead_usd"] + (cfg["expansion_daily_usd"] if flags["expand"] else 0)
        charge(day, overhead, "A", "operating overhead and intake automation", "overhead")
        capacity = cfg["daily_capacity_hours"] * (2 if flags["expand"] else 1)
        seen_days += 1
        observed_rate = (6 * cfg["lead_probability_prior"] * 10 + stats["leads"]) / (10 + seen_days)
        horizon = min(cfg["days"] - day, cfg["obsolete_after_days"])
        if flags["retain"] and day - dates["retain"] >= scenario.get("obsolete_after_days", cfg["obsolete_after_days"]):
            for key in ("retain", "share", "gym", "compose"):
                flags[key] = False
            stats["retired"] += 1
            actions.append({"day": day, "action": "retire", "reason": "declared evidence validity expired"})
        if flags["retain"] and day > dates["retain"] and (day - dates["retain"]) % cfg["maintenance_period_days"] == 0:
            charge(
                day, cfg["maintenance_usd"] * scenario["cost_scale"], "B", "retained capability maintenance", "overhead"
            )
        investments: list[tuple[float, str, float]] = []
        beta_mode = "beta_plus" if policy.stronger_beta else "beta"
        eligible_actions = []
        if policy.retain and not flags["retain"] and stats["accepted_source_jobs"] >= 8 and "retain" not in dates:
            eligible_actions.append(("retain", "v1", 0.5))
        if flags["retain"] and policy.share and not flags["share"] and "share" not in dates:
            eligible_actions.append(("share", "v2" if flags["gym"] else "v1", 0.5))
        if flags["retain"] and policy.gym and not flags["gym"] and "gym" not in dates:
            eligible_actions.append(("gym", "v2", 1.0 if flags["share"] else 0.5))
        if flags["gym"] and policy.compose and not flags["compose"] and policy.new_offering and "compose" not in dates:
            eligible_actions.append(("compose", "composed", 1.0 if flags["share"] else 0.5))
        for action, target, fraction in eligible_actions:
            offer = "robust" if action == "compose" else "nominal"
            current_mode = choose_mode(0 if action != "share" else 1, offer)[0]
            old = best_quote(
                offer,
                probability(offer, current_mode),
                intercept,
                cfg,
                scenario["cost_scale"],
                scenario["reference_scale"],
            )[0]
            new = best_quote(
                offer, probability(offer, target), intercept, cfg, scenario["cost_scale"], scenario["reference_scale"]
            )[0]
            relevance = cfg["robust_fraction_prior"] if offer == "robust" else 1 - cfg["robust_fraction_prior"]
            gain = max(0.0, new - old) * observed_rate * horizon * relevance * fraction
            gain *= cfg["campaign_success_probability"][action]
            cost = cfg["investment_costs"][action] * scenario["cost_scale"]
            duration = cfg["investment_hours"][action]
            net = gain - cost - shadow * duration
            if net > cfg["decision_margin"] * cost:
                investments.append((net / duration, action, cost))
        if policy.new_offering and not flags["launch"] and "launch" not in dates:
            _, robust_value, _, _ = choose_mode(0, "robust")
            spare_fraction = max(
                0.1, 1 - observed_rate * cfg["production_hours"]["nominal"] / cfg["daily_capacity_hours"]
            )
            gain = max(0.0, robust_value) * observed_rate * horizon * cfg["robust_fraction_prior"] * spare_fraction
            gain *= cfg["campaign_success_probability"]["launch"]
            cost = (cfg["investment_costs"]["launch"] + cfg["offer_validation_usd"]) * scenario["cost_scale"]
            net = gain - cost - shadow * cfg["investment_hours"]["launch"]
            if net > cfg["decision_margin"] * cost:
                investments.append((net / cfg["investment_hours"]["launch"], "launch", cost))
        earned_surplus = max(0.0, cash - cfg["capital_usd"] - cfg["reserve_usd"])
        if (
            policy.expand
            and not flags["expand"]
            and day >= 14
            and stats["capacity_declined"] >= 5
            and earned_surplus >= cfg["expansion_usd"]
        ):
            gain = (cfg["days"] - day) * max(0.0, shadow - cfg["expansion_daily_usd"])
            if gain > cfg["expansion_usd"] * (1 + cfg["decision_margin"]):
                investments.append((gain / 2, "expand", cfg["expansion_usd"]))
        if investments:
            _, action, cost = max(investments)
            duration = cfg["investment_hours"].get(action, 2.0)
            if capacity >= duration and cash - cost >= cfg["reserve_usd"]:
                if action == "launch":
                    charge(
                        day,
                        cfg["investment_costs"][action] * scenario["cost_scale"],
                        "C",
                        "new-offering development",
                        "model",
                    )
                    charge(
                        day,
                        cfg["offer_validation_usd"] * scenario["cost_scale"],
                        "B",
                        "independent new-offering assessment",
                        "acceptance",
                    )
                else:
                    charge(
                        day,
                        cost,
                        "C" if action in ("gym", "compose", "expand") else "B",
                        f"optional {action}",
                        "compute" if action == "gym" else "overhead",
                    )
                campaign_p = cfg["campaign_success_probability"].get(action, 1.0) * scenario.get(
                    "campaign_probability_scale", 1.0
                )
                campaign_success = uniform(seed, action, "campaign") < campaign_p
                flags[action] = campaign_success
                dates[action] = day
                capacity -= duration
                stats["investment_hours"] += duration
                actions.append(
                    {
                        "day": day,
                        "action": action,
                        "cash_cost_usd": cost,
                        "capacity_hours": duration,
                        "candidate_accepted": campaign_success,
                        "estimated_net_value_usd": max(investments)[0] * duration,
                    }
                )
        opportunities = []
        for slot in range(cfg["daily_lead_cap"]):
            if uniform(seed, day, slot, "arrival") >= scenario["lead_probability"]:
                continue
            stats["leads"] += 1
            offer = "robust" if uniform(seed, day, slot, "offering") < cfg["robust_fraction_prior"] else "nominal"
            agent = 0 if uniform(seed, day, slot, "recipient") < 0.5 else 1
            if cash - cfg["lead_cost_usd"] < cfg["reserve_usd"] * 0.25:
                continue
            charge(day, cfg["lead_cost_usd"], "A", "qualified lead acquisition and automated scoping", "overhead")
            if offer == "robust" and not flags["launch"]:
                continue
            mode, value, price, conversion = choose_mode(agent, offer)
            hours = cfg["production_hours"][offer]
            opportunities.append((value / hours, slot, offer, agent, mode, price, conversion, hours))
        for value_per_hour, slot, offer, agent, mode, price, conversion, hours in sorted(opportunities, reverse=True):
            if value_per_hour <= 0:
                continue
            if hours > capacity:
                stats["capacity_declined"] += 1
                shadow = 0.8 * shadow + 0.2 * value_per_hour
                continue
            expected_cost = sum(unit_cost(offer, cfg, scenario["cost_scale"]).values())
            worst_cost = (
                expected_cost * (1 + cfg["failure_correction_fraction"])
                + cfg["residual_hours_per_event"] * cfg["human_rate_usd"] * scenario["cost_scale"]
                + cfg["refund_processing_usd"]
            )
            if mode not in ("beta", "beta_plus") and agent == 1:
                worst_cost += 3 * scenario["cost_scale"]
            if cash - worst_cost < cfg["reserve_usd"] * 0.25:
                continue
            stats["quoted"] += 1
            reference = cfg["human_reference_cad"][offer] * cfg["cad_to_usd_assumed"] * scenario["reference_scale"]
            true_conversion = buyer_probability(
                scenario["buyer_intercept"] + scenario["trust_shift"], price / reference, probability(offer, mode), cfg
            )
            sale = uniform(seed, day, slot, "buyer") < true_conversion
            intercept = max(-3.0, min(3.0, intercept + 0.07 * (int(sale) - conversion)))
            if not sale:
                choice = uniform(seed, day, slot, "outside")
                stats["buyer_human" if choice < 0.4 else "buyer_defer" if choice < 0.75 else "buyer_decline"] += 1
                continue
            capacity -= hours
            stats["job_hours"] += hours
            attempts[offer] += 1
            job_id = f"{day}-{slot}-{offer}-{agent}"
            for category, amount in unit_cost(offer, cfg, scenario["cost_scale"]).items():
                charge(day, amount, "A", f"complete {offer} delivery including useful-work learning", category, job_id)
            if mode not in ("beta", "beta_plus") and agent == 1:
                charge(
                    day,
                    3.0 * scenario["cost_scale"],
                    "B",
                    "authenticated research capability invocation",
                    "network",
                    job_id,
                )
            if uniform(seed, day, slot, "residual") < cfg["residual_event_probability"]:
                stats["human_events"] += 1
                charge(
                    day,
                    cfg["residual_hours_per_event"] * cfg["human_rate_usd"] * scenario["cost_scale"],
                    "A",
                    "residual data-owner exception or dispute",
                    "human",
                    job_id,
                )
            records = cal[offer][mode]["confirmation_records"]
            if mode not in ("beta", "beta_plus") and agent == 1:
                reliability = scenario.get("transfer_reliability", cfg["transfer_reliability"])
                if uniform(seed, day, slot, "transfer") > reliability:
                    records = cal[offer][beta_mode]["confirmation_records"]
            index = min(len(records) - 1, int(uniform(seed, day, slot, "case") * len(records)))
            case = records[index]
            success = bool(case["accepted"])
            belief[(offer, mode)][0 if success else 1] += 1
            systemic_ok = uniform(seed, day // 7, "correlated_error") >= scenario["correlated_failure"]
            systemic_belief[0 if systemic_ok else 1] += 1
            success = success and systemic_ok
            if not success:
                stats["corrections"] += 1
                charge(
                    day,
                    expected_cost * cfg["failure_correction_fraction"],
                    "A",
                    "failed delivery correction",
                    "correction",
                    job_id,
                )
                success = uniform(seed, day, slot, "recovery") < cfg["correction_recovery_probability"]
            if success:
                accepted[offer] += 1
                if offer == "nominal" and agent == 0:
                    stats["accepted_source_jobs"] += 1
                earned += price
                pending.append((day + cfg["collection_delay_days"], price))
            else:
                stats["unpaid_failures"] += 1
                charge(
                    day,
                    cfg["refund_processing_usd"],
                    "A",
                    "failed acceptance: no collection; refund administration",
                    "correction",
                    job_id,
                )
            if record:
                actions.append(
                    {
                        "day": day,
                        "action": "production",
                        "job_id": job_id,
                        "offer": offer,
                        "agent": agent,
                        "mode": mode,
                        "case_id": case["case_id"],
                        "accepted": success,
                        "price_usd": price,
                        "collection_day": day + cfg["collection_delay_days"] if success else None,
                    }
                )
        low_cash = min(low_cash, cash)
        if not opportunities:
            shadow *= 0.9
    expenses = sum(buckets.values())
    receivables = sum(x[1] for x in pending)
    profit = earned - expenses
    cash_profit = collections - expenses
    obligations = 0.0
    available = max(0.0, cash - cfg["reserve_usd"] - obligations)
    earned_available = max(0.0, available - cfg["capital_usd"])
    if abs(cash - (cfg["capital_usd"] + collections - expenses)) > 1e-6:
        raise AssertionError("Cash identity failed")
    output = {
        "policy": policy.name,
        "seed": seed,
        "collections_usd": collections,
        "earned_usd": earned,
        "receivables_usd": receivables,
        "expenses_usd": expenses,
        "profit_usd": profit,
        "cash_profit_usd": cash_profit,
        "ending_cash_usd": cash,
        "available_usd": available,
        "earned_available_usd": earned_available,
        "capital_usd": cfg["capital_usd"],
        "reserve_usd": cfg["reserve_usd"],
        "obligations_usd": obligations,
        "minimum_cash_usd": low_cash,
        "buckets": buckets,
        "attempts": attempts,
        "accepted": accepted,
        "actions": actions,
        "stats": stats,
        "events": events,
        "technical_throughput": sum(accepted.values()),
        "quality_adjusted_productivity": sum(accepted.values())
        / max(1.0, stats["job_hours"] + stats["investment_hours"]),
    }
    return output


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "profit_usd",
        "cash_profit_usd",
        "collections_usd",
        "expenses_usd",
        "available_usd",
        "earned_available_usd",
        "technical_throughput",
        "quality_adjusted_productivity",
        "receivables_usd",
    )
    output: dict[str, Any] = {}
    for metric in metrics:
        values = np.array([r[metric] for r in rows])
        output[metric] = {
            "mean": float(values.mean()),
            "q05": float(np.quantile(values, 0.05)),
            "q95": float(np.quantile(values, 0.95)),
            "se": float(values.std(ddof=1) / math.sqrt(len(values))),
        }
    output["loss_probability"] = float(np.mean([r["profit_usd"] < 0 for r in rows]))
    output["stop_probability"] = float(np.mean([r["stats"]["stopped_day"] < DEFAULTS["days"] for r in rows]))
    output["liquidity_stop_probability"] = float(
        np.mean([r["minimum_cash_usd"] < r["reserve_usd"] * 0.25 for r in rows])
    )
    output["mean_by_bucket"] = {b: float(np.mean([r["buckets"][b] for r in rows])) for b in ("A", "B", "C")}
    output["mean_actions"] = {
        a: float(np.mean([sum(x["action"] == a for x in r["actions"]) for r in rows]))
        for a in ("retain", "share", "gym", "compose", "launch", "expand", "retire")
    }
    output["mean_accepted"] = {o: float(np.mean([r["accepted"][o] for r in rows])) for o in OFFERS}
    output["mean_attempts"] = {o: float(np.mean([r["attempts"][o] for r in rows])) for o in OFFERS}
    return output


def run(calibration_path: Path, output: Path, repetitions: int = 128) -> dict[str, Any]:
    cal = normalize_calibration(json.loads(calibration_path.read_text()))
    cfg = json.loads((ROOT / "config/economics.json").read_text())
    protocol = json.loads((ROOT / "config/economic_protocol.json").read_text())
    actual_source = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if protocol["source_sha256"] != actual_source:
        raise ValueError("Economic policy source differs from pre-execution freeze")
    output.mkdir(parents=True, exist_ok=True)
    summaries, runs, comparisons = [], [], []
    representative = None
    for scenario_name, scenario in SCENARIOS.items():
        matched: dict[str, list[dict[str, Any]]] = {}
        for policy in POLICIES:
            rows = [
                simulate(
                    policy,
                    scenario,
                    70000 + seed,
                    cal,
                    cfg,
                    record=scenario_name == "central" and policy.name == "opportunity" and seed == 0,
                )
                for seed in range(repetitions)
            ]
            matched[policy.name] = rows
            summaries.append({"scenario": scenario_name, "policy": policy.name, "n": repetitions, **summarize(rows)})
            for row in rows:
                if row["events"]:
                    representative = row
                runs.append(
                    {k: v for k, v in row.items() if k not in ("events", "actions")} | {"scenario": scenario_name}
                )
        for intervention, control in (
            ("private", "beta"),
            ("shared", "beta"),
            ("shared_gym", "shared"),
            ("opportunity", "shared_gym"),
            ("opportunity", "beta_open"),
            ("opportunity", "private_open"),
            ("opportunity", "library"),
            ("opportunity_upgrade", "beta_upgrade"),
            ("surplus_expansion", "opportunity"),
        ):
            differences = np.array(
                [a["profit_usd"] - b["profit_usd"] for a, b in zip(matched[intervention], matched[control])]
            )
            mean = float(differences.mean())
            se = float(differences.std(ddof=1) / np.sqrt(repetitions))
            comparisons.append(
                {
                    "scenario": scenario_name,
                    "intervention": intervention,
                    "control": control,
                    "mean_profit_difference_usd": mean,
                    "paired_mc_95": [mean - 1.96 * se, mean + 1.96 * se],
                    "probability_outperforming": float(np.mean(differences > 0)),
                    "interpretation": "Monte Carlo uncertainty conditional on fixed assumptions; not market uncertainty",
                }
            )
        print(f"completed matched scenario {scenario_name}", flush=True)
    frontier = []
    for demand in (0.025, 0.06, 0.12, 0.22, 0.4, 0.7):
        for cost in (1.0, 3.0, 6.0, 12.0):
            scenario = {**SCENARIOS["central"], "lead_probability": demand, "cost_scale": cost}
            for name in ("beta_open", "opportunity"):
                pol = next(p for p in POLICIES if p.name == name)
                rows = [simulate(pol, scenario, 90000 + s, cal, cfg) for s in range(max(32, repetitions // 2))]
                frontier.append(
                    {
                        "daily_expected_leads": 6 * demand,
                        "cost_scale": cost,
                        "policy": name,
                        "mean_profit_usd": float(np.mean([r["profit_usd"] for r in rows])),
                        "loss_probability": float(np.mean([r["profit_usd"] < 0 for r in rows])),
                        "gym_rate": float(np.mean([any(a["action"] == "gym" for a in r["actions"]) for r in rows])),
                        "mean_throughput": float(np.mean([r["technical_throughput"] for r in rows])),
                    }
                )
    results = {
        "status": "conditional simulated enterprise; actual numerical confirmation supplies technical outcomes",
        "repetitions": repetitions,
        "horizon_days": cfg["days"],
        "summaries": summaries,
        "paired_comparisons": comparisons,
        "frontier": frontier,
        "configuration_sha256": hashlib.sha256(canonical(cfg)).hexdigest(),
        "economic_source_sha256": actual_source,
        "calibration_sha256": hashlib.sha256(calibration_path.read_bytes()).hexdigest(),
        "no_future_information": "Decision functions receive development priors and prior observations; confirmation is consulted only after commitment",
        "uncertainty": "Paired intervals describe stochastic simulation variation, not confidence in unsupported market assumptions",
    }
    (output / "economic_results.json").write_text(json.dumps(results, indent=2) + "\n")
    with (output / "enterprise_runs.jsonl").open("w") as stream:
        for row in runs:
            stream.write(json.dumps(row) + "\n")
    if representative is not None:
        (output / "representative.json").write_text(json.dumps(representative, indent=2) + "\n")
        native = {
            "events": representative["events"],
            "collections_usd": f"{representative['collections_usd']:.6f}",
            "capital_usd": cfg["capital_usd"],
            "reserve_usd": cfg["reserve_usd"],
            "label": "central opportunity seed 70000, simulated amounts / executed native accounting",
            "artifact_digest": hashlib.sha256(calibration_path.read_bytes()).hexdigest(),
        }
        (output / "native_input.json").write_text(json.dumps(native, indent=2) + "\n")
    with (output / "economic_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "scenario",
                "policy",
                "profit",
                "collections",
                "expenses",
                "available",
                "throughput",
                "loss_probability",
            ],
        )
        writer.writeheader()
        for r in summaries:
            writer.writerow(
                {
                    "scenario": r["scenario"],
                    "policy": r["policy"],
                    "profit": r["profit_usd"]["mean"],
                    "collections": r["collections_usd"]["mean"],
                    "expenses": r["expenses_usd"]["mean"],
                    "available": r["available_usd"]["mean"],
                    "throughput": r["technical_throughput"]["mean"],
                    "loss_probability": r["loss_probability"],
                }
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path, default=ROOT / "evidence/numerical/economic_calibration.json")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/economics")
    parser.add_argument("--repetitions", type=int, default=128)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        (ROOT / "config/economics.json").write_text(json.dumps(DEFAULTS, indent=2) + "\n")
        protocol = {
            "version": 1,
            "stage": "pre-economic-confirmation",
            "date": "2026-10-27",
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "policy_specifications": [asdict(p) for p in POLICIES],
            "scenarios": SCENARIOS,
            "price_search": DEFAULTS["price_multipliers"],
            "algorithm": "finite-price expected-margin choice; conservative finite-horizon investment value with capacity shadow cost",
            "scope": "bounded policy class; no global optimality claim; no policy tuning on economic confirmation",
            "development": "actual numerical development only; confirmation hidden from action selection",
            "seed_domains": {"enterprise_confirmation": [70000, 70127], "frontier": [90000, 90063]},
            "primary_metrics": [
                "complete-cost profit",
                "collections",
                "available funds",
                "quality-adjusted productivity",
                "downside",
            ],
            "limitations": [
                "assumed buyer choice and demand",
                "researcher-authored opportunity menu",
                "no live frontier-model task evaluation",
                "public algorithmic rather than independently locked holdouts",
            ],
        }
        (ROOT / "config/economic_protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
        print("Economic source and parameters frozen before enterprise confirmation")
    else:
        run(args.calibration, args.output, args.repetitions)


if __name__ == "__main__":
    main()
