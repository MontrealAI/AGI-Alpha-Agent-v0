#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Qualify a frozen AST via unchanged Docker isolation, never host execution.

Exposed component testing only: no source authentication, physical suitability,
commercial validation, or new synthesis campaign.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

IMAGE = re.compile(r"[A-Za-z0-9./:_-]+@sha256:[a-f0-9]{64}")


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def expected_outputs(request: dict[str, Any]) -> list[dict[str, str]]:
    """Independent dimensional oracle; never import the candidate's unit table."""
    accepted = {"voltage": {"V", "kV"}, "apparent_power": {"VA", "kVA", "MVA"}, "frequency": {"Hz"}}
    requirements, records = request["requirements"], request["records"]
    if not isinstance(requirements, dict) or not 1 <= len(requirements) <= 6:
        raise ValueError("one to six requirements needed")
    if any(dimension not in accepted for dimension in requirements.values()):
        raise ValueError("unknown required dimension")
    if not isinstance(records, list) or not 1 <= len(records) <= 64:
        raise ValueError("one to 64 records needed")
    seen = set()
    outputs = []
    for record in records:
        ident = record["id"]
        if not isinstance(ident, str) or not ident or ident in seen:
            raise ValueError("nonempty unique record IDs needed")
        seen.add(ident)
        fields = record["fields"]
        if not isinstance(fields, dict):
            raise TypeError("record fields must be an object")
        consistent = all(
            isinstance(fields.get(field), dict) and fields[field].get("unit") in accepted[dimension]
            for field, dimension in requirements.items()
        )
        outputs.append({"id": ident, "status": "CONSISTENT" if consistent else "ABSTAIN"})
    return outputs


def verify_receipt(receipt: dict[str, Any], expected: list[dict[str, str]], image: str) -> None:
    """Reject absent execution and exact-output mismatches, including ID/order changes."""
    if not IMAGE.fullmatch(image):
        raise ValueError("digest-pinned image required")
    if receipt.get("status") != "EXECUTED_UNVERIFIED" or receipt.get("executed") is not True:
        raise ValueError("successful real execution required")
    if receipt.get("image") != image:
        raise ValueError("execution image mismatch")
    artifact = receipt.get("artifact")
    if not isinstance(artifact, dict) or set(artifact) != {"outputs", "trace", "operations"}:
        raise ValueError("execution artifact schema mismatch")
    if artifact["outputs"] != expected:
        raise ValueError("independent semantic outputs mismatch")
    operations, trace = artifact["operations"], artifact["trace"]
    if type(operations) is not int or not 1 <= operations <= 16384:
        raise ValueError("operation bound")
    if not isinstance(trace, list) or len(trace) != operations:
        raise ValueError("trace length mismatch")
    ids = {record["id"] for record in expected}
    for event in trace:
        if not isinstance(event, dict) or set(event) != {"record", "op"}:
            raise ValueError("trace schema mismatch")
        if event["record"] not in ids or event["op"] not in {"observe", "emit", "sequence", "if"}:
            raise ValueError("trace event mismatch")
    if {event["record"] for event in trace} != ids:
        raise ValueError("incomplete trace")


