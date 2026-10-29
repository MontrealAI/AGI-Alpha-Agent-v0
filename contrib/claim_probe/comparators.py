# SPDX-License-Identifier: Apache-2.0
"""Strong ordinary-library exact real-root analysis and grid ablation."""

from __future__ import annotations

from fractions import Fraction
from typing import Any


from alpha_factory_v1.core.runtime.claim_probe.contracts import RESULT_SCHEMA, digest, validate


from alpha_factory_v1.core.runtime.claim_probe.symbolic import ordinary_library


def grid_ablation(task: dict[str, Any]) -> dict[str, Any]:
    """A diagnostic grid never claims universal safety from finite samples."""
    c, a, b = validate(task)
    points = [a + (b - a) * Fraction(i, 100) for i in range(101)]
    for point in points:
        observed = sum((k * point**i for i, k in enumerate(c)), Fraction(0))
        if observed < 0:
            return {"status": "REFUTED", "x": str(point), "observed": str(observed), "points": 101}
    return {"status": "NO_SAMPLED_VIOLATION", "universalClaimQualified": False, "points": 101}
