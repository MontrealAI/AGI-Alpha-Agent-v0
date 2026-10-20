# SPDX-License-Identifier: Apache-2.0
"""Frozen discovery-policy comparisons using complete, durable native campaigns.

This is bounded policy selection in the source-selector domain. A campaign, not
an individual clause or correlated task, is the experimental unit. Local hashes
reject known reuse; external custody must establish sampling and independence.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from ..store import Conflict, Journal, canonical as journal_canonical, digest as journal_digest
from .protocol import canonical, digest
from .transformation import (
    DiscoveryLoop,
    DiscoveryRequest,
    IntentCharter,
    OperatorRegistry,
    SourceDocument,
    TIModel,
    _engine_digest,
    assert_public_content,
    validate_fresh_sources,
    validate_envelope,
)

KEY = "@discovery-policy-study:"
EXPOSURES = KEY + "exposures:v1"
MAX_EXPOSURE_EVENTS = 50_000
MAX_EXPOSURE_ROW_BYTES = 8 * 1024**2
MAX_EXPOSURE_BYTES = 64 * 1024**2


class _StudyLoop(DiscoveryLoop):
    """Check the parent permit in each native operation's own transaction."""

    def __init__(self, experiment: CampaignExperiment, spec: PolicyStudy, phase: str) -> None:
        super().__init__(experiment.journal)
        self.experiment, self.spec, self.phase = experiment, spec, phase

    def _running(self, cx: Any) -> None:
        super()._running(cx)
        parent = self.journal.latest(self.experiment._key(self.spec.study_id), cx)
        self.experiment._ready(parent, cx)
        expected = "training" if self.phase == "training" else "confirming"
        if parent["state"] != expected or parent["approval"] != parent["binding"]:
            raise Conflict("parent study permission was consumed or changed")


class DiscoveryPolicy(TIModel):
    """An executable bounded search policy; it cannot change an evaluator."""

    identity: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    operator_ids: list[Literal["representation", "production", "complementary"]] = Field(max_length=3)
    max_candidates: int = Field(ge=2, le=5, strict=True)

    @model_validator(mode="after")
    def distinct_operators(self) -> DiscoveryPolicy:
        if len(set(self.operator_ids)) != len(self.operator_ids):
            raise ValueError("duplicate discovery operator")
        return self


class CampaignUnit(TIModel):
    """All development, discovery, freeze and terminal work for one campaign."""

    unit_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    request: DiscoveryRequest
    terminal: list[SourceDocument] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def untouched_partition(self) -> CampaignUnit:
        validate_fresh_sources(self.request.development, self.terminal)
        assert_public_content(self.model_dump())
        return self


class PolicyStudy(TIModel):
    """Declare the whole comparison before any terminal study units are supplied."""

    study_id: str
    charter: IntentCharter
    policies: list[DiscoveryPolicy] = Field(min_length=2, max_length=8)
    incumbent_policy: str
    terminal_campaigns: int = Field(ge=2, le=64, strict=True)
    population: str = Field(min_length=1, max_length=1000)
    sampling_protocol: str = Field(min_length=1, max_length=2000)
    initial_agent: Literal["lead-source-selector/v1"] = "lead-source-selector/v1"
    archive_access: Literal["none"] = "none"
    search_cost_ppm_per_unit: int = Field(ge=0, le=1000, strict=True)

    @model_validator(mode="after")
    def fixed_basis(self) -> PolicyStudy:
        if str(uuid.UUID(self.study_id)) != self.study_id:
            raise ValueError("study requires a canonical UUID")
        identities = [policy.identity for policy in self.policies]
        if len(set(identities)) != len(identities) or self.incumbent_policy not in identities:
            raise ValueError("declare unique policies and the unchanged discovery policy")
        assert_public_content(self.model_dump())
        return self


