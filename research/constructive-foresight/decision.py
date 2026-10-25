# SPDX-License-Identifier: Apache-2.0
"""Finite, explicitly assumed timing experiment; numerical evidence is supplied separately."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import random
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PLANS = ("rent", "build", "adaptive", "defer")
POLICIES = ("forecast_only", "constructive_foresight", "wait_and_act", "static_expert",
            "adaptive_nonforecast", "adaptive_same_signal", "clairvoyant_menu")
MODEL_USERS = {"forecast_only", "constructive_foresight", "static_expert", "adaptive_same_signal"}
METRICS = ("accepted", "attempted", "missed", "compute_seconds", "decision_cpu_seconds", "decision_wall_seconds",
           "preparation_cpu_seconds", "build_seconds", "solve_seconds", "validation_seconds",
           "signal_seconds", "competitor_amortization_seconds", "failed_compute_seconds", "failed_attempts",
           "numerically_qualified", "late_attempts", "late_qualified", "late_numerical_wall_seconds",
           "numerical_wall_seconds", "assumed_wall_equivalent_seconds", "accounted_cost_seconds",
           "offline_evaluator_cpu_seconds",
           "mission_credits", "credits_without_controller", "brier", "event", "bought_signal", "built",
           "forecast_probability", "candidate_evaluations")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def load_primitives(path: Path | None, engineering: bool = False) -> list[dict[str, Any]]:
    if path is None:
        if not engineering:
            raise ValueError("Measured primitives are required outside engineering mode")
        rows = [{"matrix": "engineering_fixture_not_evidence", "build_seconds": 1.0,
                 "cold_seconds": 1.05, "ready_seconds": 0.05, "validation_seconds": 0.01,
                 "build_samples_seconds": [0.5, 1.0, 1.5], "cold_samples_seconds": [0.6, 1.05, 2.0],
                 "ready_samples_seconds": [0.025, 0.05, 0.15], "validation_samples_seconds": [0.005, 0.01, 0.03],
                 "cold_success_rate": 0.99, "ready_success_rate": 0.99, "build_success_rate": 1.0}]
    else:
        raw = read_json(path)
        rows = raw["matrices"] if isinstance(raw, dict) else raw
    if not rows or len({x["matrix"] for x in rows}) != len(rows):
        raise ValueError("Require a nonempty matrix set with unique names")
    for row in rows:
        for key in ("build_seconds", "cold_seconds", "ready_seconds", "validation_seconds"):
            value = row[key]
            if not math.isfinite(value) or value < 0 or (key != "validation_seconds" and value == 0):
                raise ValueError(f"Invalid {key}: {value}")
            sample_key = key.replace("_seconds", "_samples_seconds")
            if sample_key in row and (not row[sample_key] or any(not math.isfinite(v) or v < 0 for v in row[sample_key])):
                raise ValueError(f"Invalid empirical sample array: {sample_key}")
        for key in ("cold_success_rate", "ready_success_rate", "build_success_rate"):
            if not 0 <= row.get(key, 1.0) <= 1:
                raise ValueError(f"Invalid probability: {key}")
    return sorted(rows, key=lambda x: x["matrix"])


def posterior(prior: float, accuracy: float, signal: bool) -> float:
    numerator = prior * (accuracy if signal else 1 - accuracy)
    denominator = numerator + (1 - prior) * (1 - accuracy if signal else accuracy)
    return numerator / denominator if denominator else prior


def worlds(rows: list[dict[str, Any]], protocol: dict[str, Any], seeds: list[int], model: bool) -> list[dict[str, Any]]:
    clock = statistics.median(x["build_seconds"] for x in rows)
    result = []
    for regime_index, (regime_name, regime) in enumerate(protocol["regimes"].items()):
        for seed in seeds:
            for episode in range(protocol["episodes_per_seed_per_regime"]):
                rng = random.Random(seed * 100000 + regime_index * 1000 + episode)
                primitive = rows[episode % len(rows)]
                prior = rng.choice(protocol["base_demand_probabilities"]) * regime["demand_multiplier"]
                demand = rng.random() < prior
                accuracy = regime["signal_accuracy_model" if model else "signal_accuracy_actual"]
                signal = demand if rng.random() < accuracy else not demand
                adoption_p = (protocol["adoption_probability_model"] if model
                              else regime["adoption_probability_actual"])
                adopted = rng.random() < adoption_p
                arrival = clock * (rng.choice(protocol["arrival_clock_units"])
                                   + rng.choice(protocol["adoption_delay_clock_units"])
                                   + (0 if model else regime["arrival_shift_actual"]))
                deadline = min(clock * protocol["horizon_clock_units"],
                               arrival + clock * rng.choice(protocol["expiry_after_arrival_clock_units"]))
                times = {}
                for stem in ("build", "cold", "ready", "validation"):
                    samples = primitive.get(stem + "_samples_seconds", [primitive[stem + "_seconds"]])
                    times[stem] = rng.choice(samples)
                times["build"] *= regime["build_multiplier"]
                result.append({"regime": regime_name, "seed": seed, "episode": episode,
                               "matrix": primitive["matrix"], "prior": prior, "demand": demand,
                               "signal": signal, "adopted": adopted, "arrival": arrival, "deadline": deadline,
                               "count": rng.choices(protocol["request_counts"], protocol["request_count_weights"])[0],
                               "competitor": clock * rng.choice(regime["competitor_times"]),
                               "imitates": rng.random() < regime["imitation_probability"],
                               "imitation_lag": clock * rng.choice(regime["imitation_lags"]),
                               "build_uniform": rng.random(), "success_uniforms": [rng.random() for _ in range(64)],
                               "clock": clock, "times": times, "model_world": model})
    return result


def model_key(world: dict[str, Any]) -> str:
    return world["regime"] + "|" + world["matrix"]


def arrival_choice(world: dict[str, Any], primitive: dict[str, Any], protocol: dict[str, Any], now: float) -> str:
    remaining = max(0.0, world["deadline"] - now)
    multiplier = protocol["regimes"][world["regime"]]["build_multiplier"]
    build = primitive["build_seconds"] * multiplier
    ready = primitive["ready_seconds"] + primitive["validation_seconds"]
    competitor_now = world["competitor"] <= now
    rent = ready if competitor_now else primitive["cold_seconds"] + primitive["validation_seconds"]
    rent_success = primitive["ready_success_rate"] if competitor_now else primitive["cold_success_rate"]
    rented = min(world["count"], int(remaining / rent))
    built = min(world["count"], max(0, int((remaining - build) / ready)))
    credit = protocol["utility"]["credit_per_qualified_ontime_request"]
    cost = protocol["utility"]["credit_cost_per_clock_unit_compute"] / world["clock"]
    amortization = build / protocol["competitor_shared_build_amortization_requests"] if competitor_now else 0.0
    rent_value = credit * rented * rent_success - cost * rented * (rent + amortization)
    build_value = credit * built * primitive["ready_success_rate"] * primitive.get("build_success_rate", 1.0)
    build_value -= cost * (build + built * ready)
    values = {"rent": rent_value, "build": build_value, "defer": 0.0}
    return max(values, key=lambda key: (values[key], -["defer", "rent", "build"].index(key)))


def execute(world: dict[str, Any], primitive: dict[str, Any], protocol: dict[str, Any], plan: str,
            acquired: bool = False, controller_seconds: float = 0.0,
            dispatch_seconds: float | None = None) -> dict[str, Any]:
    clock, times = world["clock"], world["times"]
    signal_cost = protocol["signal_acquisition_clock_units"] * clock if acquired else 0.0
    now = signal_cost + (controller_seconds if dispatch_seconds is None else dispatch_seconds)
    ready_at = math.inf
    competitor = world["competitor"]
    result: dict[str, Any] = {k: 0.0 for k in METRICS}
    result.update({"plan": plan, "signal_seconds": signal_cost, "bought_signal": int(acquired),
                   "accepted": 0, "attempted": 0, "missed": 0, "failed_attempts": 0, "built": 0, "event": 0})

    def construct() -> None:
        nonlocal now, ready_at, competitor
        result["built"] = 1
        result["build_seconds"] += times["build"]
        now += times["build"]
        if world["build_uniform"] < primitive.get("build_success_rate", 1.0):
            ready_at = now
            if world["imitates"]:
                competitor = min(competitor, ready_at + world["imitation_lag"])
        else:
            result["failed_compute_seconds"] += times["build"]
    if plan == "build":
        construct()
    if world["demand"] and world["adopted"]:
        now = max(now, world["arrival"])
        if plan in ("adaptive", "wait") and now < world["deadline"]:
            chosen = arrival_choice(world, primitive, protocol, now) if plan == "adaptive" else "build"
            if chosen == "build":
                construct()
            if chosen == "defer":
                plan = "defer"
        if plan != "defer":
            for uniform in world["success_uniforms"][:world["count"]]:
                use_ready = now >= ready_at or now >= competitor
                shared = now >= competitor and now < ready_at
                estimate = primitive["ready_seconds"] if use_ready else primitive["cold_seconds"]
                estimate += primitive["validation_seconds"]
                if now + estimate > world["deadline"]:
                    break
                solve = times["ready"] if use_ready else times["cold"]
                duration = solve + times["validation"]
                now += duration
                amortization = (times["build"] / protocol["competitor_shared_build_amortization_requests"]
                                if shared else 0.0)
                success_rate = primitive["ready_success_rate"] if use_ready else primitive["cold_success_rate"]
                passed = uniform < success_rate
                on_time = now <= world["deadline"]
                result["attempted"] += 1
                result["numerically_qualified"] += int(passed)
                result["accepted"] += int(passed and on_time)
                result["solve_seconds"] += solve
                result["validation_seconds"] += times["validation"]
                result["competitor_amortization_seconds"] += amortization
                if not passed:
                    result["failed_attempts"] += 1
                    result["failed_compute_seconds"] += duration + amortization
                if not on_time:
                    result["late_attempts"] += 1
                    result["late_qualified"] += int(passed)
                    result["late_numerical_wall_seconds"] += duration
                if passed and on_time and now <= protocol["forecast_deadline_clock_units"] * clock:
                    result["event"] = 1
        result["missed"] = world["count"] - result["accepted"]
    result["last_completion_seconds"] = now
    result["readiness_seconds"] = ready_at if math.isfinite(ready_at) else None
    result["alternative_arrival_seconds"] = competitor
    native_compute = sum(result[k] for k in ("build_seconds", "solve_seconds", "validation_seconds",
                                            "signal_seconds", "competitor_amortization_seconds"))
    credit = protocol["utility"]["credit_per_qualified_ontime_request"]
    cost = protocol["utility"]["credit_cost_per_clock_unit_compute"] / clock
    result["compute_seconds"] = native_compute
    result["numerical_wall_seconds"] = sum(result[k] for k in ("build_seconds", "solve_seconds", "validation_seconds"))
    result["assumed_wall_equivalent_seconds"] = signal_cost + result["competitor_amortization_seconds"]
    result["accounted_cost_seconds"] = native_compute + controller_seconds
    result["credits_without_controller"] = credit * result["accepted"] - cost * native_compute
    result["mission_credits"] = result["credits_without_controller"] - cost * controller_seconds
    return result


def fit_model(rows: list[dict[str, Any]], protocol: dict[str, Any], seeds: list[int]) -> dict[str, Any]:
    started = time.process_time()
    primitives = {x["matrix"]: x for x in rows}
    accum: dict[str, Any] = {}
    bank = worlds(rows, protocol, seeds, model=True)
    for world in bank:
        key = model_key(world)
        entry = accum.setdefault(key, {"n": 0, "cells": {}})
        entry["n"] += 1
        for acquired in (False, True):
            for demand in (False, True):
                counterfactual = {**world, "demand": demand}
                for plan in (*PLANS, "wait"):
                    outcome = execute(counterfactual, primitives[world["matrix"]], protocol, plan, acquired)
                    label = f"{int(acquired)}|{int(demand)}|{plan}"
                    cell = entry["cells"].setdefault(label, [0.0, 0.0])
                    cell[0] += outcome["mission_credits"]
                    cell[1] += outcome["event"]
    for entry in accum.values():
        entry["cells"] = {k: [v / entry["n"] for v in values] for k, values in entry["cells"].items()}
    fitted = {"tables": accum, "training_seeds": seeds, "training_worlds": len(bank),
              "static_rules": {}, "conventional_rules": {},
              "information_cutoff": "before confirmation seeds; finite simulated model bank only"}
    for key in accum:
        regime_name = key.split("|", 1)[0]
        regime = protocol["regimes"][regime_name]
        for base in protocol["base_demand_probabilities"]:
            prior = base * regime["demand_multiplier"]
            rule_key = key + "|" + format(prior, ".12g")
            values = expectations(fitted, key, prior, False)
            plan = best_plan(values)
            fitted["static_rules"][rule_key] = [plan, values[plan][1]]
            accuracy = regime["signal_accuracy_model"]
            p_signal = prior * accuracy + (1 - prior) * (1 - accuracy)
            initial = conventional_enumeration(fitted, key, prior, False)
            options = [conventional_enumeration(fitted, key, posterior(prior, accuracy, signal), True)
                       for signal in (False, True)]
            voi = (1 - p_signal) * options[0][1] + p_signal * options[1][1] - initial[1]
            fitted["conventional_rules"][rule_key] = {"initial": initial, "posterior": options, "voi": voi}
    fitted["preparation_cpu_seconds"] = time.process_time() - started
    return fitted


def expectations(model: dict[str, Any], key: str, prior: float, acquired: bool) -> dict[str, tuple[float, float]]:
    cells = model["tables"][key]["cells"]
    return {plan: tuple((1 - prior) * cells[f"{int(acquired)}|0|{plan}"][i]
                        + prior * cells[f"{int(acquired)}|1|{plan}"][i] for i in (0, 1)) for plan in PLANS}


def best_plan(values: dict[str, tuple[float, float]]) -> str:
    return max(PLANS, key=lambda p: (values[p][0], -PLANS.index(p)))


def conventional_enumeration(model: dict[str, Any], key: str, prior: float,
                            acquired: bool) -> tuple[str, float, float]:
    cells = model["tables"][key]["cells"]
    winner, utility, probability = PLANS[0], -math.inf, 0.0
    for plan in PLANS:
        score, event = 0.0, 0.0
        for demand, weight in ((0, 1 - prior), (1, prior)):
            cell = cells[f"{int(acquired)}|{demand}|{plan}"]
            score += weight * cell[0]
            event += weight * cell[1]
        if score > utility:
            winner, utility, probability = plan, score, event
    return winner, utility, probability


def select(policy: str, world: dict[str, Any], model: dict[str, Any], protocol: dict[str, Any],
           primitive: dict[str, Any]) -> tuple[str, bool, float, float, int]:
    key, prior = model_key(world), world["prior"]
    accuracy = protocol["regimes"][world["regime"]]["signal_accuracy_model"]
    p_signal = prior * accuracy + (1 - prior) * (1 - accuracy)
    if policy == "clairvoyant_menu":
        candidates = {p: execute(world, primitive, protocol, p) for p in (*PLANS, "wait")}
        plan = max(candidates, key=lambda p: candidates[p]["mission_credits"])
        return plan, False, float(candidates[plan]["event"]), 0.0, len(candidates)
    if policy in ("wait_and_act", "adaptive_nonforecast"):
        plan = "wait" if policy == "wait_and_act" else "adaptive"
        return plan, False, 0.0, 0.0, 0
    if policy == "forecast_only":
        p = posterior(prior, accuracy, world["signal"])
        return "rent", True, expectations(model, key, p, True)["rent"][1], 0.0, 1
    if policy == "static_expert":
        plan, probability = model["static_rules"][key + "|" + format(prior, ".12g")]
        return plan, False, probability, 0.0, 0
    if policy == "adaptive_same_signal":
        rule = model["conventional_rules"][key + "|" + format(prior, ".12g")]
        prior_plan, _, prior_event = rule["initial"]
        options, voi = rule["posterior"], rule["voi"]
        if voi > 1e-12:
            chosen = options[int(world["signal"])]
            return chosen[0], True, chosen[2], voi, 0
        return prior_plan, False, prior_event, voi, 0
    if policy != "constructive_foresight":
        raise ValueError(f"Unknown policy {policy}")
    values = expectations(model, key, prior, False)
    prior_plan = best_plan(values)
    post_values = [expectations(model, key, posterior(prior, accuracy, signal), True) for signal in (False, True)]
    post_plans = [best_plan(v) for v in post_values]
    future = (1 - p_signal) * post_values[0][post_plans[0]][0] + p_signal * post_values[1][post_plans[1]][0]
    voi = future - values[prior_plan][0]
    if voi > 1e-12:
        chosen = int(world["signal"])
        return post_plans[chosen], True, post_values[chosen][post_plans[chosen]][1], voi, 3 * len(PLANS)
    return prior_plan, False, values[prior_plan][1], voi, 3 * len(PLANS)


def evaluate(rows: list[dict[str, Any]], protocol: dict[str, Any], model: dict[str, Any], seeds: list[int],
             model_world: bool) -> list[dict[str, Any]]:
    primitives = {x["matrix"]: x for x in rows}
    result = []
    amortization = (len(protocol["seeds"]["confirmation"]) * len(protocol["regimes"])
                    * protocol["episodes_per_seed_per_regime"])
    for world in worlds(rows, protocol, seeds, model=model_world):
        order = list(POLICIES)
        random.Random(world["seed"] * 1000 + world["episode"]).shuffle(order)
        for policy in order:
            cpu, wall = time.process_time(), time.perf_counter()
            plan, acquired, probability, voi, searches = select(policy, world, model, protocol, primitives[world["matrix"]])
            decision_cpu, decision_wall = time.process_time() - cpu, time.perf_counter() - wall
            output = execute(world, primitives[world["matrix"]], protocol, plan, acquired,
                             0.0 if policy == "clairvoyant_menu" else decision_cpu,
                             0.0 if policy == "clairvoyant_menu" else decision_wall)
            if policy == "clairvoyant_menu":
                output["oracle_menu_bound_credits"] = output["credits_without_controller"]
                output["mission_credits"] -= (protocol["utility"]["credit_cost_per_clock_unit_compute"]
                                             * decision_cpu / world["clock"])
            forecast_role = "policy_conditional_model_forecast"
            offline_evaluator_cpu = 0.0
            if policy in ("wait_and_act", "adaptive_nonforecast"):
                evaluation_started = time.process_time()
                cells = model["tables"][model_key(world)]["cells"]
                probability = ((1 - world["prior"]) * cells[f"0|0|{plan}"][1]
                               + world["prior"] * cells[f"0|1|{plan}"][1])
                offline_evaluator_cpu = time.process_time() - evaluation_started
                forecast_role = "offline_shared_evaluator_only"
            if policy == "clairvoyant_menu":
                forecast_role = "clairvoyant_reference_not_a_forecast"
            prep = model["preparation_cpu_seconds"] / amortization if policy in MODEL_USERS else 0.0
            output.update({"regime": world["regime"], "seed": world["seed"], "episode": world["episode"],
                           "matrix": world["matrix"], "policy": policy, "decision_cpu_seconds": decision_cpu,
                           "decision_wall_seconds": decision_wall, "preparation_cpu_seconds": prep,
                           "forecast_probability": probability, "brier": (probability - output["event"]) ** 2,
                           "forecast_role": forecast_role, "offline_evaluator_cpu_seconds": offline_evaluator_cpu,
                           "modeled_net_voi_credits": voi, "candidate_evaluations": searches,
                           "prior": world["prior"], "demand": int(world["demand"]), "adopted": int(world["adopted"]),
                           "arrival_seconds": world["arrival"], "expiry_seconds": world["deadline"],
                           "requests": world["count"], "model_world": int(model_world),
                           "observed_signal": int(world["signal"]) if acquired else "unacquired"})
            output["compute_seconds"] += decision_cpu + prep
            output["accounted_cost_seconds"] = output["compute_seconds"]
            output["mission_credits"] -= protocol["utility"]["credit_cost_per_clock_unit_compute"] * prep / world["clock"]
            result.append(output)
    return result


def mean_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {key: statistics.fmean(x[key] for x in rows) for key in METRICS}


def summarize(observations: list[dict[str, Any]], protocol: dict[str, Any], comparator: str,
              bootstrap: bool) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    blocks: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    by_episode: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    calibration: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        groups[row["regime"], row["policy"]].append(row)
        blocks[row["regime"], row["policy"], row["seed"]].append(row)
        by_episode[row["regime"], row["seed"], row["episode"]][row["policy"]] = row
        if row["forecast_role"] == "policy_conditional_model_forecast":
            calibration[row["regime"], row["policy"], min(9, int(row["forecast_probability"] * 10))].append(row)
    comparisons = {}
    rng = random.Random(protocol["bootstrap_seed"])
    for regime in protocol["regimes"]:
        seeds = sorted({key[2] for key in blocks if key[0] == regime})
        paired = []
        for seed in seeds:
            cf = mean_metrics(blocks[regime, "constructive_foresight", seed])
            baseline = mean_metrics(blocks[regime, comparator, seed])
            paired.append({metric: cf[metric] - baseline[metric]
                           for metric in ("mission_credits", "credits_without_controller", "accepted",
                                          "accounted_cost_seconds", "numerical_wall_seconds", "late_attempts")})
        intervals = {}
        for metric in paired[0]:
            values = [pair[metric] for pair in paired]
            samples = sorted(statistics.fmean(rng.choices(values, k=len(values)))
                             for _ in range(protocol["bootstrap_resamples"])) if bootstrap else []
            intervals[metric] = {"mean_difference": statistics.fmean(values),
                                 "paired_seed_block_bootstrap_95": ([samples[int(0.025 * len(samples))],
                                                                     samples[min(len(samples)-1, int(0.975 * len(samples)))]]
                                                                    if samples else None)}
        episode_rows = [value for key, value in by_episode.items() if key[0] == regime]
        harms = sum(v["constructive_foresight"]["mission_credits"] < v[comparator]["mission_credits"] - 1e-12
                    for v in episode_rows)
        without_overhead_harms = sum(v["constructive_foresight"]["credits_without_controller"]
                                    < v[comparator]["credits_without_controller"] - 1e-12 for v in episode_rows)
        disagreements = sum((v["constructive_foresight"]["plan"], v["constructive_foresight"]["bought_signal"])
                            != (v["adaptive_same_signal"]["plan"], v["adaptive_same_signal"]["bought_signal"])
                            for v in episode_rows)
        comparisons[regime] = {"comparator": comparator, "episodes": len(episode_rows), "seed_blocks": len(seeds),
                               "differences": intervals, "full_cost_harm_episodes": harms,
                               "native_model_harm_episodes": without_overhead_harms,
                               "cf_same_signal_action_disagreements": disagreements}
    return {"policy_means": [{"regime": k[0], "policy": k[1], "n": len(v),
                              "forecast_role": v[0]["forecast_role"], **mean_metrics(v)}
                              for k, v in sorted(groups.items())],
            "seed_blocks": [{"regime": k[0], "policy": k[1], "seed": k[2], **mean_metrics(v)}
                            for k, v in sorted(blocks.items())],
            "calibration_bins": [{"regime": k[0], "policy": k[1], "bin": k[2], "n": len(v),
                                  "mean_forecast": statistics.fmean(x["forecast_probability"] for x in v),
                                  "event_fraction": statistics.fmean(x["event"] for x in v)}
                                 for k, v in sorted(calibration.items())],
            "primary_comparisons": comparisons}


def save_observations(path: Path, observations: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in observations for key in row})
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(observations)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("engineering", "calibrate", "freeze", "confirm"), required=True)
    parser.add_argument("--primitives", type=Path)
    parser.add_argument("--protocol", type=Path, default=ROOT / "decision_protocol.json")
    parser.add_argument("--training", type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = read_json(args.protocol)
    rows = load_primitives(args.primitives, args.phase == "engineering")
    hashes = {"decision.py": digest(Path(__file__)), "decision_protocol.json": digest(args.protocol),
              "primitives": digest(args.primitives) if args.primitives else "synthetic-engineering-fixture"}
    if args.training:
        hashes["training"] = digest(args.training)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.phase == "freeze":
        if not args.training:
            raise ValueError("Freeze requires the calibration training file")
        target = args.freeze or args.output / "decision_freeze.json"
        with target.open("x", encoding="utf-8") as stream:
            json.dump({"hashes": hashes, "created_utc": datetime.now(timezone.utc).isoformat(),
                       "confirmation_seeds": protocol["seeds"]["confirmation"],
                       "archive_requirement": "Root must preserve and reopen this manifest and payload before confirmation"},
                      stream, indent=2)
        print(json.dumps({"freeze": str(target), "sha256": digest(target)}))
        return
    if args.phase == "confirm":
        if not args.training or not args.freeze:
            raise ValueError("Confirmation requires frozen training and an archived freeze manifest")
        frozen = read_json(args.freeze)
        if frozen["hashes"] != hashes:
            raise ValueError("Source/protocol/primitives/training changed after freeze")
        training = read_json(args.training)
        model = training["model"]
        comparator = training["primary_comparator"]
        seeds = protocol["seeds"]["confirmation"]
    else:
        seeds = protocol["seeds"]["engineering" if args.phase == "engineering" else "calibration"]
        model = fit_model(rows, protocol, seeds)
        comparator = "adaptive_same_signal"
    observations = evaluate(rows, protocol, model, seeds, model_world=args.phase == "calibrate")
    if args.phase != "confirm":
        eligible = [p for p in POLICIES if p not in ("constructive_foresight", "clairvoyant_menu")]
        scores = {p: statistics.fmean(x["mission_credits"] for x in observations if x["policy"] == p) for p in eligible}
        comparator = max(eligible, key=lambda p: scores[p])
        training = {"model": model, "primary_comparator": comparator, "calibration_comparator_scores": scores,
                    "hashes": hashes, "phase": args.phase,
                    "created_utc": datetime.now(timezone.utc).isoformat()}
        write_json(args.output / "decision_training.json", training)
    summary = summarize(observations, protocol, comparator, bootstrap=args.phase == "confirm")
    summary.update({"phase": args.phase, "evidence_class": protocol["evidence_class"], "hashes": hashes,
                    "clock_seconds": statistics.median(x["build_seconds"] for x in rows),
                    "preparation_cpu_seconds": model["preparation_cpu_seconds"], "primary_comparator": comparator,
                    "created_utc": datetime.now(timezone.utc).isoformat(), "observations": len(observations),
                    "metric_labels": {
                        "numerical_wall_seconds": "Numerical runtime: measured perf_counter wall seconds, replayed in simulation",
                        "assumed_wall_equivalent_seconds": "Assumed signal runtime and amortized competitor runtime seconds",
                        "decision_cpu_seconds": "Measured controller CPU seconds",
                        "decision_wall_seconds": "Measured controller wall seconds, used for dispatch delay",
                        "preparation_cpu_seconds": "Allocated measured model-preparation CPU seconds",
                        "accounted_cost_seconds": "Mixed accounted seconds: numerical wall + assumed runtime + controller/preparation CPU; one explicitly assumed price per second",
                        "compute_seconds": "Legacy alias of accounted_cost_seconds; not measured CPU seconds",
                        "late_numerical_wall_seconds": "Wall runtime of late attempts; subset of numerical_wall_seconds, never added again",
                        "brier": "Policy forecast score only when forecast_role is policy_conditional_model_forecast; other scores are offline diagnostics",
                        "offline_evaluator_cpu_seconds": "Study evaluation overhead outside deployment cost; wait/nonforecast forecasts are shared offline estimates"},
                    "warning": "Simulation only. No beneficiary adoption, revenue, financial return or AGI forecast is observed."})
    save_observations(args.output / "decision_observations.csv.gz", observations)
    write_json(args.output / "decision_summary.json", summary)
    print(json.dumps({"phase": args.phase, "observations": len(observations), "comparator": comparator,
                      "output": str(args.output), "clock_seconds": summary["clock_seconds"]}))


if __name__ == "__main__":
    main()
