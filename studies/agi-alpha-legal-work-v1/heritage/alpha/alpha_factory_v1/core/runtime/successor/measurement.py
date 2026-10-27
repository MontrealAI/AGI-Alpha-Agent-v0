# SPDX-License-Identifier: Apache-2.0
"""Purpose-grounded measurement epochs and a journal-wide confirmation budget.

Configured signers attest process properties; hashes do not establish them. Local
role separation is not independent organizational review. Cross-journal custody
and a separately retained checkpoint remain operational requirements.
"""

from __future__ import annotations

import copy
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, Literal

from pydantic import Field, model_validator

from ..store import Conflict, Journal
from .protocol import Count, Digest, Identifier, StrictModel, Text, canonical, digest
from .trust import SignedEnvelope, TrustRegistry


def _is_exact_type(value: object, expected: type[object]) -> bool:
    """Compare exact types without admitting bool or other subclasses."""
    return type(value) is expected


KEY = "@transformational-measurement:v1"
SCALE = 1_000_000
MAX_ATTEMPTS = 1000


class EvaluationInstrument(StrictModel):
    instrument_id: Identifier
    version: Count
    domain: Text
    method: Text
    implementation_digest: Digest
    calibration_error_ppm: int | None = Field(default=None, ge=0, le=SCALE)
    calibration_evidence: list[Digest] = Field(default_factory=list, max_length=128)
    calibration_scope: Text
    calibration_failure_ppb: int = Field(default=0, ge=0, le=1_000_000_000)


class ConfirmationClaim(StrictModel):
    claim_id: Identifier
    estimand: Text
    score_definition: Text


class ConfirmationDesign(StrictModel):
    campaign_id: Identifier
    producer: Identifier
    charter_digest: Digest
    candidate_digest: Digest
    comparator_digest: Digest
    code_digest: Digest
    model_digest: Digest
    configuration_digest: Digest
    bridge_digest: Digest
    resource_rules_digest: Digest
    initial_agents_digest: Digest
    archive_access_digest: Digest
    sampling_unit: Literal["independent-campaign", "independent-episode"]
    population: Text
    independence_protocol: Text
    claims: list[ConfirmationClaim] = Field(min_length=1, max_length=16)
    margin_ppm: int = Field(default=0, ge=0, le=SCALE)

    @model_validator(mode="after")
    def distinct_claims(self) -> ConfirmationDesign:
        if len({claim.claim_id for claim in self.claims}) != len(self.claims):
            raise ValueError("confirmation claim identities must be unique")
        return self


def _fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


