# SPDX-License-Identifier: Apache-2.0
"""Executable local institution rehearsal with signed jobs and restart-safe evidence."""

from __future__ import annotations

import hashlib
import importlib
import os
import tempfile
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

from ..store import Conflict, Journal, private_write, restrict_access
from .aggregation import BETA, CURRENT, execute
from .evaluation import current_comparator_manifest, measure, validate_frozen, workload
from .jobs import JobDispatcher, JobResult
from .protocol import (
    AdmissionDecision,
    AuthorityEnvelope,
    BehaviorArtifact,
    CandidateReleaseManifest,
    EvidenceRecord,
    ExecutionAuthorization,
    Family,
    Institution,
    JobContract,
    JobDependency,
    JobGraph,
    MemoryAdmission,
    MissionConstitution,
    Outcome,
    OutcomeMeasure,
    ProofReceipt,
    ProviderManifest,
    RehearsalRequest,
    ResourceBudget,
    UnderwritingDecision,
    Validity,
    VerifierDisclosure,
    canonical,
    digest,
    safe_json_loads,
)
from .state import ActionGateway, ActionRequest, EvidenceSubmission, SuccessorState, SuccessorStore, utc_now
from .transport import result_envelope, verify_result
from .trust import JournalCheckpoint, retained_local_principals, sign_record

CONTROLLER = "local-controller"
PRODUCER = "local-producer"
VERIFIER = "local-verifier"
FAMILIES: list[Family] = ["constitution", "evidence", "formation", "challenge", "verification", "admission", "renewal"]


def _run_key(request_id: str) -> str:
    return "@successor-run:" + str(uuid.UUID(request_id))


@contextmanager
def _operator_lock(journal: Journal) -> Iterator[None]:
    """Hold an OS-released exclusive rehearsal lease across process crashes."""
    path = journal.root / "successor.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if os.name == "nt":
            msvcrt = importlib.import_module("msvcrt")

            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")
            os.lseek(fd, 0, 0)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise Conflict("another local SUCCESSOR rehearsal is active") from exc
        else:
            import fcntl

            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise Conflict("another local SUCCESSOR rehearsal is active") from exc
        yield
    finally:
        os.close(fd)


def show_run(journal: Journal, request_id: str) -> dict[str, Any]:
    """Inspect authenticated progress without disclosing private principal keys."""
    return journal.latest(_run_key(request_id))


def retained_result(journal: Journal, request_id: str) -> dict[str, Any]:
    """Return exact saved evidence; replay does not invent new performance measurements."""
    record = show_run(journal, request_id)
    if record["state"] != "completed":
        raise Conflict("rehearsal is not completed; inspect its retained phase and failure")
    request = RehearsalRequest.model_validate(record["request"])
    result = record["result"]
    verify_result(result, request, journal.public)
    return dict(result)


def _save(journal: Journal, key: str, **fields: Any) -> dict[str, Any]:
    with journal.transaction() as cx:
        record = Journal.document(journal.latest(key, cx))
        record.update(fields)
        return journal.append(cx, key, record)


