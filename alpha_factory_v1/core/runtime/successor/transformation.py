# SPDX-License-Identifier: Apache-2.0
"""Durable bounded formulation discovery, with an executable source-understanding pilot.

The local score checks a supplied argument representation, not human understanding.
The unrestricted control deliberately matches the best constructed formulation.
Imported content is inert data; only explicitly installed operators run.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import itertools
import os
import re
import stat
import time
import sys
from types import CodeType
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import unquote, urlsplit

import pydantic
from pydantic import ConfigDict, Field, model_validator

from ..store import Conflict, Journal, private_write
from .protocol import StrictModel, canonical, digest, safe_json_loads

SCHEMA = "transformational-intelligence/v1"
KEY = "@transformation:"
AXES = ("representation", "information", "dependency", "production", "task-boundary", "mechanism", "evaluation")
PHASES = ("queued", "diagnosed", "developed", "frozen", "completed")
MAX_CLAIMS = 12
MAX_UNITS = 1_000_000
SENSITIVE_KEYS = frozenset(
    {
        "apikey",
        "privatekey",
        "accesstoken",
        "refreshtoken",
        "clientsecret",
        "password",
        "passphrase",
        "mnemonic",
        "seedphrase",
        "secret",
        "authorization",
    }
)


def assert_public_content(value: Any) -> None:
    """Reject credential-shaped fields before retention; this is not a privacy classifier."""
    pending = [(value, 0)]
    nodes = 0
    pattern = re.compile(
        r"(?:api[_ -]?key|private[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passphrase|client[_ -]?secret|secret|mnemonic|seed[_ -]?phrase|authorization)[\"' ]*\s*[:=]\s*[\"']?[^\s\"'},]+|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,})",
        re.IGNORECASE,
    )
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > 100_000 or depth > 32:
            raise ValueError("public input exceeds its structural budget")
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = re.sub(r"[^a-z0-9]", "", _decode_public_text(key).lower())
                if normalized in SENSITIVE_KEYS and isinstance(child, str) and child.strip():
                    raise ValueError(
                        "public-only input contains a credential-shaped field; remove it before continuing"
                    )
                pending.append((child, depth + 1))
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            decoded = _decode_public_text(item)
            if pattern.search(decoded):
                raise ValueError("public-only input contains credential-shaped text; remove it before continuing")
            if decoded.lstrip().startswith(("{", "[", '"')):
                try:
                    nested = safe_json_loads(decoded)
                except ValueError:
                    pass
                else:
                    pending.append((nested, depth + 1))


def _decode_public_text(text: str) -> str:
    for _ in range(3):
        decoded = unquote(re.sub(r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), text))
        if decoded == text:
            break
        text = decoded
    return text


class TIModel(StrictModel):
    """Serialize version labels under their portable alias without shadowing methods."""

    model_config = ConfigDict(serialize_by_alias=True, validate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def exact_literal_types(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for field in ("publicOnly", "public_non_personal", "removable"):
                if field in values and type(values[field]) is not bool:
                    raise ValueError("boolean fields reject integer substitution")
            if "money_minor" in values and type(values["money_minor"]) is not int:
                raise ValueError("money_minor requires an exact integer")
        return values


class DiscoveryBudget(TIModel):
    """Declare bounded logical work and separate currency allowances."""

    search_units: int = Field(default=100_000, ge=0, le=MAX_UNITS)
    execution_units: int = Field(default=100_000, ge=0, le=MAX_UNITS)
    money_minor: Literal[0] = 0
    USDCBaseUnits: Literal["0"] = "0"
    AGIALPHABaseUnits: Literal["0"] = "0"


class IntentCharter(TIModel):
    """Authorized ends and resources stay outside candidate optimization."""

    record_schema: Literal["intent-charter/v1"] = Field(default="intent-charter/v1", alias="schema")
    purpose: str = Field(min_length=1, max_length=2000)
    population: str = Field(min_length=1, max_length=500)
    outcomes: list[str] = Field(min_length=1, max_length=12)
    constraints: list[str] = Field(min_length=1, max_length=20)
    permitted_actions: list[Literal["read-public-source", "construct-bounded", "evaluate-local", "write-artifact"]]
    publicOnly: Literal[True] = True
    budgets: DiscoveryBudget = Field(default_factory=DiscoveryBudget)
    payment_route: Literal["none", "USDC", "AGIALPHA"] = "none"
    artifact: Literal["fixed-summary"] = "fixed-summary"
    max_clauses: int = Field(default=3, ge=1, le=MAX_CLAIMS)

    @model_validator(mode="after")
    def bounded_purpose(self) -> IntentCharter:
        if len(set(self.permitted_actions)) != len(self.permitted_actions):
            raise ValueError("duplicate permitted action")
        if any(not value.strip() or len(value) > 2000 for value in self.outcomes + self.constraints):
            raise ValueError("outcomes and constraints require bounded nonempty text")
        return self


class Assumption(TIModel):
    """A restriction's type and provenance are recorded before changing it."""

    name: str = Field(min_length=1, max_length=200)
    kind: Literal["authorized-end", "hard-constraint", "environmental-fact", "uncertain-hypothesis", "inherited-design"]
    statement: str = Field(min_length=1, max_length=2000)
    provenance: str = Field(min_length=1, max_length=2000)
    removable: bool = False

    @model_validator(mode="after")
    def mandatory(self) -> Assumption:
        if self.removable and self.kind in {"authorized-end", "hard-constraint", "environmental-fact"}:
            raise ValueError("mandatory requirements and known facts cannot be silently removed")
        return self


class Formulation(TIModel):
    """Versioned representations, assumptions, information, policy and intermediate goals."""

    record_schema: Literal["formulation/v1"] = Field(default="formulation/v1", alias="schema")
    representation: str = Field(min_length=1, max_length=2000)
    assumptions: list[Assumption] = Field(min_length=1, max_length=32)
    information_protocol: str = Field(min_length=1, max_length=2000)
    policy_language: Literal["source-clause-selector/v1"] = "source-clause-selector/v1"
    intermediate_objectives: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def bounded_objectives(self) -> Formulation:
        if any(not value or len(value) > 2000 for value in self.intermediate_objectives):
            raise ValueError("intermediate objectives require bounded nonempty text")
        return self


class SourceClaim(TIModel):
    """An auditable clause with declared prerequisites; never a tool instruction."""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    text: str = Field(min_length=1, max_length=1500)
    weight: int = Field(ge=1, le=1000)
    depends_on: list[str] = Field(default_factory=list, max_length=MAX_CLAIMS)
    provenance: str = Field(min_length=1, max_length=2000)


