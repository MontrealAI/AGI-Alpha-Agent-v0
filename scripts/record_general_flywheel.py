# SPDX-License-Identifier: Apache-2.0
"""Run general execution software with a scripted model and actual systems tests.

All keys, authority, funding and production-model events here are synthetic.
No calls, payments, external access, live signers or protected admissions occur.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.store import Journal, digest as runtime_digest
from alpha_factory_v1.core.runtime.successor.flywheel_checkpoint import DurableCheckpoint
from alpha_factory_v1.core.runtime.successor.flywheel_costs import CostLedger
from alpha_factory_v1.core.runtime.successor.flywheel_execution import (
    ExecutionMission,
    ExecutionPermit,
    ExecutionProfile,
    MissionExecutor,
)
from alpha_factory_v1.core.runtime.successor.flywheel_experiments import (
    PlacementProblem,
    solve_placement,
    verify_placement,
)
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record


def problem(seed: int) -> PlacementProblem:
    rng = random.Random(seed)
    return PlacementProblem(
        capacities=[rng.randint(5, 10) for _ in range(4)],
        failure_domains=["rack-a", "rack-b", "rack-c", "rack-a"],
        demands=[rng.randint(1, 3) for _ in range(6)],
        costs=[[rng.randint(2, 40) for _ in range(4)] for _ in range(6)],
    )


class SystemsTool:
    component: Literal["executed-local"] = "executed-local"

    def __init__(self) -> None:
        import alpha_factory_v1.core.runtime.successor.flywheel_experiments as implementation

        self.identity = {
            "tool": "resilient-placement-rd/v1",
            "source_sha256": hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest(),
        }

    def perform(self, name: str, arguments: dict[str, Any], active: Callable[[], bool]) -> dict[str, Any]:
        if name != "placement_experiment" or set(arguments) != {"problem"} or not active():
            raise ValueError("experiment tool refused unauthorized input")
        instance = PlacementProblem.model_validate(arguments["problem"])
        outcome = solve_placement(instance)
        if not active():
            raise InterruptedError("experiment stopped")
        return {
            "problem": instance.model_dump(),
            "outcome": outcome,
            "verification": verify_placement(instance, outcome),
            "executed_locally": True,
        }


class ScriptedModel:
    component: Literal["simulated"] = "simulated"

    def __init__(self, instance: PlacementProblem) -> None:
        self.instance = instance
        self.turn = 0

    def respond(self, payload: dict[str, Any], active: Callable[[], bool], remaining: float) -> dict[str, Any]:
        if not active() or remaining <= 0:
            raise InterruptedError("scripted model stopped")
        self.turn += 1
        if self.turn == 1:
            items = [
                {
                    "type": "function_call",
                    "name": "placement_experiment",
                    "call_id": "experiment-1",
                    "arguments": json.dumps({"problem": self.instance.model_dump()}),
                }
            ]
        else:
            tool = json.loads(payload["input"][-1]["output"])
            result = {
                "deliverable": tool["outcome"],
                "verification": tool["verification"],
                "limitations": [
                    "Scripted model; synthetic problem, identity, funding and market",
                    "No frontier baseline or live peer reuse; no Alpha admission",
                ],
                "artifacts": [
                    {"kind": "placement-result", "content": tool, "digest": digest("placement-artifact", tool)}
                ],
            }
            items = [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": json.dumps(result)}],
                }
            ]
        return {
            "id": f"scripted-{self.turn}",
            "model": "scripted-protocol-fixture/v1",
            "status": "completed",
            "output": items,
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }


def run_one(instance: PlacementProblem, seed: int) -> dict[str, Any]:
    """Use the actual signed executor, ledger and interruption-safe journal."""
    with tempfile.TemporaryDirectory(prefix="general-flywheel-fixture-") as temporary:
        root = Path(temporary)
        journal = Journal.initialize(root / "journal")
        keys = {role: Ed25519PrivateKey.generate() for role in ("controller", "accounting")}
        trust = TrustRegistry(
            {
                role: TrustAnchor(
                    key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({role})
                )
                for role, key in keys.items()
            }
        )
        costs = CostLedger(journal, trust)
        costs.checkpoint = DurableCheckpoint.initialize(root / "synthetic-custody.sqlite3", journal)
        mission = ExecutionMission(
            mission_id=f"resilient-systems-{seed}",
            beneficiary="Synthetic replicated-service engineering team",
            goal="Build and independently verify a fault-domain-aware capacity-constrained placement prototype",
            challenged_assumption="Cost-only replicas can fail together in a rack outage",
            deliverable="Exact finite solver output, constraint evidence, independent optimum/infeasibility check",
            acceptance_criteria=[
                "Two replicas in distinct failure domains",
                "All host capacities respected",
                "Minimum cost agrees with an independent exhaustive enumerator",
            ],
            inputs={"problem": instance.model_dump()},
            sharing_rights="Apache-2.0 synthetic data and original source",
            stop_conditions=["250000 search nodes", "No unauthorized tools", "No infrastructure deployment"],
            mode="hybrid",
            components={
                "model": "simulated",
                "tools": "executed-local",
                "identity": "simulated",
                "acceptance": "executed-local",
                "market": "simulated",
            },
            max_turns=3,
        )
        tool = SystemsTool()
        profile = ExecutionProfile(
            model_id="scripted-protocol-fixture/v1",
            reasoning_effort="high",
            supported_efforts=["high"],
            qualification_digest=digest("general-fixture-profile", {"model": "scripted; no actual reasoning"}),
            tools=[
                {
                    "type": "function",
                    "name": "placement_experiment",
                    "description": "Run the actual finite R&D tool",
                    "parameters": {
                        "type": "object",
                        "properties": {"problem": {"type": "object"}},
                        "required": ["problem"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            ],
        )
        costs.apply(
            sign_record(
                keys["accounting"],
                "accounting",
                "flywheel-cost-command",
                {
                    "journal_identity": journal.identity,
                    "operation_id": "synthetic-capital",
                    "action": "capital",
                    "record": {
                        "record_id": "synthetic-capital",
                        "mission_id": mission.mission_id,
                        "amount_micro_usd": 1_000_000,
                        "evidence_digest": digest("synthetic-capital", {"real": False}),
                    },
                },
            )
        )
        permit = ExecutionPermit(
            operation_id="synthetic-execution",
            request_digest=digest("flywheel-execution-request", mission),
            profile_digest=digest("flywheel-execution-profile", profile),
            environment_digest=digest("flywheel-execution-environment-contract", tool.identity),
            config_digest=runtime_digest(journal.config.model_dump()),
            quota_evidence_digest=profile.qualification_digest,
            pricing_evidence_digest=digest("scripted-no-provider", {"provider_calls": 0}),
            max_authorized_micro_usd=1000,
            expires_at=int(time.time()) + 3600,
            bucket="A",
        )
        signed = sign_record(
            keys["controller"],
            "controller",
            "flywheel-execution-permit",
            {"journal_identity": journal.identity, "permit": permit.model_dump()},
        )
        receipt = MissionExecutor(journal, trust, costs, ScriptedModel(instance), tool).run(mission, profile, signed)
        journal.verify()
        return {
            "seed": seed,
            "mission": mission.model_dump(),
            "profile": profile.model_dump(),
            "outcome": receipt.get("result"),
            "status": receipt["status"],
            "turns": receipt["turn"],
            "actions": receipt["actions"],
            "usage_events": receipt["usage_events"],
            "history": receipt["history"],
            "accounting": costs.report(),
            "tool_identity": tool.identity,
            "journal_integrity_checked": True,
            "live_network_qualified": False,
        }


def record() -> dict[str, Any]:
    """Fresh finite engineering variation; no fictional frontier transfer score."""
    cases = [run_one(problem(seed), seed) for seed in range(7300, 7312)]
    root = Path(__file__).resolve().parents[1]
    source_paths = sorted((root / "alpha_factory_v1/core/runtime").rglob("*.py")) + [Path(__file__).resolve()]
    return {
        "schema_name": "general-flywheel-conformance/v1",
        "sources": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths
        },
        "cases": cases,
        "summary": {
            "cases": len(cases),
            "actual_provider_calls": 0,
            "actual_computer_actions": 0,
            "actual_tool_invocations": sum(c["actions"] for c in cases),
            "accepted_finite_results": sum(c["outcome"]["verification"]["accepted_finite_result"] for c in cases),
            "actual_revenue_micro_usd": 0,
            "complete_actual_cost": "unknown",
            "competent_frontier_comparison": "not executed",
            "candidate_decision": "do not admit",
            "candidate_reason": "No extra advantage over competent frontier Beta has been measured",
            "peer_reuse": "not qualified",
            "growing_alpha": "not established",
            "commercial_profit": "unmeasured; synthetic funding is not revenue",
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("choose a new evidence output; preserve original attempts")
    value = canonical(record()) + b"\n"
    with args.output.open("xb") as stream:
        stream.write(value)
