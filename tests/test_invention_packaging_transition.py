# SPDX-License-Identifier: Apache-2.0
"""The verifier packaging successor preserves every historical lint boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SHA256 = "a5748c5b8bffe4eaa5e67609cae7043f73a6e0da6d5e9aea66a0414436920d35"
PROFILE = "scripts/strategy_research_e721_compatibility_v2.json"
GUARD = "scripts/check_strategy_research_compatibility_v2.py"


def historical() -> dict:
    raw = (ROOT / "tests/fixtures/invention-packaging-147-metadata.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SNAPSHOT_SHA256
    value = json.loads(raw)
    assert value["sourceCommit"] == "12770c22b4a9f90f2013bbfb64242f912ba5071e"
    return value


def test_exact_prior_metadata_and_all_legacy_pins_remain_preserved() -> None:
    snapshot = historical()
    assert set(snapshot["files"]) == {"pyproject.toml", PROFILE, GUARD}
    for name, body in snapshot["files"].items():
        raw = body.encode()
        assert snapshot["identities"][name] == {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
        }
    assert (
        hashlib.sha256((ROOT / "scripts/strategy_research_source_pins.json").read_bytes()).hexdigest()
        == snapshot["legacyPinsSha256"]
    )


def test_only_explicit_verifier_package_and_exact_commitments_change() -> None:
    old = historical()["files"]
    prior = json.loads((ROOT / "tests/fixtures/fast-delivery-packaging-147-metadata.json").read_text())["files"]
    project = prior["pyproject.toml"].encode()
    before = b'include = ["alpha_factory_v1*", "af_requests*", "openai_agents*"]'
    after = b'include = ["alpha_factory_v1*", "af_requests*", "openai_agents*", "contrib.invention_automation*"]'
    assert old["pyproject.toml"].encode().count(before) == 1
    expected_project = old["pyproject.toml"].encode().replace(before, after, 1)
    extras = b'[project.optional-dependencies]\ncompounding-discovery = ["scipy>=1.17,<1.18"]\nflood-readiness = ["pandas>=2.2,<4"]\nclaim-probe = ["sympy>=1.13,<1.15"]\nmeta-discovery = ["scipy>=1.17,<1.18"]'
    expected_project = expected_project.replace(b"[project.optional-dependencies]", extras, 1)
    assert project == expected_project
    prior_profile = old[PROFILE].encode()
    previous = json.loads(prior_profile)
    old_entry = previous["files"]["pyproject.toml"]
    raw = prior[PROFILE].encode()
    expected = prior_profile.replace(
        ('"bytes": ' + str(old_entry["bytes"])).encode(), ('"bytes": ' + str(len(project))).encode(), 1
    ).replace(old_entry["sha256"].encode(), hashlib.sha256(project).hexdigest().encode(), 1)
    assert raw == expected
    current = json.loads(raw)
    current["files"]["pyproject.toml"] = old_entry
    assert current == previous
    old_hash = hashlib.sha256(prior_profile).hexdigest().encode()
    new_hash = hashlib.sha256(raw).hexdigest().encode()
    assert old[GUARD].encode().count(old_hash) == 1
    assert prior[GUARD].encode() == old[GUARD].encode().replace(old_hash, new_hash, 1)
