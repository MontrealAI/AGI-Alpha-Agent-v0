# SPDX-License-Identifier: Apache-2.0
"""Independent rational verifier and Sturm sign reference; no solver imports."""

from __future__ import annotations

from fractions import Fraction as Q
from math import comb
import re
from typing import Any

from .contracts import RESULT_SCHEMA, digest, rational, validate


def proof_rational(raw: Any) -> Q:
    """Bound certificate arithmetic before parsing, including rational witnesses."""
    if not isinstance(raw, str) or len(raw) > 1024 or not re.fullmatch(r"-?[0-9]+(?:/[1-9][0-9]*)?", raw):
        raise ValueError("bounded certificate rational")
    return Q(raw)


def trim(p: list[Q]) -> list[Q]:
    """Canonicalize a rational polynomial."""
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p


def value(p: list[Q], x: Q) -> Q:
    """Use a power sum independent of the solver's Horner evaluation."""
    return sum((coefficient * x**i for i, coefficient in enumerate(p)), Q(0))


def divide(p: list[Q], q: list[Q]) -> tuple[list[Q], list[Q]]:
    """Divide exactly over the rationals."""
    p, q = trim(list(p)), trim(list(q))
    if q == [0]:
        raise ValueError("zero divisor")
    out = [Q(0)] * max(1, len(p) - len(q) + 1)
    while p != [0] and len(p) >= len(q):
        d, k = len(p) - len(q), p[-1] / q[-1]
        out[d] = k
        for i, coefficient in enumerate(q):
            p[d + i] -= k * coefficient
        trim(p)
    return trim(out), p


def gcd(p: list[Q], q: list[Q]) -> list[Q]:
    """Return the monic polynomial gcd."""
    p, q = trim(p[:]), trim(q[:])
    while q != [0]:
        p, q = q, divide(p, q)[1]
    return [x / p[-1] for x in p] if p != [0] else p


def multiply(p: list[Q], q: list[Q]) -> list[Q]:
    """Multiply exact coefficient arrays."""
    out = [Q(0)] * (len(p) + len(q) - 1)
    for i, x in enumerate(p):
        for j, y in enumerate(q):
            out[i + j] += x * y
    return trim(out)


def odd_part(p: list[Q]) -> list[Q]:
    """Yun square-free decomposition, retaining odd multiplicities only."""
    derivative = trim([i * p[i] for i in range(1, len(p))] or [Q(0)])
    g = gcd(p, derivative)
    w = divide(p, g)[0]
    odd = [Q(1)]
    exponent = 1
    while len(w) > 1:
        y = gcd(w, g)
        z = divide(w, y)[0]
        if exponent % 2:
            odd = multiply(odd, z)
        w, g = y, divide(g, y)[0]
        exponent += 1
    return odd


def interior_roots(p: list[Q], a: Q, b: Q) -> int:
    """Count distinct interior roots by exact Sturm variation."""
    p = trim(p[:])
    for endpoint in [a, b]:
        if len(p) > 1 and value(p, endpoint) == 0:
            p = divide(p, [-endpoint, Q(1)])[0]
    if len(p) == 1:
        return 0
    seq = [p, trim([i * p[i] for i in range(1, len(p))])]
    while seq[-1] != [0]:
        remainder = divide(seq[-2], seq[-1])[1]
        if remainder == [0]:
            break
        seq.append([-x for x in remainder])

    def variation(x: Q) -> int:
        signs = [1 if v > 0 else -1 for item in seq if (v := value(item, x)) != 0]
        return sum(left != right for left, right in zip(signs, signs[1:]))

    return variation(a) - variation(b)


def globally_nonnegative(p: list[Q], a: Q, b: Q) -> bool:
    """Independently decide the bounded-degree exact mathematical statement."""
    if p == [0]:
        return True
    if interior_roots(odd_part(p), a, b) != 0:
        return False
    for i in range(len(p) + 2):
        observed = value(p, a + (b - a) * Q(i, len(p) + 1))
        if observed:
            return observed > 0
    raise ValueError("nonzero polynomial has too many roots")


def check(task: dict[str, Any], result: Any) -> dict[str, Any]:
    """Check every claim against original inputs, with no trusted success flag."""
    try:
        p, a, b = validate(task)
        fields = {
            "schema",
            "taskHash",
            "status",
            "method",
            "witness",
            "cover",
            "reason",
            "visited",
            "elapsedSeconds",
            "physicalQualified",
        }
        if not isinstance(result, dict) or set(result) != fields or result["schema"] != RESULT_SCHEMA:
            raise ValueError("result schema")
        if result["taskHash"] != digest(task) or result["physicalQualified"] is not False:
            raise ValueError("source or scope binding")
        if type(result["visited"]) is not int or not 0 <= result["visited"] <= 100_000:
            raise ValueError("resource record")
        if type(result["elapsedSeconds"]) not in {int, float} or not 0 <= result["elapsedSeconds"] < 120:
            raise ValueError("elapsed record")
        status = result["status"]
        if status == "REFUTED":
            witness = result["witness"]
            if not isinstance(witness, dict) or set(witness) != {"x", "value"} or result["cover"]:
                raise ValueError("witness schema")
            x = proof_rational(witness["x"])
            if not a <= x <= b or str(value(p, x)) != witness["value"] or value(p, x) >= 0:
                raise ValueError("invalid counterexample")
        elif status == "PROVED":
            if result["witness"] is not None:
                raise ValueError("proof/witness conflict")
            if result["method"] == "exact-bernstein":
                cover = result["cover"]
                if not isinstance(cover, list) or not 1 <= len(cover) <= 4096:
                    raise ValueError("proof cap")
                cells = sorted(
                    (
                        proof_rational(x["interval"][0]),
                        proof_rational(x["interval"][1]),
                        proof_rational(x["lowerBound"]),
                    )
                    for x in cover
                )
                if cells[0][0] != a or cells[-1][1] != b:
                    raise ValueError("incomplete cover")
                for i, (lo, hi, asserted) in enumerate(cells):
                    if not lo < hi or i and cells[i - 1][1] != lo:
                        raise ValueError("cover gap or overlap")
                    n = len(p) - 1
                    shifted = [
                        sum((p[j] * Q(comb(j, k)) * lo ** (j - k) * (hi - lo) ** k for j in range(k, n + 1)), Q(0))
                        for k in range(n + 1)
                    ]
                    ordinates = [
                        sum((shifted[k] * Q(comb(j, k), comb(n, k)) for k in range(j + 1)), Q(0)) for j in range(n + 1)
                    ]
                    if asserted != min(ordinates) or asserted < 0:
                        raise ValueError("invalid Bernstein bound")
            elif result["method"] == "sympy-exact-roots":
                if result["cover"] or not globally_nonnegative(p, a, b):
                    raise ValueError("invalid global sign claim")
            else:
                raise ValueError("unsupported proof method")
        elif status == "UNKNOWN":
            if result["witness"] is not None or result["cover"]:
                raise ValueError("unknown promoted to evidence")
        else:
            raise ValueError("decision")
        return {
            "accepted": True,
            "decisive": status != "UNKNOWN",
            "status": status,
            "scope": "exact declared mathematical model; empirical validity untested",
        }
    except (ValueError, TypeError, KeyError, IndexError, ZeroDivisionError, OverflowError) as error:
        return {"accepted": False, "decisive": False, "reason": str(error)}
