# SPDX-License-Identifier: Apache-2.0
"""Independent direct-monomial corner verification and optional CLI."""

from __future__ import annotations

from fractions import Fraction as Q
import itertools
import json
from pathlib import Path
import sys
from typing import Any

from .contracts import digest, read
from .joint import validate_joint


def reference(task: dict[str, Any]) -> tuple[list[Q], list[list[Q]]]:
    """Expand monomials directly, independently of tensor Horner evaluation."""
    coefficients, bounds = validate_joint(task)
    dimensions = len(bounds)
    values: list[Q] = []
    points: list[list[Q]] = []
    for reversed_bits in itertools.product([0, 1], repeat=dimensions):
        bits = list(reversed(reversed_bits))
        point = [bounds[j][bits[j]] for j in range(dimensions)]
        result = Q(0)
        for mask, coefficient in enumerate(coefficients):
            term = coefficient
            for axis, coordinate in enumerate(point):
                if mask & (1 << axis):
                    term *= coordinate
            result += term
        points.append(point)
        values.append(result)
    return values, points


def check_joint(task: dict[str, Any], result: Any) -> dict[str, Any]:
    """Verify the full continuous-box conclusion using the multi-affine theorem."""
    try:
        fields = {
            "schema",
            "taskHash",
            "status",
            "minimum",
            "minimizer",
            "cornerValues",
            "elapsedSeconds",
            "physicalQualified",
        }
        if (
            not isinstance(result, dict)
            or set(result) != fields
            or result["schema"] != "agialpha/joint-affine-result/v1"
        ):
            raise ValueError("joint artifact schema")
        if result["taskHash"] != digest(task) or result["physicalQualified"] is not False:
            raise ValueError("joint source or scope binding")
        if type(result["elapsedSeconds"]) not in {int, float} or not 0 <= result["elapsedSeconds"] < 60:
            raise ValueError("invalid joint resource record")
        values, points = reference(task)
        minimum = min(values)
        point = points[values.index(minimum)]
        if result["cornerValues"] != list(map(str, values)) or result["minimum"] != str(minimum):
            raise ValueError("corner evidence changed")
        if result["minimizer"] != list(map(str, point)):
            raise ValueError("minimizing intervention changed")
        if result["status"] != ("PROVED" if minimum >= 0 else "REFUTED"):
            raise ValueError("wrong joint conclusion")
        return {
            "accepted": True,
            "decisive": True,
            "method": "independent exact monomial expansion at all corners",
            "theoremScope": "A function affine separately in each variable is a convex combination of its box-corner values",
        }
    except (ValueError, TypeError, IndexError, KeyError, ZeroDivisionError) as error:
        return {"accepted": False, "decisive": False, "reason": str(error)}


if __name__ == "__main__":
    document = read(Path(sys.argv[2]))
    verdict = check_joint(read(Path(sys.argv[1])), document.get("artifact", document))
    print(json.dumps(verdict))
    sys.exit(0 if verdict["accepted"] else 1)
