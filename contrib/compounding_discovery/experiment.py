# SPDX-License-Identifier: Apache-2.0
"""Paired factorial and chronological evaluation, outside candidate control."""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal, localcontext
from fractions import Fraction
import gzip
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import random
import secrets
import shutil
import statistics
import sys
import time
from typing import Any, Callable, Protocol, cast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
ARMS = {
    "".join(name for name, flag in zip("ASC", flags) if flag) or "none": dict(zip("ASC", flags))
    for flags in itertools.product((False, True), repeat=3)
}
REGIMES = ("nominal", "energy", "windows", "combined")
SYSTEMS = ("cumulative", "frozen", "reset", "retrieval")
REFERENCE_HASH = "7dd78c0af40609adaccf3f14fe7f0182c2841cb706960b78744dcaceb8ad73c8"
SCHEMA = "agialpha/discovery-observation/v1"
STORAGE_FLOOR = 200_000_000


class FrontierProgram(Protocol):
    """Typed view of the already source-pinned dynamically imported reference."""

    linprog: Callable[..., Any]

    def solve(self, target: dict[str, Any], *, cache: bool = False) -> dict[str, Any]: ...


def _control_difference(control: str) -> Callable[[dict[str, float]], float]:
    def difference(row: dict[str, float]) -> float:
        return row["cumulative"] - row[control]

    return difference


