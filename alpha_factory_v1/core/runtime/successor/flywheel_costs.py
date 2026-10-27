# SPDX-License-Identifier: Apache-2.0
"""Disjoint delivery, incremental-retention and optional-investment accounting.

Amounts are USD micro-units, not token movements. Signed attestations retain
their evidence and uncertainty; they are not bank or provider attestations.
"""

from __future__ import annotations

from typing import Any, Callable, Literal

from pydantic import Field, model_validator

from ..store import Conflict, Journal, digest as runtime_digest
from .protocol import MAX_JSON_BYTES, MAX_JSON_NODES, Digest, Identifier, StrictModel, Text, canonical, digest
from .trust import SignedEnvelope, TrustRegistry
from .flywheel_checkpoint import DurableCheckpoint

KEY = "@flywheel-costs:v1"
CATEGORIES = {"model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"}
MAX_OPERATION_CACHE = 128
MAX_PAYMENT_CACHE = 32
CHARGE_COMPLETION_BYTES = 40_960


def accepted_native_delivery(journal: Journal, mission_id: str, cx: Any = None) -> dict[str, Any]:
    """Read actual native completion and its bound approval, never a synthetic status flag."""
    from ..models import Mission, Research
    from ..work import verify_result

    record = journal.latest(mission_id, cx)
    review = record.get("review", {})
    if (
        record.get("state") != "completed"
        or review.get("approved") is not True
        or review.get("result_hash") != runtime_digest(record.get("result"))
        or record.get("request_hash") != runtime_digest(record.get("request"))
    ):
        raise ValueError("origin requires exact completed and approved native delivery")
    mission = Mission.model_validate(record["request"])
    if not isinstance(mission.work, Research):
        raise ValueError("this protected slice supports native public-source research delivery only")
    verify_result(mission, record["result"])
    return record


class Charge(StrictModel):
    activity_id: Identifier
    mission_id: Identifier
    bucket: Literal["A", "B", "C"]
    category: Literal[
        "model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"
    ]
    accrued_micro_usd: int | None = Field(ge=0, le=10**15)
    paid_micro_usd: int = Field(ge=0, le=10**15)
    basis: Literal["measured", "attested", "unknown"]
    evidence_digest: Digest
    note: Text

    @model_validator(mode="after")
    def complete_amount(self) -> Charge:
        if (self.accrued_micro_usd is None) != (self.basis == "unknown"):
            raise ValueError("unknown costs must stay unknown rather than becoming zero")
        if self.accrued_micro_usd is not None and self.paid_micro_usd > self.accrued_micro_usd:
            raise ValueError("paid cost exceeds its complete accrual")
        return self


class Payment(StrictModel):
    payment_id: Identifier
    activity_id: Identifier
    amount_micro_usd: int = Field(gt=0, le=10**15)
    evidence_digest: Digest


class CompletenessSeal(StrictModel):
    mission_id: Identifier
    evidence_digest: Digest
    categories: list[str] = Field(min_length=9, max_length=9)

    @model_validator(mode="after")
    def exact_categories(self) -> CompletenessSeal:
        if set(self.categories) != CATEGORIES:
            raise ValueError("completeness requires exactly every resource category")
        return self


