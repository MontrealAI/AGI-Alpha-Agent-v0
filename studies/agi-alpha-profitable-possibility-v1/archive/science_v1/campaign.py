# SPDX-License-Identifier: Apache-2.0
"""Frozen finite scientific campaign, with separate developmental evidence."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from independent_reference import (
    collision_count,
    collision_distribution_direct,
    enumerate_tables,
    finches_problem,
    labeled_cell_count,
    orbit_count,
)
from kernel import Fiber, Problem, ResourceLimit, canonical_bytes, validate_table

ROOT = Path(__file__).resolve().parent
SOURCES = ["kernel.py", "independent_reference.py", "campaign.py", "vendor/miller_harrison_exact.py"]


def source_hashes() -> dict[str, str]:
    """Bind the actual executable scientific methods, rather than a branch name."""
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def freeze(output: Path) -> dict[str, Any]:
    """Write the declared evaluation before generating confirmation instances."""
    protocol = {
        "schema": "agi-alpha-science-protocol-v1", "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_sha256": source_hashes(), "small_cases": 128, "small_seed": 872061028,
        "performance_seed": 918261028, "performance_cases": 12,
        "performance_seconds": 30, "state_budget": 100000, "transition_budget": 1500000,
        "successor_columns": [14, 18], "successor_targets": [0, 1], "sample_count": 100,
        "successor_sample_count": 100, "max_enumerated_small_tables": 100000,
        "comparators": ["exhaustive cell recursion", "labeled cell DP", "independent conventional orbit DP",
                        "authors EXACT v0.3 Python3 port on its supported binary domain",
                        "direct statistic-conditioned orbit DP", "direct all-statistics orbit DP",
                        "conventional reuse of the same inherited asset"],
        "acceptance": "Exact count equality; exhaustive bijection on small cases; cell checks and rank round trips.",
        "frontier_claim": "Only a declared measured resource envelope; no global impossibility or novelty inference.",
        "statistics": "Generated cases are software challenges, not a sampled industrial population.",
        "timing": "Local elapsed wall time; includes explicit cold load, structural validation, and query times.",
        "new_model_causality": "Not tested: no old/new model comparison, no model-price estimate substituted for usage.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError("Preserve the existing protocol; use a new run directory for a revision")
    output.write_text(json.dumps(protocol, indent=2))
    return protocol


def small_cases(seed: int, count: int) -> list[dict[str, Any]]:
    """Generate fresh tiny tests, including honest infeasibility and broken symmetries."""
    rng, problems = random.Random(seed), []
    for k in range(count):
        m, n = rng.randint(2, 4), rng.randint(2, 6)
        maximum = 1 if k % 2 == 0 else 3
        caps = [[rng.randrange(maximum + 1) for _ in range(n)] for _ in range(m)]
        table = [[rng.randrange(cap + 1) for cap in row] for row in caps]
        rows, cols = [sum(row) for row in table], [sum(row[j] for row in table) for j in range(n)]
        if k % 7 == 0:
            caps[0] = [0] * n
        problems.append({"name": f"confirmation_{k:03}", "rows": rows, "cols": cols, "caps": caps})
    return problems


def capacity_problem(n: int, variant: int = 0, rng: random.Random | None = None) -> dict[str, Any]:
    """Construct capacity worlds; these are synthetic models, not customer observations."""
    caps = [[0 if j % 4 == i else 2 for j in range(n)] for i in range(4)]
    rows, cols = [n // 2] * 4, [2] * n
    if variant:
        assert rng is not None
        table = [[0] * n for _ in range(4)]
        for j in range(n):
            allowed = [i for i in range(4) if caps[i][j]]
            for _ in range(2):
                table[rng.choice(allowed)][j] += 1
        rows = [sum(row) for row in table]
        if variant == 2:
            for i in range(4):
                for j in range(n):
                    if table[i][j] == 0 and rng.random() < 0.18:
                        caps[i][j] = 0
    return {"name": f"capacity_{n}_variant_{variant}", "rows": rows, "cols": cols, "caps": caps}


def run_small(protocol: dict[str, Any], output: Path) -> dict[str, Any]:
    """Check complete finite outputs, not only a handful of sampled frequencies."""
    records, bijections, sample_checks = [], 0, 0
    for spec in small_cases(protocol["small_seed"], protocol["small_cases"]):
        problem = Problem.from_dict(spec)
        exact = enumerate_tables(problem.rows, problem.cols, problem.caps,
                                 max_tables=protocol["max_enumerated_small_tables"])
        instrument = Fiber(problem).compile()
        baseline = orbit_count(problem.rows, problem.cols, problem.caps)
        if instrument.count != len(exact) or baseline["count"] != len(exact):
            raise AssertionError(f"count mismatch: {spec['name']}")
        generated = set()
        histogram: dict[int, int] = {}
        for rank in range(instrument.count):
            table = instrument.unrank(rank)
            if instrument.rank(table) != rank or validate_table(problem, table):
                raise AssertionError("rank or acceptance failure")
            generated.add(tuple(tuple(row) for row in table))
            collision = sum(x * (x - 1) // 2 for row in table for x in row)
            histogram[collision] = histogram.get(collision, 0) + 1
            bijections += 1
        if generated != set(exact):
            raise AssertionError("generated family differs from exhaustive oracle")
        distribution, _ = instrument.collision_distribution()
        if histogram != distribution:
            raise AssertionError("successor distribution differs from exhaustive oracle")
        for target, population in distribution.items():
            for table in instrument.conditioned_sample(target, min(3, population), seed=992 + target):
                if validate_table(problem, table) or sum(x * (x - 1) // 2 for row in table for x in row) != target:
                    raise AssertionError("conditioned acceptance failure")
                sample_checks += 1
        records.append({"name": spec["name"], "count": str(instrument.count), "states": len(instrument.nodes),
                        "compiler_seconds": instrument.compile_seconds, "reference_seconds": baseline["seconds"],
                        "all_tables_checked": instrument.count, "exact_match": True})
    result = {"cases": len(records), "exhaustive_bijections": bijections,
              "conditioned_output_checks": sample_checks, "all_match": True, "records": records}
    (output / "confirmation_inputs.json").write_text(json.dumps(small_cases(protocol["small_seed"], protocol["small_cases"])))
    (output / "confirmation.json").write_text(json.dumps(result, indent=2))
    return result


def worker(method: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Run one method in an isolated process, reporting resource refusal honestly."""
    problem = Problem.from_dict(spec)
    started = time.perf_counter()
    if method == "compiler":
        try:
            instrument = Fiber(problem).compile()
            samples = instrument.sample(100, 9182) if instrument.count else []
            if any(validate_table(problem, table) for table in samples):
                raise AssertionError("delivered table rejected")
            return {"status": "complete", "count": str(instrument.count), "seconds": instrument.compile_seconds,
                    "full_delivery_seconds": time.perf_counter() - started, "states": len(instrument.nodes),
                    "edges": sum(len(node.edges) for node in instrument.nodes), "accepted": len(samples)}
        except ResourceLimit as error:
            return {"status": "budget_refusal", "reason": str(error), "seconds": time.perf_counter() - started}
    try:
        function = orbit_count if method == "orbit" else labeled_cell_count
        result = function(problem.rows, problem.cols, problem.caps, max_states=100000)
        return {**result, "count": str(result["count"]), "status": "complete"}
    except RuntimeError as error:
        return {"status": "budget_refusal", "reason": str(error), "seconds": time.perf_counter() - started}


