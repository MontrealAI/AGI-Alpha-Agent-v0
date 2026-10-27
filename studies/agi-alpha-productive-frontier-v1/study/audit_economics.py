# SPDX-License-Identifier: Apache-2.0
"""Audit frozen economic output files without importing or rerunning the engine.

Only explicitly requested receipt/review files are written. CSV input may be
losslessly gzip-compressed. Checks establish file and accounting consistency;
they do not validate the model's market assumptions or certify live operation.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEXT_COLUMNS = {"scenario", "policy", "mode", "committed_mode", "pending_mode"}
COUNT_COLUMNS = {
    "seed", "quality_adjusted_units", "displaced_orders", "workers", "ready_offerings",
    "unfinished_preparation_tasks", "leads", "orders", "accepted", "failed", "failed_prototypes",
    "acquisition_capacity_holds", "declined_acquisition_funds", "declined_scope", "declined_margin",
    "chose_human", "deferred", "declined_buyer",
}
REQUIRED_NUMBERS = {
    "seed", "profit", "collections", "cost_A", "cost_B", "cost_C", "paid_costs", "cash", "obligations",
    "reserves", "available", "receivables_excluded", "refunds", "seed_capital", "quality_adjusted_units",
    "cpu_seconds", "processing_seconds", "weighted_units_per_processing_hour",
    "weighted_units_per_total_capacity_hour", "displaced_orders", "workers", "ready_offerings",
    "preparation_committed_seconds", "preparation_consumed_seconds", "unfinished_preparation_seconds",
    "unfinished_preparation_tasks", "gross_capacity_seconds", "production_reserved_seconds", "unused_capacity_seconds",
}
MODES = ("beta", "work", "gym")
OFFERS = ("audit", "screen", "select")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Checks:
    """Retain check counts and discrepancies, rather than silently dropping rows."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.failures: list[dict[str, Any]] = []
        self.maximum_absolute_residual: dict[str, float] = defaultdict(float)

    def test(self, condition: bool, family: str, detail: str) -> None:
        self.counts[family] += 1
        if not condition:
            self.failures.append({"family": family, "detail": detail})

    def close(self, left: float, right: float, family: str, detail: str) -> None:
        residual = abs(left - right)
        self.maximum_absolute_residual[family] = max(self.maximum_absolute_residual[family], residual)
        self.test(math.isfinite(left) and math.isfinite(right)
                  and math.isclose(left, right, rel_tol=1e-11, abs_tol=1e-7), family,
                  f"{detail}: {left!r} versus {right!r}; absolute residual {residual!r}")


def read_csv(results: Path, checks: Checks) -> tuple[list[dict[str, str]], dict[str, str]]:
    plain = results / "enterprise_runs.csv"
    compressed = results / "enterprise_runs.csv.gz"
    if plain.exists():
        content = plain.read_bytes()
        source = plain
        if compressed.exists():
            checks.test(content == gzip.decompress(compressed.read_bytes()), "compression",
                        "CSV and CSV.gz must encode identical uncompressed bytes")
    elif compressed.exists():
        content = gzip.decompress(compressed.read_bytes())
        source = compressed
    else:
        raise FileNotFoundError("Neither enterprise_runs.csv nor enterprise_runs.csv.gz exists")
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
    return rows, {"path": str(source), "file_sha256": digest(source),
                  "uncompressed_csv_sha256": hashlib.sha256(content).hexdigest()}


def parsed_row(row: dict[str, str]) -> dict[str, Any]:
    missing = sorted(k for k in REQUIRED_NUMBERS if row.get(k, "") == "")
    if missing:
        raise ValueError(f"Required scalar columns are absent/blank: {missing}")
    result: dict[str, Any] = {}
    for key, value in row.items():
        if key in TEXT_COLUMNS:
            result[key] = value or None
        elif key == "setup_ready":
            if value not in ("True", "False"):
                raise ValueError(f"Invalid setup_ready boolean: {value!r}")
            result[key] = value == "True"
        else:
            result[key] = float(value) if value else 0.0
    return result


def count_distribution(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key)) for row in rows).items()))


def describe(values: list[float]) -> dict[str, float]:
    return {"mean": statistics.fmean(values), "minimum": min(values), "maximum": max(values)}