class SourceDocument(TIModel):
    """Public data and supplied argument judgments, with no executable payloads."""

    record_schema: Literal["source-document/v1"] = Field(default="source-document/v1", alias="schema")
    title: str = Field(min_length=1, max_length=500)
    source_url: str = Field(min_length=1, max_length=2000)
    public_non_personal: Literal[True] = True
    claims: list[SourceClaim] = Field(min_length=1, max_length=MAX_CLAIMS)

    @model_validator(mode="after")
    def complete_graph(self) -> SourceDocument:
        assert_public_content(self.model_dump())
        url = urlsplit(self.source_url)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
            raise ValueError("source provenance requires a public HTTPS reference without credentials")
        names = {claim.id for claim in self.claims}
        if len(names) != len(self.claims):
            raise ValueError("source claim identifiers must be unique")
        for claim in self.claims:
            if len(set(claim.depends_on)) != len(claim.depends_on) or not set(claim.depends_on) <= names:
                raise ValueError("source dependencies must be unique references to retained claims")
            if claim.id in claim.depends_on:
                raise ValueError("a claim cannot depend on itself")
        pending = {claim.id: set(claim.depends_on) for claim in self.claims}
        while pending:
            roots = {name for name, dependencies in pending.items() if not dependencies}
            if not roots:
                raise ValueError("source dependencies must form an acyclic graph")
            pending = {name: dependencies - roots for name, dependencies in pending.items() if name not in roots}
        return self


class SelectionProgram(TIModel):
    """The closed language cannot alter the charter, evaluator or external environment."""

    record_schema: Literal["selection-program/v1"] = Field(default="selection-program/v1", alias="schema")
    representation: Literal["sequence", "argument-graph"] = "sequence"
    production: Literal["lead", "weighted", "audit-after", "closure-search"] = "lead"


class TransformationWitness(TIModel):
    """Paper Appendix D fields remain explicit for successes and failed proposals."""

    purpose: str = Field(min_length=1, max_length=4000)
    inherited_restriction: str = Field(min_length=1, max_length=4000)
    provenance: str = Field(min_length=1, max_length=4000)
    proposed_change: str = Field(min_length=1, max_length=4000)
    prerequisites: list[str] = Field(min_length=1, max_length=32)
    fallback: str = Field(min_length=1, max_length=4000)
    outcome_bridge: dict[str, Any]
    falsifier: str = Field(min_length=1, max_length=4000)
    strong_comparisons: list[str] = Field(min_length=1, max_length=32)
    frozen_confirmation_evidence: dict[str, Any]
    reuse_conditions: list[str] = Field(min_length=1, max_length=32)
    failure_cases: list[str] = Field(min_length=1, max_length=32)
    retirement_triggers: list[str] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def complete_conditions(self) -> TransformationWitness:
        fields = [
            self.prerequisites,
            self.strong_comparisons,
            self.reuse_conditions,
            self.failure_cases,
            self.retirement_triggers,
        ]
        if any(not value or len(value) > 2000 for values in fields for value in values):
            raise ValueError("witness conditions require bounded nonempty text")
        if not self.outcome_bridge or not self.frozen_confirmation_evidence:
            raise ValueError("witness requires bridge and confirmation process status")
        return self


class TransformationPackage(TIModel):
    """An executable package, rather than a model's assertion of success."""

    record_schema: Literal["transformation-package/v1"] = Field(default="transformation-package/v1", alias="schema")
    formulation: Formulation
    construction: SelectionProgram
    realization: Literal["exact-source-clauses/v1"] = "exact-source-clauses/v1"
    witness: TransformationWitness
    axes: list[
        Literal["representation", "information", "dependency", "production", "task-boundary", "mechanism", "evaluation"]
    ] = Field(min_length=1, max_length=7)


class DiscoveryRequest(TIModel):
    """A changed purpose, input, provider or budget creates a new comparison."""

    campaign_id: str
    charter: IntentCharter
    development: list[SourceDocument] = Field(min_length=1, max_length=8)
    operator_ids: list[str] = Field(default_factory=lambda: ["representation", "production", "complementary"])
    max_candidates: int = Field(default=8, ge=1, le=32)
    configuration: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def identity(self) -> DiscoveryRequest:
        assert_public_content(self.model_dump())
        if (
            str(uuid.UUID(self.campaign_id)) != self.campaign_id
            or uuid.UUID(self.campaign_id).variant != uuid.RFC_4122
            or uuid.UUID(self.campaign_id).version not in range(1, 9)
        ):
            raise ValueError("campaign requires a canonical UUID")
        if len(set(self.operator_ids)) != len(self.operator_ids) or len(self.operator_ids) > 32:
            raise ValueError("operator identifiers must be unique and bounded")
        if len(self.configuration) > 20 or any(len(k) > 80 or len(v) > 500 for k, v in self.configuration.items()):
            raise ValueError("configuration exceeds bounded public context")
        return self


def source_instrument() -> dict[str, Any]:
    """Describe an uncalibrated structural instrument; do not infer reader benefit."""
    return {
        "schema": "evaluation-instrument/v1",
        "name": "declared-dependency-coverage/v1",
        "measurement": "weight of selected exact clauses whose prerequisite closure is present, in millionths",
        "domain": "supplied acyclic argument representations with at most twelve clauses",
        "calibration": {"status": "missing", "human_understanding_bound": None},
        "authoritative_claim": "structural coverage only; source truth and reader understanding unestablished",
        "hard_requirements": [
            "exact source clauses",
            "fixed clause count",
            "no omitted prerequisite for counted value",
        ],
    }


