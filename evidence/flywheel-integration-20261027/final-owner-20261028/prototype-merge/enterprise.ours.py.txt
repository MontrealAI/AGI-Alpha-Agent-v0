# SPDX-License-Identifier: Apache-2.0
"""Offering qualification and bounded decisions on the existing protected runtime.

Forecasts are operator attestations, never sales or execution permits. Only the
existing executor and protected capability service perform actions. Journal
records retain stopped, rejected and uncertain work without automatic replay.
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from typing import Any, Literal

from pydantic import Field, model_validator

from ..store import Conflict, digest as runtime_digest
from .flywheel_execution import ExecutionMission, ExecutionPermit, ExecutionProfile, MissionExecutor, operation_key
from .flywheel_learning import accepted_general_origin
from .protocol import Digest, Identifier, StrictModel, Text, canonical, digest
from .trust import SignedEnvelope
from .transformation_library import _is_exact_type

PREFIX = "@flywheel-enterprise:"
STAGES = ("hypothesis", "prototype", "technically-qualified", "commercially-assessed", "authorized")
Action = Literal["produce", "assess", "gym", "invoke", "retain", "share", "prototype", "hold", "defer", "stop"]


def key(kind: str, identity: str) -> str:
    return PREFIX + kind + ":" + digest("enterprise-record-identity", {"id": identity})


class EvidenceRef(StrictModel):
    journal_key: str = Field(min_length=1, max_length=400)
    record_digest: Digest


class HumanReference(StrictModel):
    service: Text
    source: Text
    basis: Literal["published-market", "estimated-team-hours"]
    team_hours: int | None = Field(default=None, ge=1, le=100_000)
    hourly_rate_micro_usd: int | None = Field(default=None, ge=1, le=10**12)
    total_micro_usd: int = Field(gt=0, le=10**15)

    @model_validator(mode="after")
    def estimate(self) -> HumanReference:
        if self.basis == "estimated-team-hours" and (
            self.team_hours is None
            or self.hourly_rate_micro_usd is None
            or self.total_micro_usd != self.team_hours * self.hourly_rate_micro_usd
        ):
            raise ValueError("disclose consistent estimated team hours and rates")
        return self


class Offering(StrictModel):
    schema_name: Literal["flywheel-offering/v1"] = "flywheel-offering/v1"
    offering_id: Identifier
    version: int = Field(ge=1, le=1_000_000)
    beneficiary: Text
    useful_outcome: Text
    deliverable: Text
    scope: Text
    acceptance_criteria: list[Text] = Field(min_length=1, max_length=32)
    need_evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    demand_uncertainty: Text
    human_reference: HumanReference
    required_capabilities: list[Digest] = Field(default_factory=list, max_length=16)
    permitted_tools: list[Identifier] = Field(min_length=1, max_length=24)
    price_policy: Text
    price_candidates_micro_usd: list[int] = Field(min_length=1, max_length=16)
    capacity: int = Field(ge=1, le=64)
    turnaround_seconds: int = Field(ge=1, le=43_200)
    complete_cost_cap_micro_usd: int = Field(ge=1, le=10**12)
    risks: list[Text] = Field(min_length=1, max_length=16)
    operating_limits: list[Text] = Field(min_length=1, max_length=16)
    mode: Literal["live", "hybrid", "simulation"]
    parent_offering: EvidenceRef | None = None

    @model_validator(mode="after")
    def bounded(self) -> Offering:
        if (
            len(set(self.permitted_tools)) != len(self.permitted_tools)
            or len(set(self.required_capabilities)) != len(self.required_capabilities)
            or len(set(self.price_candidates_micro_usd)) != len(self.price_candidates_micro_usd)
            or any(not _is_exact_type(p, int) or not 1 <= p <= 10**12 for p in self.price_candidates_micro_usd)
        ):
            raise ValueError("unique bounded tools, capabilities and positive candidate prices required")
        if len(canonical(self)) > 40_000:
            raise ValueError("offering exceeds its immutable record budget")
        return self


class CommercialAssessment(StrictModel):
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    price_micro_usd: int = Field(gt=0, le=10**12)
    demand_basis: Text
    lower_net_value_micro_usd: int = Field(ge=-(10**12), le=10**12)
    upper_net_value_micro_usd: int = Field(ge=-(10**12), le=10**12)
    additional_cost_cap_micro_usd: int = Field(ge=0, le=10**12)
    limitations: Text

    @model_validator(mode="after")
    def interval(self) -> CommercialAssessment:
        if self.lower_net_value_micro_usd > self.upper_net_value_micro_usd:
            raise ValueError("commercial uncertainty interval is reversed")
        return self


class Alternative(StrictModel):
    alternative_id: Identifier
    action: Action
    offering_id: Identifier | None = None
    price_micro_usd: int | None = Field(default=None, gt=0, le=10**12)
    capability_digest: Digest | None = None
    lower_benefit_micro_usd: int = Field(ge=0, le=10**12)
    upper_benefit_micro_usd: int = Field(ge=0, le=10**12)
    cash_cost_cap_micro_usd: int = Field(ge=0, le=10**12)
    opportunity_cost_micro_usd: int = Field(ge=0, le=10**12)
    slots: int = Field(ge=0, le=64)
    seconds: int = Field(ge=0, le=43_200)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    uncertainty: Text

    @model_validator(mode="after")
    def coherent(self) -> Alternative:
        if self.lower_benefit_micro_usd > self.upper_benefit_micro_usd:
            raise ValueError("benefit uncertainty interval is reversed")
        if self.action in {"hold", "defer", "stop"} and any(
            (
                self.lower_benefit_micro_usd,
                self.upper_benefit_micro_usd,
                self.cash_cost_cap_micro_usd,
                self.opportunity_cost_micro_usd,
                self.slots,
                self.seconds,
                self.offering_id,
                self.price_micro_usd,
                self.capability_digest,
            )
        ):
            raise ValueError("inactive choices have zero resource and benefit commitments")
        if self.action in {"produce", "prototype"} and (self.offering_id is None or self.slots < 1):
            raise ValueError("productive alternatives need an offering and capacity")
        if self.action in {"produce", "prototype"} and (self.seconds < 1 or self.cash_cost_cap_micro_usd < 1):
            raise ValueError("productive alternatives require positive time and liability bounds")
        if self.action in {"invoke", "share"} and self.capability_digest is None:
            raise ValueError("invoking or sharing needs an existing pinned capability")
        return self


class DecisionRequest(StrictModel):
    decision_id: Identifier
    alternatives: list[Alternative] = Field(min_length=1, max_length=32)
    available_slots: int = Field(ge=0, le=64)
    horizon_seconds: int = Field(ge=1, le=43_200)
    extra_reserve_micro_usd: int = Field(ge=0, le=10**12)
    max_cash_micro_usd: int = Field(ge=0, le=10**12)

    @model_validator(mode="after")
    def choices(self) -> DecisionRequest:
        if len({x.alternative_id for x in self.alternatives}) != len(self.alternatives) or not any(
            x.action in {"hold", "defer", "stop"} for x in self.alternatives
        ):
            raise ValueError("distinct alternatives and a zero-investment option required")
        if len(canonical(self)) > 100_000:
            raise ValueError("decision exceeds its bounded alternative budget")
        return self


class EnterpriseCommand(StrictModel):
    journal_identity: str = Field(pattern=r"^urn:agialpha:ed25519:[0-9a-f]{64}$")
    operation_id: Identifier
    expires_at: int = Field(ge=1)
    action: Literal["offering", "advance", "decide", "reconcile"]
    expected_head: Digest | None
    record: dict[str, Any]


class Enterprise:
    """Use existing custody, trust, checkpoint, executor and accounting services."""

    def __init__(self, service: Any) -> None:
        self.service, self.journal, self.costs = service, service.journal, service.costs

    def _read(self, kind: str, identity: str, cx: Any) -> dict[str, Any] | None:
        try:
            return dict(self.journal.latest(key(kind, identity), cx))
        except KeyError:
            return None

    def _evidence(self, refs: list[EvidenceRef], cx: Any) -> None:
        for ref in refs:
            if self.journal.latest(ref.journal_key, cx)["digest"] != ref.record_digest:
                raise Conflict("evidence is stale or differs from current recorded history")

    def _commercial_evidence(self, offering: dict[str, Any], cx: Any) -> CommercialAssessment:
        assessment = CommercialAssessment.model_validate(offering["commercial"])
        self._evidence(assessment.evidence, cx)
        return assessment

    def _technical_origin(self, offering: dict[str, Any], cx: Any) -> None:
        """Recheck current support while preserving the historical qualification."""
        operation = offering.get("prototype_operation")
        if not isinstance(operation, str) or offering["qualification_source"] != self.service.execution_digest:
            raise Conflict("prototype technical source requires requalification")
        launch = self._read("launch", operation, cx)
        record, _ = accepted_general_origin(self.service, operation, cx)
        if (
            launch is None
            or launch["status"] != "completed"
            or launch["source"] != self.service.execution_digest
            or launch["offering_spec_digest"]
            != digest("enterprise-offering", Offering.model_validate(offering["spec"]))
            or launch["execution_digest"] != record["digest"]
        ):
            raise Conflict("prototype acceptance differs from the qualified offering execution")

    def _context(self, cx: Any) -> dict[str, Any]:
        _, network = self.service._state(cx)
        active = self._read("active", "capacity", cx)
        return {
            "source": self.service.execution_digest,
            "control": self.journal.latest("@control", cx)["digest"],
            "ledger": digest("enterprise-ledger-snapshot", self.costs.snapshot(cx)),
            "capabilities": digest("enterprise-capability-snapshot", network),
            "active": active["digest"] if active else None,
        }

    def inspect(self, kind: str, identity: str) -> dict[str, Any]:
        if kind not in {"offering", "decision", "launch"}:
            raise ValueError("unsupported enterprise inspection")
        with self.journal.transaction() as cx:
            self.service._state(cx)
            record = self._read(kind, identity, cx)
            if record is None:
                raise KeyError(identity)
            return record

    def apply(self, signed: SignedEnvelope) -> dict[str, Any]:
        signed = SignedEnvelope.model_validate_json(canonical(signed))
        raw = self.service.trust.verify(signed, "flywheel-enterprise-command", "controller")
        command = EnterpriseCommand.model_validate(raw)
        if command.journal_identity != self.journal.identity or command.expires_at <= int(time.time()):
            raise ValueError("enterprise command requires this journal and current authority")
        with self.journal.transaction() as cx:
            self.service._state(cx)
            if command.action != "reconcile" and self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("enterprise is stopped")
            if self._read("operation", command.operation_id, cx) is not None:
                raise Conflict("enterprise operation already consumed; inspect its recorded result")
            value: dict[str, Any]
            if command.action == "offering":
                spec = Offering.model_validate(command.record)
                old = self._read("offering", spec.offering_id, cx)
                if (old["digest"] if old else None) != command.expected_head:
                    raise Conflict("offering changed; refresh before revising")
                if spec.version != (old["spec"]["version"] + 1 if old else 1):
                    raise ValueError("offering revisions must be consecutive and requalify")
                self._evidence(spec.need_evidence + ([spec.parent_offering] if spec.parent_offering else []), cx)
                value = {
                    "spec": spec.model_dump(),
                    "stage": "hypothesis",
                    "qualification_source": None,
                    "proposer": signed.principal,
                    "history": [],
                    "commercial": None,
                }
                target = key("offering", spec.offering_id)
            elif command.action == "advance":
                target, value = self._advance(command, cx)
            elif command.action == "reconcile":
                target, value = self._reconcile(command, cx)
            else:
                request = DecisionRequest.model_validate(command.record)
                if command.expected_head is not None or self._read("decision", request.decision_id, cx) is not None:
                    raise Conflict("decision identity must be new")
                value = self._decide(request, cx)
                target = key("decision", request.decision_id)
            value["signed"] = signed.model_dump()
            record = self.journal.append(cx, target, value)
            self.journal.append(
                cx, key("operation", command.operation_id), {"target": target, "result": record["digest"]}
            )
            self.service.checkpoint.advance(self.journal, cx)
            return dict(record)

    def _reconcile(self, command: EnterpriseCommand, cx: Any) -> tuple[str, dict[str, Any]]:
        raw = command.record
        if set(raw) not in (
            {"execution_operation", "evidence"},
            {"execution_operation", "evidence", "original_mission"},
        ):
            raise ValueError("reconciliation requires exact launch and evidence")
        if not isinstance(raw["evidence"], list) or not 1 <= len(raw["evidence"]) <= 16:
            raise ValueError("reconciliation requires bounded accounting evidence")
        self._evidence([EvidenceRef.model_validate(r) for r in raw["evidence"]], cx)
        old = self._read("launch", raw["execution_operation"], cx)
        if (
            old is None
            or old["digest"] != command.expected_head
            or old["status"] not in {"failed-or-uncertain", "attempting-or-uncertain"}
            or self.journal.latest("@control", cx)["state"] != "paused"
        ):
            raise Conflict("reconciliation needs the exact failed launch and a paused enterprise")
        original = ExecutionMission.model_validate(raw["original_mission"]) if "original_mission" in raw else None
        if original is not None and digest("flywheel-execution-request", original) != old["request_digest"]:
            raise Conflict("original mission differs from the exact reserved execution intent")
        try:
            execution = self.journal.latest(operation_key(raw["execution_operation"]), cx)
        except KeyError:
            if old["status"] != "failed-or-uncertain":
                raise Conflict("missing execution cannot clear a merely attempting launch") from None
            ledger_mission = old.get("ledger_mission_id") or (original.mission_id if original else None)
            if ledger_mission is None:
                raise Conflict("legacy preflight failure requires its exact original mission") from None
            execution_digest = None
            failure_kind = "caught-preflight-failure-without-execution-record"
        else:
            if (
                digest("enterprise-execution-permit", execution["permit"]) != old.get("execution_permit_digest")
                or digest("flywheel-execution-request", execution["mission"]) != old.get("request_digest")
                or digest("flywheel-execution-profile", execution["profile"]) != old.get("profile_digest")
            ):
                raise Conflict("terminal receipt differs from the exact reserved execution intent")
            if execution["status"] not in {"failed-or-uncertain", "stopped-budget"}:
                raise Conflict("in-flight or delivered execution cannot be cleared as a failed launch")
            ledger_mission = ExecutionMission.model_validate(execution["mission"]).mission_id
            execution_digest = execution["digest"]
            failure_kind = "terminal-execution-failure"
        if old.get("ledger_mission_id", ledger_mission) != ledger_mission:
            raise Conflict("launch accounting scope differs from the original mission")
        if not self.costs.report(ledger_mission, cx)["bucket_complete"]["A"]:
            raise Conflict("complete failed-attempt liabilities must be reconciled before releasing capacity")
        closure = None
        if execution_digest is None:
            operation = raw["execution_operation"]
            if "execution/" + operation in self.costs.snapshot(cx)["charges"]:
                raise Conflict("execution reservation without its receipt requires separate investigation")
            closure = self.journal.append(
                cx,
                operation_key(operation),
                {
                    "schema_name": "flywheel-execution-closure/v1",
                    "status": "cancelled-before-execution",
                    "execution_started": False,
                    "launch_digest": old["digest"],
                    "execution_permit_digest": old["execution_permit_digest"],
                    "request_digest": old["request_digest"],
                    "profile_digest": old["profile_digest"],
                    "ledger_mission_id": ledger_mission,
                    "reconciliation_command": command.model_dump(),
                    "authority_granted": False,
                },
            )
        active = self._read("active", "capacity", cx)
        reservations = active["reservations"] if active else {}
        reservations.pop(raw["execution_operation"], None)
        self.journal.append(cx, key("active", "capacity"), {"reservations": reservations})
        value = self.journal.document(old)
        value.update(
            status="reconciled-failure",
            execution_digest=execution_digest,
            ledger_mission_id=ledger_mission,
            failure_kind=failure_kind,
            authority_restored=False,
        )
        if closure is not None:
            value["closure_digest"] = closure["digest"]
        return key("launch", raw["execution_operation"]), value

    def _advance(self, command: EnterpriseCommand, cx: Any) -> tuple[str, dict[str, Any]]:
        raw = command.record
        if set(raw) != {"offering_id", "stage", "execution_operation", "commercial"}:
            raise ValueError("offering advancement requires exact stage-specific terms")
        old = self._read("offering", raw["offering_id"], cx)
        if old is None or old["digest"] != command.expected_head:
            raise Conflict("offering head changed")
        value = self.journal.document(old)
        spec = Offering.model_validate(value["spec"])
        self._evidence(spec.need_evidence, cx)
        stage = raw["stage"]
        if value["stage"] == "authorized" or stage != STAGES[STAGES.index(value["stage"]) + 1]:
            raise ValueError("qualification stages cannot be skipped")
        if stage in {"prototype", "technically-qualified"}:
            launch = self._read("launch", raw["execution_operation"], cx)
            if (
                launch is None
                or launch["status"] != "completed"
                or launch["offering_spec_digest"] != digest("enterprise-offering", spec)
                or launch["source"] != self.service.execution_digest
                or raw["commercial"] is not None
            ):
                raise ValueError("qualification needs this offering's actual completed prototype on current source")
            execution = self.journal.latest(operation_key(raw["execution_operation"]), cx)
            if launch["execution_digest"] != execution["digest"]:
                raise Conflict("prototype execution changed")
            if stage == "technically-qualified":
                accepted_general_origin(self.service, raw["execution_operation"], cx)
                value["qualification_source"] = self.service.execution_digest
            value["prototype_operation"] = raw["execution_operation"]
        else:
            if raw["execution_operation"] is not None or value["qualification_source"] != self.service.execution_digest:
                raise ValueError("technical source requires requalification")
            self._technical_origin(value, cx)
            if stage == "commercially-assessed":
                assessment = CommercialAssessment.model_validate(raw["commercial"])
                self._evidence(assessment.evidence, cx)
                if assessment.price_micro_usd not in spec.price_candidates_micro_usd:
                    raise ValueError("commercial price is outside the versioned policy")
                value["commercial"] = assessment.model_dump()
            else:
                assessment = self._commercial_evidence(value, cx)
                if raw["commercial"] is not None or assessment.lower_net_value_micro_usd <= 0:
                    raise ValueError("authorization requires a positive conservative commercial assessment")
        value["history"].append({"from_digest": old["digest"], "stage": stage, "terms": raw})
        value["stage"] = stage
        return key("offering", spec.offering_id), value

    def _decide(self, request: DecisionRequest, cx: Any) -> dict[str, Any]:
        context, report = self._context(cx), self.costs.report(cx=cx)
        available = report["available_funds"]
        active = self._read("active", "capacity", cx)
        reservations = active["reservations"] if active else {}
        reserved_slots = sum(r["slots"] for r in reservations.values())
        reserved_cash = sum(r["cash"] for r in reservations.values())
        rows: list[dict[str, Any]] = []
        for alternative in request.alternatives:
            self._evidence(alternative.evidence, cx)
            reasons: list[str] = []
            offering = None
            if alternative.offering_id is not None:
                offering = self._read("offering", alternative.offering_id, cx)
                if offering is None:
                    reasons.append("offering missing")
                else:
                    spec = Offering.model_validate(offering["spec"])
                    self._evidence(spec.need_evidence, cx)
                    if alternative.action == "produce" and (
                        offering["stage"] != "authorized" or offering["qualification_source"] != context["source"]
                    ):
                        reasons.append("offering not currently authorized")
                    elif alternative.action == "produce":
                        try:
                            self._technical_origin(offering, cx)
                        except (KeyError, ValueError):
                            reasons.append("prototype acceptance or supporting evidence is not currently eligible")
                        try:
                            self._commercial_evidence(offering, cx)
                        except (KeyError, ValueError):
                            reasons.append("commercial assessment evidence is missing or stale")
                    if (
                        alternative.price_micro_usd is not None
                        and alternative.price_micro_usd not in spec.price_candidates_micro_usd
                    ):
                        reasons.append("price outside offering policy")
                    if alternative.slots > spec.capacity or alternative.seconds > spec.turnaround_seconds:
                        reasons.append("offering resource limits")
                    if alternative.cash_cost_cap_micro_usd > spec.complete_cost_cap_micro_usd:
                        reasons.append("offering cost limit")
                    offering_slots = sum(
                        reservation["slots"]
                        for reservation in reservations.values()
                        if reservation.get("offering_id") in {None, spec.offering_id}
                    )
                    if alternative.slots + offering_slots > spec.capacity:
                        reasons.append("offering occupied capacity")
                    if spec.required_capabilities:
                        reasons.append("capability-dependent execution adapter unqualified")
            if alternative.capability_digest is not None:
                try:
                    _, network = self.service._state(cx)
                    self.service._eligible(network, alternative.capability_digest)
                    self.service._dependencies(network, network["entries"][alternative.capability_digest])
                except (KeyError, ValueError):
                    reasons.append("capability not currently admitted")
            if alternative.action not in {"hold", "defer", "stop"}:
                if available is None or alternative.cash_cost_cap_micro_usd > min(
                    request.max_cash_micro_usd, max(0, available - request.extra_reserve_micro_usd - reserved_cash)
                ):
                    reasons.append("cash unknown or insufficient after obligations and reserves")
                if (
                    alternative.slots + reserved_slots > request.available_slots
                    or alternative.seconds > request.horizon_seconds
                ):
                    reasons.append("capacity or time budget")
            score = (
                alternative.lower_benefit_micro_usd
                - alternative.cash_cost_cap_micro_usd
                - alternative.opportunity_cost_micro_usd
            )
            rows.append(
                {
                    "alternative": alternative.model_dump(),
                    "eligible": not reasons,
                    "reasons": reasons,
                    "lower_net_value_micro_usd": score,
                    "offering_head": offering["digest"] if offering else None,
                }
            )
        eligible = [row for row in rows if row["eligible"]]
        selected = sorted(
            eligible,
            key=lambda r: (
                -r["lower_net_value_micro_usd"],
                r["alternative"]["cash_cost_cap_micro_usd"],
                r["alternative"]["alternative_id"],
            ),
        )[0]
        return {
            "request": request.model_dump(),
            "context": context,
            "accounting": report,
            "alternatives": rows,
            "selected": selected["alternative"]["alternative_id"],
            "consumed": False,
            "policy": "max conservative net value among supplied feasible alternatives; lower cash then lexical tie break",
            "reason": "Current signed evidence and forecasts only; finite menu, no claim of universal optimality",
            "authority": "recommendation only; separate exact execution, Gym or protected invocation permit required",
        }

    def run(
        self,
        decision_id: str,
        executor: MissionExecutor,
        mission: ExecutionMission,
        profile: ExecutionProfile,
        permit: SignedEnvelope,
    ) -> dict[str, Any]:
        """Consume one bounded production/prototype decision before actual I/O."""
        mission = ExecutionMission.model_validate_json(canonical(mission))
        profile = ExecutionProfile.model_validate_json(canonical(profile))
        permit = SignedEnvelope.model_validate_json(canonical(permit))
        raw = self.service.trust.verify(permit, "flywheel-execution-permit", "controller")
        terms = ExecutionPermit.model_validate(raw["permit"])
        if raw.get("journal_identity") != self.journal.identity or terms.operation_id != mission.mission_id:
            raise ValueError("enterprise execution must bind the exact journal and mission identity")
        if (
            executor.journal is not self.journal
            or executor.costs is not self.costs
            or executor.trust is not self.service.trust
        ):
            raise ValueError("enterprise must use the existing authoritative executor")
        with self.journal.transaction() as cx:
            context = self._context(cx)
            decision = self._read("decision", decision_id, cx)
            if decision is None or decision["consumed"] or decision["context"] != context:
                raise Conflict("decision consumed or operating context changed; reassess")
            command = EnterpriseCommand.model_validate(decision["signed"]["payload"])
            self.service.trust.verify(
                SignedEnvelope.model_validate(decision["signed"]), "flywheel-enterprise-command", "controller"
            )
            if command.expires_at <= int(time.time()) or self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("decision authority expired or enterprise stopped")
            for frozen_row in decision["alternatives"]:
                alternative = Alternative.model_validate(frozen_row["alternative"])
                self._evidence(alternative.evidence, cx)
                if alternative.offering_id is not None:
                    current_offering = self._read("offering", alternative.offering_id, cx)
                    if (current_offering["digest"] if current_offering else None) != frozen_row["offering_head"]:
                        raise Conflict("alternative offering changed since decision; reassess")
                    if current_offering is not None:
                        self._evidence(Offering.model_validate(current_offering["spec"]).need_evidence, cx)
                        if (
                            frozen_row["eligible"]
                            and alternative.action == "produce"
                            and current_offering["stage"] == "authorized"
                        ):
                            self._technical_origin(current_offering, cx)
                            self._commercial_evidence(current_offering, cx)
            row = next(
                x for x in decision["alternatives"] if x["alternative"]["alternative_id"] == decision["selected"]
            )
            choice = Alternative.model_validate(row["alternative"])
            if choice.action not in {"produce", "prototype"} or not row["eligible"]:
                raise ValueError("this decision requires another existing lifecycle command or no execution")
            offering = self._read("offering", str(choice.offering_id), cx)
            if offering is None or offering["digest"] != row["offering_head"]:
                raise Conflict("offering changed since decision")
            spec = Offering.model_validate(offering["spec"])
            if spec.required_capabilities:
                raise ValueError(
                    "Capability-dependent execution needs separately authenticated invocation; adapter unsupported"
                )
            tools = {t.get("name", "computer") for t in profile.tools}
            expected_bucket = "A"
            if (
                mission.beneficiary != spec.beneficiary
                or mission.goal != spec.useful_outcome
                or mission.deliverable != spec.deliverable
                or mission.acceptance_criteria != spec.acceptance_criteria
                or mission.mode != spec.mode
                or mission.max_seconds > min(choice.seconds, spec.turnaround_seconds)
                or not tools <= set(spec.permitted_tools)
                or terms.bucket != expected_bucket
                or terms.max_authorized_micro_usd > choice.cash_cost_cap_micro_usd
                or terms.expires_at <= int(time.time())
                or terms.request_digest != digest("flywheel-execution-request", mission)
                or terms.profile_digest != digest("flywheel-execution-profile", profile)
                or terms.environment_digest
                != digest("flywheel-execution-environment-contract", executor.environment.identity)
            ):
                raise ValueError("mission, permit or tools differ from the selected offering envelope")
            if terms.config_digest != runtime_digest(self.journal.config.model_dump()):
                raise ValueError("execution permit has stale runtime configuration")
            if self._read("launch", terms.operation_id, cx) is not None:
                raise Conflict("enterprise launch already attempted")
            launch = {
                "decision_id": decision_id,
                "decision_digest": decision["digest"],
                "offering_spec_digest": digest("enterprise-offering", spec),
                "execution_permit_digest": digest("enterprise-execution-permit", permit),
                "request_digest": terms.request_digest,
                "profile_digest": terms.profile_digest,
                "ledger_mission_id": mission.mission_id,
                "source": context["source"],
                "status": "attempting-or-uncertain",
                "execution_digest": None,
            }
            pending = self.journal.append(cx, key("launch", terms.operation_id), launch)
            active = self._read("active", "capacity", cx)
            reservations = active["reservations"] if active else {}
            if len(reservations) >= 64:
                raise Conflict("capacity reservation bound reached; reconcile outstanding work")
            reservations[terms.operation_id] = {
                "slots": choice.slots,
                "cash": choice.cash_cost_cap_micro_usd,
                "offering_id": spec.offering_id,
            }
            self.journal.append(cx, key("active", "capacity"), {"reservations": reservations})
            updated = self.journal.document(decision)
            updated["consumed"] = True
            self.journal.append(cx, key("decision", decision_id), updated)
            self.service.checkpoint.advance(self.journal, cx)

        def current_support() -> None:
            if choice.action == "produce":
                # active() also runs inside the executor's writer transaction.
                # Use one read-only snapshot, avoiding a nested writer lock.
                with closing(sqlite3.connect(self.journal.path.as_uri() + "?mode=ro", uri=True)) as cx:
                    cx.execute("BEGIN")
                    current_offering = self._read("offering", spec.offering_id, cx)
                    if current_offering is None or current_offering["digest"] != offering["digest"]:
                        raise Conflict("offering changed during production; reassess")
                    self._technical_origin(current_offering, cx)

        try:
            result = (
                executor.run(mission, profile, permit, support_check=current_support)
                if choice.action == "produce"
                else executor.run(mission, profile, permit)
            )
        except Exception:
            self._finish(terms.operation_id, pending["digest"], "failed-or-uncertain")
            raise
        status = (
            "completed"
            if result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
            else "failed-or-uncertain"
        )
        self._finish(terms.operation_id, pending["digest"], status)
        return result

    def _finish(self, operation: str, expected: str, status: str) -> None:
        with self.journal.transaction() as cx:
            self.service._state(cx)
            old = self._read("launch", operation, cx)
            if old is None or old["digest"] != expected:
                raise Conflict("launch changed during execution; reconciliation required")
            value = self.journal.document(old)
            execution = self.journal.latest(operation_key(operation), cx) if status == "completed" else None
            value.update(status=status, execution_digest=execution["digest"] if execution else None)
            self.journal.append(cx, key("launch", operation), value)
            if status == "completed":
                active = self._read("active", "capacity", cx)
                reservations = active["reservations"] if active else {}
                reservations.pop(operation, None)
                self.journal.append(cx, key("active", "capacity"), {"reservations": reservations})
            self.service.checkpoint.advance(self.journal, cx)
