# SPDX-License-Identifier: Apache-2.0
"""Small authenticated operator facade for explicit Jobs v0 work handoffs."""
from __future__ import annotations

import base64
from typing import Any, Literal
from pydantic import Field

from . import ecosystem
from .engine import Engine
from .models import StrictModel
from .store import Journal, digest


class Admission(StrictModel):
    spec_base64: str = Field(max_length=700_000)
    job_id: str = Field(pattern=r"^[1-9][0-9]{0,77}$")
    worker: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    assignment_tx: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    confirm: Literal[True]


class Binding(StrictModel):
    binding: str = Field(pattern=r"^@ecosystem:[0-9a-f]{64}$")


class Execute(Binding):
    confirm: Literal[True]


class Review(Execute):
    revision: int = Field(ge=1)
    result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    approve: bool
    note: str = Field(min_length=1, max_length=2000)


def status(journal: Journal) -> dict[str, Any]:
    """Configuration is distinct from fresh chain verification and production readiness."""
    try:
        profile = ecosystem.installed_profile(journal)
        selected = {
            "backend": profile.backend,
            "chain_id": profile.chain_id,
            "scope": profile.scope,
            "source_commit": profile.source_commit,
            "registry": profile.contracts["registry"].address,
            "token": profile.contracts["token"].address,
            "decimals": 18,
        }
    except (ValueError, OSError):
        selected = None
    with journal.transaction() as cx:
        ids = [
            row[0]
            for row in cx.execute(
                "SELECT mission,MAX(seq) FROM events WHERE mission LIKE '@ecosystem:%' GROUP BY mission ORDER BY MAX(seq) DESC LIMIT 100"
            )
        ]
        records = []
        for ident in ids:
            item = journal.latest(ident, cx)
            mission = journal.latest(item["mission_id"], cx)
            records.append(
                {
                    "binding": ident,
                    "job_id": item["observation"]["job_id"],
                    "state": mission["state"],
                    "goal": mission["request"]["goal"],
                }
            )
    return {
        "identity": journal.identity,
        "profile": selected,
        "records": records,
        "control": journal.latest("@control")["state"],
        "production_ready": False,
        "native_adapter": "installed; fresh assignment checks required",
        "fleet_adapter": "separate qualification required",
    }


def operate(journal: Journal, action: str, document: dict[str, Any]) -> dict[str, Any]:
    """No work file can install a profile or mint new native/market authority."""
    if action == "admit":
        value = Admission.model_validate(document)
        raw = base64.b64decode(value.spec_base64, validate=True)
        return ecosystem.admit(journal, raw, value.job_id, value.worker, value.assignment_tx)
    if action == "execute":
        run = Execute.model_validate(document)
        return ecosystem.execute(journal, run.binding)
    if action == "review":
        review = Review.model_validate(document)
        record = journal.latest(review.binding)
        return Engine(journal).review(
            record["mission_id"], review.revision, review.result_hash, review.approve, review.note
        )
    value_binding = Binding.model_validate(document)
    if action == "show":
        record = journal.latest(value_binding.binding)
        mission = journal.latest(record["mission_id"])
        return {
            "binding": record,
            "mission": {**mission, "result_hash": digest(mission["result"]) if "result" in mission else None},
        }
    if action == "export":
        return ecosystem.delivery(journal, value_binding.binding)
    raise ValueError("Unknown ecosystem operation")
