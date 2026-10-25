#!/usr/bin/env python3
"""Post-run consistency review; no producer imports or new candidate execution."""
from __future__ import annotations

import collections
import hashlib
import json
import math
import pathlib
import random
import statistics
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
RUN = ROOT / "results" / "confirmation-v1"
OUT = pathlib.Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def equal(actual, expected, label):
    if isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-10), (label, actual, expected)
    else:
        assert actual == expected, (label, actual, expected)


def bootstrap(values):
    generator = random.Random(20261024)
    means = []
    for _ in range(10000):
        draw = [values[generator.randrange(len(values))] for _ in values]
        means.append(sum(draw) / len(draw))
    means.sort()
    return statistics.fmean(values), [means[249], means[9749]]


def strategy_digest(value):
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    quoted = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(("successor-omega/v1:release-strategy\0" + quoted).encode()).hexdigest()


def without_name(value):
    if isinstance(value, dict):
        return {k: without_name(v) for k, v in value.items() if k != "name"}
    if isinstance(value, list):
        return [without_name(v) for v in value]
    return value


assert (RUN / "RUN_COMPLETE.json").exists(), "Terminal record required"
assert read(RUN / "RUN_START.json")["run_mode"] == "CONFIRMATION"
prior = read(OUT / "MAIN_INDEPENDENT_AUDIT.json")
assert prior["status"] == "PASS"
summary = read(RUN / "SUMMARY.json")
trials = [json.loads(line) for line in (RUN / "trials.jsonl").read_text().splitlines()]
native = [json.loads(line) for line in (RUN / "native-reference.jsonl").read_text().splitlines()]
equal(read(RUN / "NATIVE_REFERENCE.json")["rows"], native, "native duplicate representation")

