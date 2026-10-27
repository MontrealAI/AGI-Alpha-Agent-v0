# SPDX-License-Identifier: Apache-2.0
"""Execute connected enterprise conformance without production accounts or sales."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import Enterprise, key
from alpha_factory_v1.core.runtime.successor.flywheel_gym import GymTask, evaluate_frozen
from alpha_factory_v1.core.runtime.successor.flywheel_specialists import PlacementInvocation, PlacementWorkflow
from alpha_factory_v1.core.runtime.successor.flywheel_experiments import verify_placement
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest
from scripts.record_specialist_relay import run_arm


def record() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests/runtime"))
    import test_flywheel_enterprise as e
    import test_flywheel_protected as f
    import test_flywheel_specialists as s

    with tempfile.TemporaryDirectory(prefix="enterprise-fictional-conformance-") as temporary:
        state = f.setup.__wrapped__(Path(temporary))
        enterprise = Enterprise(state["service"])
        origin = e.launch(state)
        original_offering = enterprise.inspect("offering", "resilient-placement")
        prototype = e.advance(state, "prototype")
        e.accept(state, origin)
        technical = e.advance(state, "technically-qualified")
        commercial = e.advance(state, "commercially-assessed", e.commercial(state))
        state["service"].configure(
            f.signed(
                state,
                "configure",
                "controller",
                {"beta_digest": f.BETA, "policy_digest": f.POLICY},
                "configure-placement",
            )
        )
        frozen = s.campaign(state)
        if frozen["candidate"] is None:
            raise RuntimeError("No candidate; preserve failed campaign before another attempt")
        workflow = PlacementWorkflow.model_validate(frozen["candidate"])
        tasks = [
            GymTask(
                task_id=f"enterprise-fresh-{seed}",
                partition="protected-evaluation",
                family="changed-topology-and-contention",
                problem=s.problem(seed, hosts=5, services=5, tight=True),
            )
            for seed in range(2810, 2822)
        ]
        fresh = evaluate_frozen(frozen, tasks)
        s.seal(state, "placement-extra-rd", "C")
        ident = s.retain(state, origin, workflow, "placement-gym")
        admission = s.assess(state, ident)
        assert admission == "rejected"
        entry = state["service"].library.snapshot()["protected_network_v1"]["entries"][ident]
        hold = e.decision(state, "no-further-investment", benefit=0)
        adjacent_spec = e.offering(state, "disruption-aware-rollout").model_copy(
            update={
                "useful_outcome": "Prototype a rollout planning service with correlated-disruption checks",
                "required_capabilities": [ident],
                "parent_offering": e.evidence(state, key("offering", "resilient-placement")),
                "scope": "Adjacent research hypothesis; no customer demand or production deployment established",
            }
        )
        adjacent = e.register(state, adjacent_spec)
        composition = []
        for task in tasks[:4]:
            conventional = PlacementWorkflow(version=1, order="largest-demand", bound="residual", capacity_pruning=True)
            composition.append(
                {
                    "task": task.model_dump(),
                    "general_procedure": run_arm(task, PlacementWorkflow(version=1)),
                    "ordering_alone": run_arm(task, PlacementWorkflow(version=2, order=workflow.order)),
                    "pruning_alone": run_arm(
                        task,
                        PlacementWorkflow(version=2, bound=workflow.bound, capacity_pruning=workflow.capacity_pruning),
                    ),
                    "composed": run_arm(task, workflow, 64),
                    "strong_conventional": run_arm(task, conventional),
                    "private": run_arm(task, workflow),
                    "shared_same_contents": run_arm(task, workflow),
                    "ordinary_library_same_contents": run_arm(task, workflow),
                }
            )
        state["journal"].verify()
        technical_path = {
            "offering": original_offering,
            "decision": enterprise.inspect("decision", "first-decision"),
            "launch": enterprise.inspect("launch", "placement-origin"),
            "execution": origin,
            "artifact": origin["result"]["artifacts"][0],
            "prototype": prototype,
            "technical_qualification": technical,
            "commercial_assessment": commercial,
            "gym": frozen,
            "capability_digest": ident,
            "manifest": entry["manifest"],
            "admission": admission,
            "admission_decision": entry["decision"],
            "fresh_evaluation": fresh,
            "composition": composition,
            "next_decision": hold,
            "adjacent_offering": adjacent,
            "accounting_fictional": state["costs"].report(),
        }

    with tempfile.TemporaryDirectory(prefix="enterprise-positive-fictional-protocol-") as temporary:
        state = f.setup.__wrapped__(Path(temporary))
        origin = e.launch(state)
        e.accept(state, origin)
        state["service"].configure(
            f.signed(
                state,
                "configure",
                "controller",
                {"beta_digest": f.BETA, "policy_digest": f.POLICY},
                "configure-placement",
            )
        )
        gym = s.campaign(state)
        workflow = PlacementWorkflow.model_validate(gym["candidate"])
        s.seal(state, "placement-extra-rd", "C")
        ident = s.retain(state, origin, workflow, "placement-gym")
        assert s.assess(state, ident, synthetic_saving=20) == "assessed"
        f.control(state, ident, "validate")
        f.control(state, ident, "admit")
        invocation = PlacementInvocation(
            mission_id="enterprise-fictional-peer-fresh",
            problem=s.problem(2910, hosts=5, services=5),
            beta_digest=f.BETA,
            policy_digest=f.POLICY,
            recipient_capabilities_digest=f.ZERO,
            prerequisite_digests=[],
            logical_limit=100_000,
            cost_cap_micro_usd=100,
        )
        receipt = state["service"].invoke(
            ident, invocation, f.proof(state, ident, "invoke", digest("flywheel-invocation", invocation))
        )
        peer = {
            "scope": "FICTIONAL authority and economics; actual cryptography, protected loading and computation",
            "live_qualified": False,
            "actual_frontier_calls": 0,
            "origin_execution_digest": origin["digest"],
            "capability_digest": ident,
            "invocation": receipt,
            "independent_finite_check": verify_placement(invocation.problem, receipt["result"]),
        }
        state["journal"].verify()

    paths = sorted((root / "alpha_factory_v1/core/runtime").rglob("*.py")) + [
        Path(__file__).resolve(),
        root / "scripts/record_specialist_relay.py",
        root / "scripts/record_general_flywheel.py",
        root / "tests/runtime/test_flywheel_enterprise.py",
        root / "tests/runtime/test_flywheel_protected.py",
        root / "tests/runtime/test_flywheel_specialists.py",
    ]
    return {
        "schema_name": "enterprise-flywheel-evidence/v1",
        "author": {"name": "Vincent Boucher", "title": "President of MONTREAL.AI"},
        "sources": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "components": {
            "orchestration": "executed-local",
            "learning": "executed-workflow-search",
            "model": "scripted-protocol-fixture",
            "identity": "fictional-RPC-real-signatures",
            "market": "unmeasured",
            "accounting": "fictional-attestations",
        },
        "technical_path": technical_path,
        "positive_protocol_only": peer,
        "summary": {
            "useful_finite_delivery": True,
            "training_completed": True,
            "fresh_cases": len(fresh["cases"]),
            "technical_transfer_passed": fresh["technical_transfer_passed"],
            "actual_admission": "rejected",
            "commercial_authorization": False,
            "next_selected_action": "hold",
            "adjacent_offering_stage": "hypothesis",
            "net_alpha_positive": False,
            "sharing_worthwhile": "unmeasured",
            "growing_advantage": False,
            "live_qualified": False,
            "actual_frontier_calls": 0,
            "actual_customer_collections_micro_usd": 0,
            "complete_actual_cost": "unknown",
            "actual_profit": "not established",
            "human_reference": "Illustrative 40 team hours at USD 100/hour; not observed market pricing",
            "causal_limit": "Strong conventional and identical-content controls tie v2; composition adds work",
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("preserve the original report; choose a new output")
    value = record()
    with args.output.open("xb") as stream:
        stream.write(canonical(value) + b"\n")
