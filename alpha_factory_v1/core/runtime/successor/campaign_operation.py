# SPDX-License-Identifier: Apache-2.0
"""Finite foreground operation of the existing source-study queue, with no external effects."""

from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from ..store import Conflict, Journal, private_write
from .campaign_experiment import CampaignExperiment, CampaignUnit, PolicyStudy, _binding
from .orchestration import _operator_lock
from .protocol import canonical, digest
from .transformation import TIModel

KEY = "@discovery-policy-operation:"


def _is_exact_type(value: object, expected: type[object]) -> bool:
    return type(value) is expected


def _now() -> int:
    return time.time_ns() // 1_000_000


def _driver() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def example(*, retained_artifacts: bool = False) -> OperationSpec:
    """Reuse the shipped source-selector task and grammar on visibly synthetic changed inputs."""
    from .campaign_experiment import DiscoveryPolicy
    from .transformation import (
        DiscoveryRequest,
        IntentCharter,
        SourceClaim,
        SourceDocument,
        pilot_document,
        pilot_request,
    )

    raw = pilot_request().charter.model_dump()
    raw.update(
        purpose="Prepare prerequisite-preserving source notes for a technical reader under a two-clause limit.",
        population="synthetic annotated release-note graphs; not customer demand or reader understanding",
        max_clauses=2,
    )
    raw["budgets"].update(search_units=10_000, execution_units=10_000)
    if retained_artifacts:
        raw[
            "purpose"
        ] = "Prepare prerequisite-preserving technical source notes for a reader under a three-clause limit."
        raw["population"] = "public and synthetic annotated source graphs; no reader-comprehension claim"
        raw["max_clauses"] = 3
    charter = IntentCharter.model_validate(raw)

    def unit(label: str, index: int) -> CampaignUnit:
        def document(part: str) -> SourceDocument:
            dependencies = [[], [], ["b"], ["b"]] if index != 2 else [[], ["a"], [], ["c"]]
            weights = [2, 1, 5, 4] if index != 2 else [1, 5, 2, 8]
            if index == 3:
                dependencies, weights = [[], [], [], []], [8, 5, 2, 1]
            return SourceDocument(
                title="Synthetic release notes " + label + " " + part,
                source_url="https://example.org/synthetic-source-operation/" + label + "/" + part,
                claims=[
                    SourceClaim(
                        id=name,
                        text=f"Synthetic {label} {part} requirement {name}; graph variant {index}.",
                        weight=weight,
                        depends_on=deps,
                        provenance="Constructed mechanism fixture; local weights and dependencies, no fetched source.",
                    )
                    for name, weight, deps in zip("abcd", weights, dependencies)
                ],
            )

        return CampaignUnit(
            unit_id=label,
            request=DiscoveryRequest(
                campaign_id=str(uuid.uuid4()), charter=charter, development=[document("development")]
            ),
            terminal=[document("fresh")],
        )

    study = PolicyStudy(
        study_id=str(uuid.uuid4()),
        charter=charter,
        terminal_campaigns=3,
        policies=[
            DiscoveryPolicy(
                identity="enumerate-all",
                operator_ids=["representation", "production", "complementary"],
                max_candidates=5,
            ),
            DiscoveryPolicy(identity="direct-pair", operator_ids=["complementary"], max_candidates=3),
            DiscoveryPolicy(identity="fixed-frame", operator_ids=[], max_candidates=2),
        ],
        incumbent_policy="enumerate-all",
        search_cost_ppm_per_unit=1,
        population="Predeclared synthetic source graphs with reordered prerequisites and changed weights.",
        sampling_protocol=(
            "One training campaign, three changed campaigns; complete paired policies; "
            "exact-search comparator sees the same inputs and budgets. No independent sampling claim."
        ),
    )
    if retained_artifacts:
        raw_study = study.model_dump()
        raw_study.update(
            archive_access="shared-closed-artifacts",
            incumbent_policy="conventional-reuse",
            population=(
                "One existing public-paper example plus changed synthetic source graphs; " "local annotation judgments."
            ),
        )
        raw_study["policies"] = [
            {
                "identity": "conventional-reuse",
                "operator_ids": ["retained-program", "complementary"],
                "max_candidates": 4,
            },
            {"identity": "successor-reuse", "operator_ids": ["retained-program", "complementary"], "max_candidates": 4},
            {"identity": "direct-construction", "operator_ids": ["complementary"], "max_candidates": 4},
        ]
        study = PolicyStudy.model_validate(raw_study)
    training = unit("training", 0)
    if retained_artifacts:
        public_request = pilot_request().model_dump()
        public_request["charter"] = charter.model_dump()
        documents = [*public_request["development"], pilot_document(confirmation=True).model_dump()]
        for document in documents:
            document["source_url"] = (
                "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/"
                "787bc547f8c44854931b316d7286b8bc9f9c8bba/docs/Transformational_Intelligence.tex"
            )
        public_request["development"] = documents[:-1]
        training = CampaignUnit(
            unit_id="training", request=DiscoveryRequest.model_validate(public_request), terminal=[documents[-1]]
        )
    return OperationSpec(
        operation_id=str(uuid.uuid4()),
        study=study,
        accountable_operator="local-operator",
        training=[Arrival(after_ms=0, unit=training)],
        confirmation=[
            Arrival(after_ms=4000 + index * 4000, unit=unit("arrival-" + str(index + 1), index + 1))
            for index in range(3)
        ],
    )


