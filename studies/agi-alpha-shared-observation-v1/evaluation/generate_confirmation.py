# SPDX-License-Identifier: Apache-2.0
"""Protected synthetic confirmation generator, written without reading the compiler."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from reference import validate


SEED = 73019468271
SCOPE = "shared-secondary-risk-v1"


def probabilities(values: list[float]) -> list[float]:
    """Normalize and retain a final decimal residual."""
    total = sum(values)
    normalized = [round(x / total, 10) for x in values[:-1]]
    return normalized + [round(1 - sum(normalized), 10)]


def informative(rng: random.Random, n: int, failure: float | None = None) -> list[dict[str, Any]]:
    """Construct an explicitly assumed state-conditional sensor channel."""
    rows: list[list[float]] = []
    for state in range(n):
        missing = round(rng.uniform(0.03, 0.16), 8) if failure is None else failure
        accurate = round(rng.uniform(0.78, 0.93) * (1 - missing), 8)
        other = round((1 - missing - accurate) / (n - 1), 8)
        row = [accurate if j == state else other for j in range(n)]
        row.append(round(1 - sum(row), 8))
        rows.append(row)
    outcomes = [
        {
            "id": f"signal-{j}",
            "likelihood": [row[j] for row in rows],
            "arrival_hours": round(rng.uniform(0.15, 0.45), 6),
        }
        for j in range(n)
    ]
    outcomes.append({"id": "no-result", "likelihood": [row[-1] for row in rows], "arrival_hours": None})
    return outcomes


def base(rng: random.Random, case_id: str, n: int = 3, count: int = 4) -> dict[str, Any]:
    """Generate heterogeneous finite-risk mission obligations."""
    mission: dict[str, Any] = {
        "schema": "shared-observation-mission/v1",
        "mission_id": case_id,
        "evidence_type": "synthetic",
        "calibration_scope": SCOPE,
        "states": [f"secondary-state-{j}" for j in range(n)],
        "prior": probabilities([rng.uniform(1, 4) for _ in range(n)]),
        "observation": {
            "id": f"assumed-sensor-{case_id}",
            "usable": True,
            "rights_cleared": True,
            "calibration_scope": SCOPE,
            "outcomes": informative(rng, n),
        },
        "operators": [],
    }
    for j in range(count):
        limit = round(rng.uniform(0.7, 1.4) * 1e-4, 12)
        danger = (j + rng.randrange(n)) % n
        coast_risk = [
            round(limit * (rng.uniform(5.5, 10.0) if k == danger else rng.uniform(0.01, 0.25)), 12) for k in range(n)
        ]
        fallback_risk = [round(limit * rng.uniform(0.01, 0.12), 12) for _ in range(n)]
        deadline = round(rng.uniform(0.6, 2.4), 6)
        fallback_cost = round(rng.uniform(55, 240), 2)
        actions = [
            {"id": "coast", "risk_by_state": coast_risk, "cost_usd": 0.0, "latest_start_hours": deadline + 0.3},
            {
                "id": "fallback",
                "risk_by_state": fallback_risk,
                "cost_usd": fallback_cost,
                "latest_start_hours": deadline + 0.2,
            },
            {
                "id": "conservative",
                "risk_by_state": [round(x / 4, 12) for x in fallback_risk],
                "cost_usd": round(fallback_cost * 1.35, 2),
                "latest_start_hours": deadline + 0.2,
            },
        ]
        mission["operators"].append(
            {
                "id": f"operator-{j}",
                "risk_limit": limit,
                "decision_deadline_hours": deadline,
                "fallback_action": "fallback",
                "actions": actions,
            }
        )
    return mission


def build_cases() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Construct 48 fresh cases without computing reference answers."""
    rng = random.Random(SEED)
    cases: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    categories = [
        "shared_information",
        "zero_or_negative_value",
        "adverse_information",
        "heterogeneous_deadlines",
        "sensor_prerequisites",
        "participant_withdrawal",
    ]
    for category in categories:
        for within in range(8):
            index = len(cases) + 1
            case_id = f"confirmation-{index:03d}"
            n = rng.choice([4, 5]) if category == "participant_withdrawal" else 3
            count = 6 if category == "participant_withdrawal" else rng.randint(2, 5)
            mission = base(rng, case_id, n, count)
            note: dict[str, Any] = {"case_id": case_id, "category": category, "within_category": within}
            if category == "zero_or_negative_value":
                if within < 4:
                    for op in mission["operators"]:
                        op["actions"][0]["risk_by_state"] = [
                            round(op["risk_limit"] * rng.uniform(0.05, 0.4), 12) for _ in range(n)
                        ]
                    note["design"] = (
                        "coast safe without observation; obligatory timeout fallback can have negative value"
                    )
                else:
                    likelihoods = probabilities([rng.uniform(1, 5) for _ in range(n + 1)])
                    for j, out in enumerate(mission["observation"]["outcomes"]):
                        out["likelihood"] = [likelihoods[j]] * n
                    note["design"] = "uninformative channel, unchanged posterior"
            elif category == "adverse_information":
                hazard = round(rng.uniform(0.015, 0.07), 8)
                mission["prior"] = [round(0.65 - hazard, 8), 0.35, hazard]
                mission["observation"]["outcomes"] = [
                    {"id": "reassuring", "likelihood": [0.97, 0.97, 0.01], "arrival_hours": 0.2},
                    {"id": "adverse", "likelihood": [0.01, 0.01, 0.97], "arrival_hours": 0.2},
                    {"id": "no-result", "likelihood": [0.02, 0.02, 0.02], "arrival_hours": None},
                ]
                for op in mission["operators"]:
                    op["actions"][0]["risk_by_state"] = [round(op["risk_limit"] * x, 12) for x in [0.08, 0.1, 10]]
                note["design"] = "prior coast acceptable; adverse timely signal requires paid action"
            elif category == "heterogeneous_deadlines":
                for j, op in enumerate(mission["operators"]):
                    op["decision_deadline_hours"] = [0.5, 1.25, 2.0][j % 3]
                    for action in op["actions"]:
                        action["latest_start_hours"] = op["decision_deadline_hours"] + 0.2
                for j, out in enumerate(mission["observation"]["outcomes"][:-1]):
                    out["arrival_hours"] = [0.25, 1.0, 1.8][j]
                if within in (2, 3):
                    op = mission["operators"][0]
                    op["actions"][1]["latest_start_hours"] = op["decision_deadline_hours"] - 0.1
                    note["design"] = "timeout fallback cannot start by its latest start"
                elif within in (4, 5):
                    mission["prior"] = [0.6, 0.3, 0.1]
                    mission["observation"]["outcomes"] = [
                        {"id": "clear", "likelihood": [0.99, 0.99, 0.0], "arrival_hours": 0.25},
                        {"id": "late-danger", "likelihood": [0.0, 0.0, 0.9], "arrival_hours": 4.0},
                        {"id": "no-result", "likelihood": [0.01, 0.01, 0.1], "arrival_hours": None},
                    ]
                    for op in mission["operators"]:
                        op["actions"][0]["risk_by_state"] = [round(op["risk_limit"] * x, 12) for x in [0.1, 0.1, 8]]
                        op["actions"][1]["risk_by_state"] = [round(op["risk_limit"] * x, 12) for x in [0.2, 0.2, 2]]
                    note["design"] = "adversarial: prior-safe fallback becomes unsafe conditional on aggregated timeout"
                elif within in (6, 7):
                    mission["observation"]["outcomes"] = [
                        {"id": f"signal-{j}", "likelihood": [float(j == k) for k in range(n)], "arrival_hours": 0.5}
                        for j in range(n)
                    ]
                    mission["observation"]["outcomes"].append(
                        {"id": "unreachable-signal", "likelihood": [0.0] * n, "arrival_hours": 0.5}
                    )
                    for op in mission["operators"]:
                        op["decision_deadline_hours"] = 0.5
                        for action in op["actions"]:
                            action["latest_start_hours"] = 0.5
                    note["design"] = "deadline equality and unreachable timely/timeout branches"
                else:
                    note["design"] = "different buyers receive different timeout aggregation of the same outcomes"
            elif category == "sensor_prerequisites":
                if within % 3 == 0:
                    mission["observation"]["usable"] = False
                    note["design"] = "unusable sensor"
                elif within % 3 == 1:
                    mission["observation"]["rights_cleared"] = False
                    note["design"] = "rights not cleared"
                else:
                    mission["observation"]["calibration_scope"] = "different-supplied-scope"
                    note["design"] = "scope mismatch"
            elif category == "participant_withdrawal":
                original = copy.deepcopy(mission["operators"])
                removed = set(rng.sample(range(count), rng.randint(1, 3)))
                mission["operators"] = [op for j, op in enumerate(original) if j not in removed]
                note["withdrawn_ids"] = [original[j]["id"] for j in sorted(removed)]
                note["original_operator_count"] = count
                note["design"] = "active roster is recompiled after withdrawal; no removed buyer benefit survives"
            else:
                note["design"] = (
                    "common observation, heterogeneous purposes and positive/zero information benefit possible"
                )
            validate(mission)
            cases.append(mission)
            manifest.append(note)
    return cases, manifest


def main() -> int:
    """Save inputs and a commitment; do not evaluate the retained artifact."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases, metadata = build_cases()
    entries = []
    for mission, note in zip(cases, metadata, strict=True):
        path = args.output_dir / f"{mission['mission_id']}.json"
        payload = (json.dumps(mission, indent=2, allow_nan=False) + "\n").encode()
        path.write_bytes(payload)
        entries.append({**note, "filename": path.name, "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {
        "schema": "shared-observation-confirmation-manifest/v1",
        "evidence_type": "synthetic",
        "seed": SEED,
        "cases": entries,
        "results_computed": False,
    }
    data = (json.dumps(manifest, indent=2) + "\n").encode()
    (args.output_dir / "manifest.json").write_bytes(data)
    print(
        json.dumps(
            {"case_count": len(cases), "manifest_sha256": hashlib.sha256(data).hexdigest(), "results_computed": False}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
