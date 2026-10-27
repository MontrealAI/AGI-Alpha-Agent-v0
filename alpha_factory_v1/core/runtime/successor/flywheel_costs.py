# SPDX-License-Identifier: Apache-2.0
"""Disjoint delivery, incremental-retention and optional-investment accounting.

Amounts are USD micro-units, not token movements. Signed attestations retain
their evidence and uncertainty; they are not bank or provider attestations.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from ..store import Conflict, Journal
from .protocol import Digest, Identifier, StrictModel, Text, digest
from .trust import SignedEnvelope, TrustRegistry

KEY = "@flywheel-costs:v1"
CATEGORIES = {"model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"}


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


class CostLedger:
    """Use the existing atomic journal and configured accounting authority."""

    def __init__(self, journal: Journal, trust: TrustRegistry) -> None:
        self.journal, self.trust = journal, trust
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
        return self.journal.document(self.journal.latest(KEY, cx))

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
            if old:
                if old != binding:
                    raise Conflict("accounting operation identity already has different terms")
                return state
            if len(state["operations"]) >= 4096:
                raise Conflict("accounting capacity reached; preserve history")
            action, record = payload["action"], payload["record"]
            if action == "charge":
                charge = Charge.model_validate(record)
                if charge.activity_id in state["charges"]:
                    raise Conflict("activity already charged; A, B and C cannot overlap")
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
                state["charges"][charge.activity_id] = {
                    **charge.model_dump(),
                    "signed": signed.model_dump(),
                    "original": previous,
                }
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
                if action == "collection" and any(
                    row["evidence_digest"] == record["evidence_digest"] for row in state["receipts"].values()
                ):
                    raise Conflict("collection evidence already credited")
                state[target][record["record_id"]] = {**record, "kind": action, "signed": signed.model_dump()}
            elif action == "reserve":
                if type(record) is not int or not 0 <= record <= 10**15:
                    raise ValueError("reserve requires nonnegative integer USD micro-units")
                state["reserve_micro_usd"] = record
            elif action in {"seal", "seal-reuse", "seal-retention"}:
                if (
                    not isinstance(record, dict)
                    or set(record) != {"mission_id", "evidence_digest", "categories"}
                    or set(record["categories"]) != CATEGORIES
                ):
                    raise ValueError("complete delivery seal must cover every resource category")
                mission = record["mission_id"]
                seals = state["seals"] if action == "seal" else state.setdefault("reuse_seals", {})
                if mission in seals:
                    raise Conflict("delivery costs already sealed")
                rows = [
                    r
                    for r in state["charges"].values()
                    if r["mission_id"] == mission and r["bucket"] == ("A" if action == "seal" else "B")
                ]
                if {r["category"] for r in rows} != CATEGORIES or any(r["accrued_micro_usd"] is None for r in rows):
                    raise ValueError("missing or unknown delivery costs prevent a complete-cost claim")
                seals[mission] = {**record, "signed": signed.model_dump()}
            else:
                raise ValueError("unsupported accounting action")
            state["operations"][operation_id] = binding
            self.journal.append(cx, KEY, state)
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
        obligations = sum((r["accrued_micro_usd"] or 0) - r["paid_micro_usd"] for r in all_rows)
        unknown = any(r["accrued_micro_usd"] is None for r in all_rows)
        mission_ids = {r["mission_id"] for r in rows if r["bucket"] == "A"}
        sealed = {*state["seals"], *state.get("reuse_seals", {})}
        complete = not any(r["accrued_micro_usd"] is None for r in rows) and (
            mission_id in sealed if mission_id else bool(mission_ids) and mission_ids <= sealed
        )
        return {
            "currency": "USD",
            "unit": "micro_usd",
            "costs": totals,
            "collected_revenue": collected,
            "delivery_profit": collected - totals["A"] if complete else None,
            "complete_cost_profit": collected - sum(totals.values()) if complete else None,
            "cash": capital + all_collected - paid,
            "obligations": obligations,
            "reserve": state["reserve_micro_usd"],
            "available_funds": None
            if unknown
            else capital + all_collected - paid - obligations - state["reserve_micro_usd"],
            "complete": complete,
            "unknown_costs": unknown,
            "token_movements_included": False,
            "evidence_basis": "configured accounting signer attestations",
        }


class IdentifierModel(StrictModel):
    record_id: Identifier
    mission_id: Identifier
    amount_micro_usd: int = Field(ge=0, le=10**15)
    evidence_digest: Digest
