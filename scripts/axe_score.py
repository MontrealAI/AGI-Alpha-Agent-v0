#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Compute an accessibility score from Axe JSON output."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import os

WEIGHTS = {
    "minor": 1,
    "moderate": 5,
    "serious": 10,
    "critical": 20,
}


def compute_score(data: list | dict) -> int:
    """Return a simplified Axe score (0-100) from Axe CLI JSON."""
    violations: list[dict] = []
    if isinstance(data, list):
        for page in data:
            violations.extend(page.get("violations", []))
    else:
        violations = data.get("violations", [])

    total = 0
    for violation in violations:
        impact = violation.get("impact", "minor")
        total += WEIGHTS.get(impact, 1)
    score = max(0, 100 - total)
    return score


DEFAULT_THRESHOLD = int(os.environ.get("A11Y_THRESHOLD", "90"))


def main(path: str, threshold: int = DEFAULT_THRESHOLD) -> int:
    data = json.loads(Path(path).read_text())
    score = compute_score(data)
    print(score)
    if score < threshold:
        return 1
    return 0


if __name__ == "__main__":
    if not 2 <= len(sys.argv) <= 3:
        raise SystemExit(f"Usage: {sys.argv[0]} <axe.json> [threshold]")
    threshold = int(sys.argv[2]) if len(sys.argv) == 3 else DEFAULT_THRESHOLD
    raise SystemExit(main(sys.argv[1], threshold))
