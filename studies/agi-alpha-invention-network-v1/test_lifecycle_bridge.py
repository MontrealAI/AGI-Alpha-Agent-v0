# SPDX-License-Identifier: Apache-2.0
"""Boundary tests for the unchanged lifecycle and signed-cost bridge."""

import hashlib
import json
from pathlib import Path

import pytest

from lifecycle_bridge import native_source_manifest, replay_native_costs, run_lifecycle, verify_upstream


def candidate(path: Path, **changes: object) -> dict:
    values = {
        "id": "thermal-basis",
        "version": 1,
        "artifact_path": str(path),
        "shared": True,
        "paired_trials": [
            {
                "probeId": f"fresh-{i}",
                "clusterId": f"mission-{i}",
                "fresh": True,
                "baseline": {"netMissionValueCents": 0},
                "candidate": {"netMissionValueCents": 500},
            }
            for i in range(8)
        ],
        "lifecycle_cost_cents": 100,
        "evaluation_cost_cents": 50,
        "forecast_uses": 10,
        "correctness_passed": True,
        "replay_available": True,
        "boundary_passed": True,
        "week": 0,
        "expiry": 100,
    }
    return {**values, **changes}


def artifact(tmp_path: Path) -> Path:
    path = tmp_path / "basis.json"
    path.write_text(json.dumps({"basis": [[1, 0], [0, 1]], "scope": "local diffusion"}))
    return path


