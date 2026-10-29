# SPDX-License-Identifier: Apache-2.0
"""Independent exhaustive checker: never calls the construction algorithm."""

from __future__ import annotations

import time
from itertools import combinations
from fractions import Fraction
from typing import Any

from .instrument import digest, validate


def reference(task: dict[str, Any]) -> dict[str, Any]:
    validate(task)
    started = time.monotonic()
    examined = 0
    experiments = task["experiments"]
    models = task["models"]
    required = [(a, b) for a in range(len(models)) for b in range(a) if models[a]["decision"] != models[b]["decision"]]

    def distinguishes(selected: tuple[int, ...], a: int, b: int) -> bool:
        for idx in selected:
            pa = list(map(Fraction, experiments[idx]["prediction"][models[a]["id"]]))
            pb = list(map(Fraction, experiments[idx]["prediction"][models[b]["id"]]))
            if max(pa[0], pb[0]) > min(pa[1], pb[1]):
                return True
        return False

    best: tuple[int, tuple[int, ...]] | None = None
    for size in range(len(experiments) + 1):
        for selected in combinations(range(len(experiments)), size):
            examined += 1
            if examined % 128 == 0 and time.monotonic() - started > 10:
                raise TimeoutError("bounded exhaustive check incomplete")
            cost = sum(experiments[x]["cost"] for x in selected)
            if cost > task["budget"] or best is not None and (cost, selected) >= best:
                continue
            if all(distinguishes(selected, a, b) for a, b in required):
                best = (cost, selected)
    return {
        "status": "GO" if best else "HOLD",
        "cost": best[0] if best else None,
        "selected": [experiments[i]["id"] for i in best[1]] if best else [],
    }


def check(task: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(result, dict)
        or result.get("schema") != "agialpha/experiment-plan/v1"
        or result.get("physicalQualified") is not False
        or result.get("claimScope") != "finite declared interval model only"
    ):
        return {"accepted": False, "reason": "CLAIM_SCOPE"}
    try:
        truth = reference(task)
    except TimeoutError:
        return {"accepted": False, "reason": "CHECK_INCOMPLETE"}
    if result.get("taskHash") != digest(task) or result.get("taskId") != task["id"]:
        return {"accepted": False, "reason": "SOURCE_BINDING"}
    if result.get("status") == "INCONCLUSIVE":
        return {"accepted": False, "reason": "INCOMPLETE", "reference": truth}
    if any(result.get(key) != truth[key] for key in ("status", "cost", "selected")):
        return {"accepted": False, "reason": "OPTIMALITY_OR_DECISION", "reference": truth}
    wanted = {(a["id"], b["id"]) for a, b in combinations(task["models"], 2) if a["decision"] != b["decision"]}
    seen = set()
    exps = {e["id"]: e for e in task["experiments"]}
    unreachable = []
    for a, b in combinations(task["models"], 2):
        if a["decision"] == b["decision"]:
            continue
        separated = False
        for experiment in task["experiments"]:
            left = list(map(Fraction, experiment["prediction"][a["id"]]))
            right = list(map(Fraction, experiment["prediction"][b["id"]]))
            separated |= max(left[0], right[0]) > min(left[1], right[1])
        if not separated:
            unreachable.append([a["id"], b["id"]])
    if result.get("unseparable") != unreachable:
        return {"accepted": False, "reason": "FALSE_IMPOSSIBILITY_CERTIFICATE"}
    if not isinstance(result.get("witnesses"), list):
        return {"accepted": False, "reason": "WITNESS_SCHEMA"}
    for witness in result["witnesses"]:
        if (
            not isinstance(witness, dict)
            or set(witness) != {"models", "experiments"}
            or not isinstance(witness["models"], list)
            or len(witness["models"]) != 2
            or not all(isinstance(x, str) for x in witness["models"])
            or not isinstance(witness["experiments"], list)
            or not all(isinstance(x, str) for x in witness["experiments"])
        ):
            return {"accepted": False, "reason": "WITNESS_SCHEMA"}
        pair = tuple(witness.get("models", []))
        if pair in seen:
            return {"accepted": False, "reason": "DUPLICATE_WITNESS"}
        seen.add(pair)
        if pair not in wanted or any(e not in result["selected"] for e in witness["experiments"]):
            return {"accepted": False, "reason": "WITNESS_BINDING"}
        actual = []
        for e in result["selected"]:
            a, b = [list(map(Fraction, exps[e]["prediction"][x])) for x in pair]
            if max(a[0], b[0]) > min(a[1], b[1]):
                actual.append(e)
        if actual != witness["experiments"] or result["status"] == "GO" and not actual:
            return {"accepted": False, "reason": "FALSE_WITNESS"}
    if seen != wanted:
        return {"accepted": False, "reason": "INCOMPLETE_WITNESSES"}
    return {"accepted": True, "reason": "EXHAUSTIVE_FINITE_CHECK", "reference": truth, "physicalQualified": False}
