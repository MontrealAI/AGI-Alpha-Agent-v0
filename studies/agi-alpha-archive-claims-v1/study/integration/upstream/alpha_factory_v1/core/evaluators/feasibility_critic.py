# SPDX-License-Identifier: Apache-2.0
"""Deterministic feasibility critic using token overlap."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable, List

_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "critics" / "innovations.txt"


def load_examples(path: str | Path | None = None) -> List[str]:
    p = Path(path) if path is not None else _DATA_FILE
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


class FeasibilityCritic:
    """Score how feasible a genome appears compared to known innovations."""

    def __init__(self, examples: Iterable[str] | None = None, *, seed: int | None = None) -> None:
        self.examples = list(examples) if examples is not None else load_examples()
        self.rng = random.Random(seed)

    @staticmethod
    def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
        sa, sb = set(a), set(b)
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def score(self, genome: str | Iterable[float]) -> float:
        """Return a feasibility score based on Jaccard overlap."""
        tokens = str(genome).lower().split()
        best = 0.0
        for ex in self.examples:
            sim = self._jaccard(tokens, ex.lower().split())
            if sim > best:
                best = sim
        noise = self.rng.random() * 0.001
        val = best + noise
        return float(min(1.0, max(0.0, val)))
