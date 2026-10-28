# SPDX-License-Identifier: Apache-2.0
"""Read execution-derived contrasts without creating acceptance, costs or authority."""

from __future__ import annotations

import base64
from typing import Any

from cryptography.exceptions import InvalidSignature

from ..store import Conflict, digest as runtime_digest
from .flywheel_costs import KEY as COST_KEY
from .flywheel_discovery import ComparisonPlan, ComparisonTrial, key
from .flywheel_enterprise import EvidenceRef
from .flywheel_execution import ExecutionPermit, ExecutionProfile, operation_key
from .flywheel_learning import ACCEPTANCE_KEY, GeneralOriginAcceptance, accepted_general_origin, check_general_output
from .protocol import digest
from .signatures import verify_ed25519
from .trust import SignedEnvelope

ROLES = ("U", "E", "E+")
TERMINAL = {"delivered-awaiting-independent-acceptance-and-costs", "failed-or-uncertain", "stopped-budget"}


def freeze_cohort(discovery: Any, plan: ComparisonPlan, mode: str, cx: Any) -> None:
    """Reserve observation identities prospectively on the existing Journal."""
    if not plan.cases:
        return
    primary = [case for case in plan.cases if case.phase == "primary"]
    primary_inputs = {case.shared_inputs_digest for case in primary}
    primary_recipients = {case.recipient_id for case in primary}
    inputs = [case.shared_inputs_digest for case in plan.cases]
    if len(inputs) != len(set(inputs)):
        raise ValueError("distinct cases require distinct shared inputs; repeated work is not another sample")
    for case in plan.cases:
        if case.phase == "fresh-recipient" and (
            not primary or case.shared_inputs_digest in primary_inputs or case.recipient_id in primary_recipients
        ):
            raise ValueError("fresh-recipient work needs distinct inputs and a different declared recipient")
        for trial in case.trials:
            if trial.mission.mode != mode:
                raise ValueError("comparison mode must match its original opportunity")
            try:
                discovery.journal.latest(operation_key(trial.operation_id), cx)
            except KeyError:
                pass
            else:
                raise Conflict("freeze every trial before its first execution attempt")
            for kind, identity in (
                ("comparison-operation", trial.operation_id),
                ("comparison-mission", trial.mission.mission_id),
            ):
                if discovery._read(kind, identity, cx) is not None:
                    raise Conflict("comparison operation or ledger mission already belongs to a frozen cohort")
                discovery.journal.append(
                    cx,
                    key(kind, identity),
                    {
                        "comparison_id": plan.comparison_id,
                        "case_id": case.case_id,
                        "role": trial.role,
                        "runtime_config_digest": runtime_digest(discovery.journal.config.model_dump()),
                    },
                )


def _execution(discovery: Any, plan: ComparisonPlan, trial: ComparisonTrial, frozen: dict[str, Any], cx: Any) -> Any:
    try:
        record = dict(discovery.journal.latest(operation_key(trial.operation_id), cx))
    except KeyError:
        return None
    arm = next(arm for arm in plan.arms if arm.role == trial.role)
    profile = ExecutionProfile.model_validate(record["profile"])
    permit = ExecutionPermit.model_validate(record["permit"]["payload"]["permit"])
    claim = discovery._read("comparison-operation", trial.operation_id, cx)
    if (
        record["mission"] != trial.mission.model_dump()
        or digest("flywheel-execution-profile", profile) != arm.model_profile_digest
        or permit.operation_id != trial.operation_id
        or permit.request_digest != digest("flywheel-execution-request", trial.mission)
        or permit.profile_digest != arm.model_profile_digest
        or permit.environment_digest != arm.access_and_tools_digest
        or permit.bucket != "A"
        or permit.max_authorized_micro_usd != arm.resource_budget.cost_cap_micro_usd
        or claim is None
        or claim["comparison_id"] != plan.comparison_id
        or claim["role"] != trial.role
        or permit.config_digest != claim["runtime_config_digest"]
        or record["revision"] <= frozen["revision"]
    ):
        raise ValueError("actual execution differs from the prospectively frozen comparison condition")
    return record


