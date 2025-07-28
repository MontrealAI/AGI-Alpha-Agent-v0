# SPDX-License-Identifier: Apache-2.0
"""Pareto rank scalarisation utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence, cast

import yaml

__all__ = ["aggregate", "load_weights"]


_DEFAULT_YAML = Path(__file__).with_suffix(".yaml")


def load_weights(path: str | Path | None = None) -> dict[str, float | Sequence[float]]:
    """Return weight configuration loaded from YAML."""
    p = Path(path) if path is not None else _DEFAULT_YAML
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return data or {}


def _non_dominated_sort(values: Sequence[Sequence[float]]) -> tuple[list[int], list[list[int]]]:
    n = len(values)
    ranks = [0] * n
    S: list[set[int]] = [set() for _ in range(n)]
    dominated = [0] * n
    for i, a in enumerate(values):
        for j, b in enumerate(values):
            if i == j:
                continue
            if all(ai <= bj for ai, bj in zip(a, b)) and any(ai < bj for ai, bj in zip(a, b)):
                S[i].add(j)
            elif all(bj <= ai for ai, bj in zip(a, b)) and any(bj < ai for ai, bj in zip(a, b)):
                dominated[i] += 1
        if dominated[i] == 0:
            ranks[i] = 0
    fronts = [[i for i, d in enumerate(dominated) if d == 0]]
    i = 0
    while i < len(fronts):
        nxt: list[int] = []
        for p in fronts[i]:
            for q in S[p]:
                dominated[q] -= 1
                if dominated[q] == 0:
                    ranks[q] = i + 1
                    nxt.append(q)
        if nxt:
            fronts.append(nxt)
        i += 1
    return ranks, fronts


def _crowding(values: Sequence[Sequence[float]], fronts: Iterable[Iterable[int]]) -> list[float]:
    n = len(values)
    m = len(values[0]) if n else 0
    crowd = [0.0] * n
    for front in fronts:
        f = list(front)
        if not f:
            continue
        for idx in f:
            crowd[idx] = 0.0
        for i in range(m):
            f.sort(key=lambda idx: values[idx][i])
            crowd[f[0]] = float("inf")
            crowd[f[-1]] = float("inf")
            fmin = values[f[0]][i]
            fmax = values[f[-1]][i]
            span = fmax - fmin or 1.0
            for j in range(1, len(f) - 1):
                prev_v = values[f[j - 1]][i]
                next_v = values[f[j + 1]][i]
                crowd[f[j]] += (next_v - prev_v) / span
    return crowd


def aggregate(
    values: Sequence[Sequence[float]],
    *,
    weights: dict[str, float | Sequence[float]] | None = None,
    weights_path: str | Path | None = None,
) -> list[float]:
    """Return scalar surrogate scores for ``values``."""
    cfg = weights if weights is not None else load_weights(weights_path)
    rank_w = float(cast(float, cfg.get("rank", 1.0)))
    crowd_w = float(cast(float, cfg.get("crowd", 0.0)))
    obj_w = cfg.get("objectives", [])
    if not isinstance(obj_w, Sequence):
        obj_w = []
    obj_w = list(obj_w) + [0.0] * (len(values[0]) - len(obj_w))
    ranks, fronts = _non_dominated_sort(values)
    crowds = _crowding(values, fronts)
    scores = []
    for idx, vec in enumerate(values):
        s = rank_w * ranks[idx] + crowd_w * crowds[idx]
        s += sum(w * v for w, v in zip(obj_w, vec))
        scores.append(float(s))
    return scores
