# SPDX-License-Identifier: Apache-2.0
"""Deterministic heuristic logic critic."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable, List

_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "critics" / "innovations.txt"


def load_examples(path: str | Path | None = None) -> List[str]:
    """Return example innovations from ``path`` or the default file."""
    p = Path(path) if path is not None else _DATA_FILE
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


class LogicCritic:
    """Assign a simple logic score based on known examples."""

    def __init__(self, examples: Iterable[str] | None = None, *, seed: int | None = None) -> None:
        self.examples = list(examples) if examples is not None else load_examples()
        self.index = {e.lower(): i for i, e in enumerate(self.examples)}
        self.rng = random.Random(seed)
        self.scale = max(len(self.examples) - 1, 1)

    def score(self, genome: str | Iterable[float]) -> float:
        """Return a heuristic logic score for ``genome``."""
        key = str(genome).lower()
        pos = self.index.get(key, -1)
        base = (pos + 1) / (self.scale + 1) if pos >= 0 else 0.0
        noise = self.rng.random() * 0.001
        val = base + noise
        return float(min(1.0, max(0.0, val)))