def _recorded_acceptance(discovery: Any, trial: ComparisonTrial, record: Any, cx: Any) -> tuple[bool, Any]:
    """Inspect signed historical terms; this flag never grants current eligibility."""
    try:
        accepted = discovery.journal.latest(ACCEPTANCE_KEY + trial.operation_id, cx)
    except KeyError:
        return False, None
    reference = EvidenceRef(journal_key=ACCEPTANCE_KEY + trial.operation_id, record_digest=accepted["digest"])
    try:
        signed = SignedEnvelope.model_validate(accepted["acceptance"])
        payload = signed.payload
        terms = GeneralOriginAcceptance.model_validate(payload["record"])
        # Read only the independently installed public key, including revoked keys.
        # Current eligibility still goes through accepted_general_origin below.
        anchor = discovery.service.trust._anchors.get(signed.principal)
        if (
            anchor is None
            or "acceptance" not in anchor.roles
            or signed.domain != "flywheel-general-acceptance"
            or payload["journal_identity"] != discovery.journal.identity
            or terms.operation_id != trial.operation_id
            or accepted["record_digest"] != record["digest"]
            or terms.execution_record_digest != record["digest"]
            or terms.output_digest != digest("general-delivered-output", record["result"])
        ):
            raise ValueError("historical acceptance does not bind this exact delivery")
        commitment = digest(signed.domain, {"principal": signed.principal, "payload": payload})
        verify_ed25519(
            bytes.fromhex(anchor.public_key),
            base64.b64decode(signed.signature, validate=True),
            bytes.fromhex(commitment),
        )
        check_general_output(discovery.service, trial.operation_id, cx)
    except (Conflict, InvalidSignature, KeyError, TypeError, ValueError):
        return False, reference.model_dump()
    return True, reference.model_dump()


def _cell(discovery: Any, plan: ComparisonPlan, trial: ComparisonTrial, frozen: dict[str, Any], cx: Any) -> Any:
    cell: dict[str, Any] = {
        "role": trial.role,
        "operation_id": trial.operation_id,
        "ledger_mission_id": trial.mission.mission_id,
        "status": "not-attempted",
        "accepted": False,
        "outcome_known": False,
        "within_observed_limits": False,
        "execution_digest": None,
        "execution_authority_current": None,
        "acceptance_digest": None,
        "historical_acceptance_recorded": False,
        "historical_acceptance_evidence": None,
        "elapsed_ms": None,
        "tokens": None,
        "usage_complete": False,
        "actions": None,
        "model_component": trial.mission.components["model"],
        "mode": trial.mission.mode,
        "components": trial.mission.components,
    }
    try:
        record = _execution(discovery, plan, trial, frozen, cx)
    except (KeyError, ValueError, TypeError):
        cell["status"] = "binding-mismatch"
        return cell
    if record is None:
        return cell
    cell["execution_digest"] = record["digest"]
    try:
        authority = discovery.service.trust.verify(
            SignedEnvelope.model_validate(record["permit"]), "flywheel-execution-permit", "controller"
        )
        if authority["journal_identity"] != discovery.journal.identity:
            raise ValueError("supporting execution authority belongs to another journal")
    except (KeyError, TypeError, ValueError):
        cell["execution_authority_current"] = False
    else:
        cell["execution_authority_current"] = True
    if record["status"] not in TERMINAL:
        cell["status"] = "attempt-in-progress-or-unreconciled"
        return cell
    usage = record["usage_events"]
    tokens = sum(event["usage"]["total_tokens"] for event in usage)
    usage_complete = len(usage) == record["turn"]
    budget = next(arm.resource_budget for arm in plan.arms if arm.role == trial.role)
    cell.update(
        elapsed_ms=record["elapsed_ms"],
        tokens=tokens,
        usage_complete=usage_complete,
        actions=record["actions"],
        within_observed_limits=(
            usage_complete
            and tokens <= budget.tokens
            and record["actions"] <= budget.tool_actions
            and record["elapsed_ms"] <= budget.seconds * 1000
        ),
    )
    if record["status"] != "delivered-awaiting-independent-acceptance-and-costs":
        cell.update(status=record["status"], outcome_known=True)
        return cell
    historical, reference = _recorded_acceptance(discovery, trial, record, cx)
    cell.update(historical_acceptance_recorded=historical, historical_acceptance_evidence=reference)
    if reference is not None:
        cell["acceptance_digest"] = reference["record_digest"]
    try:
        accepted_general_origin(discovery.service, trial.operation_id, cx)
    except KeyError:
        cell["status"] = "acceptance-unassessed"
    except (ValueError, Conflict):
        cell["status"] = "acceptance-invalid-or-unsupported"
    else:
        cell.update(status="accepted-finite-placement", accepted=True, outcome_known=True)
    return cell


