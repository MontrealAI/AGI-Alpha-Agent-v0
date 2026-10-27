# SPDX-License-Identifier: Apache-2.0
"""Conditional commercial experiment driven by executed numerical measurements."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import ndtri

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "protocol" / "economic_protocol.json"
POLICIES = ["competent_beta", "private_work", "shared_work", "shared_gym", "ordinary_library", "selective"]
CATEGORIES = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]
PRICE_CACHE: dict[tuple[Any, ...], tuple[float, float, float]] = {}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def measured_costs(technical: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for split in ["confirmation", "shift"]:
        by: dict[int, dict[str, Any]] = defaultdict(dict)
        for row in read_rows(technical / f"{split}.csv"):
            by[int(row["case"])][row["method"]] = row
        samples = {"beta": [], "work": [], "gym": [], "schur": []}
        for group in by.values():
            ordinary = group["adaptive_krylov"]
            samples["schur"].append(float(group["schur"]["seconds"]))
            t_beta = float(ordinary["seconds"])
            if ordinary["accepted"] != "True":
                t_beta += float(group["schur"]["seconds"])
            samples["beta"].append(t_beta)
            for key, name in [("work", "work_pod48"), ("gym", "gym_pod48")]:
                row = group[name]
                t = float(row["seconds"])
                if row["accepted"] != "True":
                    t += t_beta
                samples[key].append(t)
        out[split] = samples
    chain_path = technical / "fallback_validation.csv"
    if not chain_path.exists():
        raise FileNotFoundError("Measured complete fallback chains are required")
    chain_rows = read_rows(chain_path)
    aliases = {"adaptive_fallback": "beta", "work48_fallback": "work", "gym48_fallback": "gym"}
    for split in ["confirmation", "shift"]:
        for native, mode in aliases.items():
            selected = sorted([r for r in chain_rows if r["split"] == split and r["method"] == native],
                              key=lambda r: int(r["case"]))
            if not selected or any(r["accepted"] != "True" for r in selected):
                raise ValueError("Required fallback chain lacks observed numerical acceptance")
            out[split][mode] = [float(r["seconds"]) for r in selected]
    selection_file = technical / "selection_results.json"
    if not selection_file.exists():
        raise FileNotFoundError("Final-source selection measurements are required")
    out["selection_raw"] = json.loads(selection_file.read_text())
    if any(row["accepted"] != row["n"] for row in out["selection_raw"]["summary"].values()):
        raise ValueError("Selection evidence contains unaccepted outputs")
    out["input_hashes"] = {p.name: sha(p) for p in technical.glob("*.csv")}
    out["input_hashes"][selection_file.name] = sha(selection_file)
    return out


def scenario_config(config: dict[str, Any], scenario: str) -> dict[str, Any]:
    c = dict(config["base"])
    changes = {
        "base": {}, "low_demand": {"leads_per_day": 0.5}, "low_wtp": {"wtp_scale": 0.1},
        "high_failures": {"package_acceptance_probability": 0.6},
        "high_integration": {"retention_integration_usd": 200, "gym_extra_usd": 250,
                             "recipient_integration_usd": 40},
        "poor_transfer": {"transfer_success_probability": 0.5},
        "capacity_pressure": {"leads_per_day": 100, "daily_capacity_seconds": 1800},
        "regime_shift": {"shift_probability": 0.75},
        "slow_collections": {"collection_delay_days": [14, 30, 60, 90]},
        "rapid_frontier_progress": {"obsolescence_day": 15, "post_upgrade_ordinary_time_factor": 0.15,
                                    "post_upgrade_model_cost_factor": 0.5},
        "high_compute_price": {"compute_usd_per_hour": 50},
        "growth_financed_by_surplus": {"leads_per_day": 100, "daily_capacity_seconds": 1800},
    }
    c.update(changes[scenario])
    return c


def world(seed: int, config: dict[str, Any], days: int) -> list[list[dict[str, Any]]]:
    rng = np.random.default_rng(seed)
    result = []
    for day in range(days):
        events = []
        for index in range(rng.poisson(config["leads_per_day"])):
            events.append({"id": f"d{day}-j{index}", "offer": int(rng.choice(3, p=config["offer_probabilities"])),
                           "value_z": float(rng.normal()), "compatible": float(rng.random()),
                           "quality": float(rng.random()), "default": float(rng.random()),
                           "delay_u": float(rng.random()), "shift": float(rng.random()),
                           "transfer": float(rng.random()), "sample": int(rng.integers(0, 64))})
        result.append(events)
    return result


def buyer_choice(values: np.ndarray, price: float, anchor: float, c: dict[str, Any]) -> np.ndarray:
    utilities = np.stack((c["ai_value_multiplier"] * values - price,
                          c["human_value_multiplier"] * values - anchor,
                          c["defer_value_multiplier"] * values - c["defer_penalty_anchor_fraction"] * anchor,
                          np.zeros_like(values)), axis=-1)
    return np.argmax(utilities, axis=-1)


def choose_price(offer: dict[str, Any], c: dict[str, Any], fractions: list[float], compute_cost: float = 0.0) -> tuple[float, float, float]:
    key = (offer["id"], offer["human_hours_estimate"], tuple(fractions), compute_cost,
           *(c[k] for k in ["wtp_scale", "wtp_log_sigma", "ai_value_multiplier", "human_value_multiplier",
                            "defer_value_multiplier", "defer_penalty_anchor_fraction", "collection_default_probability",
                            "package_acceptance_probability", "processing_fee_fraction", "model_pipeline_usd",
                            "tools_storage_network_usd", "correction_extra_usd"]))
    if key in PRICE_CACHE:
        return PRICE_CACHE[key]
    anchor = offer["human_hours_estimate"] * 150
    values = anchor * c["wtp_scale"] * np.exp(c["wtp_log_sigma"] * ndtri((np.arange(256) + 0.5) / 256))
    scores = []
    for f in fractions:
        price = anchor * f
        probability = float(np.mean(buyer_choice(values, price, anchor, c) == 0))
        collected = price * (1 - c["collection_default_probability"])
        margin = collected * (c["package_acceptance_probability"] - c["processing_fee_fraction"])
        margin -= c["model_pipeline_usd"] + c["tools_storage_network_usd"] + compute_cost
        margin -= (1 - c["package_acceptance_probability"]) * c["correction_extra_usd"]
        scores.append((probability * margin, price, probability))
    score, price, probability = max(scores)
    PRICE_CACHE[key] = (price, probability, score)
    return PRICE_CACHE[key]


def selection_seconds(measured: dict[str, Any], mode: str) -> float:
    raw = measured["selection_raw"]
    summary = raw.get("summary", raw.get("policies", raw))
    aliases = {"beta": ["adaptive_fallback", "adaptive_krylov", "adaptive_safe", "beta_adaptive", "beta"],
               "work": ["work_pod48", "work_safe", "work", "work48_fallback"],
               "gym": ["gym_pod48", "gym_safe", "gym", "gym48_fallback"]}
    for key in aliases[mode]:
        if key in summary:
            row = summary[key]
            for t in ["total_seconds", "seconds_total", "service_seconds", "seconds"]:
                if t in row:
                    return float(row[t])
    raise ValueError(f"Unknown selection schema for {mode}: {list(summary)}")


def core_seconds(measured: dict[str, Any], mode: str, offer: dict[str, Any], event: dict[str, Any],
                 c: dict[str, Any], upgraded: bool) -> float:
    actual_mode = mode
    transfer_overhead = 0.0
    if mode != "beta" and event["transfer"] > c["transfer_success_probability"]:
        actual_mode = "beta"
        transfer_overhead = 0.005
    if offer["id"] == "select":
        seconds = selection_seconds(measured, actual_mode)
    else:
        split = "shift" if event["shift"] < c["shift_probability"] else "confirmation"
        values = measured[split][actual_mode]
        start = event["sample"] % len(values)
        seconds = sum(values[(start + j) % len(values)] for j in range(offer["cases"]))
    if upgraded:
        seconds *= c["post_upgrade_ordinary_time_factor"]
    return seconds + transfer_overhead


def simulate(seed: int, scenario: str, policy: str, config: dict[str, Any], measured: dict[str, Any],
             events: list[list[dict[str, Any]]]) -> dict[str, Any]:
    c = scenario_config(config, scenario)
    days = config["days"]
    charges: list[dict[str, Any]] = []
    collections: list[dict[str, Any]] = []
    invoices: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    paths = []
    count: dict[str, int] = defaultdict(int)
    setup = c["production_setup_usd"]
    today = -1
    accrued_now = 0.0
    paid_now = 0.0
    collected_now = 0.0
    accrual_schedule: dict[int, float] = defaultdict(float)
    payment_schedule: dict[int, float] = defaultdict(float)
    collection_schedule: dict[int, float] = defaultdict(float)

    def charge(day: int, bucket: str, category: str, amount: float, reason: str, immediate_paid: bool = False) -> None:
        nonlocal accrued_now, paid_now
        charges.append({"day": day, "bucket": bucket, "category": category, "amount": amount, "reason": reason,
                        "immediate_paid": immediate_paid})
        immediate = amount if immediate_paid else amount * c["initial_paid_cost_fraction"]
        if day <= today:
            accrued_now += amount
            paid_now += immediate
        else:
            accrual_schedule[day] += amount
            payment_schedule[day] += immediate
        payment_schedule[day + c["payment_delay_cost_days"]] += amount - immediate

    def collect(day: int, amount: float, reason: str) -> None:
        nonlocal collected_now
        collections.append({"day": day, "amount": amount, "reason": reason})
        if day <= today:
            collected_now += amount
        else:
            collection_schedule[day] += amount

    def balances(day: int) -> tuple[float, float, float, float, float]:
        outstanding = accrued_now - paid_now
        cash = c["seed_capital_usd"] + collected_now - paid_now
        return accrued_now * -1 + collected_now, cash, outstanding, cash - outstanding - c["reserve_usd"], collected_now

    charge(0, "C", "model", setup, "common production integration and acceptance setup; assumed all-in budget")
    for j in range(c["origin_exact_jobs"]):
        charge(0, "C", "compute", c["origin_seconds_per_example_assumption"] * c["compute_usd_per_hour"] / 3600,
               f"unpaid-origin-full-covariance-{j}; rounded timing assumption")
        charge(0, "C", "model", c["model_pipeline_usd"], f"unpaid-origin-research-delivery-{j}")
        if c["origin_collection_usd"]:
            collect(0, c["origin_collection_usd"], f"explicitly-assumed-origin-collection-{j}")
    mode = "beta"
    if policy in ["private_work", "shared_work", "ordinary_library", "shared_gym"]:
        mode = "gym" if policy == "shared_gym" else "work"
        copies = c["agents"] if policy == "private_work" else 1
        charge(0, "B", "acceptance", copies * c["retention_assessment_usd"], "candidate evidence review")
        charge(0, "B", "model", copies * c["retention_integration_usd"], "additional retention/integration")
        if policy != "private_work":
            charge(0, "B", "network", c["shared_admission_usd"], "shared admission and rights/access preparation")
        charge(0, "B", "tools", (c["agents"] - 1) * c["recipient_integration_usd"], "recipient integration")
        if mode == "gym":
            charge(0, "C", "model", c["gym_extra_usd"], "extra Gym assessment, four solves, refit and checks")
    elif policy == "selective":
        charge(0, "B", "acceptance", c["retention_assessment_usd"], "information acquisition; rejected candidate costs retained")
    offers = {"audit"}
    attempted = {"audit"}
    prototype_draws = np.random.default_rng(seed + 331000).random(3)
    investment_capacity: dict[int, float] = defaultdict(float)
    investment_capacity[0] = c["setup_capacity_seconds"]
    if mode != "beta":
        investment_capacity[0] += c["retention_capacity_seconds"] * (c["agents"] if policy == "private_work" else 1)
        if mode == "gym":
            investment_capacity[0] += c["gym_capacity_seconds"]
    expected_kernel = {}
    for offer in config["offers"]:
        if offer["id"] == "select":
            t = selection_seconds(measured, mode)
        else:
            t = offer["cases"] * ((1-c["shift_probability"]) * np.mean(measured["confirmation"][mode]) +
                                  c["shift_probability"] * np.mean(measured["shift"][mode]))
        expected_kernel[offer["id"]] = float(t)
    price_info = [choose_price(o, c, config["price_fractions"], expected_kernel[o["id"]] * c["compute_usd_per_hour"] / 3600)
                  for o in config["offers"]]
    observed_leads = 0
    workers = 0
    displaced = 0
    value_units = 0
    cpu_seconds = 0.0
    processing_seconds = 0.0
    refunds = 0.0
    for day, daily in enumerate(events):
        today = day
        accrued_now += accrual_schedule[day]
        paid_now += payment_schedule[day]
        collected_now += collection_schedule[day]
        charge(day, "A", "overhead", c["daily_operating_overhead_usd"], "allocated monitoring, support and operations")
        prior_rate = (6 + observed_leads) / (1 + day)
        remaining = days - day
        upgraded = day >= c["obsolescence_day"]
        if day in [0, 5, 15, 30, 45]:
            for i, offer in enumerate(config["offers"]):
                if offer["id"] in attempted:
                    continue
                expected = prior_rate * remaining * c["offer_probabilities"][i] * price_info[i][2]
                expected *= c["compatible_input_probability"] * c["prototype_success_probability"]
                available = balances(day)[3]
                cost = offer["productization_usd"]
                if expected > cost and available >= cost:
                    charge(day, "C", "model", cost, f"prototype, check and package {offer['id']}")
                    attempted.add(offer["id"])
                    investment_capacity[day] += c["prototype_capacity_seconds"]
                    succeeded = bool(prototype_draws[i] < c["prototype_success_probability"])
                    if succeeded:
                        offers.add(offer["id"])
                    count["failed_prototypes"] += int(not succeeded)
                    decisions.append({"day": day, "action": "prototype", "success": succeeded, "offer": offer["id"],
                                      "expected_remaining_contribution": expected, "cost": cost})
                else:
                    decisions.append({"day": day, "action": "decline_prototype", "offer": offer["id"]})
            if policy == "selective" and mode == "beta":
                best = {"action": "hold_cash", "net": 0.0, "mode": "beta"}
                for candidate in ["work", "gym"]:
                    saved = np.mean(measured["confirmation"]["beta"]) - np.mean(measured["confirmation"][candidate])
                    selection_saved = selection_seconds(measured, "beta") - selection_seconds(measured, candidate)
                    optimistic_seconds_saved = max(0.0, float(saved) * 32, selection_saved)
                    savings_per_order = optimistic_seconds_saved * c["compute_usd_per_hour"] / 3600
                    orders = prior_rate * remaining * c["compatible_input_probability"] * max(x[1] for x in price_info)
                    benefits = orders * savings_per_order
                    extra = c["retention_integration_usd"] + c["shared_admission_usd"]
                    extra += (c["agents"] - 1) * c["recipient_integration_usd"]
                    extra += (c["gym_extra_usd"] if candidate == "gym" else 0)
                    future_upkeep = math.ceil(remaining / 15) * c["maintenance_per_15_days_usd"]
                    if benefits - extra - future_upkeep > best["net"] and balances(day)[3] >= extra:
                        best = {"action": "invest", "net": benefits - extra - future_upkeep,
                                "mode": candidate, "cost": extra, "future_upkeep_valuation_only": future_upkeep}
                if best["action"] == "invest" and mode == "beta":
                    mode = str(best["mode"])
                    gym_cost = c["gym_extra_usd"] if mode == "gym" else 0
                    charge(day, "B", "model", float(best["cost"]) - gym_cost,
                           "selective additional retention/admission/recipient integration")
                    if gym_cost:
                        charge(day, "C", "model", gym_cost, "selective optional Gym development")
                    investment_capacity[day] += c["retention_capacity_seconds"]
                    if mode == "gym":
                        investment_capacity[day] += c["gym_capacity_seconds"]
                decisions.append({"day": day, **best})
        if mode != "beta" and day and day % 15 == 0:
            copies = c["agents"] if policy == "private_work" else 1
            charge(day, "B", "acceptance", copies * c["maintenance_per_15_days_usd"], "maintenance and drift assessment")
        if scenario == "growth_financed_by_surplus" and day and day % 5 == 0:
            expected_load = prior_rate * 120 * c["compatible_input_probability"] * max(x[1] for x in price_info)
            capacity_now = c["daily_capacity_seconds"] + workers * c["growth_worker_capacity_seconds"]
            if expected_load > capacity_now and workers < c["growth_max_workers"] and balances(day)[3] > c["seed_capital_usd"] + c["growth_worker_usd"]:
                charge(day, "C", "tools", c["growth_worker_usd"], "additional capacity purchased from available operating surplus")
                workers += 1
        capacity = max(0, c["daily_capacity_seconds"] + workers * c["growth_worker_capacity_seconds"] - investment_capacity[day])
        acquisition_value = sum(c["offer_probabilities"][i] * price_info[i][2]
                                for i, offer in enumerate(config["offers"]) if offer["id"] in offers)
        buy_leads = acquisition_value * c["compatible_input_probability"] > c["qualified_lead_acquisition_usd"] + c["intake_cost_usd"]
        if not buy_leads:
            daily = []
        for event in daily:
            if balances(day)[3] < c["qualified_lead_acquisition_usd"] + c["intake_cost_usd"]:
                count["declined_acquisition_funds"] += 1
                continue
            count["leads"] += 1
            observed_leads += 1
            charge(day, "A", "overhead", c["intake_cost_usd"], "automated intake, including declined requests")
            charge(day, "A", "overhead", c["qualified_lead_acquisition_usd"], "assumed qualified lead acquisition")
            offer = config["offers"][event["offer"]]
            if event["compatible"] > c["compatible_input_probability"] or offer["id"] not in offers:
                count["declined_scope"] += 1
                continue
            price, _, expected_margin = price_info[event["offer"]]
            if expected_margin <= 0:
                count["declined_margin"] += 1
                continue
            anchor = offer["human_hours_estimate"] * 150
            value = anchor * c["wtp_scale"] * math.exp(c["wtp_log_sigma"] * event["value_z"])
            utilities = [c["ai_value_multiplier"] * value - price,
                         c["human_value_multiplier"] * value - anchor,
                         c["defer_value_multiplier"] * value - c["defer_penalty_anchor_fraction"] * anchor, 0]
            choice = max(range(4), key=lambda i: utilities[i])
            if choice:
                count[["bought_ai", "chose_human", "deferred", "declined_buyer"][choice]] += 1
                continue
            reservation = offer["model_seconds_assumed"] + offer["core_deadline_seconds"]
            committed_cost_bound = c["model_pipeline_usd"] + c["tools_storage_network_usd"]
            committed_cost_bound += c["correction_extra_usd"] + price * c["processing_fee_fraction"]
            committed_cost_bound += offer["core_deadline_seconds"] * c["compute_usd_per_hour"] / 3600
            if reservation > capacity or balances(day)[3] < committed_cost_bound:
                displaced += 1
                continue
            capacity -= reservation
            seconds = core_seconds(measured, mode, offer, event, c, upgraded)
            total_seconds = seconds + offer["model_seconds_assumed"]
            capacity = max(0, capacity - max(0, total_seconds - reservation))
            count["orders"] += 1
            cpu_seconds += seconds
            processing_seconds += total_seconds
            multiplier = c["post_upgrade_model_cost_factor"] if upgraded else 1
            charge(day, "A", "model", c["model_pipeline_usd"] * multiplier, "assumed automated frontier pipeline tokens")
            charge(day, "A", "tools", c["tools_storage_network_usd"], "automated tool/storage/network allowance")
            charge(day, "A", "compute", seconds * c["compute_usd_per_hour"] / 3600, "measured kernel time at assumed hosting rate")
            compatible_quality = event["quality"] <= c["package_acceptance_probability"]
            accepted = compatible_quality and seconds <= offer["core_deadline_seconds"]
            count["accepted"] += int(accepted)
            count["failed"] += int(not accepted)
            value_units += offer["value_units"] if accepted else 0
            if not accepted:
                charge(day, "A", "correction", c["correction_extra_usd"], "failed acceptance correction attempt")
            delay = c["collection_delay_days"][int(np.searchsorted(np.cumsum(c["collection_delay_probabilities"]), event["delay_u"]))]
            invoices.append({"day": day, "amount": price, "due": day + delay, "default": event["default"] < c["collection_default_probability"]})
            if event["default"] >= c["collection_default_probability"]:
                collect(day + delay, price, event["id"])
                charge(day + delay, "A", "overhead", price * c["processing_fee_fraction"], "collection processing fee")
                if not accepted:
                    charge(day + delay, "A", "correction", price, "full customer refund after failed acceptance", True)
                    if day + delay < days:
                        refunds += price
        profit, cash, liabilities, available, collected = balances(day)
        paths.append({"day": day, "profit": profit, "cash": cash, "obligations": liabilities,
                      "available": available, "collections": collected, "offers": len(offers), "workers": workers})
    profit, cash, liabilities, available, collected = balances(days - 1)
    accrued = {bucket: sum(x["amount"] for x in charges if x["bucket"] == bucket and x["day"] < days)
               for bucket in ["A", "B", "C"]}
    paid_total = c["seed_capital_usd"] + collected - cash
    receivables = sum(x["amount"] for x in invoices if x["due"] >= days)
    return {"seed": seed, "scenario": scenario, "policy": policy, "profit": profit, "collections": collected,
            "cost_A": accrued["A"], "cost_B": accrued["B"], "cost_C": accrued["C"], "paid_costs": paid_total,
            "cash": cash, "obligations": liabilities, "reserves": c["reserve_usd"], "available": available,
            "receivables_excluded": receivables, "refunds": refunds, "seed_capital": c["seed_capital_usd"],
            "quality_adjusted_units": value_units, "cpu_seconds": cpu_seconds,
            "weighted_units_per_processing_hour": value_units / (processing_seconds / 3600) if processing_seconds else 0,
            "processing_seconds": processing_seconds, "displaced_orders": displaced, "workers": workers,
            "prices": {o["id"]: price_info[i][0] for i, o in enumerate(config["offers"])},
            "mode": mode, **dict(count), "path": paths, "charges": charges, "collection_events": collections,
            "decisions": decisions}


def summary(values: list[float]) -> dict[str, float]:
    a = np.asarray(values)
    mean = float(a.mean())
    half = 1.96 * float(a.std(ddof=1)) / math.sqrt(len(a)) if len(a) > 1 else 0
    return {"mean": mean, "mc95_low": mean - half, "mc95_high": mean + half,
            "p05": float(np.quantile(a, .05)), "p95": float(np.quantile(a, .95))}


def run(technical: Path, output: Path, seeds: int | None = None, development: bool = False) -> None:
    config = json.loads(CONFIG.read_text())
    measured = measured_costs(technical)
    output.mkdir(parents=True, exist_ok=True)
    freeze = {"protocol_sha256": sha(CONFIG), "code_sha256": sha(Path(__file__)),
              "technical_inputs": measured["input_hashes"], "market_evidence": "ASSUMED_AND_SIMULATED",
              "confirmation_executed": False}
    (output / "economic_freeze.json").write_text(json.dumps(freeze, indent=2))
    seed0, seed1 = config["development_seeds" if development else "confirmation_seeds"]
    if seeds is not None:
        seed1 = seed0 + seeds - 1
    rows = []
    aggregate = {}
    daily = defaultdict(list)
    exemplar = None
    for scenario in config["stress_scenarios"]:
        results = []
        for seed in range(seed0, seed1 + 1):
            c = scenario_config(config, scenario)
            events = world(seed, c, config["days"])
            matched = {}
            for policy in POLICIES:
                r = simulate(seed, scenario, policy, config, measured, events)
                matched[policy] = r
                scalar = {k: v for k, v in r.items() if k not in ["path", "charges", "collection_events", "decisions"]}
                results.append(scalar)
                rows.append({k: v for k, v in scalar.items() if k != "prices"})
                if scenario == "base":
                    daily[policy].append(r["path"])
                if seed == seed0 and scenario == "base" and policy == "selective":
                    exemplar = r
            assert matched["shared_work"]["profit"] == matched["ordinary_library"]["profit"]
        aggregate[scenario] = {}
        by = {p: [r for r in results if r["policy"] == p] for p in POLICIES}
        for policy, group in by.items():
            metrics = {key: summary([r.get(key, 0) for r in group]) for key in
                       ["profit", "collections", "cost_A", "cost_B", "cost_C", "available", "cash",
                        "obligations", "quality_adjusted_units", "displaced_orders", "orders", "accepted", "workers"]}
            metrics["incremental_profit_vs_beta"] = summary([r["profit"] - b["profit"]
                                                           for r, b in zip(group, by["competent_beta"])])
            metrics["mode_counts"] = {mode: sum(r["mode"] == mode for r in group) for mode in ["beta", "work", "gym"]}
            metrics["prices"] = group[0]["prices"]
            aggregate[scenario][policy] = metrics
    keys = sorted({k for row in rows for k in row})
    with (output / "enterprise_runs.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    (output / "economic_results.json").write_text(json.dumps({"freeze": freeze,
                                                             "execution_status": "executed_development" if development else "executed_confirmation",
                                                             "seeds": [seed0, seed1], "scenarios": aggregate}, indent=2))
    (output / "exemplar.json").write_text(json.dumps(exemplar, indent=2))
    curves = {policy: [{"day": day, **{key: float(np.mean([path[day][key] for path in paths]))
                                      for key in ["profit", "available", "offers", "workers"]}}
                       for day in range(config["days"])] for policy, paths in daily.items()}
    (output / "economic_paths.json").write_text(json.dumps(curves, indent=2))
    print(json.dumps({p: aggregate["base"][p]["profit"] for p in POLICIES}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--technical", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "economics")
    parser.add_argument("--seeds", type=int)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    run(args.technical, args.output, args.seeds, args.development)
