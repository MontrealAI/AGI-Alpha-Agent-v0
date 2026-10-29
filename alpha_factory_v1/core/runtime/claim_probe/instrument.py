# SPDX-License-Identifier: Apache-2.0
"""Bounded exact Bernstein subdivision with concrete falsifying interventions."""

from __future__ import annotations

import heapq
import math
import time
from fractions import Fraction
from typing import Any

from .contracts import RESULT_SCHEMA, digest, validate


def evaluate(c: list[Fraction], x: Fraction) -> Fraction:
    """Evaluate the declared model with exact Horner arithmetic."""
    out = Fraction(0)
    for coefficient in reversed(c):
        out = out * x + coefficient
    return out


def bernstein(c: list[Fraction], a: Fraction, b: Fraction) -> list[Fraction]:
    """Convert the restriction to exact Bernstein control ordinates."""
    n = len(c) - 1
    power = [
        sum((c[i] * math.comb(i, k) * a ** (i - k) * (b - a) ** k for i in range(k, n + 1)), Fraction(0))
        for k in range(n + 1)
    ]
    return [
        sum((power[k] * Fraction(math.comb(j, k), math.comb(n, k)) for k in range(j + 1)), Fraction(0))
        for j in range(n + 1)
    ]


def probe(task: dict[str, Any]) -> dict[str, Any]:
    """Return an exact proof, an executed counterexample, or an explicit UNKNOWN."""
    c, a, b = validate(task)
    started = time.monotonic()
    limits = task["limits"]
    pending: list[tuple[Fraction, Fraction, Fraction, int]] = []
    proved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    visited = 0
    witness: dict[str, str] | None = None
    heapq.heappush(pending, (min(bernstein(c, a, b)), a, b, 0))
    reason = "complete"
    while pending:
        if visited >= limits["cells"] or time.monotonic() - started > limits["seconds"]:
            reason = "resource-limit"
            break
        _, lo, hi, depth = heapq.heappop(pending)
        visited += 1
        for x in [lo, (lo + hi) / 2, hi]:
            value = evaluate(c, x)
            if value < 0:
                witness = {"x": str(x), "value": str(value)}
                break
        if witness is not None:
            break
        bounds = bernstein(c, lo, hi)
        if min(bounds) >= 0:
            proved.append({"interval": [str(lo), str(hi)], "lowerBound": str(min(bounds))})
        elif depth >= limits["depth"]:
            unresolved.append({"interval": [str(lo), str(hi)], "reason": "depth-limit"})
            reason = "resource-limit"
        else:
            middle = (lo + hi) / 2
            for left, right in [(lo, middle), (middle, hi)]:
                heapq.heappush(pending, (min(bernstein(c, left, right)), left, right, depth + 1))
    status = "REFUTED" if witness else "PROVED" if not pending and not unresolved else "UNKNOWN"
    return {
        "schema": RESULT_SCHEMA,
        "taskHash": digest(task),
        "status": status,
        "method": "exact-bernstein",
        "witness": witness,
        "cover": proved if status == "PROVED" else [],
        "reason": reason,
        "visited": visited,
        "elapsedSeconds": time.monotonic() - started,
        "physicalQualified": False,
    }
