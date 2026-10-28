# SPDX-License-Identifier: Apache-2.0
"""Accepted general-executor origin bindings for the placement capsule adapter."""

from __future__ import annotations

import copy
from typing import Any
from .protocol import Digest, Identifier, StrictModel

from ..store import Conflict
from .flywheel_execution import ExecutionPermit, operation_key
from .flywheel_experiments import PlacementProblem, verify_placement
from .protocol import digest

ACCEPTANCE_KEY = "@flywheel-general-acceptance:"


class GeneralOriginAcceptance(StrictModel):
    operation_id: Identifier
    execution_record_digest: Digest
    output_digest: Digest
    rights_evidence: Digest


def check_general_output(service: Any, operation: str, cx: Any) -> tuple[dict[str, Any], PlacementProblem]:
    record = service.journal.latest(operation_key(operation), cx)
    if record.get("status") != "delivered-awaiting-independent-acceptance-and-costs":
        raise ValueError("general origin requires a terminal actually delivered execution")
    if record["mission"]["mission_id"] != operation or record["actions"] < 1:
        raise ValueError("general origin must bind its actual tool-executed mission identity")
    problem = PlacementProblem.model_validate(record["mission"]["inputs"]["problem"])
    artifacts = record["result"]["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise ValueError("placement origin requires one exact tool artifact")
    artifact = artifacts[0]
    content = artifact["content"]
    if (
        artifact["kind"] != "placement-result"
        or artifact["digest"] != digest("placement-artifact", content)
        or content["problem"] != problem.model_dump()
        or content["outcome"] != record["result"]["deliverable"]
    ):
        raise ValueError("general origin artifact differs from the exact problem and delivered output")
    # An actual executor observation must contain the identical tool artifact.
    observed = False
    for item in record["history"]:
        if item.get("type") != "function_call_output":
            continue
        call_id = item["call_id"]
        for index in range(1, record["actions"] + 1):
            try:
                event = service.journal.latest(operation_key(operation) + f"/event/tool/{call_id}/{index}", cx)
            except KeyError:
                continue
            if event["value"] == content:
                observed = True
    if not observed or not verify_placement(problem, content["outcome"])["accepted_finite_result"]:
        raise ValueError("origin lacks an actual matching observation and independent finite acceptance")
    return record, problem


def _current_support(service: Any, operation: str, record: dict[str, Any], cx: Any) -> None:
    payload = service.costs.current_signature(record["permit"], "flywheel-execution-permit", "controller")
    permit = ExecutionPermit.model_validate(payload["permit"])
    if (
        set(payload) != {"journal_identity", "permit"}
        or permit.operation_id != operation
        or permit.request_digest != digest("flywheel-execution-request", record["mission"])
        or permit.profile_digest != digest("flywheel-execution-profile", record["profile"])
    ):
        raise ValueError("accepted delivery differs from its currently authorized execution permit")
    service.costs.require_current_evidence(record["mission"]["mission_id"], ["A"], cx)
    if not service.costs.report(record["mission"]["mission_id"], cx)["bucket_complete"]["A"]:
        raise ValueError("accepted delivery A costs must remain complete before a new protected use")


def accept_general_origin(service: Any, signed: Any) -> dict[str, Any]:
    from .trust import SignedEnvelope

    signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
    payload = service._signed(signed, "general-acceptance", "acceptance")
    terms = GeneralOriginAcceptance.model_validate(payload["record"]).model_dump(exclude={"schema_version"})
    with service.journal.transaction() as cx:
        service._state(cx)
        record, _ = check_general_output(service, terms["operation_id"], cx)
        _current_support(service, terms["operation_id"], record, cx)
        if (
            record["digest"] != terms["execution_record_digest"]
            or digest("general-delivered-output", record["result"]) != terms["output_digest"]
        ):
            raise ValueError("general acceptance identifies changed execution or output")
        service.library._distinct(signed.principal, "acceptance", service.library.producer, "producer")
        if not service.costs.report(terms["operation_id"], cx)["bucket_complete"]["A"]:
            raise ValueError("general delivery A costs must be complete before origin acceptance")
        key = ACCEPTANCE_KEY + terms["operation_id"]
        try:
            service.journal.latest(key, cx)
        except KeyError:
            pass
        else:
            raise Conflict("general origin acceptance already recorded")
        value = {"acceptance": signed.model_dump(), "record_digest": record["digest"]}
        service.journal.append(cx, key, value)
        service.checkpoint.advance(service.journal, cx)
        return value


def accepted_general_origin(
    service: Any, operation: str, cx: Any, *, require_current: bool = True
) -> tuple[dict[str, Any], PlacementProblem]:
    record, problem = check_general_output(service, operation, cx)
    accepted = service.journal.latest(ACCEPTANCE_KEY + operation, cx)
    from .trust import SignedEnvelope

    service.trust.verify(SignedEnvelope.model_validate(record["permit"]), "flywheel-execution-permit", "controller")
    signed = SignedEnvelope.model_validate(accepted["acceptance"])
    terms = service._signed(signed, "general-acceptance", "acceptance")["record"]
    if accepted["record_digest"] != record["digest"] or terms["execution_record_digest"] != record["digest"]:
        raise ValueError("accepted general execution changed since independent acceptance")
    if require_current:
        _current_support(service, operation, record, cx)
    return record, problem
