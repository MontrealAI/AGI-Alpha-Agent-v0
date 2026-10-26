# SPDX-License-Identifier: Apache-2.0
"""The importer refuses forged material conclusions and preserves original evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from contrib.upgrade_decision.component import assess, validate, verifier
from contrib.upgrade_decision.core import load, mission_key, sha
from contrib.upgrade_decision.delivery import markdown, render_html

HERE = Path(__file__).resolve().parent


def packet() -> dict[str, Any]:
    return load((HERE / "examples/native-component.json").read_bytes())


def replace_file(pack: dict[str, Any], name: str, value: dict[str, Any]) -> None:
    text = json.dumps(value, indent=2) + "\n"
    pack["files"][name] = {"text": text, "sha256": sha(text.encode())}
    manifest = json.loads(pack["files"]["artifact-manifest.json"]["text"])
    for row in manifest["files"]:
        if row["path"] == name:
            row.update(sha256=sha(text.encode()), bytes=len(text.encode()))
    text = json.dumps(manifest, indent=2) + "\n"
    pack["files"]["artifact-manifest.json"] = {"text": text, "sha256": sha(text.encode())}


def test_complete_native_component_packet_rechecks_61_each_side() -> None:
    pack = packet()
    result = assess(pack)
    assert result["nextAction"] == "ADVANCE_COMPONENT_KEEP_LOCK"
    assert result["engineeringAcceptance"] and result["customerAcceptance"] == "unknown"
    assert [check["result"]["counts"]["PASS"] for check in result["componentChecks"]] == [61, 61]
    assert "Keep the current native application lock" in markdown(result, "en")
    assert "Conservez le verrou" in markdown(result, "fr")
    assert "Inconnu" in render_html(result) and "Unknown" in render_html(result)
    assert result["componentDecision"] == json.loads(pack["files"]["decision.json"]["text"])


def test_incomplete_observations_cannot_be_promoted_even_with_a_new_envelope_hash() -> None:
    pack = packet()
    value = json.loads(pack["files"]["evidence/target-observations.json"]["text"])
    value["observations"].pop()
    replace_file(pack, "evidence/target-observations.json", value)
    with pytest.raises(ValueError):
        assess(pack)


def test_changed_oracle_or_source_refuses() -> None:
    pack = packet()
    pack["files"]["evidence/verify_component.py"]["text"] += "\n# changed source\n"
    with pytest.raises(ValueError):
        assess(pack)


def test_false_positive_decision_does_not_override_verified_evidence() -> None:
    pack = packet()
    decision = json.loads(pack["files"]["decision.json"]["text"])
    decision["coverage"]["after_pass"] = 62
    replace_file(pack, "decision.json", decision)
    with pytest.raises(ValueError, match="summary"):
        assess(pack)


def test_replaced_dependency_tuple_refuses() -> None:
    pack = packet()
    decision = json.loads(pack["files"]["decision.json"]["text"])
    decision["after_versions"]["starlette"] = "unexamined"
    replace_file(pack, "decision.json", decision)
    with pytest.raises(ValueError, match="dependency profile"):
        assess(pack)


def test_native_mission_identity_ignores_replays_but_binds_real_input_changes() -> None:
    original = packet()
    repeated = packet()
    repeated["title"] = "Another export"
    value = json.loads(repeated["files"]["decision.json"]["text"])
    value["created_at"] = "another observation time"
    replace_file(repeated, "decision.json", value)
    assert mission_key(original) == mission_key(repeated)
    value["after_versions"]["starlette"] = "1.11.0"
    replace_file(repeated, "decision.json", value)
    assert mission_key(original) != mission_key(repeated)


def test_synthetic_substantiated_regression_returns_useful_hold_not_preservation() -> None:
    pack = packet()
    original_key = mission_key(pack)
    raw = json.loads(pack["files"]["evidence/target-observations.json"]["text"])
    raw["observations"][0]["observation"]["status"] = 400
    replace_file(pack, "evidence/target-observations.json", raw)
    contract = json.loads(pack["files"]["evidence/component-contract.json"]["text"])
    saved = json.loads(pack["files"]["evidence/target-verification.json"]["text"])
    saved["observations_sha256"] = pack["files"]["evidence/target-observations.json"]["sha256"]
    saved["cases"][0] = verifier.verify_case(contract["cases"][0], raw["observations"][0], contract["security_headers"])
    saved["status"] = "BEHAVIOR_MISMATCH"
    saved["counts"] = {"PASS": 60, "BEHAVIOR_MISMATCH": 1, "INCOMPLETE": 0}
    replace_file(pack, "evidence/target-verification.json", saved)
    decision = json.loads(pack["files"]["decision.json"]["text"])
    decision.update(decision="COMPONENT_REGRESSION", phase="synthetic-handler-control", accepted_properties=[])
    decision["coverage"]["after_pass"] = 60
    decision["limits"].append(
        "Synthetic handler control, not an observed regression, customer job or confirmation result."
    )
    for entry in decision["evidence"]:
        item = pack["files"][entry["package_path"]]
        entry.update(sha256=item["sha256"], bytes=len(item["text"].encode()))
    replace_file(pack, "decision.json", decision)
    result = assess(pack)
    assert result["nextAction"] == "HOLD_COMPONENT_AND_INVESTIGATE"
    assert result["engineeringAcceptance"] and result["customerAcceptance"] == "unknown"
    assert result["componentChecks"][1]["result"]["counts"]["BEHAVIOR_MISMATCH"] == 1
    assert result["missionKey"] == original_key
    assert "Hold this refresh" in markdown(result, "en") and "60 / 61" in render_html(result)
    assert "All 61 declared requirements passed" not in markdown(result, "en")


def test_unsafe_links_and_unmanifested_files_refuse() -> None:
    pack = packet()
    decision = json.loads(pack["files"]["decision.json"]["text"])
    decision["source_urls"][0] = "javascript:alert(1)"
    replace_file(pack, "decision.json", decision)
    with pytest.raises(ValueError):
        validate(pack)
    pack = packet()
    pack["files"]["../extra.py"] = {"text": "x", "sha256": sha(b"x")}
    with pytest.raises(ValueError):
        validate(pack)
