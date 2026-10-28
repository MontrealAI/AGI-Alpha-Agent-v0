# SPDX-License-Identifier: Apache-2.0
"""Execute the specialist relay, retaining technical and fictional scopes apart.

This source-checkout recorder uses the existing synthetic conformance fixtures.
It never provisions production trust, ENS names, accounts or paid execution.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_capsules import BRANCH
from alpha_factory_v1.core.runtime.successor.flywheel_experiments import verify_placement
from alpha_factory_v1.core.runtime.successor.flywheel_gym import GymTask, evaluate_frozen
from alpha_factory_v1.core.runtime.successor.flywheel_specialists import PlacementInvocation, PlacementWorkflow
from alpha_factory_v1.core.runtime.successor.flywheel_gym import PlacementEnvironment
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest


def run_arm(task: GymTask, workflow: PlacementWorkflow, coordination: int = 0) -> dict[str, Any]:
    env = PlacementEnvironment(workflow)
    env.reset(task.model_copy(update={"logical_limit": task.logical_limit - coordination}))
    started = time.perf_counter_ns()
    env.step({"type": "run-workflow"}, lambda: True)
    result = env.outcome()
    result["elapsed_ns_including_independent_check"] = time.perf_counter_ns() - started
    result["coordination_logical_units"] = coordination
    result["total_logical_units"] = result["logical_units"] + coordination
    return result


def record() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests/runtime"))
    import test_flywheel_protected as f
    import test_flywheel_specialists as s

    with tempfile.TemporaryDirectory(prefix="specialist-relay-fictional-") as temporary:
        state = f.setup.__wrapped__(Path(temporary))
        origin = s.origin(state)
        frozen = s.campaign(state)
        if frozen["candidate"] is None:
            raise RuntimeError("campaign produced no candidate; preserve this failed run before investigating")
        workflow = PlacementWorkflow.model_validate(frozen["candidate"])
        tasks = [
            GymTask(
                task_id=f"fresh-topology-{seed}",
                partition="protected-evaluation",
                family="five-host-three-domain-topology",
                problem=s.problem(seed, hosts=5),
            )
            for seed in range(2400, 2406)
        ] + [
            GymTask(
                task_id=f"fresh-contention-{seed}",
                partition="protected-evaluation",
                family="more-services-and-tight-capacity",
                problem=s.problem(seed, services=6, tight=True),
            )
            for seed in range(2500, 2506)
        ]
        technical = evaluate_frozen(frozen, tasks)
        s.seal(state, "placement-extra-rd", "C")
        ident = s.retain(state, origin, workflow, "placement-gym")
        decision = s.assess(state, ident)
        assert decision == "rejected"
        negative = copy_public_entry(state["library"].snapshot()[BRANCH]["entries"][ident])
        accounting = state["costs"].report()
        state["journal"].verify()

        # A separate intentionally fictional qualification tests resource-boundary
        # mechanics. It cannot change the real technical experiment's rejection.
        with tempfile.TemporaryDirectory(prefix="specialist-positive-protocol-") as protocol_temp:
            positive = f.setup.__wrapped__(Path(protocol_temp))
            positive_origin = s.origin(positive)
            positive_gym = s.campaign(positive)
            positive_workflow = PlacementWorkflow.model_validate(positive_gym["candidate"])
            s.seal(positive, "placement-extra-rd", "C")
            positive_id = s.retain(positive, positive_origin, positive_workflow, "placement-gym")
            assert s.assess(positive, positive_id, synthetic_saving=20) == "assessed"
            f.control(positive, positive_id, "validate")
            f.control(positive, positive_id, "admit")
            resource = positive["service"].catalog_resource()
            catalog = positive["service"].catalog(
                f.proof(positive, resource, "discover", digest("flywheel-catalog-request", {"resource": resource}))
            )
            instance = s.problem(2600, hosts=5, services=5, tight=True)
            invocation = PlacementInvocation(
                mission_id="peer-new-five-service-mission",
                problem=instance,
                beta_digest=f.BETA,
                policy_digest=f.POLICY,
                recipient_capabilities_digest=f.ZERO,
                prerequisite_digests=[],
                logical_limit=100_000,
                cost_cap_micro_usd=100,
            )
            receipt = positive["service"].invoke(
                positive_id,
                invocation,
                f.proof(positive, positive_id, "invoke", digest("flywheel-invocation", invocation)),
            )
            assert (
                receipt["result"] is not None
                and verify_placement(instance, receipt["result"])["accepted_finite_result"]
            )
            positive["journal"].verify()
            protocol = {
                "scope": "FICTIONAL frontier/economic/ENS attestations; actual cryptography, loading and local computation",
                "actual_live_admission": False,
                "live_ens": False,
                "actual_frontier_calls": 0,
                "catalog": catalog,
                "invocation": receipt,
                "independent_finite_check": verify_placement(instance, receipt["result"]),
                "successful_live_peer_reuse": False,
                "note": "Positive modeled admission only tests controls; no actual net Alpha or real peer is certified",
            }

        composition = []
        for seed in range(2700, 2708):
            task = GymTask(
                task_id=f"composition-{seed}",
                partition="composition",
                family="five-host-fresh-cost-and-capacity",
                problem=s.problem(seed, hosts=5, services=4, tight=True),
            )
            order_only = PlacementWorkflow(version=2, order=workflow.order)
            pruner_only = PlacementWorkflow(version=2, bound=workflow.bound, capacity_pruning=workflow.capacity_pruning)
            conventional = PlacementWorkflow(version=1, order="largest-demand", bound="residual", capacity_pruning=True)
            composition.append(
                {
                    "task": task.model_dump(),
                    "same_total_work_limit": task.logical_limit,
                    "technical_reference": run_arm(task, PlacementWorkflow(version=1)),
                    "ordering_specialist_alone": run_arm(task, order_only),
                    "pruning_specialist_alone": run_arm(task, pruner_only),
                    "composition": run_arm(task, workflow, coordination=64),
                    "strong_conventional_alternative": run_arm(task, conventional),
                    "private_retained": run_arm(task, workflow),
                    "shared_same_contents": run_arm(task, workflow),
                    "ordinary_library_same_contents": run_arm(task, workflow),
                }
            )

        with tempfile.TemporaryDirectory(prefix="specialist-interrupted-protocol-") as failed_temp:
            failed = f.setup.__wrapped__(Path(failed_temp))
            s.origin(failed)
            interrupted = s.campaign(failed, limit=1)
            assert interrupted["candidate"] is None
            failed_costs = failed["costs"].report()

        source_paths = sorted((root / "alpha_factory_v1/core/runtime").rglob("*.py")) + [
            Path(__file__).resolve(),
            root / "scripts/record_general_flywheel.py",
            root / "tests/runtime/test_flywheel_protected.py",
            root / "tests/runtime/test_flywheel_specialists.py",
        ]
        accepted = sum(row["v2"]["verification"]["accepted_finite_result"] for row in technical["cases"])
        less_work = sum(row["v2"]["logical_units"] < row["v1"]["logical_units"] for row in technical["cases"])
        return {
            "schema_name": "specialist-breakthrough-relay/v1",
            "sources": {
                path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in source_paths
            },
            "components": {
                "orchestration": "executed-local",
                "training": "executed-local-workflow-search",
                "model": "scripted-protocol-fixture/v1",
                "identity": "fictional-RPC-real-signature-conformance",
                "market": "not-observed",
                "billing": "fictional-attestations",
                "actual_acceptance": "independent-finite-oracle",
            },
            "origin": {
                "execution_record_digest": origin["digest"],
                "mission": origin["mission"],
                "artifact": origin["result"],
                "actual_customer_acceptance": False,
            },
            "gym": frozen,
            "fresh_evaluation": technical,
            "admission": negative,
            "synthetic_protocol_only": protocol,
            "composition_and_controls": composition,
            "interrupted_campaign": interrupted,
            "interrupted_accounting_fictional": failed_costs,
            "accounting_fictional": accounting,
            "summary": {
                "training_completed": True,
                "retained_artifact_changed": True,
                "fresh_cases": len(technical["cases"]),
                "independently_accepted_v2": accepted,
                "fresh_cases_with_less_logical_work": less_work,
                "technical_transfer_passed": technical["technical_transfer_passed"],
                "protected_executable_invocation": "executed with fictional ENS/model/billing authority",
                "competent_frontier_beta": "not executed",
                "net_alpha_positive": False,
                "growing_network_advantage": False,
                "live_qualified": False,
                "actual_provider_calls": 0,
                "actual_computer_actions": 0,
                "actual_revenue_micro_usd": 0,
                "complete_actual_cost": "unknown",
                "commercial_profit": "not established",
                "human_service_market_benchmark": "unmeasured",
                "actual_admission": "do not admit",
                "graph_specific_advantage": "not established; identical-content control",
                "cost_boundary": "A paid-delivery development is never rebilled; additional Gym in C; assessment and serving in B",
            },
        }


def copy_public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: entry[key] for key in ("manifest", "state", "decision", "origin_input_digests")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("preserve the previous report; select a new output")
    result = record()
    with args.output.open("xb") as stream:
        stream.write(canonical(result) + b"\n")
