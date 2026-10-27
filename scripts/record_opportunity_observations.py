# SPDX-License-Identifier: Apache-2.0
"""Execute and retain the bounded observation pilot on native discovery records."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Literal

from alpha_factory_v1.core.runtime.successor.flywheel_discovery import (
    Discovery,
    DiscoveryDecision,
    ExperimentObservation,
    ExperimentStep,
    ExplorationBundle,
    Formulation,
    Ingredient,
    Need,
    Opportunity,
    Purpose,
    TransformationWitness,
)
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import EvidenceRef
from scripts.record_workflow_discovery import _append, _apply
from alpha_factory_v1.core.runtime.successor.flywheel_execution import (
    ExecutionMission,
    ExecutionPermit,
    ExecutionProfile,
    MissionExecutor,
    operation_key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, Charge
from alpha_factory_v1.core.runtime.successor.flywheel_observations import (
    ObservationPlan,
    ObservationProblem,
    Probe,
    World,
    compile_observations,
    interpret_observations,
)
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples/opportunity-discovery"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def problem(mission: str, expected: bytes, purpose_digest: str) -> ObservationProblem:
    data = {
        "absent": None,
        "correct": expected,
        "corrupt": bytes([expected[0] ^ 1]) + expected[1:],
        "partial": expected[:5],
    }
    return ObservationProblem(
        mission_id=mission,
        purpose_digest=purpose_digest,
        environment_digest=digest("local-read-fixture", {"mission": mission, "expected": sha(expected)}),
        worlds=[
            World(world_id=name, outcome_satisfied=name == "correct", meaning="Authored " + name + " artifact state")
            for name in data
        ],
        probes=[
            Probe(
                probe_id="exists",
                resource_units=1,
                semantics="Whether the requested file exists",
                outcomes={name: "absent" if value is None else "present" for name, value in data.items()},
            ),
            Probe(
                probe_id="length",
                resource_units=2,
                semantics="Length of this bounded file or absence",
                outcomes={name: "absent" if value is None else str(len(value)) for name, value in data.items()},
            ),
            Probe(
                probe_id="digest",
                resource_units=3,
                semantics="SHA256 of this bounded file or absence",
                outcomes={name: "absent" if value is None else sha(value) for name, value in data.items()},
            ),
        ],
        max_resource_units=4,
        coverage_limitations="Only four authored local states; no concurrency, remote completeness, "
        "causation, billing or retry permission",
    )


def execute_family(
    mission: str, expected: bytes, purpose_digest: str, directory: Path, recipient: bool
) -> dict[str, Any]:
    instance = problem(mission, expected, purpose_digest)
    if recipient:
        invoked = subprocess.run(
            [sys.executable, str(FIXTURES / "recipient.py")],
            input=canonical(instance),
            capture_output=True,
            check=True,
            timeout=30,
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        invocation = json.loads(invoked.stdout)
        plan = ObservationPlan.model_validate(invocation["plan"])
    else:
        plan = compile_observations(instance)
        invocation = {"process_id": os.getpid(), "identity_basis": "local donor fixture"}
    target = directory / (mission + ".artifact")
    effect = subprocess.run(
        [sys.executable, str(FIXTURES / "write_before_ack.py")],
        input=json.dumps({"output": str(target), "content": expected.decode()}).encode(),
        capture_output=True,
        check=False,
        timeout=30,
        cwd=ROOT,
    )
    if effect.returncode != 23 or effect.stdout or target.read_bytes() != expected:
        raise RuntimeError("lost-acknowledgement fixture did not produce the required actual state")
    cases = []
    for name, data in {
        "correct": target.read_bytes(),
        "absent": None,
        "corrupt": bytes([expected[0] ^ 1]) + expected[1:],
        "partial": expected[:5],
    }.items():
        available = {
            "exists": "absent" if data is None else "present",
            "length": "absent" if data is None else str(len(data)),
            "digest": "absent" if data is None else sha(data),
        }
        observed = {probe: available[probe] for probe in plan.probes}
        finding = interpret_observations(instance, plan, observed)
        independent_acceptance = data == expected
        if (finding.outcome == "satisfied-in-model") != independent_acceptance or finding.authority:
            raise RuntimeError("purpose bridge or no-authority invariant failed")
        cases.append(
            {
                "state": name,
                "observations": observed,
                "finding": finding.model_dump(),
                "independent_byte_acceptance": independent_acceptance,
                "direct_conventional_control": independent_acceptance,
                "identical_content_library_control": finding.outcome,
                "transport_acknowledgement": "missing",
                "write_retried": False,
            }
        )
    return {
        "mission": mission,
        "problem": instance.model_dump(),
        "plan": plan.model_dump(),
        "invocation": invocation,
        "child_exit": effect.returncode,
        "child_acknowledgement_bytes": len(effect.stdout),
        "actual_write_attempts": 1,
        "artifact_sha256": sha(target.read_bytes()),
        "expected_sha256": sha(expected),
        "cases": cases,
        "baseline_limit": "Acknowledgement-only observations cannot distinguish the actual effect; "
        "competent byte checks tie",
    }


class LocalObservationTool:
    component: Literal["executed-local"] = "executed-local"

    def __init__(self, directory: Path, purpose_digest: str) -> None:
        self.directory, self.purpose_digest = directory, purpose_digest
        self.results: list[dict[str, Any]] = []
        self.identity = {
            "tool": "authored-local-observation-pilot/v1",
            "source_sha256": sha(Path(__file__).read_bytes()),
            "scope": "Two authored local effects only; no host-code or remote tool interface",
        }

    def perform(self, name: str, arguments: dict[str, Any], active: Callable[[], bool]) -> dict[str, Any]:
        if name != "observation_pilot" or arguments or not active() or self.results:
            raise ValueError("only the single predeclared authored local pilot is permitted")
        self.results = [
            execute_family(
                "donor-source-export",
                b'{"source":"public","claim":"scope-bound","version":1}\n',
                self.purpose_digest,
                self.directory,
                False,
            ),
            execute_family(
                "recipient-csv-ledger",
                b"mission,status,amount\nfresh,unpaid,0\n",
                digest("recipient-purpose", {"outcome": "Exact CSV ledger; no payment claim"}),
                self.directory,
                True,
            ),
        ]
        if not active():
            raise InterruptedError("pilot stopped; inspect completed effects before any action")
        return {"families": self.results, "scope": "Actual local effects and finite checks; no customer acceptance"}


class ScriptedObservationModel:
    component: Literal["simulated"] = "simulated"

    def __init__(self) -> None:
        self.turn = 0

    def respond(self, payload: dict[str, Any], active: Callable[[], bool], remaining: float) -> dict[str, Any]:
        if not active() or remaining <= 0:
            raise InterruptedError("scripted protocol fixture stopped")
        self.turn += 1
        result = None if self.turn == 1 else json.loads(payload["input"][-1]["output"])
        output: list[dict[str, Any]] = (
            [{"type": "function_call", "name": "observation_pilot", "call_id": "pilot-1", "arguments": "{}"}]
            if self.turn == 1
            else [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "deliverable": result,
                                    "verification": {
                                        "scope": "Inspect the independent byte checks outside this scripted response"
                                    },
                                    "limitations": ["Scripted model; local effects; no customer acceptance"],
                                    "artifacts": [
                                        {
                                            "kind": "actual-tool-observations",
                                            "digest": digest("observation-artifacts", result),
                                        }
                                    ],
                                }
                            ),
                        }
                    ],
                }
            ]
        )
        return {
            "id": f"fixture-observation-{self.turn}",
            "model": "scripted-observation-protocol-fixture/v1",
            "status": "completed",
            "output": output,
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }


def record() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "tests/runtime"))
    import test_flywheel_protected as fixture
    from alpha_factory_v1.core.runtime.successor import flywheel_observations as retained
    from scripts.observation_economics import sensitivity

    source = Path(retained.__file__)
    artifact_hash = sha(source.read_bytes())
    dossier = json.loads((FIXTURES / "dossier.json").read_bytes())
    protocol = json.loads((FIXTURES / "PILOT_PROTOCOL.json").read_bytes())
    freeze = {
        "dossier": sha((FIXTURES / "dossier.json").read_bytes()),
        "protocol": sha((FIXTURES / "PILOT_PROTOCOL.json").read_bytes()),
        "retained_artifact": artifact_hash,
    }
    with tempfile.TemporaryDirectory(prefix="observation-pilot-native-discovery-") as temporary:
        directory = Path(temporary)
        state = fixture.setup.__wrapped__(directory)
        register = _append(
            state,
            "@observation-design-source-register",
            {
                "dossier": dossier,
                "protocol": protocol,
                "freeze_before_pilot": freeze,
                "basis": "Fetched primary documentation and authored research protocol; no observed buyer demand",
            },
        )
        purpose = Purpose(
            useful_purpose=protocol["purpose"],
            deliverable="Actual local artifacts, read observations and independent byte checks",
            acceptance_criteria=["Exact requested bytes", "No duplicate write", "Unknown outcomes retain HOLD"],
            input_semantics="Authored finite artifact states; not an external service observation",
            output_semantics="Current exact-byte checks; no billing, acceptance or retry authority",
            scope="Bounded local engineering pilot; no real customer, market, concurrent writer or physical process",
        )
        opportunity = Opportunity(
            opportunity_id="mission-outcome-observation",
            version=1,
            purpose=purpose,
            needs=[
                Need(
                    need_id="ambiguous-completion",
                    beneficiary="Internal artifact consumer",
                    independently_motivated_purpose=(
                        "Determine whether the original outcome occurred " "without duplicating an effect"
                    ),
                    outside_option="Use native idempotency or direct competent byte checks first",
                    evidence=[register],
                    evidence_kind="published",
                    demand_uncertainty="Public documentation supports the failure mode; no actual buyer or price is "
                    "established",
                )
            ],
            limiting_assumptions=["An acknowledgement alone identifies useful completion"],
            shared_structure_hypothesis="Different artifact families can share a purpose-bound observation constructor",
            formulations=[
                Formulation(
                    formulation_id=row["candidate_id"],
                    approach=row["required_construction"],
                    material_difference=row["consequential_gap"],
                    assumptions=["Keep the original required outcome"],
                    dependencies=["supplied-model", "ordinary-search"],
                    uncertainty="; ".join(row["uncertainties"]),
                )
                for row in dossier["candidates"]
            ],
            ingredients=[
                Ingredient(
                    ingredient_id="supplied-model",
                    description="Researcher-authored states, read semantics and local tools",
                    origin="supplied",
                    evidence=[register],
                    limitations="Finite coverage; no autonomous discovery claim",
                ),
                Ingredient(
                    ingredient_id="ordinary-search",
                    description="Exact distinguishing-set enumeration and byte checks",
                    origin="established-method",
                    evidence=[register],
                    limitations="No new algorithm or advantage over equal-content experts",
                ),
            ],
            unresolved_questions=[
                "Full lifecycle cost",
                "Actual buyer need and willingness",
                "Competent same-model fresh comparison",
            ],
            mode="hybrid",
        )
        opportunity_record = _apply(state, "opportunity", "observation-opportunity", opportunity)
        selected = next(row for row in dossier["candidates"] if row["candidate_id"] == dossier["selection"])
        witness = TransformationWitness(
            witness_id="observation-information-bridge",
            opportunity_id=opportunity.opportunity_id,
            opportunity_spec_digest=digest("discovery-opportunity", opportunity),
            purpose=purpose,
            binding_restriction=selected["restriction"],
            removable_basis="Permitted exact artifact reads distinguish some otherwise identical "
            "acknowledgement states",
            change_kind="information",
            replacement="Construct a finite purpose-bound read plan; preserve ambiguity and grant no authority",
            operation_in_original_setting="Execute one authored local effect, inspect actual bytes after lost "
            "acknowledgement, keep unchanged acceptance",
            falsifying_observation=selected["falsifier"],
            formulation_id="observation-design",
            evidence=[register],
            limitations="Worlds and code supplied by researcher; only the probe subset is constructed. "
            "Strong conventional checks may tie.",
        )
        witness_record = _apply(state, "witness", "observation-witness", witness)
        tool = LocalObservationTool(directory, digest("discovery-purpose", purpose))
        mission = ExecutionMission(
            mission_id="observation-research",
            beneficiary="Internal artifact consumer",
            goal=purpose.useful_purpose,
            challenged_assumption=witness.binding_restriction,
            deliverable=purpose.deliverable,
            acceptance_criteria=purpose.acceptance_criteria,
            inputs={
                "frozen_opportunity": opportunity_record["digest"],
                "witness": witness_record["digest"],
                "freeze": freeze,
            },
            sharing_rights="Authored public fixtures only",
            stop_conditions=["No write retry; preserve uncertainty"],
            mode="hybrid",
            max_turns=3,
            max_actions=1,
            max_seconds=120,
            components={
                "model": "simulated",
                "tools": "executed-local",
                "identity": "simulated",
                "acceptance": "executed-local",
                "market": "unqualified",
            },
        )
        profile = ExecutionProfile(
            model_id="scripted-observation-protocol-fixture/v1",
            reasoning_effort="high",
            supported_efforts=["high"],
            qualification_digest=digest("observation-fixture-profile", freeze),
            tools=[
                {
                    "type": "function",
                    "name": "observation_pilot",
                    "description": "Execute the single authored local pilot",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                    "strict": True,
                }
            ],
        )
        operation = "observation-pilot-execution"
        bundle = ExplorationBundle(
            bundle_id="observation-local-construction",
            witness_id=witness.witness_id,
            witness_spec_digest=digest("discovery-witness", witness),
            steps=[
                ExperimentStep(
                    step_id="construct-and-check",
                    question="Do permitted observations preserve exact original artifact acceptance after an"
                    " ambiguous result?",
                    proposed_artifact="Actual JSON and CSV artifacts; exact retained compiler in a fresh local process",
                    decisive_check="Unchanged byte acceptance; competent direct checker and identical-content library",
                    falsifying_observation=witness.falsifying_observation,
                    cost_bucket="C",
                    cost_cap_micro_usd=1000,
                    seconds_cap=120,
                    execution_request_digest=digest("flywheel-execution-request", mission),
                )
            ],
            total_cost_cap_micro_usd=1000,
            total_seconds_cap=120,
            checkpoint_after=["construct-and-check"],
            stopping_conditions=[
                "Unknown full costs prevent admission",
                "Competent conventional parity stops the stronger Alpha claim",
            ],
            joint_value_hypothesis="Observation construction and fresh meaning checks may equip later missions",
            uncertainty="A fictional conformance ceiling is not spending permission or a measured cost",
        )
        planned = _apply(state, "bundle", "observation-bundle", bundle)
        fixture.account(
            state,
            "capital",
            {
                "record_id": "fictional-research-funding",
                "mission_id": mission.mission_id,
                "amount_micro_usd": 1000,
                "evidence_digest": digest("fictional-funding", {"real": False}),
            },
            "fictional-pilot-funding",
        )
        permit = ExecutionPermit(
            operation_id=operation,
            request_digest=digest("flywheel-execution-request", mission),
            profile_digest=digest("flywheel-execution-profile", profile),
            environment_digest=digest("flywheel-execution-environment-contract", tool.identity),
            config_digest=sha(canonical(state["journal"].config.model_dump())),
            quota_evidence_digest=profile.qualification_digest,
            pricing_evidence_digest=digest("no-provider", {"calls": 0}),
            max_authorized_micro_usd=1000,
            expires_at=int(time.time()) + 600,
            bucket="C",
        )
        signed = sign_record(
            state["keys"]["controller"],
            "controller",
            "flywheel-execution-permit",
            {"journal_identity": state["journal"].identity, "permit": permit.model_dump()},
        )

        def qualified() -> None:
            if state["service"]._execution_binding() != state["service"].execution_digest:
                raise ValueError("runtime or custody changed during the local pilot")

        started = time.monotonic()
        execution = MissionExecutor(
            state["journal"],
            state["trust"],
            state["costs"],
            ScriptedObservationModel(),
            tool,
            qualification_check=qualified,
        ).run(mission, profile, signed)
        execution = state["journal"].latest(operation_key(operation))
        elapsed = max(math.ceil(time.monotonic() - started), math.ceil(execution.get("elapsed_ms", 0) / 1000))
        if execution["status"] != "delivered-awaiting-independent-acceptance-and-costs" or len(tool.results) != 2:
            raise RuntimeError("existing executor did not complete the authored pilot: " + execution["status"])
        families = tool.results
        if (
            families[1]["invocation"]["retained_source_sha256"] != artifact_hash
            or sha(source.read_bytes()) != artifact_hash
        ):
            raise RuntimeError("recipient did not use the exact retained compiler")
        execution_ref = EvidenceRef(journal_key=operation_key(operation), record_digest=execution["digest"])
        for category in sorted(CATEGORIES):
            charge = Charge.model_validate(
                dict(
                    activity_id="observation-research-" + category,
                    mission_id=operation,
                    bucket="C",
                    category=category,
                    accrued_micro_usd=None,
                    paid_micro_usd=0,
                    basis="unknown",
                    evidence_digest=execution["digest"],
                    note="All engineering attempts, provider, customer and maintenance monetary "
                    "allocations remain unknown; no paid infrastructure purchase.",
                )
            )
            fixture.account(state, "charge", charge.model_dump(), "observation-cost-" + category)
        observed = _apply(
            state,
            "observe",
            "observation-native-outcome",
            ExperimentObservation(
                bundle_id=bundle.bundle_id,
                step_id="construct-and-check",
                interpretation="inconclusive",
                observation="Two actual local effects and eight finite state checks pass; conventional and "
                "ordinary-library controls tie",
                evidence=[register, execution_ref],
                artifact=execution_ref,
                cost_operation=operation,
                elapsed_seconds=elapsed,
                execution_operation=operation,
                acceptance="not-claimed",
                limitations="Byte checks are local research checks; no customer acceptance, real provider, "
                "ENS identity or complete cost",
            ),
            planned["digest"],
        )
        decision = _apply(
            state,
            "decision",
            "observation-stop",
            DiscoveryDecision(
                opportunity_id=opportunity.opportunity_id,
                opportunity_spec_digest=digest("discovery-opportunity", opportunity),
                disposition="stop",
                rationale="Keep the useful instrument; stop additional-Alpha and commercial expansion "
                "because competent controls tie and economics are unknown",
                evidence=[register, execution_ref],
                uncertainty="Finite supplied worlds; no actual demand or complete monetary accounting",
                next_question="Measure an independently valuable recipient use and full costs before any "
                "separate admission",
            ),
        )
        economics = sensitivity(register)
        accounting = state["costs"].report(operation)
        verified = state["journal"].verify()
        identity = state["journal"].identity
    paths = [
        source,
        Path(__file__),
        ROOT / "scripts/observation_economics.py",
        ROOT / "scripts/record_workflow_discovery.py",
        FIXTURES / "recipient.py",
        FIXTURES / "write_before_ack.py",
        FIXTURES / "dossier.json",
        FIXTURES / "PILOT_PROTOCOL.json",
        ROOT / "tests/runtime/test_flywheel_protected.py",
    ] + sorted((ROOT / "alpha_factory_v1/core/runtime").rglob("*.py"))
    return {
        "schema": "opportunity-observation-evidence/v1",
        "author": "Vincent Boucher — President of MONTREAL.AI",
        "mode": "hybrid",
        "sources": {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in paths},
        "freeze_before_pilot": freeze,
        "parent_runtime": "03b2eb97f1e150956ef0fa028e1ad665cc755cf6",
        "planned_head_before_effects": planned["digest"],
        "journal_identity": identity,
        "journal_verification": verified,
        "dossier": dossier,
        "families": families,
        "native_execution": execution,
        "native_opportunity": opportunity_record,
        "native_witness": witness_record,
        "native_bundle": observed,
        "native_decision": decision,
        "accounting": accounting,
        "conditional_economics": economics,
        "frontier_comparisons": {
            "H": {"status": "not-run"},
            "U": {"status": "not-run"},
            "E": {"status": "not-run"},
            "E+": {"status": "not-run"},
        },
        "components": {
            "local_effects": "executed",
            "model": "scripted-protocol-fixture-not-calibrated",
            "identity": "fictional-policy-resources",
            "market": "explicit-assumption-sensitivity",
            "billing": "unknown",
        },
        "conclusion": {
            "local_state_checks": 8,
            "actual_child_effects": 2,
            "conventional_control": "tie",
            "ordinary_library_control": "tie",
            "admission": "do not admit",
            "next_action": "stop commercial expansion; preserve engineering candidate",
            "new_market_feasible": False,
            "customer_collections_micro_usd": 0,
            "complete_actual_cost": None,
            "actual_profit": None,
            "actual_frontier_provider_calls": 0,
            "live_qualified": False,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("preserve previous evidence; select a new output")
    result = record()
    with args.output.open("xb") as output:
        output.write(canonical(result) + b"\n")