class Arrival(TIModel):
    """One immutable complete campaign and its earliest arrival in the finite operation."""

    after_ms: int = Field(ge=0, le=300_000, strict=True)
    unit: CampaignUnit


class OperationSpec(TIModel):
    """An explicit free local envelope; candidates cannot extend it or choose tools."""

    operation_id: str
    study: PolicyStudy
    accountable_operator: str = Field(min_length=1, max_length=200)
    mission_family: Literal["source-clause-selector/v1"] = "source-clause-selector/v1"
    input_sources: Literal["inline-public-nonpersonal"] = "inline-public-nonpersonal"
    allowed_effects: Literal["pure-computation-and-local-journal"] = "pure-computation-and-local-journal"
    max_concurrency: Literal[1] = 1
    max_attempts: int = Field(default=3, ge=1, le=3, strict=True)
    horizon_seconds: int = Field(default=60, ge=1, le=3600, strict=True)
    total_search_units: int = Field(default=1_000_000, ge=0, le=5_000_000, strict=True)
    total_execution_units: int = Field(default=1_000_000, ge=0, le=5_000_000, strict=True)
    training: list[Arrival] = Field(min_length=1, max_length=8)
    confirmation: list[Arrival] = Field(min_length=2, max_length=8)

    @model_validator(mode="before")
    @classmethod
    def exact_concurrency(cls, value: Any) -> Any:
        if isinstance(value, dict) and "max_concurrency" in value and not _is_exact_type(value["max_concurrency"], int):
            raise ValueError("maximum concurrency requires the integer one")
        return value

    @model_validator(mode="after")
    def bounded(self) -> OperationSpec:
        if str(uuid.UUID(self.operation_id)) != self.operation_id:
            raise ValueError("operation requires a canonical UUID")
        arrivals = [*self.training, *self.confirmation]
        if len({item.unit.unit_id for item in arrivals}) != len(arrivals):
            raise ValueError("operation units require distinct identities")
        if len(self.confirmation) != self.study.terminal_campaigns:
            raise ValueError("supply the entire declared confirmation sample")
        if any(item.after_ms >= self.horizon_seconds * 1000 for item in arrivals):
            raise ValueError("arrivals must precede the absolute operation deadline")
        if [item.after_ms for item in arrivals] != sorted(item.after_ms for item in arrivals):
            raise ValueError("arrivals must be ordered, with training before confirmation")
        if self.study.charter.payment_route != "none":
            raise ValueError("source operation requires no payment route")
        if any(item.unit.request.charter != self.study.charter for item in arrivals):
            raise ValueError("every mission must retain the approved purpose and resource envelope")
        count = len(arrivals) * len(self.study.policies) * self.max_attempts
        budget = self.study.charter.budgets
        if count * budget.search_units > self.total_search_units:
            raise ValueError("reserve construction and crash retry allowances inside total search budget")
        if count * budget.execution_units > self.total_execution_units:
            raise ValueError("reserve checking and crash retry allowances inside total execution budget")
        if len(canonical(self.model_dump())) > 128_000:
            raise ValueError("operation input exceeds 128000 bytes")
        return self