def _binding(spec: PolicyStudy) -> str:
    path = Path(__file__)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 128_000:
            raise ValueError("study driver must be a bounded regular installed source file")
        content = stream.read(128_001)
    if len(content) > 128_000:
        raise ValueError("study driver exceeds its source byte budget")
    return digest(
        "discovery-policy-study-binding",
        {
            "spec": spec.model_dump(),
            "engine": _engine_digest(),
            "driver": hashlib.sha256(content).hexdigest(),
            "operator_manifests": {
                policy.identity: OperatorRegistry().manifest([str(identity) for identity in policy.operator_ids])
                for policy in spec.policies
            },
        },
    )


def _clause_ids(units: list[CampaignUnit]) -> list[str]:
    clauses = [
        " ".join(claim.text.casefold().split())
        for unit in units
        for doc in [*unit.request.development, *unit.terminal]
        for claim in doc.claims
    ]
    fingerprints = [digest("study-source-clause", text) for text in clauses]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("complete campaigns must not reuse known source clauses")
    return fingerprints


def study_request(spec: PolicyStudy, unit: CampaignUnit, policy: DiscoveryPolicy, phase: str) -> DiscoveryRequest:
    """Construct the single exact native child authorized by a reserved study plan."""
    request = unit.request.model_dump()
    request.update(
        campaign_id=str(uuid.uuid5(uuid.UUID(spec.study_id), phase + ":" + unit.unit_id + ":" + policy.identity)),
        operator_ids=policy.operator_ids,
        max_candidates=policy.max_candidates,
    )
    request["configuration"] = {
        **request["configuration"],
        "ti_parent_study": spec.study_id,
        "ti_parent_binding": _binding(spec),
        "ti_parent_phase": phase,
        "initial_agent": spec.initial_agent,
        "archive_access": spec.archive_access,
    }
    return DiscoveryRequest.model_validate(request)


def validate_child_lease(parent: dict[str, Any], request: DiscoveryRequest) -> None:
    """A parent lease covers only its exact planned child, inputs and allowances."""
    phase = request.configuration["ti_parent_phase"]
    plans = [item for item in parent[phase]["planned_campaigns"] if item["campaign_id"] == request.campaign_id]
    if len(plans) != 1:
        raise Conflict("parent study lease does not name this child campaign")
    plan = plans[0]
    units = [unit for unit in parent[phase]["units"] if unit["unit_id"] == plan["unit_id"]]
    spec = PolicyStudy.model_validate(parent["spec"])
    policies = [policy for policy in spec.policies if policy.identity == plan["policy"]]
    if len(units) != 1 or len(policies) != 1:
        raise Conflict("parent study lease has no unique unit and policy")
    expected = study_request(spec, CampaignUnit.model_validate(units[0]), policies[0], phase)
    if request != expected:
        raise Conflict("parent study lease cannot change its child's purpose, inputs, code or budget")


