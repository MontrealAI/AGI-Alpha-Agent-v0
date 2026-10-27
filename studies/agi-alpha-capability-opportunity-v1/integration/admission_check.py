# SPDX-License-Identifier: Apache-2.0
"""Replay development-only conditional admission separately from conformance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from bridge import ROOT, run_lifecycle


def run(inputs: Path, artifact: Path, development: Path, out: Path) -> dict[str, Any]:
    """Preserve the existing gate's actual verdict, including every denial."""
    payload = json.loads(inputs.read_text())
    observed_hash = hashlib.sha256(development.read_bytes()).hexdigest()
    if observed_hash != payload["development_sha256"]:
        raise ValueError("Development observations changed after assessment preparation")
    candidates = [{**row, "artifact_path": str(artifact)} for row in payload["candidates"]]
    operations = [
        {"action": "retrieve", "key": f"{row['id']}@{row['version']}", "member": "lyra.agent.agi.eth"}
        for row in candidates
    ]
    result = run_lifecycle(candidates, operations)
    summary = {
        "schema": "capability-opportunity-development-admission/v1",
        "input_sha256": hashlib.sha256(inputs.read_bytes()).hexdigest(),
        "development_sha256": observed_hash,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "candidate_verdicts": [
            {
                "id": row["id"],
                "verdict": row["assessment"]["verdict"],
                "mean_delta_cents": row["assessment"]["meanDeltaCents"],
                "lower_delta_cents": row["assessment"]["lowerDeltaCents"],
                "lower_lifetime_net_cents": row["assessment"]["lowerLifetimeNetCents"],
                "reasons": row["assessment"]["reasons"],
                "admission": row["admission"],
            }
            for row in result["candidates"]
        ],
        "retrieval_allowed": [row["result"].get("ok") is True for row in result["operations"]],
        "evidence": "Actual synthetic numerical outcomes; USD values, scope price and reuse forecast are assumptions.",
        "selection_limitation": payload["economics"],
        "independent_confirmation": False,
        "controlled_conformance_has_separate_artificial_evidence": True,
        "production_admission": "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE",
        "actual_revenue_usd": 0,
        "frontier_model_alpha": "UNMEASURED",
    }
    out.mkdir(parents=True, exist_ok=False)
    (out / "lifecycle.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, default=ROOT.parent / "economics/lifecycle_inputs.json")
    parser.add_argument("--artifact", type=Path, default=ROOT.parent / "technical/artifacts/v2.json")
    parser.add_argument("--development", type=Path, default=ROOT.parent / "technical/results/development_rows.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = run(args.inputs, args.artifact, args.development, args.out)
    print(json.dumps(receipt["candidate_verdicts"]))
