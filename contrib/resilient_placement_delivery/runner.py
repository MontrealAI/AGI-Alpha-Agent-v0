# SPDX-License-Identifier: Apache-2.0
"""Run bounded local work, preserving unknown actual costs and synthetic money."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
import time
from typing import Any, Literal, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.store import Conflict, Journal, digest as runtime_digest
from alpha_factory_v1.core.runtime.successor.flywheel_access import (
    ENSAuthority,
    ENSPins,
    ResourceAccess,
    ServiceIdentity,
)
from alpha_factory_v1.core.runtime.successor.flywheel_capsules import ProtectedLibrary
from alpha_factory_v1.core.runtime.successor.flywheel_checkpoint import DurableCheckpoint
from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, Charge, CostLedger
from alpha_factory_v1.core.runtime.successor.flywheel_execution import (
    ExecutionMission,
    ExecutionPermit,
    ExecutionProfile,
    MissionExecutor,
    operation_key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_experiments import verify_placement
from alpha_factory_v1.core.runtime.successor.flywheel_gym import PlacementEnvironment
from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY, GeneralOriginAcceptance
from alpha_factory_v1.core.runtime.successor.flywheel_specialists import PlacementWorkflow
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.transformation_library import TransformationLibrary
from alpha_factory_v1.core.runtime.successor.trust import SignedEnvelope, TrustAnchor, TrustRegistry, sign_record
from scripts.record_general_flywheel import ScriptedModel

from .schema import PlacementBrief, parse_brief

USD = 1_000_000


class OfflineReader:
    """Refuse all identity reads; local signer roles confer no ENS authentication."""

    def call(self, method: str, params: list[Any]) -> Any:
        raise ValueError("live ENS authentication is unavailable in this offline research runner")


@dataclass
class ResearchState:
    journal: Journal
    costs: CostLedger
    service: ProtectedLibrary
    keys: dict[str, Ed25519PrivateKey]
    trust: TrustRegistry
    root: Path

    def signed(self, domain: str, role: str, record: dict[str, Any], operation: str) -> SignedEnvelope:
        return sign_record(
            self.keys[role],
            role,
            "flywheel-" + domain,
            {"journal_identity": self.journal.identity, "operation_id": operation, "record": record},
        )

    def account(self, action: str, record: dict[str, Any], operation: str) -> dict[str, Any]:
        return self.costs.apply(
            sign_record(
                self.keys["accounting"],
                "accounting",
                "flywheel-cost-command",
                {
                    "journal_identity": self.journal.identity,
                    "operation_id": operation,
                    "action": action,
                    "record": record,
                },
            )
        )


def initialize_research(root: Path) -> ResearchState:
    """Provision ephemeral local roles and an explicit noncash research envelope."""
    root.mkdir(parents=True, exist_ok=False)
    roles = {name: {name} for name in ("producer", "controller", "accounting", "acceptance")}
    keys = {name: Ed25519PrivateKey.generate() for name in roles}
    public = {name: key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex() for name, key in keys.items()}
    trust = TrustRegistry({name: TrustAnchor(public[name], frozenset(roles[name])) for name in roles})
    journal = Journal.initialize(root / "journal")
    costs = CostLedger(journal, trust)
    library = TransformationLibrary(journal, trust, producer="producer")
    pins = ENSPins(registry_sha256="0" * 64, wrapper_sha256="0" * 64, registrar_sha256="0" * 64)
    authority = ENSAuthority((OfflineReader(), OfflineReader()), pins)
    access = ResourceAccess(journal, ServiceIdentity(origin="https://offline-research.invalid"), authority)
    checkpoint = DurableCheckpoint.initialize(root / "local-custody.sqlite3", journal)
    service = ProtectedLibrary(
        library, costs, access, {"ephemeral-research": secrets.token_bytes(32)}, "ephemeral-research", checkpoint
    )
    state = ResearchState(journal, costs, service, keys, trust, root)
    _write_json(root / "public-roles.json", {"scope": "synthetic local roles; no live authority", "keys": public})
    state.account(
        "capital",
        {
            "record_id": "noncash-research-envelope",
            "mission_id": "research-budget",
            "amount_micro_usd": 10_000 * USD,
            "evidence_digest": digest("placement-noncash-research-budget", {"actual_cash": 0}),
        },
        "noncash-research-envelope",
    )
    return state


def build_execution(
    state: ResearchState, brief: PlacementBrief
) -> tuple[MissionExecutor, ExecutionMission, ExecutionProfile, SignedEnvelope]:
    """Bind a named intake to the existing bounded executor and placement tool."""
    mission = ExecutionMission(
        mission_id=brief.brief_id,
        beneficiary=brief.beneficiary,
        goal="Provide a minimum-cost two-replica placement under declared capacities and failure domains",
        challenged_assumption="Two inexpensive replicas may share one correlated failure domain",
        deliverable="Named placement plan, independent finite verification and explicit operating limits",
        acceptance_criteria=[
            "Each service has exactly two replicas in distinct declared failure domains",
            "Every declared host capacity is respected",
            "Global minimum or infeasibility agrees with independent exhaustive enumeration",
            "The named intake and rights evidence remain bound to the exact output",
        ],
        inputs={
            "problem": brief.problem.model_dump(),
            "placement_brief_digest": digest("commercial-placement-brief", brief.model_dump()),
        },
        sharing_rights=brief.rights_basis,
        stop_conditions=["Bounded local tools only", "No infrastructure deployment", "No paid provider calls"],
        mode="hybrid",
        components={
            "model": "simulated",
            "tools": "executed-local",
            "identity": "simulated",
            "acceptance": "executed-local",
            "market": "simulated",
        },
        max_turns=3,
        max_actions=1,
        max_seconds=60,
    )
    environment = PlacementEnvironment(PlacementWorkflow(version=1))
    profile = ExecutionProfile(
        model_id="scripted-protocol-fixture/v1",
        reasoning_effort="high",
        supported_efforts=["high"],
        qualification_digest=digest("placement-scripted-profile", {"actual_frontier_calls": 0}),
        tools=[
            {
                "type": "function",
                "name": "placement_experiment",
                "description": "Bounded existing placement tool",
                "strict": True,
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        ],
    )
    permit = ExecutionPermit(
        operation_id=brief.brief_id,
        request_digest=digest("flywheel-execution-request", mission),
        profile_digest=digest("flywheel-execution-profile", profile),
        environment_digest=digest("flywheel-execution-environment-contract", environment.identity),
        config_digest=runtime_digest(state.journal.config.model_dump()),
        quota_evidence_digest=profile.qualification_digest,
        pricing_evidence_digest=digest("placement-no-provider-price", {"provider_calls": 0}),
        max_authorized_micro_usd=1_000,
        expires_at=int(time.time()) + 300,
        bucket="A",
    )
    signed = sign_record(
        state.keys["controller"],
        "controller",
        "flywheel-execution-permit",
        {"journal_identity": state.journal.identity, "permit": permit.model_dump()},
    )
    executor = MissionExecutor(state.journal, state.trust, state.costs, ScriptedModel(brief.problem), environment)
    return executor, mission, profile, signed


def _unknown_categories(state: ResearchState, mission: str) -> None:
    existing = {row["category"] for row in state.costs.snapshot()["charges"].values() if row["mission_id"] == mission}
    for category in sorted(CATEGORIES - existing):
        charge = Charge(
            activity_id=f"{mission}/{category}",
            mission_id=mission,
            bucket="A",
            category=cast(
                Literal[
                    "model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"
                ],
                category,
            ),
            accrued_micro_usd=None,
            paid_micro_usd=0,
            basis="unknown",
            evidence_digest=digest("placement-unknown-cost", {"mission": mission, "category": category}),
            note="Complete actual attributable cost is unmetered; unknown is not zero or an estimate",
        )
        state.account("charge", charge.model_dump(), "unknown/" + category)


def _acceptance(state: ResearchState, brief: PlacementBrief, execution: dict[str, Any]) -> SignedEnvelope:
    terms = GeneralOriginAcceptance(
        operation_id=brief.brief_id,
        execution_record_digest=execution["digest"],
        output_digest=digest("general-delivered-output", execution["result"]),
        rights_evidence=digest("commercial-placement-brief", brief.model_dump()),
    )
    return state.signed("general-acceptance", "acceptance", terms.model_dump(), "accept/" + brief.brief_id)


def _synthetic_seal(state: ResearchState, mission: str) -> None:
    """Complete only the separate synthetic protocol ledger, never actual costs."""
    rows = [row for row in state.costs.snapshot()["charges"].values() if row["mission_id"] == mission]
    for row in rows:
        value = {k: row[k] for k in Charge.model_fields}
        value.update(
            accrued_micro_usd=USD,
            basis="attested",
            note="SYNTHETIC conformance amount USD1/category; not a cost observation or service-economic estimate",
            evidence_digest=digest("placement-synthetic-cost", {"mission": mission, "category": row["category"]}),
        )
        state.account("resolve", value, "synthetic-resolve/" + row["category"])
    state.account(
        "seal",
        {
            "mission_id": mission,
            "categories": sorted(CATEGORIES),
            "evidence_digest": digest("placement-synthetic-completeness", {"mission": mission, "actual_cost": None}),
        },
        "synthetic-seal",
    )


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _run(state: ResearchState, brief: PlacementBrief) -> dict[str, Any]:
    executor, mission, profile, permit = build_execution(state, brief)
    executor.run(mission, profile, permit)
    execution = state.journal.latest(operation_key(brief.brief_id))
    if execution["status"] != "delivered-awaiting-independent-acceptance-and-costs":
        raise RuntimeError("local execution did not deliver; inspect the persisted journal before recovery")
    _unknown_categories(state, brief.brief_id)
    before = execution["digest"]
    try:
        executor.run(mission, profile, permit)
    except Conflict as error:
        duplicate = str(error)
    else:
        raise AssertionError("duplicate execution was not refused")
    if state.journal.latest(operation_key(brief.brief_id))["digest"] != before:
        raise AssertionError("duplicate execution mutated the delivery")
    terms = _acceptance(state, brief, execution)
    ledger_before = digest("placement-refusal-ledger", state.costs.snapshot())
    try:
        state.service.accept_general_origin(terms)
    except ValueError as error:
        unknown_refusal = str(error)
    else:
        raise AssertionError("unknown actual cost was accepted as complete")
    if digest("placement-refusal-ledger", state.costs.snapshot()) != ledger_before:
        raise AssertionError("failed acceptance changed the ledger")
    verification = verify_placement(brief.problem, execution["result"]["deliverable"])
    _write_json(state.root / "execution.json", execution)
    _write_json(state.root / "unknown-cost-report.json", state.costs.report(brief.brief_id))
    return {
        "execution": execution,
        "research_acceptance": verification,
        "duplicate_execution_refused": duplicate,
        "unknown_cost_native_acceptance_refused": unknown_refusal,
        "journal_integrity": state.journal.verify(),
    }


def synthetic_conformance(state: ResearchState, brief: PlacementBrief) -> dict[str, Any]:
    """Exercise receipt/acceptance/refund transitions with fictional money only."""
    receipt = "synthetic-service-deposit"
    stages = []

    def capture(name: str) -> None:
        stages.append(
            {
                "stage": name,
                "report": state.costs.report(brief.brief_id),
                "ledger_digest": digest("placement-conformance-ledger", state.costs.snapshot()),
            }
        )

    if brief.price_micro_usd == 0:
        run = _run(state, brief)
        capture("free-local-artifact-unknown-cost-native-acceptance-refused")
        accepted = None
        if run["research_acceptance"]["accepted_finite_result"]:
            _synthetic_seal(state, brief.brief_id)
            state.service.accept_general_origin(_acceptance(state, brief, run["execution"]))
            accepted = state.journal.latest(ACCEPTANCE_KEY + brief.brief_id)
            capture("free-synthetic-cost-native-research-acceptance-no-payment")
        return {
            "mode": "synthetic-protocol-conformance-only",
            "stages": stages,
            "execution": run["execution"],
            "acceptance": accepted,
            "payment_status": "no-payment: free research deliverable",
            "actual_collections_micro_usd": 0,
            "synthetic_price_hypothesis_micro_usd": 0,
            "actual_complete_cost_micro_usd": None,
            "journal_integrity": state.journal.verify(),
        }
    state.account(
        "customer-deposit",
        {
            "receipt_id": receipt,
            "mission_id": brief.brief_id,
            "amount_micro_usd": brief.price_micro_usd,
            "purpose": "service",
            "service_price_micro_usd": brief.price_micro_usd,
            "mode": "synthetic",
            "evidence_digest": digest("placement-synthetic-deposit", {"brief": brief.brief_id}),
            "note": "SYNTHETIC price payment for protocol checks; no buyer, bank event or actual revenue",
        },
        "synthetic-deposit",
    )
    capture("synthetic-deposit-unearned")
    run = _run(state, brief)
    capture("actual-local-artifact-unknown-cost-native-acceptance-refused")
    if not run["research_acceptance"]["accepted_finite_result"]:
        state.account(
            "customer-refund",
            {
                "event_id": "synthetic-failed-delivery-refund",
                "receipt_id": receipt,
                "amount_micro_usd": brief.price_micro_usd,
                "allocation": "unearned",
                "evidence_digest": digest("placement-synthetic-refund", {"kind": "unaccepted"}),
                "reason": "SYNTHETIC complete refund after independent finite acceptance refused",
            },
            "synthetic-failed-delivery-refund",
        )
        capture("unaccepted-local-result-synthetic-full-refund")
        return {
            "mode": "synthetic-protocol-conformance-only",
            "stages": stages,
            "execution": run["execution"],
            "acceptance": None,
            "actual_collections_micro_usd": 0,
            "synthetic_price_hypothesis_micro_usd": brief.price_micro_usd,
            "actual_complete_cost_micro_usd": None,
            "journal_integrity": state.journal.verify(),
        }
    _synthetic_seal(state, brief.brief_id)
    state.service.accept_general_origin(_acceptance(state, brief, run["execution"]))
    accepted = state.journal.latest(ACCEPTANCE_KEY + brief.brief_id)
    capture("synthetic-complete-cost-native-research-acceptance")
    earning = {
        "event_id": "synthetic-earning",
        "receipt_id": receipt,
        "amount_micro_usd": brief.price_micro_usd,
        "delivery_kind": "general",
        "operation_id": brief.brief_id,
        "execution_record_digest": run["execution"]["digest"],
        "acceptance_record_digest": accepted["digest"],
    }
    state.account("customer-earn", earning, "synthetic-earn")
    capture("synthetic-earned-service-income")
    exact_before = digest("placement-customer-idempotency", state.costs.snapshot())
    state.account("customer-earn", earning, "synthetic-earn")
    if digest("placement-customer-idempotency", state.costs.snapshot()) != exact_before:
        raise AssertionError("exact earning retry changed accounting")
    try:
        state.account("customer-earn", earning, "synthetic-earn-different-operation")
    except (Conflict, ValueError) as error:
        duplicate = str(error)
    else:
        raise AssertionError("duplicate earning was not refused")
    due = {
        "event_id": "synthetic-refund-due",
        "receipt_id": receipt,
        "amount_micro_usd": max(1, brief.price_micro_usd // 10),
        "allocation": "earned",
        "evidence_digest": digest("placement-synthetic-refund", {"kind": "due"}),
        "reason": "SYNTHETIC correction refund obligation; no financial transaction",
    }
    state.account("customer-refund-due", due, "synthetic-refund-due")
    capture("synthetic-refund-obligation")
    paid = {
        **due,
        "event_id": "synthetic-refund-paid",
        "evidence_digest": digest("placement-synthetic-refund", {"kind": "paid"}),
    }
    state.account("customer-refund", paid, "synthetic-refund-paid")
    capture("synthetic-refund-recorded")
    state.journal.verify()
    return {
        "mode": "synthetic-protocol-conformance-only",
        "stages": stages,
        "execution": run["execution"],
        "acceptance": accepted,
        "duplicate_earning_refused": duplicate,
        "exact_retry_idempotent": True,
        "actual_collections_micro_usd": 0,
        "synthetic_price_hypothesis_micro_usd": brief.price_micro_usd,
        "actual_complete_cost_micro_usd": None,
        "journal_integrity": state.journal.verify(),
    }


def run_research(raw_brief: dict[str, Any], output: Path) -> dict[str, Any]:
    """Deliver inspectable local work without promoting it to a live service."""
    brief = parse_brief(raw_brief)
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "brief.json", brief.model_dump())
    actual = initialize_research(output / "actual")
    primary = _run(actual, brief)
    synthetic = initialize_research(output / "synthetic-conformance")
    conformance = synthetic_conformance(synthetic, brief)
    report = {
        "schema": "commercial-placement-research-delivery/v1",
        "mode": "actual-local-tools-scripted-model_research-acceptance",
        "brief_digest": digest("commercial-placement-brief", brief.model_dump()),
        "execution": primary["execution"],
        "research_acceptance": primary["research_acceptance"],
        "actual": {
            **primary,
            "cost_report": actual.costs.report(brief.brief_id),
            "funding_scope": "noncash synthetic research envelope; ledger capital/cash is not actual available money",
            "cost_report_interpretation": "Actual complete costs remain unknown; no actual cash or profit is established",
        },
        "synthetic_conformance": conformance,
        "summary": {
            "actual_provider_calls": 0,
            "actual_computer_actions": 0,
            "actual_primary_tool_invocations": primary["execution"]["actions"],
            "synthetic_conformance_tool_invocations": conformance["execution"]["actions"],
            "actual_customer_acceptance": False,
            "actual_customer_collections_micro_usd": 0,
            "actual_complete_cost_micro_usd": None,
            "actual_profit_micro_usd": None,
            "native_actual_acceptance": primary["unknown_cost_native_acceptance_refused"],
            "research_artifact_accepted": primary["research_acceptance"]["accepted_finite_result"],
            "live_ens_authentication": "not run; every offline identity read refuses",
            "operational_alpha": "unmeasured",
            "retained_alpha": "unmeasured",
            "retention_decision": "do not retain beyond ordinary reusable source; no incremental benefit evidence",
            "signer_scope": "ephemeral same-session local roles, not independently authenticated organizations",
            "funding_scope": "noncash synthetic research envelope, never actual unrestricted cash",
            "custody_scope": "local checkpoint outside journal, not independently durable remote custody",
        },
    }
    _write_json(output / "evidence.json", report)
    root = Path(__file__).resolve().parents[2]
    paths = [
        *sorted((root / "alpha_factory_v1/core/runtime").rglob("*.py")),
        root / "scripts/record_general_flywheel.py",
        *sorted(Path(__file__).resolve().parent.glob("*.py")),
    ]
    _write_json(
        output / "sources.json",
        {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
    )
    return report
