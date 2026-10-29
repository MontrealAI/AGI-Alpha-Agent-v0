# SPDX-License-Identifier: Apache-2.0
"""Bounded progressive reuse diagnostic over the unchanged #5024 numerical code."""

from __future__ import annotations

import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import secrets
import subprocess
import sys
import time
from typing import Any, Callable

from alpha_factory_v1.core.runtime.retained_experience import controls, experiment, solver, verifier
from alpha_factory_v1.core.runtime.structural_transfer import eadarp

ROOT = Path(__file__).resolve().parents[2]
STAGES = (0, 4, 8, 12)
ARMS = (*experiment.METHODS, "template", "ordinary-cache", "warm-start", "reset", "frozen", "retained")


def policy() -> dict[str, Any]:
    return {
        "schema": "agialpha/progressive-experience/v1",
        "parent": "e4c99ad326576d884811e6b8eabbc9258e61380c",
        "stages": list(STAGES),
        "arms": list(ARMS),
        "families": ["same-route", "withheld-stops"],
        "cases_per_regime_per_family": 2,
        "regimes": list(experiment.REGIMES),
        "repeats": 1,
        "training_seed": 2026102907,
        "fallback": "highs-ds-1",
        "quality_loss_allowed": 0,
        "minimum_lifecycle_cpu_reduction": "0.10",
        "wall_limit_seconds": 180,
        "error_allowance": 0,
        "confirmation": False,
        "new_confirmation_error_spent": 0,
        "previous_confirmation_accounting": "Preserved; not reset or reallocated by this engineering diagnostic.",
        "cohort": "Generated fixed passenger orders from one public eADARP instance; no admitted business cohort.",
        "operator_problem": "Recheck time windows, charging and battery reserves after dispatch inputs change.",
        "withheld_family": "Replace the internal charging stops 44->43 and 42->46; no such route enters training. Same instance and coefficient structure; changed route travel RHS, not an independent city or source family.",
        "reset": "Same historical solutions, rebuilt compiled memory for every target; no evaluation feedback.",
        "retained": "Append only newly verified training assets; keep them across stages and fresh targets.",
        "frozen": "Empty at stage0; first four training cases only thereafter, with all same-history costs charged.",
        "costs": "Cumulative training, asset construction, preparation, target compile/solve, output serialization, separate verification and representation storage. Money/human/maintenance unknown.",
        "cpu_rate_usd_per_hour": "0.10",
        "storage_rate_usd_per_gb_month": "0.03",
        "rate_basis": "Inherited illustrative SIM assumptions, not calibrated invoices or current quotes.",
        "frontier_control": "UNAVAILABLE: no authorized free frontier execution interface supplied; no paid calls.",
        "advancement": "No rejected output; stages8 and12 each >=10% lower lifecycle CPU than every declared control, on each family and overall. Complete monetary and commercial gates remain separate.",
        "retirement": "If advancement fails, retire promotion of this approach for this cohort; preserve code as an engineering tool. Do not enlarge this panel or tune against these exposed cases.",
        "demand": "UNKNOWN",
        "complete_cost_profit": None,
        "earned_funded_successor": "NOT_ESTABLISHED",
        "independence": "Read-only separate verifier process; shared author, host and libraries, no external certification.",
    }


def compact(target: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(target[key]) for key in ("id", "routes", "updates")}


