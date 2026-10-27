# SPDX-License-Identifier: Apache-2.0
"""Reproduce a discovery-selected information instrument, with no operating grant."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_probe import (
    EffectHypothesis,
    ProbeObservation,
    ProbeProblem,
    ReadOnlyProbe,
    inspect_information,
    verify_information,
)
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest, safe_json_loads

ROOT = Path(__file__).resolve().parents[1]


def problem(identity: str, *, distinguishable: bool = True) -> ProbeProblem:
    return ProbeProblem(
        mission_digest=digest("probe-mission", {"id": identity}),
        purpose_digest=digest("probe-purpose", {"required": "identify original effect without repeating it"}),
        input_semantics="An immutable synthetic audit snapshot after an unacknowledged local action",
        required_output_semantics="Classify only the original effect; no retry, mutation, acceptance or permission",
        observation_epoch=digest("probe-epoch", {"id": identity, "snapshot": 1}),
        coverage_basis="Three researcher-supplied finite worlds; completeness for real services is unqualified",
        probes=[
            ReadOnlyProbe(
                probe_id="client-log",
                observation_contract="Retained acknowledgment only",
                source_digest="a" * 64,
                query_units=1,
            ),
            ReadOnlyProbe(
                probe_id="effect-audit",
                observation_contract="Snapshot bound to original operation identity",
                source_digest="b" * 64,
                query_units=2,
            ),
        ],
        hypotheses=[
            EffectHypothesis(
                hypothesis_id=state,
                result=state,
                observations={
                    "client-log": "ack-missing",
                    "effect-audit": state if distinguishable else "audit-unavailable",
                },
            )
            for state in ("not-applied", "applied", "partially-applied")
        ],
        query_budget=3,
    )


def observed(spec: ProbeProblem, probe_id: str, value: str) -> ProbeObservation:
    probe = next(p for p in spec.probes if p.probe_id == probe_id)
    return ProbeObservation(
        probe_id=probe_id, value=value, observation_epoch=spec.observation_epoch, source_digest=probe.source_digest
    )


def episode(spec: ProbeProblem, value: str) -> dict[str, Any]:
    initial = [observed(spec, "client-log", "ack-missing")]
    request = inspect_information(spec, initial)
    rows = initial + ([observed(spec, "effect-audit", value)] if request["next_probe"] else [])
    result = inspect_information(spec, rows)
    return {
        "problem": spec.model_dump(),
        "observations": [r.model_dump() for r in rows],
        "before": request,
        "after": result,
        "verified": verify_information(spec, rows, result),
    }


def recipient(payload: dict[str, Any]) -> dict[str, Any]:
    spec = ProbeProblem.model_validate(payload["problem"])
    rows = [ProbeObservation.model_validate(row) for row in payload["observations"]]
    result = inspect_information(spec, rows)
    return {
        "report": result,
        "verified": verify_information(spec, rows, result),
        "authority_granted": False,
        "authentication": "separate local process, not ENS authentication",
    }


def candidate_dossier() -> list[dict[str, Any]]:
    return [
        {
            "id": "uncertain-effect-information-instrument",
            "title_en": "Find the missing observation",
            "title_fr": "Trouver l’observation manquante",
            "beneficiary": "Operators with an uncertain tool effect and no server idempotency guarantee",
            "useful_outcome": "An evidence request or justified refusal, tied to the original operation",
            "existing_approaches": "Temporal durable execution, server idempotency, MCP task reads, manual reconciliation and UndoBench recovery evaluation",
            "remaining_gap": "AGI ALPHA preserves uncertain attempts but has no finite information instrument to state which permitted read could distinguish their effects. This is a source-inspected integration gap, not a claim that recovery is unexplored.",
            "why_now": "The existing general executor supplies immutable action receipts and no-replay behavior; current task protocols separate cancellation signals from observed effect state",
            "construction": "An immutable observation contract, finite ambiguity partition and verifiable request for a distinguishing read",
            "decisive_experiment": "Hold purpose, possible states and tools fixed; compare log-only inspection, direct audit reconciliation and the constructed instrument. Include unavailable, changed-scope and unexpected evidence.",
            "commercial_mechanism": "A bounded integration/diagnosis service or pooled adapter commissioning; no buyer, price, agreement or willingness to pay observed",
            "falsifier": "A claimed resolved state is compatible with another material effect, requires undeclared evidence, changes purpose, or costs more than an available direct audit",
            "decision": "prototype internally; stop commercial offering pending real audit coverage and demand evidence",
            "evidence": [
                "alpha_factory_v1/core/runtime/successor/flywheel_execution.py",
                "tests/runtime/test_flywheel_execution.py",
                "https://docs.temporal.io/develop/python/integrations/mcp",
                "https://modelcontextprotocol.io/seps/2663-tasks-extension",
                "https://arxiv.org/abs/2610.05622",
            ],
        },
        {
            "id": "scientific-response-instrument",
            "title_en": "Construct a scientific response instrument",
            "title_fr": "Construire un instrument de réponse scientifique",
            "beneficiary": "Researchers facing repeated inverse-design questions",
            "useful_outcome": "A checked compound design under a strict simulator budget",
            "existing_approaches": "Direct search, response representations and the active capability-opportunity study #4970",
            "remaining_gap": "External recipient usefulness and advantage beyond stronger budgets remain unestablished in the published study",
            "why_now": "Actual reusable learned arrays and preserved fresh-study evidence now exist",
            "construction": "Task-specific response composition and fresh acceptance bridge",
            "decisive_experiment": "Test a real independently specified task against direct methods with identical simulator access",
            "commercial_mechanism": "Commissioned design assessment; value and price unknown",
            "falsifier": "The direct method matches the outcome after all adaptation and verification costs",
            "decision": "defer to existing research owner; do not duplicate its construction",
            "evidence": ["https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4970"],
        },
        {
            "id": "shared-resilience-planning",
            "title_en": "Pool resilience planning",
            "title_fr": "Mutualiser la planification de résilience",
            "beneficiary": "Independent critical-service operators",
            "useful_outcome": "Accepted resilience plans with customer-specific requirements",
            "existing_approaches": "Established optimization and REopt; the preserved microgrid fixture supplies its formulation",
            "remaining_gap": "No independent unmet requirement or new capability advantage has been established by this fixture",
            "why_now": "No demonstrated new feasibility-changing condition in this implementation",
            "construction": "Shared modeling/checking and conditional commissioning",
            "decisive_experiment": "First establish a real unresolved need with the competent conventional method available",
            "commercial_mechanism": "Conditional pooled demand; entirely hypothetical",
            "falsifier": "Existing tools already meet the beneficiary's requirements economically",
            "decision": "retain as historical regression; do not select as flagship",
            "evidence": [
                "https://github.com/NREL/REopt_API",
                "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6446765830",
            ],
        },
    ]


def record() -> dict[str, Any]:
    ordinary = episode(problem("fresh-upload-001"), "applied")
    partial = episode(problem("fresh-reservation-002"), "partially-applied")
    unavailable = episode(problem("audit-unavailable-003", distinguishable=False), "audit-unavailable")
    out_of_model = episode(problem("unexpected-state-004"), "unknown-server-state")
    with tempfile.TemporaryDirectory(prefix="opportunity-recipient-") as directory:
        source, target = Path(directory) / "input.json", Path(directory) / "output.json"
        source.write_bytes(canonical(partial))
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--recipient", str(source), "--output", str(target)],
            check=True,
            cwd=ROOT,
            timeout=30,
            capture_output=True,
        )
        transferred = safe_json_loads(target.read_bytes())
    if transferred["report"] != partial["after"] or not transferred["verified"]:
        raise RuntimeError("recipient must independently check the unfamiliar mission")
    closure = [
        "alpha_factory_v1/core/runtime/successor/flywheel_probe.py",
        "scripts/record_opportunity_probe.py",
    ]
    return {
        "schema": "flywheel-opportunity-probe-evidence/v1",
        "selection": {
            "candidate": "uncertain-effect-information-instrument",
            "basis": "Current executor refuses uncertain effects; a read-only evidence bridge is missing locally",
            "purpose": "Help an operator identify an interrupted action's original effect without replaying it",
            "novelty_scope": "New integration experiment for this recipient; no new recovery algorithm claimed",
            "status": "bounded internal prototype; external need, model advantage and demand unqualified",
        },
        "candidate_dossier": candidate_dossier(),
        "episodes": {
            "audit_available": ordinary,
            "different_recipient_mission": partial,
            "audit_unavailable": unavailable,
            "outside_declared_model": out_of_model,
        },
        "recipient": transferred,
        "comparisons": {
            "log_only": "All three effects have identical client logs; no defensible effect classification",
            "strong_direct_audit": "Matches the instrument's classification with the identical snapshot and full costs unknown",
            "identical_content_library": "Same instrument bytes and permissions; identical result, no graph-specific premium",
            "operational_alpha": "No H/U/E/E+ frontier trials; no expert-use or new-learning advantage measured",
        },
        "commercial_decision": "hold; no actual buyer evidence, complete monetary cost or verified live coverage",
        "scope": {
            "computation": "executed-local",
            "states": "synthetic",
            "needs": "internal-source-inspected gap",
            "frontier_model_calls": 0,
            "live_ens_authentication": False,
            "actual_collections_micro_usd": 0,
            "complete_actual_cost": "unknown",
            "authority_granted": False,
        },
        "sources": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in closure},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recipient", type=Path)
    args = parser.parse_args()
    value = recipient(safe_json_loads(args.recipient.read_bytes())) if args.recipient else record()
    with args.output.open("xb") as stream:
        stream.write(canonical(value) + b"\n")
