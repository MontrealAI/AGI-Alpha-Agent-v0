# SPDX-License-Identifier: Apache-2.0
"""The importer refuses forged material conclusions and preserves original evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from contrib.upgrade_decision.component import assess, validate
from contrib.upgrade_decision.core import load, mission_key, sha
from contrib.upgrade_decision.delivery import markdown, render_html

HERE = Path(__file__).resolve().parent


def packet() -> dict[str, Any]:
    return load((HERE / "examples/native-component.json").read_bytes())


def replace_file(pack: dict[str, Any], name: str, value: dict[str, Any] | str) -> None:
    text = value if isinstance(value, str) else json.dumps(value, indent=2) + "\n"
    pack["files"][name] = {"text": text, "sha256": sha(text.encode())}
    manifest = json.loads(pack["files"]["artifact-manifest.json"]["text"])
    for row in manifest["files"]:
        if row["path"] == name:
            row.update(sha256=sha(text.encode()), bytes=len(text.encode()))
    text = json.dumps(manifest, indent=2) + "\n"
    pack["files"]["artifact-manifest.json"] = {"text": text, "sha256": sha(text.encode())}
    # Synthetic controls explicitly update their correction scope. This never
    # refreshes execution identities or silently turns a forged lock into proof.
    correction = json.loads(pack["files"]["correction-receipt.json"]["text"])
    original = correction["original_files"]
    changes = [
        {"path": path, "before_sha256": old, "after_sha256": pack["files"][path]["sha256"]}
        for path, old in original.items()
        if path not in {"artifact-manifest.json", "assembly-receipt.json"}
        and path in pack["files"]
        and old != pack["files"][path]["sha256"]
    ]
    names = {row["path"] for row in changes}
    correction.update(
        changed_content_files=changes,
        corrected_artifact_manifest_sha256=pack["files"]["artifact-manifest.json"]["sha256"],
        behavioral_evidence_changed=any(path.startswith("evidence/") for path in names),
        decision_changed="decision.json" in names,
        method_or_evaluator_changed=bool(
            names
            & {
                "evidence/manual_probe.py",
                "evidence/measured_run.py",
                "evidence/verify_component.py",
                "evidence/component-contract.json",
                "evidence/component-projections.json",
            }
        ),
    )
    text = json.dumps(correction, indent=2) + "\n"
    pack["files"]["correction-receipt.json"] = {"text": text, "sha256": sha(text.encode())}


def refresh_decision_evidence(pack: dict[str, Any]) -> None:
    decision = json.loads(pack["files"]["decision.json"]["text"])
    for entry in decision["evidence"]:
        item = pack["files"][entry["package_path"]]
        entry.update(sha256=item["sha256"], bytes=len(item["text"].encode()))
    replace_file(pack, "decision.json", decision)


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


def test_synthetic_substantiated_regression_returns_useful_hold_not_preservation(tmp_path: Path) -> None:
    pack = packet()
    original_key = mission_key(pack)
    raw = json.loads(pack["files"]["evidence/target-observations.json"]["text"])
    raw["observations"][0]["observation"]["status"] = 400
    replace_file(pack, "evidence/target-observations.json", raw)
    mapping = {
        "evidence/component-contract.json": "protocol/component-contract.json",
        "evidence/component-projections.json": "protocol/component-projections.json",
        "evidence/api.py": "data/consumer/api.py",
        "evidence/models.py": "data/consumer/models.py",
        "evidence/test_api_boundary.py": "discovery/test_api_boundary.py",
        "evidence/target-observations.json": "observations.json",
        "evidence/target-environment.json": "environment.json",
    }
    for packaged, relative in mapping.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(pack["files"][packaged]["text"])
    # Exercise the actual fixed verifier process, not a hand-written PASS exit.
    completed = subprocess.run(
        [
            sys.executable,
            str(HERE / "vendor/verify_component.py"),
            "--contract",
            str(tmp_path / "protocol/component-contract.json"),
            "--consumer",
            str(tmp_path / "data/consumer"),
            "--environment",
            str(tmp_path / "environment.json"),
            "--projection",
            "native-fastapi-bridge-v2",
            "--observations",
            str(tmp_path / "observations.json"),
            "--out",
            str(tmp_path / "verification.json"),
        ],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 2
    saved = json.loads((tmp_path / "verification.json").read_text())
    assert saved["status"] == "BEHAVIOR_MISMATCH" and saved["counts"]["INCOMPLETE"] == 0
    replace_file(pack, "evidence/target-verification.json", saved)
    # This is a fabricated handler fixture, not a new recorded execution. Make
    # all of its relationships coherent so the classification path is exercised.
    for receipt_name in ("evidence/target-execution.json", "evidence/target-verification-execution.json"):
        receipt = json.loads(pack["files"][receipt_name]["text"])
        if receipt_name.endswith("verification-execution.json"):
            receipt.update(exit_code=completed.returncode, complete_success=False)
        for collection in ("input_identities_before", "input_identities_after", "output_identities"):
            for row in receipt[collection]:
                for leaf in ("target-observations.json", "target-verification.json"):
                    if row["path"].endswith("/" + leaf):
                        item = pack["files"]["evidence/" + leaf]
                        row.update(sha256=item["sha256"], bytes=len(item["text"].encode()))
        replace_file(pack, receipt_name, receipt)
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


@pytest.mark.parametrize("name", ["proposed-component-lock.patch", "READ-ME.md", "reproduce.txt"])
def test_self_consistent_reduced_inventory_still_refuses(name: str) -> None:
    pack = packet()
    pack["files"].pop(name)
    manifest = json.loads(pack["files"]["artifact-manifest.json"]["text"])
    manifest["files"] = [row for row in manifest["files"] if row["path"] != name]
    replace_file(pack, "artifact-manifest.json", manifest)
    with pytest.raises(ValueError, match="complete bounded text evidence"):
        assess(pack)


@pytest.mark.parametrize("mutation", ["version", "wheel-hash", "patch", "execution-input", "execution-output"])
def test_rehashed_lock_or_receipt_cannot_override_executed_profile(mutation: str) -> None:
    pack = packet()
    if mutation in {"version", "wheel-hash"}:
        text = pack["files"]["evidence/target.lock"]["text"]
        if mutation == "version":
            text = text.replace("starlette==1.10.0", "starlette==9.9.9")
        else:
            text = text.replace("478c0ab3b4ced6e82719849c118fa406f0278a3499c1a898cd15cd31bdc38ce4", "0" * 64)
        replace_file(pack, "evidence/target.lock", text)
    elif mutation == "patch":
        replace_file(pack, "proposed-component-lock.patch", "unrelated patch\n")
    else:
        value = json.loads(pack["files"]["evidence/target-execution.json"]["text"])
        if mutation == "execution-input":
            for phase in ("input_identities_before", "input_identities_after"):
                value[phase][6]["sha256"] = "0" * 64
        else:
            value["output_identities"][0]["sha256"] = "0" * 64
        replace_file(pack, "evidence/target-execution.json", value)
    refresh_decision_evidence(pack)
    with pytest.raises(ValueError, match="profile|patch|identity"):
        assess(pack)


@pytest.mark.parametrize("mutation", ["manifest", "assembly", "omitted-correction", "false-scope"])
def test_original_correction_relationships_cannot_be_silently_rewritten(mutation: str) -> None:
    pack = packet()
    correction = json.loads(pack["files"]["correction-receipt.json"]["text"])
    if mutation == "manifest":
        correction["corrected_artifact_manifest_sha256"] = "0" * 64
    elif mutation == "assembly":
        correction["original_files"]["assembly-receipt.json"] = "0" * 64
    elif mutation == "omitted-correction":
        correction["changed_content_files"].pop()
    else:
        correction["behavioral_evidence_changed"] = True
    text = json.dumps(correction, indent=2) + "\n"
    pack["files"]["correction-receipt.json"] = {"text": text, "sha256": sha(text.encode())}
    with pytest.raises(ValueError, match="custody|correction"):
        assess(pack)


@pytest.mark.parametrize("exit_code", [1, 2, -9])
def test_nonzero_verifier_exit_requires_a_complete_matching_mismatch_result(exit_code: int) -> None:
    pack = packet()
    receipt = json.loads(pack["files"]["evidence/target-verification-execution.json"]["text"])
    receipt.update(exit_code=exit_code, complete_success=False)
    replace_file(pack, "evidence/target-verification-execution.json", receipt)
    refresh_decision_evidence(pack)
    with pytest.raises(ValueError, match="recorded execution"):
        assess(pack)