def validate_authority(journal: Journal, parent: dict[str, Any], cx: Any) -> dict[str, Any]:
    """Recheck the current permit inside every child transaction, including after recovery."""
    link = parent["operation"]
    record = journal.latest(KEY + link["operation_id"], cx)
    if (
        record["state"] != "running"
        or record["binding"] != link["binding"]
        or record["driver"] != _driver()
        or record["home"] != str(journal.root)
        or _now() >= record["expires_ms"]
        or record["spec"]["study"] != parent["spec"]
        or parent["approval"] != parent["binding"]
    ):
        raise Conflict("operation stopped, expired, restored elsewhere or changed; no authority is inherited")
    return record


def validate_child(parent: dict[str, Any], request: Any) -> None:
    """Only the currently due child receives the existing exact parent study lease."""
    link = parent["operation"]
    if request.campaign_id != link.get("child") or _now() < link.get("due_ms", 2**63):
        raise Conflict("child is not the due operation mission")


def validate_batch(journal: Journal, parent: dict[str, Any], units: list[CampaignUnit], phase: str, cx: Any) -> None:
    """Bind every reservation entry point to the approved submitted arrival commitments."""
    record = validate_authority(journal, parent, cx)
    expected = [(item["unit_id"], item["input_digest"]) for item in record["spec"][phase]]
    actual = [(unit.unit_id, digest("operation-unit", unit)) for unit in units]
    if actual != expected:
        raise Conflict("reserved batch differs from the approved submitted operation inputs")