def test_exact_upstream_and_local_artifact_transfer(tmp_path: Path) -> None:
    path = artifact(tmp_path)
    result = run_lifecycle([candidate(path)], operations=[{"action": "execute", "key": "thermal-basis@1", "week": 1}])
    assert len(verify_upstream()["files"]) == 11
    assert result["candidates"][0]["state"]["status"] == "ADMITTED"
    transfer = result["operations"][0]["result"]
    assert transfer["ok"] and transfer["actualExecution"] is False
    assert transfer["transferredArtifact"]["content"] == path.read_text()
    assert transfer["transferredArtifact"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["liveCapsuleAdmission"] == "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE"
    assert result["snapshot"]["authorityMode"] == "FIXTURE_ONLY"


def test_private_rights_keep_peer_unavailable(tmp_path: Path) -> None:
    result = run_lifecycle(
        [candidate(artifact(tmp_path), shared=False)],
        operations=[
            {"action": "execute", "key": "thermal-basis@1", "member": "lyra.agent.agi.eth", "week": 1},
            {"action": "execute", "key": "thermal-basis@1", "member": "atlas.agent.agi.eth", "week": 1},
        ],
    )
    assert not result["operations"][0]["result"]["ok"]
    assert "RIGHT_NOT_GRANTED" in result["operations"][0]["result"]["reasons"]
    assert result["operations"][1]["result"]["ok"]


def test_negative_economic_evidence_does_not_admit(tmp_path: Path) -> None:
    result = run_lifecycle([candidate(artifact(tmp_path), lifecycle_cost_cents=100_000)])
    row = result["candidates"][0]
    assert row["state"]["status"] == "REJECTED"
    assert row["admission"] is None
    assert row["assessment"]["verdict"] == "reject"


def test_protected_material_cannot_be_transferred(tmp_path: Path) -> None:
    path = tmp_path / "leaky.json"
    path.write_text('{"value":"secret-independent-evaluation-value"}')
    result = run_lifecycle([candidate(path)], protected_material=["secret-independent-evaluation-value"])
    assert "PROTECTED" in result["candidates"][0]["error"]
    assert not result["snapshot"]["records"]


def test_frozen_bytes_and_declared_evidence_are_required(tmp_path: Path) -> None:
    path = artifact(tmp_path)
    with pytest.raises(ValueError, match="frozen scientific artifact bytes changed"):
        run_lifecycle([candidate(path, expected_artifact_sha256="0" * 64)])
    result = run_lifecycle([candidate(path, replay_available=False)])
    assert "EVIDENCE_GATE_FAILED" in result["candidates"][0]["error"]


def test_direct_names_and_network_wide_rights_are_enforced(tmp_path: Path) -> None:
    path = artifact(tmp_path)
    invalid = run_lifecycle([candidate(path, owner="nested.atlas.agent.agi.eth")])
    assert "INVALID_CANDIDATE_IDENTITY" in invalid["candidates"][0]["error"]
    rights = {
        "shareable": True,
        "retrieve": ["atlas.agent.agi.eth"],
        "execute": "network",
        "compose": "network",
        "export": False,
    }
    restricted = run_lifecycle([candidate(path, rights=rights)])
    assert "SHAREABLE_REQUIRES_NETWORK_AVAILABILITY" in restricted["candidates"][0]["error"]


def test_revocation_and_stronger_beta_refuse_future_reuse(tmp_path: Path) -> None:
    path = artifact(tmp_path)
    result = run_lifecycle(
        [candidate(path)],
        operations=[
            {"action": "revoke", "key": "thermal-basis@1", "week": 1},
            {"action": "execute", "key": "thermal-basis@1", "week": 2},
        ],
    )
    assert result["operations"][0]["result"]["ok"]
    assert not result["operations"][1]["result"]["ok"]
    assert result["snapshot"]["records"][0]["status"] == "REVOKED"
    updated = run_lifecycle(
        [candidate(path)],
        operations=[
            {"action": "beta-update", "beta_version": "improved-technical-beta-v2", "week": 1},
            {"action": "execute", "key": "thermal-basis@1", "week": 2},
        ],
    )
    assert not updated["operations"][1]["result"]["ok"]


def test_duplicate_version_and_exposed_probes_are_retained_as_failures(tmp_path: Path) -> None:
    path = artifact(tmp_path)
    duplicate = run_lifecycle([candidate(path), candidate(path)])
    assert "VERSION_ALREADY_EXISTS" in duplicate["candidates"][1]["error"]
    changed = tmp_path / "basis-v2.json"
    changed.write_text('{"basis":[[1,0]],"different":true}')
    reused = run_lifecycle([candidate(path), candidate(changed, version=2)])
    assert reused["candidates"][1]["state"]["status"] == "REJECTED"
    assert "PREVIOUS_EVALUATION_CANNOT_BE_RELABELED_FRESH" in reused["candidates"][1]["assessed"]["reasons"]


def charges() -> list[dict]:
    categories = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]
    return [
        {
            "activity_id": f"cost-{i}",
            "mission_id": "thermal-delivery",
            "bucket": "A",
            "category": category,
            "accrued_micro_usd": 100,
            "paid_micro_usd": 100,
        }
        for i, category in enumerate(categories)
    ]


def test_native_ledger_separates_seed_profit_cash_reserves() -> None:
    result = replay_native_costs(
        charges(),
        collections=[{"record_id": "sale", "mission_id": "thermal-delivery", "amount_micro_usd": 2000}],
        capital_micro_usd=10000,
        reserve_micro_usd=1000,
    )
    report = result["report"]
    assert report["complete"]
    assert report["complete_cost_profit"] == 1100
    assert report["collected_revenue"] == 2000
    assert report["cash"] == 11100 and report["available_funds"] == 10100
    assert result["verified_journal"]["valid"]
    assert result["actual_collections_micro_usd"] == 0
    assert any(x["path"].endswith("flywheel_costs.py") for x in native_source_manifest()["files"])


def test_unknown_cost_blocks_complete_profit_and_available_funds() -> None:
    rows = charges()
    rows[0]["accrued_micro_usd"] = None
    rows[0]["paid_micro_usd"] = 0
    result = replay_native_costs(rows, capital_micro_usd=10000)
    assert result["report"]["complete_cost_profit"] is None
    assert result["report"]["available_funds"] is None
    assert not result["report"]["complete"]


def test_same_activity_cannot_be_double_charged_between_buckets() -> None:
    rows = charges()
    rows.append({**rows[0], "bucket": "B"})
    with pytest.raises(Exception, match="A, B and C cannot overlap"):
        replay_native_costs(rows)
