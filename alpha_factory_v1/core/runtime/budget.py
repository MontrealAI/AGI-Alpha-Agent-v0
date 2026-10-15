# SPDX-License-Identifier: Apache-2.0
"""Single-journal planning reservations. No wallet custody or transfer authority."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .models import StrictModel
from .store import Conflict, Journal, canonical, digest


MAX_HISTORY_BYTES = 64 * 1024 * 1024
TERMINAL_GROWTH_BYTES = 3000
EVENT_OVERHEAD_BYTES = 1024


class BudgetScope(StrictModel):
    """One operator-declared owner, chain and token, shared by every session."""

    owner: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    chain_id: int = Field(ge=1, le=2**53 - 1)
    token: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")


class BudgetCommand(StrictModel):
    """Exact-unit operation with optimistic concurrency and durable retry identity."""

    scope: BudgetScope
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    action: Literal["set_limit", "reserve", "release", "commit"]
    expected_revision: int = Field(ge=0)
    reservation_id: str = Field(default="", pattern=r"^[a-zA-Z0-9_-]{0,64}$")
    amount: str = Field(default="0", pattern=r"^(0|[1-9][0-9]{0,77})$")
    purpose: str = Field(min_length=1, max_length=500)


def _scope(scope: BudgetScope) -> dict[str, Any]:
    value = scope.model_dump()
    value["owner"] = value["owner"].lower()
    value["token"] = value["token"].lower()
    if value["owner"] == "0x" + "0" * 40 or value["token"] == "0x" + "0" * 40:
        raise ValueError("Owner and token must be nonzero addresses")
    return value


def _key(scope: dict[str, Any]) -> str:
    return "@budget:" + digest(scope)


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    reservations = record["reservations"]
    reserved = sum(int(r["amount"]) for r in reservations.values() if r["state"] == "reserved")
    committed = sum(int(r["amount"]) for r in reservations.values() if r["state"] == "committed")
    return {
        **{k: v for k, v in record.items() if k != "requests"},
        "reserved": str(reserved),
        "committed": str(committed),
        "available": str(int(record["limit"]) - reserved - committed),
        "authority": "planning-only",
        "wallet_balance_verified": False,
        "external_transfers_prevented": False,
    }


def inspect(journal: Journal, scope: BudgetScope) -> dict[str, Any]:
    """Read retained state; a cached response never authorizes a new reservation."""
    return _summary(journal.latest(_key(_scope(scope))))


def operate(journal: Journal, command: BudgetCommand) -> dict[str, Any]:
    """Serialize check and append in one durable transaction across native processes.

    No automatic expiry: a crash or lost response retains its reservation. The
    operator must reconcile uncertain effects before explicitly releasing it.
    Committed amounts remain charged to this cumulative planning ceiling.
    """
    scope = _scope(command.scope)
    key = _key(scope)
    amount = int(command.amount)
    if amount > 2**256 - 1:
        raise ValueError("Amount exceeds uint256")
    if command.action == "set_limit":
        if command.reservation_id:
            raise ValueError("Limit changes cannot name a reservation")
    elif not command.reservation_id:
        raise ValueError("A reservation identity is required")
    if command.action == "reserve" and amount == 0:
        raise ValueError("Reservation must be positive")
    if command.action in {"release", "commit"} and amount != 0:
        raise ValueError("Terminal operations use the exact retained amount")
    payload = {**command.model_dump(), "scope": scope}
    request_hash = digest(payload)
    with journal.transaction() as cx:
        try:
            record = journal.latest(key, cx)
        except KeyError:
            if command.action != "set_limit" or command.expected_revision != 0:
                raise Conflict("Initialize this exact budget before reserving") from None
            record = {"scope": scope, "limit": "0", "reservations": {}, "requests": {}, "revision": 0}
        prior = record["requests"].get(command.request_id)
        if prior is not None:
            if prior != request_hash:
                raise Conflict("Request identity already binds different terms")
            return {**_summary(record), "replayed": True}
        if command.expected_revision != record["revision"]:
            raise Conflict("Budget changed; inspect it before authorizing new terms")
        reservations = record["reservations"]
        active = sum(reservation["state"] == "reserved" for reservation in reservations.values())
        next_active = active + (
            1 if command.action == "reserve" else -1 if command.action in {"release", "commit"} else 0
        )
        # Retain one terminal-operation slot per active reservation. Capacity
        # exhaustion must never strand an otherwise valid reconciliation.
        if len(record["requests"]) + 1 + max(0, next_active) > 4096:
            raise Conflict("Budget request retention limit reached; preserve history and reconcile active reservations")
        if command.action == "set_limit":
            summary = _summary(record)
            if amount < int(summary["reserved"]) + int(summary["committed"]):
                raise Conflict("Limit cannot fall below retained obligations")
            record["limit"] = command.amount
        elif command.action == "reserve":
            if command.reservation_id in reservations:
                raise Conflict("Reservation identity cannot be reused")
            if len(reservations) >= 1024:
                raise Conflict("Reservation retention limit reached")
            if amount > int(_summary(record)["available"]):
                raise Conflict("Insufficient unallocated planning budget")
            reservations[command.reservation_id] = {
                "amount": command.amount,
                "purpose": command.purpose,
                "state": "reserved",
            }
        else:
            reservation = reservations.get(command.reservation_id)
            if reservation is None or reservation["state"] != "reserved":
                raise Conflict("Only a retained active reservation can be reconciled")
            reservation["state"] = "released" if command.action == "release" else "committed"
            reservation["reconciliation"] = command.purpose
        record["requests"][command.request_id] = request_hash
        document = Journal.document(record)
        event_bound = len(canonical(document)) + EVENT_OVERHEAD_BYTES
        retained = cx.execute(
            "SELECT COALESCE(SUM(length(CAST(body AS BLOB)) + 512), 0) FROM events WHERE mission=?", (key,)
        ).fetchone()[0]
        # Each future terminal response may add a 500-character Unicode reason
        # and one retry identity. Reserve a conservative full-snapshot bound for
        # every active obligation, so a size ceiling cannot strand reconciliation.
        terminal_headroom = max(0, next_active) * (event_bound + max(0, next_active) * TERMINAL_GROWTH_BYTES)
        if retained + event_bound + terminal_headroom > MAX_HISTORY_BYTES:
            raise Conflict("Budget history byte limit reached; reconcile active reservations and preserve history")
        return {**_summary(journal.append(cx, key, Journal.document(record))), "replayed": False}
