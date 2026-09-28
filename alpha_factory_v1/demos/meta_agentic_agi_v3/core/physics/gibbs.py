# SPDX-License-Identifier: Apache-2.0
"""Numerically stable cost-minus-entropy proxy; not a physical energy or ELBO."""
from math import exp, isfinite, log
from typing import Sequence


def free_energy(logp: Sequence[float], temperature: float, task_cost: float) -> float:
    """Return E − T·H for normalized finite log weights and nonnegative T."""
    values = [float(x) for x in logp]
    if not values or not all(isfinite(x) for x in values):
        raise ValueError("Log weights must be nonempty and finite")
    if not isfinite(temperature) or temperature < 0 or not isfinite(task_cost):
        raise ValueError("Temperature must be nonnegative and cost finite")
    peak = max(values)
    weights = [exp(x - peak) for x in values]
    total = sum(weights)
    entropy = -sum((w / total) * log(w / total) for w in weights if w)
    return task_cost - temperature * entropy
