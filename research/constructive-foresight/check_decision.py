# SPDX-License-Identifier: Apache-2.0
"""Independent ledger/seed/freeze audit; never imports or executes decision.py.

This checks retained model evidence, not the truth of its adoption, demand,
competition, value, linear service-time or cost-equivalence assumptions.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MODEL_USERS = {"forecast_only", "constructive_foresight", "static_expert", "adaptive_same_signal"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def frozen_prediction(row: dict[str, str], model: dict[str, Any], protocol: dict[str, Any]) -> tuple[str, bool, float, float]:
    """Reconstruct policy choice/probability from frozen tables and allowed inputs."""
    policy, prior = row["policy"], float(row["prior"])
    cells = model["tables"][row["regime"] + "|" + row["matrix"]]["cells"]
    accuracy = protocol["regimes"][row["regime"]]["signal_accuracy_model"]
    plans = protocol["plans"]

    def expectation(plan: str, p: float, acquired: bool) -> tuple[float, float]:
        absent, present = cells[f"{int(acquired)}|0|{plan}"], cells[f"{int(acquired)}|1|{plan}"]
        return tuple(math.fsum(((1 - p) * absent[j], p * present[j])) for j in (0, 1))

    def best(p: float, acquired: bool) -> tuple[str, float, float]:
        evaluations = [(plan, *expectation(plan, p, acquired)) for plan in plans]
        return max(evaluations, key=lambda item: (item[1], -plans.index(item[0])))

    def posterior(signal: bool) -> float:
        positive = prior * (accuracy if signal else 1 - accuracy)
        total = positive + (1 - prior) * (1 - accuracy if signal else accuracy)
        return positive / total if total else prior

    if policy in ("wait_and_act", "adaptive_nonforecast"):
        plan = "wait" if policy == "wait_and_act" else "adaptive"
        return plan, False, expectation(plan, prior, False)[1], 0.0
    if policy == "forecast_only":
        observed = int(row["observed_signal"])
        return "rent", True, expectation("rent", posterior(bool(observed)), True)[1], 0.0
    prior_plan, prior_utility, prior_event = best(prior, False)
    if policy == "static_expert":
        return prior_plan, False, prior_event, 0.0
    if policy not in ("constructive_foresight", "adaptive_same_signal"):
        raise ValueError("No deployable forecast reconstruction for this policy")
    branches = [best(posterior(signal), True) for signal in (False, True)]
    positive_signal_probability = prior * accuracy + (1 - prior) * (1 - accuracy)
    voi = math.fsum(((1 - positive_signal_probability) * branches[0][1],
                    positive_signal_probability * branches[1][1])) - prior_utility
    if voi > 1e-12:
        chosen = branches[int(row["observed_signal"])]
        return chosen[0], True, chosen[2], voi
    return prior_plan, False, prior_event, voi


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("observations", "summary", "training", "freeze", "primitives", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=HERE / "decision_protocol.json")
    parser.add_argument("--source", type=Path, default=HERE / "decision.py")
    parser.add_argument("--invocation", type=Path, help="Optional externally retained confirmation start/end record")
    args = parser.parse_args()
    protocol, summary, training, frozen = map(load, (args.protocol, args.summary, args.training, args.freeze))
    primitive_file = load(args.primitives)
    primitives = primitive_file["matrices"] if isinstance(primitive_file, dict) else primitive_file
    primitives = sorted(primitives, key=lambda row: row["matrix"])
    with gzip.open(args.observations, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    failures: list[str] = []
    checks = 0

    def require(condition: Any, label: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    def number(actual: float, expected: float, label: str) -> None:
        require(math.isfinite(actual) and math.isfinite(expected) and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-10), label)

    hashes = {"decision.py": sha(args.source), "decision_protocol.json": sha(args.protocol),
              "primitives": sha(args.primitives), "training": sha(args.training)}
    require(frozen["hashes"] == hashes, "Frozen source/protocol/primitives/training hashes")
    require(summary["hashes"] == hashes, "Confirmation hashes equal freeze")
    require(training["hashes"] == {key: value for key, value in hashes.items() if key != "training"}, "Calibration training input provenance")
    require(training["phase"] == "calibrate", "Training is calibration")
    require(training["model"]["training_seeds"] == protocol["seeds"]["calibration"], "Only calibration seeds in fitted model")
    require(set(protocol["seeds"]["calibration"]).isdisjoint(protocol["seeds"]["confirmation"]), "Disjoint calibration/confirmation seeds")
    require(frozen["confirmation_seeds"] == protocol["seeds"]["confirmation"], "Frozen confirmation seed list")
    require(instant(training["created_utc"]) <= instant(frozen["created_utc"]) <= instant(summary["created_utc"]), "Training/freeze/summary timestamp order")
    require(summary["phase"] == "confirm", "Confirmation phase")
    invocation_checked = False
    if args.invocation:
        invocation = load(args.invocation)
        require(instant(frozen["created_utc"]) < instant(invocation["issued_utc"]) <= instant(summary["created_utc"]) <= instant(invocation["completed_utc"]), "External invocation brackets confirmation after freeze")
        require(invocation.get("state") == "completed" and invocation.get("returncode") == 0,
                "External invocation completed successfully")
        command = invocation["command"]
        require("--phase" in command and command[command.index("--phase") + 1] == "confirm",
                "External invocation is confirmation")
        if "freeze_sha256" in invocation:
            require(invocation["freeze_sha256"] == sha(args.freeze), "Invocation freeze hash")
        invocation_hashes = invocation.get("hashes", {})
        for relative, committed_hash in invocation_hashes.items():
            require(sha(args.source.parent / relative) == committed_hash, "Invocation source/input binding: " + relative)
        recorded_freeze = [value for key, value in invocation_hashes.items() if Path(key).name == args.freeze.name]
        require(invocation.get("freeze_sha256") == sha(args.freeze) or recorded_freeze == [sha(args.freeze)],
                "External invocation binds exact decision freeze")
        invocation_checked = True
    eligible = [p for p in protocol["policies"] if p not in ("constructive_foresight", "clairvoyant_menu")]
    scores = training["calibration_comparator_scores"]
    require(set(scores) == set(eligible), "All eligible calibration comparator scores retained")
    comparator = max(eligible, key=lambda policy: scores[policy])
    require(comparator == training["primary_comparator"] == summary["primary_comparator"], "Strongest calibration comparator fixed")
    expected = {(regime, seed, episode, policy) for regime in protocol["regimes"] for seed in protocol["seeds"]["confirmation"] for episode in range(protocol["episodes_per_seed_per_regime"]) for policy in protocol["policies"]}
    keys = [(r["regime"], int(r["seed"]), int(r["episode"]), r["policy"]) for r in rows]
    require(len(keys) == len(set(keys)), "No duplicate episode-policy cells")
    require(set(keys) == expected, "Every preregistered cell retained exactly once")
    require(summary["observations"] == len(rows), "Summary observation count")
    clock = statistics.median(p["build_seconds"] for p in primitives)
    number(summary["clock_seconds"], clock, "One calibration-only clock scale")
    credit = protocol["utility"]["credit_per_qualified_ontime_request"]
    cost = protocol["utility"]["credit_cost_per_clock_unit_compute"] / clock
    amortization = len(protocol["seeds"]["confirmation"]) * len(protocol["regimes"]) * protocol["episodes_per_seed_per_regime"]
    by_world: dict[tuple[str, int, int], dict[str, dict[str, str]]] = defaultdict(dict)
    by_policy: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    reported = {(r["regime"], r["policy"]): r for r in summary["policy_means"]}
    for row in rows:
        key = (row["regime"], int(row["seed"]), int(row["episode"]))
        label = ":".join(map(str, (*key, row["policy"])))
        by_world[key][row["policy"]] = row
        by_policy[row["regime"], row["policy"]].append(row)
        value = lambda field: float(row[field])
        for field in ("accepted", "attempted", "missed", "requests", "numerically_qualified", "failed_attempts",
                      "late_attempts", "late_qualified", "event", "built", "bought_signal"):
            require(math.isfinite(value(field)) and value(field) >= 0 and value(field).is_integer(),
                    label + ": nonnegative integer " + field)
        for field in ("event", "built", "bought_signal"):
            require(value(field) <= 1, label + ": Boolean " + field)
        for field in ("build_seconds", "solve_seconds", "validation_seconds", "signal_seconds", "competitor_amortization_seconds",
                      "decision_cpu_seconds", "decision_wall_seconds", "preparation_cpu_seconds", "offline_evaluator_cpu_seconds",
                      "failed_compute_seconds", "late_numerical_wall_seconds", "compute_seconds", "accounted_cost_seconds"):
            require(math.isfinite(value(field)) and value(field) >= 0, label + ": nonnegative " + field)
        require(row["matrix"] == primitives[int(row["episode"]) % len(primitives)]["matrix"], label + ": fixed matrix allocation")
        require(int(row["model_world"]) == 0, label + ": confirmation uses actual stress distributions")
        require(0 <= value("accepted") <= value("attempted") <= value("requests"), label + ": accepted/attempted/request ordering")
        require(value("numerically_qualified") == value("accepted") + value("late_qualified"), label + ": qualified separates late work")
        require(value("failed_attempts") + value("numerically_qualified") == value("attempted"), label + ": every attempt classified")
        require(0 <= value("late_qualified") <= value("late_attempts") <= value("attempted"), label + ": late attempt bounds")
        require(0 <= value("event") <= min(1, value("accepted")), label + ": event requires accepted delivery")
        native = math.fsum(value(field) for field in ("build_seconds", "solve_seconds", "validation_seconds", "signal_seconds", "competitor_amortization_seconds"))
        full = native + value("decision_cpu_seconds") + value("preparation_cpu_seconds")
        number(value("compute_seconds"), full, label + ": full cost decomposition")
        number(value("accounted_cost_seconds"), full, label + ": accounted cost")
        number(value("numerical_wall_seconds"), value("build_seconds") + value("solve_seconds") + value("validation_seconds"), label + ": numerical wall time")
        number(value("credits_without_controller"), credit * value("accepted") - cost * native, label + ": mission value before controller")
        number(value("mission_credits"), credit * value("accepted") - cost * full, label + ": full-cost mission value")
        require(value("failed_compute_seconds") <= native + 1e-10, label + ": failure cost subset, not double-added")
        require(value("late_numerical_wall_seconds") <= value("solve_seconds") + value("validation_seconds") + 1e-10, label + ": late cost subset")
        expected_prep = training["model"]["preparation_cpu_seconds"] / amortization if row["policy"] in MODEL_USERS else 0.0
        number(value("preparation_cpu_seconds"), expected_prep, label + ": independent deployment preparation allocation")
        require(0 <= value("forecast_probability") <= 1, label + ": probability bounds")
        number(value("brier"), (value("forecast_probability") - value("event")) ** 2, label + ": Brier score")
        offline = row["policy"] in ("wait_and_act", "adaptive_nonforecast")
        require((row["forecast_role"] == "offline_shared_evaluator_only") == offline, label + ": offline evaluator separation")
        if row["policy"] == "clairvoyant_menu":
            require(row["forecast_role"] == "clairvoyant_reference_not_a_forecast", label + ": oracle excluded from forecasts")
        else:
            predicted_plan, acquired, probability, voi = frozen_prediction(row, training["model"], protocol)
            require(row["plan"] == predicted_plan, label + ": chosen plan reconstructed from frozen model")
            require(bool(value("bought_signal")) == acquired, label + ": acquisition decision reconstructed from frozen model")
            number(value("forecast_probability"), probability, label + ": frozen policy-conditional probability")
            number(value("modeled_net_voi_credits"), voi, label + ": frozen information value")
        if int(float(row["bought_signal"])):
            require(row["observed_signal"] in ("0", "1"), label + ": acquired signal explicit")
        else:
            require(row["observed_signal"] == "unacquired", label + ": no unbought signal exposed")
        number(value("signal_seconds"), protocol["signal_acquisition_clock_units"] * clock * value("bought_signal"), label + ": information acquisition cost")
        missed = value("requests") - value("accepted") if int(row["demand"]) and int(row["adopted"]) else 0.0
        number(value("missed"), missed, label + ": unmet adopted demand")
        require(value("arrival_seconds") >= 0 and value("expiry_seconds") >= 0 and value("last_completion_seconds") >= 0,
                label + ": nonnegative model times")
        deadline = protocol["forecast_deadline_clock_units"] * clock
        if value("arrival_seconds") > deadline:
            require(value("event") == 0, label + ": late arrival cannot resolve early delivery")
        if value("accepted") > 0 and value("last_completion_seconds") <= deadline:
            require(value("event") == 1, label + ": early completed accepted work resolves event")
        if value("late_attempts") > 0:
            require(value("last_completion_seconds") > value("expiry_seconds"), label + ": late attempt ends after expiry")
        elif value("accepted") > 0:
            require(value("last_completion_seconds") <= value("expiry_seconds"), label + ": all completions before expiry")
    shared = ("matrix", "prior", "demand", "adopted", "arrival_seconds", "expiry_seconds", "requests")
    disagreements = 0
    for key, world_rows in by_world.items():
        reference = world_rows["constructive_foresight"]
        for policy, row in world_rows.items():
            require(all(row[field] == reference[field] for field in shared), str(key) + ": common exogenous world " + policy)
        other = world_rows["adaptive_same_signal"]
        disagreements += int((reference["plan"], reference["bought_signal"]) != (other["plan"], other["bought_signal"]))
    comparisons = []
    require(set(reported) == set(by_policy), "Every policy mean reported exactly once")
    for (regime, policy), group in sorted(by_policy.items()):
        require(set(("mission_credits", "accepted", "compute_seconds", "brier", "late_attempts")) <= set(reported[regime, policy]), f"{regime}:{policy}: required mean metrics")
        for metric, metric_value in reported[regime, policy].items():
            if metric not in ("regime", "policy", "n", "forecast_role"):
                number(metric_value, statistics.fmean(float(row[metric]) for row in group), f"{regime}:{policy}: reported {metric}")
        require(all(row["forecast_role"] == reported[regime, policy]["forecast_role"] for row in group),
                f"{regime}:{policy}: reported forecast role")
        require(reported[regime, policy]["n"] == len(group), f"{regime}:{policy}: mean sample count")
    for regime in protocol["regimes"]:
        for baseline in eligible:
            pairs = [float(world["constructive_foresight"]["mission_credits"]) - float(world[baseline]["mission_credits"]) for key, world in by_world.items() if key[0] == regime]
            comparisons.append({"regime": regime, "comparator": baseline, "paired_episodes": len(pairs),
                                "mean_cf_minus_comparator": statistics.fmean(pairs),
                                "cf_worse_episodes": sum(v < -1e-12 for v in pairs)})
    seed_groups: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        seed_groups[row["regime"], row["policy"], int(row["seed"])].append(row)
    seed_reports = {(r["regime"], r["policy"], r["seed"]): r for r in summary["seed_blocks"]}
    require(set(seed_reports) == set(seed_groups), "Every seed block reported")
    for key, group in seed_groups.items():
        for metric, metric_value in seed_reports[key].items():
            if metric not in ("regime", "policy", "seed"):
                number(metric_value, statistics.fmean(float(row[metric]) for row in group), str(key) + ": seed mean " + metric)
    bootstrap_rng = random.Random(protocol["bootstrap_seed"])
    require(set(summary["primary_comparisons"]) == set(protocol["regimes"]), "Every primary regime comparison retained")
    for regime in protocol["regimes"]:
        primary = summary["primary_comparisons"][regime]
        seeds = protocol["seeds"]["confirmation"]
        worlds_in_regime = [world for key, world in by_world.items() if key[0] == regime]
        require(primary["comparator"] == comparator and primary["episodes"] == len(worlds_in_regime) and primary["seed_blocks"] == len(seeds), regime + ": primary comparison identity")
        metrics = ("mission_credits", "credits_without_controller", "accepted", "accounted_cost_seconds",
                   "numerical_wall_seconds", "late_attempts")
        require(set(primary["differences"]) == set(metrics), regime + ": complete primary metrics")
        for metric in metrics:
            differences = [statistics.fmean(float(r[metric]) for r in seed_groups[regime, "constructive_foresight", seed]) -
                           statistics.fmean(float(r[metric]) for r in seed_groups[regime, comparator, seed]) for seed in seeds]
            number(primary["differences"][metric]["mean_difference"], statistics.fmean(differences), regime + ": primary mean " + metric)
            sampled = sorted(statistics.fmean(bootstrap_rng.choices(differences, k=len(differences))) for _ in range(protocol["bootstrap_resamples"]))
            interval = primary["differences"][metric]["paired_seed_block_bootstrap_95"]
            number(interval[0], sampled[int(0.025 * len(sampled))], regime + ": lower paired bootstrap " + metric)
            number(interval[1], sampled[min(len(sampled) - 1, int(0.975 * len(sampled)))], regime + ": upper paired bootstrap " + metric)
        for field, metric in (("full_cost_harm_episodes", "mission_credits"), ("native_model_harm_episodes", "credits_without_controller")):
            count = sum(float(w["constructive_foresight"][metric]) < float(w[comparator][metric]) - 1e-12 for w in worlds_in_regime)
            require(primary[field] == count, regime + ": primary harm count " + metric)
        local_disagreement = sum((w["constructive_foresight"]["plan"], w["constructive_foresight"]["bought_signal"]) !=
                                 (w["adaptive_same_signal"]["plan"], w["adaptive_same_signal"]["bought_signal"]) for w in worlds_in_regime)
        require(primary["cf_same_signal_action_disagreements"] == local_disagreement, regime + ": reported policy disagreement")
    calibration_groups: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["forecast_role"] == "policy_conditional_model_forecast":
            calibration_groups[row["regime"], row["policy"], min(9, int(float(row["forecast_probability"]) * 10))].append(row)
    calibration_reports = {(r["regime"], r["policy"], r["bin"]): r for r in summary["calibration_bins"]}
    require(set(calibration_reports) == set(calibration_groups), "Calibration bins exclude offline/oracle and retain all policy bins")
    for key, group in calibration_groups.items():
        require(calibration_reports[key]["n"] == len(group), str(key) + ": calibration bin count")
        number(calibration_reports[key]["mean_forecast"], statistics.fmean(float(r["forecast_probability"]) for r in group), str(key) + ": calibration mean forecast")
        number(calibration_reports[key]["event_fraction"], statistics.fmean(float(r["event"]) for r in group), str(key) + ": calibration event fraction")
    result = {"schema": "writer9-independent-decision-audit/v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "checker_sha256": sha(Path(__file__)), "source_imported": False, "checks": checks, "passed": not failures,
              "failures": failures, "rows": len(rows), "paired_worlds": len(by_world), "primary_comparator": comparator,
              "same_signal_action_disagreements": disagreements, "late_attempts_retained": sum(float(r["late_attempts"]) for r in rows),
              "external_start_record_checked": invocation_checked,
              "comparisons": comparisons, "hashes": hashes, "observations_sha256": sha(args.observations),
              "scope": "Internal arithmetic, frozen policy forecasts/choices, recorded information cutoffs, reported comparisons and source hashes checked. Exact first-qualified event timestamps are unretained; event-time bounds only are checked. Same operator; no external time authority, causal identification outside the model, adoption evidence or full unknown labor valuation."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"passed": result["passed"], "checks": checks, "failures": failures[:20], "output": str(args.output)}))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
