# SPDX-License-Identifier: Apache-2.0
"""Finite affine-recurrence reframing with exact checks and durable local evidence.

This separately installed driver is not the native source-selector language.  It
uses a closed algorithm family, shared witness types and the signed Journal.  It
performs no model, network, wallet or subprocess action.  An operation count is a
specified logical cost, not a timing, energy, monetary or intelligence measure.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import platform
import os
import stat
import time
import uuid
from pathlib import Path
from typing import Any, Literal

import pydantic
from pydantic import Field, model_validator

from ..store import Conflict, Journal, private_write
from .protocol import StrictModel, canonical, digest
from .transformation import Assumption, DiscoveryBudget, TransformationWitness, _engine_digest


def _is_exact_type(value: object, expected: type[object]) -> bool:
    """Compare exact types without admitting bool or other subclasses."""
    return type(value) is expected


SCHEMA = "ti-affine-recurrence/v1"
KEY = "@ti-affine:"
PROGRAMS = ("direct", "cycle", "affine-compose", "representation-only")
COST_RULE = {
    "schema": "affine-logical-cost/v1",
    "scalar_add_multiply_modulo": 1,
    "direct_loop_bookkeeping": 1,
    "cycle_lookup_insert_and_loop_bookkeeping": 3,
    "cycle_index_recovery": 6,
    "binary_bit_test_shift_and_loop_bookkeeping": 3,
    "pair_loop_bookkeeping": 1,
    "scope": "bounded scalar and dictionary operations; not CPU instructions or monetary cost",
    "excluded": ["input parsing", "Python allocation", "journal signing and I/O", "human review", "energy"],
}


class AffineCase(StrictModel):
    """A complete public task; unsupported nonlinear recurrences have no encoding."""

    modulus: int = Field(ge=2, le=257)
    multiplier: int = Field(ge=0, le=256)
    increment: int = Field(ge=0, le=256)
    initial: int = Field(ge=0, le=256)
    steps: int = Field(ge=0, le=4096)

    @model_validator(mode="after")
    def residues(self) -> AffineCase:
        if max(self.multiplier, self.increment, self.initial) >= self.modulus:
            raise ValueError("coefficients and initial state require canonical residues")
        return self


class MathCharter(StrictModel):
    """The exact mathematical goal and free local authority never become candidates."""

    purpose: Literal[
        "Compute x_n exactly for x_(t+1)=(a*x_t+b) modulo m"
    ] = "Compute x_n exactly for x_(t+1)=(a*x_t+b) modulo m"
    outcome: Literal["exact-final-state"] = "exact-final-state"
    permitted_actions: list[Literal["construct-bounded", "evaluate-local", "write-artifact"]]
    publicOnly: Literal[True] = True
    budgets: DiscoveryBudget = Field(default_factory=DiscoveryBudget)
    settlement: Literal["none"] = "none"

    @model_validator(mode="before")
    @classmethod
    def exact_public(cls, value: Any) -> Any:
        if isinstance(value, dict) and "publicOnly" in value and not _is_exact_type(value["publicOnly"], bool):
            raise ValueError("publicOnly requires an exact boolean")
        return value

    @model_validator(mode="after")
    def actions(self) -> MathCharter:
        if len(set(self.permitted_actions)) != len(self.permitted_actions):
            raise ValueError("actions must be unique")
        return self


class MathRequest(StrictModel):
    """Freeze complete confirmation inputs by commitment without evaluating them."""

    campaign_id: str
    charter: MathCharter
    development: list[AffineCase] = Field(min_length=1, max_length=32)
    confirmation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmation_count: int = Field(ge=1, le=2048)

    @model_validator(mode="after")
    def complete_identity(self) -> MathRequest:
        parsed = uuid.UUID(self.campaign_id)
        if str(parsed) != self.campaign_id or parsed.variant != uuid.RFC_4122 or parsed.version not in range(1, 9):
            raise ValueError("campaign requires a canonical UUID")
        if len({digest("affine-case", case) for case in self.development}) != len(self.development):
            raise ValueError("development cases must be distinct complete tasks")
        return self


class MathProgram(StrictModel):
    """Only installed scalar iteration, cycle detection or affine composition."""

    algorithm: Literal["direct", "cycle", "affine-compose", "representation-only"]


class MathPackage(StrictModel):
    """Executable construction and its mathematical bridge remain explicit."""

    schema_name: Literal["affine-transformation-package/v1"] = "affine-transformation-package/v1"
    program: MathProgram
    representation: Literal["scalar-state", "affine-function-pair"]
    witness: TransformationWitness
    assumptions: list[Assumption]
    proof_status: Literal["argument-present-not-machine-checked"] = "argument-present-not-machine-checked"
    authority: Literal["none"] = "none"


class BudgetExhausted(ValueError):
    """Stop before an operation that exceeds its remaining logical allowance."""


class Meter:
    """Count actual specified operations, including failed and comparator work."""

    def __init__(self, limit: int) -> None:
        if not _is_exact_type(limit, int) or not 0 <= limit <= 1_000_000:
            raise ValueError("logical allowance must be an exact bounded integer")
        self.limit, self.used = limit, 0

    def charge(self, units: int) -> None:
        if not _is_exact_type(units, int) or units < 0:
            raise ValueError("invalid charge")
        if self.used + units > self.limit:
            raise BudgetExhausted("logical budget exhausted; partial work cannot establish a comparison")
        self.used += units


def _compose(outer: tuple[int, int], inner: tuple[int, int], modulus: int, meter: Meter) -> tuple[int, int]:
    meter.charge(5)  # two multiplies, one addition, two reductions
    return outer[0] * inner[0] % modulus, (outer[0] * inner[1] + outer[1]) % modulus


def execute(case: AffineCase, program: MathProgram, meter: Meter) -> dict[str, int]:
    """Run a pure closed-language calculation; callers own local resource consent."""
    case = AffineCase.model_validate(copy.deepcopy(case.model_dump()))
    program = MathProgram.model_validate(program.model_dump())
    before = meter.used
    value, steps, modulus = case.initial, case.steps, case.modulus
    if program.algorithm == "direct":
        for _ in range(steps):
            meter.charge(4)
            value = (case.multiplier * value + case.increment) % modulus
    elif program.algorithm == "cycle":
        seen: dict[int, int] = {}
        history: list[int] = []
        index = 0
        while index < steps:
            meter.charge(1)
            if value in seen:
                meter.charge(6)
                start = seen[value]
                value = history[start + (steps - start) % (index - start)]
                break
            meter.charge(5)  # insertion, scalar transition and index update
            seen[value] = index
            history.append(value)
            value = (case.multiplier * value + case.increment) % modulus
            index += 1
    else:
        result, base = (1, 0), (case.multiplier, case.increment)
        if program.algorithm == "representation-only":
            for _ in range(steps):
                meter.charge(1)
                result = _compose(base, result, modulus, meter)
        else:
            exponent = steps
            while exponent:
                meter.charge(3)
                if exponent & 1:
                    result = _compose(base, result, modulus, meter)
                exponent >>= 1
                if exponent:
                    base = _compose(base, base, modulus, meter)
        if steps:
            meter.charge(3)
            value = (result[0] * case.initial + result[1]) % modulus
    return {"value": value, "units": meter.used - before}


def instrument() -> dict[str, Any]:
    """An exact reference check on complete finite tasks; no statistical calibration."""
    return {
        "schema": "affine-evaluation/v1",
        "epoch": 1,
        "correctness": "integer equality against direct recurrence, on every complete supplied case",
        "selection": "all development outputs exact, then lowest total execution units; ties retain direct",
        "confirmation": (
            "one committed complete finite census; no IID, blinded-custod" "y or population-generalization claim"
        ),
        "cost": COST_RULE,
        "search_cost": {
            "program_case_evaluation": 1,
            "development_selection_per_program": 1,
            "unrestricted_oracle_comparison_per_program_case": 1,
        },
    }


def bindings(request: MathRequest) -> dict[str, Any]:
    """Bind installed behavior and dependencies, not a caller-declared source label."""
    source = Path(__file__)
    before = source.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > 512_000:
        raise ValueError("mathematical driver source must be a bounded regular file")
    descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino) or not stat.S_ISREG(opened.st_mode):
            raise ValueError("mathematical driver source changed during binding")
        content = stream.read(512_001)
    if len(content) > 512_000:
        raise ValueError("mathematical driver source exceeds its byte budget")
    return {
        "request": request.model_dump(),
        "driver_sha256": hashlib.sha256(content).hexdigest(),
        "shared_engine_digest": _engine_digest(),
        "programs": list(PROGRAMS),
        "instrument": instrument(),
        "python": platform.python_version(),
        "pydantic": pydantic.__version__,
        "provider": {"kind": "none", "requests": 0},
    }


def _package(program: MathProgram, commitment: str) -> MathPackage:
    package = MathPackage(
        program=program,
        representation=(
            "affine-function-pair" if program.algorithm in {"affine-compose", "representation-only"} else "scalar-state"
        ),
        assumptions=[
            Assumption(
                name="exact-end",
                kind="authorized-end",
                statement="Return the same x_n, not an approximation.",
                provenance="fixed mathematical charter",
            ),
            Assumption(
                name="affine-domain",
                kind="hard-constraint",
                statement="One fixed affine map over Z/mZ; 2<=m<=257 and 0<=n<=4096.",
                provenance="closed AffineCase schema",
            ),
            Assumption(
                name="step-by-step",
                kind="inherited-design",
                statement="The state must be advanced one tick at a time.",
                provenance="direct recurrence incumbent",
                removable=True,
            ),
        ],
        witness=TransformationWitness(
            purpose="Compute exactly the charter's final recurrence state within fixed free local allowances.",
            inherited_restriction=(
                "The direct representation retains only the current scalar an" "d repeats every transition."
            ),
            provenance=(
                "Explicit incumbent implementation; repetition is an inherite"
                "d algorithm, not a mathematical requirement."
            ),
            proposed_change=(
                "Represent a transition as (p,q) for x -> p*x+q mod m; constr"
                "uct powers by closed composition and binary decomposition."
            ),
            prerequisites=[
                "Fixed integer affine recurrence; canonical residues",
                "Installed source and instrument unchanged",
                "Explicit exact local approval before construction",
            ],
            fallback=(
                "Retain direct iteration or the stronger cycle-detection cont"
                "rol when the reduction is not supported or not cheaper."
            ),
            outcome_bridge={
                "composition_identity": "(u,v) after (p,q) equals (u*p mod m, (u*q+v) mod m)",
                "identity": "(1,0) represents x -> x",
                "loop_invariant": (
                    "B^e composed with R equals the original F^n; R is the accumu" "lated map and B the current power"
                ),
                "argument": (
                    "Expanding u*(p*x+q)+v gives (u*p)*x+(u*q+v). Associativity f"
                    "ollows from function composition. For e=2k+r, B^e composed w"
                    "ith R=(B^2)^k composed with (B^r composed with R). At e=0 th"
                    "e retained R equals F^n."
                ),
                "status": "human-readable algebraic argument; no proof-assistant certificate",
            },
            falsifier=(
                "Any complete admitted case whose composed result differs fro"
                "m direct iteration; also reject non-affine or time-varying t"
                "ransitions."
            ),
            strong_comparisons=[
                "unchanged direct iteration",
                "hand-engineered cycle detection including tails",
                "automated finite-family selection",
                "per-case oracle minimum over all installed correct controls",
            ],
            frozen_confirmation_evidence={
                "status": "design-frozen",
                "confirmation_commitment": commitment,
                "independent_custody": False,
            },
            reuse_conditions=[
                "Same admitted affine domain, exact outcome and cost rule",
                "New task requires its own local authority and allowance; package grants none",
            ],
            failure_cases=[
                "Non-affine or time-varying recurrence",
                "Modulus outside the bounded domain",
                "A modulus-period shortcut can be false when multipliers are not one",
                "Small horizons and short cycles may favor a control",
            ],
            retirement_triggers=[
                "Code, mathematical domain, instrument or authority changes",
                "Any exact counterexample",
                "Measured full cost fails the intended reuse horizon",
            ],
        ),
    )
    if program.algorithm != "affine-compose":
        alternatives = {
            "direct": {
                "proposed_change": "Retain the unchanged scalar recurrence; no reframing was selected.",
                "outcome_bridge": {
                    "argument": "After t direct updates, the stored scalar is x_t by induction.",
                    "status": "human-readable induction; no proof-assistant certificate",
                },
            },
            "cycle": {
                "proposed_change": (
                    "Retain a first-seen state table, split the deterministic orb"
                    "it into a tail and cycle, then recover the exact requested i"
                    "ndex."
                ),
                "outcome_bridge": {
                    "argument": (
                        "If x_i=x_j for i<j, determinism gives x_(i+k)=x_(j+k) for al"
                        "l k>=0 by induction. Thus x_n=x_(i+(n-i) mod (j-i)) for n>=j"
                        ". Store the tail, not an assumed modulus-sized period."
                    ),
                    "status": "human-readable deterministic-cycle argument; no proof-assistant certificate",
                },
            },
            "representation-only": {
                "proposed_change": (
                    "Represent maps as affine pairs but retain one composition pe"
                    "r original transition; this isolates representation without "
                    "binary production."
                ),
                "outcome_bridge": {
                    "argument": (
                        "One pair composition per tick represents F^t after t iterati"
                        "ons by the affine composition identity. No logarithmic produ"
                        "ction step is used."
                    ),
                    "status": "human-readable induction; no proof-assistant certificate",
                },
            },
        }
        package = package.model_copy(
            update={"witness": package.witness.model_copy(update=alternatives[program.algorithm])}
        )
    return package


def _table(
    cases: list[AffineCase], execution: Meter, search: Meter, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for case in cases:
        outputs: dict[str, Any] = {}
        for name in PROGRAMS:
            search.charge(1)
            outputs[name] = execute(case, MathProgram(algorithm=name), execution)  # type: ignore[arg-type]
        expected = outputs["direct"]["value"]
        correct = all(value["value"] == expected for value in outputs.values())
        rows.append({"case": case.model_dump(), "expected": expected, "methods": outputs, "all_exact": correct})
        if not correct:
            raise ValueError("an installed recurrence method failed the fixed exact-reference check")
    return rows


def additional_workloads_to_break_even(setup: int, direct: int, candidate: int) -> int | None:
    """Minimum extra identical workloads for nonnegative modeled net saving.

    The measured campaign already produced the first workload. Exact equality
    counts as break-even; strictly positive savings can require one more use.
    """
    if any(not _is_exact_type(value, int) or value < 0 for value in (setup, direct, candidate)):
        raise ValueError("break-even accounting requires nonnegative exact logical units")
    deficit = max(0, setup - direct)
    if deficit == 0:
        return 0
    gain = direct - candidate
    if gain <= 0:
        return None
    return (deficit + gain - 1) // gain


class AffineDiscovery:
    """A local signed-journal campaign; exports are inert, without native-v1 authority."""

    def __init__(self, journal: Journal) -> None:
        journal.verify()
        self.journal = journal

    @staticmethod
    def _key(campaign_id: str) -> str:
        return KEY + str(uuid.UUID(campaign_id))

    def show(self, campaign_id: str) -> dict[str, Any]:
        return self.journal.latest(self._key(campaign_id))

    def create(self, request: MathRequest) -> dict[str, Any]:
        request = MathRequest.model_validate(copy.deepcopy(request.model_dump()))
        binding = bindings(request)
        commitment = digest("affine-bindings", binding)
        with self.journal.transaction() as cx:
            try:
                record = self.journal.latest(self._key(request.campaign_id), cx)
            except KeyError:
                return self.journal.append(
                    cx,
                    self._key(request.campaign_id),
                    {
                        "schema": SCHEMA,
                        "state": "queued",
                        "binding": binding,
                        "binding_digest": commitment,
                        "request": request.model_dump(),
                        "approval": None,
                        "spent": {"execution_units": 0, "search_units": 0},
                        "development": [],
                        "freeze": None,
                        "confirmation": None,
                        "result": None,
                    },
                )
            if record["binding_digest"] != commitment:
                raise Conflict("campaign identity belongs to another goal, budget, code or comparison")
            return record

    def _current(self, data: dict[str, Any]) -> MathRequest:
        request = MathRequest.model_validate(data["request"])
        if digest("affine-bindings", bindings(request)) != data["binding_digest"]:
            raise Conflict("installed code, evaluator or comparison changed; new approval and campaign required")
        return request

    def _ready(self, data: dict[str, Any], cx: Any) -> MathRequest:
        if self.journal.latest("@control", cx)["state"] != "ready":
            raise Conflict("operator STOP is active")
        request = self._current(data)
        if data["approval"] != data["binding_digest"]:
            raise PermissionError("approve the exact bounded mathematical comparison first")
        required = {"construct-bounded", "evaluate-local", "write-artifact"}
        if not required <= set(request.charter.permitted_actions):
            raise PermissionError("the fixed charter does not permit this local construction and evidence")
        return request

    def approve(self, campaign_id: str, binding_digest: str) -> dict[str, Any]:
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            self._current(data)
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("operator STOP is active")
            if data["state"] != "queued" or binding_digest != data["binding_digest"]:
                raise Conflict("approval requires the queued exact comparison")
            if data["approval"] == binding_digest:
                return record
            data["approval"] = binding_digest
            return self.journal.append(cx, self._key(campaign_id), data)

    def freeze(self, campaign_id: str) -> dict[str, Any]:
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            if data["state"] in {"frozen", "completed"}:
                return record
            request = self._ready(data, cx)
            execution = Meter(request.charter.budgets.execution_units)
            search = Meter(request.charter.budgets.search_units)
            try:
                _table(request.development, execution, search, data["development"])
                totals = {name: sum(row["methods"][name]["units"] for row in data["development"]) for name in PROGRAMS}
                search.charge(len(PROGRAMS))
                selected = min(PROGRAMS, key=lambda name: (totals[name], name != "direct", name))
                package = _package(
                    MathProgram(algorithm=selected),  # type: ignore[arg-type]
                    request.confirmation_digest,
                )
                manifest = {
                    "selected": selected,
                    "development_units": totals,
                    "package": package.model_dump(),
                    "instrument": instrument(),
                    "binding": data["binding_digest"],
                    "confirmation_digest": request.confirmation_digest,
                    "confirmation_count": request.confirmation_count,
                }
                data["freeze"] = {"manifest": manifest, "digest": digest("affine-freeze", manifest)}
                data["state"] = "frozen"
            except (BudgetExhausted, ArithmeticError, ValueError) as exc:
                data["state"], data["approval"] = "completed", None
                data["result"] = {
                    "decision": "retain-incumbent",
                    "reason": (
                        "incomplete-development-budget"
                        if isinstance(exc, BudgetExhausted)
                        else "invalid-development-result"
                    ),
                    "metrics": None,
                }
            data["spent"] = {"execution_units": execution.used, "search_units": search.used}
            return self.journal.append(cx, self._key(campaign_id), data)

    def confirm(self, campaign_id: str, cases: list[AffineCase], freeze_digest: str) -> dict[str, Any]:
        cases = [AffineCase.model_validate(copy.deepcopy(case.model_dump())) for case in cases]
        if not 1 <= len(cases) <= 2048:
            raise ValueError("confirmation requires a bounded complete case list")
        input_digest = digest("affine-confirmation", cases)
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            if data["state"] == "completed":
                if (
                    data["confirmation"]
                    and data["confirmation"]["input_digest"] == input_digest
                    and data["freeze"]["digest"] == freeze_digest
                ):
                    return record
                raise Conflict("terminal comparison cannot receive another confirmation")
            request = self._ready(data, cx)
            if data["state"] != "frozen" or data["freeze"]["digest"] != freeze_digest:
                raise Conflict("confirmation requires the exact recorded freeze")
            if input_digest != request.confirmation_digest or len(cases) != request.confirmation_count:
                raise ValueError("confirmation must supply the entire committed finite census")
            development = {digest("affine-case", case) for case in request.development}
            fresh = {digest("affine-case", case) for case in cases}
            if len(fresh) != len(cases) or fresh & development:
                raise ValueError("confirmation requires fresh distinct complete cases")
            execution = Meter(request.charter.budgets.execution_units - data["spent"]["execution_units"])
            search = Meter(request.charter.budgets.search_units - data["spent"]["search_units"])
            data["confirmation"] = {"input_digest": input_digest, "rows": [], "complete": False}
            try:
                rows = _table(cases, execution, search, data["confirmation"]["rows"])
                selected = data["freeze"]["manifest"]["selected"]
                totals = {name: sum(row["methods"][name]["units"] for row in rows) for name in PROGRAMS}
                # The unrestricted control has oracle access to every observed method cost.
                # Its data are reused transparently; no additional algorithm is run free.
                search.charge(len(rows) * len(PROGRAMS))
                unrestricted = sum(min(row["methods"][name]["units"] for name in PROGRAMS) for row in rows)
                setup = data["spent"]["execution_units"] + execution.used
                setup_search = data["spent"]["search_units"] + search.used
                full_setup = setup + setup_search
                gain = totals["direct"] - totals[selected]
                data["confirmation"].update({"rows": rows, "complete": True})
                data["result"] = {
                    "decision": (
                        "retain-incumbent"
                        if gain <= 0
                        else (
                            "retain-stronger-cycle-control"
                            if totals["cycle"] <= totals[selected] and selected != "cycle"
                            else "candidate-supported-on-finite-census"
                        )
                    ),
                    "selected": selected,
                    "case_count": len(rows),
                    "all_exact": True,
                    "totals": {**totals, "automated": totals[selected], "unrestricted-oracle": unrestricted},
                    "gain_vs_direct_units": gain,
                    "gain_vs_hand_engineered_units": totals["cycle"] - totals[selected],
                    "beats_unrestricted": totals[selected] < unrestricted,
                    "full_campaign_execution_units": setup,
                    "full_campaign_search_units": setup_search,
                    "full_campaign_logical_units": full_setup,
                    "net_one_census_units_vs_direct": totals["direct"] - full_setup,
                    "minimum_additional_identical_workloads_to_break_even": additional_workloads_to_break_even(
                        full_setup, totals["direct"], totals[selected]
                    ),
                    "reuse_is_not_authorized": True,
                    "control_reuse": (
                        "automated and per-case unrestricted oracle reuse already exe"
                        "cuted method outputs; no extra method execution"
                    ),
                    "scope": (
                        "exact public finite census only; no blind sampling, independ"
                        "ent validation, universal speedup or research novelty claim"
                    ),
                    "proof_status": "argument-present-not-machine-checked",
                    "provider_requests": 0,
                    "device_cost": "UNKNOWN",
                    "human_review_cost": "UNKNOWN",
                }
            except (BudgetExhausted, ArithmeticError, ValueError) as exc:
                data["result"] = {
                    "decision": "retain-incumbent",
                    "reason": (
                        "incomplete-confirmation-budget"
                        if isinstance(exc, BudgetExhausted)
                        else "invalid-confirmation-result"
                    ),
                    "metrics": None,
                }
            data["spent"]["execution_units"] += execution.used
            data["spent"]["search_units"] += search.used
            data["state"], data["approval"] = "completed", None
            return self.journal.append(cx, self._key(campaign_id), data)

    def envelope(self, campaign_id: str) -> dict[str, Any]:
        """Return durable package/evidence as inert data; no import/execution API exists."""
        record = self.show(campaign_id)
        data = Journal.document(record)
        data["approval"] = None
        return {
            "schema": SCHEMA,
            "journal_checkpoint": {
                "identity": self.journal.identity,
                "revision": record["revision"],
                "digest": record["digest"],
                "requires_original_journal_for_verification": True,
            },
            "campaign": data,
            "authority": "none",
            "native_v1_compatible": False,
            "review": "pending; same local operator is not organizational independence",
            "settlement": "none",
        }


def confirmation_cases() -> list[AffineCase]:
    """Complete Cartesian census of this explicit finite public validation family."""
    return [
        AffineCase(modulus=m, multiplier=a, increment=b, initial=x, steps=n)
        for m in (5, 17, 31, 97)
        for a in (0, 1, 2, m - 1)
        for b in (0, 1, m - 1)
        for x in (0, 1, m - 1)
        for n in (0, 1, 7, 31, 127, 255)
    ]


def example_request(campaign_id: str | None = None) -> MathRequest:
    """A documented development set with moduli disjoint from confirmation."""
    fresh = confirmation_cases()
    return MathRequest(
        campaign_id=campaign_id or str(uuid.uuid4()),
        charter=MathCharter(
            permitted_actions=["construct-bounded", "evaluate-local", "write-artifact"],
            budgets=DiscoveryBudget(search_units=100_000, execution_units=1_000_000),
        ),
        development=[
            AffineCase(modulus=m, multiplier=2, increment=1, initial=0, steps=n)
            for m in (7, 13, 29)
            for n in (31, 127, 511)
        ],
        confirmation_digest=digest("affine-confirmation", fresh),
        confirmation_count=len(fresh),
    )


def main() -> None:
    """Create a new durable, explicitly free local reproduction; never overwrite files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-id", help="optional canonical UUID for repeatable source-context evidence")
    parser.add_argument("--state", type=Path, required=True, help="absent directory for the durable signed journal")
    parser.add_argument("--output", type=Path, required=True, help="absent UTF-8 evidence JSON path")
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.state.exists() or args.state.is_symlink():
        parser.error("state and output must be new paths; existing evidence is never replaced")
    started = time.monotonic_ns()
    request = example_request(args.campaign_id)
    loop = AffineDiscovery(Journal.initialize(args.state))
    queued = loop.create(request)
    loop.approve(request.campaign_id, queued["binding_digest"])
    frozen = loop.freeze(request.campaign_id)
    if frozen["state"] == "frozen":
        loop.confirm(request.campaign_id, confirmation_cases(), frozen["freeze"]["digest"])
    report = loop.envelope(request.campaign_id)
    report["elapsed_nanoseconds"] = time.monotonic_ns() - started
    private_write(args.output, canonical(report) + b"\n")
    print(f"Retained {SCHEMA} evidence at {args.output}; local cost only, no execution or spending authority exported.")


if __name__ == "__main__":
    main()