def _source_artifacts() -> list[BehaviorArtifact]:
    root = Path(__file__).parent
    paths = sorted(root.glob("*.py")) + [root.parent / name for name in ("models.py", "store.py", "provider.py")]
    return [
        BehaviorArtifact(
            name=str(path.relative_to(root.parent)).replace("/", ":"),
            role="source",
            digest=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in paths
    ]


def _manifest(
    institution_id: str,
    label: str,
    payload: dict[str, Any],
    environment: str,
    issued_at: str,
    parent: str | None = None,
    memory: list[str] | None = None,
) -> CandidateReleaseManifest:
    return CandidateReleaseManifest(
        release_id=label,
        institution_id=institution_id,
        mission_id="streaming-metrics-v1",
        producer=PRODUCER,
        environment_digest=environment,
        artifacts=_source_artifacts()
        + [BehaviorArtifact(name="complete-composition", role="other", digest=digest("composition", payload))],
        providers=[
            ProviderManifest(
                provider="bounded-grammar",
                model="no-neural-model",
                endpoint="local-fixed-engine",
                observed_at=issued_at,
                implementation="deterministic",
                pinning_limitations=(
                    "Repository source and finite configuration are pinned; no remote weights are claimed."
                ),
            )
        ],
        world_digest=digest("world", payload.get("world", {})),
        policy_digest=digest("policy", payload.get("policy", {})),
        budget=ResourceBudget(
            limits={"job_units": 14, "action_units": 3},
            units={"job_units": "bounded job dispatches", "action_units": "fixed inspection actions"},
            enforceable=["job_units", "action_units"],
            unknown_costs=["human-review", "money"],
        ),
        development_evaluator_digest=digest("development-interface", "bounded-aggregation-development-v1"),
        final_proof_interface_digest=digest("proof-interface", "successor.evaluation.evaluate_frozen/v1"),
        parent_release_digest=parent,
        memory_digests=memory or [],
        configuration={"mode": "local-rehearsal", "label": label},
    )


def _graph(release: CandidateReleaseManifest, until: str) -> JobGraph:
    workers: dict[str, str] = {family: PRODUCER for family in FAMILIES}
    workers.update(constitution=VERIFIER, challenge=VERIFIER, verification=VERIFIER, admission=CONTROLLER)
    owners = {family: CONTROLLER if workers[family] == VERIFIER else VERIFIER for family in FAMILIES}
    jobs = [
        JobContract(
            job_id=family,
            family=family,
            worker=workers[family],
            acceptance_owner=owners[family],
            release_digest=digest("release", release),
            environment_digest=release.environment_digest,
            outputs={"report": "successor-phase-report-v1"},
            critical_functions=[family],
            resources={"job_units": 1},
            valid_until=until,
            max_attempts=2,
            institution_id=release.institution_id,
            mission_id=release.mission_id,
            allowed_tools=["bounded-" + family],
            prohibited_effects=["network", "filesystem", "shell", "deployment"],
            acceptance_conditions=["Exact output digest, required dependency and distinct acceptance principal."],
            lifecycle_obligations=["Retain failed attempts and never transfer development permission into production."],
        )
        for family in FAMILIES
    ]
    edges = [
        JobDependency(
            source=left,
            target=right,
            kind="challenge" if left == "challenge" else "evidence",
            required_type="successor-phase-report-v1",
        )
        for left, right in pairwise(FAMILIES)
    ]
    edges.append(JobDependency(source="constitution", target="formation", kind="control", principal=CONTROLLER))
    return JobGraph(
        jobs=jobs, edges=edges, required_families=FAMILIES, required_functions=[str(family) for family in FAMILIES]
    )


class _Lifecycle:
    def __init__(self, journal: Journal, request: RehearsalRequest, record: dict[str, Any]) -> None:
        self.journal, self.request, self.key = journal, request, _run_key(request.request_id)
        self.started, self.until = record["started_at"], record["valid_until"]
        self.institution_id = "mission-" + request.request_id
        self.trust, self.keys = retained_local_principals(journal.root / "successor-principals")
        self.store = SuccessorStore(journal, self.trust)
        self.constitution = MissionConstitution(
            mission_id=request.mission,
            owner=CONTROLLER,
            beneficiary=CONTROLLER,
            objective="Optimize exact public streaming metrics while retaining a competent available alternative.",
            outcome_measures=[
                OutcomeMeasure(name="correctness", unit="all-cases", direction="exact", threshold="1", hard_gate=True),
                OutcomeMeasure(name="runtime", unit="nanoseconds-per-workload", direction="minimize"),
            ],
            evidence_rights=["Synthetic non-personal workload observations and repository-owned methods."],
            constraints=[
                "Closed finite grammar only; no arbitrary host code.",
                "Missing independent frontier evidence means HOLD.",
            ],
            prohibited_actions=["network", "filesystem", "shell", "deployment", "production"],
            incumbent="current",
            alternatives=["beta", "frontier-unavailable"],
            authority_ceiling="sandbox",
            budget=ResourceBudget(
                limits={"job_units": 14, "action_units": 3},
                units={"job_units": "dispatches", "action_units": "inspection actions"},
                enforceable=["job_units", "action_units"],
                unknown_costs=["human-review", "money"],
            ),
            proof_requirements=["correctness"],
            stop_conditions=["incorrect output", "revoked evidence", "exhausted bounded job allowance"],
            validity=Validity(valid_from=self.started, valid_until=self.until),
        )
        self.store.create_institution(
            Institution(id=self.institution_id, constitution=self.constitution, controller=CONTROLLER),
            {"job_units": 14, "action_units": 3},
        )
        self.runtime_release = _manifest(
            self.institution_id,
            "development-runtime",
            request.model_dump(),
            digest("environment", {"mode": "closed-grammar-development", "max_events": request.max_events}),
            self.started,
        )
        self.store.register_release(self.institution_id, self.runtime_release, request_id="register-runtime")
        self.graph = _graph(self.runtime_release, self.until)
        self.dispatcher = JobDispatcher(self.store, self.institution_id)
        self.dispatcher.seal(self.graph)

    def signed(self, domain: str, value: Any, principal: str = CONTROLLER) -> Any:
        return sign_record(self.keys[principal], principal, domain, value)

    def checkpoint(self) -> None:
        """Revalidate stop controls and admitted treatment before each bounded unit."""
        from .mission import admitted_knowledge

        if self.journal.latest("@control")["state"] != "ready":
            raise Conflict("agent is paused")
        state = SuccessorState.model_validate(Journal.document(self.store.read(self.institution_id)))
        if state.stopped:
            raise Conflict("institution is stopped")
        record = show_run(self.journal, self.request.request_id)
        if record["current_phase"] == "renewal":
            memory_digest = digest("memory", admitted_knowledge(record["phases"]["formation"]))
            self.store._memory(state, memory_digest, utc_now(), use="formation")

    def phase(self, family: str, operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        if family == "renewal":
            self.prepare_admission()
        record = show_run(self.journal, self.request.request_id)
        if family in record["phases"]:
            cached = dict(record["phases"][family])
            if family == "formation":
                self.freeze_releases(cached)
            return cached
        terms = next(job for job in self.graph.jobs if job.job_id == family)
        graph_state = self.journal.latest(self.dispatcher.key)
        attempts = graph_state["runs"].get(family, [])
        if attempts and attempts[-1]["state"] == "running":
            self.dispatcher.recover_job(
                self.signed(
                    "job-recovery",
                    {"job_id": family, "reason": "explicitly resumed interrupted bounded attempt; no effect replay"},
                )
            )
        attempt = len(attempts) + 1
        authorization = ExecutionAuthorization(
            authorization_id=f"{family}-{attempt}",
            acting_identity=str(terms.worker),
            job_terms_digest=digest("job-terms", terms),
            release_digest=terms.release_digest,
            environment_digest=terms.environment_digest,
            capabilities=terms.allowed_tools,
            reservation_id=f"reserve-{family}-{attempt}",
            expires_at=self.until,
        )
        self.dispatcher.dispatch(family, self.signed("execution", authorization))
        _save(self.journal, self.key, current_phase=family)
        self.checkpoint()
        payload = self.dispatcher.execute_tool(
            family,
            tool="bounded-" + family,
            actor=str(terms.worker),
            invocation_id=f"{family}-{attempt}",
            handler=operation,
        )
        result = JobResult(
            job_id=family,
            authorization_id=authorization.authorization_id,
            terms_digest=digest("job-terms", terms),
            output_digest=digest("phase-output", payload),
            outputs=terms.outputs,
            accepted=True,
            accepted_by=terms.acceptance_owner,
            valid_until=self.until,
            permitted_uses=["dependency", "formation"],
            candidate_verdict=payload.get("decision", {}).get("local_verdict"),
            actual_resources={"job_units": 1},
        )
        self.dispatcher.complete(self.signed("job-acceptance", result, terms.acceptance_owner))
        phases = show_run(self.journal, self.request.request_id)["phases"]
        phases[family] = payload
        _save(self.journal, self.key, phases=phases)
        if family == "formation":
            self.freeze_releases(payload)
        return dict(payload)

    def freeze_releases(self, formation: dict[str, Any]) -> tuple[CandidateReleaseManifest, CandidateReleaseManifest]:
        frozen = formation["freeze"]
        environment = digest("environment", frozen["manifest"]["environment"])
        candidate = _manifest(
            self.institution_id, "challenger-generation-one", frozen["manifest"], environment, self.started
        )
        current_manifest = _manifest(
            self.institution_id,
            "current-sandbox-fixture",
            current_comparator_manifest(frozen),
            environment,
            self.started,
        )
        self.store.register_release(self.institution_id, candidate, request_id="register-candidate")
        self.store.register_release(self.institution_id, current_manifest, request_id="register-current")
        for evidence_id, commitment, source in (
            ("trial-freeze", frozen["release_digest"], "candidate composition frozen before protected evaluation"),
            (
                "current-comparator-subject",
                current_comparator_manifest(frozen)["subject_digest"],
                "exact Current comparator composition frozen before protected evaluation",
            ),
        ):
            evidence = EvidenceRecord(
                evidence_id=evidence_id,
                source=source,
                acquired_at=self.decision_time("freeze"),
                content_digest=commitment,
                permitted_uses=["proof"],
                valid_until=self.until,
                scope=self.request.mission,
                uncertainty="Local source commitment; performance and correctness require fresh measurement.",
                retention_until=self.until,
                accepted_by=CONTROLLER,
            )
            self.store.record_evidence(
                self.institution_id,
                self.signed("evidence", EvidenceSubmission(institution_id=self.institution_id, evidence=evidence)),
                request_id=evidence_id + "-evidence",
            )
        return candidate, current_manifest

    def decision_time(self, name: str) -> str:
        record = show_run(self.journal, self.request.request_id)
        times = record.get("decision_times", {})
        if name not in times:
            times[name] = utc_now()
            _save(self.journal, self.key, decision_times=times)
        return str(times[name])

    def prepare_admission(self) -> None:
        from .mission import admitted_knowledge

        phases = show_run(self.journal, self.request.request_id)["phases"]
        if "admission" in phases:
            return
        formation, proof = phases["formation"], phases["verification"]
        candidate, _ = self.freeze_releases(formation)
        candidate_digest = digest("release", candidate)
        disclosure = VerifierDisclosure(
            verifier=VERIFIER,
            organization="same local operator",
            control_separation="distinct local role keys; no organizational independence",
            custodian="local-process-custodian",
            funding_and_conflicts="same operator funds and controls this rehearsal",
            protocol_controller=CONTROLLER,
            replication_status="not-replicated",
        )
        outcomes: dict[str, Outcome] = {
            "PASS": "pass",
            "FAIL": "fail",
            "TIE": "tie",
            "RETAIN_INCUMBENT": "retain_incumbent",
            "RETAIN_ALTERNATIVE": "retain_alternative",
            "INSUFFICIENT_EVIDENCE": "insufficient_evidence",
        }
        candidate_receipt = ProofReceipt(
            proof_id="candidate-comparison",
            institution_id=self.institution_id,
            mission_id=self.request.mission,
            release_digest=candidate_digest,
            environment_digest=proof["environment_hash"],
            verifier=VERIFIER,
            valid_until=self.until,
            outcome=outcomes.get(proof["decision"]["local_verdict"], "insufficient_evidence"),
            claim="alpha",
            comparator_manifest_digest=proof["comparator_hash"],
            protocol_digest=proof["protocol_hash"],
            evidence_commitment=proof["protected_evidence_commitment"],
            disclosure=disclosure,
            evaluation_units=len(proof["units"]),
            issued_at=self.decision_time("admission"),
            uncertainty=(
                "Descriptive local workload comparison; missing frontier comparator and independent verifier. "
                "Economic Alpha withheld."
            ),
            failures=[str(failure) for failure in proof["failures"]],
        )
        self.store.record_proof(
            self.institution_id, self.signed("proof", candidate_receipt, VERIFIER), request_id="candidate-comparison"
        )
        refusal = AdmissionDecision(
            decision_id="candidate-hold",
            institution_id=self.institution_id,
            release_digest=candidate_digest,
            principal=CONTROLLER,
            outcome="refuse",
            rationale="HOLD: independent comparator, verifier and customer qualification have not been supplied.",
            issued_at=self.decision_time("admission"),
        )
        self.store.admit(self.institution_id, self.signed("admission", refusal), request_id="candidate-hold")
        knowledge = admitted_knowledge(formation)
        memory_digest = digest("memory", knowledge)
        evidence = EvidenceRecord(
            evidence_id="formation-methods",
            source="actual generation-one development; protected proof excluded",
            acquired_at=self.decision_time("admission"),
            content_digest=memory_digest,
            permitted_uses=["formation"],
            valid_until=self.until,
            scope=self.request.mission,
            uncertainty="Inspected development methods; future benefit unestablished",
            retention_until=self.until,
            accepted_by=CONTROLLER,
        )
        self.store.record_evidence(
            self.institution_id,
            self.signed("evidence", EvidenceSubmission(institution_id=self.institution_id, evidence=evidence)),
            request_id="formation-evidence",
        )
        memory = MemoryAdmission(
            admission_id="development-memory",
            institution_id=self.institution_id,
            principal=CONTROLLER,
            artifact_digest=memory_digest,
            evidence_ids=[evidence.evidence_id],
            permitted_uses=["formation"],
            scope=self.request.mission,
            rights=["repository-owned code and synthetic non-personal observations"],
            valid_until=self.until,
            retention_until=self.until,
            outcome="admit",
            restrictions=["exclude final proof outcomes, protected corpus, credentials and grants"],
        )
        self.store.admit_memory(
            self.institution_id, self.signed("memory-admission", memory), request_id="memory-admission"
        )
        self.phase(
            "admission",
            lambda: {
                "candidate_verdict": proof["decision"]["local_verdict"],
                "institutional_admission": "HOLD",
                "candidate_admission_decision": refusal.model_dump(),
                "memory_admission": memory.model_dump(),
                "memory_digest": memory_digest,
                "knowledge": knowledge,
                "production_authority": False,
            },
        )

    def finish(self, study: dict[str, Any]) -> dict[str, Any]:
        phases = show_run(self.journal, self.request.request_id)["phases"]
        first, proof = study["generation_one"], study["generation_one"]["proof"]
        _, current_manifest = self.freeze_releases(first)
        current_digest = digest("release", current_manifest)
        memory_digest = phases["admission"]["memory_digest"]
        descendant_data = study["generation_two"]["trials"][0]["arms"]["memory"]["formation"]["freeze"]
        descendant = _manifest(
            self.institution_id,
            "generation-two-shadow",
            descendant_data["manifest"],
            digest("environment", descendant_data["manifest"]["environment"]),
            self.started,
            parent=digest(
                "release",
                _manifest(
                    self.institution_id,
                    "challenger-generation-one",
                    first["freeze"]["manifest"],
                    proof["environment_hash"],
                    self.started,
                ),
            ),
            memory=[memory_digest],
        )
        self.store.descendant(self.institution_id, descendant, request_id="shadow-descendant")
        current_failures = [failure for failure in proof["failures"] if failure["system"] == "current"]
        fixture: dict[str, Any] = {
            "scope": "local sandbox mechanics for measured Current; challenger remains unadmitted",
            "current_failures": current_failures,
        }
        if not current_failures:
            disclosure = VerifierDisclosure(
                verifier=VERIFIER,
                organization="same local operator",
                control_separation="distinct local keys only",
                custodian="local-process-custodian",
                funding_and_conflicts="same local operator",
                protocol_controller=CONTROLLER,
                replication_status="not-replicated",
            )
            receipt = ProofReceipt(
                proof_id="current-correctness",
                institution_id=self.institution_id,
                mission_id=self.request.mission,
                release_digest=current_digest,
                environment_digest=proof["environment_hash"],
                verifier=VERIFIER,
                valid_until=self.until,
                outcome="pass",
                claim="correctness",
                comparator_manifest_digest=proof["comparator_hash"],
                protocol_digest=proof["protocol_hash"],
                evidence_commitment=proof["protected_evidence_commitment"],
                disclosure=disclosure,
                evaluation_units=len(proof["units"]),
                issued_at=self.decision_time("operations"),
                dependency_digests=[
                    first["freeze"]["release_digest"],
                    current_comparator_manifest(first["freeze"])["subject_digest"],
                ],
                uncertainty="Finite local correctness checks; no superiority or external qualification.",
            )
            self.store.record_proof(
                self.institution_id, self.signed("proof", receipt, VERIFIER), request_id="current-correctness"
            )
            decision = AdmissionDecision(
                decision_id="current-sandbox-admission",
                institution_id=self.institution_id,
                release_digest=current_digest,
                principal=CONTROLLER,
                outcome="admit",
                proof_ids=[receipt.proof_id],
                rationale="Explicit local rehearsal policy: allow fixed report inspection only; no production effects.",
                issued_at=self.decision_time("operations"),
            )
            self.store.admit(
                self.institution_id, self.signed("admission", decision), request_id="current-sandbox-admission"
            )
            context = digest(
                "inspection-context", {"request_hash": study["request_hash"], "report": digest("proof-report", proof)}
            )
            grant = AuthorityEnvelope(
                grant_id="current-inspection",
                institution_id=self.institution_id,
                mission_id=self.request.mission,
                release_digest=current_digest,
                subject=PRODUCER,
                issuer=CONTROLLER,
                actions=["inspect"],
                tools=["fixed-report-inspector"],
                targets=["local-evidence"],
                resources={"action_units": 2},
                proof_ids=[receipt.proof_id],
                valid_until=self.until,
                approval_required=False,
                context_digest=context,
                scope="sandbox",
                monitoring=["one fixed no-effect inspection", "grant revocation blocks queued action"],
                issued_at=self.decision_time("operations"),
            )
            self.store.grant(self.institution_id, self.signed("authority", grant), request_id="current-inspection")
            self.store.cutover(
                self.institution_id,
                self.signed("cutover", {"release_digest": current_digest}),
                request_id="install-current",
                expected_revision=self.store.read(self.institution_id)["revision"],
            )
            action = ActionRequest(
                action_id="inspect-current-report",
                subject=PRODUCER,
                release_digest=current_digest,
                environment_digest=proof["environment_hash"],
                action="inspect",
                tool="fixed-report-inspector",
                target="local-evidence",
                context_digest=context,
                resources={"action_units": 1},
            )
            prior_inspection = self.store.read(self.institution_id)["actions"].get(action.action_id)
            if prior_inspection is not None and prior_inspection["state"] in {
                "executing",
                "uncertain",
                "failed",
                "cancelled",
            }:
                self.store.revoke(
                    self.institution_id,
                    self.signed(
                        "revocation",
                        {"grant_id": grant.grant_id, "reason": "rehearsal completes with authority withdrawn"},
                    ),
                    request_id="revoke-current",
                )
                recovered = self.store.recover(
                    self.institution_id,
                    self.signed("recovery", {"institution_id": self.institution_id}),
                    request_id="recover-interrupted-inspection",
                )
                fixture.update(
                    action=recovered["actions"][action.action_id]["state"],
                    grant="revoked",
                    final_state="stopped",
                    recovery="signed controller recovery; interrupted or failed inspection was not replayed",
                    inspection_success=False,
                    revocation_before_action="not_exercised_after_interruption",
                )
            else:
                self.store.dispatch_action(self.institution_id, action)
                self.store.execute_action(
                    self.institution_id,
                    action.action_id,
                    ActionGateway(
                        {
                            ("fixed-report-inspector", "inspect"): lambda _action: {
                                "report_digest": digest("proof-report", proof)
                            }
                        }
                    ),
                    actual_resources={"action_units": 1},
                )
                queued = action.model_copy(update={"action_id": "revoked-queued-inspection"})
                self.store.dispatch_action(self.institution_id, queued)
                self.store.revoke(
                    self.institution_id,
                    self.signed(
                        "revocation",
                        {"grant_id": grant.grant_id, "reason": "rehearsal completes with authority withdrawn"},
                    ),
                    request_id="revoke-current",
                )
                try:
                    self.store.execute_action(
                        self.institution_id, queued.action_id, ActionGateway({}), actual_resources={"action_units": 1}
                    )
                except ValueError:
                    fixture["revocation_before_action"] = "denied"
                else:
                    raise ValueError("revoked queued action unexpectedly executed")
                self.store.recover(
                    self.institution_id,
                    self.signed("recovery", {"institution_id": self.institution_id}),
                    request_id="recover-queued",
                )
                fixture.update(action="completed", grant="revoked", final_state="stopped")
        method_contents = {
            "candidate": ("release", first["freeze"]["manifest"]),
            "descendant": ("release", descendant_data["manifest"]),
            "world": ("world-program", first["world"]),
            "policy": ("policy-program", first["freeze"]["manifest"]["policy"]),
            "knowledge": ("memory", phases["admission"]["knowledge"]),
            "request": ("request", self.request.model_dump()),
            "current": ("current-comparator", current_comparator_manifest(first["freeze"])["manifest"]),
        }
        method_bundle = {
            "schema_version": 1,
            "kind": "successor-method-bundle",
            "institution_id": self.institution_id,
            "request_hash": study["request_hash"],
            "entries": {
                name: {"domain": domain, "digest": digest(domain, content), "content": content}
                for name, (domain, content) in method_contents.items()
            },
        }
        portable = self.store.export_portable(self.institution_id, artifact_bundle=method_bundle)
        transported_portable = safe_json_loads(canonical(portable))
        checkpoint = JournalCheckpoint(**transported_portable["payload"]["checkpoint"])
        with tempfile.TemporaryDirectory(prefix="successor-clean-restore-") as directory:
            restored_journal = Journal.initialize(Path(directory) / "home")
            restored_trust, _ = retained_local_principals(restored_journal.root / "successor-principals")
            restored_store = SuccessorStore(restored_journal, restored_trust)
            restored = restored_store.restore_portable(
                transported_portable,
                {"job_units": 14, "action_units": 3},
                source_public_key=self.journal.public,
                checkpoint=checkpoint,
            )
            if restored["proofs"] or restored["grants"] or restored["serving_release"] is not None:
                raise ValueError("clean restore inherited permission")
            from .mission import GrammarSupplier

            restored_bundle = safe_json_loads(restored["artifact_bundle_json"])
            candidate_entry = restored_bundle["entries"]["candidate"]
            restored_freeze = {
                "schema_version": 1,
                "manifest": candidate_entry["content"],
                "release_digest": candidate_entry["digest"],
            }
            restored_program = validate_frozen(restored_freeze)["program"]
            restored_knowledge = restored_bundle["entries"]["knowledge"]
            if digest("memory", restored_knowledge["content"]) != memory_digest:
                raise ValueError("restored method bytes do not match the admitted historical knowledge")
            substitute, supplier_record = GrammarSupplier("systematic-composition-v1").propose(
                (self.request.seed + 117) % 2**32, 2, None
            )
            probes = [workload((self.request.seed + 117 + index) % 2**32, 64, index) for index in range(4)]
            equivalence = all(
                execute(probe, restored_program) == execute(probe, BETA) == execute(probe, substitute[0])
                for probe in probes
            )
            if not equivalence:
                raise ValueError("restored bounded method or substitute failed behavioral equivalence")
            measurements = [
                {
                    "unit": index,
                    "restored": measure(restored_program, probe),
                    "substitute": measure(substitute[0], probe),
                }
                for index, probe in enumerate(probes)
            ]
            restoration = {
                "verified_source_key": self.journal.public,
                "source_checkpoint": portable["payload"]["checkpoint"],
                "identity_preserved": restored["institution"]["id"] == self.institution_id,
                "active_proofs": [],
                "active_grants": [],
                "stopped": restored["stopped"],
                "supplier_equivalence": equivalence,
                "supplier_record": supplier_record,
                "restored_method_digest": candidate_entry["digest"],
                "restored_knowledge_digest": restored_knowledge["digest"],
                "method_source": "signed artifact bundle decoded from serialized portable bytes",
                "canary_units": len(probes),
                "new_measurements": measurements,
                "knowledge_influence_admitted": False,
                "scope": (
                    "clean local journal and method restoration with new no-effect canary measurements; "
                    "deterministic supplier substitution only, no real-model portability or new authority"
                ),
            }
        return {
            "institution_id": self.institution_id,
            "fixture": fixture,
            "portable": portable,
            "restoration": restoration,
            "shadow_successor": {"manifest": descendant.model_dump(), "active_proof": [], "active_grants": []},
            "state": Journal.document(self.store.read(self.institution_id)),
            "job_graph": Journal.document(self.journal.latest(self.dispatcher.key)),
            "production_authority": False,
        }


def rehearse(home: Path, request: RehearsalRequest, *, resume: bool = False) -> dict[str, Any]:
    """Run actual phases once, retaining each result and every interrupted attempt."""
    from .mission import run_study

    request = RehearsalRequest.model_validate(request.model_dump())
    journal = Journal(home) if home.exists() else Journal.initialize(home)
    journal.verify()
    with _operator_lock(journal):
        key = _run_key(request.request_id)
        with journal.transaction() as cx:
            try:
                record = journal.latest(key, cx)
            except KeyError:
                started = utc_now()
                until = (
                    (datetime.fromisoformat(started) + timedelta(days=1))
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z")
                )
                record = journal.append(
                    cx,
                    key,
                    {
                        "state": "new",
                        "request": request.model_dump(),
                        "request_hash": digest("request", request),
                        "started_at": started,
                        "valid_until": until,
                        "phases": {},
                        "current_phase": None,
                    },
                )
        if record["request_hash"] != digest("request", request):
            raise Conflict("request identity belongs to different frozen inputs")
        if record["state"] == "completed":
            return retained_result(journal, request.request_id)
        if record["state"] != "new" and not resume:
            raise Conflict("previous run was interrupted; inspect it and explicitly use --resume")
        _save(journal, key, state="running")
        try:
            lifecycle = _Lifecycle(journal, request, record)
            finalization = record.get("finalization")
            if finalization is not None:
                if (
                    not isinstance(finalization, dict)
                    or set(finalization) != {"study_digest", "request_hash"}
                    or not isinstance(record.get("study"), dict)
                    or finalization["request_hash"] != digest("request", request)
                    or finalization["study_digest"] != digest("completed-study", record["study"])
                    or record["study"].get("request_hash") != finalization["request_hash"]
                    or set(record["phases"]) != set(FAMILIES)
                ):
                    raise ValueError("retained finalization does not bind a complete study and exact request")
                study = record["study"]
            else:
                underwriting = UnderwritingDecision(
                    decision_id="underwrite-evidence",
                    institution_id=lifecycle.institution_id,
                    mission_id=request.mission,
                    principal=CONTROLLER,
                    changed_assumption=(
                        "A bounded aggregation composition may improve recurring workload cost "
                        "without behavior changes."
                    ),
                    considered_alternatives=["retain", "repair", "rent", "build", "partner", "reserve", "stop"],
                    selected="build",
                    decisive_evidence=["current-and-beta-correctness", "paired-fresh-workloads"],
                    proof_budget=lifecycle.constitution.budget,
                    rationale=(
                        "Run a finite public-input evidence programme; retain stronger alternatives "
                        "and stop at qualification HOLD."
                    ),
                    issued_at=lifecycle.started,
                )
                lifecycle.phase(
                    "constitution",
                    lambda: {
                        "constitution": lifecycle.constitution.model_dump(),
                        "underwriting": lifecycle.signed("underwriting", underwriting).model_dump(),
                    },
                )
                lifecycle.phase(
                    "evidence",
                    lambda: {
                        "inputs": "synthetic-public-non-personal",
                        "rights": "repository-owned synthetic generation",
                        "current": CURRENT,
                        "beta": BETA,
                        "frontier": "unavailable",
                        "production_permission": False,
                    },
                )
                study = run_study(request, checkpoint=lifecycle.checkpoint, phase_hook=lifecycle.phase)
                _save(
                    journal,
                    key,
                    state="finalizing",
                    study=study,
                    finalization={
                        "study_digest": digest("completed-study", study),
                        "request_hash": digest("request", request),
                    },
                )
            integration = lifecycle.finish(study)
            result = result_envelope(
                request,
                {
                    "study": study,
                    "lifecycle": integration,
                    "status": "completed",
                    "qualification": "HOLD",
                    "production_authority": False,
                },
                journal.key,
            )
            _save(journal, key, state="completed", current_phase=None, result=result)
            return result
        except BaseException as exc:
            _save(
                journal,
                key,
                state="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                failure=type(exc).__name__,
            )
            raise


def write_demo(home: Path, request: RehearsalRequest, output: Path) -> dict[str, Any]:
    """Write a usable evidence directory, keeping all private state outside the export."""
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    restrict_access(output)
    private_write(output / "request.json", canonical(request))
    result = rehearse(home, request)
    private_write(output / "result.json", canonical(result))
    evidence = result["evidence"]
    private_write(output / "portable.json", canonical(evidence["lifecycle"]["portable"]))
    private_write(output / "checkpoint.json", canonical(evidence["lifecycle"]["portable"]["payload"]["checkpoint"]))
    private_write(output / "public-key.txt", (result["signature"]["public_key"] + "\n").encode("ascii"))
    verdict = evidence["study"]["local_verdict"]
    if request.language == "fr":
        report = f"SUCCESSOR Ω — répétition terminée\nVerdict local : {verdict}\nQualification : HOLD (en attente)\n"
        report += "Autorité de production : aucune\n"
        report += (
            "Recherche bornée exécutée, nouvel examen local, travaux signés, "
            "essais mémoire/témoin et restauration propre.\n"
        )
        report += "Conservez public-key.txt et checkpoint.json séparément avant d'accepter des exports ultérieurs.\n"
        report += "result.json authentifie les mesures consignées; la vérification ne remesure pas les performances.\n"
    else:
        report = f"SUCCESSOR Ω — rehearsal complete\nLocal verdict: {verdict}\n"
        report += "Qualification: HOLD\nProduction authority: none\n"
        report += (
            "Actual bounded search, fresh local examination, signed jobs, memory/control trials and clean restore.\n"
        )
        report += "Retain public-key.txt and checkpoint.json independently before accepting later exports.\n"
        report += "result.json authenticates recorded measurements; verification does not remeasure performance.\n"
    private_write(output / "REPORT.txt", report.encode("utf-8"))
    return {
        "output": str(output.resolve()),
        "request_id": request.request_id,
        "public_key": result["signature"]["public_key"],
        "local_verdict": evidence["study"]["local_verdict"],
        "qualification": "HOLD",
        "production_authority": False,
    }
