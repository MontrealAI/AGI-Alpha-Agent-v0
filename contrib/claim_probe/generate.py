# SPDX-License-Identifier: Apache-2.0
"""Predeclared structural task generator; no private truth given to solvers."""

import random
from fractions import Fraction as Q

from alpha_factory_v1.core.runtime.claim_probe.operator import example


def multiply(a, b):
    out = [Q(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def make_task(seed, family, index):
    rng = random.Random(seed)
    t = example()
    t["id"] = f"claim-{family}-{index}"
    t["limits"] = {"cells": 256, "depth": 18, "seconds": 5}
    r = Q(rng.randint(10, 80), 100)
    if family == "positive":
        c = multiply([-r, Q(1)], [-r, Q(1)])
        c[0] += Q(rng.randint(1, 50), 100)
    elif family == "boundary":
        c = [Q(rng.randint(1, 10), 100), -Q(1)]
    elif family == "narrow":
        r = Q(rng.randint(50, 900) * 2 + 1, 2000)
        c = multiply([-r, Q(1)], [-r, Q(1)])
        c[0] -= Q(1, 10**8)
    elif family == "tangency":
        t["domain"] = ["0", "2"]
        base = [-Q(rng.choice([2, 3])), Q(0), Q(1)]
        c = multiply(base, base)
    elif family == "mixed":
        c = [Q(1)]
        for _ in range(rng.randint(3, 6)):
            c = multiply(c, [-Q(rng.randint(1, 9), 10), Q(1)])
    elif family == "resource":
        t["domain"] = ["0", "2"]
        c = [Q(4), Q(0), -Q(4), Q(0), Q(1)]
        t["limits"].update(cells=1, depth=0)
    else:
        raise ValueError("undeclared family")
    t["coefficients"] = list(map(str, c))
    return t


FAMILIES = ["positive", "boundary", "narrow", "tangency", "mixed", "resource"]