def validate_envelope(value: dict[str, Any]) -> dict[str, Any]:
    """Validate full commitments and inert authority without trusting imported claims."""
    canonical(value)
    assert_public_content(value)
    required = {
        "schema",
        "campaign_id",
        "revision",
        "charter",
        "charter_digest",
        "formulation",
        "formulation_digest",
        "evaluation",
        "transformation",
        "transformation_digest",
        "bindings",
        "bindings_digest",
        "phase",
        "authorization",
        "execution",
        "review",
        "settlement",
        "freeze",
        "result",
    }
    if set(value) not in (required, required | {"elapsed_ms"}) or value["schema"] != SCHEMA:
        raise ValueError("unsupported transformation envelope or fields")
    if (
        str(uuid.UUID(value["campaign_id"])) != value["campaign_id"]
        or type(value["revision"]) is not int
        or value["revision"] < 0
    ):
        raise ValueError("invalid campaign identity or revision")
    charter = IntentCharter.model_validate(value["charter"])
    formulation = Formulation.model_validate(value["formulation"])
    package = TransformationPackage.model_validate(value["transformation"])
    if any(
        canonical(model.model_dump()) != canonical(raw)
        for model, raw in (
            (charter, value["charter"]),
            (formulation, value["formulation"]),
            (package, value["transformation"]),
        )
    ):
        raise ValueError("native records require complete canonical fields and current versions")
    for key, domain in (
        ("charter", "ti-charter"),
        ("formulation", "ti-formulation"),
        ("transformation", "ti-transformation"),
        ("bindings", "ti-bindings"),
    ):
        if value[key + "_digest"] != digest(domain, value[key]):
            raise ValueError("transformation content commitment mismatch")
    evaluation = value["evaluation"]
    if (
        set(evaluation) != {"instrument", "instrument_digest", "epoch", "status"}
        or canonical(evaluation["instrument"]) != canonical(source_instrument())
        or evaluation["instrument_digest"] != digest("ti-instrument", evaluation["instrument"])
    ):
        raise ValueError("imported evaluator is unsupported or changed")
    if (
        type(evaluation["epoch"]) is not int
        or evaluation["epoch"] != 1
        or evaluation["status"] != "local_structural_only"
    ):
        raise ValueError("imported evaluation cannot claim independent qualification")
    binding = value["bindings"]
    if set(binding) != {"request", "operators", "instrument", "engine_sha256", "provider"}:
        raise ValueError("incomplete frozen behavior bindings")
    request = DiscoveryRequest.model_validate(binding["request"])
    if (
        canonical(request.model_dump()) != canonical(binding["request"])
        or canonical(request.charter) != canonical(charter)
        or request.campaign_id != value["campaign_id"]
    ):
        raise ValueError("frozen request changed the purpose, resource rules or campaign identity")
    if (
        canonical(binding["instrument"]) != canonical(evaluation["instrument"])
        or canonical(package.formulation) != canonical(formulation)
        or package.witness.purpose != charter.purpose
    ):
        raise ValueError("transformation bridge changed the original comparison basis")
    if canonical(binding["provider"]) != canonical(
        {"kind": "deterministic-installed-operators", "model": "none", "paid_calls": 0}
    ):
        raise ValueError("unsupported imported provider authority")
    hashes = [binding["engine_sha256"], *binding["operators"].values()]
    if set(binding["operators"]) != set(request.operator_ids) or any(
        type(item) is not str or len(item) != 64 or any(c not in "0123456789abcdef" for c in item) for item in hashes
    ):
        raise ValueError("operator or engine bindings are malformed")
    if (
        canonical(value["authorization"])
        != canonical({"scope": "local-bounded", "binding": None, "authority_expansion": False})
        or canonical(value["execution"]) != canonical({"status": "inert-export", "artifacts": []})
        or canonical(value["review"]) != canonical({"status": "pending", "independent": False})
    ):
        raise ValueError("imported history cannot grant execution or independent review authority")
    if canonical(value["settlement"]) != canonical(
        {"route": charter.payment_route, "status": "unfunded", "transaction_prepared": False}
    ):
        raise ValueError("settlement must preserve the explicit unfunded currency route")
    if value["phase"] not in {*PHASES, "paused", "canceled"}:
        raise ValueError("unsupported discovery phase")
    frozen = value["freeze"]
    if value["phase"] == "frozen" and frozen is None or value["phase"] == "completed" and value["result"] is None:
        raise ValueError("terminal or frozen phase is missing its required evidence")
    if frozen is not None and value["phase"] not in {"frozen", "completed", "paused", "canceled"}:
        raise ValueError("finalist evidence cannot precede discovery and freeze")
    if frozen is not None:
        if (
            set(frozen) != {"manifest", "digest", "journal_predecessor", "journal_revision"}
            or digest("ti-finalist-freeze", frozen["manifest"]) != frozen["digest"]
        ):
            raise ValueError("frozen finalist was altered")
        if (
            frozen["manifest"]["binding"] != value["bindings_digest"]
            or frozen["manifest"]["package"] != value["transformation"]
        ):
            raise ValueError("transformation does not match the frozen finalist")
        manifest = frozen["manifest"]
        expected = {"binding", "selected", "package", "comparators", "instrument", "confirmation", "claim"}
        if (
            set(manifest) != expected
            or manifest["comparators"] != DiscoveryLoop._comparators()
            or manifest["instrument"] != evaluation["instrument"]
        ):
            raise ValueError("frozen confirmation changed the required strong comparisons or instrument")
        if manifest["selected"]["program"] != package.construction.model_dump() or manifest["selected"][
            "program_digest"
        ] != digest("ti-program", package.construction):
            raise ValueError("frozen selection changed executable construction")
    if frozen is not None and (
        not isinstance(frozen["journal_predecessor"], str)
        or len(frozen["journal_predecessor"]) != 64
        or any(c not in "0123456789abcdef" for c in frozen["journal_predecessor"])
        or type(frozen["journal_revision"]) is not int
        or not 0 < frozen["journal_revision"] < value["revision"]
    ):
        raise ValueError("frozen journal process references are malformed")
    if value["result"] is not None and frozen is None:
        if value["phase"] != "completed" or value["result"] != {
            "decision": "retain-incumbent",
            "reason": "no feasible candidate within budget",
        }:
            raise ValueError("missing frozen evidence cannot support confirmation or improvement")
        return value
    if value["result"] is not None and (
        value["phase"] != "completed" or value["result"].get("freeze_digest") != frozen["digest"]
    ):
        raise ValueError("result does not bind frozen candidate evidence or terminal phase")
    if value["result"] is not None:
        result = value["result"]
        if (
            result.get("independent_review") != "pending"
            or result.get("certified_ceiling_escape") is not False
            or result.get("reader_understanding") != "uncalibrated"
        ):
            raise ValueError("unreviewed structural evidence cannot assert independent outcomes or ceiling escape")
        fresh = [SourceDocument.model_validate(document) for document in result["fresh_sources"]]
        if not 1 <= len(fresh) <= 8:
            raise ValueError("missing complete confirmation sources")
        if canonical([document.model_dump() for document in fresh]) != canonical(result["fresh_sources"]):
            raise ValueError("terminal source wire records require every explicit version and field")
        validate_fresh_sources(request.development, fresh)
        terminal_expected = _terminal_results(request, package.construction, fresh)
        for field in (
            "decision",
            "failure",
            "results",
            "means_millionths",
            "observed_gain_vs_incumbent",
            "beats_unrestricted",
        ):
            if field not in result or canonical(result[field]) != canonical(terminal_expected[field]):
                raise ValueError("recorded terminal comparison or structural score cannot be reproduced")
        if canonical(result["costs"]["execution_units"]) != canonical(terminal_expected["execution_units"]):
            raise ValueError("recorded terminal resource cost cannot be reproduced")
        costs = result["costs"]
        if (
            set(costs)
            != {
                "search_units",
                "execution_units",
                "paid_calls",
                "money_minor",
                "human_effort",
                "maintenance",
                "reuse_horizon",
            }
            or type(costs["search_units"]) is not int
            or not 0 <= costs["search_units"] <= charter.budgets.search_units
        ):
            raise ValueError("invalid declared discovery resource costs")
        fixed_costs = {
            "paid_calls": 0,
            "money_minor": 0,
            "human_effort": "not measured",
            "maintenance": "not measured",
            "reuse_horizon": "undeclared; economic break-even not established",
        }
        if canonical({key: costs[key] for key in fixed_costs}) != canonical(fixed_costs):
            raise ValueError("unsupported lifecycle cost or economic claims")
    return value


def _closure(document: SourceDocument, selected: set[str]) -> set[str]:
    claims = {claim.id: claim for claim in document.claims}
    result, todo = set(selected), list(selected)
    while todo:
        for dependency in claims[todo.pop()].depends_on:
            if dependency not in result:
                result.add(dependency)
                todo.append(dependency)
    return result


