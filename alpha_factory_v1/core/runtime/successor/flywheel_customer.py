# SPDX-License-Identifier: Apache-2.0
"""Customer cash, earned service income and refundable custody on the existing ledger."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .protocol import Digest, Identifier, StrictModel, Text

MODES = ("live", "recorded", "synthetic", "calibrated")


class CustomerDeposit(StrictModel):
    receipt_id: Identifier
    mission_id: Identifier
    amount_micro_usd: int = Field(gt=0, le=10**12)
    purpose: Literal["service", "pass-through"]
    service_price_micro_usd: int = Field(ge=0, le=10**12)
    mode: Literal["live", "recorded", "synthetic", "calibrated"]
    evidence_digest: Digest
    note: Text

    @model_validator(mode="after")
    def allocated(self) -> CustomerDeposit:
        if self.purpose == "service" and not 0 < self.amount_micro_usd <= self.service_price_micro_usd:
            raise ValueError("service deposits require a positive bounded total service price")
        if self.purpose == "pass-through" and self.service_price_micro_usd != 0:
            raise ValueError("pass-through custody has no provider service price")
        return self


class CustomerEarning(StrictModel):
    event_id: Identifier
    receipt_id: Identifier
    amount_micro_usd: int = Field(gt=0, le=10**12)
    delivery_kind: Literal["native", "general"]
    operation_id: Identifier | None
    execution_record_digest: Digest
    acceptance_record_digest: Digest

    @model_validator(mode="after")
    def exact_operation(self) -> CustomerEarning:
        if (self.operation_id is not None) != (self.delivery_kind == "general"):
            raise ValueError("only general delivery uses an explicit execution operation")
        return self


class CustomerRefund(StrictModel):
    event_id: Identifier
    receipt_id: Identifier
    amount_micro_usd: int = Field(gt=0, le=10**12)
    allocation: Literal["unearned", "earned", "pass-through"]
    evidence_digest: Digest
    reason: Text


def balances(row: dict[str, Any]) -> dict[str, int]:
    """Compute disjoint custody and net income without posting another activity."""
    amount = row["terms"]["amount_micro_usd"]
    earned, returned = row["earned_micro_usd"], row["refunded_micro_usd"]
    earned_refund = row["earned_refund_micro_usd"]
    pending_earned = row.get("pending_earned_refund_micro_usd", 0)
    service = row["terms"]["purpose"] == "service"
    unearned = amount - earned - (returned - earned_refund) if service else 0
    return {
        "gross_collections": amount,
        "refunds": returned,
        "net_cash": amount - returned,
        "earned_revenue": earned - earned_refund - pending_earned,
        "unearned_service": unearned,
        "pass_through_custody": amount - returned if not service else 0,
        "customer_obligations": (unearned if service else amount - returned) + pending_earned,
        "pending_refunds": sum(
            row.get("pending_" + allocation + "_refund_micro_usd", 0)
            for allocation in ("unearned", "earned", "pass-through")
        ),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate one evidence mode; callers keep synthetic and live totals separate."""
    result = dict.fromkeys(
        (
            "gross_collections",
            "refunds",
            "net_cash",
            "earned_revenue",
            "unearned_service",
            "pass_through_custody",
            "customer_obligations",
            "pending_refunds",
        ),
        0,
    )
    for row in rows:
        for name, amount in balances(row).items():
            result[name] += amount
    return result
