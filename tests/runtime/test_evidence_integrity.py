# SPDX-License-Identifier: Apache-2.0
"""Reject well-signed but internally inconsistent evidence and lossy numeric values."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime import ascension
from alpha_factory_v1.core.runtime import work
from alpha_factory_v1.core.runtime.engine import Engine, verify_export
from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.store import Journal, canonical, digest
from alpha_factory_v1.core.runtime.work import verify_result


def allocation() -> Mission:
    return Mission.model_validate(
        {
            "goal": "Select the single feasible project",
            "work": {"kind": "allocation", "budget": 1, "items": [{"id": "A", "cost": 1, "value": 1}]},
        }
    )


def resign(artifact: dict[str, Any], journal: Journal) -> None:
    receipt = artifact["receipt"]
    receipt["canonical_result"] = canonical(receipt["body"]["document"]["result"]).decode()
    receipt["canonical_body"] = canonical(receipt["body"]).decode()
    receipt["hash"] = digest(receipt["body"])
    receipt["signature"] = base64.b64encode(journal.key.sign(bytes.fromhex(receipt["hash"]))).decode()


@pytest.fixture
def approved(tmp_path: Path) -> tuple[Journal, Engine, str]:
    journal = Journal.initialize(tmp_path / "state")
    engine = Engine(journal)
    record = engine.execute(journal.submit(allocation())["id"])
    engine.review(record["id"], record["revision"], digest(record["result"]), True, "Checked the input and totals.")
    return journal, engine, record["id"]


@pytest.mark.parametrize("problem", ["rejected", "numeric-approval", "text-approval", "schema"])
def test_valid_signature_does_not_authorize_a_contradictory_receipt(approved, problem: str) -> None:
    journal, engine, ident = approved
    artifact = engine.export(ident)
    assert verify_export(artifact, journal.public)["valid"]
    document = artifact["receipt"]["body"]["document"]
    if problem == "schema":
        artifact["schema"] = True
    else:
        document["review"]["approved"] = {"rejected": False, "numeric-approval": 1, "text-approval": "true"}[problem]
    resign(artifact, journal)
    with pytest.raises(ValueError, match="schema|approved intact result"):
        verify_export(artifact, journal.public)


@pytest.mark.parametrize("field", ["cost", "value", "risk"])
@pytest.mark.parametrize("numeric", ["boolean", "float"])
def test_allocation_rejects_python_equal_but_noninteger_totals(field: str, numeric: str) -> None:
    result = {"selected": ["A"], "cost": 1, "value": 1, "risk": 0}
    assert verify_result(allocation(), result)["passed"]
    result[field] = bool(result[field]) if numeric == "boolean" else float(result[field])
    with pytest.raises(ValueError, match="integers"):
        verify_result(allocation(), result)


@pytest.mark.parametrize("field", ["operation", "makespan", "tardiness"])
@pytest.mark.parametrize("numeric", ["boolean", "float"])
def test_schedule_rejects_numeric_aliases(field: str, numeric: str) -> None:
    mission = Mission.model_validate(
        {
            "goal": "Schedule one operation",
            "work": {
                "kind": "schedule",
                "jobs": [{"id": "A", "due": 1, "operations": [{"machine": "M", "duration": 1}]}],
            },
        }
    )
    result = {
        "operations": [{"job": "A", "operation": 0, "machine": "M", "start": 0, "end": 1}],
        "makespan": 1,
        "tardiness": 0,
    }
    assert verify_result(mission, result)["passed"]
    target = result["operations"][0] if field == "operation" else result
    target[field] = bool(target[field]) if numeric == "boolean" else float(target[field])
    with pytest.raises(ValueError, match="integers"):
        verify_result(mission, result)


@pytest.mark.parametrize("field,value", [("case_count", True), ("case_count", 1.0), ("accuracy", True)])
def test_code_rejects_numeric_aliases_before_execution(monkeypatch, field: str, value: object) -> None:
    mission = Mission.model_validate(
        {
            "goal": "Evaluate the supplied function",
            "work": {"kind": "code", "candidate": "def solve(): return 1", "heldout": [{"args": [], "expected": 1}]},
        }
    )
    result = {"case_count": 1, "accuracy": 1.0, field: value}
    monkeypatch.setattr(work, "coding", lambda *args: pytest.fail("Invalid evidence must not execute code"))
    with pytest.raises(ValueError, match="numeric"):
        verify_result(mission, result)


def test_ascension_replays_signed_numeric_evidence_instead_of_accepting_signature_alone(approved) -> None:
    journal, engine, ident = approved
    plan = ascension.compile_plan(
        [
            {
                "goal": allocation().goal,
                "successMetric": "Replay exact integer totals",
                "bounty": "100",
                "duration": 1,
                "priceWeight": 6000,
            }
        ]
    )
    envelope = json.loads(ascension.delivery(journal, plan, 0, ident))
    artifact = envelope["body"]["nativeExport"]
    document = artifact["receipt"]["body"]["document"]
    document["result"]["cost"] = True
    document["review"]["result_hash"] = digest(document["result"])
    resign(artifact, journal)
    envelope["signature"] = base64.b64encode(
        journal.key.sign(hashlib.sha256(canonical(envelope["body"])).digest())
    ).decode()
    assert verify_export(artifact, journal.public)["valid"]
    with pytest.raises(ValueError, match="integers"):
        ascension.verify_delivery(canonical(envelope), journal.public, plan["planRoot"])