class CampaignExperiment:
    """One-shot training/confirmation with restart and no imported authority."""

    def __init__(self, journal: Journal) -> None:
        journal.verify()
        self.journal = journal
        self.loop = DiscoveryLoop(journal)

    def _key(self, study_id: str) -> str:
        return KEY + str(uuid.UUID(study_id))

    def show(self, study_id: str) -> dict[str, Any]:
        return self.journal.latest(self._key(study_id))

    def _ready(self, record: dict[str, Any], cx: Any) -> PolicyStudy:
        if self.journal.latest("@control", cx)["state"] != "ready":
            raise Conflict("operator STOP is active")
        if record["state"] in {"paused", "canceled"}:
            raise Conflict("study is paused or canceled")
        spec = PolicyStudy.model_validate(record["spec"])
        if record["binding"] != _binding(spec):
            raise Conflict("study code or comparison basis changed; new study required")
        return spec

    def create(self, spec: PolicyStudy) -> dict[str, Any]:
        spec = PolicyStudy.model_validate(spec.model_dump())
        # Explicitly bind the actual installed operators, in addition to driver code.
        for policy in spec.policies:
            self.loop.registry.manifest([str(identity) for identity in policy.operator_ids])
        with self.journal.transaction() as cx:
            try:
                previous = self.journal.latest(self._key(spec.study_id), cx)
            except KeyError:
                return self.journal.append(
                    cx,
                    self._key(spec.study_id),
                    {
                        "schema": "discovery-policy-study/v1",
                        "spec": spec.model_dump(),
                        "binding": _binding(spec),
                        "state": "proposed",
                        "approval": None,
                        "training": None,
                        "freeze": None,
                        "confirmation": None,
                        "history": [],
                    },
                )
            if previous["binding"] != _binding(spec):
                raise Conflict("study identity cannot replace its comparison basis")
            return previous

    def approve(self, study_id: str, binding: str) -> dict[str, Any]:
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(study_id), cx)
            self._ready(record, cx)
            if record["state"] != "proposed" or binding != record["binding"]:
                raise Conflict("approve the exact proposed comparison")
            if record["approval"] == binding:
                return record
            data = Journal.document(record)
            data["approval"] = binding
            return self.journal.append(cx, self._key(study_id), data)

    def control(self, study_id: str, action: Literal["pause", "resume", "cancel"]) -> dict[str, Any]:
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(study_id), cx)
            data = Journal.document(record)
            if action == "pause" and data["state"] in {"proposed", "training", "trained", "confirming"}:
                data["resume_state"], data["state"] = data["state"], "paused"
            elif action == "resume" and data["state"] == "paused":
                if data["binding"] != _binding(PolicyStudy.model_validate(data["spec"])):
                    raise Conflict("study code changed while paused")
                if self.journal.latest("@control", cx)["state"] != "ready":
                    raise Conflict("operator STOP is active")
                data["state"] = data.pop("resume_state")
            elif action == "cancel" and data["state"] != "completed":
                data["state"], data["approval"] = "canceled", None
            else:
                raise Conflict("invalid study control transition")
            data["history"].append({"action": action, "revision": record["revision"]})
            return self.journal.append(cx, self._key(study_id), data)

    def _known_clauses(self, cx: Any) -> set[str]:
        """Read every authenticated event document in the caller's transaction."""
        if not cx.in_transaction:
            raise Conflict("history exposure scan requires the study transaction")
        event_count, history_bytes = 0, 0
        with closing(
            cx.execute(
                "SELECT length(CAST(mission AS BLOB)) + length(CAST(body AS BLOB)) + "
                "length(CAST(hash AS BLOB)) + length(CAST(signature AS BLOB)) "
                "FROM events ORDER BY seq LIMIT ?",
                (MAX_EXPOSURE_EVENTS + 1,),
            )
        ) as rows:
            for (size,) in rows:
                event_count += 1
                if (
                    event_count > MAX_EXPOSURE_EVENTS
                    or not isinstance(size, int)
                    or not 0 <= size <= MAX_EXPOSURE_ROW_BYTES
                ):
                    raise Conflict("history exposure event capacity reached; external checkpoint required")
                history_bytes += size
                if history_bytes > MAX_EXPOSURE_BYTES:
                    raise Conflict("history exposure byte capacity reached; external checkpoint required")
        missions: set[str] = set()
        with closing(cx.execute("SELECT mission FROM events ORDER BY seq LIMIT ?", (MAX_EXPOSURE_EVENTS + 1,))) as rows:
            for (mission,) in rows:
                if not isinstance(mission, str):
                    raise ValueError("journal mission is corrupt")
                missions.add(mission)
                if len(missions) > 5000:
                    raise Conflict("history exposure scan capacity reached; external checkpoint required")
        seen: set[str] = set()
        nodes, sequence = 0, 0
        previous = "0" * 64
        public_key = self.journal.key.public_key()
        with closing(
            cx.execute(
                "SELECT seq,mission,body,hash,signature FROM events ORDER BY seq LIMIT ?",
                (MAX_EXPOSURE_EVENTS + 1,),
            )
        ) as rows:
            for seq, mission, raw, hashed, signature in rows:
                sequence += 1
                if sequence > event_count:
                    raise Conflict("history exposure snapshot changed")
                body = json.loads(raw)
                if not isinstance(raw, str) or journal_canonical(body) != raw.encode("utf-8"):
                    raise ValueError("journal canonical bytes differ")
                if not isinstance(body, dict) or (
                    body["schema"] != 1
                    or seq != sequence
                    or body["sequence"] != seq
                    or body["previous"] != previous
                    or body["identity"] != self.journal.identity
                    or body["mission"] != mission
                    or journal_digest(body) != hashed
                ):
                    raise ValueError("journal content is corrupt")
                public_key.verify(base64.b64decode(signature, validate=True), bytes.fromhex(hashed))
                previous = hashed
                document = body["document"]
                if not isinstance(document, dict):
                    raise ValueError("journal document is corrupt")
                pending = [document]
                while pending:
                    item = pending.pop()
                    nodes += 1
                    if nodes > 1_000_000:
                        raise Conflict("history exposure scan exceeds its structural budget")
                    if isinstance(item, dict):
                        if item.get("schema") == "source-document/v1":
                            document = SourceDocument.model_validate(item)
                            seen.update(
                                digest("study-source-clause", " ".join(claim.text.casefold().split()))
                                for claim in document.claims
                            )
                        else:
                            pending.extend(item.values())
                    elif isinstance(item, list):
                        pending.extend(item)
        if sequence != event_count:
            raise Conflict("history exposure snapshot changed")
        return seen

    def _reserve(self, study_id: str, units: list[CampaignUnit], phase: str) -> dict[str, Any]:
        units = [CampaignUnit.model_validate(unit.model_dump()) for unit in units]
        if not 1 <= len(units) <= 64 or len({unit.unit_id for unit in units}) != len(units):
            raise ValueError("supply distinct bounded complete campaigns")
        if len(canonical(units)) > 128_000:
            raise ValueError("complete campaign batch exceeds its retained input byte budget")
        clauses = _clause_ids(units)
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(study_id), cx)
            spec = self._ready(record, cx)
            if any(unit.request.charter != spec.charter for unit in units):
                raise PermissionError("campaign changed the authorized study purpose, permissions or budget")
            input_digest = digest("study-units", units)
            if record[phase] is not None:
                if record[phase]["input_digest"] != input_digest:
                    raise Conflict("exposed campaign batch cannot be replaced or repeatedly tested")
                return record
            if record["approval"] != record["binding"]:
                raise PermissionError("review and approve the full policy comparison first")
            expected = "proposed" if phase == "training" else "trained"
            if record["state"] != expected:
                raise Conflict("train and freeze discovery policies before fresh confirmation")
            if phase == "confirmation" and len(units) != spec.terminal_campaigns:
                raise ValueError("supply the entire preregistered campaign sample at once")
            try:
                exposures = Journal.document(self.journal.latest(EXPOSURES, cx))
            except KeyError:
                exposures = {"schema": "discovery-policy-exposures/v1", "clauses": [], "units": []}
            if set(clauses) & (set(exposures["clauses"]) | self._known_clauses(cx)) or {u.unit_id for u in units} & set(
                exposures["units"]
            ):
                raise Conflict("known training or terminal campaign exposure cannot become fresh evidence")
            if len(exposures["clauses"]) + len(clauses) > 100_000:
                raise Conflict("campaign exposure ledger capacity reached; external checkpoint required")
            exposures["clauses"].extend(clauses)
            exposures["units"].extend(unit.unit_id for unit in units)
            self.journal.append(cx, EXPOSURES, exposures)
            data = Journal.document(record)
            data[phase] = {
                "input_digest": input_digest,
                "units": [unit.model_dump() for unit in units],
                "runs": [],
                "planned_campaigns": [
                    {
                        "unit_id": unit.unit_id,
                        "policy": policy.identity,
                        "campaign_id": str(
                            uuid.uuid5(uuid.UUID(spec.study_id), phase + ":" + unit.unit_id + ":" + policy.identity)
                        ),
                    }
                    for unit in units
                    for policy in spec.policies
                ],
            }
            data["state"] = "training" if phase == "training" else "confirming"
            data["history"].append({"action": "reserve-" + phase, "revision": record["revision"]})
            return self.journal.append(cx, self._key(study_id), data)

    def _campaign(self, spec: PolicyStudy, unit: CampaignUnit, policy: DiscoveryPolicy, phase: str) -> dict[str, Any]:
        native = study_request(spec, unit, policy, phase)
        campaign_id = native.campaign_id
        loop = _StudyLoop(self, spec, phase)
        current = loop.create(native)
        if current["state"] not in {"frozen", "completed"}:
            loop.approve(campaign_id, current["binding_digest"])
            for step in ("diagnose", "develop", "freeze"):
                current = loop.step(campaign_id, operation_id="study-" + step)
        if current["state"] == "frozen":
            current = loop.confirm(campaign_id, unit.terminal, current["freeze"]["digest"])
        result = current.get("result") or {}
        score = result.get("means_millionths", {}).get("candidate")
        spent = current["spent"]
        return {
            "unit_id": unit.unit_id,
            "policy": policy.identity,
            "campaign_id": campaign_id,
            "campaign_record_digest": current["digest"],
            "campaign_revision": current["revision"],
            "status": "complete" if score is not None and not result.get("failure") else "inconclusive",
            "terminal_score_ppm": score,
            "search_units": spent["search_units"],
            "execution_units": spent["execution_units"],
            "utility_ppm": (
                None
                if score is None or result.get("failure")
                else score - spec.search_cost_ppm_per_unit * spent["search_units"]
            ),
            "native_envelope_digest": digest("study-native-envelope", self.loop.envelope(campaign_id)),
        }

    def export(self, study_id: str) -> dict[str, Any]:
        """Expand immutable child references for independent offline inspection."""
        record = self.show(study_id)
        campaigns = {}
        pending_campaigns = {}
        for phase in ("training", "confirmation"):
            for run in (record.get(phase) or {}).get("runs", []):
                child = self.loop.show(run["campaign_id"])
                envelope = validate_envelope(self.loop.envelope(run["campaign_id"]))
                if child["digest"] != run["campaign_record_digest"] or child["revision"] != run["campaign_revision"]:
                    raise Conflict("retained child campaign identity changed")
                if digest("study-native-envelope", envelope) != run["native_envelope_digest"]:
                    raise Conflict("retained campaign envelope changed")
                campaigns[run["campaign_id"]] = envelope
            for planned in (record.get(phase) or {}).get("planned_campaigns", []):
                if planned["campaign_id"] in campaigns:
                    continue
                try:
                    pending_campaigns[planned["campaign_id"]] = self.loop.show(planned["campaign_id"])
                except KeyError:
                    pending_campaigns[planned["campaign_id"]] = {
                        "state": "not-started",
                        "spent": {"search_units": 0, "execution_units": 0},
                    }
        result = {
            "schema": "discovery-policy-evidence/v1",
            "study": record,
            "campaigns": campaigns,
            "pending_campaigns": pending_campaigns,
            "authority_granted": False,
            "independent_review": "pending",
        }
        if len(canonical(result)) > 8_000_000:
            raise ValueError("export exceeds byte budget; inspect referenced child campaigns separately")
        return result

    def _run(self, study_id: str, phase: str) -> dict[str, Any]:
        record = self.show(study_id)
        finished = {"trained", "confirming", "completed"} if phase == "training" else {"completed"}
        if record["state"] in finished:
            return record
        expected_state = "training" if phase == "training" else "confirming"
        if record["state"] != expected_state:
            raise Conflict("study phase is out of order")
        spec = PolicyStudy.model_validate(record["spec"])
        units = [CampaignUnit.model_validate(unit) for unit in record[phase]["units"]]
        for unit in units:
            for policy in spec.policies:
                with self.journal.transaction() as cx:
                    current = self.journal.latest(self._key(study_id), cx)
                    self._ready(current, cx)
                    if any(
                        r["unit_id"] == unit.unit_id and r["policy"] == policy.identity for r in current[phase]["runs"]
                    ):
                        continue
                run = self._campaign(spec, unit, policy, phase)
                with self.journal.transaction() as cx:
                    current = self.journal.latest(self._key(study_id), cx)
                    self._ready(current, cx)
                    data = Journal.document(current)
                    if not any(
                        r["unit_id"] == unit.unit_id and r["policy"] == policy.identity for r in data[phase]["runs"]
                    ):
                        data[phase]["runs"].append(run)
                        self.journal.append(cx, self._key(study_id), data)
        with self.journal.transaction() as cx:
            current = self.journal.latest(self._key(study_id), cx)
            self._ready(current, cx)
            if current["state"] in finished:
                return current
            if current["state"] != expected_state:
                raise Conflict("study phase changed before finalization")
            data = Journal.document(current)
            means = {}
            for policy in spec.policies:
                runs = [r for r in data[phase]["runs"] if r["policy"] == policy.identity]
                means[policy.identity] = (
                    None
                    if any(r["status"] != "complete" for r in runs)
                    else sum(r["utility_ppm"] for r in runs) // len(units)
                )
            data[phase]["mean_utility_ppm"] = means
            if phase == "training":
                incumbent = means[spec.incumbent_policy]
                eligible = [(value, identity) for identity, value in means.items() if value is not None]
                best = (
                    sorted(eligible, key=lambda item: (-item[0], item[1]))[0][1] if eligible else spec.incumbent_policy
                )
                if incumbent is not None and (means[best] is None or means[best] <= incumbent):
                    best = spec.incumbent_policy
                manifest = {
                    "binding": data["binding"],
                    "selected_policy": best,
                    "training_digest": digest("study-training", data[phase]),
                    "terminal_campaigns": spec.terminal_campaigns,
                    "sampling_unit": "complete-campaign",
                    "initial_agent": spec.initial_agent,
                    "archive_access": spec.archive_access,
                }
                data["freeze"] = {
                    "manifest": manifest,
                    "digest": digest("discovery-policy-freeze", manifest),
                    "journal_predecessor": current["digest"],
                }
                data["state"] = "trained"
            else:
                selected = data["freeze"]["manifest"]["selected_policy"]
                candidate, incumbent = means[selected], means[spec.incumbent_policy]
                data[phase]["paired_campaign_differences_ppm"] = (
                    [
                        next(
                            r["utility_ppm"]
                            for r in data[phase]["runs"]
                            if r["unit_id"] == unit.unit_id and r["policy"] == selected
                        )
                        - next(
                            r["utility_ppm"]
                            for r in data[phase]["runs"]
                            if r["unit_id"] == unit.unit_id and r["policy"] == spec.incumbent_policy
                        )
                        for unit in units
                    ]
                    if candidate is not None and incumbent is not None
                    else None
                )
                data[phase]["observed_policy_gain_ppm"] = (
                    None if candidate is None or incumbent is None else candidate - incumbent
                )
                data[phase]["claim"] = (
                    "observed bounded discovery-policy comparison; no calibrated "
                    "outcome or general transfer certificate"
                )
                data[phase]["independence"] = (
                    "known exact clause reuse rejected in this Journal; external "
                    "sampling/custody and semantic independence unestablished"
                )
                data[phase]["costs"] = {
                    "search_units": sum(r["search_units"] for r in data[phase]["runs"]),
                    "execution_units": sum(r["execution_units"] for r in data[phase]["runs"]),
                    "paid_model_calls": 0,
                    "USDCBaseUnits": "0",
                    "AGIALPHABaseUnits": "0",
                    "construction_migration_maintenance_human_effort": "not measured",
                    "economic_break_even": "not established",
                }
                data["state"], data["approval"] = "completed", None
            return self.journal.append(cx, self._key(study_id), data)

    def train(self, study_id: str, units: list[CampaignUnit]) -> dict[str, Any]:
        self._reserve(study_id, units, "training")
        return self._run(study_id, "training")

    def confirm(self, study_id: str, units: list[CampaignUnit], freeze_digest: str) -> dict[str, Any]:
        current = self.show(study_id)
        freeze = current.get("freeze")
        if (
            not freeze
            or freeze["digest"] != freeze_digest
            or digest("discovery-policy-freeze", freeze["manifest"]) != freeze_digest
        ):
            raise Conflict("freeze the learned discovery policy before supplying terminal campaigns")
        self._reserve(study_id, units, "confirmation")
        return self._run(study_id, "confirmation")