class CostLedger:
    """Use the existing atomic journal and configured accounting authority."""

    def __init__(self, journal: Journal, trust: TrustRegistry) -> None:
        self.journal, self.trust = journal, trust
        self.checkpoint: DurableCheckpoint | None = None
        self.custody_check: Callable[[], None] | None = None
        with journal.transaction() as cx:
            try:
                journal.latest(KEY, cx)
            except KeyError:
                journal.append(
                    cx,
                    KEY,
                    {
                        "charges": {},
                        "receipts": {},
                        "offers": {},
                        "capital": {},
                        "reserve_micro_usd": 0,
                        "seals": {},
                        "reuse_seals": {},
                        "operations": {},
                    },
                )

    def snapshot(self, cx: Any = None) -> dict[str, Any]:
        if self.custody_check is not None:
            self.custody_check()
        if self.checkpoint is not None:
            if cx is None:
                with self.journal.transaction() as connection:
                    return self.snapshot(connection)
            self.checkpoint.verify(self.journal, cx)
        return self.journal.document(self.journal.latest(KEY, cx))

    @staticmethod
    def require_open(state: dict[str, Any], mission_id: str, bucket: str) -> None:
        seals = (
            state["seals"]
            if bucket == "A"
            else state.get("reuse_seals", {})
            if bucket == "B"
            else state.get("investment_seals", {})
        )
        if mission_id in seals:
            raise Conflict("sealed cost records cannot acquire another invocation or activity")

    @staticmethod
    def _nodes(value: Any) -> int:
        pending = [value]
        count = 0
        while pending:
            item = pending.pop()
            count += 1
            if isinstance(item, dict):
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        return count

    def _persist(self, cx: Any, state: dict[str, Any]) -> None:
        """Reserve worst-case bounded reconciliation before any new paid work."""
        rows = list(state["charges"].values())
        seals = {"A": state["seals"], "B": state.get("reuse_seals", {}), "C": state.get("investment_seals", {})}
        groups: dict[tuple[str, str], set[str]] = {}
        for row in rows:
            if row["mission_id"] not in seals[row["bucket"]]:
                groups.setdefault((row["mission_id"], row["bucket"]), set()).add(row["category"])
        unknown = sum(row["accrued_micro_usd"] is None for row in rows)
        missing = sum(len(CATEGORIES - categories) for categories in groups.values())
        operations, payments = state["operations"], state.get("payments", {})
        # Working caches always have this finite budget, regardless of current fill.
        reserve_bytes = (
            16_384
            + CHARGE_COMPLETION_BYTES * (unknown + missing)
            + 4096 * len(groups)
            + 32_768
            - len(canonical(operations))
            + 262_144
            - len(canonical(payments))
        )
        reserve_nodes = (
            512 + 128 * (unknown + missing + len(groups)) + 129 - self._nodes(operations) + 2048 - self._nodes(payments)
        )
        for row in rows:
            if row["accrued_micro_usd"] is None or row["paid_micro_usd"] < row["accrued_micro_usd"]:
                summary = {"paid_micro_usd": row["paid_micro_usd"]}
                if "payment_count" in row:
                    summary["payment_count"] = row["payment_count"]
                reserve_bytes += 128 - len(canonical(summary))
                reserve_nodes += 2 - int("payment_count" in row)
        if (
            len(operations) > MAX_OPERATION_CACHE
            or len(payments) > MAX_PAYMENT_CACHE
            or reserve_bytes < 0
            or reserve_nodes < 0
        ):
            raise Conflict("accounting working caches require durable compaction")
        state["reserved_capacity_bytes"], state["reserved_capacity_nodes"] = reserve_bytes, reserve_nodes
        if (
            len(canonical(state)) + reserve_bytes > MAX_JSON_BYTES
            or self._nodes(state) + reserve_nodes > MAX_JSON_NODES
        ):
            raise Conflict("accounting capacity preserves outstanding reconciliation and completeness reserves")
        self.journal.append(cx, KEY, state)

    def _remember_operation(
        self, cx: Any, state: dict[str, Any], operation: str, binding: str, signed: SignedEnvelope
    ) -> None:
        self.journal.append(
            cx, "@flywheel-accounting-operation:" + operation, {"binding": binding, "signed": signed.model_dump()}
        )
        operations = state["operations"]
        operations[operation] = binding
        while len(operations) > MAX_OPERATION_CACHE:
            old = next(iter(operations))
            old_binding = operations.pop(old)
            try:
                self.journal.latest("@flywheel-accounting-operation:" + old, cx)
            except KeyError:
                self.journal.append(cx, "@flywheel-accounting-operation:" + old, {"binding": old_binding})

    def _remember_payment(self, cx: Any, payment_id: str, payment: dict[str, Any]) -> None:
        self.journal.append(cx, "@flywheel-payment:" + payment_id, payment)
        self.journal.append(cx, "@flywheel-payment-evidence:" + payment["evidence_digest"], {"payment_id": payment_id})

    def apply(self, signed: SignedEnvelope) -> dict[str, Any]:
        signed = SignedEnvelope.model_validate(signed.model_dump())
        payload = self.trust.verify(signed, "flywheel-cost-command", "accounting")
        if payload.get("journal_identity") != self.journal.identity or set(payload) != {
            "journal_identity",
            "operation_id",
            "action",
            "record",
        }:
            raise ValueError("accounting command must bind this journal and exact terms")
        operation_id = payload["operation_id"]
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 128:
            raise ValueError("bounded accounting operation identity required")
        binding = digest("flywheel-cost-command", payload)
        with self.journal.transaction() as cx:
            state = self.snapshot(cx)
            old = state["operations"].get(operation_id)
            if old is None:
                try:
                    old = self.journal.latest("@flywheel-accounting-operation:" + operation_id, cx)["binding"]
                except KeyError:
                    pass
            if old:
                if old != binding:
                    raise Conflict("accounting operation identity already has different terms")
                return state
            action, record = payload["action"], payload["record"]
            if action == "charge":
                charge = Charge.model_validate(record)
                if charge.activity_id in state["charges"]:
                    raise Conflict("activity already charged; A, B and C cannot overlap")
                self.require_open(state, charge.mission_id, charge.bucket)
                if charge.bucket == "A" and charge.mission_id in state["seals"]:
                    raise Conflict("sealed delivery cannot acquire an unreviewed additional charge")
                if charge.bucket == "B" and charge.mission_id in state.get("reuse_seals", {}):
                    raise Conflict("sealed incremental-cost record cannot acquire additional charges")
                state["charges"][charge.activity_id] = {**charge.model_dump(), "signed": signed.model_dump()}
            elif action == "resolve":
                charge = Charge.model_validate(record)
                previous = state["charges"].get(charge.activity_id)
                if previous is None or previous["accrued_micro_usd"] is not None or charge.accrued_micro_usd is None:
                    raise Conflict("only a recorded unknown charge may be resolved once")
                if any(previous[k] != getattr(charge, k) for k in ("mission_id", "bucket", "category")):
                    raise ValueError("reconciliation cannot move an activity between records or buckets")
                if charge.paid_micro_usd < previous["paid_micro_usd"]:
                    raise ValueError("reconciliation cannot reverse an already recorded payment")
                state["charges"][charge.activity_id] = {
                    **charge.model_dump(),
                    "signed": signed.model_dump(),
                    "original": previous,
                }
            elif action == "payment":
                payment = Payment.model_validate(record)
                payments = state.setdefault("payments", {})
                if payment.payment_id in payments or any(
                    row["evidence_digest"] == payment.evidence_digest for row in payments.values()
                ):
                    raise Conflict("payment identity or allocated evidence already reconciled")
                for key in (
                    "@flywheel-payment:" + payment.payment_id,
                    "@flywheel-payment-evidence:" + payment.evidence_digest,
                ):
                    try:
                        self.journal.latest(key, cx)
                    except KeyError:
                        pass
                    else:
                        raise Conflict("payment identity or allocated evidence already reconciled")
                charge_record = state["charges"].get(payment.activity_id)
                if charge_record is None or charge_record["accrued_micro_usd"] is None:
                    raise Conflict("payment reconciliation requires an existing known accrual")
                if payment.amount_micro_usd > charge_record["accrued_micro_usd"] - charge_record["paid_micro_usd"]:
                    raise ValueError("payment exceeds the remaining accrued liability")
                charge_record["paid_micro_usd"] += payment.amount_micro_usd
                old_ids = charge_record.pop("payment_ids", [])
                charge_record["payment_count"] = charge_record.get("payment_count", len(old_ids)) + 1
                payments[payment.payment_id] = {**payment.model_dump(), "signed": signed.model_dump()}
                self._remember_payment(cx, payment.payment_id, payments[payment.payment_id])
                while len(payments) > MAX_PAYMENT_CACHE:
                    old_payment = next(iter(payments))
                    self._remember_payment(cx, old_payment, payments.pop(old_payment))
            elif action in {"capital", "collection", "offer", "invoice", "pending"}:
                if not isinstance(record, dict) or set(record) != {
                    "record_id",
                    "mission_id",
                    "amount_micro_usd",
                    "evidence_digest",
                }:
                    raise ValueError("money records require exact identity, mission, amount and evidence")
                IdentifierModel.model_validate(record)
                target = "capital" if action == "capital" else "receipts" if action == "collection" else "offers"
                if any(record["record_id"] in state[key] for key in ("capital", "receipts", "offers")):
                    raise Conflict("money record identity already used")
                if action in {"capital", "collection"} and any(
                    row["evidence_digest"] == record["evidence_digest"]
                    for key in ("capital", "receipts")
                    for row in state[key].values()
                ):
                    raise Conflict("incoming funding evidence already credited as capital or collection")
                state[target][record["record_id"]] = {**record, "kind": action, "signed": signed.model_dump()}
            elif action == "reserve":
                if type(record) is not int or not 0 <= record <= 10**15:
                    raise ValueError("reserve requires nonnegative integer USD micro-units")
                state["reserve_micro_usd"] = record
            elif action in {"seal", "seal-reuse", "seal-retention", "seal-investment"}:
                record = CompletenessSeal.model_validate(record).model_dump()
                mission = record["mission_id"]
                seals = (
                    state["seals"]
                    if action == "seal"
                    else state.setdefault("investment_seals" if action == "seal-investment" else "reuse_seals", {})
                )
                if mission in seals:
                    raise Conflict("delivery costs already sealed")
                rows = [
                    r
                    for r in state["charges"].values()
                    if r["mission_id"] == mission
                    and r["bucket"] == ("A" if action == "seal" else "C" if action == "seal-investment" else "B")
                ]
                if {r["category"] for r in rows} != CATEGORIES or any(r["accrued_micro_usd"] is None for r in rows):
                    raise ValueError("missing or unknown delivery costs prevent a complete-cost claim")
                seals[mission] = {**record, "signed": signed.model_dump()}
            else:
                raise ValueError("unsupported accounting action")
            self._remember_operation(cx, state, operation_id, binding, signed)
            self._persist(cx, state)
            if self.checkpoint is not None:
                self.checkpoint.advance(self.journal, cx)
            return state

    def report(self, mission_id: str | None = None, cx: Any = None) -> dict[str, Any]:
        state = self.snapshot(cx)
        all_rows = list(state["charges"].values())
        rows = [r for r in all_rows if mission_id is None or r["mission_id"] == mission_id]
        totals = {
            bucket: sum(r["accrued_micro_usd"] or 0 for r in rows if r["bucket"] == bucket)
            for bucket in ("A", "B", "C")
        }
        collected = sum(
            r["amount_micro_usd"]
            for r in state["receipts"].values()
            if mission_id is None or r["mission_id"] == mission_id
        )
        capital = sum(r["amount_micro_usd"] for r in state["capital"].values())
        all_collected = sum(r["amount_micro_usd"] for r in state["receipts"].values())
        paid = sum(r["paid_micro_usd"] for r in all_rows)
        obligations = sum(
            r["accrued_micro_usd"] - r["paid_micro_usd"] for r in all_rows if r["accrued_micro_usd"] is not None
        )
        unknown = any(r["accrued_micro_usd"] is None for r in all_rows)
        seal_sets = {"A": state["seals"], "B": state.get("reuse_seals", {}), "C": state.get("investment_seals", {})}
        present = {row["bucket"] for row in rows}
        bucket_complete = {}
        for bucket in ("A", "B", "C"):
            selected = [row for row in rows if row["bucket"] == bucket]
            missions = {row["mission_id"] for row in selected}
            bucket_complete[bucket] = (
                bool(missions)
                and missions <= set(seal_sets[bucket])
                and all(row["accrued_micro_usd"] is not None for row in selected)
            )
        complete = bool(present) and all(bucket_complete[bucket] for bucket in present)
        return {
            "currency": "USD",
            "unit": "micro_usd",
            "costs": totals,
            "collected_revenue": collected,
            "delivery_profit": collected - totals["A"] if bucket_complete["A"] else None,
            "complete_cost_profit": collected - sum(totals.values()) if complete else None,
            "cash": capital + all_collected - paid,
            "obligations": None if unknown else obligations,
            "known_obligations": obligations,
            "reserve": state["reserve_micro_usd"],
            "available_funds": None
            if unknown
            else capital + all_collected - paid - obligations - state["reserve_micro_usd"],
            "complete": complete,
            "bucket_complete": bucket_complete,
            "unknown_costs": unknown,
            "token_movements_included": False,
            "evidence_basis": "configured accounting signer attestations",
        }


class IdentifierModel(StrictModel):
    record_id: Identifier
    mission_id: Identifier
    amount_micro_usd: int = Field(ge=0, le=10**15)
    evidence_digest: Digest