def check_row(row: dict[str, Any], checks: Checks, label: str) -> None:
    for key, value in row.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            checks.test(math.isfinite(value), "finite_values", f"{label}.{key}")
            if key not in {"profit", "available", "cash"}:
                checks.test(value >= -1e-7, "nonnegative_values", f"{label}.{key}={value}")
        if key in COUNT_COLUMNS:
            checks.close(value, round(value), "integer_counts", f"{label}.{key}")
    total_cost = math.fsum(row[f"cost_{bucket}"] for bucket in "ABC")
    checks.close(row["profit"], row["collections"] - total_cost, "cash_accounting", f"{label}.profit")
    checks.close(row["obligations"], total_cost - row["paid_costs"], "cash_accounting", f"{label}.obligations")
    checks.close(row["cash"], row["seed_capital"] + row["collections"] - row["paid_costs"],
                 "cash_accounting", f"{label}.cash")
    checks.close(row["available"], row["cash"] - row["obligations"] - row["reserves"],
                 "cash_accounting", f"{label}.available")
    checks.close(row["available"], row["seed_capital"] + row["profit"] - row["reserves"],
                 "cash_accounting", f"{label}.available versus profit")
    checks.close(row["gross_capacity_seconds"], row["preparation_consumed_seconds"]
                 + row["production_reserved_seconds"] + row["unused_capacity_seconds"],
                 "horizon_capacity", label)
    checks.close(row["preparation_committed_seconds"], row["preparation_consumed_seconds"]
                 + row["unfinished_preparation_seconds"], "horizon_backlog", label)
    checks.test(row["processing_seconds"] <= row["production_reserved_seconds"] + 1e-7,
                "production_reservations", f"{label}: actual processing must fit reserved capacity")
    checks.test(row["cpu_seconds"] <= row["processing_seconds"] + 1e-7,
                "production_reservations", f"{label}: numerical kernel is a subset of total processing")
    for metric, denominator in [("weighted_units_per_processing_hour", "processing_seconds"),
                                ("weighted_units_per_total_capacity_hour", "gross_capacity_seconds")]:
        expected = row["quality_adjusted_units"] * 3600 / row[denominator] if row[denominator] else 0
        checks.close(row[metric], expected, "productivity_denominators", f"{label}.{metric}")
    checks.close(row.get("orders", 0), row.get("accepted", 0) + row.get("failed", 0),
                 "order_counts", label)
    checks.test(row.get("orders", 0) <= row.get("leads", 0), "order_counts", f"{label}: orders <= acquired leads")
    checks.test(row["refunds"] <= row["collections"] + 1e-7 and row["refunds"] <= row["cost_A"] + 1e-7,
                "refund_accounting", label)
    checks.test(row["mode"] in MODES and row["committed_mode"] in MODES, "mode_state", label)
    expected_pending = row["committed_mode"] if row["committed_mode"] != row["mode"] else None
    checks.test(row["pending_mode"] == expected_pending, "mode_state", f"{label}: pending target")
    checks.test(row["setup_ready"] or (row["mode"] == "beta" and row["ready_offerings"] == 0),
                "mode_state", f"{label}: no offering or specialist before common setup")
    checks.test((row["unfinished_preparation_seconds"] > 0) == (row["unfinished_preparation_tasks"] > 0),
                "horizon_backlog", f"{label}: unfinished task count/seconds")


def check_daily_capacity(paths: list[dict[str, Any]], checks: Checks, label: str) -> None:
    totals = defaultdict(float)
    prior_backlog = 0.0
    pairs = {
        "preparation_consumed_seconds": "cumulative_preparation_seconds",
        "gross_capacity_seconds": "cumulative_gross_capacity_seconds",
        "production_reserved_seconds": "cumulative_production_reserved_seconds",
        "unused_capacity_seconds": "cumulative_unused_capacity_seconds",
    }
    for day, row in enumerate(paths):
        where = f"{label}.day{day}"
        checks.test(row["day"] == day, "daily_sequence", where)
        for key in [*pairs, "preparation_backlog_start_seconds", "preparation_scheduled_seconds",
                    "preparation_backlog_end_seconds"]:
            checks.test(math.isfinite(row[key]) and row[key] >= -1e-7, "daily_capacity", f"{where}.{key}")
        checks.close(row["gross_capacity_seconds"], row["preparation_consumed_seconds"]
                     + row["production_reserved_seconds"] + row["unused_capacity_seconds"], "daily_capacity", where)
        checks.close(row["preparation_backlog_start_seconds"], prior_backlog, "daily_backlog", where)
        checks.close(row["preparation_backlog_start_seconds"] + row["preparation_scheduled_seconds"],
                     row["preparation_consumed_seconds"] + row["preparation_backlog_end_seconds"],
                     "daily_backlog", where)
        totals["committed"] += row["preparation_scheduled_seconds"]
        for daily_key, cumulative_key in pairs.items():
            totals[daily_key] += row[daily_key]
            checks.close(row[cumulative_key], totals[daily_key], "daily_cumulative", f"{where}.{cumulative_key}")
        checks.close(totals["committed"], row["cumulative_preparation_seconds"]
                     + row["preparation_backlog_end_seconds"], "daily_cumulative", f"{where}.preparation")
        checks.close(row["cumulative_gross_capacity_seconds"], row["cumulative_preparation_seconds"]
                     + row["cumulative_production_reserved_seconds"] + row["cumulative_unused_capacity_seconds"],
                     "daily_cumulative", f"{where}.capacity")
        prior_backlog = row["preparation_backlog_end_seconds"]


