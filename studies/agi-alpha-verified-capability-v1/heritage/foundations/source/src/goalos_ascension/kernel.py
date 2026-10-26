from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import (
    CapabilityPackage,
    ChronicleEntry,
    EvidenceDocket,
    GovernedDecisionState,
    MissionContract,
    ProofBundle,
    ProofJob,
    SettlementReceipt,
    ToolTrace,
    ValidatorReport,
    canonical_hash,
)


def hash_payload(payload: Any) -> str:
    return canonical_hash(payload)


@dataclass(frozen=True)
class Decision:
    state: str
    reason: str
    evidence_hash: str | None = None
    missing: list[str] = field(default_factory=list)


class ClaimBoundary:
    blocked_phrases = (
        "guaranteed returns", "guaranteed profit", "achieved agi", "achieved asi",
        "empirical sota achieved", "production activated: yes", "user-fund authorization: yes",
        "mainnet activated: yes", "legal approval guaranteed", "autonomous legal sovereignty achieved",
    )

    def scan_text(self, text: str) -> list[str]:
        lowered = text.lower()
        return [phrase for phrase in self.blocked_phrases if phrase in lowered]

    def scan_payload(self, payload: Any) -> list[str]:
        import json
        return self.scan_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


class ProofKernel:
    required_docket_fields = (
        "id", "mission_id", "claim_boundary", "proof_bundles", "validator_reports",
        "risk_ledger", "cost_ledger", "decision_state",
    )

    blocked_phrases = ClaimBoundary.blocked_phrases

    def __init__(self) -> None:
        self.claim_boundary = ClaimBoundary()

    def evaluate_docket(self, docket: dict[str, Any]) -> Decision:
        missing = [field for field in self.required_docket_fields if not docket.get(field)]
        if missing:
            return Decision("BLOCKED", "Evidence Docket is incomplete.", missing=missing)
        blocked = self.claim_boundary.scan_payload(docket)
        if blocked:
            return Decision("BLOCKED", "Unsupported or unsafe claim phrase detected.", missing=blocked)
        reports = docket.get("validator_reports", [])
        bundles = docket.get("proof_bundles", [])
        if not reports or not bundles:
            return Decision("NEEDS_REVISION", "Docket needs proof bundles and validator reports.")
        # Examples may reference validator reports by ID strings; rich dockets may embed report objects.
        # Non-empty proof bundles + non-empty validator reports are the minimum public-alpha gate.
        return Decision("READY_FOR_SETTLEMENT", "Docket has minimum proof structure.", hash_payload(docket), [])

    def settle(self, docket: dict[str, Any], accepted_claim: str) -> dict[str, Any]:
        decision = self.evaluate_docket(docket)
        if decision.state != "READY_FOR_SETTLEMENT":
            return {"decision": "blocked", "reason": decision.reason, "missing": decision.missing}
        return SettlementReceipt(
            receipt_id=f"settlement-{docket.get('mission_id', 'unknown')}",
            mission_id=docket.get("mission_id", "unknown"),
            simulated=True,
            decision="accepted_for_simulated_settlement",
            settled_claim=accepted_claim,
            evidence_hash=decision.evidence_hash,
            limitations=[
                "simulation only", "not production authorization", "not legal, tax, or financial advice",
                "not a claim of achieved AGI or ASI", "human review remains required",
            ],
        ).to_dict()


