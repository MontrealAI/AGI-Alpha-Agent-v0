# SPDX-License-Identifier: Apache-2.0
"""Ordinary exact real-root analysis, credited to SymPy."""

from __future__ import annotations

import time
from fractions import Fraction
from typing import Any

import sympy as sp

from alpha_factory_v1.core.runtime.claim_probe.contracts import RESULT_SCHEMA, digest, validate


def ordinary_library(task: dict[str, Any]) -> dict[str, Any]:
    """Isolate all real roots exactly; sign samples between isolating intervals."""
    c, a, b = validate(task)
    started = time.monotonic()
    x = sp.Symbol("x")
    polynomial = sp.Poly(sum(sp.Rational(k.numerator, k.denominator) * x**i for i, k in enumerate(c)), x)
    intervals = polynomial.intervals(eps=sp.Rational(1, 10**10)) if not polynomial.is_zero else []
    points = {a, b, (a + b) / 2}
    for (left, right), _multiplicity in intervals:
        for endpoint in [left, right]:
            point = Fraction(int(endpoint.p), int(endpoint.q))
            if a <= point <= b:
                points.add(point)
    ordered = sorted(points)
    points.update((left + right) / 2 for left, right in zip(ordered, ordered[1:]))
    witness = None
    for point in sorted(points):
        y = polynomial.eval(sp.Rational(point.numerator, point.denominator))
        if y < 0:
            witness = {"x": str(point), "value": str(Fraction(int(y.p), int(y.q)))}
            break
    elapsed = time.monotonic() - started
    status = "REFUTED" if witness else "PROVED"
    if elapsed > task["limits"]["seconds"]:
        status, witness = "UNKNOWN", None
    return {
        "schema": RESULT_SCHEMA,
        "taskHash": digest(task),
        "status": status,
        "method": "sympy-exact-roots",
        "witness": witness,
        "cover": [],
        "reason": "complete" if status != "UNKNOWN" else "time-limit",
        "visited": len(points),
        "elapsedSeconds": elapsed,
        "physicalQualified": False,
    }