def _costs(discovery: Any, mission_id: str, buckets: list[str], cx: Any) -> dict[str, Any]:
    report = discovery.costs.report(mission_id, cx)
    ledger = discovery.costs.snapshot(cx)
    signatures_current = True
    supporting = [
        (row, {"charge", "resolve"})
        for row in ledger["charges"].values()
        if row["mission_id"] == mission_id and row["bucket"] in buckets
    ]
    seals = {"A": "seals", "B": "reuse_seals", "C": "investment_seals"}
    seal_actions = {"A": {"seal"}, "B": {"seal-reuse", "seal-retention"}, "C": {"seal-investment"}}
    supporting.extend((ledger.get(seals[bucket], {}).get(mission_id), seal_actions[bucket]) for bucket in buckets)
    for row, actions in supporting:
        if row is None:
            continue
        try:
            signed = SignedEnvelope.model_validate(row["signed"])
            domain, role = (
                ("flywheel-execution-permit", "controller")
                if signed.domain == "flywheel-execution-permit"
                and "activity_id" in row
                and row["accrued_micro_usd"] is None
                else ("flywheel-cost-command", "accounting")
            )
            payload = discovery.costs.trust.verify(signed, domain, role)
            if payload["journal_identity"] != discovery.journal.identity:
                raise ValueError("supporting accounting authority belongs to another journal")
            if domain == "flywheel-cost-command" and (
                payload.get("action") not in actions or payload["record"]["mission_id"] != mission_id
            ):
                raise ValueError("supporting accounting authority has different terms")
        except (KeyError, TypeError, ValueError):
            signatures_current = False
    historical_complete = all(report["bucket_complete"][bucket] for bucket in buckets)
    return {
        "mission_id": mission_id,
        "buckets": buckets,
        "known_micro_usd": {bucket: str(report["costs"][bucket]) for bucket in buckets},
        "complete": historical_complete and signatures_current,
        "historical_complete": historical_complete,
        "historical_bucket_complete": report["bucket_complete"],
        "supporting_signatures_current": signatures_current,
        "basis": report["evidence_basis"],
    }