# Independently derive every window from ledger positions and receipt indices.
for trial in trials:
    checkpoint = read(RUN / trial["artifact_path"] / "checkpoint.json")
    width = 24 if trial["category"] == "main" else math.ceil(trial["offered"] / 3)
    for number, reported in enumerate(trial["windows"]):
        receipts = [m for m in checkpoint["missions"] if min(2, m["index"] // width) == number]
        charge = sum(e["work"] for e in checkpoint["ledger"] if min(2, e["mission_index"] // width) == number)
        qualified = sum(m["qualified"] for m in receipts)
        expected = {"window": number + 1, "offered": 24 if trial["category"] == "main" else None,
                    "attempted": len(receipts), "qualified": qualified, "work": charge,
                    "qualified_per_100k_work": qualified * 100000 / charge if charge else None}
        for key, value in expected.items():
            equal(reported[key], value, (trial["artifact_path"], "window", number, key))

diagnostic = [r for r in trials if r["category"] == "diagnostic"]
diagnostic_verified = []
for reported in summary["diagnostic"]:
    treatment = reported["treatment"]
    group = [r for r in diagnostic if r["parent_treatment"] == treatment]
    expected = {
        "streams": len(group), "valid": sum(r["valid"] for r in group),
        "qualified": sum(r["qualified"] for r in group),
        "mean_work": statistics.fmean(r["work"] for r in group),
        "complete_three_stage_chains": sum({a["stage"] for a in r["assets"]} == {"dispatch", "lookahead", "repair"} for r in group),
        "active_three_stage_chains": sum({a["stage"] for a in r["assets"] if a["active"]} == {"dispatch", "lookahead", "repair"} for r in group),
        "gates": dict(collections.Counter(d["decision"] for r in group for d in r["discoveries"])),
        "dispatch_rollout_calls": sum(r["inherited_policy_calls"]["dispatch_rollouts"] for r in group),
        "lookahead_repair_decisions": sum(r["inherited_policy_calls"]["lookahead_repair_decisions"] for r in group),
        "reconstruction_exact_recoveries": sum(bool(e.get("exact_contents_recovered")) for r in group for e in r["constructive_events"]),
    }
    for key, value in expected.items():
        equal(reported[key], value, ("diagnostic", treatment, key))
    # Contents must really embed the declared predecessor's strategy.
    for trial in group:
        by_digest = {a["digest"]: a for a in trial["assets"]}
        for asset in trial["assets"]:
            equal(asset["gate"], "DIAGNOSTIC_CORRECTNESS_ONLY", "diagnostic gate")
            if asset["parent_digest"] is not None:
                base = asset["strategy"]["base"]
                equal(strategy_digest(base), asset["parent_digest"], "actual embedded predecessor identity")
                if asset["parent_digest"] in by_digest:
                    parent = by_digest[asset["parent_digest"]]
                    equal(base, parent["strategy"], "actual embedded predecessor")
                else:
                    assert treatment == "equivalent", "An unrecorded ancestor is not permitted"
                    event = next(e for e in trial["constructive_events"] if e["kind"] == "REPLACEMENT" and e["equivalent"] == asset["parent_digest"])
                    parent = by_digest[event["original"]]
                    equal(without_name(base), without_name(parent["strategy"]), "equivalent replacement keeps executable contents")
    diagnostic_verified.append({"treatment": treatment, **expected})

pair_checks = []
for reported in summary["diagnostic_pairs"]:
    candidates = {r["parent_treatment"]: r for r in diagnostic if r["stream"] == reported["stream"]}
    original, other = candidates["inherited"], candidates[reported["treatment"]]
    common = min(len(original["mission_results"]), len(other["mission_results"]))
    equal(reported["qualified_difference"], other["qualified"] - original["qualified"], "paired qualified")
    equal(reported["work_difference"], other["work"] - original["work"], "paired work")
    equal(reported["common_missions"], common, "paired common count")
    equal(reported["all_missions_completed_both"], common == 4, "paired completion")
    identical = all(a["schedule_sha256"] == b["schedule_sha256"] for a, b in zip(original["mission_results"], other["mission_results"]))
    equal(reported["same_fresh_schedules_on_common_prefix"], identical, "paired fresh schedules")
    pair_checks.append(reported)

native_verified = []
for reported in summary["native"]:
    group = [r for r in native if r["mode"] == reported["mode"]]
    expected = {
        "tasks": len(group), "valid": sum(r["valid"] for r in group), "qualified": sum(r["qualified"] for r in group),
        "practical_workflow_valid": sum(r["practical_workflow_valid"] for r in group),
        "practical_workflow_qualified": sum(r["practical_workflow_qualified"] for r in group),
        "mean_end_to_end_ms": statistics.fmean(r["attributable_end_to_end_ms"] for r in group),
        "mean_practical_workflow_ms": statistics.fmean(r["practical_workflow_end_to_end_ms"] for r in group),
        "mean_solver_reported_ms": statistics.fmean(r["native"]["model_solve_ms"] for r in group if r["native"] and "model_solve_ms" in r["native"]),
        "timeouts_or_limits": sum(r["error"] is not None or bool(r["native"] and r["native"].get("status_code") == 1) for r in group),
        "reported_status_counts": dict(collections.Counter(str(r["native"].get("status_code", r["native"].get("status"))) if r["native"] else str(r["error"]) for r in group)),
        "objective_targets_makespan": reported["mode"] == "makespan", "comparison_work_units": None,
    }
    for key, value in expected.items():
        equal(reported[key], value, ("native", reported["mode"], key))
    native_verified.append({"mode": reported["mode"], **expected})

primary = {(r["stream"], r["arm"]): r for r in trials if r["category"] == "main" and r["budget"] == 1000000}
differences = []
declines = {"flywheel": 0, "portfolio": 0}
rate_windows = {"flywheel": [[], [], []], "portfolio": [[], [], []]}
for reported in summary["increasing_rate"]["windows"]:
    rates = {}
    for arm in declines:
        rates[arm] = [w["qualified_per_100k_work"] for w in primary[reported["stream"], arm]["windows"]]
        equal(reported[arm + "_rates"], rates[arm], "recorded window rates")
        declines[arm] += rates[arm][-1] < rates[arm][0]
        for index, value in enumerate(rates[arm]):
            rate_windows[arm][index].append(value)
    value = (rates["flywheel"][-1] - rates["flywheel"][0]) - (rates["portfolio"][-1] - rates["portfolio"][0])
    equal(reported["difference_in_last_minus_first_rate"], value, "difference in changes")
    differences.append(value)
observed_mean, interval = bootstrap(differences)
equal(summary["increasing_rate"]["difference_in_changes"]["mean"], observed_mean, "exploratory mean")
for actual, expected in zip(summary["increasing_rate"]["difference_in_changes"]["percentile_95_interval"], interval):
    equal(actual, expected, "exploratory interval")

pair_aggregate = {}
for treatment in ["removed", "rebuild", "equivalent"]:
    group = [r for r in pair_checks if r["treatment"] == treatment]
    pair_aggregate[treatment] = {
        "streams": len(group), "qualified_difference_total": sum(r["qualified_difference"] for r in group),
        "work_difference_mean": statistics.fmean(r["work_difference"] for r in group),
        "same_fresh_schedules_streams": sum(r["same_fresh_schedules_on_common_prefix"] for r in group),
    }
result = {
    "schema": "agi-alpha-independent-summary-audit/v1", "status": "PASS",
    "scope": "Post-run consistency checks of recorded diagnostic, native and exploratory window summaries; no new candidate execution.",
    "scientific_source_hash": prior["source_hash"], "top_freeze_sha256": prior["top_freeze_sha256"],
    "audit_source_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    "input_hashes": {name: hashlib.sha256((RUN / name).read_bytes()).hexdigest() for name in ["SUMMARY.json", "trials.jsonl", "native-reference.jsonl", "NATIVE_REFERENCE.json"]},
    "windows_verified": len(trials) * 3, "diagnostic_verified": diagnostic_verified,
    "diagnostic_pairs_verified": len(pair_checks), "diagnostic_pair_aggregates": pair_aggregate,
    "native_verified": native_verified,
    "exploratory_rate": {"first_to_last_decline_streams": declines, "mean_window_rates": {arm: [statistics.fmean(w) for w in windows] for arm, windows in rate_windows.items()},
                         "difference_in_changes_mean": observed_mean, "percentile_95_interval": interval,
                         "interpretation": "Relative difference in rate changes is not absolute acceleration; no primary flywheel asset was retained. This does not establish self-acceleration."},
    "independence": "Separate stdlib implementation; no producer module imports. Same project commission, author environment and retained data; not an external laboratory replication. Timings are consistency-checked observations, not rerun timing benchmarks.",
}
(OUT / "MAIN_SUMMARY_AUDIT.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": "PASS", "windows": result["windows_verified"], "diagnostic_pairs": len(pair_checks), "native_cases": len(native), "rate_declines": declines, "pair_aggregates": pair_aggregate}))