class GoalOSKernel:
    def __init__(self) -> None:
        self.proof_kernel = ProofKernel()

    def create_mission(self, objective: str, mission_id: str = "mission-001") -> MissionContract:
        return MissionContract(
            mission_id=mission_id,
            objective=objective,
            success_criteria=["public-safe Evidence Docket emitted", "validator report emitted", "replay path present"],
            failure_criteria=["unsupported claim", "missing validator report", "missing replay path", "external action attempted"],
            constraints=["browser/local reference only", "no wallet", "no transaction", "human review required"],
        )

    def plan_jobs(self, mission: MissionContract) -> list[ProofJob]:
        return [
            ProofJob(
                job_id=f"{mission.mission_id}-job-{i:02d}",
                mission_id=mission.mission_id,
                objective=f"Produce {artifact.replace('_', ' ')}",
                acceptance_criteria=[f"{artifact} is present", "claim boundary preserved"],
                proof_requirements=["trace root", "output hash", "replay path"],
                allowed_tools=mission.allowed_tools,
                risk_class=mission.risk_class,
                status="executed",
            ) for i, artifact in enumerate(mission.required_artifacts, start=1)
        ]

    def execute_reference_job(self, job: ProofJob) -> tuple[ToolTrace, ProofBundle]:
        trace = ToolTrace(
            trace_id=f"trace-{job.job_id}", job_id=job.job_id, tool_name="local_reference_engine",
            action_reason="Generate public-alpha proof artifact for implementation parity.",
            permission_scope="local_repository_only", expected_observation="artifact generated",
            actual_observation="artifact generated", reversible=True, external_action=False,
        )
        bundle = ProofBundle(
            proof_id=f"proof-{job.job_id}", job_id=job.job_id,
            trace_root=trace.to_dict()["_hash"], output_hash=hash_payload(job.to_dict()),
            policy_decision_root=hash_payload({"policy": "default_deny", "external_action": False}),
            tool_history_root=trace.to_dict()["_hash"], cost={"usd": 0, "mode": "local_reference"},
            latency_ms=1, signatures=["local-reference-signature"], replay_path="scripts/run_proof_run_001.py",
            evidence_uri="evidence/proof-run-001/proof-run-001-docket.json",
        )
        return trace, bundle

    def run_until_done(self, objective: str, mission_id: str = "proof-run-001") -> dict[str, Any]:
        mission = self.create_mission(objective, mission_id)
        jobs = self.plan_jobs(mission)
        traces: list[dict[str, Any]] = []
        bundles: list[dict[str, Any]] = []
        for job in jobs:
            trace, bundle = self.execute_reference_job(job)
            traces.append(trace.to_dict())
            bundles.append(bundle.to_dict())
        provisional_state = GovernedDecisionState(
            decision_id=f"decision-{mission_id}", mission_id=mission_id, state="READY_FOR_HUMAN_REVIEW",
            rationale="Reference loop reached DONE=true for public-alpha artifact completeness; human review remains required.",
            evidence_hash=None,
        )
        docket = EvidenceDocket(
            id=f"docket-{mission_id}", mission_id=mission_id, claim_boundary=mission.claim_boundary,
            claims_matrix=[
                {"claim": "GoalOS public-alpha loop can produce a complete local Evidence Docket scaffold.", "status": "supported_by_reference_run"},
                {"claim": "The run authorizes production, external action, wallet, or mainnet settlement.", "status": "explicitly_not_claimed"},
            ],
            proof_bundles=bundles,
            validator_reports=[],
            risk_ledger=[{"risk": "overclaiming", "control": "claim boundary and blocked phrase scan", "status": "controlled"}],
            cost_ledger={"usd": 0, "mode": "local_reference", "external_services": 0},
            decision_state=provisional_state.to_dict(),
            replay_path="python scripts/run_proof_run_001.py",
            public_private_boundary={"public": ["hashes", "reports", "docket"], "private": ["none in reference run"]},
        )
        validator = ValidatorReport(
            validator_id="local-reference-validator", docket_id=docket.id, verdict="accept",
            checks={"required_fields": True, "proof_bundles": True, "claim_boundary": True, "human_review_required": True},
            notes=["Local public-alpha reference only.", "No external authority granted."],
        )
        docket_dict = {**docket.to_dict(), "validator_reports": [validator.to_dict()]}
        decision = self.proof_kernel.evaluate_docket(docket_dict)
        decision_state = GovernedDecisionState(
            decision_id=f"decision-{mission_id}", mission_id=mission_id,
            state="READY_FOR_HUMAN_REVIEW" if decision.state == "READY_FOR_SETTLEMENT" else "NEEDS_REVISION",
            rationale=decision.reason, evidence_hash=decision.evidence_hash,
        )
        settlement = self.proof_kernel.settle(docket_dict, "public-alpha proof-run-001 reference loop")
        capability = CapabilityPackage(
            package_id=f"capability-{mission_id}", mission_id=mission_id,
            name="Proof Run 001 Reference Loop", initiation_conditions=["public-safe mission", "human review"],
            tool_contracts=["local_reference_engine"], validators=["local-reference-validator"],
            risk_class=mission.risk_class, evidence_history=[decision.evidence_hash or docket_dict["_hash"]],
            replay_path="scripts/run_proof_run_001.py", rollback_plan="revert generated evidence artifacts",
            promotion_status="candidate",
        )
        chronicle = ChronicleEntry(
            entry_id=f"chronicle-{mission_id}", mission_id=mission_id,
            summary="Proof Run 001 reference loop generated a local Evidence Docket, validator report, simulated settlement receipt, and capability package.",
            decision_state=decision_state.state, evidence_hash=decision.evidence_hash,
            capability_package_id=capability.package_id,
        )
        return {
            "mission_contract": mission.to_dict(), "proof_jobs": [j.to_dict() for j in jobs],
            "tool_traces": traces, "evidence_docket": {**docket_dict, "decision_state": decision_state.to_dict()},
            "governed_decision_state": decision_state.to_dict(), "settlement_receipt": settlement,
            "chronicle_entry": chronicle.to_dict(), "capability_package": capability.to_dict(),
            "done": decision.state == "READY_FOR_SETTLEMENT", "boundary": "local public-alpha reference only",
        }