class CampaignOperation:
    """Drive preapproved existing phases; no second queue, generated code or production cutover."""

    def __init__(self, journal: Journal) -> None:
        self.experiment = CampaignExperiment(journal)
        self.journal = journal

    def show(self, operation_id: str) -> dict[str, Any]:
        return self.journal.latest(KEY + str(uuid.UUID(operation_id)))

    def _spec(self, record: dict[str, Any]) -> OperationSpec:
        from .transport import read_document

        spec = OperationSpec.model_validate(read_document(self.journal.root / record["input_file"]))
        expected = digest(
            "source-operation", {"spec": spec.model_dump(), "study": _binding(spec.study), "driver": _driver()}
        )
        if expected != record["binding"]:
            raise Conflict("submitted operation inputs or installed code changed")
        return spec

    def start(self, spec: OperationSpec) -> dict[str, Any]:
        """An explicit operator command approves one exact finite envelope, never an imported grant."""
        spec = OperationSpec.model_validate(spec.model_dump())
        parent = self.experiment.create(spec.study)
        binding = digest(
            "source-operation", {"spec": spec.model_dump(), "study": parent["binding"], "driver": _driver()}
        )
        input_file = "source-operation-" + spec.operation_id + ".json"
        source = self.journal.root / input_file
        if source.exists():
            if source.is_symlink() or source.read_bytes() != canonical(spec.model_dump()):
                raise Conflict("submitted operation input file cannot be replaced")
        else:
            private_write(source, canonical(spec.model_dump()))
        manifest = spec.model_dump()
        for phase in ("training", "confirmation"):
            manifest[phase] = [
                {
                    "after_ms": item.after_ms,
                    "unit_id": item.unit.unit_id,
                    "input_digest": digest("operation-unit", item.unit),
                }
                for item in getattr(spec, phase)
            ]
        with self.journal.transaction() as cx:
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("operator STOP is active")
            try:
                existing = self.journal.latest(KEY + spec.operation_id, cx)
            except KeyError:
                existing = None
            if existing is not None:
                if existing["binding"] != binding:
                    raise Conflict("operation identity cannot replace submitted inputs or scope")
                return existing
            parent = self.journal.latest(self.experiment._key(spec.study.study_id), cx)
            if parent["state"] != "proposed" or parent.get("operation") or parent["approval"] is not None:
                raise Conflict("operation requires a new unapproved existing study")
            now = _now()
            data = Journal.document(parent)
            data["approval"] = data["binding"]
            data["operation"] = {"operation_id": spec.operation_id, "binding": binding, "child": None, "due_ms": now}
            self.journal.append(cx, self.experiment._key(spec.study.study_id), data)
            return self.journal.append(
                cx,
                KEY + spec.operation_id,
                {
                    "schema": "source-study-operation/v1",
                    "spec": manifest,
                    "input_file": input_file,
                    "binding": binding,
                    "driver": _driver(),
                    "home": str(self.journal.root),
                    "started_ms": now,
                    "expires_ms": now + spec.horizon_seconds * 1000,
                    "state": "running",
                    "attempts": [],
                    "sessions": [],
                    "failure": None,
                    "interventions": [{"action": "approve-envelope", "actor": spec.accountable_operator, "at_ms": now}],
                    "human_minutes": "not measured",
                },
            )

    def stop(self, operation_id: str) -> dict[str, Any]:
        """Permanently revoke this operation, atomically fencing all stale child workers."""
        with self.journal.transaction() as cx:
            record = self.journal.latest(KEY + operation_id, cx)
            data = Journal.document(record)
            if data["state"] == "completed":
                return record
            data["state"] = "canceled"
            data["interventions"].append({"action": "stop", "at_ms": _now(), "actor": "operator-command"})
            parent_key = self.experiment._key(data["spec"]["study"]["study_id"])
            parent = Journal.document(self.journal.latest(parent_key, cx))
            parent["state"], parent["approval"] = "canceled", None
            self.journal.append(cx, parent_key, parent)
            return self.journal.append(cx, KEY + operation_id, data)

    def _choose(self, record: dict[str, Any], parent: dict[str, Any]) -> tuple[str, str | None, int]:
        spec = self._spec(record)
        phase = "training" if parent["state"] in {"proposed", "training"} else "confirmation"
        arrivals = getattr(spec, phase)
        runs = (parent.get(phase) or {}).get("runs", [])
        for arrival in arrivals:
            for policy in spec.study.policies:
                if not any(run["unit_id"] == arrival.unit.unit_id and run["policy"] == policy.identity for run in runs):
                    child = str(
                        uuid.uuid5(
                            uuid.UUID(spec.study.study_id), phase + ":" + arrival.unit.unit_id + ":" + policy.identity
                        )
                    )
                    return phase, child, record["started_ms"] + arrival.after_ms
        return phase, None, record["started_ms"]

    def advance(self, operation_id: str) -> dict[str, Any]:
        """Commit at most one due existing child; a crash reconciles its durable outcome before retry."""
        record = self.show(operation_id)
        if record["state"] != "running":
            return record
        spec = self._spec(record)
        parent = self.experiment.show(spec.study.study_id)
        if parent["state"] == "completed":
            return self._finish(operation_id, "completed")
        with self.journal.transaction() as cx:
            self.experiment._ready(self.journal.latest(self.experiment._key(spec.study.study_id), cx), cx)
        phase, child, due = self._choose(record, parent)
        if _now() < due:
            return record
        with self.journal.transaction() as cx:
            record = self.journal.latest(KEY + operation_id, cx)
            parent = self.journal.latest(self.experiment._key(spec.study.study_id), cx)
            self.experiment._ready(parent, cx)
            data = Journal.document(record)
            attempts = [
                attempt
                for attempt in data["attempts"]
                if attempt["child"] == child
                and attempt["phase"] == phase
                and attempt.get("kind", "execute") != "reconcile"
            ]
            for attempt in attempts:
                if attempt["state"] == "running":
                    attempt["state"], attempt["unmeasured_crash_work"] = "interrupted", True
            reconcile = False
            if child:
                try:
                    reconcile = self.experiment.loop.show(child)["state"] == "completed"
                except KeyError:
                    pass
            if not reconcile and len(attempts) >= spec.max_attempts:
                data["state"] = "hold"
                data["failure"] = {
                    "type": "AttemptBudgetExhausted",
                    "at_ms": _now(),
                    "action": "inspect retained attempts; new approval required",
                }
                return self.journal.append(cx, KEY + operation_id, data)
            data["attempts"].append(
                {
                    "phase": phase,
                    "child": child,
                    "state": "running",
                    "started_ms": _now(),
                    "kind": "reconcile" if reconcile else "execute",
                }
            )
            record = self.journal.append(cx, KEY + operation_id, data)
            parent_data = Journal.document(parent)
            parent_data["operation"].update(child=child, due_ms=due)
            self.journal.append(cx, self.experiment._key(spec.study.study_id), parent_data)
        cpu, wall = time.process_time_ns(), time.monotonic_ns()
        error: Exception | None = None
        try:
            if parent[phase] is None:
                self.experiment._reserve(spec.study.study_id, [item.unit for item in getattr(spec, phase)], phase)
            self.experiment._run(spec.study.study_id, phase, max_runs=1)
        except Exception as exc:
            error = exc
        with self.journal.transaction() as cx:
            data = Journal.document(self.journal.latest(KEY + operation_id, cx))
            attempt = data["attempts"][-1]
            attempt.update(
                state="failed" if error else "committed",
                cpu_ns=time.process_time_ns() - cpu,
                wall_ns=time.monotonic_ns() - wall,
            )
            if error:
                data["failure"] = {
                    "type": type(error).__name__,
                    "at_ms": _now(),
                    "action": "inspect retained study and operation",
                }
                if data["state"] == "running":
                    data["state"] = "hold"
            result = self.journal.append(cx, KEY + operation_id, data)
        if error:
            raise error
        return result

    def _finish(self, operation_id: str, state: str) -> dict[str, Any]:
        with self.journal.transaction() as cx:
            record = self.journal.latest(KEY + operation_id, cx)
            data = Journal.document(record)
            if data["state"] == "running":
                data["state"] = state
            return self.journal.append(cx, KEY + operation_id, data)

    def run(self, operation_id: str) -> dict[str, Any]:
        """Run in this foreground OS process only; the existing operator lock bounds concurrency."""
        with _operator_lock(self.journal):
            with self.journal.transaction() as cx:
                record = self.journal.latest(KEY + operation_id, cx)
                data = Journal.document(record)
                if data["state"] != "running":
                    raise Conflict("operation is terminal or on HOLD; inspect it before creating new work")
                for session in data["sessions"]:
                    if session["state"] == "running":
                        session["state"] = "unclean-exit; unmeasured process work"
                data["sessions"].append({"started_ms": _now(), "state": "running"})
                data["interventions"].append(
                    {"action": "start-process", "at_ms": _now(), "actor": "operator-or-service"}
                )
                self.journal.append(cx, KEY + operation_id, data)
            cpu, wall = time.process_time_ns(), time.monotonic_ns()
            try:
                while self.show(operation_id)["state"] == "running":
                    if _now() >= self.show(operation_id)["expires_ms"]:
                        self._finish(operation_id, "expired")
                        break
                    self.advance(operation_id)
                    time.sleep(0.1)
            finally:
                with self.journal.transaction() as cx:
                    data = Journal.document(self.journal.latest(KEY + operation_id, cx))
                    data["sessions"][-1].update(
                        state="exited",
                        cpu_ns=time.process_time_ns() - cpu,
                        wall_ns=time.monotonic_ns() - wall,
                        ended_ms=_now(),
                    )
                    self.journal.append(cx, KEY + operation_id, data)
        return self.status(operation_id)

    def status(self, operation_id: str) -> dict[str, Any]:
        """One plain operator view; all historical receipts remain available in export."""
        record = self.show(operation_id)
        parent = self.experiment.show(record["spec"]["study"]["study_id"])
        phases = {phase: (parent.get(phase) or {}).get("runs", []) for phase in ("training", "confirmation")}
        runs = [run for group in phases.values() for run in group]
        artifact = (parent.get("freeze") or {}).get("manifest", {}).get("retained_program")
        spent = {}
        for phase in ("training", "confirmation"):
            for plan in (parent.get(phase) or {}).get("planned_campaigns", []):
                try:
                    spent[plan["campaign_id"]] = self.experiment.loop.show(plan["campaign_id"])["spent"]
                except KeyError:
                    continue
        latest_output = None
        selected = (
            (parent.get("freeze") or {}).get("manifest", {}).get("selected_policy", parent["spec"]["incumbent_policy"])
        )
        selected_runs = [run for run in runs if run["policy"] == selected]
        if selected_runs:
            chosen = selected_runs[-1]
            child = self.experiment.loop.show(chosen["campaign_id"])
            latest_output = {
                "unit": chosen["unit_id"],
                "policy": chosen["policy"],
                "notes": (child.get("result") or {}).get("results", {}).get("candidate", []),
            }
        active = False
        try:
            with _operator_lock(self.journal):
                pass
        except Conflict:
            active = True
        paused = self.journal.latest("@control")["state"] != "ready"
        return {
            "operation_id": operation_id,
            "state": record["state"],
            "executor_active": active,
            "operator_paused": paused,
            "what_is_running": "finite local source summaries; foreground executor only",
            "operator": record["spec"]["accountable_operator"],
            "expires_ms": record["expires_ms"],
            "completed_mission_comparisons": len(runs),
            "retained_capability": {
                "profile": parent["spec"]["archive_access"],
                "program_digest": artifact["program_digest"] if artifact else None,
                "artifact_digest": artifact["digest"] if artifact else None,
                "origin_campaign": artifact["origin_campaign"] if artifact else None,
                "fresh_trials": sum(bool(run.get("retained_program_tested")) for run in runs),
                "fresh_selections": sum(bool(run.get("retained_program_selected")) for run in runs),
                "comparisons_with_retained_worker": sum(bool(run.get("retained_worker_bound")) for run in runs),
                "authority_granted": False,
            },
            "inconclusive": sum(run["status"] != "complete" for run in runs),
            "changed_since_training": parent.get("freeze"),
            "improvement_evidence": (parent.get("confirmation") or {}).get("observed_policy_gain_ppm"),
            "costs": {
                "search_units_including_ancestors": sum(value["search_units"] for value in spent.values()),
                "execution_units_including_ancestors": sum(value["execution_units"] for value in spent.values()),
                "reserved_search_ceiling": record["spec"]["total_search_units"],
                "reserved_execution_ceiling": record["spec"]["total_execution_units"],
                "measured_process_cpu_ns": sum(session.get("cpu_ns", 0) for session in record["sessions"]),
                "measured_session_wall_ns": sum(session.get("wall_ns", 0) for session in record["sessions"]),
                "unclean_sessions": sum(session["state"].startswith("unclean") for session in record["sessions"]),
                "human_minutes": record["human_minutes"],
                "engineering_and_review": "not measured",
                "USDCBaseUnits": "0",
                "AGIALPHABaseUnits": "0",
            },
            "needs_attention": record["state"] in {"hold", "expired", "canceled"}
            or record["failure"] is not None
            or (record["state"] == "running" and (not active or paused or _now() >= record["expires_ms"])),
            "failure": record["failure"],
            "interventions": record["interventions"],
            "useful_output": "Source notes and checks: operation-export evidence.campaigns.*.result",
            "latest_output": latest_output,
            "stop": "alpha-agent --home HOME successor-study --output NEW.json operation-stop " + operation_id,
            "evidence_scope": (
                "synthetic mechanism when synthetic inputs are used; local structural checking; "
                "no commercial, comprehension or physical claim"
            ),
            "authority_granted": False,
        }

    def export(self, operation_id: str) -> dict[str, Any]:
        """Export inert public history, never the private identity or a resumable permission."""
        record = self.show(operation_id)
        try:
            inputs = {"status": "verified-submission", "spec": self._spec(record).model_dump()}
        except (ValueError, FileNotFoundError) as exc:
            inputs = {"status": "unavailable-or-changed", "error": type(exc).__name__, "binding": record["binding"]}
        return {
            "schema": "source-operation-history/v1",
            "operation": self.show(operation_id),
            "submitted_inputs": inputs,
            "status": self.status(operation_id),
            "evidence": self.experiment.export(self.show(operation_id)["spec"]["study"]["study_id"]),
            "active_authority": [],
        }