def check_capacity_export(data: dict[str, Any], config: dict[str, Any],
                          groups: dict[tuple[str, str], list[dict[str, Any]]], checks: Checks) -> dict[str, Any]:
    policies = config["policy_candidates"]
    n = config["confirmation_seeds"][1] - config["confirmation_seeds"][0] + 1
    checks.test(data["schema"] == "productive-frontier-capacity-paths/v1", "capacity_export", "schema")
    checks.test(data["scenario"] == "capacity_pressure" and data["seeds"] == config["confirmation_seeds"]
                and data["per_policy_histories"] == n, "capacity_export", "scenario and cohort")
    checks.test("End-of-day" in data.get("readiness_semantics", ""), "capacity_export", "explicit end-of-day semantics")
    checks.test(set(data["policies"]) == set(policies), "capacity_export", "all policies")
    description = {}
    for policy, paths in data["policies"].items():
        checks.test(len(paths) == config["days"], "capacity_export", f"{policy}: complete daily horizon")
        check_daily_capacity(paths, checks, f"capacity_pressure.{policy}")
        previous = {offer: 0.0 for offer in OFFERS}
        for day, row in enumerate(paths):
            where = f"capacity_pressure.{policy}.day{day}"
            ready, mode, committed = (row[k] for k in ["ready_offer_fractions", "mode_ready_fractions", "committed_mode_fractions"])
            checks.test(set(ready) == set(OFFERS) and set(mode) == set(MODES) and set(committed) == set(MODES),
                        "readiness_fractions", where)
            fractions = [*ready.values(), *mode.values(), *committed.values(), row["setup_ready"],
                         row["enterprise_not_ready_fraction"]]
            for fraction in fractions:
                checks.test(math.isfinite(fraction) and -1e-12 <= fraction <= 1 + 1e-12,
                            "readiness_fractions", f"{where}: fraction range")
                checks.close(fraction * n, round(fraction * n), "readiness_fractions", f"{where}: empirical count")
            checks.close(sum(ready.values()), row["offers"], "readiness_fractions", f"{where}.offering count")
            checks.close(ready["audit"], row["setup_ready"], "readiness_fractions", f"{where}.audit prerequisite")
            checks.close(sum(mode.values()), row["setup_ready"], "readiness_fractions", f"{where}.ready mode")
            checks.close(sum(mode.values()) + row["enterprise_not_ready_fraction"], 1,
                         "readiness_fractions", f"{where}.enterprise state partition")
            checks.close(sum(committed.values()), 1, "readiness_fractions", f"{where}.committed state partition")
            for offer, fraction in ready.items():
                checks.test(fraction + 1e-12 >= previous[offer] and fraction <= row["setup_ready"] + 1e-12,
                            "readiness_fractions", f"{where}.{offer}: persistent readiness after setup")
            previous = ready
        rows = groups[("capacity_pressure", policy)]
        final = paths[-1]
        mapping = {"cumulative_gross_capacity_seconds": "gross_capacity_seconds",
                   "cumulative_preparation_seconds": "preparation_consumed_seconds",
                   "cumulative_production_reserved_seconds": "production_reserved_seconds",
                   "cumulative_unused_capacity_seconds": "unused_capacity_seconds",
                   "preparation_backlog_end_seconds": "unfinished_preparation_seconds", "offers": "ready_offerings",
                   "workers": "workers", "setup_ready": "setup_ready"}
        for field, raw in mapping.items():
            checks.close(final[field], statistics.fmean(row[raw] for row in rows), "capacity_export_reconciliation", f"{policy}.{field}")
        checks.close(sum(day["preparation_scheduled_seconds"] for day in paths),
                     statistics.fmean(row["preparation_committed_seconds"] for row in rows),
                     "capacity_export_reconciliation", f"{policy}.committed preparation")
        for mode in MODES:
            checks.close(final["mode_ready_fractions"][mode],
                         statistics.fmean(row["setup_ready"] and row["mode"] == mode for row in rows),
                         "capacity_export_reconciliation", f"{policy}.{mode} readiness")
            checks.close(final["committed_mode_fractions"][mode], statistics.fmean(row["committed_mode"] == mode for row in rows),
                         "capacity_export_reconciliation", f"{policy}.{mode} commitment")
        description[policy] = {
            "first_day_any_ready": {offer: next((p["day"] for p in paths if p["ready_offer_fractions"][offer] > 0), None)
                                    for offer in OFFERS},
            "first_day_all_ready": {offer: next((p["day"] for p in paths if p["ready_offer_fractions"][offer] == 1), None)
                                    for offer in OFFERS},
            "ready_with_zero_mean_production_days": [p["day"] for p in paths if p["offers"] > 0 and p["production_reserved_seconds"] == 0],
            "mean_preparation_seconds": final["cumulative_preparation_seconds"],
            "mean_horizon_backlog_seconds": final["preparation_backlog_end_seconds"],
        }
    checks.test(data["policies"]["shared_work"] == data["policies"]["ordinary_library"],
                "exact_library_equivalence", "all exported capacity/readiness paths")
    return description


