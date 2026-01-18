# SPDX-License-Identifier: Apache-2.0
"""Pareto based parent selection helpers."""

from __future__ import annotations

import random
from typing import Any, Mapping, Protocol, Sequence


__all__ = ["select_parent"]


class RandomLike(Protocol):
    """Protocol for random number generators used by selection helpers."""

    def random(self) -> float:
        """Return a random float in the range [0.0, 1.0)."""

    def choice(self, seq: Sequence[Any]) -> Any:
        """Return a random element from a non-empty sequence."""


def _metrics(item: Any) -> tuple[float, float, float]:
    """Return (rmse, inference_ms, gasCost) triple for ``item``."""
    if isinstance(item, Mapping):
        rmse = float(item.get("rmse", item.get("RMSE", 0.0)))
        inf = float(item.get("inference_ms", 0.0))
        gas = float(item.get("gasCost", item.get("gas_cost", 0.0)))
        return rmse, inf, gas
    rmse = float(getattr(item, "rmse", getattr(item, "RMSE", 0.0)))
    inf = float(getattr(item, "inference_ms", 0.0))
    gas = float(getattr(item, "gasCost", getattr(item, "gas_cost", 0.0)))
    return rmse, inf, gas


def _pareto_ranks(pop: Sequence[Any]) -> list[int]:
    metrics = [_metrics(p) for p in pop]
    ranks = [1 for _ in pop]
    for i, a in enumerate(metrics):
        for j, b in enumerate(metrics):
            if i == j:
                continue
            if all(bk <= ak for bk, ak in zip(b, a)) and any(bk < ak for bk, ak in zip(b, a)):
                ranks[i] += 1
    return ranks


def select_parent(pop: Sequence[Any], *, epsilon: float = 0.1, rng: RandomLike | None = None) -> Any:
    """Return a parent from ``pop`` via Pareto rank with epsilon-greedy randomness."""
    if not pop:
        raise ValueError("population is empty")
    rng = rng or random
    ranks = _pareto_ranks(pop)
    best = min(ranks)
    candidates = [ind for ind, r in zip(pop, ranks) if r == best]
    non_best = [ind for ind, r in zip(pop, ranks) if r != best]
    if non_best and rng.random() < epsilon:
        return rng.choice(non_best)
    return rng.choice(candidates)
