# SPDX-License-Identifier: Apache-2.0
"""Read execution-derived contrasts without creating acceptance, costs or authority."""

from __future__ import annotations

from typing import Any

from ..store import Conflict, digest as runtime_digest
from .flywheel_costs import KEY as COST_KEY
from .flywheel_discovery import ComparisonPlan, ComparisonTrial, key
from .flywheel_execution import ExecutionPermit, ExecutionProfile, operation_key
from .flywheel_learning import ACCEPTANCE_KEY, accepted_general_origin
from .protocol import digest
from .transformation_library import _is_exact_type
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


def _model_io(discovery: Any, trial: ComparisonTrial, record: dict[str, Any], cx: Any) -> dict[str, Any]:
    """Read durable request boundaries without turning a declared mode into provider proof."""
    result: dict[str, Any] = {
        "status": "insufficient-executor-boundary-evidence",
        "declared_component": trial.mission.components["model"],
        "request_boundary_lower_bound": 0,
        "recorded_response_count": 0,
        "processed_usage_count": None,
        "pending_model_request": None,
        "unresolved_request": None,
        "provider_call_count": None,
        "provider_provenance_verified": False,
    }
    turn, reserved, usage = (
        record.get("turn"),
        record.get("reserved_request_caps_micro_usd"),
        record.get("usage_events"),
    )
    if (
        not isinstance(turn, int)
        or not _is_exact_type(turn, int)
        or not 0 <= turn <= trial.mission.max_turns
        or not isinstance(reserved, int)
        or not _is_exact_type(reserved, int)
        or reserved < 0
        or not isinstance(usage, list)
        or not _is_exact_type(usage, list)
        or len(usage) > turn
    ):
        return result
    responses: dict[int, dict[str, Any]] = {}
    valid = True
    for index in range(turn):
        label = "model/" + str(index)
        try:
            event = discovery.journal.latest(operation_key(trial.operation_id) + "/event/" + label, cx)
        except KeyError:
            continue
        if (
            event.get("attempt") != label
            or event.get("components") != trial.mission.components
            or not isinstance(event.get("value"), dict)
        ):
            valid = False
            continue
        responses[index] = event["value"]
    for index, item in enumerate(usage):
        body = responses.get(index)
        if (
            body is None
            or not isinstance(item, dict)
            or item.get("response_digest") != digest("flywheel-responses-response", body)
            or item.get("usage") != body.get("usage")
            or item.get("model") != body.get("model")
        ):
            valid = False
    pending = record.get("pending")
    unresolved = False
    boundaries = set(responses)
    if isinstance(pending, str) and pending.startswith("model/"):
        suffix = pending.removeprefix("model/")
        if not suffix.isdecimal() or suffix != str(int(suffix)) or not 0 <= int(suffix) < turn:
            valid = False
        else:
            index = int(suffix)
            boundaries.add(index)
            unresolved = index not in responses
        result["pending_model_request"] = pending
    elif pending is not None and (not isinstance(pending, str) or not pending.startswith("tool/")):
        valid = False
    if reserved > 0 and not responses and not boundaries:
        unresolved = True
    result.update(
        request_boundary_lower_bound=len(boundaries),
        recorded_response_count=len(responses),
        processed_usage_count=len(usage),
        unresolved_request=unresolved if valid else None,
        status=(
            "insufficient-executor-boundary-evidence"
            if not valid
            else "request-boundary-unresolved"
            if unresolved
            else "response-recorded"
            if responses
            else "no-request-boundary-recorded"
        ),
    )
    return result


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
        "acceptance_digest": None,
        "elapsed_ms": None,
        "tokens": None,
        "usage_complete": False,
        "actions": None,
        "model_component": trial.mission.components["model"],
        "mode": trial.mission.mode,
        "components": trial.mission.components,
        "execution_authority_current": True,
        "model_io": {"status": "not-attempted", "provider_call_count": None, "provider_provenance_verified": False},
    }
    try:
        record = _execution(discovery, plan, trial, frozen, cx)
    except (KeyError, ValueError, TypeError):
        cell["status"] = "binding-mismatch"
        cell["model_io"]["status"] = "unbound-execution-record"
        return cell
    if record is None:
        return cell
    cell["execution_digest"] = record["digest"]
    cell["model_io"] = _model_io(discovery, trial, record, cx)
    try:
        discovery.costs.current_signature(record["permit"], "flywheel-execution-permit", "controller")
    except (KeyError, ValueError, TypeError):
        cell["execution_authority_current"] = False
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
    try:
        accepted_general_origin(discovery.service, trial.operation_id, cx, require_current=False)
        acceptance = discovery.journal.latest(ACCEPTANCE_KEY + trial.operation_id, cx)
    except KeyError:
        cell["status"] = "acceptance-unassessed"
    except (ValueError, Conflict):
        cell["status"] = "acceptance-invalid-or-unsupported"
    else:
        cell.update(status="accepted-finite-placement", accepted=True, outcome_known=True)
        cell["acceptance_digest"] = acceptance["digest"]
    return cell


def _costs(discovery: Any, mission_id: str, buckets: list[str], cx: Any) -> dict[str, Any]:
    report = discovery.costs.report(mission_id, cx)
    current = True
    try:
        discovery.costs.require_current_evidence(mission_id, buckets, cx)
    except (KeyError, ValueError, TypeError):
        current = False
    return {
        "mission_id": mission_id,
        "buckets": buckets,
        "known_micro_usd": {bucket: str(report["costs"][bucket]) for bucket in buckets},
        "complete": current and all(report["bucket_complete"][bucket] for bucket in buckets),
        "current_evidence_valid": current,
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
                current = current and cell["execution_authority_current"]
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
                current = current and row["current_evidence_valid"]
                row.update(role=trial.role, case_id=case.case_id, allocation="existing-delivery-costs")
                cost_rows.append(row)
        for scope in plan.additional_costs:
            row = _costs(discovery, scope.mission_id, [scope.bucket], cx)
            current = current and row["current_evidence_valid"]
            row.update(role=scope.role, case_id=None, allocation="additional-not-already-charged")
            cost_rows.append(row)
        summaries: dict[str, Any] = {}
        for role in ROLES:
            observed = [cell for cell in cells if cell["role"] == role]
            costs = [row for row in cost_rows if row["role"] == role]
            summaries[role] = {
                "planned": len(observed),
                "execution_records": sum(cell["execution_digest"] is not None for cell in observed),
                "accepted": sum(cell["accepted"] for cell in observed),
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
        executed = [cell for cell in cells if cell["execution_digest"] is not None]
        observed = [cell for cell in executed if cell["model_io"].get("recorded_response_count", 0) > 0]
        unresolved = any(
            cell["model_io"]["status"] in {"request-boundary-unresolved", "insufficient-executor-boundary-evidence"}
            for cell in executed
        )
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
            "contrasts": contrasts,
            "cells": cells,
            "cost_allocations": cost_rows,
            "model_evidence": (
                "no-executions"
                if not executed
                else "model-request-evidence-unresolved"
                if unresolved
                else "bound-executions-without-model-io-evidence"
                if not observed
                else "simulated-model-protocol-fixture"
                if all(cell["model_component"] == "simulated" for cell in observed)
                else "recorded-model-responses-provider-unverified"
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
                "Retained cost contrasts require explicit B accounting, including an attested zero where justified",
                "A declared retained input proves neither payload use, transfer nor incremental benefit",
                "Token counts are observed usage, not a provider bill or an enforced total-token limiter",
            ],
        }
        result["report_digest"] = digest("flywheel-operational-alpha-result", result)
        return result
