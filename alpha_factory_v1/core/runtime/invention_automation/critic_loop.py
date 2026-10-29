# SPDX-License-Identifier: Apache-2.0
"""Native creator, evidence critic, separate adjudicator and correction loop.

Generated ASTs remain inert unless the inherited Docker boundary admits them.
The separate verifier reads frozen artifacts and never modifies the candidate.
"""

from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from ..structural_transfer.contracts import bounded, digest, read, write_new
from . import evidence_critic, specification_run
from . import specification as spec
from .evidence_contracts import Adjudication, Objection, Verdict

SCHEMA = "agialpha/evidence-critic-loop/v1"
ROOT = Path(__file__).resolve().parents[4]
GENERATION_CUTOFF = datetime(2026, 10, 29, 16, 53, tzinfo=UTC)


def verify_role(
    request_path: Path,
    context_path: Path,
    freeze_path: Path,
    *,
    objection_path: Path | None = None,
    program_path: Path | None = None,
    execution_path: Path | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "contrib.invention_automation.critic_verify",
        "--root",
        str(ROOT),
        "--freeze",
        str(freeze_path.resolve()),
        "--request",
        str(request_path.resolve()),
        "--context",
        str(context_path.resolve()),
    ]
    for flag, path in [("--objection", objection_path), ("--program", program_path), ("--execution", execution_path)]:
        if path is not None:
            command.extend([flag, str(path.resolve())])
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if len(result.stdout.encode()) > 1_048_576 or len(result.stderr.encode()) > 1_048_576:
        raise ValueError("verifier output bound")
    try:
        receipt = json.loads(result.stdout)
        bounded(receipt)
        if type(receipt) is not dict:
            raise ValueError("verifier receipt object required")
    except (ValueError, TypeError) as error:
        raise ValueError(
            "separate verifier unavailable; no host candidate fallback: " + result.stderr[-1000:]
        ) from error
    if result.returncode or receipt.get("freeze_verified") is not True:
        raise ValueError("separate source/protocol verification failed: " + str(receipt.get("reason", receipt)))
    if receipt.get("candidate_write_denied_by_os") is not True or receipt.get("new_socket_denied_by_os") is not True:
        raise ValueError("separate verifier restrictions not established")
    return cast(dict[str, Any], receipt)


def _adjudication(receipt: dict[str, Any], candidate_hash: str) -> Adjudication:
    if receipt.get("candidate_hash") != candidate_hash:
        raise ValueError("verifier candidate binding mismatch")
    return Adjudication(
        receipt.get("objection_id"),
        candidate_hash,
        Verdict(receipt["verdict"]),
        receipt["reason"],
        tuple(receipt["evidence_hashes"]),
        tuple(receipt["counterevidence"]),
        receipt["scope"],
        {"kind": "separate-read-only-verifier", "receipt_hash": digest(receipt), "external_certification": False},
    )


