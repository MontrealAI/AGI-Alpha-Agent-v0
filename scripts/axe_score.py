#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Compute an accessibility score from Axe JSON output."""

from __future__ import annotations

import json
import sys
from pathlib import Path

WEIGHTS = {
    "minor": 1,
    "moderate": 5,
    "serious": 10,
    "critical": 20,
}


def compute_score(data: dict) -> int:
    """Return a simplified Axe score (0-100)."""
    total = 0
    for violation in data.get("violations", []):
        impact = violation.get("impact", "minor")
        total += WEIGHTS.get(impact, 1)
    score = max(0, 100 - total)
    return score


def main(path: str) -> int:
    data = json.loads(Path(path).read_text())
    if isinstance(data, list):
        data = data[0]
    violations = data.get("violations", [])
    score = compute_score({"violations": violations})
    print(score)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} <axe.json>")
    raise SystemExit(main(sys.argv[1]))
