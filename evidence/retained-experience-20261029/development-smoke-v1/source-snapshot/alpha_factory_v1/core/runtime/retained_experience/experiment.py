# SPDX-License-Identifier: Apache-2.0
"""Execute a frozen, prospective retained-experience comparison, with honest costs."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import secrets
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any, Callable

from ..structural_transfer import eadarp
from . import controls, solver, verifier

ROOT = Path(__file__).resolve().parents[4]
METHODS = {f"{method}-{int(presolve)}": (method, presolve)
           for method in ("highs", "highs-ds", "highs-ipm") for presolve in (True, False)}
ARMS = (*METHODS, "template", "ordinary-cache", "warm-start", "retained")
REGIMES = ("continuity", "tight-windows", "energy-shift", "matrix-shift")
SCHEMA = "agialpha/retained-experience-trial/v1"


def write(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(verifier.canonical(value) + b"\n")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol(count: int, repeats: int) -> dict[str, Any]:
    if type(count) is not int or not 1 <= count <= 16 or type(repeats) is not int or not 1 <= repeats <= 5:
        raise ValueError("bounded panel: 1..16 cases per regime and 1..5 timing repeats")
    return {
        "schema": SCHEMA, "arms": list(ARMS), "regimes": list(REGIMES), "cases_per_regime": count,
        "repeats": repeats, "development_seed": 20261029, "development_per_regime": 2,
        "optimality_gap_max": "1/100000", "minimum_lifecycle_cpu_reduction": "1/10",
        "quality_loss_allowed": 0, "memory_updates_during_evaluation": False,
        "strongest_control": "minimum full-panel lifecycle CPU across every declared competent control",
        "selection": "fallback chosen on development only; ex-post best control is a conservative test, not tuning",
        "confirmation": False, "inference": "exploratory generated parameter panel; no statistical confirmation spent",
        "freshness": "semantic task hashes exclude ID/prose; seed sampled after source and candidate freezes",
        "costs": "training, selection, failed construction, setup, checks, fallback, deployment and storage retained",
        "limits": ["same public raw instance and fixed route family", "no physical dispatch or buyer validation",
                   "standard parametric LP methods, not algorithmic novelty", "shared author, host and libraries",
                   "no universal strongest-workflow claim; only the complete declared comparator set"],
    }


def make_panel(base: dict[str, Any], seed: int, count: int, prefix: str) -> list[dict[str, Any]]:
    rng, tasks = random.Random(seed), []
    for regime in REGIMES:
        for index in range(count):
            task = deepcopy(base)
            task["id"] = f"{prefix}-{regime}-{index}"
            if regime == "continuity":
                values = (rng.uniform(.98, 1.03), 1, rng.uniform(.98, 1.03), rng.uniform(0, .5), rng.uniform(.99, 1.03))
            elif regime == "tight-windows":
                values = (rng.uniform(1.01, 1.05), 1, 1, rng.uniform(1, 3), rng.uniform(.8, .94))
            elif regime == "energy-shift":
                values = (rng.uniform(1.1, 1.2), 1, rng.uniform(1.25, 1.6), 0, 1)
            else:
                values = (rng.uniform(1, 1.1), rng.uniform(.65, .85), rng.uniform(1, 1.2), 0, 1)
            task["updates"] = dict(zip(
                ("travel_multiplier", "charge_multiplier", "consumption_multiplier", "window_shift", "window_scale"),
                (f"{x:.8f}" for x in values),
            ))
            tasks.append(task)
    return tasks


def _measure(function: Callable[[], Any]) -> tuple[Any, int, int]:
    cpu, wall = time.process_time_ns(), time.monotonic_ns()
    value = function()
    return value, time.process_time_ns() - cpu, time.monotonic_ns() - wall


def default_costs() -> dict[str, Any]:
    return {"basis": "modeled rates; unresolved costs are null, never zero", "cpu_usd_per_hour": "1/10",
            "storage_usd_per_gb_month": "3/100", "retention_months": "1", "shared_development_usd": None,
            "arm_fixed_usd": {arm: None for arm in ARMS}, "arm_per_task_usd": {arm: None for arm in ARMS}}


def validate_costs(costs: dict[str, Any]) -> None:
    if set(costs) != set(default_costs()) or not isinstance(costs["basis"], str) or not costs["basis"].strip():
        raise ValueError("explicit complete-cost policy required")
    for key in ("cpu_usd_per_hour", "storage_usd_per_gb_month", "retention_months", "shared_development_usd"):
        if costs[key] is not None and (not isinstance(costs[key], str) or Fraction(costs[key]) < 0):
            raise ValueError("nonnegative exact declared costs required")
    if any(costs[k] is None for k in ("cpu_usd_per_hour", "storage_usd_per_gb_month", "retention_months")):
        raise ValueError("resource rates required")
    for key in ("arm_fixed_usd", "arm_per_task_usd"):
        if set(costs[key]) != set(ARMS):
            raise ValueError("cost policy must cover every arm")
        for value in costs[key].values():
            if value is not None and (not isinstance(value, str) or Fraction(value) < 0):
                raise ValueError("nonnegative exact declared arm costs required")


def summarize(
    directory: Path, setup: dict[str, int], storage: dict[str, int], costs: dict[str, Any], audit: dict[str, Any],
) -> dict[str, Any]:
    planned = verifier.read(directory / "protocol.json")
    records = [json.loads(line) for line in (directory / "observations.jsonl").read_text().splitlines()]
    ledger = [json.loads(line) for line in (directory / "costs.jsonl").read_text().splitlines()]
    totals = {}
    for arm in ARMS:
        selected = [row for row in records if row["arm"] == arm]
        grouped: dict[str, list[int]] = {}
        for row in (x for x in ledger if x["arm"] == arm):
            grouped.setdefault(row["task_hash"], []).append(row["cpu_ns"])
        deployment = sum(int(statistics.median(values)) for values in grouped.values())
        # Timing repeats are diagnostics, not three independently productive deliveries.
        common_verification = (audit["process_cpu_ns"] - sum(audit["arm_check_cpu_ns"].values())) if arm not in METHODS else 0
        lifecycle = setup[arm] + deployment + audit["arm_check_cpu_ns"].get(arm, 0) // planned["repeats"] + common_verification
        partial = Fraction(lifecycle, 10**9 * 3600) * Fraction(costs["cpu_usd_per_hour"])
        partial += Fraction(storage[arm], 10**9) * Fraction(costs["storage_usd_per_gb_month"]) * Fraction(costs["retention_months"])
        unknown = [key for key in ("shared_development_usd",) if costs[key] is None]
        unknown += [key for key in ("arm_fixed_usd", "arm_per_task_usd") if costs[key][arm] is None]
        full = None
        if not unknown:
            full = partial + Fraction(costs["shared_development_usd"]) + Fraction(costs["arm_fixed_usd"][arm])
            full += len(grouped) * Fraction(costs["arm_per_task_usd"][arm])
        totals[arm] = {"setup_cpu_ns": setup[arm], "deployment_median_cpu_ns": deployment,
                       "lifecycle_cpu_ns": lifecycle, "retained_bytes": storage[arm],
                       "observations": len(selected), "failures": sum("failure" in x for x in selected),
                       "zero_solver_call_observations": sum(x.get("output", {}).get("solver_calls") == 0 for x in selected),
                       "measured_component_modeled_usd": str(partial), "complete_modeled_usd": str(full) if full is not None else None,
                       "unresolved_costs": unknown}
    best = min((arm for arm in ARMS if arm != "retained"), key=lambda arm: totals[arm]["lifecycle_cpu_ns"])
    base, candidate = totals[best]["lifecycle_cpu_ns"], totals["retained"]["lifecycle_cpu_ns"]
    quality = not audit["rejected"]
    reduction = Fraction(base - candidate, base) if base else Fraction(0)
    cpu_pass = quality and reduction >= Fraction(planned["minimum_lifecycle_cpu_reduction"])
    complete = all(totals[arm]["complete_modeled_usd"] is not None for arm in ARMS)
    monetary_pass: bool | None = None
    if complete:
        candidate_cost = Fraction(totals["retained"]["complete_modeled_usd"])
        best_cost = min(Fraction(totals[arm]["complete_modeled_usd"]) for arm in ARMS if arm != "retained")
        monetary_pass = quality and candidate_cost <= best_cost * Fraction(9, 10)
    return {"schema": SCHEMA, "arms": totals, "best_observed_control": best,
            "lifecycle_cpu_reduction": str(reduction), "quality_preserved": quality,
            "measured_cpu_advantage": cpu_pass, "complete_cost_advantage": monetary_pass,
            "overall_demonstration": "SUPPORTED_MODELED_PANEL" if cpu_pass and monetary_pass else
                                     "UNKNOWN_COMPLETE_COST" if cpu_pass and not complete else "NOT_DEMONSTRATED",
            "confirmation": False, "profit_established": False, "actual_external_spending_usd": "0",
            "scope": planned["limits"], "freeze_sha256": file_hash(directory / "freeze.json"),
            "tasks_sha256": file_hash(directory / "tasks.json"), "audit": audit}


def independent_audit(directory: Path, freeze_sha: str, *, save: bool = True) -> dict[str, Any]:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    process = subprocess.run(
        [sys.executable, "-B", "-m", "alpha_factory_v1.core.runtime.retained_experience.verifier",
         str(directory.resolve()), "--freeze-sha256", freeze_sha],
        capture_output=True, text=True, timeout=300, check=False,
        env={"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
             "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
    )
    if len(process.stdout) > 2_000_000:
        raise ValueError("verifier output bound exceeded")
    receipt = json.loads(process.stdout)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt["process_cpu_ns"] = int((after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime) * 1e9)
    if save:
        write(directory / "verification.json", receipt)
    if process.returncode not in {0, 1} or receipt.get("freeze_verified") is not True:
        raise ValueError("independent verification refused; all original outputs retained")
    return receipt


def run(base: dict[str, Any], directory: Path, *, count: int = 8, repeats: int = 3,
        costs: dict[str, Any] | None = None, replay_from: Path | None = None) -> dict[str, Any]:
    """Freeze, learn, then evaluate fresh work once without updating the candidate."""
    policy, rates = protocol(count, repeats), deepcopy(costs if costs is not None else default_costs())
    validate_costs(rates)
    eadarp.parse(base)
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise ValueError("symlink output refused")
    if shutil.disk_usage(directory.parent).free < 200_000_000:
        raise ValueError("insufficient retained evidence reserve")
    directory.mkdir(exist_ok=False)
    started_cpu, started_wall = time.process_time_ns(), time.monotonic_ns()
    try:
        write(directory / "protocol.json", policy)
        write(directory / "cost-policy.json", rates)
        write(directory / "base.json", base)
        sources = [*Path(__file__).parent.glob("*.py"),
                   *Path(__file__).parents[1].joinpath("structural_transfer").glob("*.py"),
                   ROOT / "alpha_factory_v1/core/runtime/compounding_discovery/programs.py",
                   ROOT / "contrib/invention_automation/readonly.py"]
        freeze = {"schema": SCHEMA, "sources": {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(sources)},
                  "protocol_hash": verifier.hash_value(policy), "base_hash": verifier.hash_value(base),
                  "cost_policy_hash": verifier.hash_value(rates), "frozen_at_ns": time.time_ns(),
                  "dependencies": {"numpy": solver.np.__version__, "scipy": controls.scipy.__version__}}
        write(directory / "freeze.json", freeze)
        snapshot = directory / "source-snapshot"
        for name, expected in freeze["sources"].items():
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            raw = (ROOT / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("source changed while freezing snapshot")
            with destination.open("xb") as stream:
                stream.write(raw)
        if replay_from is not None:
            prior = verifier.read(replay_from / "freeze.json")
            if any(prior[key] != freeze[key] for key in ("sources", "protocol_hash", "base_hash", "cost_policy_hash", "dependencies")):
                raise ValueError("replay requires the exact frozen sources, policies, base and dependencies")
        training = [deepcopy(base), *make_panel(base, policy["development_seed"], 2, "development")]
        training[0]["id"] = "development-original"
        history, development = [], []
        scores: dict[str, int] = {arm: 0 for arm in METHODS}
        for target in training:
            for arm, (method, presolve) in METHODS.items():
                def execute() -> dict[str, Any]:
                    output = solver.solve(target, eadarp.compile_model(target), method, presolve)
                    if verifier.check_output(target, output)["accepted"] is not True:
                        raise ValueError("development reference unqualified")
                    return output

                output, cpu, wall = _measure(execute)
                development.append({"target_hash": verifier.hash_value(target), "arm": arm, "cpu_ns": cpu, "wall_ns": wall})
                scores[arm] += cpu
                if arm == "highs-1":
                    history.append({"target": target, "output": output})
        write(directory / "development.json", development)
        write(directory / "history.json", history)
        best = min(scores, key=lambda arm: (scores[arm], arm))
        method, presolve = METHODS[best]
        selection_cpu = sum(scores.values())
        memory, learn_cpu, _ = _measure(lambda: solver.learn(history))
        point_memory, point_cpu, _ = _measure(lambda: solver.learn(history, points_only=True))
        prepared, prepare_cpu, _ = _measure(lambda: solver.PreparedExperience(memory))
        ordinary, ordinary_cpu, _ = _measure(lambda: solver.PreparedExperience(point_memory))
        warm, warm_cpu, _ = _measure(lambda: controls.WarmStart(history))
        templates: dict[str, Any] = {}

        def build_templates() -> None:
            for record in history:
                for item in eadarp.compile_model(record["target"])["vehicles"]:
                    matrix, _, objective = solver.arrays(item)
                    templates[solver.signature(item)] = (matrix, objective)

        _, template_cpu, _ = _measure(build_templates)
        write(directory / "memory.json", memory)
        write(directory / "ordinary-cache.json", point_memory)
        write(directory / "candidate-freeze.json", {"memory_hash": verifier.hash_value(memory),
                                                   "fallback": best, "selection_scores_cpu_ns": scores})
        # All methods and the learned candidate are now frozen, BEFORE the secret seed.
        seed = verifier.read(replay_from / "seed.json")["seed"] if replay_from is not None else secrets.randbits(63)
        tasks = make_panel(base, seed, count, "fresh")
        write(directory / "seed.json", {"seed": seed, "generated_after_candidate_freeze": replay_from is None,
                                        "reproduction": replay_from is not None})
        write(directory / "tasks.json", tasks)
        order_rng = random.Random(seed ^ 0x5A17)
        with ((directory / "observations.jsonl").open("x", encoding="utf-8") as stream,
              (directory / "costs.jsonl").open("x", encoding="utf-8") as cost_stream):
            for repeat in range(repeats):
                ordered_tasks = list(tasks)
                order_rng.shuffle(ordered_tasks)
                for target in ordered_tasks:
                    order = list(ARMS)
                    order_rng.shuffle(order)
                    for arm in order:
                        cpu, wall = time.process_time_ns(), time.monotonic_ns()
                        record: dict[str, Any] = {"task_hash": verifier.hash_value(target), "arm": arm, "repeat": repeat}
                        try:
                            model = eadarp.compile_model(target)
                            if arm in METHODS:
                                output = solver.solve(target, model, *METHODS[arm])
                            elif arm == "template":
                                output = solver.solve(target, model, method, presolve, templates)
                            elif arm == "warm-start":
                                output = warm.run(target, model, method, presolve)
                            else:
                                actor = prepared if arm == "retained" else ordinary
                                output = actor.run(target, model, method=method, presolve=presolve,
                                                   ordinary_cache=arm == "ordinary-cache")
                            record["output"] = output
                            record["acceptance"] = verifier.check_output(target, output)
                        except Exception as error:
                            record["failure"] = type(error).__name__
                        record.update({"cpu_ns": time.process_time_ns() - cpu,
                                       "wall_ns": time.monotonic_ns() - wall})
                        stream.write(verifier.canonical(record).decode() + "\n")
                        stream.flush()
                        event = {"task_hash": record["task_hash"], "arm": arm, "repeat": repeat,
                                 "cpu_ns": time.process_time_ns() - cpu, "wall_ns": time.monotonic_ns() - wall}
                        cost_stream.write(verifier.canonical(event).decode() + "\n")
                        cost_stream.flush()
                        if time.monotonic_ns() - started_wall > 600 * 10**9:
                            raise TimeoutError("campaign wall ceiling; retain partial denominator")
        if verifier.hash_value(prepared.memory) != verifier.hash_value(memory):
            raise ValueError("evaluation changed frozen memory")
        setup = {arm: 0 for arm in METHODS}
        setup.update({"retained": selection_cpu + learn_cpu + prepare_cpu,
                      "ordinary-cache": selection_cpu + point_cpu + ordinary_cpu,
                      "template": selection_cpu + template_cpu, "warm-start": selection_cpu + warm_cpu})
        history_bytes = (directory / "history.json").stat().st_size
        storage = {arm: 0 for arm in METHODS}
        storage.update({"retained": history_bytes + (directory / "memory.json").stat().st_size,
                        "ordinary-cache": history_bytes + (directory / "ordinary-cache.json").stat().st_size,
                        "template": history_bytes + sum(a.nbytes + c.nbytes for a, c in templates.values()),
                        "warm-start": history_bytes + sum(len(b.row_status) + len(b.col_status) for _, b in warm.sessions.values()) * 8})
        write(directory / "lifecycle.json", {"setup_cpu_ns": setup, "retained_bytes": storage,
                                             "development_cpu_ns": selection_cpu})
        audit = independent_audit(directory, file_hash(directory / "freeze.json"))
        summary = summarize(directory, setup, storage, rates, audit)
        summary["campaign_resources"] = {"cpu_ns": time.process_time_ns() - started_cpu,
                                         "verifier_cpu_ns": audit["process_cpu_ns"], "wall_ns": time.monotonic_ns() - started_wall,
                                         "child_cpu_seconds": str(resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime +
                                                                  resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime),
                                         "basis": "actual whole experiment; distinct from counterfactual one-pass deployment"}
        write(directory / "summary.json", summary)
        write(directory / "evidence-seal.json", {"schema": SCHEMA,
              "files": {p.name: file_hash(p) for p in sorted(directory.iterdir()) if p.is_file()},
              "confirmation": False})
        return summary
    except Exception as error:
        write(directory / "failure.json", {"schema": SCHEMA, "error": type(error).__name__, "reason": str(error),
                                          "cpu_ns": time.process_time_ns() - started_cpu,
                                          "wall_ns": time.monotonic_ns() - started_wall, "confirmation": False})
        raise