def check_exemplar(exemplar: dict[str, Any], raw: dict[str, Any], config: dict[str, Any], checks: Checks) -> None:
    """Reconstruct the emitted exemplar ledger/task state, without the simulator."""
    days = config["days"]
    base = config["base"]
    for key, value in raw.items():
        other = exemplar.get(key, 0)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            checks.close(value, other, "exemplar_scalars", key)
        else:
            checks.test(value == other, "exemplar_scalars", key)
    paths = exemplar["path"]
    checks.test(len(paths) == days, "exemplar_ledger", "complete horizon")
    check_daily_capacity(paths, checks, "exemplar")
    tasks = exemplar["preparation_tasks"]
    checks.test(len({t["task_id"] for t in tasks}) == len(tasks), "exemplar_tasks", "unique task IDs")
    pending_seen = False
    last_completion = -1
    for task in tasks:
        checks.test(0 <= task["submitted_day"] < days and 0 <= task["remaining_seconds"] <= task["total_seconds"],
                    "exemplar_tasks", task["task_id"])
        if task["status"] == "pending":
            pending_seen = True
            checks.test(task["completed_day"] is None and task["remaining_seconds"] > 0 and "success" not in task,
                        "exemplar_tasks", f"{task['task_id']}: unfinished outcome remains undisclosed")
        else:
            checks.test(task["status"] == "completed" and not pending_seen and task["remaining_seconds"] == 0
                        and task["submitted_day"] <= task["completed_day"] < days and task["completed_day"] >= last_completion,
                        "exemplar_tasks", f"{task['task_id']}: FIFO completion")
            last_completion = task["completed_day"]
    checks.close(sum(t["total_seconds"] for t in tasks), exemplar["preparation_committed_seconds"], "exemplar_tasks", "committed work")
    checks.close(sum(t["remaining_seconds"] for t in tasks), exemplar["unfinished_preparation_seconds"], "exemplar_tasks", "horizon backlog")
    checks.close(sum(t["status"] == "pending" for t in tasks), exemplar["unfinished_preparation_tasks"], "exemplar_tasks", "horizon pending tasks")
    for day, path in enumerate(paths):
        charges = [x for x in exemplar["charges"] if x["day"] <= day]
        accrued = math.fsum(x["amount"] for x in charges)
        paid_parts = []
        for charge in charges:
            immediate = charge["amount"] if charge["immediate_paid"] else charge["amount"] * base["initial_paid_cost_fraction"]
            paid_parts.append(immediate)
            if charge["day"] + base["payment_delay_cost_days"] <= day:
                paid_parts.append(charge["amount"] - immediate)
        paid = math.fsum(paid_parts)
        collected = math.fsum(x["amount"] for x in exemplar["collection_events"] if x["day"] <= day)
        expected = {"collections": collected, "profit": collected - accrued,
                    "cash": base["seed_capital_usd"] + collected - paid, "obligations": accrued - paid,
                    "available": base["seed_capital_usd"] + collected - accrued - base["reserve_usd"]}
        for key, value in expected.items():
            checks.close(path[key], value, "exemplar_ledger", f"day{day}.{key}")
        completed = [t for t in tasks if t["completed_day"] is not None and t["completed_day"] <= day]
        ready = {"audit" for t in completed if t["kind"] == "setup"}
        ready.update(t["offer"] for t in completed if t["kind"] == "prototype" and t["success"])
        mode = next((t["target_mode"] for t in reversed(completed) if t["kind"] == "capability"), "beta")
        checks.test(set(path["ready_offers"]) == ready and path["mode"] == mode and path["offers"] == len(ready),
                    "exemplar_readiness", f"day{day}: end-of-day completed tasks determine readiness")
        checks.test(path["setup_ready"] == ("audit" in ready), "exemplar_readiness", f"day{day}: setup")
        checks.test(path["completed_preparations"] == [t["task_id"] for t in tasks if t["completed_day"] == day],
                    "exemplar_tasks", f"day{day}: completion record")
        checks.close(path["preparation_scheduled_seconds"], sum(t["total_seconds"] for t in tasks if t["submitted_day"] == day),
                     "exemplar_tasks", f"day{day}: preparation commitments")
        if not ready:
            checks.close(path["production_reserved_seconds"], 0, "exemplar_readiness", f"day{day}: no production before setup")
    for bucket in "ABC":
        checks.close(exemplar[f"cost_{bucket}"], math.fsum(x["amount"] for x in exemplar["charges"]
                     if x["day"] < days and x["bucket"] == bucket), "exemplar_ledger", f"cost_{bucket}")
    checks.close(exemplar["refunds"], math.fsum(x["amount"] for x in exemplar["charges"]
                 if x["day"] < days and x["reason"] == "full customer refund after failed acceptance"),
                 "exemplar_ledger", "refunds retained once in A")