def comparison_report(discovery: Any, identity: str) -> dict[str, Any]:
    """Keep the whole planned denominator, including missing and failed attempts."""
    with discovery.journal.transaction() as cx:
        discovery.service._state(cx)
        frozen = discovery._read("comparison", identity, cx)
        if frozen is None:
            raise KeyError(identity)
        plan = ComparisonPlan.model_validate(frozen["spec"])
        current = frozen["source"] == discovery.service.execution_digest
        try:
            discovery.service.trust.verify(
                SignedEnvelope.model_validate(frozen["signed"]), "flywheel-discovery-command", "controller"
            )
            discovery._opportunity(plan.opportunity_id, plan.opportunity_spec_digest, cx)
            discovery._evidence(plan.evidence, cx)
        except (Conflict, KeyError, ValueError):
            current = False
        ledger = discovery.costs.snapshot(cx)
        cells, cost_rows = [], []
        for case in plan.cases:
            for trial in case.trials:
                cell = _cell(discovery, plan, trial, frozen, cx)
                claim = discovery._read("comparison-operation", trial.operation_id, cx)
                if claim is None or claim["runtime_config_digest"] != runtime_digest(
                    discovery.journal.config.model_dump()
                ):
                    current = False
                cell.update(case_id=case.case_id, phase=case.phase, recipient_id=case.recipient_id)
                cells.append(cell)
                present = {
                    row["bucket"] for row in ledger["charges"].values() if row["mission_id"] == trial.mission.mission_id
                }
                row = _costs(discovery, trial.mission.mission_id, sorted(present | {"A"}), cx)
                row.update(role=trial.role, case_id=case.case_id, allocation="existing-delivery-costs")
                cost_rows.append(row)
                cap = next(arm.resource_budget.cost_cap_micro_usd for arm in plan.arms if arm.role == trial.role)
                known_delivery_cost = int(row["known_micro_usd"]["A"])
                delivery_cost_complete = row["historical_bucket_complete"]["A"] and row["supporting_signatures_current"]
                cost_status = (
                    "over-cap"
                    if known_delivery_cost > cap
                    else "within-cap"
                    if delivery_cost_complete
                    else "incomplete"
                )
                cell.update(
                    known_delivery_cost_micro_usd=str(known_delivery_cost),
                    delivery_cost_cap_micro_usd=str(cap),
                    delivery_cost_complete=delivery_cost_complete,
                    delivery_cost_status=cost_status,
                    within_observed_limits=cell["within_observed_limits"] and cost_status == "within-cap",
                )
        for scope in plan.additional_costs:
            row = _costs(discovery, scope.mission_id, [scope.bucket], cx)
            row.update(role=scope.role, case_id=None, allocation="additional-not-already-charged")
            cost_rows.append(row)
        current = (
            current
            and all(cell["execution_authority_current"] is not False for cell in cells)
            and all(row["supporting_signatures_current"] for row in cost_rows)
        )
        summaries: dict[str, Any] = {}
        for role in ROLES:
            observed = [cell for cell in cells if cell["role"] == role]
            costs = [row for row in cost_rows if row["role"] == role]
            summaries[role] = {
                "planned": len(observed),
                "execution_records": sum(cell["execution_digest"] is not None for cell in observed),
                "accepted": sum(cell["accepted"] for cell in observed),
                "historical_acceptance_recorded": sum(cell["historical_acceptance_recorded"] for cell in observed),
                "known_outcomes": sum(cell["outcome_known"] for cell in observed),
                "failed": sum(cell["outcome_known"] and not cell["accepted"] for cell in observed),
                "unassessed": sum(not cell["outcome_known"] for cell in observed),
                "within_observed_limits": all(cell["within_observed_limits"] for cell in observed) and bool(observed),
                "cost_complete": all(row["complete"] for row in costs) and bool(costs),
                "retention_accounting_present": any("B" in row["buckets"] for row in costs),
                "known_costs_micro_usd": {
                    bucket: str(sum(int(row["known_micro_usd"].get(bucket, "0")) for row in costs))
                    for bucket in ("A", "B", "C")
                },
            }
        contrasts = {}
        for name, baseline, candidate in (("operational", "U", "E"), ("retained", "E", "E+")):
            a, b = summaries[baseline], summaries[candidate]
            difference = b["accepted"] - a["accepted"]
            comparable = (
                bool(plan.cases)
                and current
                and a["unassessed"] == b["unassessed"] == 0
                and a["within_observed_limits"]
                and b["within_observed_limits"]
            )
            complete_costs = comparable and a["cost_complete"] and b["cost_complete"]
            if name == "retained" and not b["retention_accounting_present"]:
                complete_costs = False
            contrasts[name] = {
                "baseline": baseline,
                "candidate": candidate,
                "planned_denominator": len(plan.cases),
                "accepted_difference": difference,
                "possible_difference_bounds": [difference - a["unassessed"], difference + b["unassessed"]],
                "complete_matched_outcomes": comparable,
                "cost_saving_micro_usd": (
                    str(
                        sum(int(v) for v in a["known_costs_micro_usd"].values())
                        - sum(int(v) for v in b["known_costs_micro_usd"].values())
                    )
                    if complete_costs
                    else None
                ),
                "cost_basis": "existing signed ledger attestations; not inferred from token usage",
            }
        result = {
            "schema_name": "flywheel-operational-alpha-result/v1",
            "comparison_id": plan.comparison_id,
            "plan_record_digest": frozen["digest"],
            "ledger_record_digest": discovery.journal.latest(COST_KEY, cx)["digest"],
            "source_digest": discovery.service.execution_digest,
            "opportunity_id": plan.opportunity_id,
            "current_evidence_valid": current,
            "stage": "derived-observations" if plan.cases else "legacy-plan-without-frozen-cases",
            "planned_cases": len(plan.cases),
            "fresh_recipient_cases": sum(case.phase == "fresh-recipient" for case in plan.cases),
            "mode": plan.cases[0].trials[0].mission.mode if plan.cases else "not-executed",
            "human_reference": plan.human_reference.model_dump(),
            "human_reference_role": "commercial reference only; not another measured arm",
            "arms": summaries,
            "accepted_count_basis": "current-origin-eligibility; authenticated historical receipts counted separately",
            "contrasts": contrasts,
            "cells": cells,
            "cost_allocations": cost_rows,
            "model_evidence": (
                "simulated-model-protocol-fixture"
                if any(
                    cell["execution_digest"] is not None and cell["model_component"] == "simulated" for cell in cells
                )
                else "actual-model-records-with-unqualified-attribution"
                if any(cell["execution_digest"] is not None for cell in cells)
                else "no-executions"
            ),
            "scope": plan.purpose.scope,
            "authority_granted": False,
            "customer_acceptance_established": False,
            "commercial_profit_established": False,
            "retained_invocation_established": False,
            "limits": [
                "Descriptive finite cohort, not generality or causal proof of model superiority",
                "Workflow and recipient names are frozen declarations, not proof of independent operation or live ENS",
                "Distinct prospective inputs do not by themselves prove absence of training exposure",
                "Only the existing finite placement acceptance adapter is supported here",
                "Trial costs and declared additional scopes count once; completeness remains signer-attested",
                "Each trial's current complete A accrual must fit its frozen monetary cap; receipts and refunds do not net delivery costs",
                "Historical observations remain visible; current qualification rechecks execution and accounting signers",
                "Retained cost contrasts require explicit B accounting, including an attested zero where justified",
                "A declared retained input proves neither payload use, transfer nor incremental benefit",
                "Token counts are observed usage, not a provider bill or an enforced total-token limiter",
            ],
        }
        result["report_digest"] = digest("flywheel-operational-alpha-result", result)
        return result
