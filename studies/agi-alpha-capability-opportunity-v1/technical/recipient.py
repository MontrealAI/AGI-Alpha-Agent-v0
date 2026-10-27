# SPDX-License-Identifier: Apache-2.0
"""Pure recipient execution of a retrieved empirical capability and declared observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from learning import WIDTH, features, fit_guarded


def invoke(artifact_bytes: bytes, mission: dict[str, Any]) -> dict[str, Any]:
    """Fit the recipient's own observations with the effective retrieved support artifact."""
    artifact = json.loads(artifact_bytes)
    support = artifact["support"]
    if not isinstance(support, list) or not support or any(type(i) is not int or i < 0 or i >= WIDTH for i in support):
        raise ValueError("Invalid empirical support artifact")
    train = features(np.asarray(mission["train_inputs"], dtype=float))
    values = np.asarray(mission["train_outputs"], dtype=float)
    validation = features(np.asarray(mission["validation_inputs"], dtype=float))
    validation_values = np.asarray(mission["validation_outputs"], dtype=float)
    model, metadata = fit_guarded(train, values, validation, validation_values, support)
    plans = np.asarray(mission["candidate_plans"], dtype=float)
    predicted = features(plans) @ model
    costs = 0.2 + np.mean((plans + 1) ** 2, axis=1)
    allowed = np.flatnonzero((predicted >= mission["target_response"] + 0.01) & (costs <= mission["cost_ceiling"]))
    chosen = int(allowed[np.argmin(costs[allowed])]) if len(allowed) else -1
    return {"artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(), "artifact_version": artifact["version"],
            "coefficients": model.tolist(), "chosen_plan": chosen,
            "chosen_plan_inputs": plans[chosen].tolist() if chosen >= 0 else None,
            "predicted_response": float(predicted[chosen]) if chosen >= 0 else None,
            "known_cost": float(costs[chosen]) if chosen >= 0 else None,
            "metadata": metadata, "operational_status": "proposal only; actual final simulator query still required",
            "rights": "Synthetic researcher-generated observations; no customer material"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--mission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = invoke(args.artifact.read_bytes(), json.loads(args.mission.read_text()))
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
