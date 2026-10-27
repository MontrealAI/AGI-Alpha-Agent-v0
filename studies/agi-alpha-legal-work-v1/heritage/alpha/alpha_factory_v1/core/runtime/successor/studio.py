# SPDX-License-Identifier: Apache-2.0
"""Portable Studio requests bound to the existing authorized Ascension executor."""

from __future__ import annotations

import base64
import hashlib
import os
import platform
import re
import shutil
import subprocess
import uuid
from collections.abc import Callable
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature

from .. import ascension as legacy
from ..store import Conflict, Journal
from . import ascension, workbench
from .jobs import JobDispatcher, JobResult
from .protocol import (
    BehaviorArtifact,
    CandidateReleaseManifest,
    ExecutionAuthorization,
    JobContract,
    JobGraph,
    ResourceBudget,
    canonical,
    digest,
    safe_json_loads,
)
from .signatures import verify_ed25519
from .state import SuccessorStore
from .trust import SignedEnvelope

REQUEST_SCHEMA = "agialpha.ascension.studio-work.v1"
RESULT_SCHEMA = "agialpha.ascension.studio-result.v1"
ARTIFACT_SCHEMA = "agialpha.ascension.work-artifact.v1"
TOOL = "fixed-workbench"
FAMILIES = frozenset({"reliability", "performance", "documentation", "public-data", "numerical"})


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    """Validate inert public inputs without taking trust, endpoints or executable paths."""
    value = safe_json_loads(canonical(request))
    if set(value) != {"schema", "project_id", "cycle_id", "plan", "plan_index", "work_spec"}:
        raise ValueError("Studio work request has unexpected fields")
    if value["schema"] != REQUEST_SCHEMA:
        raise ValueError("Unsupported Studio work request")
    for name in ("project_id", "cycle_id"):
        if not isinstance(value[name], str) or str(uuid.UUID(value[name])) != value[name]:
            raise ValueError("Studio project/cycle IDs must be canonical UUIDs")
    legacy.verify_plan(value["plan"])
    index = value["plan_index"]
    if type(index) is not int or not 0 <= index < len(value["plan"]["jobs"]):  # noqa: E721
        raise ValueError("Studio work requires an exact existing plan index")
    if not isinstance(value["work_spec"], dict) or value["work_spec"].get("family") not in FAMILIES:
        raise ValueError("This executor supports only the installed fixed workbench families")
    return dict(value)