def source_fingerprint(document: SourceDocument) -> str:
    """Reject reused source content even when IDs, titles, weights or provenance change."""
    return digest("ti-source-content", sorted(claim.text for claim in document.claims))


def validate_fresh_sources(development: list[SourceDocument], fresh: list[SourceDocument]) -> None:
    """Reject exact known clause reuse; semantic independence still needs outside custody."""
    seen = {claim.text for document in development for claim in document.claims}
    for document in fresh:
        clauses = {claim.text for claim in document.claims}
        if seen & clauses:
            raise ValueError("confirmation reuses development or duplicate source clause content")
        seen.update(clauses)


def inspect_summary(document: SourceDocument, selected: list[str], max_clauses: int) -> dict[str, Any]:
    """Independently recompute structural outputs without trusting producer scores."""
    names = {claim.id for claim in document.claims}
    if len(selected) > max_clauses or len(set(selected)) != len(selected) or not set(selected) <= names:
        raise ValueError("summary violates source identity or fixed-artifact limit")
    chosen = set(selected)
    valid = [claim.id for claim in document.claims if claim.id in chosen and _closure(document, {claim.id}) <= chosen]
    covered = sum(claim.weight for claim in document.claims if claim.id in valid)
    total = sum(claim.weight for claim in document.claims)
    return {
        "score_millionths": covered * 1_000_000 // total,
        "covered_weight": covered,
        "total_weight": total,
        "supported_claims": valid,
        "unsupported_claims": sorted(chosen - set(valid)),
        "selected": selected,
        "text": "\n".join(claim.text for claim in document.claims if claim.id in chosen),
        "references": [
            {"id": claim.id, "provenance": claim.provenance} for claim in document.claims if claim.id in chosen
        ],
    }


def _select(
    document: SourceDocument, program: SelectionProgram, limit: int, charge: Callable[[int], None]
) -> list[str]:
    ordered = list(document.claims)
    charge(len(ordered))
    if program.production == "lead":
        return [claim.id for claim in ordered[:limit]]
    weighted = sorted(ordered, key=lambda claim: (-claim.weight, claim.id))
    if (
        program.production == "weighted"
        or program.production == "closure-search"
        and program.representation == "sequence"
    ):
        return [claim.id for claim in weighted[:limit]]
    if program.production == "audit-after":
        selected = {claim.id for claim in ordered[:limit]}
        for claim in sorted(ordered, key=lambda value: (value.weight, value.id)):
            charge(1)
            if len(_closure(document, selected)) <= limit:
                break
            selected.discard(claim.id)
        selected = _closure(document, selected)
        return [claim.id for claim in ordered if claim.id in selected]
    best: tuple[int, int, tuple[str, ...]] = (-1, 0, ())
    for size in range(min(limit, len(ordered)) + 1):
        for subset in itertools.combinations(ordered, size):
            charge(1)
            names = {claim.id for claim in subset}
            if _closure(document, names) <= names:
                candidate = (sum(claim.weight for claim in subset), -len(subset), tuple(claim.id for claim in subset))
                if candidate[:2] > best[:2] or candidate[:2] == best[:2] and candidate[2] < best[2]:
                    best = candidate
    return list(best[2])


def execute_selection(
    document: SourceDocument, program: SelectionProgram, charter: IntentCharter, charge: Callable[[int], None]
) -> dict[str, Any]:
    """Execute only this installed pure selector after checking required permissions."""
    if not {"read-public-source", "construct-bounded", "evaluate-local"} <= set(charter.permitted_actions):
        raise PermissionError("charter does not authorize bounded construction and local evaluation")
    selected = _select(document, program, charter.max_clauses, charge)
    result = inspect_summary(document, selected, charter.max_clauses)
    result["program_digest"] = digest("ti-program", program)
    result["source_digest"] = digest("ti-source", document)
    return result


class Operator(Protocol):
    """Only locally installed trusted operators construct executable programs."""

    identity: str
    source_digest: str

    def propose(self, request: DiscoveryRequest) -> list[SelectionProgram]:
        """Construct bounded proposals without receiving confirmation material."""


class StructuralOperator:
    """Expose single edits and complementary representation/production changes."""

    def __init__(self, identity: str) -> None:
        if identity not in {"representation", "production", "complementary"}:
            raise ValueError("unsupported built-in operator")
        self.identity = identity
        self.source_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def propose(self, request: DiscoveryRequest) -> list[SelectionProgram]:
        """Generate executable hypotheses; candidate generation does not score them."""
        representation: Literal["sequence", "argument-graph"] = (
            "argument-graph" if self.identity != "production" else "sequence"
        )
        production: Literal["lead", "closure-search"] = (
            "closure-search" if self.identity != "representation" else "lead"
        )
        return [SelectionProgram(representation=representation, production=production)]


class OperatorRegistry:
    """An extensible installed-code boundary, never a dynamic import or code evaluator."""

    def __init__(self) -> None:
        self.operators: dict[str, Operator] = {}
        for identity in ("representation", "production", "complementary"):
            self.register(StructuralOperator(identity))

    def register(self, operator: Operator) -> None:
        """Require a unique identity and explicit installed implementation commitment."""
        if not operator.identity or len(operator.identity) > 80 or operator.identity in self.operators:
            raise ValueError("operator identity is empty, duplicate or oversized")
        if len(operator.source_digest) != 64 or any(c not in "0123456789abcdef" for c in operator.source_digest):
            raise ValueError("operator requires its installed source SHA-256")
        self.operators[operator.identity] = operator

    def manifest(self, identities: list[str]) -> dict[str, str]:
        """Freeze exact enabled operators, rejecting silently missing adapters."""
        if any(identity not in self.operators for identity in identities):
            raise ValueError("requested operator is not explicitly installed")
        result = {}
        for identity in identities:
            operator = self.operators[identity]
            method = operator.propose
            function = getattr(method, "__func__", None)
            if function is None or not hasattr(function, "__code__"):
                raise ValueError("operator requires an inspectable installed Python implementation")
            state = dict(vars(operator))
            class_state = {
                key: value
                for parent in reversed(type(operator).__mro__[:-1])
                for key, value in vars(parent).items()
                if not key.startswith("__") and not callable(value)
            }
            try:
                canonical(state)
                canonical(class_state)
                closure = [cell.cell_contents for cell in function.__closure__ or ()]
                canonical(closure)
                defaults = list(function.__defaults__ or ())
                keyword_defaults = function.__kwdefaults__ or {}
                canonical(defaults)
                canonical(keyword_defaults)
                referenced_configuration = {}
                for name, item in inspect.getclosurevars(function).globals.items():
                    if item is SelectionProgram:
                        continue
                    if inspect.isclass(item) or inspect.isfunction(item):
                        raise ValueError("operator helper callables require a separately reviewed bounded driver")
                    canonical(item)
                    referenced_configuration[name] = item
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    "operator configuration and closure must be immutable JSON-bindable public data"
                ) from exc
            source_path = inspect.getsourcefile(function)
            source = (
                hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
                if source_path and Path(source_path).is_file()
                else None
            )
            result[identity] = digest(
                "ti-installed-operator",
                {
                    "declared_source": operator.source_digest,
                    "file_sha256": source,
                    "callable_sha256": digest("ti-callable", _code_description(function.__code__)),
                    "instance_configuration": state,
                    "class_configuration": class_state,
                    "closure": closure,
                    "defaults": defaults,
                    "keyword_defaults": keyword_defaults,
                    "referenced_configuration": referenced_configuration,
                },
            )
        return result


