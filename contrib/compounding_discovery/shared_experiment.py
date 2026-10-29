# SPDX-License-Identifier: Apache-2.0
"""Fresh scope extension checks; no attribution to transfer or earned succession."""

from __future__ import annotations
import argparse, copy, gzip, hashlib, json, random, secrets, time
from fractions import Fraction
from pathlib import Path
from typing import Any
from alpha_factory_v1.core.runtime.compounding_discovery import engine, programs, shared_charger
from alpha_factory_v1.core.runtime.structural_transfer import eadarp, eadarp_check


def digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def write(p: Path, v: Any) -> None:
    raw = json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    with p.open("xb") as f:
        f.write(gzip.compress(raw, mtime=0) if p.suffix == ".gz" else raw)


def run(output: Path, count: int = 32) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    basepath = Path(__file__).with_name("base-target.json")
    base = json.loads(basepath.read_text())
    source = [
        Path(__file__),
        basepath,
        Path(shared_charger.__file__),
        Path(eadarp.__file__),
        Path(eadarp_check.__file__),
        Path(programs.__file__),
        Path(engine.__file__),
    ]
    freeze = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
    write(
        output / "freeze.json",
        {
            "sources": freeze,
            "n": count,
            "budget": {"cpu_seconds": 30, "solver_calls": 16, "operations": 100},
            "funding": "seed",
            "comparison": "per-vehicle relaxation vs conventional joint MILP; this is new model scope, not an A/S/C or algorithm superiority test",
            "outcome": "shared-capacity independently accepted feasible certificate",
            "novelty": "new repository capability; established specialist scheduling mathematics",
        },
    )
    seed = secrets.randbits(48)
    write(output / "seed.json", {"seed": seed})
    rng = random.Random(seed)
    rows = []
    for i in range(count):
        task = copy.deepcopy(base)
        task["id"] = f"fresh-shared-{i}-{seed:x}"
        task["routes"][1] = [44 if n == 42 else n for n in task["routes"][1]]
        task["updates"].update(
            {
                "charge_multiplier": f"{rng.uniform(1.5, 2.5):.8f}",
                "window_scale": f"{rng.uniform(0.85, 1.3):.8f}",
                "travel_multiplier": f"{rng.uniform(0.95, 1.08):.8f}",
                "consumption_multiplier": f"{rng.uniform(0.9, 1.1):.8f}",
            }
        )
        wrapper = shared_charger.wrap_target(task, task_id=task["id"])
        order = ["relaxation", "joint"]
        rng.shuffle(order)
        out = {}
        for arm in order:
            start = time.process_time_ns()
            if arm == "joint":
                artifact = shared_charger.solve(wrapper)
                verdict = shared_charger.check(wrapper, artifact)
            else:
                meter = engine.Meter({"cpu_seconds": 30, "solver_calls": 16, "operations": 100})
                ordinary = programs.solve_program(task, eadarp.compile_model(task), engine.DEFAULT_PROGRAM, meter)
                artifact = {
                    "schema": shared_charger.RESULT_SCHEMA,
                    "task_hash": shared_charger.digest(wrapper),
                    "status": ordinary["status"],
                    "base_artifact": ordinary,
                    "resources": {"solver_calls": meter.calls},
                    "scope": shared_charger.SCOPE,
                }
                verdict = shared_charger.check(wrapper, artifact)
            cpu = Fraction(time.process_time_ns() - start, 10**9)
            out[arm] = {
                "artifact": artifact,
                "acceptance": verdict,
                "cpu_seconds": str(cpu),
                "cost_usd": str(cpu * Fraction(engine.CPU_RATE)),
                "cpu_cap_satisfied": cpu <= 30,
            }
        row = {"id": task["id"], "request": wrapper, "outcomes": out}
        write(output / f"case-{i:03d}.json.gz", row)
        rows.append(row)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in freeze.items()):
        raise ValueError("source changed")
    summary = {
        "n": count,
        "joint_accepted": sum(r["outcomes"]["joint"]["acceptance"]["accepted"] for r in rows),
        "relaxation_accepted": sum(r["outcomes"]["relaxation"]["acceptance"]["accepted"] for r in rows),
        "new_scope_accepted_only_with_joint_construction": sum(
            r["outcomes"]["joint"]["acceptance"]["accepted"]
            and not r["outcomes"]["relaxation"]["acceptance"]["accepted"]
            for r in rows
        ),
        "unresolved_joint": sum(r["outcomes"]["joint"]["artifact"]["status"] == "UNRESOLVED" for r in rows),
        "all_cpu_caps_satisfied": all(x["cpu_cap_satisfied"] for r in rows for x in r["outcomes"].values()),
        "measured_execution_equivalent_usd": str(
            sum((Fraction(x["cost_usd"]) for r in rows for x in r["outcomes"].values()), Fraction())
        ),
        "source_unchanged": True,
        "seed_funded": True,
        "earned_successor": False,
        "physical_or_customer_validation": False,
        "scope": "fresh simulated operator updates on known public raw data and modified fixed orders; no new city or field data; relaxed control does not model shared ports; joint MILP is conventional specialist mathematics",
    }
    write(output / "summary.json", summary)
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--count", type=int, default=32)
    a = p.parse_args()
    if not 1 <= a.count <= 100:
        p.error("count must be1to100")
    print(json.dumps(run(a.output, a.count), indent=2))
