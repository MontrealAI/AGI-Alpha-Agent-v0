# SPDX-License-Identifier: Apache-2.0
"""Execute a research-only discovery custody journey using the actual native service.

Ephemeral local roles bind this rehearsal only. Refusing RPC readers make all
chain requests fail; no production identity, provider, payment or claim is made.
Private runtime state is written only under the explicitly supplied local path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.flywheel_access import (
    ENSAuthority,
    ENSPins,
    ResourceAccess,
    ServiceIdentity,
)
from alpha_factory_v1.core.runtime.successor.flywheel_capsules import ProtectedLibrary
from alpha_factory_v1.core.runtime.successor.flywheel_checkpoint import DurableCheckpoint
from alpha_factory_v1.core.runtime.successor.flywheel_costs import CostLedger
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import Discovery, DiscoveryCommand
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.transformation_library import TransformationLibrary
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record
from discovery_means import instrument
from discovery_means.cli import read_bounded


class RefusingRPC:
    """Count and refuse any attempted network action in this local rehearsal."""

    def __init__(self) -> None:
        self.calls = 0

    def call(self, method: str, params: list[Any]) -> Any:
        self.calls += 1
        raise RuntimeError("No chain access is authorized or implemented in this research rehearsal")


def run(problem: dict[str, Any], private_directory: Path) -> dict[str, Any]:
    """Run instrument, bind its evidence, and submit native discovery transitions."""
    if private_directory.exists():
        raise ValueError("Use a fresh private directory; prior runtime records are preserved")
    private_directory.mkdir(mode=0o700, parents=True)
    p = instrument.validate(problem)
    started = time.monotonic()
    report = instrument.solve(p)
    verified = instrument.verify(p, report)
    if not verified["accepted_policy"]:
        raise ValueError("This example journey requires an independently traversable successful policy")
    elapsed = max(1, int(time.monotonic() - started) + 1)
    roles = {"research-controller": {"controller"}, "research-producer": {"producer"}}
    keys = {name: Ed25519PrivateKey.generate() for name in roles}
    trust = TrustRegistry(
        {
            name: TrustAnchor(
                key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset(roles[name])
            )
            for name, key in keys.items()
        }
    )
    journal = Journal.initialize(private_directory / "runtime")
    costs = CostLedger(journal, trust)
    readers = (RefusingRPC(), RefusingRPC())
    sentinel = digest("research-unconfigured-ens", {"configured": False})
    authority = ENSAuthority(
        readers, ENSPins(registry_sha256=sentinel, wrapper_sha256=sentinel, registrar_sha256=sentinel)
    )
    access = ResourceAccess(journal, ServiceIdentity(origin="https://research-only.invalid"), authority)
    library = TransformationLibrary(journal, trust, producer="research-producer")
    checkpoint = DurableCheckpoint.initialize(private_directory / "separate-custody.sqlite3", journal)
    service = ProtectedLibrary(
        library, costs, access, {"ephemeral-research": secrets.token_bytes(32)}, "ephemeral-research", checkpoint
    )
    discovery = Discovery(service)
    source_hash = hashlib.sha256(Path(str(instrument.__file__)).read_bytes()).hexdigest()
    with journal.transaction() as cx:
        service._state(cx)
        artifact = journal.append(
            cx,
            "@adaptive-research-artifact",
            {
                "kind": "actual-locally-executed-finite-instrument",
                "source_sha256": source_hash,
                "problem": p,
                "construction": report,
                "verification": verified,
                "physical_adequacy": False,
                "customer_acceptance": False,
                "full_costs_known": False,
            },
        )
        checkpoint.advance(journal, cx)
    ref = {"journal_key": "@adaptive-research-artifact", "record_digest": artifact["digest"]}
    purpose = {
        "useful_purpose": "Resolve finite models with observation-conditioned permitted experiments",
        "deliverable": "A source-bound checked policy and its finite assumptions",
        "acceptance_criteria": ["Every policy branch ends in one hypothesis within the supplied caps"],
        "input_semantics": "Finite set-valued observations, abstract costs and allowed flags",
        "output_semantics": "Conditional policy; no actual experiment authority",
        "scope": "Computational instrument study with authored finite models",
    }
    opportunity = {
        "opportunity_id": "adaptive-research",
        "version": 1,
        "purpose": purpose,
        "needs": [
            {
                "need_id": "research-need",
                "beneficiary": "Research user",
                "independently_motivated_purpose": "Inspect the cost of conditioning on observations",
                "outside_option": "Established adaptive diagnosis and static set cover",
                "evidence": [ref],
                "evidence_kind": "internal-research",
                "demand_uncertainty": "No observed customer demand",
            }
        ],
        "limiting_assumptions": ["Supplied hypotheses and observation sets need external validation"],
        "shared_structure_hypothesis": "Set-valued observations constrain allowable next tests",
        "formulations": [
            {
                "formulation_id": identity,
                "approach": approach,
                "material_difference": difference,
                "assumptions": ["Finite validated inputs"],
                "dependencies": ["exact-search"],
                "uncertainty": "Conventional methods may tie",
            }
            for identity, approach, difference in (
                ("adaptive", "Contingent policy", "Select after observed evidence"),
                ("static", "Fixed portfolio", "Commit all probes before evidence"),
            )
        ],
        "ingredients": [
            {
                "ingredient_id": "exact-search",
                "description": "Known finite dynamic programming",
                "origin": "established-method",
                "evidence": [ref],
                "limitations": "Exponential finite state space",
            }
        ],
        "unresolved_questions": ["Can real independently grounded investigations benefit after full costs?"],
        "mode": "simulation",
    }

    def signed(
        action: Literal["opportunity", "witness", "bundle", "observe"],
        record: dict[str, Any],
        identity: str,
        expected: str | None = None,
    ) -> Any:
        command = DiscoveryCommand(
            journal_identity=journal.identity,
            operation_id=identity,
            expires_at=int(time.time()) + 600,
            action=action,
            expected_head=expected,
            record=record,
        )
        return sign_record(keys["research-controller"], "research-controller", "flywheel-discovery-command", command)

    op = discovery.apply(signed("opportunity", opportunity, "register-opportunity"))
    witness = {
        "witness_id": "adaptive-witness",
        "opportunity_id": "adaptive-research",
        "opportunity_spec_digest": digest("discovery-opportunity", op["spec"]),
        "purpose": purpose,
        "binding_restriction": "A fixed portfolio may exceed a per-path resource allowance",
        "removable_basis": "Information can select a different later test",
        "change_kind": "experiment",
        "replacement": "Checked contingent finite policy",
        "operation_in_original_setting": "A fixed portfolio remains a competent comparator",
        "falsifying_observation": "An unresolved branch, infeasible cap, or ordinary adaptive tie",
        "formulation_id": "adaptive",
        "evidence": [ref],
        "limitations": "Known decision-tree method; finite case only, no novelty or commerce established",
    }
    wit = discovery.apply(signed("witness", witness, "register-witness"))
    bundle = {
        "bundle_id": "adaptive-bundle",
        "witness_id": "adaptive-witness",
        "witness_spec_digest": digest("discovery-witness", wit["spec"]),
        "steps": [
            {
                "step_id": "construct",
                "question": purpose["useful_purpose"],
                "dependencies": [],
                "proposed_artifact": report["problem_digest"],
                "decisive_check": "Full policy branch traversal",
                "falsifying_observation": "A branch violates its finite contract",
                "cost_bucket": "B",
                "cost_cap_micro_usd": 0,
                "seconds_cap": 60,
            }
        ],
        "total_cost_cap_micro_usd": 0,
        "total_seconds_cap": 60,
        "checkpoint_after": ["construct"],
        "stopping_conditions": ["Stop at resource cap", "Pause until unknown costs are reconciled"],
        "joint_value_hypothesis": "Conditional experiments can fit a per-path research allowance",
        "uncertainty": "All monetary resource costs remain unknown; no funding or investment is inferred",
    }
    plan = discovery.apply(signed("bundle", bundle, "register-bundle"))
    observation = {
        "bundle_id": "adaptive-bundle",
        "step_id": "construct",
        "interpretation": "supports",
        "observation": "Actual local algorithm produced the attached independently traversed policy",
        "evidence": [ref],
        "artifact": ref,
        "cost_operation": "adaptive-local-computation",
        "elapsed_seconds": elapsed,
        "execution_operation": None,
        "acceptance": "not-claimed",
        "limitations": "Native custody of local evidence; no general executor, model or physical experiment",
    }
    command = signed("observe", observation, "record-observation", plan["digest"])
    observed = discovery.apply(command)
    replay_refused = False
    try:
        discovery.apply(command)
    except Conflict:
        replay_refused = True
    inspected = discovery.inspect("bundle", "adaptive-bundle")
    if inspected["digest"] != observed["digest"]:
        raise RuntimeError("Native readback differs from the recorded transition")
    costs_report = costs.report("adaptive-local-computation")
    return {
        "scope": "actual native Discovery/ProtectedLibrary custody of locally executed instrument evidence",
        "native_general_executor_used": False,
        "integration_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_sha256": source_hash,
        "native_execution_digest": service.execution_digest,
        "record_digests": {
            "artifact": artifact["digest"],
            "opportunity": op["digest"],
            "witness": wit["digest"],
            "bundle": plan["digest"],
            "observed_bundle": observed["digest"],
        },
        "instrument_status": report["status"],
        "policy_checked": verified["accepted_policy"],
        "bundle_status": observed["status"],
        "readback_matched": True,
        "replay_refused": replay_refused,
        "ledger_bucket_complete": costs_report["bucket_complete"],
        "rpc_calls": sum(r.calls for r in readers),
        "execution_authority": observed["execution_authority"],
        "actual_customer_acceptance": False,
        "production_qualification": "BLOCKED",
        "authority_granted": observed["authority_granted"],
        "private_state_exported": False,
    }


def main() -> None:
    """Run only an explicitly requested fresh local rehearsal."""
    parser = argparse.ArgumentParser()
    parser.add_argument("problem", type=Path)
    parser.add_argument("--private-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(read_bounded(args.problem), args.private_directory)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"bundle_status": result["bundle_status"], "replay_refused": result["replay_refused"]}))


if __name__ == "__main__":
    main()
