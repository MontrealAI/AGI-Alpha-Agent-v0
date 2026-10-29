# SPDX-License-Identifier: Apache-2.0
"""Immutable, inert evidence contracts; an objection never confers execution authority."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import MISSING, dataclass, fields, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Self, cast


class Verdict(str, Enum):
    CONFIRMED = "CONFIRMED"
    REFUTED = "REFUTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    NO_DEFECT_ESTABLISHED = "NO_DEFECT_ESTABLISHED"


class Acceptance(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    STATIC_ONLY = "STATIC_ONLY"


EXPERIMENT_KINDS = frozenset({"static-dimension-dominance", "source-literal", "dynamic-paired"})
MAX_BYTES = 1_048_576


def _text(value: Any, *, limit: int = 16_000) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError("bounded nonempty text required")
    return value


def _ident(value: Any) -> str:
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", value) is None:
        raise ValueError("bounded identifier required")
    return value


def _hash(value: Any) -> str:
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise ValueError("SHA256 lowercase hexadecimal required")
    return value


def _json(value: Any) -> Any:
    count = 0

    def freeze(item: Any, depth: int) -> Any:
        nonlocal count
        count += 1
        if count > 20_000 or depth > 24:
            raise ValueError("inert JSON structural bound exceeded")
        if item is None or type(item) in {bool, int}:
            if type(item) is int and abs(item) > 10**18:
                raise ValueError("inert JSON integer bound exceeded")
            return item
        if type(item) is str:
            if len(item) > MAX_BYTES:
                raise ValueError("inert JSON string bound exceeded")
            return item
        if type(item) in {list, tuple}:
            return tuple(freeze(child, depth + 1) for child in item)
        if type(item) in {dict, MappingProxyType} and all(type(key) is str for key in item):
            return MappingProxyType({key: freeze(child, depth + 1) for key, child in item.items()})
        raise ValueError("inert exact JSON required; no floats, objects or code")

    result = freeze(value, 0)
    if len(_canonical(_plain(result))) > MAX_BYTES:
        raise ValueError("inert JSON byte bound exceeded")
    return result


def _mapping(value: Any) -> Mapping[str, Any]:
    if type(value) not in {dict, MappingProxyType}:
        raise ValueError("evidence object required")
    return cast(Mapping[str, Any], _json(value))


def _strings(value: Any, *, nonempty: bool = False, limit: int = 64) -> tuple[str, ...]:
    if type(value) not in {tuple, list} or len(value) > limit or (nonempty and not value):
        raise ValueError("bounded text sequence required")
    return tuple(_text(item) for item in value)


def _plain(value: Any) -> Any:
    if isinstance(value, Record):
        return value.to_dict()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _plain(child) for key, child in value.items()}
    if type(value) in {list, tuple}:
        return [_plain(child) for child in value]
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


@dataclass(frozen=True)
class Record:
    """Strict portable serialization with no executable deserialization hooks."""

    @classmethod
    def from_dict(cls, value: Any) -> Self:
        if type(value) is not dict:
            raise ValueError("record object required")
        declared = {field.name for field in fields(cls)}
        required = {
            field.name for field in fields(cls) if field.default is MISSING and field.default_factory is MISSING
        }
        if not required <= set(value) or set(value) - declared:
            raise ValueError("record schema mismatch")
        try:
            return cls(**value)
        except TypeError as error:
            raise ValueError("record type mismatch") from error

    def to_dict(self) -> dict[str, Any]:
        return {field.name: _plain(getattr(self, field.name)) for field in fields(self)}

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()


@dataclass(frozen=True)
class SourceLocation(Record):
    source_id: str
    location: str
    sha256: str

    def __post_init__(self) -> None:
        _ident(self.source_id)
        _text(self.location, limit=1024)
        _hash(self.sha256)
        if not (self.location.startswith("/") or re.fullmatch(r"line:[1-9][0-9]*(?:-[1-9][0-9]*)?", self.location)):
            raise ValueError("exact source JSON pointer or line location required")


@dataclass(frozen=True)
class Experiment(Record):
    id: str
    kind: str
    hypothesis: str
    pass_observation: str
    fail_observation: str
    unresolved: tuple[str, ...]
    estimated_cost: Mapping[str, Any]

    def __post_init__(self) -> None:
        _ident(self.id)
        if self.kind not in EXPERIMENT_KINDS:
            raise ValueError("uninstalled experiment kind; no command or generated host code")
        for value in [self.hypothesis, self.pass_observation, self.fail_observation]:
            _text(value)
        if self.pass_observation == self.fail_observation:
            raise ValueError("experiment must declare discriminating observations")
        object.__setattr__(self, "unresolved", _strings(self.unresolved, nonempty=True))
        cost = _mapping(self.estimated_cost)
        if not cost or len(cost) > 16:
            raise ValueError("explicit bounded estimated cost required")
        for name, value in cost.items():
            _ident(name)
            if value != "UNKNOWN" and (type(value) is not int or not 0 <= value <= 10**18):
                raise ValueError("cost must be an exact nonnegative integer or UNKNOWN")
        object.__setattr__(self, "estimated_cost", cost)


@dataclass(frozen=True)
class Objection(Record):
    id: str
    candidate_hash: str
    claim_id: str
    requirement_id: str
    requirement: str
    source: SourceLocation
    witness: Mapping[str, Any]
    consequence: str
    causal_explanation: str
    test: Experiment
    retraction_criteria: tuple[str, ...]
    uncertainty: str
    alternatives: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    provenance: Mapping[str, Any]
    severity: int
    evidence_strength: int
    revision: int = 0
    parent_hash: str | None = None

    def __post_init__(self) -> None:
        for value in [self.id, self.claim_id, self.requirement_id]:
            _ident(value)
        _hash(self.candidate_hash)
        for value in [self.requirement, self.consequence, self.causal_explanation, self.uncertainty]:
            _text(value)
        source: Any = self.source
        test: Any = self.test
        if type(source) is dict:
            object.__setattr__(self, "source", SourceLocation.from_dict(source))
        if type(test) is dict:
            object.__setattr__(self, "test", Experiment.from_dict(test))
        if type(self.source) is not SourceLocation or type(self.test) is not Experiment:
            raise ValueError("typed source and experiment required")
        witness, provenance = _mapping(self.witness), _mapping(self.provenance)
        if not witness or not provenance:
            raise ValueError("explicit witness and provenance required")
        object.__setattr__(self, "witness", witness)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "retraction_criteria", _strings(self.retraction_criteria, nonempty=True))
        object.__setattr__(self, "alternatives", _strings(self.alternatives, nonempty=True))
        object.__setattr__(self, "missing_capabilities", _strings(self.missing_capabilities))
        for ranking_value in [self.severity, self.evidence_strength]:
            if type(ranking_value) is not int or not 1 <= ranking_value <= 3:
                raise ValueError("supported severity and evidence strength must be integers 1..3")
        if type(self.revision) is not int or not 0 <= self.revision <= 1000:
            raise ValueError("bounded objection revision required")
        if self.revision == 0:
            if self.parent_hash is not None:
                raise ValueError("original objection cannot claim a parent")
        else:
            _hash(self.parent_hash)

    def revise(self, **changes: Any) -> Self:
        if set(changes) & {"id", "candidate_hash", "revision", "parent_hash"}:
            raise ValueError("revision cannot replace objection or candidate identity")
        return replace(self, **changes, revision=self.revision + 1, parent_hash=self.digest)


@dataclass(frozen=True)
class CriticFinding(Record):
    candidate_hash: str
    objections: tuple[Objection, ...]
    no_defect_rationale: str | None
    search_limits: tuple[str, ...]
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        _hash(self.candidate_hash)
        if type(self.objections) not in {tuple, list} or len(self.objections) > 64:
            raise ValueError("bounded objection sequence required")
        raw_objections: Any = self.objections
        objections: tuple[Objection, ...] = tuple(
            Objection.from_dict(item) if type(item) is dict else item for item in raw_objections
        )
        if any(not isinstance(item, Objection) or item.candidate_hash != self.candidate_hash for item in objections):
            raise ValueError("finding objections must bind the same candidate")
        if len({item.id for item in objections}) != len(objections):
            raise ValueError("duplicate objection identity")
        if objections:
            if self.no_defect_rationale is not None:
                raise ValueError("objections and no-defect rationale are exclusive")
        else:
            _text(self.no_defect_rationale)
        object.__setattr__(self, "objections", objections)
        object.__setattr__(self, "search_limits", _strings(self.search_limits, nonempty=True))
        provenance = _mapping(self.provenance)
        if not provenance:
            raise ValueError("finding provenance required")
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True)
class Adjudication(Record):
    objection_id: str | None
    candidate_hash: str
    verdict: Verdict
    reason: str
    evidence_hashes: tuple[str, ...]
    counterevidence: tuple[str, ...]
    scope: str
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        _hash(self.candidate_hash)
        try:
            verdict = Verdict(self.verdict)
        except (TypeError, ValueError) as error:
            raise ValueError("one of four objection verdicts required") from error
        object.__setattr__(self, "verdict", verdict)
        if verdict == Verdict.NO_DEFECT_ESTABLISHED:
            if self.objection_id is not None:
                raise ValueError("no-defect outcome must not invent an objection")
        elif verdict != Verdict.INCONCLUSIVE or self.objection_id is not None:
            _ident(self.objection_id)
        _text(self.reason)
        _text(self.scope)
        hashes = _strings(self.evidence_hashes)
        for value in hashes:
            _hash(value)
        if verdict in {Verdict.CONFIRMED, Verdict.REFUTED} and not hashes:
            raise ValueError("confirmed or refuted objection requires evidence hashes")
        object.__setattr__(self, "evidence_hashes", hashes)
        object.__setattr__(self, "counterevidence", _strings(self.counterevidence))
        provenance = _mapping(self.provenance)
        if not provenance:
            raise ValueError("adjudication provenance required")
        object.__setattr__(self, "provenance", provenance)


def rank_objections(objections: Iterable[Objection]) -> tuple[Objection, ...]:
    """Prioritize evidence before supported consequence; display uncertainty and costs separately."""
    values = tuple(objections)
    if len(values) > 64 or any(not isinstance(item, Objection) for item in values):
        raise ValueError("bounded typed objections required")

    def key(item: Objection) -> tuple[int, int, int, str]:
        wall = item.test.estimated_cost.get("wall_ms", "UNKNOWN")
        return (-item.evidence_strength, -item.severity, wall if type(wall) is int else 10**18, item.id)

    return tuple(sorted(values, key=key))
