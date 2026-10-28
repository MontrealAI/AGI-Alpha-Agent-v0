# SPDX-License-Identifier: Apache-2.0
"""Produce transparent development briefs; confirmation is generated separately."""

from __future__ import annotations
import json
import random
from pathlib import Path
from engine import DEFAULT_BOX, deliver

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Exercise complementary access and a different robust-portfolio mission."""
    witness = json.loads((ROOT / "verification/independent_graphs.json").read_text())
    models = [{"id": m["id"], "adjacency": m["adjacency"]} for m in witness["models"]]
    brief = {
        "schema": "possibility-engine-input-v1",
        "models": models,
        "uncertainty": DEFAULT_BOX,
        "times": [i / 1000 for i in range(50, 501)],
        "failure_mode": "none",
    }
    arms = {
        "current": [(0, 0)],
        "actuator_only": [(i, 0) for i in range(16)],
        "sensor_only": [(0, i) for i in range(16)],
        "joint": [(i, j) for i in range(16) for j in range(16)],
    }
    for name, choices in arms.items():
        data = {
            **brief,
            "experiments": [
                {"actuator": a, "sensor": s, "cost_units": 2 + (a != 0) * 5 + (s != 0) * 7} for a, s in choices
            ],
        }
        r = deliver(data, ROOT / "evidence/development" / name)
        print(name, r["status"], r["cost_units"], r["robust_margin"])
    rng = random.Random(20261028)
    neighbors = witness["root_neighbors"]
    others = [i for i in range(1, 16) if i not in neighbors]
    family = models.copy()
    for n in range(4):
        p = list(range(16))
        ns = neighbors.copy()
        os = others.copy()
        rng.shuffle(ns)
        rng.shuffle(os)
        for old, new in zip(neighbors + others, ns + os):
            p[old] = new
        a = models[n % 2]["adjacency"]
        b = [[a[p[i]][p[j]] for j in range(16)] for i in range(16)]
        family.append({"id": f"variant_{n}", "adjacency": b})
    choices = [
        (1, 3),
        (2, 6),
        (4, 7),
        (5, 10),
        (6, 9),
        (7, 11),
        (8, 12),
        (9, 13),
        (10, 14),
        (11, 15),
        (1, 8),
        (3, 14),
        (2, 12),
        (4, 15),
        (5, 13),
        (6, 11),
    ]
    data = {
        **brief,
        "models": family,
        "failure_mode": "one_terminal",
        "experiments": [{"actuator": a, "sensor": s, "cost_units": 10 + (a * 3 + s) % 7} for a, s in choices],
    }
    r = deliver(data, ROOT / "evidence/development/successor")
    print("successor", r["status"], r["cost_units"], len(r["selected"]))


if __name__ == "__main__":
    main()