def _code_description(code: CodeType) -> dict[str, Any]:
    return {
        "bytecode": code.co_code.hex(),
        "constants": [_code_description(item) if isinstance(item, CodeType) else repr(item) for item in code.co_consts],
        "names": list(code.co_names),
        "arguments": list(code.co_varnames),
    }


def _assumptions(request: DiscoveryRequest) -> list[Assumption]:
    return [
        Assumption(
            name="purpose", kind="authorized-end", statement=request.charter.purpose, provenance="intent charter"
        ),
        Assumption(
            name="fixed-output",
            kind="hard-constraint",
            statement="Retain exact source clauses within the fixed limit.",
            provenance="intent charter artifact and max_clauses",
        ),
        Assumption(
            name="public-input",
            kind="environmental-fact",
            statement="Only the explicitly supplied public document is available.",
            provenance="supplied source document; provenance does not certify truth",
        ),
        Assumption(
            name="source-order",
            kind="inherited-design",
            statement="The first clauses are the best summary.",
            provenance="incumbent lead-order policy",
            removable=True,
        ),
        Assumption(
            name="dependency-benefit",
            kind="uncertain-hypothesis",
            statement="Preserving dependencies before selection helps structural coverage.",
            provenance="paper source-understanding protocol; reader benefit remains unmeasured",
            removable=True,
        ),
    ]


def _formulation(request: DiscoveryRequest, program: SelectionProgram) -> Formulation:
    return Formulation(
        representation=program.representation,
        assumptions=_assumptions(request),
        information_protocol="same supplied public source and argument annotations for every method",
        intermediate_objectives=["retain supported weighted clauses", "preserve required exact-clause output"],
    )


def _package(request: DiscoveryRequest, program: SelectionProgram) -> TransformationPackage:
    return TransformationPackage(
        formulation=_formulation(request, program),
        construction=program,
        axes=["representation", "production"] if program.representation == "argument-graph" else ["production"],
        witness=TransformationWitness(
            purpose=request.charter.purpose,
            inherited_restriction="Select or criticize a source-order draft without representing prerequisite closure before compression.",
            provenance="declared incumbent policy; not a proved ceiling",
            proposed_change="Represent dependencies explicitly and search supported clause subsets under the same output limit.",
            prerequisites=[
                "audited acyclic argument annotations",
                "at most twelve clauses",
                "local bounded construction permission",
            ],
            fallback="retain source-order incumbent or request clarification",
            outcome_bridge={
                "type": "computational-structural",
                "scope": "exact source clauses and supplied dependencies only",
                "preserves": ["source identity", "fixed clause limit", "permissions", "currency budgets"],
                "human_understanding": "not calibrated",
            },
            falsifier="Equal-or-better unchanged-frame control, invalid source dependencies, or setup cost exceeding declared reuse benefit.",
            strong_comparisons=[
                "lead-order",
                "audit-after-draft",
                "weighted-without-dependencies",
                "unrestricted-exact-search",
            ],
            frozen_confirmation_evidence={"status": "not supplied"},
            reuse_conditions=[
                "same structural instrument",
                "fresh complete source documents",
                "revalidate annotations and full costs",
            ],
            failure_cases=[
                "unreliable graph annotations",
                "strict short output",
                "irreducible dependencies",
                "unknown reader preferences",
            ],
            retirement_triggers=[
                "code/model/configuration/evaluator change",
                "unsupported sources",
                "failed independent review",
            ],
        ),
    )


def _engine_digest(source_root: Path | None = None) -> str:
    root = Path(__file__).parent if source_root is None else source_root
    if root.is_symlink() or root.parent.is_symlink():
        raise ValueError("native execution source directories must not be symlinks")
    paths = [root / name for name in ("transformation.py", "protocol.py", "trust.py", "signatures.py")]
    paths += [root.parent / name for name in ("store.py", "models.py")]
    manifest = {}
    for path in paths:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > 512_000:
            raise ValueError("native execution source must be a bounded regular readable file")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise ValueError("native execution source changed during binding")
            content = stream.read(512_001)
        if len(content) > 512_000:
            raise ValueError("native execution source exceeds its byte budget")
        manifest[path.relative_to(root.parent).as_posix()] = hashlib.sha256(content).hexdigest()
    return digest("ti-installed-engine", {"sources": manifest, "python": sys.version, "pydantic": pydantic.__version__})


