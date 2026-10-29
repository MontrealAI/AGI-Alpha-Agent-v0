# SPDX-License-Identifier: Apache-2.0
"""New funded multi-affine construction: exact extrema on a continuous box."""

from __future__ import annotations

import time
from fractions import Fraction
from typing import Any

from .contracts import canonical, digest, rational


def validate_joint(task: Any) -> tuple[list[Fraction], list[tuple[Fraction, Fraction]]]:
    """Accept only an explicit bounded multi-affine mathematical claim."""
    fields = {"schema", "id", "variables", "coefficients", "domain", "sources", "claim", "scope"}
    if not isinstance(task, dict) or set(task) != fields or task["schema"] != "agialpha/joint-affine-claim/v1":
        raise ValueError("joint claim schema")
    variables = task["variables"]
    if not isinstance(variables, list) or not 2 <= len(variables) <= 8:
        raise ValueError("two to eight variables required")
    if any(not isinstance(x, str) or not x.isidentifier() or len(x) > 40 for x in variables):
        raise ValueError("variable identity")
    if len(set(variables)) != len(variables):
        raise ValueError("duplicate variable")
    if not isinstance(task["id"], str) or not 1 <= len(task["id"]) <= 100:
        raise ValueError("joint task identity")
    if task["claim"] != "nonnegative-throughout-box" or task["scope"] != "declared-mathematical-model-only":
        raise ValueError("joint scope")
    if not isinstance(task["coefficients"], list) or len(task["coefficients"]) != 2 ** len(variables):
        raise ValueError("one coefficient for every square-free monomial")
    c = [rational(x) for x in task["coefficients"]]
    if not isinstance(task["domain"], list) or len(task["domain"]) != len(variables):
        raise ValueError("joint domain")
    bounds = []
    for pair in task["domain"]:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("box interval")
        lo, hi = map(rational, pair)
        if not lo < hi or max(abs(lo), abs(hi)) > 10**6:
            raise ValueError("box interval order")
        bounds.append((lo, hi))
    if not isinstance(task["sources"], list) or not 1 <= len(task["sources"]) <= 8:
        raise ValueError("joint source provenance")
    if any(not isinstance(x, str) or len(x) > 1000 or not x.startswith("https://") for x in task["sources"]):
        raise ValueError("joint source reference")
    if len(canonical(task)) > 64000:
        raise ValueError("joint input cap")
    return c, bounds


def construct(task: dict[str, Any]) -> dict[str, Any]:
    """Construct all exact corner values by tensor Horner evaluation."""
    coefficients, bounds = validate_joint(task)
    started = time.monotonic()
    values = coefficients[:]
    for axis, (lo, hi) in enumerate(bounds):
        bit = 1 << axis
        for index in range(len(values)):
            if index & bit:
                continue
            left, right = values[index], values[index | bit]
            values[index] = left + right * lo
            values[index | bit] = left + right * hi
    smallest = min(values)
    corner = values.index(smallest)
    witness = [str(hi if corner & (1 << j) else lo) for j, (lo, hi) in enumerate(bounds)]
    return {
        "schema": "agialpha/joint-affine-result/v1",
        "taskHash": digest(task),
        "status": "PROVED" if smallest >= 0 else "REFUTED",
        "minimum": str(smallest),
        "minimizer": witness,
        "cornerValues": list(map(str, values)),
        "elapsedSeconds": time.monotonic() - started,
        "physicalQualified": False,
    }


def construct_and_check(task: dict[str, Any]) -> dict[str, Any]:
    """Construct a real result and subject it to a separately implemented check."""
    from .joint_check import check_joint

    artifact = construct(task)
    validation = check_joint(task, artifact)
    if not validation["accepted"]:
        raise ValueError("joint independent check failed")
    return {
        "artifact": artifact,
        "verification": validation,
        "scope": "Exact multi-affine mathematical model; external application unqualified",
    }