def expand(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    return {**deepcopy(base), **deepcopy(patch)}


def withheld(target: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(target)
    result["routes"][0] = [43 if node == 44 else node for node in result["routes"][0]]
    result["routes"][1] = [46 if node == 42 else node for node in result["routes"][1]]
    eadarp.compile_model(result)
    return result


def append_assets(memory: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    new = solver.learn(history)
    body: dict[str, Any] = {key: memory[key] + new[key] for key in ("training", "assets", "failed_constructions")}
    body["schema"] = new["schema"]
    return {**body, "memory_hash": verifier.hash_value(body)}


def measured(function: Callable[[], Any]) -> tuple[Any, int]:
    start = time.process_time_ns()
    result = function()
    return result, time.process_time_ns() - start


def write(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(verifier.canonical(value) + b"\n")


def source_paths() -> list[Path]:
    runtime = ROOT / "alpha_factory_v1/core/runtime"
    return sorted(
        {
            *runtime.joinpath("retained_experience").glob("*.py"),
            *runtime.joinpath("structural_transfer").glob("*.py"),
            runtime / "compounding_discovery/programs.py",
            runtime / "store.py",
            runtime / "models.py",
            *runtime.joinpath("successor").glob("*.py"),
            ROOT / "contrib/invention_automation/readonly.py",
            Path(__file__),
            Path(__file__).with_name("progressive_check.py"),
        }
    )


def accounting_checkpoint(directory: Path, result: dict[str, Any]) -> None:
    from alpha_factory_v1.core.runtime.store import Journal
    from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, Charge, CostLedger
    from alpha_factory_v1.core.runtime.successor.trust import TrustRegistry

    # This separate private directory is never included in the public evidence package.
    journal = Journal.initialize(directory.parent / (directory.name + "-private-journal"))
    ledger = CostLedger(journal, TrustRegistry({}))
    mission = "progressive-experience-diagnostic"
    for kind, record in (
        (
            "opportunity",
            {"operator_problem": policy()["operator_problem"], "cohort": policy()["cohort"], "demand": "UNKNOWN"},
        ),
        ("invention", {"method": "unchanged verified LP asset append", "protocol_hash": verifier.hash_value(policy())}),
        ("result", {"decision": result["decision"], "complete_cost_profit": None, "scientific_confirmation": False}),
    ):
        with journal.transaction() as cx:
            journal.append(cx, mission + "/" + kind, record)
    inputs = [
        Charge.model_validate(
            {
                "activity_id": f"diagnostic/{category}",
                "mission_id": mission,
                "bucket": "C",
                "category": category,
                "accrued_micro_usd": None,
                "paid_micro_usd": 0,
                "basis": "unknown",
                "evidence_digest": verifier.hash_value(result),
                "note": "Unsigned diagnostic cost input. No accounting authority configured; no ledger charge or payment.",
            }
        ).model_dump()
        for category in sorted(CATEGORIES)
    ]
    write(
        directory / "accounting.json",
        {
            "journal_chain": journal.verify(),
            "ledger_report": ledger.report(mission),
            "unsigned_cost_inputs": inputs,
            "accounting_authority": "UNPROVISIONED",
            "grants_created": 0,
            "complete_monetary_cost": None,
            "scope": "Empty financial ledger is incomplete, not evidence of zero cost or profit.",
        },
    )


def run(directory: Path) -> dict[str, Any]:
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError("symlink output refused")
    directory.mkdir(exist_ok=False)
    started = time.monotonic()
    campaign_cpu = time.process_time_ns()
    base = verifier.read(ROOT / "contrib/compounding_discovery/base-target.json")
    spec = policy()
    write(directory / "base.json", base)
    write(directory / "protocol.json", spec)
    freeze: dict[str, Any] = {
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths()},
        "base_hash": verifier.hash_value(base),
        "policy_hash": verifier.hash_value(spec),
        "frozen_at_ns": time.time_ns(),
    }
    write(directory / "freeze.json", freeze)
    for name in freeze["sources"]:
        destination = directory / "source-snapshot" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    development = experiment.make_panel(base, spec["training_seed"], 3, "training")
    training = [development[r * 3 + i] for i in range(3) for r in range(4)]
    history: list[dict[str, Any]] = []
    memory, initial_learning = measured(lambda: solver.learn([]))
    states, actors = [], {}
    cumulative_training = 0
    cumulative_learning = initial_learning
    cumulative_preparation = 0
    training_cpu, setup_cpu, retained_bytes = {}, {}, {}
    for stage in STAGES:
        block = []
        for target in training[len(history) : stage]:

            def train(target: dict[str, Any] = target) -> dict[str, Any]:
                output = solver.solve(target, eadarp.compile_model(target), "highs-ds", True)
                if verifier.check_output(target, output).get("accepted") is not True:
                    raise ValueError("unqualified training output")
                return {"target": target, "output": output}

            row, cpu = measured(train)
            block.append(row)
            cumulative_training += cpu
        history.extend(block)
        memory, cpu = measured(lambda: append_assets(memory, block))
        cumulative_learning += cpu
        retained, prep = measured(lambda: solver.PreparedExperience(memory))
        cumulative_preparation += prep
        ordinary_memory, ordinary_learn = measured(lambda: solver.learn(history, points_only=True))
        ordinary, ordinary_prep = measured(lambda: solver.PreparedExperience(ordinary_memory))
        # Reconstructing the frozen baseline is charged, even though its asset state stays fixed.
        frozen_memory, frozen_learn = measured(lambda: solver.learn(history[:4]))
        frozen, frozen_prep = measured(lambda: solver.PreparedExperience(frozen_memory))
        warm, warm_cpu = measured(lambda: controls.WarmStart(history))
        templates = {}

        def make_templates() -> None:
            for row in history:
                for item in eadarp.compile_model(row["target"])["vehicles"]:
                    matrix, _, objective = solver.arrays(item)
                    templates[solver.signature(item)] = (matrix, objective)

        _, template_cpu = measured(make_templates)
        training_cpu[stage] = cumulative_training
        setup_cpu[stage] = {arm: 0 for arm in ARMS}
        setup_cpu[stage].update(
            {
                "retained": cumulative_training + cumulative_learning + cumulative_preparation,
                "ordinary-cache": cumulative_training + ordinary_learn + ordinary_prep,
                "frozen": cumulative_training + frozen_learn + frozen_prep,
                "reset": cumulative_training,
                "warm-start": cumulative_training + warm_cpu,
                "template": cumulative_training + template_cpu,
            }
        )
        history_size = len(verifier.canonical(history))
        retained_bytes[stage] = {arm: 0 for arm in experiment.METHODS}
        retained_bytes[stage].update(
            {
                "retained": history_size + len(verifier.canonical(memory)),
                "ordinary-cache": history_size + len(verifier.canonical(ordinary_memory)),
                "frozen": history_size + len(verifier.canonical(frozen_memory)),
                "reset": history_size,
                "warm-start": history_size
                + sum(len(b.row_status) + len(b.col_status) for _, b in warm.sessions.values()) * 8,
                "template": history_size + sum(a.nbytes + c.nbytes for a, c in templates.values()),
            }
        )
        states.append(
            {
                "stage": stage,
                "memory": memory,
                "ordinary": ordinary_memory,
                "frozen": frozen_memory,
                "setup_cpu_ns": setup_cpu[stage],
                "retained_bytes": retained_bytes[stage],
            }
        )
        actors[stage] = (retained, ordinary, frozen, warm, templates, list(history))
    write(directory / "history.json", [{"target": compact(r["target"]), "output": r["output"]} for r in history])
    write(directory / "states.json", states)
    write(
        directory / "candidate-freeze.json",
        {
            "history_sha256": experiment.file_hash(directory / "history.json"),
            "states_sha256": experiment.file_hash(directory / "states.json"),
            "frozen_at_ns": time.time_ns(),
        },
    )
    # No evaluation seed exists until every candidate, control and setup cost is frozen.
    seed = secrets.randbits(63)
    write(directory / "seed.json", {"seed": seed, "generated_at_ns": time.time_ns()})
    tasks = []
    for stage in STAGES:
        for family in spec["families"]:
            for target in experiment.make_panel(base, seed + stage, 2, f"evaluation-{stage}-{family}"):
                if family == "withheld-stops":
                    target = withheld(target)
                tasks.append({"stage": stage, "family": family, "target": compact(target)})
    write(directory / "tasks.json", tasks)
    rng = random.Random(seed)
    rng.shuffle(tasks)
    with (directory / "observations.jsonl").open("x") as stream, (directory / "costs.jsonl").open("x") as cost_stream:
        for item in tasks:
            stage = item["stage"]
            target = expand(base, item["target"])
            retained, ordinary, frozen, warm, templates, shared_history = actors[stage]
            order = list(ARMS)
            rng.shuffle(order)
            for arm in order:
                start = time.process_time_ns()
                model = eadarp.compile_model(target)
                row = {"stage": stage, "family": item["family"], "task_hash": verifier.hash_value(target), "arm": arm}
                try:
                    if arm in experiment.METHODS:
                        output = solver.solve(target, model, *experiment.METHODS[arm])
                    elif arm == "template":
                        output = solver.solve(target, model, "highs-ds", True, templates)
                    elif arm == "warm-start":
                        output = warm.run(target, model, "highs-ds", True)
                    else:
                        actor = {"retained": retained, "ordinary-cache": ordinary, "frozen": frozen}.get(arm)
                        if arm == "reset":
                            actor = solver.PreparedExperience(solver.learn(shared_history))
                        if actor is None:
                            raise ValueError("unsupported diagnostic arm")
                        output = actor.run(
                            target, model, method="highs-ds", presolve=True, ordinary_cache=arm == "ordinary-cache"
                        )
                    row["output"] = output
                except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, OSError, IndexError) as error:
                    row["failure"] = type(error).__name__ + ": " + str(error)
                row["execution_cpu_ns"] = time.process_time_ns() - start
                stream.write(verifier.canonical(row).decode() + "\n")
                stream.flush()
                cost = {key: row[key] for key in ("stage", "family", "task_hash", "arm")}
                cost["cpu_ns"] = time.process_time_ns() - start
                cost_stream.write(verifier.canonical(cost).decode() + "\n")
                cost_stream.flush()
                if time.monotonic() - started > spec["wall_limit_seconds"]:
                    raise TimeoutError("bounded campaign stopped; partial evidence retained")
    for state in states:
        if verifier.hash_value(actors[state["stage"]][0].memory) != verifier.hash_value(state["memory"]):
            raise ValueError("evaluation modified retained memory")
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    command = [
        sys.executable,
        "-B",
        "-m",
        "contrib.retained_experience.progressive_check",
        str(directory.resolve()),
        "--freeze-sha256",
        experiment.file_hash(directory / "freeze.json"),
    ]
    child = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env={
            "PATH": os.defpath,
            "PYTHONPATH": str(ROOT),
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
        },
    )
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    audit = json.loads(child.stdout)
    audit["process_cpu_ns"] = int((after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime) * 1e9)
    allocated = sum(v for key, v in audit.get("check_cpu_ns", {}).items() if key.split("/")[1] == "all")
    allocated += sum(audit.get("memory_check_cpu_ns", {}).values()) + sum(
        audit.get("history_check_cpu_ns", {}).values()
    )
    audit["unallocated_validation_cpu_ns"] = max(0, audit["process_cpu_ns"] - allocated)
    audit["unallocated_scaling"] = "Measured remainder; fixed/recurring scaling not established by one panel."
    write(directory / "verification.json", audit)
    if child.returncode or not audit.get("accepted"):
        raise ValueError("separate verification refused; original outputs retained")
    records = [json.loads(s) for s in (directory / "observations.jsonl").read_text().splitlines()]
    costs = {
        (r["stage"], r["task_hash"], r["arm"]): r["cpu_ns"]
        for r in (json.loads(s) for s in (directory / "costs.jsonl").read_text().splitlines())
    }
    panels = []
    for stage in STAGES:
        for family in (*spec["families"], "all"):
            selected = [r for r in records if r["stage"] == stage and (family == "all" or r["family"] == family)]
            rows = {}
            for arm in ARMS:
                delivered = [r for r in selected if r["arm"] == arm]
                key = f"{stage}/{family}/{arm}"
                # Entire stage setup is charged to each family comparison; never diluted across fresh tasks.
                lifecycle = setup_cpu[stage][arm] + sum(costs[stage, r["task_hash"], arm] for r in delivered)
                lifecycle += audit["check_cpu_ns"][key]
                if arm not in experiment.METHODS:
                    lifecycle += audit["memory_check_cpu_ns"][f"{stage}/{arm}"]
                    lifecycle += audit["history_check_cpu_ns"][str(stage)]
                    lifecycle += audit["unallocated_validation_cpu_ns"]
                rows[arm] = {
                    "lifecycle_cpu_ns": lifecycle,
                    "deployment_cpu_ns": sum(r["execution_cpu_ns"] for r in delivered),
                    "setup_cpu_ns": setup_cpu[stage][arm],
                    "solver_free_tasks": sum(r["output"].get("solver_calls") == 0 for r in delivered),
                    "retained_representation_bytes": retained_bytes[stage][arm],
                    "modeled_cpu_usd": str(Fraction(lifecycle, 10**9 * 3600) * Fraction(spec["cpu_rate_usd_per_hour"])),
                    "modeled_storage_usd": str(
                        Fraction(retained_bytes[stage][arm], 10**9) * Fraction(spec["storage_rate_usd_per_gb_month"])
                    ),
                    "other_complete_costs_usd": None,
                }
            best = min((a for a in ARMS if a != "retained"), key=lambda a: rows[a]["lifecycle_cpu_ns"])
            reduction = 1 - rows["retained"]["lifecycle_cpu_ns"] / rows[best]["lifecycle_cpu_ns"]
            panels.append(
                {
                    "stage": stage,
                    "family": family,
                    "tasks": len(selected) // len(ARMS),
                    "arms": rows,
                    "best_control": best,
                    "retained_lifecycle_reduction": reduction,
                }
            )
    advance = all(p["retained_lifecycle_reduction"] >= 0.10 for p in panels if p["stage"] in (8, 12))
    result = {
        "schema": spec["schema"],
        "decision": "ADVANCE_ENGINEERING_ONLY" if advance else "RETIRE_COHORT_PROMOTION",
        "accepted_outputs": audit["outputs"],
        "unique_tasks": len(tasks),
        "panels": panels,
        "complete_money_cost": None,
        "profit": None,
        "demand": "UNKNOWN",
        "confirmation": False,
        "frontier_control": spec["frontier_control"],
        "state_unchanged": True,
        "verifier_process_cpu_ns": audit["process_cpu_ns"],
        "wall_seconds": time.monotonic() - started,
        "campaign_cpu_ns": time.process_time_ns() - campaign_cpu,
        "next_decision": (
            spec["retirement"]
            if not advance
            else "Obtain independent cohort cost/demand evidence before commercial advancement."
        ),
    }
    accounting_checkpoint(directory, result)
    write(directory / "RESULTS.json", result)
    seal = {p.name: experiment.file_hash(p) for p in sorted(directory.iterdir()) if p.is_file()}
    write(directory / "seal.json", seal)
    return {
        "decision": result["decision"],
        "outputs": audit["outputs"],
        "unique_tasks": len(tasks),
        "seal_sha256": experiment.file_hash(directory / "seal.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output), allow_nan=False))


if __name__ == "__main__":
    main()
