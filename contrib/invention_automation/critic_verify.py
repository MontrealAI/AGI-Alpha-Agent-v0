# SPDX-License-Identifier: Apache-2.0
"""Frozen read-only adjudicator for source-bound dimensional-screen objections.

This verifier imports no candidate runtime. It checks inert sources and static
control flow; it never runs the generated AST or certifies a publisher's claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
from fractions import Fraction
from pathlib import Path
from typing import Any

from .qualify_verify import (
    UNIT_DIMENSIONS,
    bounded,
    conventional_reference,
    keys,
    prove_program,
    read_json,
    require,
    sha,
    text,
    verify_request,
    verify_source_freeze,
)

OBJECTION_KEYS = {
    "id",
    "candidate_hash",
    "claim_id",
    "requirement_id",
    "requirement",
    "source",
    "witness",
    "consequence",
    "causal_explanation",
    "test",
    "retraction_criteria",
    "uncertainty",
    "alternatives",
    "missing_capabilities",
    "provenance",
    "severity",
    "evidence_strength",
    "revision",
    "parent_hash",
}
FREEZE_SCHEMA = "agialpha/critic-verifier-freeze/v1"
CONTEXT_SCHEMA = "agialpha/critic-context/v1"
STATIC_SCOPE = "source-field literal integrity and static dimensional dominance only; no candidate execution"


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_context(request: dict[str, Any], context: dict[str, Any]) -> None:
    """Check the frozen task authority and retrieval context, not remote authenticity."""
    bounded(context)
    keys(context, {"schema", "requirements", "sources", "bindings"})
    require(context["schema"] == CONTEXT_SCHEMA, "context schema")
    require(type(context["requirements"]) is dict, "context requirements")
    require(set(context["requirements"]) == set(request["requirements"]), "context requirement identity")
    for field, declaration in context["requirements"].items():
        keys(declaration, {"dimension", "authority", "labels", "location"})
        require(declaration["dimension"] == request["requirements"][field], "context dimension")
        require(declaration["authority"] == "declared-task", "requirement authority")
        text(declaration["location"])
        labels = declaration["labels"]
        require(type(labels) is list and 1 <= len(labels) <= 8, "bounded source labels")
        require(len(set(labels)) == len(labels), "unique labels")
        for label in labels:
            text(label, limit=120)
            require(re.fullmatch(r"[A-Za-z][A-Za-z0-9 _/-]*", label) is not None, "plain grounded label")
    require(type(context["sources"]) is list and 1 <= len(context["sources"]) <= 16, "bounded retrieval provenance")
    declarations = {}
    sources = {source["id"]: source for source in request["sources"]}
    for declaration in context["sources"]:
        keys(declaration, {"id", "sha256", "version", "retrieved_utc", "method", "url"})
        ident = declaration["id"]
        require(ident in sources and ident not in declarations, "retrieval source identity")
        require(declaration["sha256"] == sources[ident]["sha256"], "retrieval excerpt binding")
        require(declaration["url"] == sources[ident]["url"], "retrieval URL binding")
        for field in ["version", "retrieved_utc", "method"]:
            text(declaration[field])
        declarations[ident] = declaration
    require(set(declarations) == set(sources), "all sources need retrieval declarations")
    require(type(context["bindings"]) is list and len(context["bindings"]) <= 384, "bounded evidence bindings")
    records = {record["id"]: record for record in request["records"]}
    seen = set()
    for binding in context["bindings"]:
        keys(binding, {"record_id", "field", "source_id", "start", "end"})
        record_id, field, source_id = (binding[name] for name in ["record_id", "field", "source_id"])
        require(record_id in records and field in request["requirements"], "binding record/field")
        require(source_id == records[record_id]["source_id"], "binding record/source")
        start, end = binding["start"], binding["end"]
        require(type(start) is int and type(end) is int, "exact source offsets")
        require(0 <= start < end <= len(sources[source_id]["excerpt"]), "source offset bounds")
        ident = (record_id, field)
        require(ident not in seen, "unique record/field binding")
        seen.add(ident)


def _receipt(
    request: dict[str, Any],
    objection: dict[str, Any] | None,
    verdict: str,
    reason: str,
    *,
    evidence: list[str] | None = None,
    counterevidence: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "agialpha/critic-adjudication-verification/v1",
        "objection_id": None if objection is None else objection.get("id"),
        "objection_hash": None if objection is None else sha(objection),
        "candidate_hash": sha(request["baseline"]) if "baseline" in request else "UNKNOWN",
        "request_hash": sha(request),
        "verdict": verdict,
        "reason": reason,
        "evidence_hashes": evidence or [],
        "counterevidence": counterevidence or [],
        "scope": STATIC_SCOPE,
        "details": details or {},
        "candidate_executed": False,
        "technical_activity_accepted": False,
        "business_accepted": False,
        "confirmation": False,
        "provenance": {
            "role": "separate-read-only-static-verifier",
            "implementation": "contrib/invention_automation/critic_verify.py",
            "independence": "procedural separation; shared host, libraries, and mission context",
            "external_certification": False,
        },
    }


def field_literal(
    request: dict[str, Any], context: dict[str, Any], witness: dict[str, Any], source_location: dict[str, Any]
) -> tuple[bool, str, dict[str, Any]]:
    """Bind quantity to an authorized field label in one exact source clause.

    A source-wide number/unit match cannot attribute rated power to voltage.
    Label declarations are frozen task context, never generated by the critic.
    """
    required = {"record_id", "field", "value", "unit", "source_id", "start", "end"}
    if type(witness) is not dict or set(witness) != required:
        return False, "witness shape does not bind one field and source span", {}
    if any(
        type(witness[name]) is not str or not witness[name]
        for name in ["record_id", "field", "value", "unit", "source_id"]
    ):
        return False, "malformed witness scalar text", {}
    if any(type(witness[name]) is not int for name in ["start", "end"]):
        return False, "malformed witness exact offsets", {}
    records = {record["id"]: record for record in request["records"]}
    if witness["record_id"] not in records or witness["field"] not in request["requirements"]:
        return False, "witness record or requirement is absent", {}
    record = records[witness["record_id"]]
    field = witness["field"]
    reading = record["fields"].get(field)
    if reading is None or reading != {"value": witness["value"], "unit": witness["unit"]}:
        return False, "witness quantity differs from the retained record", {}
    if witness["source_id"] != record["source_id"]:
        return False, "witness source differs from the retained record", {}
    sources = {source["id"]: source for source in request["sources"]}
    source = sources[record["source_id"]]
    if source_location["source_id"] != source["id"] or source_location["sha256"] != source["sha256"]:
        return False, "objection source identity/hash contradicts retained evidence", {}
    bindings = [
        binding for binding in context["bindings"] if binding["record_id"] == record["id"] and binding["field"] == field
    ]
    if not bindings:
        return False, "no frozen field-specific source span was provided", {}
    binding = bindings[0]
    if any(witness[name] != binding[name] for name in ["record_id", "field", "source_id", "start", "end"]):
        return False, "witness span differs from the frozen evidence binding", {}
    index = next(index for index, item in enumerate(request["sources"]) if item["id"] == source["id"])
    expected_location = f"/sources/{index}/excerpt#chars={binding['start']}:{binding['end']}"
    if source_location["location"] != expected_location:
        return False, "objection exact source location differs from frozen span", {}
    span = source["excerpt"][binding["start"] : binding["end"]]
    if any(separator in span for separator in [";", "\n", "\r"]):
        return False, "evidence span crosses a clause boundary", {"span": span}
    normalized = span.casefold()
    labels = context["requirements"][field]["labels"]
    starts = []
    for label in labels:
        pattern = r"(?<![\w])" + re.escape(label.casefold()) + r"(?![\w])"
        starts.extend((match.start(), match.end()) for match in re.finditer(pattern, normalized))
    if len(starts) != 1:
        return False, "source span lacks one unambiguous authorized field label", {"span": span}
    _, label_end = starts[0]
    tail = span[label_end:]
    if any(
        other != field and any(label.casefold() in tail.casefold() for label in declaration["labels"])
        for other, declaration in context["requirements"].items()
    ):
        return False, "quantity/unit is not attributable while another field occurs in the same span", {"span": span}
    quantity = re.search(r"(?<![\w.])([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)(?![\w])", tail)
    if quantity is not None and Fraction(quantity[1]) == Fraction(reading["value"]) and quantity[2] == reading["unit"]:
        return (
            True,
            "field label and first exact quantity/unit occupy the same frozen clause",
            {
                "span": span,
                "source_hash": source["sha256"],
                "record_hash": sha(record),
                "location": expected_location,
            },
        )
    return False, "first quantity/unit is not attributable to the declared field in its frozen clause", {"span": span}


def adjudicate(
    request: dict[str, Any], context: dict[str, Any], objection: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Adjudicate only the registered static claim with counterevidence explicit."""
    try:
        verify_request(request)
        verify_context(request, context)
        baseline = prove_program(request["baseline"], request["requirements"], request["budget"], dominance=False)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        return _receipt(request, objection, "INCONCLUSIVE", "Invalid or incomplete frozen evidence: " + str(error))
    evidence = [sha(request), sha(context), sha(request["baseline"])]
    if objection is None:
        if not baseline["unsafe_fields"]:
            return _receipt(
                request,
                None,
                "NO_DEFECT_ESTABLISHED",
                "No dimensional-dominance violation established in the registered static search.",
                evidence=evidence,
                details={"baseline_static": baseline},
                counterevidence=["Every CONSISTENT branch has all declared dimension guards."],
            )
        return _receipt(
            request,
            None,
            "NO_DEFECT_ESTABLISHED",
            "No source-bound consequential objection was supplied; unsafe static paths alone were not promoted.",
            evidence=evidence,
            details={"baseline_static": baseline},
            counterevidence=["Static unsafe fields remain an unresolved investigation lead."],
        )
    try:
        bounded(objection)
        keys(objection, OBJECTION_KEYS)
        keys(objection["source"], {"source_id", "location", "sha256"})
        keys(
            objection["test"],
            {"id", "kind", "hypothesis", "pass_observation", "fail_observation", "unresolved", "estimated_cost"},
        )
        for name in [
            "id",
            "candidate_hash",
            "claim_id",
            "requirement_id",
            "requirement",
            "consequence",
            "causal_explanation",
            "uncertainty",
        ]:
            text(objection[name])
        for name in ["source_id", "location", "sha256"]:
            text(objection["source"][name])
        for name in ["id", "kind", "hypothesis", "pass_observation", "fail_observation"]:
            text(objection["test"][name])
        require(type(objection["witness"]) is dict, "typed witness mapping")
        require(re.fullmatch(r"[a-f0-9]{64}", objection["candidate_hash"]) is not None, "candidate hash")
        require(re.fullmatch(r"[a-f0-9]{64}", objection["source"]["sha256"]) is not None, "source hash")
    except (ValueError, TypeError, KeyError) as error:
        return _receipt(request, objection, "INCONCLUSIVE", "Malformed objection: " + str(error), evidence=evidence)
    if objection["candidate_hash"] != sha(request["baseline"]):
        return _receipt(request, objection, "REFUTED", "Objection identifies a different candidate.", evidence=evidence)
    if objection["claim_id"] != "dimensional-source-admission":
        return _receipt(
            request,
            objection,
            "INCONCLUSIVE",
            "The objection is outside the frozen dimensional-admission claim.",
            evidence=evidence,
        )
    field = objection["requirement_id"]
    if field not in request["requirements"]:
        return _receipt(
            request, objection, "REFUTED", "Objection cites no authoritative requirement.", evidence=evidence
        )
    if objection["test"]["kind"] == "dynamic-paired":
        return _receipt(
            request,
            objection,
            "INCONCLUSIVE",
            "Static evidence cannot adjudicate a dynamic output claim; restricted execution is required.",
            evidence=evidence,
            counterevidence=["Candidate has not executed in this verifier."],
        )
    if objection["test"]["kind"] not in {"static-dimension-dominance", "source-literal"}:
        return _receipt(
            request,
            objection,
            "INCONCLUSIVE",
            "Proposed experiment is not an installed trusted oracle.",
            evidence=evidence,
        )
    if field not in baseline["unsafe_fields"]:
        return _receipt(
            request,
            objection,
            "REFUTED",
            "Frozen candidate already guards this dimension on every accepting path.",
            evidence=evidence,
            details={"baseline_static": baseline},
            counterevidence=["The allegation's required missing guard is contradicted by symbolic control-flow proof."],
        )
    bound, reason, literal = field_literal(request, context, objection["witness"], objection["source"])
    if not bound:
        # A contradicted quantity or provenance is refuted; absence of a trustworthy
        # field attribution remains inconclusive rather than inventing a correction.
        contradicted = any(
            fragment in reason for fragment in ["differs", "contradicts", "not attributable", "lacks", "crosses"]
        )
        return _receipt(
            request,
            objection,
            "REFUTED" if contradicted else "INCONCLUSIVE",
            reason,
            evidence=evidence,
            details={"source_binding": literal},
            counterevidence=[reason],
        )
    witness = objection["witness"]
    if witness["field"] != field:
        return _receipt(
            request, objection, "REFUTED", "Witness concerns a different declared requirement.", evidence=evidence
        )
    if UNIT_DIMENSIONS.get(witness["unit"]) == request["requirements"][field]:
        return _receipt(
            request,
            objection,
            "REFUTED",
            "Literal unit has the required dimension; incompatibility is contradicted.",
            evidence=evidence,
            details={"source_binding": literal},
        )
    evidence.extend([literal["source_hash"], literal["record_hash"], sha(objection)])
    return _receipt(
        request,
        objection,
        "CONFIRMED",
        "The exact source-field literal has an incompatible dimension, and an accepting control-flow path lacks its required guard. This confirms only the registered static defect.",
        evidence=evidence,
        details={"baseline_static": baseline, "source_binding": literal},
        counterevidence=[
            "The publisher may contain a typo; intended replacement remains UNKNOWN.",
            "No runtime misclassification, engineering suitability, economic loss, or superiority over a conventional validator is established.",
        ],
    )