def qualify(
    request: dict[str, Any],
    program: dict[str, Any],
    evidence: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
    freeze: dict[str, Any] | None = None,
) -> None:
    """Populate evidence in place so failed execution receipts are retained."""
    evidence.update(
        request_sha256=digest(request),
        program_sha256=digest(program),
        cohort_sha256=digest(request["records"]),
        source_evidence_sha256=digest(request["sources"]),
    )
    if "proposal" not in request or digest(program) != digest(request["proposal"]):
        raise ValueError("program is not the retained proposal bound by the frozen request")
    evidence["retained_proposal_bound"] = True
    expected = expected_outputs(request)
    if {row["status"] for row in expected} != {"CONSISTENT", "ABSTAIN"}:
        raise ValueError("qualification cohort must include both consistent and inconsistent records")
    evidence["expected_outputs"] = expected
    if not shutil.which("docker"):
        evidence.update(status="BLOCKED", reason="Docker unavailable; no host execution fallback")
        return
    image = os.environ.get("ALPHA_SANDBOX_IMAGE", "")
    if not IMAGE.fullmatch(image):
        evidence.update(status="BLOCKED", reason="locally provisioned digest-pinned image required")
        return
    if context is None or freeze is None:
        raise ValueError("explicit frozen context and source freeze required")
    evidence.update(context_sha256=digest(context), freeze_sha256=digest(freeze))
    # No generator is invoked: the retained candidate is requalified after its
    # original campaign, without changing or resetting its generation cutoff.
    from alpha_factory_v1.core.runtime.invention_automation import critic_loop
    from alpha_factory_v1.core.runtime.invention_verification.qualify_verify import prove_program

    evidence["image"] = image
    evidence["implementation_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="alpha-retained-ast-qualification-") as directory:
        root = Path(directory)
        for name, value in {"request": request, "program": program, "context": context, "freeze": freeze}.items():
            (root / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        admission = critic_loop.verify_role(root / "request.json", root / "context.json", root / "freeze.json")
        evidence["frozen_admission"] = admission
        if admission.get("request_hash") != digest(request) or admission.get("candidate_hash") != digest(
            request["baseline"]
        ):
            raise ValueError("frozen admission request/baseline identity mismatch")
        require_restrictions(admission)
        evidence["pre_execution_static_proof"] = prove_program(
            program, request["requirements"], request["budget"], dominance=True
        )
        receipt = critic_loop.execute_bound(program, request["records"])
        evidence["candidate_execution"] = receipt
        if receipt.get("status") == "BLOCKED":
            evidence.update(status="BLOCKED", reason=receipt.get("reason", "sandbox unavailable"))
            return
        verify_bound_receipt(receipt, program, request["records"])
        verify_receipt(receipt, expected, image)
        execution_path = root / "execution.json"
        execution_path.write_text(json.dumps(receipt), encoding="utf-8")
        acceptance = critic_loop.verify_role(
            root / "request.json",
            root / "context.json",
            root / "freeze.json",
            program_path=root / "program.json",
            execution_path=execution_path,
        )
        evidence["separate_acceptance"] = acceptance
        require_restrictions(acceptance)
        if (
            acceptance.get("acceptance") != "ACCEPTED"
            or acceptance.get("candidate_executed") is not True
            or acceptance.get("program_hash") != digest(program)
            or acceptance.get("request_hash") != digest(request)
            or acceptance.get("execution_hash") != digest(receipt)
            or acceptance.get("confirmation") is not False
            or acceptance.get("business_accepted") is not False
        ):
            raise ValueError("separate acceptance rejected or identity/scope mismatch")
        control = {"op": "emit", "status": "CONSISTENT"}
        evidence["negative_control_program_sha256"] = digest(control)
        negative = critic_loop.execute_bound(control, request["records"])
        evidence["negative_control_execution"] = negative
        verify_bound_receipt(negative, control, request["records"])
        wrong = [{"id": row["id"], "status": "CONSISTENT"} for row in expected]
        verify_receipt(negative, wrong, image)  # Crashed/blocked controls do not count.
        try:
            verify_receipt(negative, expected, image)
        except ValueError:
            evidence["negative_control_rejected"] = True
        else:
            raise ValueError("known-defective control was accepted")
        negative_program_path = root / "negative-program.json"
        negative_execution_path = root / "negative-execution.json"
        negative_program_path.write_text(json.dumps(control), encoding="utf-8")
        negative_execution_path.write_text(json.dumps(negative), encoding="utf-8")
        negative_acceptance = critic_loop.verify_role(
            root / "request.json",
            root / "context.json",
            root / "freeze.json",
            program_path=negative_program_path,
            execution_path=negative_execution_path,
        )
        evidence["negative_native_acceptance"] = negative_acceptance
        require_restrictions(negative_acceptance)
        if (
            negative_acceptance.get("acceptance") != "REJECTED"
            or negative_acceptance.get("program_hash") != digest(control)
            or negative_acceptance.get("request_hash") != digest(request)
            or negative_acceptance.get("execution_hash") != digest(negative)
            or negative_acceptance.get("confirmation") is not False
            or negative_acceptance.get("business_accepted") is not False
        ):
            raise ValueError("native negative acceptance did not reject the exact executed control")
        evidence["negative_native_rejected"] = True
        evidence["negative_native_scope"] = (
            "Native rejection may be static; wrong actual outputs are also checked by the separate semantic oracle."
        )
    evidence["status"] = "DYNAMIC_COMPONENT_PASS"


def verify_bound_receipt(receipt: dict[str, Any], program: dict[str, Any], records: list[dict[str, Any]]) -> None:
    if receipt.get("program_hash") != digest(program) or receipt.get("records_hash") != digest(records):
        raise ValueError("execution program/cohort identity mismatch")


def require_restrictions(receipt: dict[str, Any]) -> None:
    for key in ("freeze_verified", "source_freeze_verified", "candidate_write_denied_by_os", "new_socket_denied_by_os"):
        if receipt.get(key) is not True:
            raise ValueError("separate verifier source freeze or restrictions unestablished")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--program", type=Path, required=True, help="JSON AST itself, not a bundle")
    parser.add_argument(
        "--output", type=Path, required=True, help="new evidence file; never overwrite historical results"
    )
    args = parser.parse_args()
    evidence: dict[str, Any] = {
        "schema": "agialpha/invention-dynamic-qualification/v1",
        "status": "FAILED",
        "confirmation": False,
        "scope": (
            "runtime requalification of retained AST; no fresh discovery, provenance authentication, "
            "physical or commercial qualification"
        ),
    }
    with args.output.open("x", encoding="utf-8") as output:
        try:
            values = {}
            for name in ("request", "program", "context", "freeze"):
                path = getattr(args, name)
                if path.stat().st_size > 1024 * 1024:
                    raise ValueError("fixture exceeds 1 MiB bound")
                raw = path.read_bytes()
                if len(raw) > 1024 * 1024:
                    raise ValueError("fixture exceeds 1 MiB bound")
                evidence[name + "_file_sha256"] = hashlib.sha256(raw).hexdigest()
                values[name] = json.loads(raw)
            qualify(values["request"], values["program"], evidence, context=values["context"], freeze=values["freeze"])

        except Exception as error:
            evidence.update(status="FAILED", reason=f"{type(error).__name__}: {error}")
            raise
        finally:
            output.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": evidence["status"], "output": str(args.output)}))
    return 0 if evidence["status"] == "DYNAMIC_COMPONENT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