def audit(results: Path, technical: Path, root: Path = ROOT) -> dict[str, Any]:
    checks = Checks()
    config_path = root / "protocol/economic_protocol.json"
    config = json.loads(config_path.read_text())
    freeze_path = results / "economic_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    summary_path = results / "economic_results.json"
    summary = json.loads(summary_path.read_text())
    files = [config_path, root / "study/economics.py", Path(__file__).resolve(), freeze_path, summary_path,
             results / "economic_paths.json", results / "capacity_paths.json", results / "exemplar.json"]
    checks.test(freeze["code_sha256"] == digest(root / "study/economics.py"), "frozen_hashes", "current engine equals frozen engine")
    checks.test(freeze["protocol_sha256"] == digest(config_path), "frozen_hashes", "current protocol equals frozen protocol")
    checks.test(summary["freeze"] == freeze, "frozen_hashes", "summary embeds the exact initial freeze")
    checks.test(summary["execution_status"] == "executed_confirmation", "cohort", "confirmation execution status")
    checks.test(summary["seeds"] == config["confirmation_seeds"], "cohort", "declared protected seed range")
    checks.test(freeze["confirmation_executed"] is False, "frozen_hashes", "freeze preserves its pre-execution flag")
    input_paths = [*technical.glob("*.csv"), technical / "selection_results.json"]
    inputs = {p.name: digest(p) for p in input_paths}
    checks.test(inputs == freeze["technical_inputs"], "frozen_hashes", "all current measured input files and digests")
    files.extend(input_paths)
    amendment = root / config["correctness_amendment"]
    checks.test(digest(amendment) == config["correctness_amendment_sha256"], "frozen_hashes", "correctness amendment reference")
    files.append(amendment)
    raw_rows, csv_receipt = read_csv(results, checks)
    rows = [parsed_row(row) for row in raw_rows]
    seeds = range(config["confirmation_seeds"][0], config["confirmation_seeds"][1] + 1)
    policies, scenarios = config["policy_candidates"], config["stress_scenarios"]
    expected_keys = {(scenario, policy, seed) for scenario in scenarios for policy in policies for seed in seeds}
    def key(row: dict[str, Any]) -> tuple[str, str, int]:
        return row["scenario"], row["policy"], int(row["seed"])

    by_key = {key(row): row for row in rows}
    by_key_raw = {key(row): row for row in raw_rows}
    checks.test(len(rows) == len(expected_keys), "cohort", "exact declared row count")
    checks.test(len(by_key) == len(rows), "cohort", "no duplicate scenario-policy-seed keys")
    checks.test(set(by_key) == expected_keys, "cohort", "complete Cartesian cohort; no missing or extra keys")
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        label = f"{row['scenario']}/{row['policy']}/{int(row['seed'])}"
        check_row(row, checks, label)
        checks.close(row["seed_capital"], config["base"]["seed_capital_usd"], "common_resources", label)
        checks.close(row["reserves"], config["base"]["reserve_usd"], "common_resources", label)
        if row["scenario"] != "growth_financed_by_surplus":
            baseline = by_key[(row["scenario"], "competent_beta", int(row["seed"]))]
            checks.close(row["gross_capacity_seconds"], baseline["gross_capacity_seconds"], "common_resources", label)
        groups[(row["scenario"], row["policy"])].append(row)
    for scenario in scenarios:
        for seed in seeds:
            shared, library = (by_key_raw[(scenario, p, seed)] for p in ["shared_work", "ordinary_library"])
            checks.test({k: v for k, v in shared.items() if k != "policy"}
                        == {k: v for k, v in library.items() if k != "policy"},
                        "exact_library_equivalence", f"{scenario}/{seed}: all scalar CSV cells except policy")
    checks.test(set(summary["scenarios"]) == set(scenarios), "aggregate_reconciliation", "all scenario summaries")
    descriptives: dict[str, Any] = {}
    for scenario in scenarios:
        descriptives[scenario] = {}
        checks.test(set(summary["scenarios"][scenario]) == set(policies), "aggregate_reconciliation", f"{scenario}: all policies")
        for policy in policies:
            group = groups[(scenario, policy)]
            output = summary["scenarios"][scenario][policy]
            differences = [r["profit"] - by_key[(scenario, "competent_beta", int(r["seed"]))]["profit"] for r in group]
            for metric, value in output.items():
                if isinstance(value, dict) and "mean" in value:
                    values = differences if metric == "incremental_profit_vs_beta" else [r.get(metric, 0) for r in group]
                    mean = statistics.fmean(values)
                    checks.close(value["mean"], mean, "aggregate_reconciliation", f"{scenario}.{policy}.{metric}.mean")
                    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0
                    checks.close(value["mc95_low"], mean - half, "aggregate_intervals", f"{scenario}.{policy}.{metric}.low")
                    checks.close(value["mc95_high"], mean + half, "aggregate_intervals", f"{scenario}.{policy}.{metric}.high")
            for column, field, modes in [("mode", "mode_counts", MODES), ("committed_mode", "committed_mode_counts", MODES),
                                         ("pending_mode", "pending_mode_counts", ("work", "gym"))]:
                expected = {mode: sum(r[column] == mode for r in group) for mode in modes}
                checks.test(output[field] == expected, "aggregate_reconciliation", f"{scenario}.{policy}.{field}")
            fields = ["profit", "collections", "available", "cash", "obligations", "cost_A", "cost_B", "cost_C",
                      "orders", "accepted", "failed", "failed_prototypes", "refunds", "workers", "leads",
                      "acquisition_capacity_holds", "unfinished_preparation_seconds", "unfinished_preparation_tasks",
                      "preparation_consumed_seconds", "production_reserved_seconds", "unused_capacity_seconds",
                      "quality_adjusted_units", "weighted_units_per_processing_hour", "weighted_units_per_total_capacity_hour"]
            descriptives[scenario][policy] = {
                "histories": len(group), "metrics": {field: describe([r.get(field, 0) for r in group]) for field in fields},
                "negative_profit_histories": sum(r["profit"] < -1e-7 for r in group),
                "positive_incremental_profit_histories": sum(v > 1e-7 for v in differences),
                "negative_incremental_profit_histories": sum(v < -1e-7 for v in differences),
                "effectively_zero_incremental_profit_histories": sum(abs(v) <= 1e-7 for v in differences),
                "incremental_profit_vs_beta": describe(differences), "worker_counts": count_distribution(group, "workers"),
                "mode_counts": count_distribution(group, "mode"), "committed_mode_counts": count_distribution(group, "committed_mode"),
                "pending_mode_counts": count_distribution(group, "pending_mode"),
                "histories_with_failed_delivery": sum(r.get("failed", 0) > 0 for r in group),
                "histories_with_failed_prototype": sum(r.get("failed_prototypes", 0) > 0 for r in group),
                "histories_with_unfinished_preparation": sum(r["unfinished_preparation_seconds"] > 0 for r in group),
            }
    base_paths = json.loads((results / "economic_paths.json").read_text())
    checks.test(set(base_paths) == set(policies), "base_paths", "all policy paths")
    for policy, paths in base_paths.items():
        checks.test(len(paths) == config["days"], "base_paths", f"{policy}: full horizon")
        for day, path in enumerate(paths):
            checks.test(path["day"] == day, "base_paths", f"{policy}.day{day}")
            checks.close(path["available"], config["base"]["seed_capital_usd"] + path["profit"] - config["base"]["reserve_usd"],
                         "base_paths", f"{policy}.day{day}: available funds")
        for field, raw in [("profit", "profit"), ("available", "available"), ("offers", "ready_offerings"), ("workers", "workers")]:
            checks.close(paths[-1][field], statistics.fmean(r[raw] for r in groups[("base", policy)]),
                         "base_paths", f"{policy}: final {field}")
    checks.test(base_paths["shared_work"] == base_paths["ordinary_library"], "exact_library_equivalence", "all base paths")
    capacity_description = check_capacity_export(json.loads((results / "capacity_paths.json").read_text()), config, groups, checks)
    exemplar = json.loads((results / "exemplar.json").read_text())
    checks.test((exemplar["scenario"], exemplar["policy"], exemplar["seed"]) == ("base", "selective", seeds.start),
                "exemplar_ledger", "declared first-seed selective exemplar")
    check_exemplar(exemplar, by_key[key(exemplar)], config, checks)
    return {
        "schema": "productive-frontier-frozen-economic-audit/v1", "status": "PASS" if not checks.failures else "FAIL",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "review_role": "AI-assisted output-consistency audit by the capacity-scheduler implementation lane. The separate technical agent's resource-accounting source/fixture review is an independent work role; neither review is external institutional certification.",
        "operation": "Read-only inspection of existing results and source hashes; engine was neither imported nor executed.",
        "cohort": {"seeds": list(config["confirmation_seeds"]), "scenarios": len(scenarios), "policies": len(policies),
                   "raw_rows": len(rows), "unique_keys": len(by_key), "expected_rows": len(expected_keys)},
        "tolerances": {"relative": 1e-11, "absolute": 1e-7, "paired_sign_zero_usd": 1e-7,
                       "library_equivalence": "exact raw-cell equality, excluding policy"},
        "checks_by_family": dict(checks.counts), "maximum_absolute_residual_by_family": dict(checks.maximum_absolute_residual),
        "failure_count": len(checks.failures), "failures": checks.failures,
        "csv": csv_receipt, "file_sha256": {str(p): digest(p) for p in files},
        "scenario_policy_descriptives": descriptives, "capacity_readiness_descriptives": capacity_description,
        "limitations": [
            "Market demand, prices, service acceptance, model workload, preparation time and complete cash costs remain assumed/simulated.",
            "Scalar conservation covers every history; daily conservation covers exported capacity-pressure means and the full base/selective exemplar. Individual daily histories for every seed are not stored.",
            "Readiness is end-of-day availability. It does not imply that an offer was available before preparation or had remaining same-day production capacity.",
            "File consistency cannot by itself establish absence of information leakage; the separate source review and controlled prefix/sentinel regressions cover that concern.",
            "Monte Carlo intervals describe simulation variation, not market evidence. No live customer revenue or external certification is established.",
        ],
    }