class DiscoveryLoop:
    """Resume pure bounded work through the existing signed transactional Journal."""

    def __init__(self, journal: Journal, registry: OperatorRegistry | None = None) -> None:
        journal.verify()
        self.journal, self.registry = journal, registry or OperatorRegistry()

    def _running(self, cx: Any) -> None:
        if self.journal.latest("@control", cx)["state"] != "ready":
            raise Conflict("operator STOP is active; no discovery construction or confirmation may run")

    def _key(self, campaign_id: str) -> str:
        return KEY + str(uuid.UUID(campaign_id))

    def bindings(self, request: DiscoveryRequest) -> dict[str, Any]:
        """Bind code, charter, inputs, evaluator, operators and configuration before approval."""
        return {
            "request": request.model_dump(),
            "operators": self.registry.manifest(request.operator_ids),
            "instrument": source_instrument(),
            "engine_sha256": _engine_digest(),
            "provider": {"kind": "deterministic-installed-operators", "model": "none", "paid_calls": 0},
        }

    def create(self, request: DiscoveryRequest) -> dict[str, Any]:
        """Persist a comparison idempotently; changed input cannot reuse its identity."""
        key, binding = self._key(request.campaign_id), self.bindings(request)
        with self.journal.transaction() as cx:
            try:
                existing = self.journal.latest(key, cx)
            except KeyError:
                return self.journal.append(
                    cx,
                    key,
                    {
                        "schema": SCHEMA,
                        "state": "queued",
                        "resume_state": None,
                        "request": request.model_dump(),
                        "binding": binding,
                        "binding_digest": digest("ti-bindings", binding),
                        "approval": None,
                        "attempts": [],
                        "spent": {"search_units": 0, "execution_units": 0},
                        "result": None,
                        "freeze": None,
                        "history": [],
                        "successors": [],
                        "active_successor": None,
                        "operations": {},
                    },
                )
            if existing["binding_digest"] != digest("ti-bindings", binding):
                raise Conflict("campaign identity already belongs to another purpose, code or comparison basis")
            return existing

    def show(self, campaign_id: str) -> dict[str, Any]:
        """Read retained evidence without executing or granting authority."""
        return self.journal.latest(self._key(campaign_id))

    def approve(self, campaign_id: str, binding_digest: str) -> dict[str, Any]:
        """Explicitly authorize exact free local computation; no external capability is granted."""
        return self._update(campaign_id, "approve", binding_digest=binding_digest)

    def control(self, campaign_id: str, action: Literal["pause", "resume", "cancel"]) -> dict[str, Any]:
        """Keep interruption/cancellation evidence and never resume canceled work."""
        return self._update(campaign_id, action)

    def _update(self, campaign_id: str, action: str, **arguments: Any) -> dict[str, Any]:
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            if action == "approve":
                self._running(cx)
                if data["state"] in {"completed", "canceled"}:
                    raise Conflict("finished campaigns cannot receive execution approval")
                self._current(data)
                if arguments["binding_digest"] != data["binding_digest"]:
                    raise Conflict("approval is stale or belongs to another comparison")
                data["approval"] = {"binding": data["binding_digest"], "scope": "local-bounded", "paid_use": False}
            elif action == "pause":
                if data["state"] not in PHASES[:-1]:
                    raise Conflict("only active discovery can be paused")
                data["resume_state"], data["state"] = data["state"], "paused"
            elif action == "resume":
                self._running(cx)
                if data["state"] != "paused":
                    raise Conflict("only a paused campaign can resume")
                self._current(data)
                data["state"], data["resume_state"] = data["resume_state"], None
            elif action == "cancel":
                if data["state"] == "completed":
                    raise Conflict("completed evidence is historical and cannot be canceled")
                if data["state"] == "canceled":
                    return record
                data["state"], data["approval"] = "canceled", None
            else:
                raise ValueError("unknown campaign control")
            data["history"].append({"action": action, "from_revision": record["revision"]})
            return self.journal.append(cx, self._key(campaign_id), data)

    def _current(self, data: dict[str, Any]) -> DiscoveryRequest:
        request = DiscoveryRequest.model_validate(data["request"])
        if digest("ti-bindings", self.bindings(request)) != data["binding_digest"]:
            raise Conflict(
                "code, configuration, inputs, operators or evaluator changed; fresh approval/comparison required"
            )
        return request

    def step(self, campaign_id: str, *, operation_id: str) -> dict[str, Any]:
        """Run one atomic pure phase; a process crash rolls back incomplete state and costs."""
        with self.journal.transaction() as cx:
            self._running(cx)
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            if not operation_id or len(operation_id) > 96:
                raise ValueError("phase requires a bounded operation identity")
            if operation_id in data["operations"] or data["state"] == "completed":
                return record
            if data["state"] not in PHASES[:-1]:
                raise Conflict("campaign is paused or canceled")
            request = self._current(data)
            if data["approval"] is None or data["approval"]["binding"] != data["binding_digest"]:
                raise PermissionError("review and approve the exact local comparison before construction")
            previous = data["state"]
            if previous == "queued":
                data["diagnosis"] = {
                    "assumptions": [item.model_dump() for item in _assumptions(request)],
                    "obstruction": "Source-order selection can omit required prerequisites under compression.",
                    "evidence": "Supplied dependency graph; repeated failure alone is not a ceiling certificate.",
                    "alternatives": [
                        "unchanged-frame",
                        "clarify annotations",
                        "stop",
                        "representation-plus-production",
                    ],
                    "ceiling_certified": False,
                }
                data["state"] = "diagnosed"
            elif previous == "diagnosed":
                self._develop(request, data)
                data["state"] = "developed"
            elif previous == "developed":
                eligible = [attempt for attempt in data["attempts"] if attempt["status"] == "valid"]
                if not eligible:
                    data["result"] = {"decision": "retain-incumbent", "reason": "no feasible candidate within budget"}
                    data["state"] = "completed"
                else:
                    selected = sorted(
                        eligible, key=lambda item: (-item["score"], item["units"], item["program_digest"])
                    )[0]
                    incumbent = next((item for item in eligible if item["label"] == "incumbent"), None)
                    if incumbent and selected["score"] <= incumbent["score"]:
                        selected = incumbent
                    package = _package(request, SelectionProgram.model_validate(selected["program"]))
                    package.witness.frozen_confirmation_evidence.update(
                        {
                            "status": "design-frozen",
                            "binding": data["binding_digest"],
                            "sampling_unit": "complete source document",
                            "freshness_custody": "independent evidence required",
                        }
                    )
                    manifest = {
                        "binding": data["binding_digest"],
                        "selected": selected,
                        "package": package.model_dump(),
                        "comparators": self._comparators(),
                        "instrument": source_instrument(),
                        "confirmation": "fresh complete documents supplied after this recorded freeze; one-shot",
                        "claim": "structural coverage only; independent outcome review pending",
                    }
                    data["freeze"] = {
                        "manifest": manifest,
                        "digest": digest("ti-finalist-freeze", manifest),
                        "journal_predecessor": record["digest"],
                        "journal_revision": record["revision"],
                    }
                    data["state"] = "frozen"
            else:
                raise Conflict("supply fresh confirmation documents after freezing the finalist")
            data["operations"][operation_id] = {"from": previous, "to": data["state"]}
            data["history"].append(
                {"action": "step", "from": previous, "to": data["state"], "from_revision": record["revision"]}
            )
            return self.journal.append(cx, self._key(campaign_id), data)

    @staticmethod
    def _comparators() -> dict[str, dict[str, Any]]:
        return {
            name: program.model_dump()
            for name, program in {
                "lead-order": SelectionProgram(),
                "audit-after-draft": SelectionProgram(production="audit-after"),
                "weighted-without-dependencies": SelectionProgram(production="weighted"),
                "unrestricted-exact-search": SelectionProgram(
                    representation="argument-graph", production="closure-search"
                ),
            }.items()
        }

    def _develop(self, request: DiscoveryRequest, data: dict[str, Any]) -> None:
        if not {"read-public-source", "construct-bounded", "evaluate-local"} <= set(request.charter.permitted_actions):
            raise PermissionError("check construction and evaluation permissions before invoking any proposal operator")
        programs: list[tuple[str, SelectionProgram]] = [
            ("incumbent", SelectionProgram()),
            ("audit-after-draft", SelectionProgram(production="audit-after")),
        ]
        for identity in request.operator_ids:
            supplied = DiscoveryRequest.model_validate(request.model_dump())
            programs.extend((identity, program) for program in self.registry.operators[identity].propose(supplied))
        seen: set[str] = set()
        for label, program in programs[: request.max_candidates]:
            program = SelectionProgram.model_validate(program)
            program_digest = digest("ti-program", program)
            if program_digest in seen:
                continue
            seen.add(program_digest)
            start = data["spent"]["search_units"]
            attempt: dict[str, Any] = {
                "label": label,
                "program": program.model_dump(),
                "program_digest": program_digest,
                "status": "valid",
                "observations": [],
                "score": 0,
                "units": 0,
            }

            def charge(units: int) -> None:
                if data["spent"]["search_units"] + units > request.charter.budgets.search_units:
                    raise Conflict("declared discovery search budget exhausted")
                data["spent"]["search_units"] += units

            try:
                for document in request.development:
                    attempt["observations"].append(execute_selection(document, program, request.charter, charge))
                attempt["score"] = sum(item["score_millionths"] for item in attempt["observations"]) // len(
                    request.development
                )
            except Conflict:
                attempt["status"], attempt["reason"] = "inconclusive", "budget-exhausted"
            except (ValueError, PermissionError):
                attempt["status"], attempt["reason"] = "rejected", "invalid program or unauthorized construction"
            attempt["units"] = data["spent"]["search_units"] - start
            data["attempts"].append(attempt)

    def confirm(self, campaign_id: str, fresh: list[SourceDocument], freeze_digest: str) -> dict[str, Any]:
        """Execute a frozen terminal comparison once; freshness custody is an explicit limitation."""
        if not 1 <= len(fresh) <= 8:
            raise ValueError("terminal evaluation requires one to eight complete fresh documents")
        with self.journal.transaction() as cx:
            self._running(cx)
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            if data["state"] == "completed":
                if data.get("confirmation_input_digest") == digest("ti-confirmation-input", fresh):
                    return record
                raise Conflict("completed confirmation cannot be replaced or repeatedly inspected")
            if data["state"] != "frozen":
                raise Conflict("freeze finalists before supplying terminal evidence")
            request = self._current(data)
            frozen = data["freeze"]
            if frozen["digest"] != freeze_digest or digest("ti-finalist-freeze", frozen["manifest"]) != freeze_digest:
                raise Conflict("finalist, comparison or confirmation commitment mismatch")
            validate_fresh_sources(request.development, fresh)
            selected = SelectionProgram.model_validate(frozen["manifest"]["selected"]["program"])
            terminal = _terminal_results(request, selected, fresh)
            data["spent"]["execution_units"] = terminal["execution_units"]
            data["confirmation_input_digest"] = digest("ti-confirmation-input", fresh)
            data["result"] = {
                **{key: val for key, val in terminal.items() if key != "execution_units"},
                "fresh_sources": [document.model_dump() for document in fresh],
                "mechanism": "declared representation/production ablations retained in development; inspect supplied dependencies",
                "certified_ceiling_escape": False,
                "independent_review": "pending",
                "reader_understanding": "uncalibrated",
                "freeze_digest": freeze_digest,
                "process_evidence": {
                    "freeze_journal_predecessor": frozen["journal_predecessor"],
                    "freeze_journal_revision": frozen["journal_revision"],
                    "freshness": "exact known clause reuse rejected; semantic independence, custody and untouchedness require independent evidence",
                    "independence": "local computational checker; no organizational independence claimed",
                },
                "costs": {
                    **data["spent"],
                    "paid_calls": 0,
                    "money_minor": 0,
                    "human_effort": "not measured",
                    "maintenance": "not measured",
                    "reuse_horizon": "undeclared; economic break-even not established",
                },
            }
            data["state"] = "completed"
            data["approval"] = None
            data["history"].append({"action": "confirm", "from_revision": record["revision"]})
            return self.journal.append(cx, self._key(campaign_id), data)

    def envelope(self, campaign_id: str) -> dict[str, Any]:
        """Emit an inert full-object integration record; no balance or execution permission travels."""
        record = self.show(campaign_id)
        request = DiscoveryRequest.model_validate(record["request"])
        program = (
            SelectionProgram()
            if record["freeze"] is None
            else SelectionProgram.model_validate(record["freeze"]["manifest"]["selected"]["program"])
        )
        formulation = _formulation(request, program)
        package = (
            _package(request, program)
            if record["freeze"] is None
            else TransformationPackage.model_validate(record["freeze"]["manifest"]["package"])
        )
        instrument = source_instrument()
        payload = {
            "schema": SCHEMA,
            "campaign_id": campaign_id,
            "revision": record["revision"],
            "charter": request.charter.model_dump(),
            "charter_digest": digest("ti-charter", request.charter),
            "formulation": formulation.model_dump(),
            "formulation_digest": digest("ti-formulation", formulation),
            "evaluation": {
                "instrument": instrument,
                "instrument_digest": digest("ti-instrument", instrument),
                "epoch": 1,
                "status": "local_structural_only",
            },
            "transformation": package.model_dump(),
            "transformation_digest": digest("ti-transformation", package),
            "bindings": record["binding"],
            "bindings_digest": record["binding_digest"],
            "phase": record["state"],
            "authorization": {"scope": "local-bounded", "binding": None, "authority_expansion": False},
            "execution": {"status": "inert-export", "artifacts": []},
            "review": {"status": "pending", "independent": False},
            "settlement": {"route": request.charter.payment_route, "status": "unfunded", "transaction_prepared": False},
            "freeze": record["freeze"],
            "result": record["result"],
        }
        return payload

    def import_history(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Retain validated history only; imported approval, spending and activation stay empty."""
        value = validate_envelope(envelope)
        commitment = digest("ti-import", value)
        key = "@transformation-import:" + commitment
        with self.journal.transaction() as cx:
            try:
                return self.journal.latest(key, cx)
            except KeyError:
                return self.journal.append(
                    cx,
                    key,
                    {
                        "schema": "ti-imported-history/v1",
                        "envelope": value,
                        "commitment": commitment,
                        "active_permission": None,
                        "active_successor": None,
                        "status": "historical-only",
                        "reapproval_required": True,
                    },
                )


def _terminal_results(
    request: DiscoveryRequest, selected: SelectionProgram, fresh: list[SourceDocument]
) -> dict[str, Any]:
    results: dict[str, list[dict[str, Any]]] = {name: [] for name in ["candidate", *DiscoveryLoop._comparators()]}
    spent = 0

    def charge(units: int) -> None:
        nonlocal spent
        if spent + units > request.charter.budgets.execution_units:
            raise Conflict("declared terminal execution budget exhausted")
        spent += units

    failure = None
    try:
        for document in fresh:
            results["candidate"].append(execute_selection(document, selected, request.charter, charge))
            for name, program in DiscoveryLoop._comparators().items():
                results[name].append(
                    execute_selection(document, SelectionProgram.model_validate(program), request.charter, charge)
                )
    except Conflict:
        failure = "terminal budget exhausted; incomplete evidence cannot support promotion"
    means = {
        name: None if len(items) != len(fresh) else sum(item["score_millionths"] for item in items) // len(fresh)
        for name, items in results.items()
    }
    candidate_mean, incumbent_mean, unrestricted_mean = (
        means["candidate"],
        means["lead-order"],
        means["unrestricted-exact-search"],
    )
    gain = None if candidate_mean is None or incumbent_mean is None else candidate_mean - incumbent_mean
    return {
        "decision": (
            "retain-incumbent" if failure or gain is None or gain <= 0 else "propose-reuse-pending-independent-review"
        ),
        "failure": failure,
        "results": results,
        "means_millionths": means,
        "observed_gain_vs_incumbent": gain,
        "beats_unrestricted": (
            None if candidate_mean is None or unrestricted_mean is None else candidate_mean > unrestricted_mean
        ),
        "execution_units": spent,
    }


def pilot_document(*, confirmation: bool = False) -> SourceDocument:
    """Use actual public paper clauses; fresh document concerns a separate section."""
    if confirmation:
        title, section = "Paper confirmation: reusable methods", "Continuous discovery"
        clauses = [
            ("first", 'The durable memory should not say only "this worked."', 2, []),
            (
                "conditions",
                "It should retain the restriction encountered, the transformation attempted, the evidence supporting its mechanism, its prerequisites, its construction costs, its failure conditions, and the scope of its outcome claim.",
                9,
                ["cost"],
            ),
            ("cost", "The same idea can succeed at a long reuse horizon and fail at a short one.", 7, []),
            (
                "router",
                "independently successful components do not guarantee that the router selects or composes them correctly.",
                8,
                ["test"],
            ),
            ("test", "A router that chooses among archived transformations is itself a policy", 5, []),
        ]
    else:
        title, section = "Paper development: the fixed summary charter", "Appendix C: Two legitimate charters"
        clauses = [
            (
                "first",
                "The motivating book example is useful because it forces the framework to distinguish a genuinely new route from a silent change in the assignment.",
                2,
                [],
            ),
            ("summary", "The system may change how it reads, represents, drafts, and checks.", 9, ["fixed"]),
            (
                "fixed",
                "In a fixed-artifact charter, the user needs a faithful summary of a particular edition, for a specified audience and purpose, within a strict length and format.",
                7,
                [],
            ),
            (
                "interface",
                "A source-grounded question interface, an adaptive explanation, or a small set of discriminating questions may be permissible alternatives.",
                8,
                ["permission"],
            ),
            (
                "permission",
                "The freedom must be real and declared; the system cannot infer consent merely because another product sounds more sophisticated.",
                5,
                [],
            ),
        ]
    return SourceDocument(
        title=title,
        source_url="https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/Transformational_Intelligence.tex",
        claims=[
            SourceClaim(
                id=name,
                text=text,
                weight=weight,
                depends_on=dependencies,
                provenance=section
                + "; verbatim prose after TeX emphasis/quote normalization; source SHA256 "
                + "9d4a664d951d6b97f5136bf0b44f1ca458e90d585434a6a27a542694bb2ece5f; lines "
                + ("480-482" if confirmation else "782-787")
                + "; weights/dependencies are local judgments",
            )
            for name, text, weight, dependencies in clauses
        ],
    )


def pilot_request(campaign_id: str | None = None) -> DiscoveryRequest:
    """A free bounded practical artifact; annotations are not independently adjudicated."""
    return DiscoveryRequest(
        campaign_id=campaign_id or str(uuid.uuid4()),
        charter=IntentCharter(
            purpose="Produce a concise source-grounded fixed summary of the paper's authorized-method requirements.",
            population="public-source argument clauses; no claim about reader comprehension",
            outcomes=["three or fewer exact supplied source clauses", "make prerequisite qualifications inspectable"],
            constraints=[
                "public non-personal input only",
                "no paid provider or external execution",
                "preserve the fixed summary artifact",
            ],
            permitted_actions=["read-public-source", "construct-bounded", "evaluate-local", "write-artifact"],
        ),
        development=[pilot_document()],
    )


def add_commands(commands: Any) -> None:
    """Add a discoverable free native path without changing existing commands."""
    parser = commands.add_parser(
        "successor-transform", help="Discover a bounded source-understanding formulation with retained evidence"
    )
    actions = parser.add_subparsers(dest="transformation_action", required=True)
    demo = actions.add_parser("demo", help="Run the explicit free local paper-clause pilot; no model or wallet")
    demo.add_argument("--output", type=Path, required=True)
    create = actions.add_parser("create", help="Retain a public DiscoveryRequest without construction")
    create.add_argument("file", type=Path)
    import_action = actions.add_parser("import", help="Retain imported history with no active execution or approval")
    import_action.add_argument("file", type=Path)
    for name in ("show", "step", "pause", "resume", "cancel", "export"):
        action = actions.add_parser(name)
        action.add_argument("campaign_id")
        if name == "step":
            action.add_argument("--operation-id", required=True)
        if name == "export":
            action.add_argument("--output", type=Path, required=True)
    approve = actions.add_parser("approve", help="Approve exact bounded local work after cost review")
    approve.add_argument("campaign_id")
    approve.add_argument("--binding", required=True)
    confirm = actions.add_parser("confirm", help="Run one frozen comparison on fresh complete SourceDocuments")
    confirm.add_argument("campaign_id")
    confirm.add_argument("file", type=Path)
    confirm.add_argument("--freeze", required=True)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Keep imported data inert and write outputs exclusively without replacing files."""
    from .transport import read_document

    if args.transformation_action == "demo":
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError("choose a new evidence output")
        journal = Journal(args.home) if (args.home / "journal.sqlite3").exists() else Journal.initialize(args.home)
        journal.verify()
        loop, request = DiscoveryLoop(journal), pilot_request()
        record = loop.create(request)
        loop.approve(request.campaign_id, record["binding_digest"])
        started = time.monotonic_ns()
        for _ in range(3):
            record = loop.step(request.campaign_id, operation_id="demo-phase-" + str(_))
        record = loop.confirm(request.campaign_id, [pilot_document(confirmation=True)], record["freeze"]["digest"])
        envelope = loop.envelope(request.campaign_id)
        envelope["elapsed_ms"] = (time.monotonic_ns() - started) // 1_000_000
        private_write(args.output, canonical(envelope))
        return {
            "output": str(args.output.resolve()),
            "campaign_id": request.campaign_id,
            "decision": record["result"]["decision"],
            "scope": "local structural pilot; independent review pending",
        }
    journal = Journal(args.home)
    journal.verify()
    loop = DiscoveryLoop(journal)
    action = args.transformation_action
    if action == "create":
        return loop.create(DiscoveryRequest.model_validate(read_document(args.file)))
    if action == "import":
        return loop.import_history(read_document(args.file))
    if action == "approve":
        return loop.approve(args.campaign_id, args.binding)
    if action in {"pause", "resume", "cancel"}:
        return loop.control(args.campaign_id, action)
    if action == "step":
        return loop.step(args.campaign_id, operation_id=args.operation_id)
    if action == "show":
        return loop.show(args.campaign_id)
    if action == "export":
        private_write(args.output, canonical(loop.envelope(args.campaign_id)))
        return {"output": str(args.output.resolve()), "authority_exported": False}
    if action == "confirm":
        documents = read_document(args.file)
        if set(documents) != {"documents"} or not isinstance(documents["documents"], list):
            raise ValueError("confirmation file requires only a documents array")
        return loop.confirm(
            args.campaign_id, [SourceDocument.model_validate(item) for item in documents["documents"]], args.freeze
        )
    raise ValueError("unknown transformation command")
