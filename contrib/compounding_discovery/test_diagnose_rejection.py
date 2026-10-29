# SPDX-License-Identifier: Apache-2.0
"""Verify read-only diagnostic capture without modifying the frozen implementation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any

import pytest

from contrib.compounding_discovery import diagnose_rejection as diagnostic


def test_trace_preserves_inner_failed_artifact_and_restores_previous_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    target = json.loads(Path(__file__).with_name("base-target.json").read_text())
    artifact = {
        "schema": "agialpha/eadarp-certificate/v1",
        "task_hash": diagnostic.digest(target),
        "status": "UNRESOLVED",
        "vehicles": [],
        "objective": "0",
        "witness": {},
        "scope": "declared-eADARP-linear-model-only",
    }
    memory = diagnostic.engine.empty_memory()
    record = {
        "request": {"target": target},
        "memory_version": diagnostic.digest(memory),
        "accepted": False,
        "result": {"memory_before_hash": memory["memory_hash"], "result_hash": "original-fixture-identity"},
    }
    original = copy.deepcopy(record)

    def fixture_failure(request: dict[str, Any], memory: dict[str, Any]) -> None:
        candidates = [
            {
                "program": {"op": "per-vehicle-lp", "method": "highs", "presolve": True},
                "artifact": copy.deepcopy(artifact),
            }
        ]
        assert candidates[0]["artifact"]["status"] == "UNRESOLVED"
        raise ValueError("authored diagnostic regression fixture")

    monkeypatch.setattr(diagnostic.engine, "execute", fixture_failure)
    previous = sys.gettrace()
    replay = diagnostic.replay(record, memory)
    assert sys.gettrace() is previous
    assert record == original
    assert replay["new_replay_outcome"]["accepted"] is False
    assert replay["new_exception_traces"][-1]["locals"]["candidates"][0]["artifact"] == artifact
    assert replay["new_independent_candidate_checks"][0]["independent_acceptance"]["accepted"] is False
    assert "not recovered" in replay["scope"]
