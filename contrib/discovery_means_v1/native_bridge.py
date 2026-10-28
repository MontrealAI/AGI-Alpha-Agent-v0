# SPDX-License-Identifier: Apache-2.0
"""Read-only bridge to installed native discovery contracts and predecessor.

The bundle is a validated DRAFT. This module never submits commands, provisions
roles, calls a provider, constructs a ledger or grants execution permissions.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor import flywheel_discovery, flywheel_probe, protocol
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import ExplorationBundle, ExperimentStep
from alpha_factory_v1.core.runtime.successor.flywheel_probe import (
    ProbeProblem,
    ReadOnlyProbe,
    EffectHypothesis,
    inspect_information,
    verify_information,
)
from alpha_factory_v1.core.runtime.successor.protocol import digest
from discovery_means import instrument


def native_receipt(problem: dict[str, Any]) -> dict[str, Any]:
    """Execute installed native encoders, schema and historical finite predecessor."""
    result = instrument.solve(problem)
    checked = instrument.verify(problem, result)
    witness = digest("discovery-means-draft-witness/v1", {"problem": result["problem_digest"]})
    draft = ExplorationBundle.model_validate(
        dict(
            bundle_id="adaptive-investigation-draft",
            witness_id="unsubmitted-instrument-witness",
            witness_spec_digest=witness,
            steps=[
                {
                    "step_id": "construct-policy",
                    "question": "Can a permitted contingent policy identify every model?",
                    "dependencies": [],
                    "proposed_artifact": result["problem_digest"],
                    "decisive_check": "Independently traverse all policy branches and compare an exact oracle",
                    "falsifying_observation": "An allowed observation reaches an ambiguous leaf or exceeds a cap",
                    "cost_bucket": "B",
                    "cost_cap_micro_usd": 0,
                    "seconds_cap": 60,
                }
            ],
            total_cost_cap_micro_usd=0,
            total_seconds_cap=60,
            checkpoint_after=["construct-policy"],
            stopping_conditions=["No outside actions or provider calls", "Stop at finite search cap"],
            joint_value_hypothesis="Observation-conditioned actions may resolve work that exceeds a static portfolio budget",
            uncertainty="Cost units are abstract; full research cost unknown. This draft is not authority or funding.",
        )
    )
    example = ProbeProblem.model_validate(
        dict(
            mission_digest=witness,
            purpose_digest=witness,
            input_semantics="Two finite effect hypotheses",
            required_output_semantics="Effect class in the declared finite model",
            observation_epoch=witness,
            coverage_basis="Authored development compatibility case; no physical adequacy claim",
            probes=[
                {
                    "probe_id": "read",
                    "observation_contract": "Singleton symbol",
                    "source_digest": witness,
                    "query_units": 1,
                }
            ],
            hypotheses=[
                {"hypothesis_id": "absent", "result": "not-applied", "observations": {"read": "zero"}},
                {"hypothesis_id": "present", "result": "applied", "observations": {"read": "one"}},
            ],
            query_budget=1,
        )
    )
    prior = inspect_information(example, [])
    modules = {}
    for module in (instrument, protocol, flywheel_probe, flywheel_discovery):
        path = Path(str(module.__file__)).resolve()
        modules[module.__name__] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return {
        "scope": "installed editable add-on plus installed native contracts; not full operating qualification",
        "distribution_versions": {
            n: importlib.metadata.version(n)
            for n in ("alpha-factory-v1", "agi-discovery-means", "pydantic", "cryptography")
        },
        "loaded_modules": modules,
        "construction": result,
        "policy_verification": checked,
        "native_bundle_draft": draft.model_dump(),
        "native_bundle_submitted": False,
        "native_predecessor": prior,
        "native_predecessor_verified": verify_information(example, [], prior),
        "frontier_execution": "BLOCKED: no provisioned signed deployment/model permit; no call attempted",
        "qualification": "BLOCKED: sparse environment and installed dependency versions do not meet full lock",
        "authority_granted": False,
        "new_ledger_created": False,
    }


def main() -> None:
    """Write a receipt to standard output for capture outside private runtime state."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("problem", type=Path)
    args = parser.parse_args()
    from discovery_means.cli import read_bounded

    print(json.dumps(native_receipt(read_bounded(args.problem)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
