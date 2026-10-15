# SPDX-License-Identifier: Apache-2.0
"""Explicit synthetic Jobs browser handoff using the existing isolated computer executor."""

from __future__ import annotations

import base64
from collections.abc import Callable
import hashlib
import os
from pathlib import Path
from typing import Any, Literal
from types import SimpleNamespace
import uuid

from pydantic import Field

from . import ecosystem
from .models import StrictModel
from .store import Journal, Conflict, canonical, digest
from .supplier_browser_spec import SupplierSpec, read_spec, computer_task, extract_artifacts, MAX_RESULT_BYTES
from .successor import computer
from .successor.protocol import safe_json_loads
from .successor.trust import SignedEnvelope, TrustAnchor, TrustRegistry

PREFIX = "@supplier-browser:"


class ExecutorProfile(StrictModel):
    schema_id: Literal["agialpha.supplier-browser-profile.v1"] = Field(alias="schema")
    scope: Literal["synthetic-laboratory"]
    image: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provider: Literal["responses", "vision-json"]
    model: str = Field(min_length=1, max_length=200)
    base_url: str = Field(min_length=1, max_length=2048)
    key_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,79}$")


def bounded_file(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Expected a bounded regular file")
    with path.open("rb") as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("File grew beyond its bound")
    return raw


def installed_executor(journal: Journal) -> ExecutorProfile:
    return ExecutorProfile.model_validate(
        safe_json_loads(bounded_file(journal.root / "supplier-browser-profile.json", 16_000), max_bytes=16_000)
    )


def _advisor(profile: ExecutorProfile) -> computer.HTTPAdvisor:
    return computer.HTTPAdvisor(profile.provider, profile.model, profile.base_url, os.environ.get(profile.key_env, ""))


def _change(journal: Journal, key: str, revision: int, **changes: Any) -> dict[str, Any]:
    with journal.transaction() as cx:
        old = journal.latest(key, cx)
        if old["revision"] != revision:
            raise Conflict("Supplier browser record changed; inspect before continuing")
        return journal.append(cx, key, {**Journal.document(old), **changes})


def admit(journal: Journal, raw: bytes, job_id: str, worker: str, assignment_tx: str) -> dict[str, Any]:
    """Exact read-only assignment validation grants no execution permission."""
    journal.verify()
    _, spec_hash = read_spec(raw)
    profile = ecosystem.installed_profile(journal)
    observation = ecosystem.observe_assignment(profile, job_id, worker, spec_hash, assignment_tx)
    key = binding_key(observation)
    with journal.transaction() as cx:
        control = journal.latest("@control", cx)
        if control["state"] != "ready" or control["config_hash"] != digest(journal.config.model_dump()):
            raise Conflict("Agent is paused or configuration changed")
        try:
            old = journal.latest(key, cx)
        except KeyError:
            old = None
        if old is not None:
            for field in ("spec_hash", "worker", "profile_digest", "assignment_transaction"):
                if old["observation"][field] != observation[field]:
                    raise Conflict("Previously admitted supplier assignment differs")
            return old
        return journal.append(
            cx,
            key,
            {
                "state": "admitted",
                "spec_base64": base64.b64encode(raw).decode(),
                "observation": observation,
                "authority": [],
                "productionApproved": False,
            },
        )


def retained(journal: Journal, key: str) -> tuple[dict[str, Any], SupplierSpec, ecosystem.JobsProfile]:
    journal.verify()
    if not key.startswith(PREFIX) or len(key) != len(PREFIX) + 64:
        raise ValueError("Invalid supplier-browser binding")
    record = journal.latest(key)
    spec, spec_hash = read_spec(base64.b64decode(record["spec_base64"], validate=True))
    profile = ecosystem.installed_profile(journal)
    if (
        spec_hash != record["observation"]["spec_hash"]
        or digest(profile.model_dump()) != record["observation"]["profile_digest"]
    ):
        raise Conflict("Supplier specification or installed market profile changed")
    return record, spec, profile


def binding_key(observation: dict[str, Any]) -> str:
    return PREFIX + digest(
        {"chain": observation["chain_id"], "registry": observation["registry"], "job": observation["job_id"]}
    )


def permission_document(
    spec: SupplierSpec,
    obs: dict[str, Any],
    revision: int,
    profile: ExecutorProfile,
    advisor: computer.Advisor,
) -> dict[str, Any]:
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError("Permission requires an exact journal revision")
    key = binding_key(obs)
    task = computer_task(spec)
    execution_context = digest({"binding": key, "binding_revision": revision, "assignment": obs})
    task_commitment = computer.commitment(task, advisor, profile.image, execution_context)
    permit = digest(
        {
            "binding": key,
            "binding_revision": revision,
            "observation": obs,
            "executor_profile": profile.model_dump(),
            "computer_commitment": task_commitment,
        }
    )
    return {
        "permit": permit,
        "computer_commitment": task_commitment,
        "execution_context": execution_context,
        "binding_revision": revision,
        "executor_profile": profile.model_dump(by_alias=True),
        "binding": key,
        "limits": {"turns": task.max_turns, "actions": task.max_actions, "seconds": task.max_seconds},
        "billing": "UNKNOWN; configure provider-side spending limits",
        "scope": "synthetic-laboratory",
        "authority": [],
        "productionApproved": False,
    }


def prepare(journal: Journal, key: str) -> dict[str, Any]:
    """Display exact provider/image/assignment permission without a model call."""
    record, spec, market = retained(journal, key)
    control = journal.latest("@control")
    if control["state"] != "ready" or control["config_hash"] != digest(journal.config.model_dump()):
        raise Conflict("Agent is paused or configuration changed")
    obs = record["observation"]
    ecosystem.observe_assignment(market, obs["job_id"], obs["worker"], obs["spec_hash"], obs["assignment_transaction"])
    profile = installed_executor(journal)
    return permission_document(spec, obs, record["revision"], profile, _advisor(profile))


def execute(
    journal: Journal,
    key: str,
    permit: str,
    *,
    _factory: Callable[
        [str, computer.ComputerTask, Callable[[], None]], computer.DockerComputer
    ] = computer.DockerComputer,
) -> dict[str, Any]:
    initial, _, _ = retained(journal, key)
    if initial["state"] != "admitted":
        raise Conflict("Session already attempted; no implicit replay")
    permission = prepare(journal, key)
    if permission["permit"] != permit:
        raise ValueError("Permit differs from the exact assignment/provider/image/task")
    record, spec, _ = retained(journal, key)
    profile = installed_executor(journal)
    if profile.model_dump(by_alias=True) != permission["executor_profile"]:
        raise Conflict("Installed executor changed during preparation")
    advisor = _advisor(profile)
    if (
        computer.commitment(computer_task(spec), advisor, profile.image, permission["execution_context"])
        != permission["computer_commitment"]
    ):
        raise Conflict("Installed worker or provider changed during preparation")
    if record["state"] != "admitted" or record["revision"] != permission["binding_revision"]:
        raise Conflict("Session or exact permission revision changed; no implicit replay")
    attempt_id = str(uuid.uuid4())
    record = _change(journal, key, record["revision"], state="running", permission=permission, attempt_id=attempt_id)
    output = journal.root / ("supplier-browser-output-" + attempt_id)

    def admitted_factory(
        image: str, task: computer.ComputerTask, checkpoint: Callable[[], None]
    ) -> computer.DockerComputer:
        current = journal.latest(key)
        if current["state"] != "running" or current["revision"] != record["revision"]:
            raise Conflict("Supplier execution was revoked before actuator startup")
        return _factory(image, task, checkpoint)

    try:
        result = computer.run_session(
            journal,
            computer_task(spec),
            advisor,
            profile.image,
            output,
            permission["computer_commitment"],
            factory=admitted_factory,
            execution_context=permission["execution_context"],
        )
        session = journal.latest("@successor-computer:" + result["run_id"])
        if session["state"] != "review" or session.get("cleanup") != "VERIFIED":
            raise Conflict("Computer session is not cleanly awaiting review")
        envelope = SignedEnvelope.model_validate(
            safe_json_loads(bounded_file(output / "signed-receipt.json", 2_000_000), max_bytes=2_000_000)
        )
        trust = TrustRegistry({journal.identity: TrustAnchor(journal.public, frozenset({"computer"}))})
        observed_record = trust.verify(envelope, "computer-receipt", "computer")
        if observed_record != Journal.document(session):
            raise Conflict("Computer receipt differs from retained session")
        text = bounded_file(output / "visible-text.txt", MAX_RESULT_BYTES).decode("utf-8", errors="strict")
        if observed_record.get("observed_text_sha256") != hashlib.sha256(
            text.encode()
        ).hexdigest() or observed_record.get("observed_text_bytes") != len(text.encode()):
            raise Conflict("Observed browser file differs from the signed computer receipt")
        artifacts = extract_artifacts(spec, text)
        payload = {
            "computer_receipt": envelope.model_dump(),
            "observed_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "visible_text": text,
            "delivery": artifacts,
            "permission": permission,
        }
        return _change(
            journal,
            key,
            record["revision"],
            state="review",
            result=payload,
            result_hash=digest(payload),
            output_directory=output.name,
        )
    except BaseException as error:
        # A delayed attempt must never overwrite a later reconciled/new attempt.
        with journal.transaction() as cx:
            latest = journal.latest(key, cx)
            if latest.get("attempt_id") == attempt_id:
                terminal = "stopped" if latest["state"] == "stopped" else "interrupted"
                try:
                    guard = journal.latest("@successor-computer-task:" + permission["computer_commitment"], cx)
                    session = journal.latest("@successor-computer:" + guard["run_id"], cx)
                    if session["state"] == "quarantined":
                        terminal = "quarantined"
                    elif session["state"] == "stopped":
                        terminal = "stopped"
                except KeyError:
                    pass
                journal.append(
                    cx,
                    key,
                    {
                        **Journal.document(latest),
                        "state": terminal,
                        "error": type(error).__name__,
                        "output_directory": output.name,
                        "reconciliation": "Inspect retained computer session; no automatic replay",
                    },
                )
        raise


def review(journal: Journal, key: str, revision: int, result_hash: str, approve: bool, note: str) -> dict[str, Any]:
    record, _, _ = retained(journal, key)
    if not isinstance(approve, bool) or not isinstance(note, str) or (not note.strip() or len(note) > 2000):
        raise ValueError("Explicit decision and bounded review note required")
    if record["revision"] != revision or record["state"] != "review" or record["result_hash"] != result_hash:
        raise Conflict("Review must match the exact current result")
    return _change(
        journal,
        key,
        revision,
        state="approved" if approve else "rejected",
        local_review={
            "approved": approve,
            "note": note,
            "result_hash": result_hash,
            "scope": "local operator; marketplace validation remains separate",
        },
    )


def delivery(journal: Journal, key: str) -> dict[str, Any]:
    """Sign reviewed work only; callers must perform any market submission separately."""
    record, spec, profile = retained(journal, key)
    if record["state"] != "approved" or record.get("local_review", {}).get("approved") is not True:
        raise Conflict("An exact separate local approval is required")
    result = record["result"]
    if digest(result) != record["result_hash"] or record["local_review"]["result_hash"] != record["result_hash"]:
        raise Conflict("Reviewed result differs")
    session_id = result["computer_receipt"]["payload"]["run_id"]
    session = journal.latest("@successor-computer:" + session_id)
    if session["state"] != "review" or session.get("cleanup") != "VERIFIED":
        raise Conflict("Computer session was changed or stopped after execution")
    if canonical(extract_artifacts(spec, result["visible_text"])) != canonical(result["delivery"]):
        raise Conflict("Retained observed output differs")
    old = record["observation"]
    current = ecosystem.observe_assignment(
        profile, old["job_id"], old["worker"], old["spec_hash"], old["assignment_transaction"], states=(2, 3, 4, 5, 6)
    )
    body = {
        "schema": "agialpha.reviewed-supplier-browser-delivery.v1",
        "spec_base64": record["spec_base64"],
        "binding": old,
        "result": result,
        "local_review": record["local_review"],
        "authority": [],
        "productionApproved": False,
        "settlementApproved": False,
    }
    hashed = digest(body)
    with journal.transaction() as cx:
        fresh = journal.latest(key, cx)
        fresh_session = journal.latest("@successor-computer:" + session_id, cx)
        if fresh["revision"] != record["revision"] or fresh_session["revision"] != session["revision"]:
            raise Conflict("Local review or computer session changed during export")
        envelope = {
            "body": body,
            "public_key": journal.public,
            "sha256": hashed,
            "signature": base64.b64encode(journal.key.sign(bytes.fromhex(hashed))).decode(),
        }
    raw = canonical(envelope)
    if len(raw) > ecosystem.MAX_DELIVERY_BYTES:
        raise ValueError("Supplier browser export exceeds the shared artifact bound")
    result_hash = "0x" + hashlib.sha256(raw).hexdigest()
    if current["state"] != 2 and current["result_hash"] != result_hash:
        raise Conflict("Market result differs from this exact delivery")
    return {
        "artifact_base64": base64.b64encode(raw).decode(),
        "result_hash": result_hash,
        "scope": "synthetic computer laboratory; local review; no settlement authority",
    }


def stop(journal: Journal, key: str) -> dict[str, Any]:
    """Revoke a local in-flight session; its existing executor performs bounded cleanup."""
    journal.verify()
    if not key.startswith(PREFIX) or len(key) != len(PREFIX) + 64:
        raise ValueError("Invalid supplier-browser binding")
    record = journal.latest(key)
    if record["state"] not in {"running", "review"}:
        raise Conflict("Only active or unreviewed work can be stopped")
    with journal.transaction() as cx:
        current = journal.latest(key, cx)
        if current["revision"] != record["revision"]:
            raise Conflict("Supplier session changed")
        commitment = current["permission"]["computer_commitment"]
        try:
            guard = journal.latest("@successor-computer-task:" + commitment, cx)
            session_key = "@successor-computer:" + guard["run_id"]
            session = journal.latest(session_key, cx)
        except KeyError:
            session = None
        if session is not None and session["state"] != "quarantined":
            journal.append(cx, session_key, {**Journal.document(session), "state": "stopped"})
        return journal.append(cx, key, {**Journal.document(current), "state": "stopped"})


def verify_delivery(raw: bytes, trusted_key: str, expected_binding: dict[str, Any]) -> dict[str, Any]:
    """Verify exact local attribution and deterministic acceptance, never settlement."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    value = safe_json_loads(raw, max_bytes=ecosystem.MAX_DELIVERY_BYTES)
    if set(value) != {"body", "public_key", "sha256", "signature"} or value["public_key"] != trusted_key:
        raise ValueError("Supplier delivery identity or envelope differs")
    body = value["body"]
    if set(body) != {
        "schema",
        "spec_base64",
        "binding",
        "result",
        "local_review",
        "authority",
        "productionApproved",
        "settlementApproved",
    }:
        raise ValueError("Supplier delivery shape differs")
    if body["schema"] != "agialpha.reviewed-supplier-browser-delivery.v1" or body["binding"] != expected_binding:
        raise ValueError("Supplier delivery binding differs")
    if body["authority"] != [] or body["productionApproved"] is not False or body["settlementApproved"] is not False:
        raise ValueError("Supplier delivery cannot grant authority")
    if digest(body) != value["sha256"]:
        raise ValueError("Supplier delivery digest differs")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(trusted_key)).verify(
        base64.b64decode(value["signature"], validate=True), bytes.fromhex(value["sha256"])
    )
    spec, spec_hash = read_spec(base64.b64decode(body["spec_base64"], validate=True))
    if spec_hash != expected_binding["spec_hash"]:
        raise ValueError("Supplier work commitment differs")
    result = body["result"]
    if set(result) != {"computer_receipt", "observed_text_sha256", "visible_text", "delivery", "permission"}:
        raise ValueError("Supplier result shape differs")
    if hashlib.sha256(result["visible_text"].encode()).hexdigest() != result["observed_text_sha256"]:
        raise ValueError("Observed text commitment differs")
    if canonical(extract_artifacts(spec, result["visible_text"])) != canonical(result["delivery"]):
        raise ValueError("Supplier output fails deterministic acceptance")
    receipt = SignedEnvelope.model_validate(result["computer_receipt"])
    trust = TrustRegistry({receipt.principal: TrustAnchor(trusted_key, frozenset({"computer"}))})
    observed = trust.verify(receipt, "computer-receipt", "computer")
    if observed["state"] != "review" or observed.get("cleanup") != "VERIFIED":
        raise ValueError("Computer session is not cleanly reviewable")
    permission = result["permission"]
    profile = ExecutorProfile.model_validate(permission["executor_profile"])
    # Constructor validates identity syntax only; no request or credential access occurs.
    identity = computer.HTTPAdvisor(
        profile.provider, profile.model, profile.base_url, "identity-validation-only"
    ).identity
    expected_permission = permission_document(
        spec, expected_binding, permission["binding_revision"], profile, SimpleNamespace(identity=identity)
    )
    if canonical(permission) != canonical(expected_permission):
        raise ValueError("Exact assignment/task/provider/image permission differs")
    if (
        observed["commitment"] != expected_permission["computer_commitment"]
        or observed.get("execution_context") != expected_permission["execution_context"]
        or observed["provider"] != identity
    ):
        raise ValueError("Computer permission differs")
    if observed.get("observed_text_sha256") != result["observed_text_sha256"] or observed.get(
        "observed_text_bytes"
    ) != len(result["visible_text"].encode("utf-8")):
        raise ValueError("Observed output differs from signed computer receipt")
    review = body["local_review"]
    if (
        set(review) != {"approved", "note", "result_hash", "scope"}
        or review.get("approved") is not True
        or review.get("result_hash") != digest(result)
        or not isinstance(review.get("note"), str)
        or not review["note"].strip()
        or len(review["note"]) > 2000
        or review.get("scope") != "local operator; marketplace validation remains separate"
    ):
        raise ValueError("Exact local review is absent")
    return {
        "valid": True,
        "result_hash": "0x" + hashlib.sha256(raw).hexdigest(),
        "authority": [],
        "productionApproved": False,
        "settlementApproved": False,
    }


def reconcile(journal: Journal, key: str, revision: int, confirm: bool, note: str) -> dict[str, Any]:
    """Explicitly permit a new session only after retained cleanup; never resume old actions."""
    journal.verify()
    if confirm is not True or not isinstance(note, str) or (not note.strip() or len(note) > 2000):
        raise ValueError("Explicit reconciliation and bounded inspection note required")
    if not key.startswith(PREFIX) or len(key) != len(PREFIX) + 64:
        raise ValueError("Invalid supplier-browser binding")
    with journal.transaction() as cx:
        record = journal.latest(key, cx)
        if record["revision"] != revision or record["state"] not in {"stopped", "interrupted"}:
            raise Conflict("Only the exact stopped/interrupted attempt can be reconciled")
        history = record.get("reconciliations", [])
        if len(history) >= 16:
            raise Conflict("Bounded retry history exhausted; inspect without further execution")
        task_key = "@successor-computer-task:" + record["permission"]["computer_commitment"]
        try:
            guard = journal.latest(task_key, cx)
        except KeyError:
            guard = None
        if guard is not None:
            session = journal.latest("@successor-computer:" + guard["run_id"], cx)
            if session.get("cleanup") != "VERIFIED" or session["state"] not in {"stopped", "interrupted", "review"}:
                raise Conflict("Computer cleanup or terminal state remains uncertain")
            journal.append(cx, task_key, {**Journal.document(guard), "state": "reconciled"})
        return journal.append(
            cx,
            key,
            {
                **Journal.document(record),
                "state": "admitted",
                "reconciliations": history + [{"prior_revision": revision, "note": note, "new_session_required": True}],
                "result": None,
                "result_hash": None,
                "local_review": None,
                "attempt_id": None,
                "permission": None,
            },
        )


def main() -> None:
    """Operator CLI uses only installed profiles; imported work cannot configure execution."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    admission = sub.add_parser("admit")
    admission.add_argument("--spec", type=Path, required=True)
    admission.add_argument("--job-id", required=True)
    admission.add_argument("--worker", required=True)
    admission.add_argument("--assignment-tx", required=True)
    for name in ("prepare", "execute", "show", "stop", "review", "reconcile", "export"):
        command = sub.add_parser(name)
        command.add_argument("--binding", required=True)
        if name == "execute":
            command.add_argument("--permit", required=True)
        if name == "reconcile":
            command.add_argument("--revision", type=int, required=True)
            command.add_argument("--confirm", action="store_true", required=True)
            command.add_argument("--note", required=True)
        if name == "review":
            command.add_argument("--revision", type=int, required=True)
            command.add_argument("--result-hash", required=True)
            command.add_argument("--decision", choices=("approve", "reject"), required=True)
            command.add_argument("--note", required=True)
    args = parser.parse_args()
    journal = Journal(args.home)
    if args.action == "admit":
        result = admit(journal, bounded_file(args.spec, 64_000), args.job_id, args.worker, args.assignment_tx)
    elif args.action == "prepare":
        result = prepare(journal, args.binding)
    elif args.action == "execute":
        result = execute(journal, args.binding, args.permit)
    elif args.action == "show":
        result = retained(journal, args.binding)[0]
    elif args.action == "stop":
        result = stop(journal, args.binding)
    elif args.action == "reconcile":
        result = reconcile(journal, args.binding, args.revision, args.confirm, args.note)
    elif args.action == "review":
        result = review(journal, args.binding, args.revision, args.result_hash, args.decision == "approve", args.note)
    else:
        result = delivery(journal, args.binding)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