def construct_verified(
    request: dict[str, Any],
    context: dict[str, Any],
    objection: Objection,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    if receipt.get("verdict") != "CONFIRMED" or receipt.get("candidate_hash") != digest(request["baseline"]):
        raise ValueError("only a reproduced objection of this exact candidate can constrain construction")
    if receipt.get("objection_id") != objection.id or receipt.get("objection_hash") != objection.digest:
        raise ValueError("verifier objection identity mismatch")
    link = {k: objection.to_dict()["witness"][k] for k in ["record_id", "field", "source_id", "start", "end"]}
    valid, _ = evidence_critic.bound_literal(request, context, link)
    if not valid:
        raise ValueError("source association no longer valid")
    witness_request = deepcopy(request)
    witness_record = deepcopy(next(r for r in request["records"] if r["id"] == link["record_id"]))
    witness_record["fields"] = {link["field"]: witness_record["fields"][link["field"]]}
    witness_request["records"] = [witness_record]
    # Reuse the installed compiler over the adjudicated witness. Its complete
    # required-field grammar is unchanged; final testing retains the full cohort.
    legacy = spec.criticize(witness_request)
    if legacy["field"] != link["field"]:
        raise ValueError("legacy compiler witness differs from independently adjudicated source field")
    constraint = spec.constrain(witness_request, legacy)
    construction = spec.construct(witness_request, constraint)
    return {
        "constraint": {
            **constraint,
            "objection_hash": objection.digest,
            "verifier_receipt_hash": digest(receipt),
            "source_span": link,
            "full_request_hash": digest(request),
            "useful_outcome": "Every dimension-consistent record retained; incompatible/missing dimensions abstain.",
            "scope": "static contract only; runtime acceptance separate",
        },
        "construction": construction,
        "program": construction["program"],
        "prerequisites": [
            "Same field semantics, frozen requirements and lexical evidence association",
            "Independent runtime acceptance",
        ],
        "invalidation": [
            "Different quantity semantics",
            "Changed requirements/source versions",
            "Failed neighboring or known-good cases",
        ],
        "counterexamples": [
            "A dimensionally correct voltage can still be electrically unsuitable.",
            "A valid AST proof is not a runtime output test.",
        ],
        "promotion": "QUARANTINED_STATIC_ONLY",
    }


def _safe_directory(path: Path) -> None:
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError("symlink evidence path refused")
    if shutil.disk_usage(path.parent).free < 2 * 1024**3:
        raise ValueError("preserve inherited minimum 2 GiB free")


def execute_bound(program: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    result = specification_run.isolated(program, records)
    return {**result, "program_hash": digest(program), "records_hash": digest(records)}


def run(
    request_path: Path,
    context_path: Path,
    freeze_path: Path,
    output: Path,
    *,
    provenance: dict[str, Any] | None = None,
    objections_path: Path | None = None,
) -> dict[str, Any]:
    _safe_directory(output)
    if datetime.now(UTC) >= GENERATION_CUTOFF:
        raise ValueError("inherited generation cutoff reached; verify/resume only, no reset allowance")
    request, context = read(request_path), read(context_path)
    evidence_critic.validate_context(request, context)
    output.mkdir(parents=False, exist_ok=False)
    initial_cpu, initial_wall = time.process_time_ns(), time.monotonic_ns()
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    events: list[dict[str, Any]] = []

    def event(stage: str, payload: Any) -> None:
        entry = {
            "index": len(events),
            "stage": stage,
            "payload_hash": digest(payload),
            "previous": digest(events[-1]) if events else None,
        }
        events.append(entry)
        write_new(output / f"event-{entry['index']:02}.json", entry)

    try:
        write_new(output / "request.json", request)
        write_new(output / "context.json", context)
        write_new(output / "freeze.json", read(freeze_path))
        gate = verify_role(output / "request.json", output / "context.json", freeze_path)
        write_new(output / "initial-verification.json", gate)
        event("frozen-input-and-source-admission", gate)
        attribution = provenance or {
            "kind": "deterministic-source-investigator",
            "model": "NONE",
            "usage": "NOT_A_MODEL_CALL",
            "limitations": "Actual host critic is separately retained; runtime scanner is supplied trusted software.",
        }
        finding = evidence_critic.investigate(request, context, attribution)
        write_new(output / "finding.json", finding.to_dict())
        event("creator-artifact-and-critic-finding", finding.to_dict())
        objections = list(finding.objections)
        if objections_path is not None:
            supplied = read(objections_path)
            if type(supplied) is not list or len(supplied) > 16:
                raise ValueError("bounded typed host objection list required")
            additions = [Objection.from_dict(x) for x in supplied]
            if any(o.candidate_hash != digest(request["baseline"]) for o in additions):
                raise ValueError("host objection candidate mismatch")
            objections.extend(additions)
            write_new(output / "host-objections-original.json", supplied)
        if len({o.id for o in objections}) != len(objections):
            raise ValueError("duplicate objection identity; revisions need separate records")
        verdicts = []
        confirmed = []
        if not objections:
            judgement = _adjudication(gate, digest(request["baseline"]))
            verdicts.append(judgement.to_dict())
        for i, objection in enumerate(objections):
            path = output / f"objection-{i:02}.json"
            write_new(path, objection.to_dict())
            receipt = verify_role(output / "request.json", output / "context.json", freeze_path, objection_path=path)
            write_new(output / f"adjudication-raw-{i:02}.json", receipt)
            judgement = _adjudication(receipt, digest(request["baseline"]))
            verdicts.append(judgement.to_dict())
            event("executable-static-adjudication", receipt)
            if judgement.verdict == Verdict.CONFIRMED:
                confirmed.append((objection, receipt))
        write_new(output / "verdicts.json", verdicts)
        adaptation = None
        if confirmed:
            if datetime.now(UTC) >= GENERATION_CUTOFF:
                raise ValueError(
                    "inherited generation cutoff reached during adjudication; no new candidate constructed"
                )
            # Ranked supported objections determine the first adaptation; additional
            # confirmed objections remain visible and do not reset the budget.
            confirmed.sort(key=lambda pair: (-pair[0].evidence_strength, -pair[0].severity, pair[0].id))
            adaptation = construct_verified(request, context, *confirmed[0])
            write_new(output / "adaptation.json", adaptation)
            event("verified-constraint-to-compositional-ast", adaptation)
        baseline_execution = execute_bound(request["baseline"], request["records"])
        write_new(output / "baseline-execution.json", baseline_execution)
        execution = {"status": "NOT_ATTEMPTED", "executed": False, "reason": "no confirmed corrective constraint"}
        acceptance = {"acceptance": "UNKNOWN", "scope": "No corrective candidate proposed.", "confirmation": False}
        if adaptation is not None:
            # A missing boundary is not a reason to rerun the same failed probe.
            execution = (
                {
                    **baseline_execution,
                    "reason": baseline_execution.get("reason", "boundary blocked"),
                    "shared_boundary_probe": True,
                    "program_hash": digest(adaptation["program"]),
                }
                if baseline_execution["status"] == "BLOCKED"
                else execute_bound(adaptation["program"], request["records"])
            )
            write_new(output / "program.json", adaptation["program"])
            write_new(output / "execution.json", execution)
            acceptance = verify_role(
                output / "request.json",
                output / "context.json",
                freeze_path,
                program_path=output / "program.json",
                execution_path=output / "execution.json",
            )
            write_new(output / "acceptance.json", acceptance)
            event("separate-final-acceptance", acceptance)
        reference = spec.inspect_records(request)
        write_new(output / "conventional-reference.json", reference)
        late_children = resource.getrusage(resource.RUSAGE_CHILDREN)
        costs = {
            "event_id": "critic-loop-"
            + digest({"request": request, "context": context, "output": str(output.resolve())})[:24],
            "enclosing_process_cpu_ns": time.process_time_ns() - initial_cpu,
            "enclosing_wall_ns": time.monotonic_ns() - initial_wall,
            "child_cpu_seconds": str(
                late_children.ru_utime + late_children.ru_stime - children.ru_utime - children.ru_stime
            ),
            "model_tokens": "UNKNOWN; host role usage not exposed",
            "retrieval_and_development_cost": "UNKNOWN",
            "actual_external_cash_paid": 0,
            "complete_economic_cost": "UNKNOWN",
            "accounting": "One enclosing event; nested stage costs are diagnostic, never added again.",
        }
        write_new(output / "costs.json", costs)
        result = {
            "schema": SCHEMA,
            "request_hash": digest(request),
            "context_hash": digest(context),
            "candidate_hash": digest(request["baseline"]),
            "finding": finding.to_dict(),
            "verdicts": verdicts,
            "adaptation_hash": digest(adaptation) if adaptation else None,
            "execution": execution,
            "acceptance": acceptance,
            "complete_loop_status": (
                "BLOCKED" if execution["executed"] is False else "EXECUTED_REQUIRES_PAIRED_ANALYSIS"
            ),
            "comparison": {
                "reference": "Strong conventional dimensional/schema validator",
                "reference_outcomes": reference,
                "effect_size": "UNKNOWN; no dynamic paired output unless both executions admitted",
                "false_rejection_rate": "UNKNOWN for generated candidate; reference all-outcome list retained",
                "harmful_regression": "UNKNOWN while generated candidate execution blocked",
                "five_arm_comparison": "NOT_RUN; first dynamic useful probe unavailable",
            },
            "economics": {
                "cohort_admitted": False,
                "complete_cost_profit": "UNKNOWN",
                "earned_surplus": "0",
                "payback": "UNKNOWN",
                "unrestricted_cash": "UNKNOWN",
                "NPV": "UNKNOWN",
                "investment_attractiveness": "UNKNOWN",
                "full_flywheel": "NOT_ESTABLISHED",
            },
            "experience": "STATIC QUARANTINE; no fresh causal benefit or weight training established",
            "model_path": {
                "creator": request["author"],
                "runtime_critic": "Supplied deterministic source investigator; actual host critic transcript retained separately.",
                "runtime_frontier_model": "BLOCKED; no authorized no-cost runtime model endpoint exposed",
                "paid_api_calls": 0,
                "observable_model_usage": "UNKNOWN, not zero",
            },
            "costs": costs,
            "event_chain": events,
            "confirmation": False,
            "shared_infrastructure": "Roles share host, model family where exposed, Python libraries and input corpus; procedural separation only.",
        }
        write_new(output / "result.json", result)
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
        write_new(output / "checkpoint.json", {"schema": SCHEMA, "files": files})
        return result
    except Exception as error:
        write_new(
            output / "failure.json",
            {
                "schema": SCHEMA,
                "error": type(error).__name__,
                "reason": str(error),
                "events": events,
                "cpu_ns": time.process_time_ns() - initial_cpu,
                "wall_ns": time.monotonic_ns() - initial_wall,
                "confirmation": False,
                "retry_rule": "preserve this attempt; never reset allocation",
            },
        )
        raise


def resume(output: Path) -> dict[str, Any]:
    _safe_directory(output)
    checkpoint = read(output / "checkpoint.json")
    if set(checkpoint) != {"schema", "files"} or checkpoint["schema"] != SCHEMA:
        raise ValueError("critic checkpoint schema")
    if "result.json" not in checkpoint["files"]:
        raise ValueError("incomplete critic checkpoint")
    for name, expected in checkpoint["files"].items():
        if Path(name).name != name:
            raise ValueError("checkpoint path escape")
        path = output / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("checkpoint corruption: " + name)
    request, context = read(output / "request.json"), read(output / "context.json")
    verify_role(output / "request.json", output / "context.json", output / "freeze.json")
    result = read(output / "result.json")
    if result["request_hash"] != digest(request) or result["context_hash"] != digest(context):
        raise ValueError("checkpoint identity mismatch")
    return cast(dict[str, Any], result)