def accept(request: dict[str, Any], program: dict[str, Any], execution: dict[str, Any] | None) -> dict[str, Any]:
    """Check narrow output acceptance separately from objection adjudication.

    Execution receipts are trusted local-orchestrator inputs, not a signature or
    remote attestation. Fixture receipts test plumbing only. This method never
    starts a candidate interpreter or converts blocked execution to acceptance.
    """
    receipt = {
        "schema": "agialpha/critic-acceptance-verification/v1",
        "request_hash": sha(request),
        "program_hash": sha(program),
        "execution_hash": None if execution is None else sha(execution),
        "scope": "declared dimensional-screen contract only; no engineering suitability or business acceptance",
        "candidate_executed": False,
        "business_accepted": False,
        "confirmation": False,
        "receipt_trust": "locally supplied orchestrator receipt; no cryptographic execution attestation or external certification",
        "independence": "separate trusted verifier implementation/process, shared host and libraries",
    }
    try:
        verify_request(request)
        proof = prove_program(program, request["requirements"], request["budget"], dominance=True)
    except (ValueError, TypeError, KeyError) as error:
        return {**receipt, "acceptance": "REJECTED", "reason": "Static contract failed: " + str(error)}
    receipt["static_proof"] = proof
    if execution is None:
        return {
            **receipt,
            "acceptance": "STATIC_ONLY",
            "reason": "Static proof does not establish executed useful output.",
        }
    try:
        bounded(execution)
        if execution.get("status") == "BLOCKED" and execution.get("executed") is False:
            return {
                **receipt,
                "acceptance": "BLOCKED",
                "reason": "Restricted candidate execution is blocked; no host fallback or output acceptance.",
            }
        if execution.get("status") != "EXECUTED_UNVERIFIED" or execution.get("executed") is not True:
            return {**receipt, "acceptance": "REJECTED", "reason": "No successful restricted execution receipt."}
        keys(execution, {"status", "executed", "image", "artifact", "program_hash", "records_hash"})
        require(execution["program_hash"] == sha(program), "execution receipt program identity mismatch")
        require(
            execution["records_hash"] == sha(request["records"]), "execution receipt immutable record identity mismatch"
        )
        require(
            type(execution["image"]) is str
            and re.fullmatch(r"[A-Za-z0-9./:_-]+@sha256:[a-f0-9]{64}", execution["image"]) is not None,
            "digest-pinned execution image required",
        )
        artifact = execution["artifact"]
        keys(artifact, {"outputs", "trace", "operations"})
        expected = [{"id": row["id"], "status": row["status"]} for row in conventional_reference(request)]
        require(
            artifact["outputs"] == expected,
            "coverage, useful known-good delivery, or dimensional output disagrees with independent reference",
        )
        require(
            type(artifact["operations"]) is int and 1 <= artifact["operations"] <= 16_384,
            "exact bounded operation count",
        )
        require(
            type(artifact["trace"]) is list and len(artifact["trace"]) == artifact["operations"],
            "trace/operation accounting",
        )
        ids = {row["id"] for row in expected}
        for event in artifact["trace"]:
            keys(event, {"record", "op"})
            require(
                event["record"] in ids and event["op"] in {"sequence", "observe", "if", "emit"}, "trace event contract"
            )
        require({event["record"] for event in artifact["trace"]} == ids, "trace retains all admitted records")
    except (ValueError, TypeError, KeyError) as error:
        return {**receipt, "acceptance": "REJECTED", "reason": "Execution evidence failed: " + str(error)}
    return {
        **receipt,
        "acceptance": "ACCEPTED",
        "candidate_executed": True,
        "reason": "Static contract and all supplied restricted-run outputs match the independent dimensional reference.",
        "all_cohort_ids": [row["id"] for row in expected],
        "boundary": "No superiority, runtime security certification, commercial profitability, or general learning claim.",
    }