def installed_environment() -> dict[str, Any]:
    """Fingerprint the installed worker and actual host without inheriting preload hooks."""
    node = shutil.which("node")
    if node is None:
        raise ValueError("Node.js 22 or later is required for the fixed Studio executor")
    environment = {key: value for key, value in os.environ.items() if key in {"PATH", "SYSTEMROOT", "WINDIR"}}
    version = subprocess.run(
        [node, "--version"], env=environment, capture_output=True, text=True, timeout=5, check=True
    ).stdout.strip()
    if int(version.lstrip("v").split(".")[0]) < 22:
        raise ValueError("Node.js 22 or later is required for the fixed Studio executor")
    package = Path(__file__).parent
    source_names = (
        "studio.py",
        "workbench.py",
        "ascension.py",
        "jobs.py",
        "protocol.py",
        "state.py",
        "trust.py",
        "signatures.py",
        "../ascension.py",
        "../models.py",
        "../store.py",
    )
    runtime_sources = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in source_names}
    return {
        "schema": "agialpha.ascension.fixed-environment.v1",
        "node": version,
        "system": platform.system(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "worker_sha256": hashlib.sha256(workbench.WORKER.read_bytes()).hexdigest(),
        "bridge_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "runtime_sha256": digest("ascension-studio-runtime", runtime_sources),
        "network": False,
        "arbitrary_code": False,
    }


def prepare_work(
    request: dict[str, Any],
    *,
    institution_id: str,
    mission_id: str,
    producer: str,
    acceptance_owner: str,
    valid_until: str,
) -> dict[str, Any]:
    """Propose exact immutable terms; this creates no journal, principal or permission."""
    request = validate_request(request)
    workbench.invoke({"operation": "plan", "spec": request["work_spec"]})
    environment = installed_environment()
    request_hash = digest("ascension-studio-request", request)
    job_id = "studio-" + request["cycle_id"] + "-" + str(request["plan_index"])
    budget = ResourceBudget(
        limits={"calls": 1},
        units={"calls": "one bounded fixed-adapter execution; maximum 65 seconds"},
        enforceable=["calls"],
        unknown_costs=["compute", "human-review"],
    )
    release = CandidateReleaseManifest(
        release_id=job_id,
        institution_id=institution_id,
        mission_id=mission_id,
        producer=producer,
        environment_digest=digest("ascension-studio-environment", environment),
        artifacts=[
            BehaviorArtifact(name="studio-request", role="other", digest=request_hash),
            BehaviorArtifact(name="installed-worker", role="source", digest=environment["worker_sha256"]),
            BehaviorArtifact(name="installed-bridge", role="source", digest=environment["bridge_sha256"]),
        ],
        configuration={"family": request["work_spec"]["family"], "network": False, "arbitrary_code": False},
        budget=budget,
    )
    terms = JobContract(
        job_id=job_id,
        institution_id=institution_id,
        mission_id=mission_id,
        family="verification",
        worker=None,
        acceptance_owner=acceptance_owner,
        release_digest=digest("release", release),
        environment_digest=release.environment_digest,
        goal=request["plan"]["jobs"][request["plan_index"]]["spec"]["goal"],
        outputs={"report": ARTIFACT_SCHEMA},
        resources={"calls": 1},
        valid_until=valid_until,
        allowed_tools=[TOOL],
        prohibited_effects=["network", "host-code", "wallet-signing", "automatic-admission"],
        acceptance_conditions=[
            "Review exact fixed-adapter inputs, output artifacts, limitations and retained failures.",
            "An accurate negative evaluation is eligible work; candidate adoption requires a separate decision.",
        ],
        evidence_assumptions=["studio-request-sha256:" + request_hash],
    )
    return {
        "request_digest": request_hash,
        "job_contract": terms.model_dump(mode="json"),
        "release": release.model_dump(mode="json"),
        "environment": environment,
        "active_authority": [],
    }


def _validate_prepared(request: dict[str, Any], prepared: dict[str, Any]) -> JobContract:
    terms: JobContract = JobContract.model_validate(prepared["job_contract"])
    release = CandidateReleaseManifest.model_validate(prepared["release"])
    expected = prepare_work(
        request,
        institution_id=release.institution_id,
        mission_id=release.mission_id,
        producer=release.producer,
        acceptance_owner=terms.acceptance_owner,
        valid_until=terms.valid_until,
    )
    if canonical(expected) != canonical(prepared):
        raise ValueError("Prepared terms, request, installed release or environment changed")
    return terms


def seal_work(
    store: SuccessorStore,
    request: dict[str, Any],
    reader: ascension.MarketReader,
    prepared: dict[str, Any],
    graph: JobGraph,
) -> dict[str, Any]:
    """Seal operator-approved richer terms before posting using the existing journal."""
    request = validate_request(request)
    terms = _validate_prepared(request, prepared)
    if reader.context.mark is None:
        raise ValueError("Studio requests require their actual MARK and NovaSeed context")
    if [job for job in graph.jobs if job.job_id == terms.job_id] != [terms]:
        raise ValueError("Approved runtime graph does not contain the exact prepared Studio job")
    institution_id = terms.institution_id or ""
    store.trust.anchor(terms.acceptance_owner, "acceptance")
    state = store.read(institution_id)
    if state["institution"]["constitution"]["mission_id"] != terms.mission_id:
        raise ValueError("Studio terms differ from the configured institution mission")
    store.register_release(
        institution_id,
        CandidateReleaseManifest.model_validate(prepared["release"]),
        request_id="studio-freeze-" + prepared["request_digest"],
    )
    JobDispatcher(store, institution_id).seal(graph)
    return ascension.seal_terms(
        store.journal,
        terms,
        request["plan"]["jobs"][request["plan_index"]]["spec"],
        reader,
        plan=request["plan"],
        index=request["plan_index"],
    )


def _request_seal(request: dict[str, Any], seal: dict[str, Any], public_key: str) -> JobContract:
    body = ascension._verified(seal, "ascension-terms", public_key)
    terms: JobContract = JobContract.model_validate(body["job_contract"])
    request_hash = digest("ascension-studio-request", request)
    expected = "studio-" + request["cycle_id"] + "-" + str(request["plan_index"])
    spec = request["plan"]["jobs"][request["plan_index"]]["spec"]
    if (
        terms.job_id != expected
        or "studio-request-sha256:" + request_hash not in terms.evidence_assumptions
        or body["job_terms_digest"] != digest("job-terms", terms)
        or body["legacy_spec"] != spec
        or body["plan_binding"]["plan_root"] != request["plan"]["planRoot"]
        or body["plan_binding"]["plan_index"] != request["plan_index"]
        or body["plan_binding"]["indexed_leaf"] != ascension.indexed_leaf(request["plan_index"], spec)
        or body["market_spec_hash"] != ascension.market_spec_hash(spec)
    ):
        raise ValueError("Preposting seal belongs to another exact Studio request")
    return terms


def bind_work(
    journal: Journal,
    request: dict[str, Any],
    seal: dict[str, Any],
    reader: ascension.MarketReader,
    *,
    market_job_id: str,
    posting_tx: str,
    assignment_tx: str,
    execution_authorization: dict[str, Any],
) -> dict[str, Any]:
    """Observe assignment without signing a controller execution authorization."""
    request = validate_request(request)
    _request_seal(request, seal, journal.public)
    return ascension.bind_assignment(
        journal,
        seal,
        reader,
        market_job_id=market_job_id,
        posting_tx=posting_tx,
        assignment_tx=assignment_tx,
        execution_authorization=execution_authorization,
    )


def _candidate_verdict(pack: dict[str, Any]) -> str:
    family, result = pack["spec"]["family"], pack["result"]
    summary = result["summary"]
    if family == "numerical":
        return "PASS" if summary["simpson"] else "FAIL"
    if family == "documentation":
        return "FAIL" if summary["incorrectExamples"] or summary["invalidInputs"] else "PASS"
    if family == "reliability":
        if summary["candidateFailures"]:
            return "FAIL"
        return "PASS" if summary["defects"] else "RETAIN_INCUMBENT"
    if family == "performance":
        return "FAIL" if not summary["correct"] else "INSUFFICIENT_EVIDENCE"
    return "NOT_APPLICABLE"


def _sign_result(journal: Journal, body: dict[str, Any]) -> dict[str, Any]:
    hashed = digest("ascension-studio-result", body)
    return {
        **body,
        "signature": {
            "public_key": journal.public,
            "digest": hashed,
            "signature": base64.b64encode(journal.key.sign(bytes.fromhex(hashed))).decode("ascii"),
        },
    }


def retained_work(journal: Journal, request: dict[str, Any], binding_digest: str) -> dict[str, Any]:
    """Recover already completed output without checking or replaying expired authority."""
    ascension.hash32("0x" + binding_digest)
    prior = journal.latest("@successor:studio:execution:" + binding_digest)
    if prior.get("state") != "completed":
        raise Conflict("No completed Studio output exists; inspect interrupted work and reserved resources")
    result = prior["result"]
    verify_work_result(request, result, public_key=journal.public)
    if result["execution_binding"]["digest"] != binding_digest:
        raise ValueError("Retained result belongs to another binding")
    return dict(result)


def execute_work(
    dispatcher: JobDispatcher,
    request: dict[str, Any],
    seal: dict[str, Any],
    binding: dict[str, Any],
    authorization: SignedEnvelope,
    *,
    operator_checkpoint: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Run genuine fixed work once under existing controller and action-time checks."""
    request = validate_request(request)
    journal = dispatcher.journal
    if dispatcher.market_public_key != journal.public:
        raise ValueError("This portable executor requires the configured local observation journal")
    terms = _request_seal(request, seal, dispatcher.market_public_key)
    auth = ExecutionAuthorization.model_validate(
        dispatcher.store.trust.verify(authorization, "execution", "controller")
    )
    bound = ascension.verify_execution_binding(binding, dispatcher.market_public_key, auth)
    if bound["terms_seal_digest"] != seal["digest"] or bound["job_terms_digest"] != digest("job-terms", terms):
        raise ValueError("Assignment does not bind the exact preposting seal")
    state = dispatcher.store.read(dispatcher.institution_id)
    release = CandidateReleaseManifest.model_validate(state["releases"].get(terms.release_digest))
    environment = installed_environment()
    if release.environment_digest != digest("ascension-studio-environment", environment):
        raise ValueError("Installed executor environment changed after the immutable seal")
    request_hash = digest("ascension-studio-request", request)
    expected_artifacts = {
        "studio-request": request_hash,
        "installed-worker": environment["worker_sha256"],
        "installed-bridge": environment["bridge_sha256"],
    }
    if {item.name: item.digest for item in release.artifacts} != expected_artifacts:
        raise ValueError("Installed release does not bind the exact request and worker bytes")
    key = "@successor:studio:execution:" + binding["digest"]
    try:
        prior = journal.latest(key)
    except KeyError:
        prior = None
    if prior is not None:
        if prior.get("state") != "completed":
            raise Conflict("Interrupted Studio execution requires explicit controller recovery; do not replay")
        return retained_work(journal, request, binding["digest"])
    if operator_checkpoint is not None:
        operator_checkpoint()
    dispatcher.dispatch(terms.job_id, authorization, market_binding=binding)
    with journal.transaction() as cx:
        try:
            journal.latest(key, cx)
        except KeyError:
            journal.append(cx, key, {"state": "executing", "request_digest": request_hash})
        else:
            raise Conflict("Studio execution is already claimed; inspect the retained result")

    def checkpoint() -> None:
        if operator_checkpoint is not None:
            operator_checkpoint()
        dispatcher.check_action(terms.job_id, tool=TOOL, actor=auth.acting_identity)
        if installed_environment() != environment:
            raise ValueError("Installed executor changed during authorized execution")

    try:
        pack = dispatcher.execute_tool(
            terms.job_id,
            tool=TOOL,
            actor=auth.acting_identity,
            invocation_id="studio-" + binding["digest"],
            handler=lambda: workbench.invoke({"operation": "run", "spec": request["work_spec"]}, checkpoint),
        )
        verdict = _candidate_verdict(pack)
        artifact = canonical(
            {
                "schema": ARTIFACT_SCHEMA,
                "project_id": request["project_id"],
                "cycle_id": request["cycle_id"],
                "request_digest": request_hash,
                "execution_binding_digest": binding["digest"],
                "authorization_id": auth.authorization_id,
                "report": pack,
                "candidate_verdict": verdict,
                "authority_status": "not_granted",
            }
        )
        delivery = ascension.bind_delivery(journal, binding, artifact, candidate_verdict=verdict)
        result = _sign_result(
            journal,
            {
                "schema": RESULT_SCHEMA,
                "project_id": request["project_id"],
                "cycle_id": request["cycle_id"],
                "request_digest": request_hash,
                "terms_seal": seal,
                "execution_binding": binding,
                "delivery": delivery,
                "artifact_utf8": artifact.decode("utf-8"),
                "artifact_sha256": "0x" + hashlib.sha256(artifact).hexdigest(),
                "artifact_keccak256": "0x" + legacy.keccak(artifact).hex(),
                "candidate_verdict": verdict,
                "scope": "native-fixed-workbench",
                "authority_status": "not_granted",
            },
        )
        verify_work_result(request, result, public_key=journal.public)
        with journal.transaction() as cx:
            journal.append(cx, key, {"state": "completed", "request_digest": request_hash, "result": result})
        return result
    except BaseException as error:
        with journal.transaction() as cx:
            journal.append(
                cx, key, {"state": "interrupted", "request_digest": request_hash, "error": type(error).__name__}
            )
        raise


def verify_work_result(request: dict[str, Any], result: dict[str, Any], *, public_key: str) -> dict[str, Any]:
    """Authenticate retained exact bytes against separately supplied operator trust."""
    request = validate_request(request)
    value = safe_json_loads(canonical(result))
    signature = value.pop("signature", None)
    expected = {
        "schema",
        "project_id",
        "cycle_id",
        "request_digest",
        "terms_seal",
        "execution_binding",
        "delivery",
        "artifact_utf8",
        "artifact_sha256",
        "artifact_keccak256",
        "candidate_verdict",
        "scope",
        "authority_status",
    }
    if set(value) != expected or value["schema"] != RESULT_SCHEMA:
        raise ValueError("Unexpected Studio result fields")
    if (
        not isinstance(signature, dict)
        or set(signature) != {"public_key", "digest", "signature"}
        or signature["public_key"] != public_key
        or signature["digest"] != digest("ascension-studio-result", value)
    ):
        raise ValueError("Studio result does not match the separately pinned operator")
    try:
        verify_ed25519(
            bytes.fromhex(public_key),
            base64.b64decode(signature["signature"], validate=True),
            bytes.fromhex(signature["digest"]),
        )
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise ValueError("Studio result signature is invalid") from exc
    terms = _request_seal(request, value["terms_seal"], public_key)
    bound = ascension._verified(value["execution_binding"], "ascension-execution-binding", public_key)
    delivered = ascension._verified(value["delivery"], "ascension-delivery-binding", public_key)
    artifact = value["artifact_utf8"].encode("utf-8")
    request_hash = digest("ascension-studio-request", request)
    if (
        value["project_id"] != request["project_id"]
        or value["cycle_id"] != request["cycle_id"]
        or value["request_digest"] != request_hash
        or value["scope"] != "native-fixed-workbench"
        or value["authority_status"] != "not_granted"
        or bound["terms_seal_digest"] != value["terms_seal"]["digest"]
        or bound["job_terms_digest"] != digest("job-terms", terms)
        or delivered["execution_binding_digest"] != value["execution_binding"]["digest"]
        or delivered["artifact_size"] != len(artifact)
        or delivered["candidate_verdict"] != value["candidate_verdict"]
        or value["artifact_sha256"] != "0x" + hashlib.sha256(artifact).hexdigest()
        or value["artifact_keccak256"] != "0x" + legacy.keccak(artifact).hex()
        or delivered["artifact_keccak256"] != value["artifact_keccak256"]
    ):
        raise ValueError("Studio result exact request, artifact or execution binding changed")
    body = safe_json_loads(artifact)
    if (
        set(body)
        != {
            "schema",
            "project_id",
            "cycle_id",
            "request_digest",
            "execution_binding_digest",
            "authorization_id",
            "report",
            "candidate_verdict",
            "authority_status",
        }
        or canonical(body) != artifact
        or body["schema"] != ARTIFACT_SCHEMA
        or body["project_id"] != request["project_id"]
        or body["cycle_id"] != request["cycle_id"]
        or body["request_digest"] != request_hash
        or body["execution_binding_digest"] != value["execution_binding"]["digest"]
        or body["authorization_id"] != bound["execution_authorization"]["authorization_id"]
        or body["candidate_verdict"] != value["candidate_verdict"]
        or body["authority_status"] != "not_granted"
        or body["report"]["spec"] != request["work_spec"]
        or _candidate_verdict(body["report"]) != value["candidate_verdict"]
    ):
        raise ValueError("Exact Studio artifact differs from its request and result")
    return {
        "request_digest": request_hash,
        "artifact_sha256": value["artifact_sha256"],
        "artifact_keccak256": value["artifact_keccak256"],
        "candidate_verdict": value["candidate_verdict"],
        "authentication": "configured-operator",
        "authority_status": "not_granted",
    }


def settle_work(
    journal: Journal,
    request: dict[str, Any],
    result: dict[str, Any],
    reader: ascension.MarketReader,
    *,
    settlement_tx: str,
) -> dict[str, Any]:
    """Reconcile exact delivery and committee receipts idempotently without admission."""
    verify_work_result(request, result, public_key=journal.public)
    return ascension.import_settlement(
        journal,
        result["execution_binding"],
        result["delivery"],
        result["artifact_utf8"].encode("utf-8"),
        reader,
        settlement_tx=settlement_tx,
    )


def acceptance_request(
    request: dict[str, Any],
    result: dict[str, Any],
    *,
    public_key: str,
    valid_until: str | None = None,
    accepted: bool = True,
) -> dict[str, Any]:
    """Prepare an unsigned exact-report decision for its separately configured owner."""
    verify_work_result(request, result, public_key=public_key)
    terms = JobContract.model_validate(result["terms_seal"]["body"]["job_contract"])
    expires = valid_until or terms.valid_until
    JobContract.model_validate({**terms.model_dump(mode="json"), "valid_until": expires})
    if datetime.fromisoformat(expires) > datetime.fromisoformat(terms.valid_until):
        raise ValueError("Work acceptance cannot extend its frozen evidence validity")
    auth = result["execution_binding"]["body"]["execution_authorization"]
    return dict(
        JobResult(
            job_id=terms.job_id,
            authorization_id=auth["authorization_id"],
            terms_digest=digest("job-terms", terms),
            output_digest=result["artifact_sha256"][2:],
            outputs=terms.outputs,
            accepted=accepted,
            accepted_by=terms.acceptance_owner,
            valid_until=expires,
            candidate_verdict=result["candidate_verdict"],
            actual_resources={"calls": 1},
        ).model_dump(mode="json")
    )


def accept_work(
    dispatcher: JobDispatcher,
    request: dict[str, Any],
    result: dict[str, Any],
    acceptance: SignedEnvelope,
) -> dict[str, Any]:
    """Close reserved runtime resources only after an explicit exact-artifact owner decision."""
    actual = JobResult.model_validate(dispatcher.store.trust.verify(acceptance, "job-acceptance", "acceptance"))
    expected = acceptance_request(
        request,
        result,
        public_key=dispatcher.journal.public,
        valid_until=actual.valid_until,
        accepted=actual.accepted,
    )
    if canonical(actual.model_dump(mode="json")) != canonical(expected):
        raise ValueError("Work acceptance differs from exact delivered artifact and measured execution")
    return dispatcher.complete(acceptance)


def _numerical_input(request: dict[str, Any]) -> dict[str, Any]:
    checked = validate_request(request)
    if checked["work_spec"]["family"] != "numerical":
        raise ValueError("Frozen comparison currently supports the exact polynomial numerical adapter")
    return dict(checked["work_spec"]["inputs"])


def freeze_evaluation(
    journal: Journal,
    baseline_request: dict[str, Any],
    baseline_result: dict[str, Any],
    next_request: dict[str, Any],
    *,
    evaluation_id: str,
) -> dict[str, Any]:
    """Freeze two installed numerical methods before separately authorized fresh work."""
    if str(uuid.UUID(evaluation_id)) != evaluation_id:
        raise ValueError("Evaluation identity must be a canonical UUID")
    verify_work_result(baseline_request, baseline_result, public_key=journal.public)
    before, after = _numerical_input(baseline_request), _numerical_input(next_request)
    workbench.invoke({"operation": "plan", "spec": next_request["work_spec"]})
    if baseline_request["project_id"] != next_request["project_id"]:
        raise ValueError("Evaluation must preserve the same project history")
    if all(before[name] == after[name] for name in ("coefficients", "lower", "upper")):
        raise ValueError(
            "Fresh evaluation requires a distinct polynomial or domain; renaming or retuning is insufficient"
        )
    request_hash = digest("ascension-studio-request", next_request)
    body = {
        "schema_version": 1,
        "evaluation_id": evaluation_id,
        "project_id": next_request["project_id"],
        "cycle_id": next_request["cycle_id"],
        "baseline_request_digest": digest("ascension-studio-request", baseline_request),
        "baseline_artifact_keccak256": baseline_result["artifact_keccak256"],
        "request_digest": request_hash,
        "methods": {"baseline": "trapezoid", "candidate": "simpson"},
        "fresh_common_inputs": after,
        "budget": {"calls": 1, "max_milliseconds": 65000, "steps_per_method": after["steps"]},
        "criterion": "candidate meets frozen absolute tolerance and has smaller exact error than baseline",
        "input_policy": "fresh operator-visible common inputs; no independently protected holdout",
        "selection_policy": "one predeclared fixed comparison; retain all outcomes and unknown costs",
        "source_environment_digest": digest("ascension-studio-environment", installed_environment()),
        "authority_status": "not_granted",
    }
    key = "@successor:studio:evaluation-freeze:" + evaluation_id
    with journal.transaction() as cx:
        try:
            old = journal.latest(key, cx)
        except KeyError:
            old = None
        if old is not None:
            if canonical(old["freeze"]["body"]) != canonical(body):
                raise Conflict("Evaluation identity already belongs to different frozen criteria")
            return dict(old["freeze"])
        for (mission,) in cx.execute(
            "SELECT DISTINCT mission FROM events WHERE mission LIKE '@successor:studio:execution:%'"
        ):
            previous = journal.latest(mission, cx)
            if previous.get("request_digest") == request_hash:
                raise Conflict("Evaluation must be frozen before the fresh execution starts")
        envelope = ascension._signed(journal, "ascension-evaluation-freeze", body)
        journal.append(cx, key, {"state": "frozen", "freeze": envelope})
    return envelope


def _fraction(value: Any) -> Fraction:
    if not isinstance(value, str) or len(value) > 160 or not re.fullmatch(r"-?[0-9]+/[1-9][0-9]*", value):
        raise ValueError("Numerical evidence requires bounded exact rational values")
    number = Fraction(value)
    if str(number.numerator) + "/" + str(number.denominator) != value:
        raise ValueError("Numerical evidence must use reduced canonical rational values")
    return number


def evaluate_work(
    journal: Journal,
    freeze: dict[str, Any],
    baseline_request: dict[str, Any],
    baseline_result: dict[str, Any],
    next_request: dict[str, Any],
    next_result: dict[str, Any],
) -> dict[str, Any]:
    """Compare actual matched algorithm outputs without a new execution or adoption grant."""
    protocol = ascension._verified(freeze, "ascension-evaluation-freeze", journal.public)
    verify_work_result(baseline_request, baseline_result, public_key=journal.public)
    verify_work_result(next_request, next_result, public_key=journal.public)
    expected = freeze_evaluation(
        journal, baseline_request, baseline_result, next_request, evaluation_id=protocol["evaluation_id"]
    )
    if canonical(expected) != canonical(freeze):
        raise ValueError("Evaluation differs from its retained preregistration")
    retained = retained_work(journal, next_request, next_result["execution_binding"]["digest"])
    if canonical(retained) != canonical(next_result):
        raise ValueError("Evaluation result is not the retained actual execution")
    with journal.transaction() as cx:
        checkpoint = journal.latest("@successor:studio:evaluation-freeze:" + protocol["evaluation_id"], cx)
        first = cx.execute(
            "SELECT min(seq) FROM events WHERE mission=?",
            ("@successor:studio:execution:" + next_result["execution_binding"]["digest"],),
        ).fetchone()[0]
        if first is None or first <= checkpoint["revision"]:
            raise ValueError("Actual execution predates the frozen comparison")
    artifact = safe_json_loads(next_result["artifact_utf8"])
    report = artifact["report"]
    inputs, evidence = protocol["fresh_common_inputs"], report["result"]["evidence"]
    truth = sum(
        (
            Fraction(coefficient * (inputs["upper"] ** power - inputs["lower"] ** power), power)
            for power, coefficient in enumerate(inputs["coefficients"], 1)
        ),
        Fraction(0),
    )
    if truth != _fraction(evidence["analytic"]):
        raise ValueError("Numerical report analytic reference is incorrect")
    tolerance = Fraction(inputs["tolerancePpm"], 1_000_000)
    if tolerance != _fraction(evidence["absoluteTolerance"]):
        raise ValueError("Numerical report changed its frozen tolerance")
    errors = {method: abs(_fraction(evidence[method]) - truth) for method in ("trapezoid", "simpson")}
    for method, error in errors.items():
        if error != _fraction(evidence["absoluteErrors"][method]) or evidence["passes"][method] is not (
            error <= tolerance
        ):
            raise ValueError("Numerical report changed its exact error or tolerance verdict")
    elapsed = report["economics"]["elapsedMilliseconds"]
    if type(elapsed) is not int or elapsed < 0:  # noqa: E721
        raise ValueError("Numerical report has invalid measured elapsed time")
    if elapsed > protocol["budget"]["max_milliseconds"]:
        outcome = "INSUFFICIENT_EVIDENCE"
    elif errors["simpson"] > tolerance or errors["simpson"] > errors["trapezoid"]:
        outcome = "FAIL"
    elif errors["simpson"] == errors["trapezoid"]:
        outcome = "TIE"
    else:
        outcome = "PASS"
    body = {
        "schema_version": 1,
        "evaluation_id": protocol["evaluation_id"],
        "project_id": protocol["project_id"],
        "cycle_id": protocol["cycle_id"],
        "freeze_digest": freeze["digest"],
        "baseline_artifact_keccak256": baseline_result["artifact_keccak256"],
        "evaluated_artifact_keccak256": next_result["artifact_keccak256"],
        "request_digest": protocol["request_digest"],
        "methods": protocol["methods"],
        "common_inputs": inputs,
        "exact_absolute_errors": evidence["absoluteErrors"],
        "absolute_tolerance": evidence["absoluteTolerance"],
        "outcome": outcome,
        "measured_elapsed_milliseconds": elapsed,
        "budget": protocol["budget"],
        "compute_cost": None,
        "human_cost": None,
        "provider_execution": False,
        "independent_proof": False,
        "scope": "exact numerical error on one fresh common polynomial; no general or economic superiority",
        "tradeoff": (
            "Both methods share the same node evaluations; general accuracy, memory and costs remain unqualified."
        ),
        "admission": "HOLD",
        "authority_status": "not_granted",
    }
    envelope = ascension._signed(journal, "ascension-evaluation-report", body)
    key = "@successor:studio:evaluation-report:" + protocol["evaluation_id"]
    with journal.transaction() as cx:
        try:
            old = journal.latest(key, cx)
        except KeyError:
            journal.append(cx, key, {"state": "evaluated", "report": envelope})
            return envelope
        if canonical(old["report"]) != canonical(envelope):
            raise Conflict("Evaluation already records another result; retain the original outcome")
        return dict(old["report"])
