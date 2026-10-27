# SPDX-License-Identifier: Apache-2.0
"""Frozen, auditable hypothetical enterprise replay of measured technical outcomes."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
BASE_METHODS = {"beta_space", "beta_dopt", "beta_adaptive", "beta_direct", "beta_paired_diagnosis"}
POLICIES = ("beta", "private", "shared", "shared_no_gym", "shared_library", "shared_gym_pilot")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def rows_from(path: Path) -> list[dict[str, Any]]:
    value = read_json(path)
    return value if isinstance(value, list) else value["rows"]


def token_cost(config: dict[str, Any]) -> float:
    return sum(
        (v["input_tokens"] * v["input_usd_per_million"] + v["output_tokens"] * v["output_usd_per_million"])
        / 1_000_000
        for v in config["model_token_bundle_assumed"].values()
    )


def outcome(row: dict[str, Any], offering: dict[str, Any]) -> bool:
    return bool(row.get(offering["acceptance_key"], False))


def calls(row: dict[str, Any], offering: dict[str, Any], config: dict[str, Any]) -> float:
    if row["method"] == "beta_paired_diagnosis":
        return float(row["paired_diagnosis_extra_calls"] + config.get("extra_job_validation_calls", 0))
    return float(row["oracle_calls"] + offering["extra_acceptance_queries"] + config.get("extra_job_validation_calls", 0))


def job_cost(query_count: float, method: str, config: dict[str, Any]) -> float:
    extra = config["specialist_invocation_cost_assumed"] if method in {"v1", "v2", "library_v2"} else 0.0
    return (
        token_cost(config)
        + config["job_tool_and_packaging_cost_assumed"]
        + config["job_service_overhead_cost_assumed"]
        + query_count * config["query_cost_assumed"]
        + extra
    )


def customer_choice(price: float, quality: float, offering: dict[str, Any], config: dict[str, Any], u: float) -> str:
    reference = offering["price_reference_usd"] * config.get("price_scale", 1.0)
    value = reference * (config["buyer_value_min_multiple"] + u * (
        config["buyer_value_max_multiple"] - config["buyer_value_min_multiple"]))
    ai_utility = value * quality * config["buyer_trust"] - price - config["customer_effort_penalty"]
    human_utility = (
        value * config["human_quality_assumed"] - reference - config["human_delay_penalty"]
        if offering["human_option"] else -math.inf
    )
    if ai_utility >= max(0.0, human_utility):
        return "buy_ai"
    return "human" if human_utility > 0 else ("defer" if u > 0.5 else "decline")


def estimate_configs(dev: list[dict[str, Any]], offering: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in dev:
        if row["method"] == "oracle_support":
            continue
        if int(row["budget"]) > config.get("operating_query_budget", 96):
            continue
        grouped.setdefault((row["method"], int(row["budget"])), []).append(row)
    if offering["id"] == "fault_diagnosis":
        direct = {}
        for row in dev:
            if row.get("paired_diagnosis_accepted") is not None:
                direct[row["task_id"]] = {**row, "method": "beta_paired_diagnosis", "budget": 32,
                                          "diagnosis_accepted": row["paired_diagnosis_accepted"]}
        if direct:
            grouped[("beta_paired_diagnosis", 32)] = list(direct.values())
    estimates = []
    for (method, budget), observed in sorted(grouped.items()):
        successes = sum(outcome(r, offering) for r in observed)
        quality = (successes + 1) / (len(observed) + 2)
        query_count = statistics.mean(calls(r, offering, config) for r in observed)
        cost = job_cost(query_count, method, config)
        candidates = []
        for multiple in config["price_multipliers"]:
            price = offering["price_reference_usd"] * config.get("price_scale", 1) * multiple
            purchase = sum(customer_choice(price, quality, offering, config, (i + .5) / 200) == "buy_ai"
                           for i in range(200)) / 200
            conditional = quality * price * (1 - config["payment_fee_fraction"]) - cost
            candidates.append({"price": price, "purchase_probability": purchase,
                               "expected_profit_per_arrival": purchase * conditional})
        selected = max(candidates, key=lambda x: (x["expected_profit_per_arrival"], -x["price"]))
        estimates.append({"method": method, "budget": budget, "development_n": len(observed),
                          "development_successes": successes, "quality_forecast": quality,
                          "expected_calls": query_count, "expected_A_cost": cost, **selected})
    return estimates


def best(estimates: list[dict[str, Any]], methods: set[str]) -> dict[str, Any] | None:
    eligible = [e for e in estimates if e["method"] in methods and e["expected_profit_per_arrival"] > 0]
    return max(eligible, key=lambda e: (e["expected_profit_per_arrival"], -e["expected_calls"])) if eligible else None


def expected_gain(table: dict[str, list[dict[str, Any]]], old: set[str], new: set[str], config: dict[str, Any]) -> float:
    gain = 0.0
    for name, values in table.items():
        before, after = best(values, old), best(values, new)
        gain += config["task_offer_weights"][name] * (
            (after or {}).get("expected_profit_per_arrival", 0) - (before or {}).get("expected_profit_per_arrival", 0))
    return gain * config["arrival_rate_per_day"] * config["horizon_days"]


def learning_counts(ledger: dict[str, Any]) -> tuple[int, int]:
    origin_events = [e for e in ledger.get("events", []) if e.get("category") == "A"]
    origin = sum(int(e["complete_delivery_calls"]) for e in origin_events)
    if not origin_events:
        raise ValueError("Origin complete A query ledger required; no invented origin delivery cost.")
    gym = int(ledger.get("gym_oracle_calls", 1280))
    return origin, gym


def build_policy(name: str, dev: list[dict[str, Any]], offerings: list[dict[str, Any]],
                 config: dict[str, Any], learning: dict[str, Any]) -> dict[str, Any]:
    table = {o["id"]: estimate_configs(dev, o, config) for o in offerings}
    observed_methods = {r["method"] for r in dev}
    if any(r.get("paired_diagnosis_accepted") is not None for r in dev):
        observed_methods.add("beta_paired_diagnosis")
    base = BASE_METHODS & observed_methods
    if config.get("stronger_beta", False):
        base |= {"library_v2"} & observed_methods
    tasks = {r["task_id"] for r in dev}
    common_assessment_calls = 896 * len(tasks)
    selected_methods = set(base)
    decisions = []
    origin, gym = learning_counts(learning)
    gym_cost = gym * config["query_cost_assumed"]
    retained: list[str] = []
    share = name in {"shared", "shared_no_gym", "shared_library", "shared_gym_pilot"}
    access_fraction = 1.0 if share else 1 / config["agents"]
    v1_gain = expected_gain(table, base, base | {"v1"}, config) * access_fraction
    v1_fixed = config["retention_cost_per_version_assumed"] + config["horizon_days"] * config["maintenance_per_version_per_day_assumed"]
    extra_calls = sum(float(r["oracle_calls"]) for r in dev if r["method"] == "v1")
    v1_assessment_cost = extra_calls * config["query_cost_assumed"] + config["admission_administration_cost_assumed"]
    if name != "beta":
        selected_methods.add("v1")
        admit = v1_gain > v1_fixed + v1_assessment_cost
        decisions.append({"candidate": "v1", "decision": "admit" if admit else "reject",
                          "forecast_incremental_value": v1_gain, "extra_assessment_cost_B": v1_assessment_cost,
                          "prospective_retention_upkeep_B": v1_fixed})
        if admit:
            retained.append("v1")
    gym_decision = name != "beta" and name != "shared_no_gym" and v1_gain > gym_cost + v1_fixed + v1_assessment_cost
    if name == "shared_gym_pilot":
        gym_decision = True
    if name != "beta":
        decisions.append({"candidate": "gym", "decision": "practice" if gym_decision else "preserve_cash",
                          "rule": ("prebudgeted controlled exploration comparison; outcome not guaranteed" if name == "shared_gym_pilot" else
                                   "v1 development forecast must cover its assessment/retention/upkeep plus the actual Gym query budget; v2 outcomes are not read for this decision"),
                          "forecast_from_v1_only": v1_gain, "cost_C": gym_cost})
    if gym_decision:
        selected_methods.add("v2")
        v2_gain = expected_gain(table, base | set(retained), base | set(retained) | {"v2"}, config) * access_fraction
        v2_calls = sum(float(r["oracle_calls"]) for r in dev if r["method"] == "v2")
        v2_assess = v2_calls * config["query_cost_assumed"] + config["admission_administration_cost_assumed"]
        admit_v2 = v2_gain > v1_fixed + v2_assess
        decisions.append({"candidate": "v2", "decision": "admit" if admit_v2 else "reject",
                          "forecast_incremental_value": v2_gain, "extra_assessment_cost_B": v2_assess,
                          "prospective_retention_upkeep_B": v1_fixed})
        if admit_v2:
            retained.append("v2")
    share_cost = config["sharing_setup_cost_assumed"] + (config["agents"] - 1) * config["sharing_cost_per_peer_assumed"]
    peer_gain = expected_gain(table, base, base | set(retained), config) * (1 - 1 / config["agents"])
    share_enabled = share and bool(retained) and peer_gain > share_cost
    if share:
        decisions.append({"candidate": "network_sharing", "decision": "share" if share_enabled else "private_only",
                          "forecast_peer_gain": peer_gain, "extra_distribution_cost_B": share_cost})
    active = base | set(retained)
    routes = {o["id"]: {"origin": best(table[o["id"]], active),
                           "peer": best(table[o["id"]], active if share_enabled else base)} for o in offerings}
    if name == "shared_library":
        for route in routes.values():
            for role in route.values():
                if role and role["method"] == "v2":
                    role["method"] = "library_v2"
    proposal_cost = config["offering_development_cost_assumed"] + config["offering_development_extra_queries_assumed"] * config["query_cost_assumed"]
    proposals = []
    prototype_routes = {}
    for o in offerings:
        if not o["new_offering"]:
            continue
        route = routes[o["id"]]
        weighted = ((route["origin"] or {}).get("expected_profit_per_arrival", 0) +
                    (config["agents"] - 1) * (route["peer"] or {}).get("expected_profit_per_arrival", 0)) / config["agents"]
        forecast = weighted * config["arrival_rate_per_day"] * config["horizon_days"] * config["task_offer_weights"][o["id"]]
        develop = forecast > proposal_cost
        proposals.append({"offering": o["id"], "decision": "prototype" if develop else "reject", "forecast_value": forecast,
                          "development_cost_C": proposal_cost, "status": "frozen_menu_research_prototype_no_demand_validation"})
        prototype_routes[o["id"]] = copy.deepcopy(routes[o["id"]]) if develop else {"origin": None, "peer": None}
        if not develop or not config.get("diagnostic_market_hypothesis", False):
            routes[o["id"]] = {"origin": None, "peer": None}
    assessment_calls = common_assessment_calls + sum(float(r["oracle_calls"]) for r in dev if r["method"] in selected_methods)
    fixed_B = assessment_calls * config["query_cost_assumed"]
    fixed_B += (len(selected_methods - base)) * config["admission_administration_cost_assumed"]
    fixed_B += len(retained) * config["retention_cost_per_version_assumed"]
    fixed_B += share_cost if share_enabled else 0
    fixed_C = gym_cost if gym_decision else 0
    fixed_C += sum(p["development_cost_C"] for p in proposals if p["decision"] == "prototype")
    setup_calls = assessment_calls + (gym if gym_decision else 0)
    setup_calls += sum(config["offering_development_extra_queries_assumed"] for p in proposals if p["decision"] == "prototype")
    return {"name": name, "routes": routes, "prototype_routes": prototype_routes,
            "retained_versions": retained, "share_enabled": share_enabled,
            "gym": gym_decision, "decisions": decisions, "proposals": proposals, "fixed_B": fixed_B, "fixed_C": fixed_C,
            "assessment_calls_B": assessment_calls, "setup_calls": setup_calls, "origin_calls_A": origin,
            "base_methods": sorted(base), "evidence_methods_assessed": sorted(selected_methods), "development_tasks": len(tasks)}


def scenario_variants(base: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    variants = [("primary", copy.deepcopy(base))]
    changes = {
        "zero_query_price": {"query_cost_assumed": 0.0},
        "query_price_0_5": {"query_cost_assumed": .5},
        "query_price_2": {"query_cost_assumed": 2.0},
        "half_demand": {"arrival_rate_per_day": base["arrival_rate_per_day"] / 2},
        "double_demand": {"arrival_rate_per_day": base["arrival_rate_per_day"] * 2},
        "half_prices": {"price_scale": .5},
        "low_trust": {"buyer_trust": .55},
        "transfer_loss": {"transfer_failure_probability": .25},
        "low_reuse": {"regime_weights": {"compatible": .15, "partial_shift": .35, "novel_family": .50}},
        "congestion": {"agent_hours_per_day": 2},
        "delay_21_days": {"collection_delay_days": 21},
        "maintenance_10x": {"maintenance_per_version_per_day_assumed": 5.0},
        "obsolescence_day15": {"obsolescence_day": 15},
        "validator_correlated": {"correlated_validator_error_probability": .20},
        "stronger_beta": {"stronger_beta": True},
        "extra_896_verification": {"extra_job_validation_calls": 896},
        "surplus_financed_expansion": {"allow_expansion": True},
        "query_envelope_24": {"operating_query_budget": 24},
        "query_envelope_40": {"operating_query_budget": 40},
        "query_envelope_64": {"operating_query_budget": 64},
        "diagnostic_market_hypothesis": {"diagnostic_market_hypothesis": True},
    }
    for name, change in changes.items():
        value = copy.deepcopy(base)
        value.update(change)
        variants.append((name, value))
    for demand in (.5, 1.5):
        for price in (.5, 1.0):
            for trust in (.55, .85):
                value = copy.deepcopy(base)
                value.update(arrival_rate_per_day=base["arrival_rate_per_day"] * demand, price_scale=price, buyer_trust=trust)
                variants.append((f"factorial_d{demand}_p{price}_t{trust}", value))
    return variants


def freeze(dev_path: Path, learning_path: Path, overwrite: bool = False) -> dict[str, Any]:
    target = HERE / "policy_freeze.json"
    if target.exists() and not overwrite:
        raise RuntimeError("A policy freeze already exists; do not silently overwrite it.")
    dev = rows_from(dev_path)
    if not dev or any(r["split"] != "development" for r in dev):
        raise ValueError("Policy selection may read development rows only.")
    config = read_json(HERE / "scenario.json")
    offerings = read_json(HERE / "offerings.json")["offerings"]
    learning = read_json(learning_path)
    scenarios = []
    for name, values in scenario_variants(config):
        scenarios.append({"name": name, "config": values,
                          "policies": [build_policy(p, dev, offerings, values, learning) for p in POLICIES]})
    result = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": "FROZEN_BEFORE_CONFIRMATION_READ",
              "scenario_sha256": digest(HERE / "scenario.json"), "offerings_sha256": digest(HERE / "offerings.json"),
              "code_sha256": digest(Path(__file__)), "development_sha256": digest(dev_path),
              "learning_sha256": digest(learning_path), "learning_ledger": learning, "scenarios": scenarios,
              "development_task_ids": sorted({r["task_id"] for r in dev}),
              "decision_information": "development output counts, public price sources and frozen assumptions only; no confirmation outcome or hidden regime labels in a dispatch choice"}
    write_json(target, result)
    return result


def poisson(rng: random.Random, rate: float) -> int:
    threshold, product, count = math.exp(-rate), 1.0, 0
    while product > threshold:
        product *= rng.random()
        count += 1
    return count - 1


def event_stream(seed: int, config: dict[str, Any], task_groups: dict[str, list[str]]) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    events = []
    offers = list(config["task_offer_weights"])
    regimes = list(config["regime_weights"])
    for day in range(1, config["horizon_days"] + 1):
        bad_validator = rng.random() < config["correlated_validator_error_probability"]
        for _ in range(poisson(rng, config["arrival_rate_per_day"])):
            regime = rng.choices(regimes, weights=[config["regime_weights"][r] for r in regimes])[0]
            tasks = task_groups.get(regime, [])
            if not tasks:
                tasks = sum(task_groups.values(), [])
            events.append({"event_id": len(events), "day": day, "task_id": rng.choice(tasks),
                           "offering": rng.choices(offers, weights=[config["task_offer_weights"][o] for o in offers])[0],
                           "agent": rng.randrange(config["agents"]), "buyer_u": rng.random(),
                           "transfer_u": rng.random(), "validator_bad": bad_validator})
    return events


def simulate(policy: dict[str, Any], events: list[dict[str, Any]], index: dict[tuple[str, str, int], dict[str, Any]],
             offerings: dict[str, dict[str, Any]], config: dict[str, Any], learning: dict[str, Any],
             keep_ledger: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seed_cash = config["starting_cash"]
    cash, A, B, C = seed_cash, 0.0, 0.0, 0.0
    recognized, collections, refunds, fees, gross_invoices, wrong_invoices = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    pending: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    received_jobs = 0
    accepted_jobs = 0
    failed_jobs = 0
    false_accepts = 0
    cash_rejections = 0
    capacity_rejections = 0
    human_choices = 0
    deferred = 0
    rejected_jobs = 0
    lost_opportunity = 0.0
    query_total = 0.0
    expanded = False
    retired = False
    per_day_calls = config["agents"] * config["agent_hours_per_day"] * 3600 / config["query_seconds_assumed"]
    daily_limit = per_day_calls
    total_limit = daily_limit * config["horizon_days"]
    setup_calls = float(policy["setup_calls"])
    setup_backlog = setup_calls
    origin_calls = float(policy["origin_calls_A"])
    origin_cost = job_cost(origin_calls, "beta_adaptive", config)
    A += origin_cost
    cash -= origin_cost
    query_total += origin_calls
    setup_backlog += origin_calls
    origin_ok = all(e.get("accepted", False) for e in learning["events"] if e.get("category") == "A")
    origin_price = 960.0 * config.get("price_scale", 1)
    if origin_ok:
        recognized += origin_price
        gross_invoices += origin_price
        A += origin_price * config["payment_fee_fraction"]
        pending.append({"due": config["collection_delay_days"], "amount": origin_price, "kind": "collection", "event": "origin"})
    fixed_total = policy["fixed_B"] + policy["fixed_C"]
    setup_funded = cash - fixed_total >= config["reserve_floor"] and setup_calls + origin_calls <= total_limit
    operational = copy.deepcopy(policy)
    if setup_funded:
        B += policy["fixed_B"]
        C += policy["fixed_C"]
        cash -= fixed_total
        query_total += setup_calls
    else:
        setup_backlog = 0
        operational["routes"] = {name: {"origin": None, "peer": None} for name in offerings}
        operational["retained_versions"] = []
    if keep_ledger:
        ledger.append({"day": 0, "kind": "origin_and_setup", "A_cost": origin_cost, "B_cost": B, "C_cost": C,
                       "cash": cash, "origin_accepted": origin_ok, "origin_revenue": origin_price if origin_ok else 0,
                       "setup_funded": setup_funded, "query_calls": query_total, "seed_capital": seed_cash})
    event_groups: dict[int, list[dict[str, Any]]] = {}
    for event in events:
        event_groups.setdefault(event["day"], []).append(event)
    arrivals_seen = 0
    for day in range(1, config["horizon_days"] + 1):
        for item in list(pending):
            if item["due"] <= day:
                if item["kind"] == "collection":
                    charge = item["amount"] * config["payment_fee_fraction"]
                    cash += item["amount"] - charge
                    collections += item["amount"]
                    fees += charge
                else:
                    cash -= item["amount"]
                    refunds += item["amount"]
                pending.remove(item)
        maintenance = len(operational["retained_versions"]) * config["maintenance_per_version_per_day_assumed"]
        if retired:
            maintenance = 0
        B += maintenance
        cash -= maintenance
        if config["obsolescence_day"] is not None and day >= config["obsolescence_day"]:
            retired = True
        earned_available = max(0, cash - seed_cash - config["reserve_floor"])
        if config.get("allow_expansion") and not expanded and day == config["expansion_decision_day"]:
            projected_backlog = arrivals_seen / max(1, day - 1) * 96 > daily_limit * .8
            if earned_available >= config["expansion_min_available_earned_surplus"] and projected_backlog:
                extra = config["expansion_cost_assumed"]
                cash -= extra
                C += extra
                daily_limit += config["expansion_extra_agent_hours_per_day"] * 3600 / config["query_seconds_assumed"]
                total_limit += (config["horizon_days"] - day + 1) * (daily_limit - per_day_calls)
                expanded = True
        busy = min(daily_limit, setup_backlog)
        setup_backlog -= busy
        day_used = busy
        for event in event_groups.get(day, []):
            arrivals_seen += 1
            offering = offerings[event["offering"]]
            role = "origin" if event["agent"] == 0 else "peer"
            route = operational["routes"][event["offering"]][role]
            record = {**event, "policy": policy["name"], "A_cost": 0.0, "B_cost": 0.0, "C_cost": 0.0}
            if route is None:
                rejected_jobs += 1
                record["decision"] = "no_profitable_qualified_offer"
            else:
                method = route["method"]
                if retired and method in {"v1", "v2", "library_v2"}:
                    method = "beta_adaptive" if "beta_adaptive" in policy["base_methods"] else sorted(policy["base_methods"])[0]
                reserved_calls = (32 if method == "beta_paired_diagnosis" else
                                  route["budget"] + offering["extra_acceptance_queries"])
                reserved_calls += config.get("extra_job_validation_calls", 0)
                reserved_cost = job_cost(reserved_calls, method, config)
                expected_reserve = config["reserve_floor"] + max(0, gross_invoices - refunds) * config["warranty_reserve_fraction"]
                choice = customer_choice(route["price"], route["quality_forecast"], offering, config, event["buyer_u"])
                record.update(method=method, budget=route["budget"], quoted_price=route["price"], customer_choice=choice,
                              reserved_query_calls=reserved_calls, reserved_cost=reserved_cost,
                              observed_invoice_based_reserve=expected_reserve)
                if choice != "buy_ai":
                    human_choices += choice == "human"
                    deferred += choice in {"defer", "decline"}
                    record["decision"] = choice
                elif cash - reserved_cost < expected_reserve:
                    cash_rejections += 1
                    lost_opportunity += max(0, route["expected_profit_per_arrival"])
                    record["decision"] = "preserve_cash"
                elif day_used + reserved_calls > daily_limit or query_total + reserved_calls > total_limit:
                    capacity_rejections += 1
                    lost_opportunity += max(0, route["expected_profit_per_arrival"])
                    record["decision"] = "capacity_decline"
                else:
                    if role == "peer" and method in {"v1", "v2", "library_v2"} and event["transfer_u"] < config["transfer_failure_probability"]:
                        method = "wrong_prior"
                    row = index.get((event["task_id"], method, int(route["budget"])))
                    if row is None:
                        raise ValueError(f"Missing measured technical row: {event['task_id']}, {method}, {route['budget']}")
                    query_count = calls(row, offering, config)
                    cost = job_cost(query_count, method, config)
                    if query_count > reserved_calls:
                        raise AssertionError("Realized calls exceed the declared precommitment reservation.")
                    day_used += query_count
                    query_total += query_count
                    received_jobs += 1
                    A += cost
                    cash -= cost
                    truth = outcome(row, offering)
                    reported = truth or event["validator_bad"]
                    accepted_jobs += truth
                    failed_jobs += not truth
                    false_accepts += reported and not truth
                    if truth:
                        recognized += route["price"]
                    if reported:
                        gross_invoices += route["price"]
                        A += route["price"] * config["payment_fee_fraction"]
                        pending.append({"due": day + config["collection_delay_days"], "amount": route["price"],
                                        "kind": "collection", "event": event["event_id"]})
                    if reported and not truth:
                        wrong_invoices += route["price"]
                        pending.append({"due": day + config["collection_delay_days"] + config["correction_delay_days"],
                                        "amount": route["price"], "kind": "refund", "event": event["event_id"]})
                    record.update(decision="deliver", true_accepted=truth, reported_accepted=reported,
                                  A_cost=cost, query_calls=query_count, true_revenue=route["price"] if truth else 0,
                                  simulated_invoice=route["price"] if reported else 0,
                                  method=method, released_unused_query_calls=reserved_calls - query_count,
                                  technical_observed_seconds=row["observed_seconds"],
                                  hypothetical_execution_seconds=query_count * config["query_seconds_assumed"])
            record.update(cash=cash, recognized_revenue=recognized, cost_A_cumulative=A, cost_B_cumulative=B,
                          cost_C_cumulative=C, cumulative_profit=recognized - A - B - C)
            if keep_ledger:
                ledger.append(record)
        if keep_ledger:
            ledger.append({"day": day, "kind": "day_close", "cash": cash, "collections": collections,
                           "refunds": refunds, "recognized_revenue": recognized, "cost_A": A, "cost_B": B,
                           "cost_C": C, "profit": recognized - A - B - C, "query_calls": query_total,
                           "setup_backlog_calls": setup_backlog})
    refund_obligations = sum(p["amount"] for p in pending if p["kind"] == "refund")
    receivables = sum(p["amount"] for p in pending if p["kind"] == "collection")
    fee_payables = receivables * config["payment_fee_fraction"]
    reserves = config["reserve_floor"] + recognized * config["warranty_reserve_fraction"]
    available = max(0, cash - refund_obligations - fee_payables - reserves)
    profit = recognized - A - B - C
    cash_identity = seed_cash + collections - refunds - A - B - C + fee_payables
    if abs(cash - cash_identity) > 1e-6:
        raise AssertionError("Cash identity failed; fee or expense double counting.")
    if query_total > total_limit + 1e-6:
        raise AssertionError("A policy exceeded the matched resource envelope.")
    return {"policy": policy["name"], "simulated_revenue": recognized, "gross_invoices": gross_invoices,
            "simulated_collections": collections, "refunds_paid": refunds, "false_accepted_invoice_total": wrong_invoices,
            "cost_A": A, "cost_B": B, "cost_C": C, "complete_cost": A + B + C, "profit": profit,
            "cash": cash, "seed_capital": seed_cash, "receivables": receivables, "refund_obligations": refund_obligations,
            "payment_fee_payables": fee_payables, "obligations": refund_obligations + fee_payables,
            "reserves": reserves, "available_funds": available, "available_earned_surplus": max(0, available - seed_cash),
            "jobs_executed": received_jobs, "true_accepted_jobs": accepted_jobs, "failed_jobs": failed_jobs,
            "false_acceptances": false_accepts, "cash_rejections": cash_rejections,
            "capacity_rejections": capacity_rejections, "unqualified_rejections": rejected_jobs,
            "human_choices": human_choices, "defer_decline": deferred, "query_calls": query_total,
            "query_capacity": total_limit, "lost_opportunity_estimate_not_expensed": lost_opportunity,
            "accepted_output_cost": (A + B + C) / accepted_jobs if accepted_jobs else None,
            "setup_funded": setup_funded, "surplus_financed_expansion": expanded, "skill_retired": retired,
            "cash_identity_residual": cash - cash_identity}, ledger


def interval(values: list[float]) -> dict[str, float]:
    mean = statistics.mean(values)
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0
    return {"mean": mean, "conditional_seed_ci95_low": mean - half, "conditional_seed_ci95_high": mean + half,
            "minimum": min(values), "maximum": max(values)}


def execute(confirm_path: Path) -> dict[str, Any]:
    frozen = read_json(HERE / "policy_freeze.json")
    if frozen["scenario_sha256"] != digest(HERE / "scenario.json") or frozen["offerings_sha256"] != digest(HERE / "offerings.json"):
        raise ValueError("Frozen scenario/offerings changed after selection.")
    rows = rows_from(confirm_path)
    if not rows or any(r["split"] != "confirmation" for r in rows):
        raise ValueError("Confirmation rows required.")
    confirm_ids = {r["task_id"] for r in rows}
    if confirm_ids & set(frozen["development_task_ids"]):
        raise ValueError("Development/confirmation task leakage.")
    index = {(r["task_id"], r["method"], int(r["budget"])): r for r in rows}
    for row in rows:
        if row.get("paired_diagnosis_accepted") is not None:
            index[(row["task_id"], "beta_paired_diagnosis", 32)] = {
                **row, "method": "beta_paired_diagnosis", "budget": 32,
                "diagnosis_accepted": row["paired_diagnosis_accepted"]}
    task_groups: dict[str, list[str]] = {}
    seen = set()
    for row in rows:
        if row["task_id"] not in seen:
            task_groups.setdefault(row["regime"], []).append(row["task_id"])
            seen.add(row["task_id"])
    offerings = {o["id"]: o for o in read_json(HERE / "offerings.json")["offerings"]}
    records, summaries = [], []
    for scenario in frozen["scenarios"]:
        config = scenario["config"]
        per_policy = {p["name"]: [] for p in scenario["policies"]}
        for seed in range(config["replicates"]):
            events = event_stream(61000 + seed, config, task_groups)
            for policy in scenario["policies"]:
                keep = scenario["name"] == "primary" and seed == 0
                result, ledger = simulate(policy, events, index, offerings, config, frozen["learning_ledger"], keep)
                result.update(scenario=scenario["name"], seed=seed)
                records.append(result)
                per_policy[policy["name"]].append(result)
                if keep:
                    write_json(HERE / "results" / f"ledger_{policy['name']}_seed0.json", ledger)
            if scenario["name"] == "primary" and seed == 0:
                write_json(HERE / "results" / "matched_events_seed0.json", events)
        reference = per_policy["beta"]
        for policy, values in per_policy.items():
            summary = {"scenario": scenario["name"], "policy": policy, "replicates": len(values)}
            for key in ("profit", "simulated_revenue", "simulated_collections", "complete_cost", "cash", "available_funds",
                        "cost_A", "cost_B", "cost_C", "true_accepted_jobs", "query_calls", "refund_obligations",
                        "false_acceptances", "available_earned_surplus", "reserves", "receivables"):
                summary[key] = interval([v[key] for v in values])
            summary["paired_incremental_profit_vs_beta"] = interval([v["profit"] - b["profit"] for v, b in zip(values, reference)])
            summary["investment_or_setup_rejected_runs"] = sum(not v["setup_funded"] for v in values)
            summary["expansion_runs"] = sum(v["surplus_financed_expansion"] for v in values)
            summaries.append(summary)
    with (HERE / "results" / "enterprise_runs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    primary = {s["policy"]: s for s in summaries if s["scenario"] == "primary"}
    library_gap = primary["shared"]["profit"]["mean"] - primary["shared_library"]["profit"]["mean"]
    result = {"status": "SIMULATED_ECONOMICS_FROM_EXECUTED_SYNTHETIC_OUTCOMES_NO_SALES",
              "policy_freeze_sha256": digest(HERE / "policy_freeze.json"), "confirmation_sha256": digest(confirm_path),
              "code_sha256_at_execution": digest(Path(__file__)), "code_sha256_at_freeze": frozen["code_sha256"],
              "same_code_as_freeze": digest(Path(__file__)) == frozen["code_sha256"],
              "summary": summaries, "primary": primary, "equal_content_library_profit_gap": library_gap,
              "confidence_interval_scope": "Variation over assumed customer-event seeds conditional on one finite technical sample and all assumptions; not uncertainty over demand validity, frontier ability, prices, technical generalization or real profit.",
              "research_confirmation_unique_oracle_calls": len(confirm_ids) * 896,
              "research_confirmation_proxy_cost_C_separate_from_enterprises": len(confirm_ids) * 896 * frozen["scenarios"][0]["config"]["query_cost_assumed"],
              "earned_revenue_observed": 0, "actual_customer_sales": 0,
              "graph_specific_benefit_claimed": False,
              "limitations": ["Diagnostic economics use an unvalidated willingness-to-pay hypothesis and protected true-fault acceptance.",
                              "All prices, demand and collections are simulated; no latest-frontier end-to-end baseline was measured.",
                              "Technical outcomes are replayed from a finite fresh synthetic benchmark; simulation seeds create no new technical evidence.",
                              "Production price optimization uses an assumed buyer utility model, not an empirically fitted demand curve.",
                              "Origin learning is charged once to A; extra Gym only to C; rejected assessments and retention/distribution/upkeep only to B."]}
    write_json(HERE / "results" / "summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze", "run"))
    parser.add_argument("--development", type=Path, default=STUDY / "technical/results/development_rows.json")
    parser.add_argument("--learning", type=Path, default=STUDY / "technical/results/learning_ledger.json")
    parser.add_argument("--confirmation", type=Path, default=STUDY / "technical/results/raw_rows.json")
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze(args.development, args.learning)
        print(json.dumps({"status": result["status"], "scenarios": len(result["scenarios"]), "created_utc": result["created_utc"]}))
    else:
        result = execute(args.confirmation)
        print(json.dumps({"status": result["status"], "primary": {
            p: {"mean_profit": s["profit"]["mean"], "mean_accepted": s["true_accepted_jobs"]["mean"]}
            for p, s in result["primary"].items()}, "library_gap": result["equal_content_library_profit_gap"]}))


if __name__ == "__main__":
    main()