class StorageBoundary(ValueError):
    """The frozen storage reserve prevents dependent experiment execution."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def write(path: Path, value: Any) -> None:
    raw = canonical(value) + b"\n"
    if path.suffix == ".gz":
        raw = gzip.compress(raw, mtime=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f"immutable output differs: {path}")
        return
    with path.open("xb") as stream:
        stream.write(raw)


def source_manifest(reference: Path | None) -> dict[str, str]:
    paths = [Path(__file__), Path(__file__).with_name("PROTOCOL.md")]
    paths.extend(
        path
        for path in (
            ROOT / "docs/compounding_discovery.md",
            ROOT / "studies/compounding-discovery-v1/SEED_AND_COST_POLICY.json",
            ROOT / "studies/compounding-discovery-v1/V3_SEED_POLICY.json",
            ROOT / "studies/compounding-discovery-v1/V3_PROSPECTIVE_AMENDMENT.json",
            ROOT / "studies/compounding-discovery-v1/V3_PROSPECTIVE_AMENDMENT.md",
            ROOT / "studies/compounding-discovery-v1/v3-proposal/TYPE_HYGIENE.json",
            ROOT / "studies/compounding-discovery-v1/v3-proposal/typed-runner.patch",
        )
        if path.exists()
    )
    paths.extend(
        path
        for path in (
            Path(__file__).with_name("audit.py"),
            Path(__file__).with_name("test_engine.py"),
            Path(__file__).with_name("test_shared_charger.py"),
            Path(__file__).with_name("test_decimal_witness.py"),
        )
        if path.exists()
    )
    paths.extend(sorted(Path(__file__).parent.glob("*.py")))
    runtime = ROOT / "alpha_factory_v1/core/runtime"
    paths.extend(runtime / name for name in ("cli.py", "engine.py", "models.py", "store.py"))
    paths.extend(sorted(path for path in Path(__file__).with_name("source-evidence").rglob("*") if path.is_file()))
    for folder in ("compounding_discovery", "structural_transfer"):
        paths.extend(sorted((runtime / folder).glob("*.py")))
    if reference:
        paths.append(reference)
    result = {}
    for path in paths:
        resolved = path.resolve()
        name = str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)
        result[name] = file_hash(resolved)
    return result


def storage_guard(directory: Path, phase: str, identity: str) -> dict[str, Any]:
    free = shutil.disk_usage(directory).free
    record = {
        "id": f"guard-{secrets.token_hex(12)}",
        "phase": phase,
        "identity": identity,
        "free_bytes": free,
        "floor_bytes": STORAGE_FLOOR,
        "qualified": free >= STORAGE_FLOOR,
        "time_ns": time.time_ns(),
    }
    path = directory / "resource-observations.jsonl"
    if path.is_symlink():
        raise StorageBoundary("resource receipt path is a symlink")
    with path.open("ab") as stream:
        stream.write(canonical(record) + b"\n")
        stream.flush()
    if not record["qualified"]:
        write(
            directory / f"resource-failure-{record['id']}.json",
            {"status": "NOT COMPLETE", "reason": "frozen reserved disk floor", "resource_observation": record},
        )
        raise StorageBoundary(f"free disk {free} bytes is below the frozen {STORAGE_FLOOR}-byte reserve")
    return record


def unchanged(sources: dict[str, str]) -> None:
    paths = [(Path(path) if Path(path).is_absolute() else ROOT / path, value) for path, value in sources.items()]
    if any(not path.is_file() or file_hash(path) != value for path, value in paths):
        raise ValueError("frozen source changed; create a revised campaign with fresh confirmation")


def snapshot_sources(directory: Path, sources: dict[str, str]) -> dict[str, str]:
    snapshots = {}
    for name, expected in sources.items():
        source = Path(name) if Path(name).is_absolute() else ROOT / name
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("source changed while creating the execution snapshot")
        path = directory / "source-snapshot" / expected
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != raw:
                raise ValueError("source snapshot collision")
        else:
            with path.open("xb") as stream:
                stream.write(raw)
        snapshots[name] = str(path.relative_to(directory))
    return snapshots


def make_panel(base: dict[str, Any], seed: int, count: int, prefix: str) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    tasks = []
    for regime in REGIMES:
        for index in range(count):
            task = copy.deepcopy(base)
            task["id"] = f"{prefix}-{regime}-{index}-{seed:x}"
            values: tuple[float, float, float, float, float]
            if regime == "nominal":
                values = (rng.uniform(0.97, 1.03), rng.uniform(0.95, 1.05), rng.uniform(0.97, 1.03), 0, 1)
            elif regime == "energy":
                values = (rng.uniform(1, 1.1), rng.uniform(0.55, 1.1), rng.uniform(1.05, 1.6), 0, 1)
            elif regime == "windows":
                values = (rng.uniform(0.98, 1.08), 1, 1, rng.uniform(0, 4), rng.uniform(0.55, 1.05))
            else:
                values = (
                    rng.uniform(1.05, 1.4),
                    rng.uniform(0.5, 0.95),
                    rng.uniform(1.1, 1.6),
                    rng.uniform(0, 5),
                    rng.uniform(0.5, 0.95),
                )
            task["updates"] = dict(
                zip(
                    (
                        "travel_multiplier",
                        "charge_multiplier",
                        "consumption_multiplier",
                        "window_shift",
                        "window_scale",
                    ),
                    (f"{value:.8f}" for value in values),
                )
            )
            task["need"] = (
                "Check the declared fixed route for all sixteen passenger requests after operator "
                "travel, charging, energy-use and appointment updates; no physical dispatch authority."
            )
            tasks.append({"case_id": task["id"], "regime": regime, "target": task})
    return tasks


def percentile(values: list[float], proportion: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(proportion * (len(ordered) - 1))))]


def paired_estimate(
    clusters: list[dict[str, float]], contrast: Callable[[dict[str, float]], float], seed: int, draws: int = 2000
) -> dict[str, Any]:
    if not clusters:
        return {"estimate": None, "ci95": None, "clusters": 0}
    values = [contrast(cluster) for cluster in clusters]
    rng = random.Random(seed)
    sampled = [statistics.fmean(rng.choices(values, k=len(values))) for _ in range(draws)]
    return {
        "estimate": statistics.fmean(values),
        "ci95": [percentile(sampled, 0.025), percentile(sampled, 0.975)],
        "clusters": len(values),
        "method": "task-cluster paired percentile bootstrap",
        "draws": draws,
    }


def factorial_analysis(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[float]]] = {}
    for record in records:
        if record["arm"] in ARMS:
            grouped.setdefault(record["case_id"], {}).setdefault(record["arm"], []).append(float(record["accepted"]))
    clusters = [
        {arm: statistics.fmean(values) for arm, values in cluster.items()}
        for cluster in grouped.values()
        if set(cluster) == set(ARMS)
    ]
    effects: dict[str, Any] = {}
    for size in (1, 2, 3):
        for selected in itertools.combinations("ASC", size):

            def contrast(cell: dict[str, float], selected: tuple[str, ...] = selected) -> float:
                terms = []
                for arm, flags in ARMS.items():
                    sign = (-1) ** sum(not flags[name] for name in selected)
                    terms.append(sign * cell[arm])
                return cast(float, sum(terms) / 2 ** (3 - len(selected)))

            name = "".join(selected)
            effects[name] = paired_estimate(clusters, contrast, 77000 + sum(map(ord, selected)))
    full = paired_estimate(clusters, lambda cell: cell["ASC"] - cell["none"], 812721)
    cells = {}
    for arm in [*ARMS, "frontier_program"]:
        arm_records = [r for r in records if r["arm"] == arm]
        if arm_records:
            costs = [float(Fraction(r["cost_total"])) for r in arm_records]
            cells[arm] = {
                "n": len(arm_records),
                "accepted": sum(r["accepted"] for r in arm_records),
                "accepted_rate": statistics.fmean(float(r["accepted"]) for r in arm_records),
                "accepted_feasible": sum(r["feasible"] for r in arm_records),
                "rejected_unsupported_conclusions": sum(r["unsupported_conclusion"] for r in arm_records),
                "mean_execution_cost_usd": statistics.fmean(costs),
                "total_execution_cost_usd": str(sum((Fraction(r["cost_total"]) for r in arm_records), Fraction())),
                "mean_cpu_seconds": statistics.fmean(float(r["measurements"]["cpu_seconds"]) for r in arm_records),
            }
    supported = full["estimate"] is not None and full["estimate"] >= 0.05 and full["ci95"][0] > 0
    paired: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for record in records:
        paired.setdefault((record["case_id"], record["run_seed"]), {})[record["arm"]] = record
    complete_pairs = [row for row in paired.values() if "ASC" in row and "none" in row]
    for arm, cell in cells.items():
        cell["independently_contradicted_conclusions"] = sum(
            row["none"]["accepted"]
            and row[arm]["result"]["artifact"]["status"] in {"FEASIBLE", "INFEASIBLE"}
            and row[arm]["result"]["artifact"]["status"] != row["none"]["result"]["artifact"]["status"]
            for row in paired.values()
            if arm in row and "none" in row
        )
    return {
        "cells": cells,
        "full_vs_none": full,
        "factorial_effects": effects,
        "fresh_feasible_full_only": sum(
            row["ASC"]["feasible"] and not row["none"]["feasible"] for row in complete_pairs
        ),
        "negative_transfer_full_rejected_none_accepted": sum(
            not row["ASC"]["accepted"] and row["none"]["accepted"] for row in complete_pairs
        ),
        "strong_conventional_reference": "none: existing full-semantics direct LP, not a weakened solver",
        "combination_practical_gain_supported": supported,
        "synergy_scale": "additive accepted-certificate proportion",
        "positive_interactions": [
            name
            for name, value in effects.items()
            if len(name) > 1 and value["ci95"] is not None and value["ci95"][0] > 0
        ],
        "multiplication_tested": False,
    }


def learning_analysis(
    records: list[dict[str, Any]],
    training: list[dict[str, Any]] | None = None,
    promotions: list[dict[str, Any]] | None = None,
    memory_sizes: dict[int, int] | None = None,
) -> dict[str, Any]:
    training, promotions, memory_sizes = training or [], promotions or [], memory_sizes or {}
    checkpoints = sorted(set(record["checkpoint"] for record in records))
    output = {}
    for checkpoint in checkpoints:
        selected = [record for record in records if record["checkpoint"] == checkpoint]
        grouped: dict[str, dict[str, list[float]]] = {}
        for record in selected:
            grouped.setdefault(record["case_id"], {}).setdefault(record["arm"], []).append(float(record["accepted"]))
        clusters = [
            {arm: statistics.fmean(value) for arm, value in row.items()}
            for row in grouped.values()
            if set(row) == set(SYSTEMS)
        ]
        systems = {}
        for system in SYSTEMS:
            rows = [row for row in selected if row["arm"] == system]
            marginal = sum((Fraction(row["cost_total"]) for row in rows), Fraction())
            origin = sum(
                (Fraction(row["cost_total"]) for row in training if row["checkpoint"] <= checkpoint), Fraction()
            )
            origin = origin if system in {"cumulative", "retrieval"} else Fraction()
            promotion = sum(
                (Fraction(event["amount"]) for event in promotions if event["checkpoint"] <= checkpoint), Fraction()
            )
            promotion = promotion if system == "cumulative" else Fraction()
            retained_bytes = memory_sizes.get(checkpoint if system in {"cumulative", "retrieval"} else 0, 0)
            retention = Fraction(retained_bytes * 3, 100_000_000_000)
            systems[system] = {
                "n": len(rows),
                "accepted": sum(row["accepted"] for row in rows),
                "mean_solver_calls": statistics.fmean(row["result"]["resources"]["solver_calls"] for row in rows),
                "mean_operations": statistics.fmean(row["result"]["resources"]["operations"] for row in rows),
                "marginal_cost_usd": str(marginal),
                "mean_marginal_cost_usd": str(marginal / max(1, len(rows))),
                "historical_record_origin_cost_usd": str(origin),
                "structured_promotion_cost_usd": str(promotion),
                "retention_bytes": retained_bytes,
                "one_month_retention_cost_usd": str(retention),
                "known_lifecycle_cost_usd": str(marginal + origin + promotion + retention),
            }
        paired_resources = {}
        for metric in ("cost_total", "solver_calls", "operations"):
            grouped_resources: dict[str, dict[str, list[float]]] = {}
            for row in selected:
                value = (
                    float(Fraction(row["cost_total"]))
                    if metric == "cost_total"
                    else float(row["result"]["resources"][metric])
                )
                grouped_resources.setdefault(row["case_id"], {}).setdefault(row["arm"], []).append(value)
            resource_clusters = [
                {arm: statistics.fmean(value) for arm, value in row.items()}
                for row in grouped_resources.values()
                if set(row) == set(SYSTEMS)
            ]
            paired_resources[metric] = {
                control: paired_estimate(resource_clusters, _control_difference(control), 61000 + checkpoint)
                for control in SYSTEMS[1:]
            }
        output[str(checkpoint)] = {
            "systems": systems,
            "paired_resource_differences_full_minus_control": paired_resources,
            "paired_gains": {
                control: paired_estimate(clusters, _control_difference(control), 45100 + checkpoint)
                for control in SYSTEMS[1:]
            },
        }
    last = output[str(checkpoints[-1])] if checkpoints else {}
    gains = last.get("paired_gains", {})
    supported = bool(gains) and all(item["estimate"] >= 0.05 and item["ci95"][0] > 0 for item in gains.values())
    return {
        "checkpoints": output,
        "progressive_usefulness_supported": supported,
        "retention_assumption": "USD 0.03 per decimal GB-month, one month; simulated rate, not an invoice",
        "lifecycle_scope": "Checkpoint deployment panel plus prior historical generation, checked promotion, one-month memory retention; authoring/source-origin costs separate",
        "allocation": "Historical records are generated once; their common origin cost is shown once in each history-consuming counterfactual, not added twice as actual spending",
        "scope": "Fresh parameter instances of one known public fixed-route structure; no new-domain claim",
    }


def observation(
    path: Path,
    request: dict[str, Any],
    memory: dict[str, Any],
    metadata: dict[str, Any],
    execute: Callable[..., Any],
    campaign_root: Path,
) -> dict[str, Any]:
    from alpha_factory_v1.core.runtime.compounding_discovery.engine import source_hashes
    from alpha_factory_v1.core.runtime.structural_transfer import eadarp_check

    path = path.with_suffix(".json.gz")
    guard = storage_guard(campaign_root, "observation", request["id"])
    if path.exists():
        record = read(path)
        if record["request"] != request or record["memory_version"] != digest(memory):
            raise ValueError("resume input or memory identity differs")
        return cast(dict[str, Any], record)
    begin, cpu = time.perf_counter(), time.process_time()
    cpu_started_ns = time.process_time_ns()
    snapshot: dict[str, Any] = {"costs": [], "operations": 0, "solver_calls": 0, "elapsed_cpu_ns": 0}

    def checkpoint(value: dict[str, Any]) -> None:
        snapshot.clear()
        snapshot.update(copy.deepcopy(value))

    try:
        result = execute(request, copy.deepcopy(memory), _checkpoint=checkpoint)
    except Exception as exc:
        from alpha_factory_v1.core.runtime.compounding_discovery.engine import CPU_RATE

        artifact = {
            "schema": "agialpha/eadarp-certificate/v1",
            "task_hash": digest(request["target"]),
            "status": "UNRESOLVED",
            "vehicles": [],
            "objective": "0",
            "witness": {},
            "scope": "declared-eADARP-linear-model-only",
        }
        costs = snapshot["costs"]
        elapsed = Fraction(time.process_time_ns() - cpu_started_ns, 10**9)
        overhead = max(Fraction(), elapsed - sum((Fraction(x["quantity"]) for x in costs), Fraction()))
        costs.append(
            {
                "id": "failed-closing-envelope",
                "stage": "failed-execution-overhead",
                "quantity": str(overhead),
                "rate": CPU_RATE,
                "amount": str(overhead * Fraction(CPU_RATE)),
                "basis": "measured-cpu",
            }
        )
        result = {
            "schema": "agialpha/discovery-result/v1",
            "status": "FAILED",
            "error": type(exc).__name__,
            "id": request["id"],
            "request": request,
            "request_hash": digest(request),
            "source_hashes": source_hashes(),
            "artifact": artifact,
            "accepted": False,
            "acceptance": eadarp_check.check(request["target"], artifact),
            "costs": costs,
            "cost_total": str(sum((Fraction(x["amount"]) for x in costs), Fraction())),
            "budget_cap": request["budget"],
            "resources": {
                "operations": len(costs),
                "solver_calls": snapshot["solver_calls"],
                "cpu_seconds": str(sum((Fraction(x["quantity"]) for x in costs), Fraction())),
            },
            "memory_before_hash": memory["memory_hash"],
            "memory_used": [],
            "funding": {"earned": False, "source": "seed-funded-research"},
        }
        result["result_hash"] = digest(result)
    verdict = eadarp_check.check(request["target"], result["artifact"])
    accepted = verdict.get("accepted") is True
    status = result["artifact"].get("status")
    record = {
        "schema": SCHEMA,
        **metadata,
        "request": request,
        "target": request["target"],
        "task_hash": digest(request["target"]),
        "result": result,
        "independent_acceptance": verdict,
        "memory_version": digest(memory),
        "storage_guard_id": guard["id"],
        "accepted": accepted,
        "feasible": accepted and status == "FEASIBLE",
        "unsupported_conclusion": status in {"FEASIBLE", "INFEASIBLE"} and not accepted,
        "conclusion_truth_note": "Rejected certificates are unsupported; a false conclusion requires an independently accepted opposite-status certificate",
        "cost_total": result["cost_total"],
        "measurements": {
            "wall_seconds": str(time.perf_counter() - begin),
            "cpu_seconds": str(time.process_time() - cpu),
        },
    }
    write(path, record)
    return record


def reference_executor(path: Path) -> Callable[..., Any]:
    if file_hash(path) != REFERENCE_HASH:
        raise ValueError("frontier program source identity changed")
    spec = importlib.util.spec_from_file_location("source_bound_frontier_reference", path)
    if spec is None or spec.loader is None:
        raise ValueError("reference module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    frontier = cast(FrontierProgram, module)

    def execute_reference(
        request: dict[str, Any], memory: dict[str, Any], *, _checkpoint: Callable[..., Any] | None = None
    ) -> dict[str, Any]:
        from alpha_factory_v1.core.runtime.compounding_discovery.engine import CPU_RATE, Meter, source_hashes
        from alpha_factory_v1.core.runtime.structural_transfer import eadarp_check

        meter = Meter(request["budget"], _checkpoint)
        meter.stage("independent-input-contract", lambda: eadarp_check._read(request["target"]))
        original = frontier.linprog

        def counted_solver(*solver_args: Any, **kwargs: Any) -> Any:
            meter.solver()
            kwargs["options"] = {**kwargs.get("options", {}), "time_limit": meter.remaining()}
            return original(*solver_args, **kwargs)

        frontier.linprog = counted_solver
        try:
            raw_artifact = meter.stage(
                "source-pinned-frontier-program", lambda: frontier.solve(request["target"], cache=False)
            )
        finally:
            frontier.linprog = original

        def normalize() -> dict[str, Any]:
            artifact: dict[str, Any] = copy.deepcopy(raw_artifact)
            old = artifact.get("witness", {})
            if (
                artifact.get("status") == "INFEASIBLE"
                and old.get("type") == "bounded-farkas/v1"
                and "residual_lower_bound" in old
            ):
                with localcontext() as context:
                    context.prec = 250
                    gap = format(Decimal(old["residual_lower_bound"]) - Decimal(old["contradiction"]), ".24f")
                artifact["witness"] = {
                    "type": old["type"],
                    "vehicle": old["vehicle"],
                    "rows": old["rows"],
                    "contradiction": gap,
                }
            return artifact

        artifact = meter.stage("source-witness-wire-format-adaptation", normalize)
        verdict = meter.stage("final-independent-acceptance", lambda: eadarp_check.check(request["target"], artifact))
        costs = copy.deepcopy(meter.costs)
        result = {
            "schema": "agialpha/discovery-result/v1",
            "id": request["id"],
            "request": request,
            "method": "source-bound-frontier-authored-program",
            "request_hash": digest(request),
            "source_hashes": source_hashes(),
            "reference_sha256": REFERENCE_HASH,
            "reference_raw_artifact": raw_artifact,
            "reference_adaptation": "Canonical bounded-gap witness = declared residual lower bound minus declared weighted rhs; no solver or checker change",
            "artifact": artifact,
            "acceptance": verdict,
            "accepted": verdict.get("accepted") is True,
            "costs": costs,
            "cost_total": str(sum((Fraction(x["amount"]) for x in costs), Fraction())),
            "budget_cap": request["budget"],
            "resources": {
                "operations": meter.operations,
                "solver_calls": meter.calls,
                "cpu_seconds": str(sum((Fraction(x["quantity"]) for x in costs), Fraction())),
            },
            "memory_before_hash": memory["memory_hash"],
            "memory_used": [],
            "funding": {"earned": False, "source": "seed-funded-research"},
        }
        elapsed = Fraction(time.process_time_ns() - meter.start, 10**9)
        overhead = elapsed - sum((Fraction(x["quantity"]) for x in costs), Fraction())
        costs.append(
            {
                "id": "closing-envelope",
                "stage": "execution-overhead",
                "quantity": str(overhead),
                "rate": CPU_RATE,
                "amount": str(overhead * Fraction(CPU_RATE)),
                "basis": "measured-cpu",
            }
        )
        result["resources"]["operations"] = len(costs)
        result["resources"]["cpu_seconds"] = str(elapsed)
        result["cost_total"] = str(sum((Fraction(x["amount"]) for x in costs), Fraction()))
        if len(costs) > request["budget"]["operations"] or elapsed > request["budget"]["cpu_seconds"]:
            raise ValueError("reference closing envelope exceeds common resource cap")
        result["result_hash"] = digest(result)
        return result

    return execute_reference


def run(args: argparse.Namespace) -> dict[str, Any]:
    from alpha_factory_v1.core.runtime.compounding_discovery.engine import (
        CPU_RATE,
        empty_memory,
        execute,
        learn,
        source_hashes,
    )

    previous = args.reproduce_from or args.final_from
    root = args.output.resolve()
    if root.exists() and not args.resume:
        raise ValueError("output exists; use a fresh directory or --resume")
    root.mkdir(parents=True, exist_ok=args.resume)
    if previous:
        original = previous.resolve()
        freeze = read(original / "freeze.json")
        unchanged(freeze["sources"])
        config, seeds = freeze["config"], read(original / "seeds.json")
        base, captures, mapping = (
            read(original / "base.json"),
            read(original / "captures.json"),
            read(original / "mapping.json"),
        )
    elif args.resume:
        freeze = read(root / "freeze.json")
        unchanged(freeze["sources"])
        config, seeds = freeze["config"], read(root / "seeds.json")
        base, captures, mapping = read(root / "base.json"), read(root / "captures.json"), read(root / "mapping.json")
    else:
        if not args.base or not args.capture or not args.mapping:
            raise ValueError("--base, --capture and --mapping are required for a new campaign")
        base, captures, mapping = read(args.base), [read(path) for path in args.capture], read(args.mapping)
        config = {
            "tasks_per_regime": args.tasks_per_regime,
            "run_seeds": args.run_seeds,
            "cycles": args.cycles,
            "training_tasks_per_regime": args.training_tasks_per_regime,
            "budget": {
                "operations": args.operations,
                "solver_calls": args.solver_calls,
                "cpu_seconds": args.cpu_seconds,
            },
            "reference_path": (
                str(args.reference_program.resolve().relative_to(ROOT))
                if args.reference_program and args.reference_program.resolve().is_relative_to(ROOT)
                else str(args.reference_program.resolve())
                if args.reference_program
                else None
            ),
            "practical_gain": 0.05,
            "bootstrap_draws": 2000,
            "regimes": list(REGIMES),
        }
        reference = args.reference_program.resolve() if args.reference_program else None
        if reference and file_hash(reference) != REFERENCE_HASH:
            raise ValueError("reference differs from inspected preceding frontier-authored source")
        freeze = {
            "schema": "agialpha/discovery-freeze/v1",
            "sources": source_manifest(reference),
            "config": config,
            "engine_source_hashes": source_hashes(),
            "base_hash": digest(base),
            "captures_hash": digest(captures),
            "mapping_hash": digest(mapping),
            "authority": "local simulated work only",
            "future_seed_sampled_after_freeze": True,
            "resource_policy": {
                "preserve_free_disk_bytes": STORAGE_FLOOR,
                "guard_version": "pre-observation-and-promotion/v1",
            },
        }
        freeze["source_snapshots"] = snapshot_sources(root, freeze["sources"])
        write(root / "freeze.json", freeze)
        seeds = {
            "factorial": secrets.randbits(48),
            "training": [secrets.randbits(48) for _ in range(config["cycles"])],
            "checkpoint": [secrets.randbits(48) for _ in range(config["cycles"] + 1)],
            "final_untouched": secrets.randbits(48),
            "execution": [secrets.randbits(32) for _ in range(config["run_seeds"])],
        }
    if "source_snapshots" in freeze:
        if snapshot_sources(root, freeze["sources"]) != freeze["source_snapshots"]:
            raise ValueError("source snapshot mapping differs")
    for name, value in (
        ("freeze", freeze),
        ("seeds", seeds),
        ("base", base),
        ("captures", captures),
        ("mapping", mapping),
    ):
        write(root / f"{name}.json", value)
    if (
        digest(base) != freeze["base_hash"]
        or digest(captures) != freeze["captures_hash"]
        or digest(mapping) != freeze["mapping_hash"]
    ):
        raise ValueError("captured input identity mismatch")
    if args.resume and (root / "summary.json").is_file():
        return cast(dict[str, Any], read(root / "summary.json"))
    initial, memory = empty_memory(), empty_memory()
    if args.final_from:
        memory = read(original / "memory-final.json")
    factorial, learning_records, training_records, learning_costs = [], [], [], []
    memory_sizes = {0: len(canonical(initial))}
    reference_path = Path(config["reference_path"]) if config["reference_path"] else None
    if reference_path and not reference_path.is_absolute():
        reference_path = ROOT / reference_path
    reference = reference_executor(reference_path) if reference_path else None
    if args.final_from:
        training_records = [read(path) for path in sorted((original / "training").glob("*.json*"))]
        learning_costs = read(original / "learning-costs.json")
        historical_resources = original / "resource-observations.jsonl"
        if historical_resources.exists():
            destination = root / "historical-resource-observations.jsonl"
            raw = historical_resources.read_bytes()
            if destination.exists():
                if destination.read_bytes() != raw:
                    raise ValueError("historical resource receipt collision")
            else:
                with destination.open("xb") as stream:
                    stream.write(raw)

    def request_for(
        target: dict[str, Any], ident: str, flags: dict[str, bool], seed: int, mode: str = "structured"
    ) -> dict[str, Any]:
        return {
            "schema": "agialpha/discovery-request/v1",
            "id": ident,
            "target": target,
            "capabilities": flags,
            "budget": config["budget"],
            "seed": seed,
            "captures": captures,
            "mapping": mapping,
            "memory_mode": mode,
        }

    if not args.final_from:
        panel = make_panel(base, seeds["factorial"], config["tasks_per_regime"], "factorial")
        write(root / "factorial-panel.json", panel)
        for case in panel:
            for seed in seeds["execution"]:
                arm_names = [*ARMS, *(["frontier_program"] if reference else [])]
                random.Random(seed ^ int(digest(case["case_id"])[:8], 16)).shuffle(arm_names)
                for arm in arm_names:
                    flags = ARMS.get(arm, ARMS["none"])
                    request = request_for(case["target"], f"{arm}-{seed}-{case['case_id']}", flags, seed)
                    metadata = {
                        "phase": "factorial",
                        "case_id": case["case_id"],
                        "regime": case["regime"],
                        "arm": arm,
                        "run_seed": seed,
                    }
                    factorial.append(
                        observation(
                            root / "factorial" / case["case_id"] / f"{arm}-{seed}.json",
                            request,
                            initial,
                            metadata,
                            cast(Callable[..., Any], reference) if arm == "frontier_program" else execute,
                            root,
                        )
                    )
    checkpoints = [config["cycles"]] if args.final_from else list(range(config["cycles"] + 1))
    for checkpoint in checkpoints:
        if checkpoint and not args.final_from:
            training = make_panel(
                base, seeds["training"][checkpoint - 1], config["training_tasks_per_regime"], f"train-{checkpoint}"
            )
            for case in training:
                seed = seeds["execution"][0]
                request = request_for(case["target"], case["case_id"], ARMS["ASC"], seed)
                metadata = {
                    "phase": "training",
                    "case_id": case["case_id"],
                    "regime": case["regime"],
                    "arm": "cumulative",
                    "run_seed": seed,
                    "checkpoint": checkpoint,
                }
                record = observation(
                    root / "training" / f"{case['case_id']}.json", request, memory, metadata, execute, root
                )
                training_records.append(record)
                if record["accepted"]:
                    guard = storage_guard(root, "promotion", case["case_id"])
                    cost_path = root / "learning-costs" / f"{case['case_id']}.json"
                    started = time.process_time_ns()
                    promotion_error = None
                    memory_before = memory["memory_hash"]
                    try:
                        memory = learn(memory, record["result"])
                    except Exception as exc:
                        promotion_error = type(exc).__name__
                        raise
                    finally:
                        quantity = Fraction(time.process_time_ns() - started, 10**9)
                        measured_event = {
                            "id": f"promotion-{case['case_id']}",
                            "stage": "checked-chronological-promotion",
                            "quantity": str(quantity),
                            "rate": CPU_RATE,
                            "amount": str(quantity * Fraction(CPU_RATE)),
                            "basis": "measured-cpu",
                            "checkpoint": checkpoint,
                            "promotion_accepted": promotion_error is None,
                            "error_type": promotion_error,
                            "storage_guard_id": guard["id"],
                        }
                        if cost_path.exists():
                            event = read(cost_path)
                            recovery_id = f"recovery-{case['case_id']}-{secrets.token_hex(8)}"
                            write(
                                root / "recovery-costs" / f"{recovery_id}.json",
                                {
                                    **measured_event,
                                    "id": recovery_id,
                                    "stage": "resume-memory-reconstruction",
                                    "original_promotion_cost_receipt": str(cost_path.relative_to(root)),
                                },
                            )
                        else:
                            event = measured_event
                            write(cost_path, event)
                        learning_costs.append(event)
                        if promotion_error:
                            write(root / "learning-costs.json", learning_costs)
                            write(
                                root / "promotion-failure.json",
                                {
                                    "status": "NOT COMPLETE",
                                    "phase": "chronological-promotion",
                                    "error_type": promotion_error,
                                    "case_id": case["case_id"],
                                    "memory_before_hash": memory_before,
                                    "source_freeze": digest(freeze),
                                    "incurred_cost_receipt": str(cost_path.relative_to(root)),
                                    "cost_event": measured_event,
                                },
                            )
            write(root / f"memory-{checkpoint}.json", memory)
        memory_sizes[checkpoint] = len(canonical(memory))
        panel_seed = seeds["final_untouched"] if args.final_from else seeds["checkpoint"][checkpoint]
        prefix = "final" if args.final_from else f"checkpoint-{checkpoint}"
        panel = make_panel(base, panel_seed, config["tasks_per_regime"], prefix)
        write(root / f"{prefix}-panel.json", panel)
        for case in panel:
            for seed in seeds["execution"]:
                for system in SYSTEMS:
                    state = memory if system in {"cumulative", "retrieval"} else initial
                    flags = ARMS["SC"] if system == "retrieval" else ARMS["ASC"]
                    request = request_for(
                        case["target"],
                        f"{system}-{seed}-{case['case_id']}",
                        flags,
                        seed,
                        "retrieval" if system == "retrieval" else "structured",
                    )
                    metadata = {
                        "phase": "final" if args.final_from else "learning",
                        "checkpoint": checkpoint,
                        "case_id": case["case_id"],
                        "regime": case["regime"],
                        "arm": system,
                        "run_seed": seed,
                    }
                    learning_records.append(
                        observation(
                            root / "learning" / str(checkpoint) / case["case_id"] / f"{system}-{seed}.json",
                            request,
                            state,
                            metadata,
                            execute,
                            root,
                        )
                    )
    write(root / "memory-final.json", memory)
    unchanged(freeze["sources"])
    marginal = sum((Fraction(r["cost_total"]) for r in learning_records), Fraction())
    training_cost = sum((Fraction(r["cost_total"]) for r in training_records), Fraction())
    promotion_cost = sum((Fraction(event["amount"]) for event in learning_costs), Fraction())
    write(root / "learning-costs.json", learning_costs)
    resource_observations = [
        json.loads(line) for line in (root / "resource-observations.jsonl").read_text().splitlines()
    ]
    summary = {
        "schema": "agialpha/discovery-summary/v1",
        "source_freeze": digest(freeze),
        "factorial": factorial_analysis(factorial),
        "learning": learning_analysis(learning_records, training_records, learning_costs, memory_sizes),
        "training_execution_cost_usd": str(training_cost),
        "chronological_promotion_cost_usd": str(promotion_cost),
        "known_training_plus_all_checkpoint_execution_cost_usd": str(training_cost + promotion_cost + marginal),
        "cpu_rate_assumption_usd_per_hour": "0.10",
        "cpu_rate_10x_sensitivity_multiplier": 10,
        "retention_bytes": len(canonical(memory)),
        "retention_monetary_rate_usd_per_gb_month": "0.03",
        "cost_event_identity": "result.request_hash + '/' + scoped cost event id",
        "additional_resume_overhead_receipts": "recovery-costs/; separate from original lifecycle costs",
        "storage_policy": {
            "qualified": all(row["qualified"] for row in resource_observations),
            "floor_bytes": STORAGE_FLOOR,
            "checks": len(resource_observations),
            "minimum_observed_free_bytes": min(row["free_bytes"] for row in resource_observations),
            "scope": "Prospective checks before every observation and checked promotion; external concurrent allocation can still intervene between checks",
        },
        "training_count": len(training_records),
        "training_executed_this_run": 0 if args.final_from else len(training_records),
        "final_untouched_executed": bool(args.final_from),
        "final_panel_commitment": digest(seeds["final_untouched"]),
        "all_frozen_sources_unchanged": True,
        "frontier_program": {
            "status": "EXECUTED"
            if reference and not args.final_from
            else "NOT_EXECUTED_FINAL"
            if reference
            else "UNAVAILABLE",
            "sha256": REFERENCE_HASH if reference else None,
            "scope": "previously frontier-authored deterministic program; no new model call",
        },
        "cost_scope": "Modeled per-execution events; development, retained historical source and commercial costs require separate ledger",
        "mission_status": "NOT COMPLETE",
        "commercial_flywheel_established": False,
        "reproduce_command": f"python contrib/compounding_discovery/experiment.py --reproduce-from {root} --output NEW_OUTPUT",
        "final_command": f"python contrib/compounding_discovery/experiment.py --final-from {root} --output NEW_FINAL_OUTPUT",
        "resume_command": f"python contrib/compounding_discovery/experiment.py --resume --output {root}",
    }
    write(root / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--capture", action="append", type=Path)
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--reference-program", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--reproduce-from", type=Path)
    parser.add_argument("--final-from", type=Path)
    parser.add_argument("--tasks-per-regime", type=int, default=4)
    parser.add_argument("--run-seeds", type=int, default=3)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--training-tasks-per-regime", type=int, default=1)
    parser.add_argument("--operations", type=int, default=100)
    parser.add_argument("--solver-calls", type=int, default=16)
    parser.add_argument("--cpu-seconds", type=int, default=30)
    args = parser.parse_args()
    if any(
        not 1 <= value <= 100
        for value in (
            args.tasks_per_regime,
            args.run_seeds,
            args.cycles,
            args.training_tasks_per_regime,
            args.operations,
            args.solver_calls,
            args.cpu_seconds,
        )
    ):
        parser.error("all experiment sizes and budgets must be positive and at most 100")
    if sum((bool(args.resume), bool(args.reproduce_from), bool(args.final_from))) > 1:
        parser.error("choose only one resume/reproduction/final mode")
    if args.cycles * args.training_tasks_per_regime * len(REGIMES) > 16:
        parser.error("chronological training exceeds the runtime's sixteen-record memory authority")
    print(json.dumps(run(args), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
