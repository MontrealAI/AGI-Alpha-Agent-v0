# SPDX-License-Identifier: Apache-2.0
"""Compile an exact minimum-cost experiment cover with auditable witnesses."""

from __future__ import annotations

import hashlib
import json
import re
import time
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from typing import Any

MAX_BYTES = 1_000_000
MAX_MODELS = 16
MAX_EXPERIMENTS = 18
SCHEMA = "agialpha/decision-experiment/v1"


def rational(value: str) -> Fraction:
    if not isinstance(value, str) or not re.fullmatch(r"[+-]?[0-9]{1,20}(?:\.[0-9]{1,16}|/[0-9]{1,20})?", value):
        raise ValueError("bounded rational syntax")
    return Fraction(value)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("regular bounded input required")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, val in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = val
        return result

    value = json.loads(
        path.read_bytes(),
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
    )
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def write_new(path: Path, value: Any) -> None:
    with path.open("xb") as file:
        file.write(canonical(value) + b"\n")


def validate(task: dict[str, Any]) -> None:
    if (
        set(task) != {"schema", "id", "source", "models", "experiments", "budget", "assumptions"}
        or task["schema"] != SCHEMA
    ):
        raise ValueError("schema or fields")
    if not isinstance(task["id"], str) or not task["id"] or len(canonical(task)) > MAX_BYTES:
        raise ValueError("identity or size")
    if type(task["budget"]) is not int or not 0 <= task["budget"] <= 10**9:
        raise ValueError("budget")
    if not isinstance(task["source"], str) or not task["source"] or not isinstance(task["assumptions"], list):
        raise ValueError("source and assumptions required")
    models, experiments = task["models"], task["experiments"]
    if not 2 <= len(models) <= MAX_MODELS or not 1 <= len(experiments) <= MAX_EXPERIMENTS:
        raise ValueError("bounded dimensions")
    for model in models:
        if set(model) != {"id", "decision"} or not all(isinstance(v, str) and v for v in model.values()):
            raise ValueError("model")
    names = [m["id"] for m in models]
    if len(set(names)) != len(names) or len({e["id"] for e in experiments}) != len(experiments):
        raise ValueError("duplicate identity")
    for experiment in experiments:
        if (
            set(experiment) != {"id", "cost", "prediction", "action"}
            or not isinstance(experiment["id"], str)
            or not experiment["id"]
        ):
            raise ValueError("experiment fields")
        if type(experiment["cost"]) is not int or not 0 < experiment["cost"] <= 10**9:
            raise ValueError("experiment cost")
        if not isinstance(experiment["action"], dict) or set(experiment["prediction"]) != set(names):
            raise ValueError("prediction binding")
        for interval in experiment["prediction"].values():
            if (
                not isinstance(interval, list)
                or len(interval) != 2
                or not all(isinstance(x, str) and len(x) <= 64 for x in interval)
            ):
                raise ValueError("exact rational interval required")
            if rational(interval[0]) > rational(interval[1]):
                raise ValueError("reversed interval")


def compile_plan(task: dict[str, Any], max_states: int = 100_000, timeout: float = 10) -> dict[str, Any]:
    validate(task)
    if type(max_states) is not int or max_states < 1 or timeout <= 0:
        raise ValueError("resource limit")
    start = time.monotonic()
    models = task["models"]
    pairs = [(a["id"], b["id"]) for a, b in combinations(models, 2) if a["decision"] != b["decision"]]
    masks = []
    for exp in task["experiments"]:
        mask = 0
        for idx, (a, b) in enumerate(pairs):
            al, ah = map(rational, exp["prediction"][a])
            bl, bh = map(rational, exp["prediction"][b])
            if ah < bl or bh < al:
                mask |= 1 << idx
        masks.append(mask)
    target = (1 << len(pairs)) - 1
    states: dict[int, tuple[int, tuple[int, ...]]] = {0: (0, ())}
    steps = 0
    exhausted = False
    for idx, mask in enumerate(masks):
        for old, (cost, prior_chosen) in list(states.items()):
            steps += 1
            if steps > max_states or time.monotonic() - start > timeout:
                exhausted = True
                break
            nc = cost + task["experiments"][idx]["cost"]
            if nc > task["budget"]:
                continue
            nm = old | mask
            candidate = (nc, prior_chosen + (idx,))
            if nm not in states or candidate < states[nm]:
                states[nm] = candidate
        if exhausted:
            break
    union = 0
    for mask in masks:
        union |= mask
    unreachable = [list(pair) for idx, pair in enumerate(pairs) if not union & (1 << idx)]
    solution = states.get(target)
    status = "INCONCLUSIVE" if exhausted else "GO" if solution else "HOLD"
    chosen = list(solution[1]) if solution and not exhausted else []
    witnesses = []
    for idx, pair in enumerate(pairs):
        separating = [task["experiments"][e]["id"] for e in chosen if masks[e] & (1 << idx)]
        witnesses.append({"models": list(pair), "experiments": separating})
    return {
        "schema": "agialpha/experiment-plan/v1",
        "instrumentVersion": "0.1.0",
        "taskHash": digest(task),
        "taskId": task["id"],
        "status": status,
        "selected": [task["experiments"][i]["id"] for i in chosen],
        "cost": solution[0] if solution is not None and not exhausted else None,
        "witnesses": witnesses,
        "unseparable": unreachable,
        "statesVisited": steps,
        "elapsedSeconds": time.monotonic() - start,
        "claimScope": "finite declared interval model only",
        "physicalQualified": False,
    }


def update_belief(task: dict[str, Any], observations: dict[str, str]) -> dict[str, Any]:
    validate(task)
    exps = {e["id"]: e for e in task["experiments"]}
    if not observations or any(k not in exps for k in observations):
        raise ValueError("observation identity")
    retained = []
    for model in task["models"]:
        if all(
            rational(exps[e]["prediction"][model["id"]][0])
            <= rational(v)
            <= rational(exps[e]["prediction"][model["id"]][1])
            for e, v in observations.items()
        ):
            retained.append(model)
    decisions = sorted({m["decision"] for m in retained})
    return {
        "taskHash": digest(task),
        "observations": observations,
        "retainedModels": [m["id"] for m in retained],
        "decision": decisions[0] if len(decisions) == 1 else None,
        "status": "MODEL_MISMATCH" if not retained else "DECISIVE" if len(decisions) == 1 else "AMBIGUOUS",
        "physicalQualified": False,
    }