def isolated(method: str, spec: dict[str, Any], seconds: int) -> dict[str, Any]:
    """Apply the same hard wall-time allowance to each fresh count process."""
    started = time.perf_counter()
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "worker", "--method", method],
                                input=json.dumps(spec), text=True, capture_output=True, timeout=seconds, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "seconds": seconds, "count": None}
    if result.returncode:
        raise RuntimeError(f"{method}: {result.stderr[-1200:]}")
    return {**json.loads(result.stdout), "process_wall_seconds": time.perf_counter() - started}


def run_performance(protocol: dict[str, Any], output: Path) -> list[dict[str, Any]]:
    """Compare fresh bounded requests with a strong same-law conventional solver."""
    rng, records = random.Random(protocol["performance_seed"]), []
    for n in (8, 12, 16, 20):
        for variant in range(3):
            spec = capacity_problem(n, variant, rng)
            methods = {method: isolated(method, spec, protocol["performance_seconds"])
                       for method in ("compiler", "orbit", "labeled")}
            counts = {r["count"] for r in methods.values() if r["status"] == "complete"}
            if len(counts) > 1:
                raise AssertionError(f"comparison count mismatch: {spec['name']}")
            record = {"problem": spec, "methods": methods, "complete_counts_agree": len(counts) <= 1}
            records.append(record)
            (output / "performance.json").write_text(json.dumps(records, indent=2))
            print(json.dumps({"case": spec["name"], "methods": methods}), flush=True)
    return records