def verify_freeze(
    root: Path, freeze: dict[str, Any], request: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    keys(freeze, {"schema", "files", "protocol_path", "protocol_sha256", "request_hashes", "context_hashes"})
    require(freeze["schema"] == FREEZE_SCHEMA, "freeze schema")
    required = {
        "contrib/invention_automation/critic_verify.py",
        "contrib/invention_automation/qualify_verify.py",
        "contrib/invention_automation/readonly.py",
        "alpha_factory_v1/core/runtime/invention_automation/specification.py",
        "alpha_factory_v1/core/runtime/invention_automation/specification_run.py",
        "alpha_factory_v1/core/utils/secure_run.py",
        "alpha_factory_v1/core/runtime/invention_automation/critic_loop.py",
        "alpha_factory_v1/core/runtime/invention_automation/evidence_critic.py",
        "alpha_factory_v1/core/runtime/invention_automation/evidence_contracts.py",
        "alpha_factory_v1/core/runtime/invention_automation/operator.py",
        "alpha_factory_v1/core/runtime/structural_transfer/contracts.py",
        "alpha_factory_v1/core/runtime/invention_automation/critic_protocol.json",
    }
    require(required <= set(freeze["files"]), "verifier, candidate, and isolation source pins required")
    verify_source_freeze(root, freeze["files"])
    protocol_path = root / freeze["protocol_path"]
    require(protocol_path.resolve(strict=True).is_relative_to(root.resolve()), "protocol escapes repository")
    require(not any(path.is_symlink() for path in [protocol_path, *protocol_path.parents]), "protocol symlink")
    require(digest_file(protocol_path) == freeze["protocol_sha256"], "protocol freeze mismatch")
    require(
        freeze["files"].get(freeze["protocol_path"]) == freeze["protocol_sha256"], "protocol missing from source pins"
    )
    for name, value in [("request_hashes", request), ("context_hashes", context)]:
        require(type(freeze[name]) is list and 1 <= len(freeze[name]) <= 64, "bounded registered controls")
        require(sha(value) in freeze[name], "input not registered in frozen " + name)
    return read_json(protocol_path)


def main() -> None:
    from .readonly import enforce

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--objection", type=Path)
    parser.add_argument("--program", type=Path)
    parser.add_argument("--execution", type=Path)
    args = parser.parse_args()
    if (args.program is None) != (args.execution is None):
        parser.error("--program and --execution must be supplied together")
    if args.program is not None and args.objection is not None:
        parser.error("acceptance and objection adjudication are separate modes")
    restriction = enforce()
    request = read_json(args.request)
    context = read_json(args.context)
    objection = read_json(args.objection) if args.objection else None
    try:
        protocol = verify_freeze(args.root, read_json(args.freeze), request, context)
        own = args.root / "contrib/invention_automation/critic_verify.py"
        try:
            with own.open("ab"):
                pass
        except PermissionError:
            write_denied = True
        else:
            write_denied = False
        try:
            with socket.socket():
                pass
        except PermissionError:
            socket_denied = True
        else:
            socket_denied = False
        require(write_denied and socket_denied, "read-only/socket kernel restriction failed")
        receipt = (
            accept(request, read_json(args.program), read_json(args.execution))
            if args.program is not None
            else adjudicate(request, context, objection)
        )
        receipt.update(
            {
                "protocol_hash": sha(protocol),
                "source_freeze_verified": True,
                "freeze_verified": True,
                "restriction": restriction,
                "candidate_write_denied_by_os": write_denied,
                "new_socket_denied_by_os": socket_denied,
            }
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
    except (ValueError, TypeError, KeyError, OSError) as error:
        receipt = _receipt(request, objection, "INCONCLUSIVE", "Frozen verifier admission failed: " + str(error))
        receipt.update({"source_freeze_verified": False, "freeze_verified": False, "restriction": restriction})
        print(json.dumps(receipt, indent=2, sort_keys=True))
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
