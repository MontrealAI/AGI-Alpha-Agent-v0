# SPDX-License-Identifier: Apache-2.0
"""Authenticated, explicit operator actions for the separate supplier laboratory."""
from __future__ import annotations

import base64
from typing import Any, Literal
from pydantic import Field, field_validator

from . import supplier_browser as adapter
from .models import StrictModel
from .store import Journal


class Binding(StrictModel):
    binding: str = Field(pattern=r"^@supplier-browser:[0-9a-f]{64}$")


class Confirmation(StrictModel):
    confirm: Literal[True]

    @field_validator("confirm", mode="before")
    @classmethod
    def exact_confirmation(cls, value: Any) -> bool:
        if value is not True:
            raise ValueError("Explicit true confirmation required")
        return value


class Confirmed(Binding, Confirmation):
    pass


class Admission(Confirmation):
    spec_base64: str = Field(max_length=85_336)
    job_id: str = Field(pattern=r"^[1-9][0-9]{0,77}$")
    worker: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    assignment_tx: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    confirm: Literal[True]


class Execute(Confirmed):
    permit: str = Field(pattern=r"^[0-9a-f]{64}$")


class Reconcile(Confirmed):
    revision: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=2000)


class Review(Reconcile):
    result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    approve: bool


def status(journal: Journal) -> dict[str, Any]:
    journal.verify()
    profiles = {}
    for name, loader in (("market", adapter.ecosystem.installed_profile), ("executor", adapter.installed_executor)):
        try:
            profiles[name] = loader(journal).model_dump(by_alias=True)
        except (ValueError, OSError):
            profiles[name] = None
    with journal.transaction() as cx:
        ids = [
            row[0]
            for row in cx.execute(
                "SELECT mission,MAX(seq) FROM events WHERE mission LIKE '@supplier-browser:%' "
                "GROUP BY mission ORDER BY MAX(seq) DESC LIMIT 100"
            )
        ]
        records = []
        for key in ids:
            record = journal.latest(key, cx)
            records.append(
                {
                    "binding": key,
                    "job_id": record["observation"]["job_id"],
                    "state": record["state"],
                    "attempt_id": record.get("attempt_id"),
                    "revision": record["revision"],
                }
            )
    return {
        "identity": journal.identity,
        "profiles": profiles,
        "records": records,
        "control": journal.latest("@control")["state"],
        "scope": "synthetic-laboratory",
        "production_ready": False,
        "provider_cost": "UNKNOWN",
        "qualification": "Docker isolation and live provider commissioning require separate evidence",
    }


def operate(journal: Journal, action: str, document: dict[str, Any]) -> dict[str, Any]:
    if action == "admit":
        value = Admission.model_validate(document)
        return adapter.admit(
            journal, base64.b64decode(value.spec_base64, validate=True), value.job_id, value.worker, value.assignment_tx
        )
    if action == "execute":
        value = Execute.model_validate(document)
        return adapter.execute(journal, value.binding, value.permit)
    if action == "review":
        value = Review.model_validate(document)
        return adapter.review(journal, value.binding, value.revision, value.result_hash, value.approve, value.note)
    if action == "reconcile":
        value = Reconcile.model_validate(document)
        return adapter.reconcile(journal, value.binding, value.revision, value.confirm, value.note)
    if action == "stop":
        value = Confirmed.model_validate(document)
        return adapter.stop(journal, value.binding)
    value = Binding.model_validate(document)
    if action == "show":
        journal.verify()
        # Retained evidence remains inspectable when host configuration is unavailable.
        return journal.latest(value.binding)
    if action == "prepare":
        return adapter.prepare(journal, value.binding)
    if action == "export":
        return adapter.delivery(journal, value.binding)
    raise ValueError("Unknown supplier-browser operation")
