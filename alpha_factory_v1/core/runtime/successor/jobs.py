# SPDX-License-Identifier: Apache-2.0
"""Bounded job compilation, dependency dispatch and distinct work acceptance."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

from pydantic import ConfigDict, Field

from ..store import Conflict, Journal
from .protocol import ExecutionAuthorization, JobContract, JobGraph, StrictModel, digest
from .state import SuccessorState, SuccessorStore, checked_resources, current, utc_now
from .trust import SignedEnvelope

FAMILIES = {"constitution", "evidence", "formation", "challenge", "verification", "admission", "renewal"}


class JobResult(StrictModel):
    """Acceptance belongs to its owner; a negative candidate report can be useful work."""

    job_id: str
    authorization_id: str
    terms_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outputs: dict[str, str]
    accepted: bool
    accepted_by: str
    valid_until: str
    permitted_uses: list[str] = Field(default_factory=list)
    revoked: bool = False
    rollback_available: bool = False
    candidate_verdict: str | None = None
    actual_resources: dict[str, int] | None = None
    interventions: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)


class ToolInvocation(StrictModel):
    """Durable tool claim prevents automatic replay after an uncertain effect."""

    tool: str
    actor: str
    state: str = "executing"
    result_digest: str | None = None


class JobRun(StrictModel):
    """The exact authorization and every attempt remain attributable."""

    authorization: ExecutionAuthorization
    authorization_envelope: SignedEnvelope
    attempt: int
    state: str = "running"
    result: JobResult | None = None
    acceptance: SignedEnvelope | None = None
    tools: dict[str, ToolInvocation] = Field(default_factory=dict)


class GraphState(StrictModel):
    """A compiled graph snapshot with immutable terms and mutable attempt history."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=False, validate_default=True)
    graph: JobGraph
    graph_digest: str
    order: list[str]
    runs: dict[str, list[JobRun]] = Field(default_factory=dict)
    revoked_jobs: list[str] = Field(default_factory=list)


def compile_jobs(graph: JobGraph, *, prohibited_effects: set[str] | None = None) -> list[str]:
    """Reject cycles in v1 and require all seven lifecycle families and critical coverage."""
    terms = {job.job_id: job for job in graph.jobs}
    if len(terms) != len(graph.jobs):
        raise ValueError("job IDs must be unique")
    if not FAMILIES <= {job.family for job in graph.jobs}:
        raise ValueError("graph must cover all seven SUCCESSOR job families")
    functions = {name for job in graph.jobs for name in job.critical_functions}
    if not set(graph.required_functions) <= functions:
        raise ValueError("graph omits required critical functions")
    disallowed = prohibited_effects or set()
    formation_workers = {job.worker for job in graph.jobs if job.family == "formation" and job.worker}
    for job in graph.jobs:
        checked_resources(job.resources)
        if not job.resources or any(amount < 1 for amount in job.resources.values()):
            raise ValueError("job requires positive controllable resource reservations")
        if job.worker is not None and job.worker == job.acceptance_owner:
            raise ValueError("work acceptance must be separate from the worker")
        if job.family in {"challenge", "verification", "admission"} and job.worker in formation_workers:
            raise ValueError("formation worker cannot own its challenge, verification or admission")
        if set(job.effects).intersection(disallowed | set(job.prohibited_effects)):
            raise ValueError("job declares prohibited effects")
        if not set(job.repair_routes) <= terms.keys():
            raise ValueError("repair route refers to missing work")
    incoming = {key: 0 for key in terms}
    outgoing: dict[str, list[str]] = {key: [] for key in terms}
    seen: set[tuple[str, str, str]] = set()
    for edge in graph.edges:
        if edge.source not in terms or edge.target not in terms:
            raise ValueError("dependency refers to a missing job")
        identity = (edge.source, edge.target, edge.kind)
        if identity in seen:
            raise ValueError("duplicate dependency edge")
        seen.add(identity)
        if edge.kind == "control" and not edge.principal:
            raise ValueError("control dependency requires its accountable principal")
        source, target = terms[edge.source], terms[edge.target]
        if edge.kind == "evidence":
            if edge.required_type and edge.required_type not in source.outputs.values():
                raise ValueError("evidence dependency cannot supply its required type")
            if target.inputs and not set(target.inputs.values()).intersection(source.outputs.values()):
                raise ValueError("evidence output and dependent input types are incompatible")
        if edge.kind == "challenge" and source.family != "challenge":
            raise ValueError("challenge edge requires a challenge-family job")
        if edge.kind == "rollback" and not source.rollback_target:
            raise ValueError("rollback dependency requires an explicit recovery target")
        incoming[edge.target] += 1
        outgoing[edge.source].append(edge.target)
    for target in graph.jobs:
        supplied = {}
        for edge in graph.edges:
            if edge.target == target.job_id and edge.kind == "evidence":
                supplied.update(terms[edge.source].outputs)
        if any(supplied.get(name) != expected for name, expected in target.inputs.items()):
            raise ValueError("required input port lacks compatible evidence coverage")
    queue = sorted(key for key, value in incoming.items() if not value)
    order: list[str] = []
    while queue:
        source_id = queue.pop(0)
        order.append(source_id)
        for target_id in outgoing[source_id]:
            incoming[target_id] -= 1
            if incoming[target_id] == 0:
                queue.append(target_id)
                queue.sort()
    if len(order) != len(terms):
        raise ValueError("cyclic job dependencies are unsupported in v1; use a bounded new graph")
    return order