class MeasurementLedger:
    """Serialize all projects' attempts in one existing authenticated journal."""

    def __init__(self, journal: Journal, trust: TrustRegistry, *, producer: str = "local-producer") -> None:
        self.journal, self.trust, self.producer = journal, trust, producer
        trust.anchor(producer, "producer")
        journal.verify()
        with journal.transaction() as cx:
            try:
                journal.latest(KEY, cx)
            except KeyError:
                journal.append(cx, KEY, {"schema": "ti-measurement/v1", "epochs": [], "attempts": [], "operations": {}})

    def snapshot(self) -> dict[str, Any]:
        return self.journal.document(self.journal.latest(KEY))

    def _authenticate(self, envelope: SignedEnvelope, domain: str, role: str) -> dict[str, Any]:
        payload = self.trust.verify(envelope, domain, role)
        if payload.get("journal_identity") != self.journal.identity:
            raise ValueError("measurement authorization belongs to a different journal")
        canonical(payload)
        return payload

    @staticmethod
    def _stable(envelope: SignedEnvelope) -> SignedEnvelope:
        return SignedEnvelope.model_validate(copy.deepcopy(envelope.model_dump()))

    def _distinct(self, first: str, role: str, second: str, other_role: str) -> None:
        if (
            first == second
            or self.trust.anchor(first, role).public_key == self.trust.anchor(second, other_role).public_key
        ):
            raise ValueError("measurement roles require distinct configured principals and keys")

    @staticmethod
    def _operation(state: dict[str, Any], operation_id: str, payload: Any) -> bool:
        if not operation_id or len(operation_id) > 128:
            raise ValueError("a bounded operation identity is required")
        fingerprint = digest("measurement-command", payload)
        old = state["operations"].get(operation_id)
        if old is not None and old != fingerprint:
            raise Conflict("measurement operation identity already has different terms")
        if len(state["operations"]) >= 5000 and old is None:
            raise Conflict("measurement ledger capacity reached; do not reset its error budget")
        state["operations"][operation_id] = fingerprint
        return old is not None

    def revise_instrument(
        self,
        instrument: EvaluationInstrument,
        validation: SignedEnvelope,
        approval: SignedEnvelope,
        *,
        operation_id: str,
    ) -> dict[str, Any]:
        """Require a verifier's disagreement study and a separate controller's approval."""
        instrument = EvaluationInstrument.model_validate(copy.deepcopy(instrument.model_dump()))
        validation, approval = self._stable(validation), self._stable(approval)
        checked = self._authenticate(validation, "measurement-validation", "verifier")
        accepted = self._authenticate(approval, "measurement-approval", "controller")
        instrument_hash = digest("measurement-instrument", instrument)
        self._distinct(validation.principal, "verifier", approval.principal, "controller")
        self._distinct(validation.principal, "verifier", self.producer, "producer")
        self._distinct(approval.principal, "controller", self.producer, "producer")
        required = {"journal_identity", "previous_instrument", "instrument_digest", "diagnosis", "cases", "scope"}
        if set(checked) != required or checked["instrument_digest"] != instrument_hash:
            raise ValueError("instrument validation does not bind this exact replacement")
        if not all(_is_exact_type(checked[key], str) and checked[key] for key in ("diagnosis", "scope")):
            raise ValueError("instrument validation requires a diagnosis and explicit evidence scope")
        cases = checked["cases"]
        if not _is_exact_type(cases, list) or not 1 <= len(cases) <= 128:
            raise ValueError("instrument validation requires separately adjudicated cases")
        seen: set[str] = set()
        for case in cases:
            if (
                not _is_exact_type(case, dict)
                or set(case) != {"id", "evidence_digest", "old_score_ppm", "new_score_ppm", "outcome_ppm"}
                or not _is_exact_type(case["id"], str)
                or not case["id"]
                or case["id"] in seen
            ):
                raise ValueError("invalid or duplicate instrument disagreement case")
            seen.add(case["id"])
            if (
                not _is_exact_type(case["evidence_digest"], str)
                or len(case["evidence_digest"]) != 64
                or any(c not in "0123456789abcdef" for c in case["evidence_digest"])
                or any(
                    not _is_exact_type(case[key], int) or not 0 <= case[key] <= SCALE
                    for key in ("old_score_ppm", "new_score_ppm", "outcome_ppm")
                )
            ):
                raise ValueError("invalid case evidence or bounded scores")
        expected = {
            "journal_identity": self.journal.identity,
            "instrument_digest": instrument_hash,
            "validation_digest": digest("measurement-validation", validation.model_dump()),
            "previous_instrument": checked["previous_instrument"],
        }
        if accepted != expected:
            raise ValueError("controller approval must bind the complete validated revision")
        if instrument.calibration_error_ppm is not None and not instrument.calibration_evidence:
            raise ValueError("a calibration bound requires explicit supporting evidence")
        with self.journal.transaction() as cx:
            state = self.journal.document(self.journal.latest(KEY, cx))
            if self._operation(
                state, operation_id, [instrument.model_dump(), validation.model_dump(), approval.model_dump()]
            ):
                return next(copy.deepcopy(e) for e in state["epochs"] if e["operation_id"] == operation_id)
            previous = state["epochs"][-1]["instrument_digest"] if state["epochs"] else None
            if checked["previous_instrument"] != previous:
                raise Conflict("instrument changed; a fresh validation and comparison basis are required")
            if previous is not None and not any(c["old_score_ppm"] != c["new_score_ppm"] for c in cases):
                raise ValueError("a revision requires independently adjudicated disagreement cases")
            epoch = {
                "epoch": len(state["epochs"]) + 1,
                "instrument_digest": instrument_hash,
                "operation_id": operation_id,
                "instrument": instrument.model_dump(),
                "validation": validation.model_dump(),
                "approval": approval.model_dump(),
                "scope": "configured-role-attestation",
            }
            state["epochs"].append(epoch)
            self.journal.append(cx, KEY, state)
            return copy.deepcopy(epoch)

    def reserve_confirmation(
        self,
        frozen: ConfirmationDesign,
        sample_size: int,
        claim_count: int,
        approval: SignedEnvelope,
        *,
        operation_id: str,
    ) -> dict[str, Any]:
        frozen = ConfirmationDesign.model_validate(copy.deepcopy(frozen.model_dump()))
        approval = self._stable(approval)
        if (
            not _is_exact_type(sample_size, int)
            or not 1 <= sample_size <= 5000
            or not _is_exact_type(claim_count, int)
            or not 1 <= claim_count <= 16
            or sample_size * claim_count > 10000
            or claim_count != len(frozen.claims)
        ):
            raise ValueError("confirmation requires a fixed bounded sample and claim count")
        payload = self._authenticate(approval, "measurement-confirmation", "verifier")
        if frozen.producer != self.producer:
            raise ValueError("confirmation producer must match the independently configured runtime producer")
        self._distinct(approval.principal, "verifier", self.producer, "producer")
        with self.journal.transaction() as cx:
            state = self.journal.document(self.journal.latest(KEY, cx))
            terms = [frozen.model_dump(), sample_size, claim_count, approval.model_dump()]
            if self._operation(state, operation_id, terms):
                return next(copy.deepcopy(a) for a in state["attempts"] if a["operation_id"] == operation_id)
            if not state["epochs"] or len(state["attempts"]) >= MAX_ATTEMPTS:
                raise Conflict("validated instrument required or global attempt budget exhausted")
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("agent is stopped")
            epoch = state["epochs"][-1]
            expected = {
                "journal_identity": self.journal.identity,
                "freeze_digest": digest("confirmation-design", frozen),
                "sample_size": sample_size,
                "claim_count": claim_count,
                "instrument_digest": epoch["instrument_digest"],
                "epoch": epoch["epoch"],
                "operation_id": operation_id,
            }
            if payload != expected:
                raise ValueError("confirmation approval is stale or belongs to different frozen terms")
            number = len(state["attempts"]) + 1
            attempt = {
                **expected,
                "attempt": number,
                "alpha_per_claim": _fraction(Fraction(1, 20 * number * (number + 1) * claim_count)),
                "frozen": frozen.model_dump(),
                "custodian": approval.principal,
                "approval": approval.model_dump(),
                "state": "reserved",
                "result": None,
            }
            attempt["attempt_digest"] = digest("confirmation-attempt", attempt)
            state["attempts"].append(attempt)
            self.journal.append(cx, KEY, state)
            return copy.deepcopy(attempt)

    def conclude(self, attempt_number: int, observations: SignedEnvelope) -> dict[str, Any]:
        """Consume the entire fixed sample once; never expose an intermediate promotion gate."""
        observations = self._stable(observations)
        payload = self._authenticate(observations, "measurement-observations", "verifier")
        if not _is_exact_type(attempt_number, int) or attempt_number < 1:
            raise ValueError("invalid attempt number")
        with self.journal.transaction() as cx:
            state = self.journal.document(self.journal.latest(KEY, cx))
            if attempt_number > len(state["attempts"]):
                raise ValueError("unknown confirmation attempt")
            attempt = state["attempts"][attempt_number - 1]
            observation_digest = digest("confirmation-observations", observations.model_dump())
            if attempt["state"] == "complete":
                if attempt["result"]["observation_digest"] != observation_digest:
                    raise Conflict("fixed-sample attempt already completed with different observations")
                return copy.deepcopy(attempt["result"])
            if attempt["state"] != "reserved":
                raise Conflict("failed or cancelled attempts cannot be reused")
            required = {
                "journal_identity",
                "attempt_digest",
                "unit_ids",
                "scores",
                "freshness_attestation",
                "independence_attestation",
            }
            if (
                set(payload) != required
                or observations.principal != attempt["custodian"]
                or payload["attempt_digest"] != attempt["attempt_digest"]
                or not all(
                    _is_exact_type(payload[k], str) and payload[k]
                    for k in ("freshness_attestation", "independence_attestation")
                )
            ):
                raise ValueError("confirmation requires the reserved custodian's bound process evidence")
            units = payload["unit_ids"]
            used = {
                unit for old in state["attempts"] if old["result"] is not None for unit in old["result"]["unit_ids"]
            }

            def invalid(reason: str) -> dict[str, Any]:
                disclosed = (
                    sorted({u for u in units if _is_exact_type(u, str) and 0 < len(u) <= 160})
                    if _is_exact_type(units, list)
                    else []
                )
                result = {
                    "decision": "invalid-sample",
                    "reason": reason,
                    "claims": [],
                    "unit_ids": disclosed,
                    "observation_digest": observation_digest,
                    "observations": observations.model_dump(),
                    "authorization_granted": False,
                }
                attempt.update(state="invalid", result=result)
                self.journal.append(cx, KEY, state)
                return copy.deepcopy(result)

            if (
                not _is_exact_type(units, list)
                or len(units) != attempt["sample_size"]
                or any(not _is_exact_type(u, str) or not u or len(u) > 160 for u in units)
                or len(set(units)) != len(units)
                or set(units) & used
            ):
                return invalid("complete fresh nonrepeated experimental units are required")
            scores = payload["scores"]
            if not _is_exact_type(scores, list) or len(scores) != attempt["claim_count"]:
                return invalid("all preregistered claims must be reported")
            instrument = state["epochs"][attempt["epoch"] - 1]["instrument"]
            claims = []
            with localcontext() as ctx:
                ctx.prec = 60
                alpha = Fraction(attempt["alpha_per_claim"])
                radius = (
                    Decimal(2) * (Decimal(alpha.denominator) / Decimal(alpha.numerator)).ln() / Decimal(len(units))
                ).sqrt()
                for claim_design, pairs in zip(attempt["frozen"]["claims"], scores, strict=True):
                    if (
                        not _is_exact_type(pairs, list)
                        or len(pairs) != len(units)
                        or any(
                            not _is_exact_type(p, list)
                            or len(p) != 2
                            or any(not _is_exact_type(s, int) or not 0 <= s <= SCALE for s in p)
                            for p in pairs
                        )
                    ):
                        return invalid("use the complete paired candidate/comparator sample in integer ppm")
                    mean = Decimal(sum(p[0] - p[1] for p in pairs)) / Decimal(SCALE * len(units))
                    lower = (mean - radius).next_minus()
                    epsilon = instrument["calibration_error_ppm"]
                    corrected = None if epsilon is None else (lower - Decimal(2 * epsilon) / SCALE).next_minus()
                    margin = Decimal(attempt["frozen"]["margin_ppm"]) / SCALE
                    claims.append(
                        {
                            "claim_id": claim_design["claim_id"],
                            "estimand": claim_design["estimand"],
                            "score_definition": claim_design["score_definition"],
                            "mean_gain": str(mean),
                            "score_lower_bound": str(lower),
                            "outcome_lower_bound": None if corrected is None else str(corrected),
                            "score_margin_pass": lower > margin,
                            "outcome_margin_pass": None if corrected is None else corrected > margin,
                        }
                    )
            result = {
                "claims": claims,
                "unit_ids": units,
                "observation_digest": observation_digest,
                "observations": observations.model_dump(),
                "epoch": attempt["epoch"],
                "alpha_per_claim": attempt["alpha_per_claim"],
                "calibration_failure_ppb": instrument["calibration_failure_ppb"],
                "global_score_error_budget": "1/20",
                "calibration_error_accounted": _fraction(
                    Fraction(sum(e["instrument"]["calibration_failure_ppb"] for e in state["epochs"]), 1_000_000_000)
                ),
                "calibration_accounting_scope": (
                    "one separately justified uniform event per registered instru" "ment epoch"
                ),
                "authorization_granted": False,
                "evidence_scope": "signed-process-attestation; independence is not established by hashes",
            }
            attempt.update(state="complete", result=result)
            self.journal.append(cx, KEY, state)
            return copy.deepcopy(result)

    def abandon(self, attempt_number: int, reason: str, approval: SignedEnvelope) -> None:
        if not _is_exact_type(attempt_number, int) or attempt_number < 1 or not reason or len(reason) > 4000:
            raise ValueError("a valid attempt and bounded reason are required")
        approval = self._stable(approval)
        payload = self._authenticate(approval, "measurement-abandon", "verifier")
        with self.journal.transaction() as cx:
            state = self.journal.document(self.journal.latest(KEY, cx))
            if attempt_number > len(state["attempts"]):
                raise ValueError("unknown confirmation attempt")
            attempt = state["attempts"][attempt_number - 1]
            if approval.principal != attempt["custodian"] or payload != {
                "journal_identity": self.journal.identity,
                "attempt_digest": attempt["attempt_digest"],
                "reason": reason,
            }:
                raise ValueError("only the reserved custodian may abandon the exact attempt")
            if attempt["state"] != "reserved":
                raise Conflict("attempt is already terminal")
            attempt.update(state="abandoned", reason=reason)
            self.journal.append(cx, KEY, state)
