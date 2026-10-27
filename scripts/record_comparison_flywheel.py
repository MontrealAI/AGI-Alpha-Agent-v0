# SPDX-License-Identifier: Apache-2.0
"""Replay prospective comparison reconciliation using the existing conformance seams."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_discovery import ComparisonCost
from alpha_factory_v1.core.runtime.successor.protocol import canonical

ROOT = Path(__file__).resolve().parents[1]


def record() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "tests/runtime"))
    import test_flywheel_comparisons as c
    import test_flywheel_protected as f
    import test_flywheel_specialists as s

    with tempfile.TemporaryDirectory(prefix="comparison-flywheel-conformance-") as temporary:
        state = f.setup.__wrapped__(Path(temporary))
        spec = c.plan(state).model_copy(
            update={
                "additional_costs": [
                    ComparisonCost(role="E+", mission_id="comparison-retention-assessment", bucket="B")
                ]
            }
        )
        spec = c.freeze(state, spec)
        planned = c.report(state, spec)
        for trial in spec.cases[0].trials:
            c.run_trial(state, trial)
        partial = c.report(state, spec)
        for trial in spec.cases[1].trials:
            c.run_trial(state, trial)
        unknown_additional = c.report(state, spec)
        f.account(
            state,
            "charge",
            {
                "activity_id": "comparison-retention-screen",
                "mission_id": "comparison-retention-assessment",
                "bucket": "B",
                "category": "human",
                "accrued_micro_usd": 77,
                "paid_micro_usd": 0,
                "basis": "attested",
                "evidence_digest": f.ZERO,
                "note": "FICTIONAL micro-unit conformance amount; actual complete cost remains unknown",
            },
            "comparison-retention-screen",
        )
        s.seal(state, "comparison-retention-assessment", "B")
        complete = c.report(state, spec)
        before = state["costs"].snapshot()
        assert complete == c.report(state, spec)
        assert before == state["costs"].snapshot()
        assert all(arm["accepted"] == arm["planned"] == 2 for arm in complete["arms"].values())
        assert all(row["accepted_difference"] == 0 for row in complete["contrasts"].values())
        assert complete["contrasts"]["retained"]["cost_saving_micro_usd"] == "-77"
        frozen = c.Discovery(state["service"]).inspect("comparison", spec.comparison_id)
        return {
            "schema_name": "flywheel-comparison-conformance/v1",
            "selection": {
                "beneficiary": "Operators qualifying useful agent work on the existing Flywheel",
                "unmet_need": "Execution-derived attribution across a complete prospective comparison cohort",
                "existing_limitation": "Current plans freeze conditions but carry no reconciled observations",
                "transformation": "Join frozen operations, original mission costs and independent acceptance in place",
                "alternatives": [
                    {
                        "approach": "Self-reported scores",
                        "decision": "reject",
                        "reason": "No exact execution or complete denominator",
                    },
                    {
                        "approach": "Separate evaluation registry",
                        "decision": "reject",
                        "reason": "Duplicates existing custody and accounting",
                    },
                    {
                        "approach": "Derived existing-Journal report",
                        "decision": "construct",
                        "reason": "Preserves native authority and costs",
                    },
                ],
                "falsifier": "A changed receipt, hidden failure or unknown cost yields a qualified positive contrast",
                "commercial_hypothesis": "Reduce qualification errors and repeat audit work; buyer value unmeasured",
                "provenance": "Researcher-selected need and supplied protocol cases; no autonomous invention",
            },
            "components": {
                "orchestration": "executed-local",
                "tools": "executed-local",
                "acceptance": "independent-existing-finite-placement-checker",
                "model": "scripted-protocol-fixture/v1",
                "identity": "simulated-fixture",
                "billing": "fictional signed conformance amounts",
                "market": "not-observed",
            },
            "plan": frozen,
            "stages": {
                "planned": planned,
                "partially-executed": partial,
                "additional-costs-unknown": unknown_additional,
                "reconciled-fixture": complete,
            },
            "actual_customer_collections_micro_usd": 0,
            "actual_complete_cost_micro_usd": None,
            "controlled_frontier_trials": 0,
            "ordinary_library_control": "Not run here; existing parent controls retain their original scope",
            "retention": "No new admission; a declared condition proves neither invocation nor economic benefit",
            "read_only_reconciliation": True,
            "sources": {
                str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (
                    ROOT / "alpha_factory_v1/core/runtime/successor/flywheel_comparisons.py",
                    ROOT / "alpha_factory_v1/core/runtime/successor/flywheel_discovery.py",
                    ROOT / "alpha_factory_v1/core/runtime/successor/flywheel_execution.py",
                    ROOT / "alpha_factory_v1/core/runtime/successor/flywheel_costs.py",
                    ROOT / "alpha_factory_v1/core/runtime/successor/flywheel_learning.py",
                    ROOT / "scripts/record_comparison_flywheel.py",
                    ROOT / "tests/runtime/test_flywheel_comparisons.py",
                )
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = record()
    with args.output.open("xb") as output:
        output.write(canonical(value) + b"\n")


if __name__ == "__main__":
    main()