def render_review(receipt: dict[str, Any]) -> str:
    if "cohort" not in receipt:
        return "# Economic results audit — revision 3\n\n**Status: FAIL**. Audit could not finish:\n\n" + receipt["error"] + "\n"
    cohort = receipt["cohort"]
    desc = receipt["scenario_policy_descriptives"]
    lines = ["# Economic results audit — revision 3", "", f"**Status: {receipt['status']}**. Audited {receipt['audited_at_utc']}.", "",
             f"Read-only review of {cohort['raw_rows']:,} rows ({cohort['scenarios']} scenarios × {cohort['policies']} policies × "
             f"{cohort['seeds'][1] - cohort['seeds'][0] + 1} seeds, {cohort['seeds'][0]}–{cohort['seeds'][1]}). "
             "The engine was neither imported nor rerun. This output-consistency audit was built by the capacity-scheduler implementation lane. "
             "A separate technical agent independently reviewed the resource source and fixtures; neither review is external institutional certification.", "",
             "## Accounting, resources and provenance", "",
             f"The audit executed {sum(receipt['checks_by_family'].values()):,} checks and recorded {receipt['failure_count']} discrepancies. "
             "It reconciles financial identities, horizon capacity and backlog, both productivity denominators, aggregate means/Monte Carlo mean intervals, "
             "exact shared/library scalar equivalence, daily exported capacity/readiness, the detailed exemplar ledger/tasks, and frozen source/input hashes. "
             "The JSON receipt retains per-family counts, maximum numerical residuals, exact hashes, and all discrepancies.", "",
             "Revision 3 follows the disclosed post-review capacity/readiness correctness repair. Earlier editions remain historical evidence; "
             "this audit does not recast the repaired policy as unchanged preregistration. Cash commitments are retained once; preparation "
             "is conserved across days and readiness follows completion. End-of-day readiness can coexist with zero remaining production capacity.", "",
             "## Base-case distributions", "",
             "Amounts below are simulated USD means; counts refer to the 256 histories for each policy.", "",
             "| Policy | Mean surplus | Mean increment vs Beta | Positive paired increments | Loss histories | Mean orders | Mean full-capacity units/hour |", 
             "|---|---:|---:|---:|---:|---:|---:|"]
    for policy, data in desc["base"].items():
        metrics = data["metrics"]
        lines.append(f"| {policy} | {metrics['profit']['mean']:,.2f} | {data['incremental_profit_vs_beta']['mean']:,.2f} | "
                     f"{data['positive_incremental_profit_histories']} | {data['negative_profit_histories']} | "
                     f"{metrics['orders']['mean']:.2f} | {metrics['weighted_units_per_total_capacity_hour']['mean']:.3f} |")
    lines.extend(["", "Base-case financial components (simulated USD means):", "",
                  "| Policy | Collections | A costs | B costs | C costs | Unpaid obligations | Available funds |",
                  "|---|---:|---:|---:|---:|---:|---:|"])
    for policy, data in desc["base"].items():
        metrics = data["metrics"]
        values = [metrics[field]["mean"] for field in ["collections", "cost_A", "cost_B", "cost_C", "obligations", "available"]]
        lines.append(f"| {policy} | " + " | ".join(f"{value:,.2f}" for value in values) + " |")
    lines.extend(["", "Available funds subtract outstanding obligations and the reserve from cash. "
                  "The audit reconciles cash separately; seed capital and unpaid future invoices are excluded from collections. "
                  "The full receipt includes cash, all cost buckets, refunds, obligations and available-funds distributions for every scenario/policy."])
    lines.extend(["", "## Stress and readiness findings", "",
                  "| Scenario | Beta mean surplus | Selective mean increment | Selective committed modes | Loss histories, all policies | Positive increments, all policies |", 
                  "|---|---:|---:|---|---:|---:|"])
    for scenario, policies in desc.items():
        selective = policies["selective"]
        modes = ", ".join(f"{k}:{v}" for k, v in selective["committed_mode_counts"].items())
        lines.append(f"| {scenario} | {policies['competent_beta']['metrics']['profit']['mean']:,.2f} | "
                     f"{selective['incremental_profit_vs_beta']['mean']:,.2f} | {modes} | "
                     f"{sum(d['negative_profit_histories'] for d in policies.values())} | "
                     f"{sum(d['positive_incremental_profit_histories'] for d in policies.values())} |")
    lines.extend(["", "Growth-scenario terminal worker counts (worker count: histories):", ""])
    for policy, data in desc["growth_financed_by_surplus"].items():
        lines.append(f"- **{policy}:** " + ", ".join(f"{k}:{v}" for k, v in data["worker_counts"].items()) + ".")
    lines.extend(["", "Resource-sensitive output diagnostics (means; units are the protocol's assumed 1/3/6 weights):", "",
                  "| Scenario / policy | Orders | Weighted output | Units / total capacity hour | Mean extra workers | Increment vs Beta |",
                  "|---|---:|---:|---:|---:|---:|"])
    for scenario in ["capacity_pressure", "growth_financed_by_surplus"]:
        for policy in ["competent_beta", "private_work", "shared_work", "shared_gym", "selective"]:
            data = desc[scenario][policy]
            metrics = data["metrics"]
            lines.append(f"| {scenario} / {policy} | {metrics['orders']['mean']:.2f} | "
                         f"{metrics['quality_adjusted_units']['mean']:.2f} | "
                         f"{metrics['weighted_units_per_total_capacity_hour']['mean']:.4f} | "
                         f"{metrics['workers']['mean']:.4f} | {data['incremental_profit_vs_beta']['mean']:,.2f} |")
    lines.extend(["", "The growth scenario has policy-dependent capacity purchases. Its mean of within-history output/capacity ratios "
                  "can rise while total output and surplus fall; compare these quantities jointly. The historical processing-only ratio "
                  "excludes preparation and idle capacity, so it remains a separately labeled diagnostic."])
    all_groups = [group for scenario in desc.values() for group in scenario.values()]
    total_failed = sum(group["metrics"]["failed"]["mean"] * group["histories"] for group in all_groups)
    total_prototype_failed = sum(group["metrics"]["failed_prototypes"]["mean"] * group["histories"] for group in all_groups)
    backlog_histories = sum(group["histories_with_unfinished_preparation"] for group in all_groups)
    lines.extend(["", f"Across all recorded policy histories: {total_failed:,.0f} failed package deliveries, "
                  f"{total_prototype_failed:,.0f} failed completed prototypes, and {backlog_histories:,} histories ending with unfinished preparation. "
                  "These totals count matched policy histories separately; they are not distinct real customers or experiments.", "",
                  "Capacity-pressure first day with any ready recipient (zero-based; `None` means absent throughout):", ""])
    for policy, data in receipt["capacity_readiness_descriptives"].items():
        ready = ", ".join(f"{k}={v}" for k, v in data["first_day_any_ready"].items())
        lines.append(f"- **{policy}:** {ready}; mean consumed preparation {data['mean_preparation_seconds']:.2f} seconds; "
                     f"mean horizon backlog {data['mean_horizon_backlog_seconds']:.2f} seconds.")
    lines.extend(["", "## Limits", ""] + [f"- {text}" for text in receipt["limitations"]])
    if receipt["failures"]:
        lines.extend(["", "## Discrepancies", "", "The audit is not cleared. Inspect the full JSON receipt before using these results.", ""])
        lines.extend(f"- {failure['family']}: {failure['detail']}" for failure in receipt["failures"][:30])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "results/economics")
    parser.add_argument("--technical", type=Path, default=ROOT / "results/economic_inputs")
    parser.add_argument("--receipt", type=Path, help="Optional audit JSON output; does not modify source results")
    parser.add_argument("--review", type=Path, help="Optional concise Markdown review output")
    args = parser.parse_args()
    results, technical = args.results.resolve(), args.technical.resolve()
    protected = {Path(__file__).resolve(), ROOT / "study/economics.py", ROOT / "protocol/economic_protocol.json",
                 ROOT / "protocol/economic_capacity_amendment.json"}
    for output in [args.receipt, args.review]:
        if output is not None and (output.resolve() in protected or output.resolve().is_relative_to(results)
                                   or output.resolve().is_relative_to(technical)):
            parser.error("Audit outputs must not overwrite frozen source/results/input locations")
    if args.receipt is not None and args.review is not None and args.receipt.resolve() == args.review.resolve():
        parser.error("Receipt and review must have distinct paths")
    try:
        receipt = audit(results, technical)
    except (OSError, ValueError, KeyError, TypeError) as error:
        receipt = {"schema": "productive-frontier-frozen-economic-audit/v1", "status": "FAIL",
                   "audited_at_utc": datetime.now(timezone.utc).isoformat(),
                   "error": f"{type(error).__name__}: {error}", "failure_count": 1, "checks_by_family": {}}
    for path, content in [(args.receipt, json.dumps(receipt, indent=2) + "\n"),
                          (args.review, render_review(receipt))]:
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print(json.dumps({"status": receipt["status"], "cohort": receipt.get("cohort"),
                      "checks": sum(receipt["checks_by_family"].values()), "failure_count": receipt["failure_count"],
                      "csv": receipt.get("csv"), "error": receipt.get("error")}, indent=2))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