def run_successor(protocol: dict[str, Any], output: Path) -> list[dict[str, Any]]:
    """Measure cold inheritance, warm reuse, and the strongest specific shortcuts."""
    records = []
    for n in protocol["successor_columns"]:
        spec = capacity_problem(n)
        problem = Problem.from_dict(spec)
        predecessor = Fiber(problem).compile()
        issued = predecessor.as_dict()
        asset_path = output / f"inherited_{n}.json.gz"
        started = time.perf_counter()
        asset_path.write_bytes(gzip.compress(canonical_bytes(issued), mtime=0))
        export_seconds = time.perf_counter() - started
        started = time.perf_counter()
        loaded = json.loads(gzip.decompress(asset_path.read_bytes()))
        read_parse_seconds = time.perf_counter() - started
        started = time.perf_counter()
        successor = Fiber.from_dict(loaded, expected_sha256=issued["sha256"])
        validation_seconds = time.perf_counter() - started
        started = time.perf_counter()
        distribution, _ = successor.collision_distribution()
        query_seconds = time.perf_counter() - started
        direct_distribution = collision_distribution_direct(problem.rows, problem.cols, problem.caps)
        conventional_histogram = {int(k): v for k, v in direct_distribution["distribution"].items()}
        if distribution != conventional_histogram:
            raise AssertionError("direct all-statistics comparator disagrees")
        targets = []
        for target in protocol["successor_targets"]:
            reference = collision_count(problem.rows, problem.cols, problem.caps, target)
            if reference["count"] != distribution.get(target, 0):
                raise AssertionError("direct conditional comparator disagrees")
            started = time.perf_counter()
            tables = successor.conditioned_sample(target, protocol["successor_sample_count"], seed=300 + n + target)
            sample_seconds = time.perf_counter() - started
            if any(validate_table(problem, table) or sum(x * (x - 1) // 2 for row in table for x in row) != target
                   for table in tables):
                raise AssertionError("fresh successor output rejected")
            targets.append({"target": target, "count": str(reference["count"]),
                            "direct_reference_seconds": reference["seconds"], "direct_reference": reference,
                            "conditional_generation_seconds": sample_seconds, "accepted": len(tables),
                            "event_probability": reference["count"] / predecessor.count,
                            "rejection_expected_draws_per_result": predecessor.count / reference["count"]})
            (output / f"successor_{n}_target_{target}_tables.json").write_text(json.dumps(tables))
        conventional_same_asset = Fiber.from_dict(loaded, expected_sha256=issued["sha256"])
        equal_asset_match = (conventional_same_asset.conditioned_sample(1, 20, seed=33) ==
                             successor.conditioned_sample(1, 20, seed=33))
        if not equal_asset_match:
            raise AssertionError("equal-inheritance conventional control differs")
        record = {"problem": spec, "predecessor_count": str(predecessor.count),
                  "predecessor_build_seconds": predecessor.compile_seconds, "states": len(predecessor.nodes),
                  "edges": sum(len(node.edges) for node in predecessor.nodes),
                  "asset_sha256": issued["sha256"], "asset_compressed_bytes": asset_path.stat().st_size,
                  "asset_json_bytes": len(canonical_bytes(issued)), "asset_export_seconds": export_seconds,
                  "asset_read_parse_seconds": read_parse_seconds, "asset_validation_seconds": validation_seconds,
                  "inherited_query_seconds": query_seconds,
                  "cold_inherited_query_seconds": read_parse_seconds + validation_seconds + query_seconds,
                  "direct_all_statistics_seconds": direct_distribution["seconds"],
                  "direct_all_statistics": direct_distribution,
                  "same_asset_conventional_match": equal_asset_match,
                  "distribution": {str(k): str(v) for k, v in sorted(distribution.items())}, "targets": targets}
        records.append(record)
        (output / "successor.json").write_text(json.dumps(records, indent=2))
        print(json.dumps({"successor_columns": n, "cold_inherited_seconds": record["cold_inherited_query_seconds"],
                          "direct_seconds": record["direct_all_statistics_seconds"]}), flush=True)
    return records


def run_published(output: Path) -> dict[str, Any]:
    """Reproduce a published count using the authors' actual supported implementation."""
    sys.path.insert(0, str(ROOT / "vendor"))
    from miller_harrison_exact import count as authors_count

    spec = finches_problem()
    problem = Problem.from_dict(spec)
    started = time.perf_counter()
    author_result = authors_count(list(problem.rows), list(problem.cols))
    elapsed = time.perf_counter() - started
    if isinstance(author_result, tuple):
        number = author_result[0]
    else:
        number = author_result
    instrument = Fiber(problem).compile()
    if number != spec["published_count"] or instrument.count != number:
        raise AssertionError("published authors comparison failed")
    record = {"problem": spec, "authors_count": str(number), "authors_seconds": elapsed,
              "compiler_count": str(instrument.count), "compiler_seconds": instrument.compile_seconds,
              "compiler_states": len(instrument.nodes), "same_output": True}
    (output / "published_comparator.json").write_text(json.dumps(record, indent=2))
    return record


def run(protocol_path: Path, output: Path) -> None:
    """Run exactly the frozen experiment and leave every accepted/refused result."""
    protocol = json.loads(protocol_path.read_text())
    if protocol["source_sha256"] != source_hashes():
        raise ValueError("methods changed after freeze; preserve this run and register a new protocol")
    output.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest()}
    summary["small"] = run_small(protocol, output)
    summary["published"] = run_published(output)
    summary["performance"] = run_performance(protocol, output)
    summary["successor"] = run_successor(protocol, output)
    summary["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (output / "scientific_summary.json").write_text(json.dumps(summary, indent=2))
    with (output / "performance.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case", "method", "status", "count", "seconds", "states"])
        for case in summary["performance"]:
            for method, result in case["methods"].items():
                writer.writerow([case["problem"]["name"], method, result["status"], result.get("count"),
                                 result.get("seconds"), result.get("states")])
    print(json.dumps({"complete": True, "confirmation_cases": summary["small"]["cases"],
                      "bijections": summary["small"]["exhaustive_bijections"]}), flush=True)


def main() -> None:
    """Expose reproducible freeze, run, and isolated-worker commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "run", "worker"])
    parser.add_argument("--protocol", type=Path, default=ROOT / "configs/scientific_protocol_v1.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/confirmation_v1")
    parser.add_argument("--method", choices=["compiler", "orbit", "labeled"])
    args = parser.parse_args()
    if args.action == "freeze":
        print(json.dumps(freeze(args.protocol), indent=2))
    elif args.action == "worker":
        print(json.dumps(worker(args.method, json.loads(sys.stdin.read()))))
    else:
        run(args.protocol, args.output)


if __name__ == "__main__":
    main()