class JobDispatcher:
    """Seal work then check live dependencies at dispatch and each tool boundary."""

    def __init__(self, store: SuccessorStore, institution_id: str, *, market_public_key: str | None = None) -> None:
        self.store = store
        self.journal = store.journal
        self.institution_id = institution_id
        self.key = "@successor-jobs:" + institution_id
        self.market_public_key = market_public_key or self.journal.public

    def seal(self, graph: JobGraph) -> dict[str, Any]:
        """Freeze all terms atomically without reserving or granting production authority."""
        institution = self.store.read(self.institution_id)
        prohibited = set(institution["institution"]["constitution"]["prohibited_actions"])
        order = compile_jobs(graph, prohibited_effects=prohibited)
        for job in graph.jobs:
            self.store.trust.anchor(job.acceptance_owner, "acceptance")
            if job.worker is not None:
                self.store.trust.anchor(job.worker, "worker")
        state = GraphState(graph=graph, graph_digest=digest("job-graph", graph), order=order)
        with self.journal.transaction() as cx:
            try:
                old = self.journal.latest(self.key, cx)
            except KeyError:
                return self.journal.append(cx, self.key, state.model_dump(mode="json"))
            if old["graph_digest"] != state.graph_digest:
                raise Conflict("sealed job terms cannot be changed; use a new institution or graph version")
            return old

    @staticmethod
    def _terms(state: GraphState, job_id: str) -> JobContract:
        for terms in state.graph.jobs:
            if terms.job_id == job_id:
                return terms
        raise ValueError("job does not exist")

    def _dependencies(self, state: GraphState, job_id: str, now: str) -> None:
        if job_id in state.revoked_jobs:
            raise ValueError("job or its evidence is revoked")
        for edge in state.graph.edges:
            if edge.target != job_id:
                continue
            runs = state.runs.get(edge.source, [])
            if not runs or runs[-1].result is None or runs[-1].acceptance is None:
                raise ValueError("required dependency has no accepted work")
            result = runs[-1].result
            accepted = JobResult.model_validate(
                self.store.trust.verify(runs[-1].acceptance, "job-acceptance", "acceptance")
            )
            if (
                edge.source in state.revoked_jobs
                or not result.accepted
                or result.revoked
                or accepted != result
                or not current(result.valid_until, now)
            ):
                raise ValueError("dependency is unaccepted, expired or revoked")
            if edge.kind == "evidence" and "dependency" not in result.permitted_uses:
                raise ValueError("evidence rights do not permit dependent work")
            if edge.required_type and edge.required_type not in result.outputs.values():
                raise ValueError("current dependency evidence has an incompatible type")
            if edge.kind == "control" and result.accepted_by != edge.principal:
                raise ValueError("control decision belongs to the wrong principal")
            if edge.kind == "rollback" and not result.rollback_available:
                raise ValueError("rollback target is unavailable")

    def _authorization(self, terms: JobContract, authorization: ExecutionAuthorization, now: str) -> None:
        if (
            authorization.job_terms_digest != digest("job-terms", terms)
            or authorization.release_digest != terms.release_digest
            or authorization.environment_digest != terms.environment_digest
            or (terms.worker is not None and authorization.acting_identity != terms.worker)
            or authorization.acting_identity == terms.acceptance_owner
            or not current(authorization.expires_at, now)
            or not current(terms.valid_until, now)
            or not set(authorization.capabilities) <= set(terms.allowed_tools)
        ):
            raise ValueError("execution authorization does not match current frozen work terms")
        self.store.trust.anchor(authorization.acting_identity, "worker")

    def dispatch(
        self, job_id: str, envelope: SignedEnvelope, *, market_binding: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Reserve shared institution resources atomically with a signed assignment."""
        authorization = ExecutionAuthorization.model_validate(
            self.store.trust.verify(envelope, "execution", "controller")
        )
        if authorization.market_binding_digest is not None:
            from .ascension import verify_execution_binding

            if market_binding is None:
                raise ValueError("market-assigned execution requires its pinned assignment binding")
            binding = verify_execution_binding(market_binding, self.market_public_key, authorization)
            if binding["institution_id"] != self.institution_id or binding["logical_job_id"] != job_id:
                raise ValueError("market assignment belongs to another institution or logical job")
        elif market_binding is not None:
            raise ValueError("standalone execution cannot borrow an unrelated market assignment")
        with self.journal.transaction() as cx:
            original = self.journal.latest(self.key, cx)
            state = GraphState.model_validate(Journal.document(original))
            institution_raw = self.journal.latest(self.store._key(self.institution_id), cx)
            institution = SuccessorState.model_validate(Journal.document(institution_raw))
            if envelope.principal != institution.institution.controller:
                raise ValueError("assignment requires the institution controller")
            if institution.stopped or self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("institution or agent is stopped")
            terms = self._terms(state, job_id)
            now = utc_now()
            self._authorization(terms, authorization, now)
            if terms.institution_id is not None and terms.institution_id != self.institution_id:
                raise ValueError("frozen job belongs to another institution")
            if terms.mission_id is not None and terms.mission_id != institution.institution.constitution.mission_id:
                raise ValueError("frozen job belongs to another mission")
            if terms.family in {"challenge", "verification", "admission"}:
                formation_workers = {job.worker for job in state.graph.jobs if job.family == "formation" and job.worker}
                for formation_job in state.graph.jobs:
                    if formation_job.family == "formation":
                        formation_workers.update(
                            run.authorization.acting_identity for run in state.runs.get(formation_job.job_id, [])
                        )
                if authorization.acting_identity in formation_workers:
                    raise ValueError("resolved formation worker cannot verify or admit its own work")
            self._dependencies(state, job_id, now)
            release = self.store._release(institution, terms.release_digest)
            if release.environment_digest != terms.environment_digest:
                raise ValueError("job environment differs from the frozen runtime release")
            for evidence_id in terms.input_evidence:
                evidence = self.store._evidence(institution, evidence_id, now)
                if (
                    evidence.scope != institution.institution.constitution.mission_id
                    or terms.family not in evidence.permitted_uses
                ):
                    raise ValueError("input evidence scope or rights exclude this job family")
            runs = state.runs.get(job_id, [])
            for previous in runs:
                if previous.authorization.authorization_id == authorization.authorization_id:
                    if previous.authorization != authorization:
                        raise Conflict("authorization ID belongs to different execution")
                    return original
            if len(runs) >= terms.max_attempts or (runs and runs[-1].state == "running"):
                raise Conflict("job attempt bound exhausted or an attempt is already running")
            for other in state.runs.values():
                if any(run.authorization.reservation_id == authorization.reservation_id for run in other):
                    raise Conflict("reservation identity is already used")
            for unit, amount in terms.resources.items():
                ledger = institution.resources
                if amount > ledger.limits.get(unit, -1) - ledger.spent.get(unit, 0) - ledger.reserved.get(unit, 0):
                    raise ValueError("shared institution job resource ceiling is exhausted")
            for unit, amount in terms.resources.items():
                institution.resources.reserved[unit] = institution.resources.reserved.get(unit, 0) + amount
            state.runs.setdefault(job_id, []).append(
                JobRun(authorization=authorization, authorization_envelope=envelope, attempt=len(runs) + 1)
            )
            self.journal.append(cx, self.store._key(self.institution_id), institution.model_dump(mode="json"))
            return self.journal.append(cx, self.key, state.model_dump(mode="json"))

    def _check_action(self, cx: sqlite3.Connection, job_id: str, tool: str, actor: str) -> tuple[GraphState, JobRun]:
        state = GraphState.model_validate(Journal.document(self.journal.latest(self.key, cx)))
        institution = SuccessorState.model_validate(
            Journal.document(self.journal.latest(self.store._key(self.institution_id), cx))
        )
        if institution.stopped or self.journal.latest("@control", cx)["state"] != "ready":
            raise Conflict("institution or agent is stopped")
        terms = self._terms(state, job_id)
        runs = state.runs.get(job_id, [])
        if not runs or runs[-1].state != "running":
            raise ValueError("job is not running")
        run = runs[-1]
        self.store.trust.verify(run.authorization_envelope, "execution", "controller")
        now = utc_now()
        self._dependencies(state, job_id, now)
        self._authorization(terms, run.authorization, now)
        release = self.store._release(institution, terms.release_digest)
        if release.environment_digest != terms.environment_digest:
            raise ValueError("job execution environment changed")
        for evidence_id in terms.input_evidence:
            evidence = self.store._evidence(institution, evidence_id, now)
            if (
                evidence.scope != institution.institution.constitution.mission_id
                or terms.family not in evidence.permitted_uses
            ):
                raise ValueError("input evidence no longer permits this job family")
        if tool not in run.authorization.capabilities or actor != run.authorization.acting_identity:
            raise ValueError("tool or acting principal is outside execution authorization")
        return state, run

    def check_action(self, job_id: str, *, tool: str, actor: str) -> ExecutionAuthorization:
        """Recheck a development boundary; use execute_tool to close the dispatch race."""
        try:
            with self.journal.transaction() as cx:
                _, run = self._check_action(cx, job_id, tool, actor)
                return run.authorization
        except (ValueError, Conflict) as exc:
            self.store._deny(self.institution_id, job_id, str(exc))
            raise

    def execute_tool(
        self,
        job_id: str,
        *,
        tool: str,
        actor: str,
        invocation_id: str,
        handler: Callable[[], Any],
    ) -> Any:
        """Execute an installed bounded development tool with durable at-most-once claims.

        The handler is installed pure application code with no external side effects.
        It runs without a write lock so stop/revocation and bounded checkpoints remain
        responsive. Revalidation suppresses results invalidated during computation.
        Consequential actions require ActionGateway; arbitrary code requires the
        existing explicitly opted-in isolated runner, never this callable boundary.
        """
        if not invocation_id or len(invocation_id) > 128:
            raise ValueError("tool invocation requires a bounded unique identity")
        try:
            with self.journal.transaction() as cx:
                state, run = self._check_action(cx, job_id, tool, actor)
                if invocation_id in run.tools:
                    raise Conflict("tool invocation already started; recover rather than replay")
                run.tools[invocation_id] = ToolInvocation(tool=tool, actor=actor)
                self.journal.append(cx, self.key, state.model_dump(mode="json"))
            failure: Exception | None = None
            result = None
            result_digest = None
            with self.journal.transaction() as cx:
                _, checked_run = self._check_action(cx, job_id, tool, actor)
                if checked_run.tools[invocation_id].state != "executing":
                    raise Conflict("tool invocation is no longer executable")
                authorization_id = checked_run.authorization.authorization_id
            try:
                result = handler()
                result_digest = digest("job-tool-output", result)
            except Exception as exc:  # noqa: BLE001 - persist boundary failures before re-raising
                failure = exc
            with self.journal.transaction() as cx:
                state = GraphState.model_validate(Journal.document(self.journal.latest(self.key, cx)))
                run = state.runs[job_id][-1]
                if run.authorization.authorization_id != authorization_id:
                    raise Conflict("job attempt changed during bounded work; suppress its result")
                invocation = run.tools[invocation_id]
                if invocation.state != "executing":
                    raise Conflict("job tool was recovered while running; suppress its result")
                try:
                    self._check_action(cx, job_id, tool, actor)
                except (ValueError, Conflict) as exc:
                    failure = exc
                run.tools[invocation_id] = invocation.model_copy(
                    update={
                        "state": "failed" if failure else "completed",
                        "result_digest": None if failure else result_digest,
                    }
                )
                self.journal.append(cx, self.key, state.model_dump(mode="json"))
            if failure is not None:
                raise ValueError("bounded job tool failed; failure retained") from failure
            return result
        except (ValueError, Conflict) as exc:
            self.store._deny(self.institution_id, job_id, str(exc))
            raise

    def complete(self, envelope: SignedEnvelope) -> dict[str, Any]:
        """Accept exact output and charge once; candidate admission stays separate."""
        result = JobResult.model_validate(self.store.trust.verify(envelope, "job-acceptance", "acceptance"))
        with self.journal.transaction() as cx:
            old = self.journal.latest(self.key, cx)
            state = GraphState.model_validate(Journal.document(old))
            terms = self._terms(state, result.job_id)
            if result.accepted_by != envelope.principal or result.accepted_by != terms.acceptance_owner:
                raise ValueError("work acceptance belongs to another principal")
            if result.terms_digest != digest("job-terms", terms) or result.outputs != terms.outputs:
                raise ValueError("accepted output is not bound to frozen work terms and types")
            runs = state.runs.get(result.job_id, [])
            if not runs:
                raise ValueError("cannot accept undispatched work")
            run = runs[-1]
            if result.authorization_id != run.authorization.authorization_id:
                raise ValueError("work result belongs to a different execution attempt")
            if run.state != "running":
                if run.result == result:
                    return old
                raise Conflict("completed attempt cannot change acceptance or accounting")
            if any(invocation.state == "executing" for invocation in run.tools.values()):
                raise Conflict("uncertain tool invocation requires recovery before acceptance")
            institution_raw = self.journal.latest(self.store._key(self.institution_id), cx)
            institution = SuccessorState.model_validate(Journal.document(institution_raw))
            actual = result.actual_resources
            if actual is not None:
                checked_resources(actual)
                if set(actual) != set(terms.resources):
                    raise ValueError("actual resources must include every reserved unit")
            for unit, bound in terms.resources.items():
                institution.resources.reserved[unit] -= bound
                measured = bound if actual is None else actual[unit]
                institution.resources.spent[unit] = institution.resources.spent.get(unit, 0) + max(bound, measured)
                if measured > bound:
                    institution.resources.overruns.append(result.job_id + ":" + unit)
                    institution.stopped = True
            if actual is None:
                institution.resources.unknown.append(result.job_id)
            runs[-1] = run.model_copy(update={"state": "completed", "result": result, "acceptance": envelope})
            self.journal.append(cx, self.store._key(self.institution_id), institution.model_dump(mode="json"))
            return self.journal.append(cx, self.key, state.model_dump(mode="json"))

    def recover_job(self, envelope: SignedEnvelope) -> dict[str, Any]:
        """Conservatively close an interrupted bounded attempt under a new owner decision."""
        payload = self.store.trust.verify(envelope, "job-recovery", "controller")
        if set(payload) != {"job_id", "reason"} or not all(isinstance(value, str) for value in payload.values()):
            raise ValueError("job recovery requires job_id and reason strings")
        with self.journal.transaction() as cx:
            old = self.journal.latest(self.key, cx)
            state = GraphState.model_validate(Journal.document(old))
            institution = SuccessorState.model_validate(
                Journal.document(self.journal.latest(self.store._key(self.institution_id), cx))
            )
            if envelope.principal != institution.institution.controller:
                raise ValueError("job recovery requires the institution controller")
            terms = self._terms(state, payload["job_id"])
            runs = state.runs.get(terms.job_id, [])
            if not runs or runs[-1].state != "running":
                return old
            run = runs[-1]
            for unit, amount in terms.resources.items():
                institution.resources.reserved[unit] -= amount
                institution.resources.spent[unit] = institution.resources.spent.get(unit, 0) + amount
            institution.resources.unknown.append(run.authorization.authorization_id)
            for ident, invocation in run.tools.items():
                if invocation.state == "executing":
                    run.tools[ident] = invocation.model_copy(update={"state": "uncertain"})
            runs[-1] = run.model_copy(update={"state": "uncertain"})
            self.journal.append(cx, self.store._key(self.institution_id), institution.model_dump(mode="json"))
            return self.journal.append(cx, self.key, state.model_dump(mode="json"))

    def revoke_dependency(self, envelope: SignedEnvelope) -> dict[str, Any]:
        """Revoke influence transitively without deleting accepted work history."""
        payload = self.store.trust.verify(envelope, "job-revocation", "controller")
        if set(payload) != {"job_id", "reason"}:
            raise ValueError("job revocation requires a job_id and reason")
        with self.journal.transaction() as cx:
            state = GraphState.model_validate(Journal.document(self.journal.latest(self.key, cx)))
            institution = SuccessorState.model_validate(
                Journal.document(self.journal.latest(self.store._key(self.institution_id), cx))
            )
            if envelope.principal != institution.institution.controller:
                raise ValueError("job revocation requires this institution controller")
            self._terms(state, payload["job_id"])
            pending = [payload["job_id"]]
            while pending:
                job_id = pending.pop()
                if job_id in state.revoked_jobs:
                    continue
                state.revoked_jobs.append(job_id)
                pending.extend(edge.target for edge in state.graph.edges if edge.source == job_id)
            return self.journal.append(cx, self.key, state.model_dump(mode="json"))
