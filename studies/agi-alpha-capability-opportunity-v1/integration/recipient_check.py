# SPDX-License-Identifier: Apache-2.0
"""Execute retrieved capability bytes on one preregistered, fresh synthetic task."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent
TECHNICAL = ROOT.parent / "technical"


def sha256(path: Path) -> str:
    """Hash an ordinary source or artifact file."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected an ordinary file: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(original: Path, retrieved: Path, out: Path) -> dict[str, Any]:
    """Freeze a challenge, then make only declared oracle observations available."""
    out.mkdir(parents=True, exist_ok=False)
    source_paths = [TECHNICAL / name for name in ["benchmark.py", "learning.py", "recipient.py"]]
    protocol: dict[str, Any] = {
        "schema": "capability-opportunity-recipient-protocol/v1",
        "seed": 1_010_007,
        "regime": "compatible",
        "development_or_confirmation_case": False,
        "training_observations": 31,
        "visible_validation_observations": 8,
        "final_plan_validation_observations": 1,
        "total_oracle_budget": 40,
        "candidate_design_points": 192,
        "candidate_plans": 512,
        "target_response": 2.0,
        "cost_ceiling": 1.2,
        "source_sha256": {path.name: sha256(path) for path in source_paths},
        "original_artifact_sha256": sha256(original),
        "retrieved_artifact_sha256": sha256(retrieved),
        "evidence_scope": "Separate integration challenge; not an additional confirmation replicate.",
        "authorization": "Controlled local research execution; no production capsule admission.",
        "freeze_order": "This protocol is written before task generation or oracle evaluation.",
    }
    (out / "protocol.json").write_text(json.dumps(protocol, indent=2, allow_nan=False) + "\n")
    if protocol["original_artifact_sha256"] != protocol["retrieved_artifact_sha256"]:
        raise ValueError("Retrieved bytes do not equal the frozen originating artifact")
    sys.path.insert(0, str(TECHNICAL))
    from benchmark import evaluate, make_task, points
    from learning import d_optimal_order
    from recipient import invoke

    seed = int(protocol["seed"])
    artifact = json.loads(retrieved.read_bytes())
    oracle, _ = make_task(seed, "compatible")
    pool = points(seed + 440_009, 192)
    train = pool[d_optimal_order(pool, artifact["support"])[:31]]
    validation = points(seed + 110_003, 8)
    mission = {
        "train_inputs": train.tolist(),
        "train_outputs": oracle.query(train).tolist(),
        "validation_inputs": validation.tolist(),
        "validation_outputs": oracle.query(validation).tolist(),
        "candidate_plans": points(seed + 720_007, 512).tolist(),
        "target_response": 2.0,
        "cost_ceiling": 1.2,
    }
    # This identical-content local library has the same observations and execution
    # rights. Its parity makes no claim that a graph improves numerical intelligence.
    recipient_output = invoke(retrieved.read_bytes(), mission)
    library_output = invoke(original.read_bytes(), mission)
    equal_outputs = recipient_output == library_output
    chosen = recipient_output["chosen_plan_inputs"]
    actual_response: float | None = None
    actual_cost: float | None = None
    accepted = False
    if chosen is not None:
        actual_response = float(oracle.query(np.asarray([chosen], dtype=float))[0])
        actual_cost = float(0.2 + np.mean((np.asarray(chosen, dtype=float) + 1) ** 2))
        accepted = bool(actual_response >= 2.0 and actual_cost <= 1.2)
    else:
        actual_cost = None
    # Protected synthetic coefficients are used only after the delivered action has
    # been fixed. The scorer does not provide observations to the recipient.
    audit = evaluate(np.asarray(recipient_output["coefficients"]), oracle, seed, recipient_output["chosen_plan"])
    result = {
        "schema": "capability-opportunity-recipient-receipt/v1",
        "artifact_sha256": protocol["retrieved_artifact_sha256"],
        "artifact_bytes": retrieved.stat().st_size,
        "task_seed": seed,
        "independently_chosen_new_task": True,
        "declared_oracle_budget": 40,
        "actual_observation_calls": oracle.calls,
        "selected_plan": recipient_output["chosen_plan"],
        "actual_response": actual_response,
        "actual_cost": actual_cost,
        "acceptance": {"response_at_least": 2.0, "cost_at_most": 1.2, "accepted": accepted},
        "library_with_identical_content_and_permissions_output_identical": equal_outputs,
        "source_hashes_unchanged": all(sha256(path) == protocol["source_sha256"][path.name] for path in source_paths),
        "research_audit": audit,
        "audit_cost_boundary": "896 synthetic scorer evaluations equivalent, excluded from the 40 paid observations; this integration audit is research overhead.",
        "originating_artifact_retrieved_through": "Pinned research lifecycle with explicitly artificial monetary conformance evidence.",
        "empirical_alpha_admission": False,
        "controlled_research_execution_only": True,
        "production_admission": "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE",
        "authentication": "SYNTHETIC_MEMBERS_REAL_LOCAL_CRYPTO_NO_LIVE_ENS",
        "graph_specific_numerical_advantage": False,
        "actual_frontier_model_calls": 0,
        "actual_revenue_usd": 0,
        "limitations": "One compatible synthetic task tests the data path and execution; it does not establish transfer rates, market demand, or live authority.",
    }
    for name, record in [
        ("mission", mission),
        ("recipient-output", recipient_output),
        ("ordinary-library-output", library_output),
        ("receipt", result),
    ]:
        (out / (name + ".json")).write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    if not equal_outputs or not result["source_hashes_unchanged"] or oracle.calls > 40:
        raise RuntimeError("The integration execution violated its frozen data-path controls")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--retrieved", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    receipt = run(arguments.original, arguments.retrieved, arguments.out)
    print(json.dumps({key: receipt[key] for key in ["artifact_sha256", "actual_observation_calls", "acceptance"]}))
