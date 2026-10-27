# SPDX-License-Identifier: Apache-2.0
"""A new release changes only reviewed metadata in the fixed lint profile."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import refresh_capability_checkout as checkout

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_PROJECT = "042380c2e3e90872027acc1053ebef09472cc34db142318af1ff2390aec5483f"
PREVIOUS_PROFILE = "fb9aae3b8e67e66deb4da42c18c22ef16150d63390d53be31b1243b7ecbe778e"
PREVIOUS_GUARD = "802bf748051d6b9bfa2af73aefba8abbdbcdb608a713ec3d0f4fe9688a6eff41"
WORKER_FIXTURE = "96d9e55c28af87074299d5a8b55d1e7108aeb26ad3123ed1169e5d37c48e2759"


def test_release_metadata_preserves_entire_predecessor_configuration_and_guard() -> None:
    project = (ROOT / "pyproject.toml").read_bytes()
    assert project.count(b'version = "1.45.0"') == 1
    previous = project.replace(b'version = "1.45.0"', b'version = "1.44.0"', 1)
    assert hashlib.sha256(previous).hexdigest() == PREVIOUS_PROJECT
    raw = (ROOT / "scripts/strategy_research_e721_compatibility_v2.json").read_bytes()
    profile = json.loads(raw)
    assert profile["files"]["pyproject.toml"] == {"bytes": len(project), "sha256": hashlib.sha256(project).hexdigest()}
    profile["files"]["pyproject.toml"]["sha256"] = PREVIOUS_PROJECT
    original = (json.dumps(profile, indent=2) + "\n").encode()
    assert hashlib.sha256(original).hexdigest() == PREVIOUS_PROFILE
    guard = (ROOT / "scripts/check_strategy_research_compatibility_v2.py").read_bytes()
    current = hashlib.sha256(raw).hexdigest().encode()
    assert guard.count(current) == 1
    assert hashlib.sha256(guard.replace(current, PREVIOUS_PROFILE.encode(), 1)).hexdigest() == PREVIOUS_GUARD


def test_flywheel_worker_edition_is_complete_and_cannot_mix_with_predecessor(tmp_path: Path) -> None:
    for mask in range(8):
        _check_worker_mix(tmp_path / str(mask), mask)


def _check_worker_mix(tmp_path: Path, mask: int) -> None:
    raw = (ROOT / "tests/fixtures/capability-checkout-release-145-workers.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == WORKER_FIXTURE
    fixture = json.loads(raw)
    previous = json.loads((ROOT / "tests/fixtures/capability-checkout-release-144-workers.json").read_bytes())
    workers = tuple(fixture["files"])
    catalog = json.loads((ROOT / checkout.CATALOG).read_bytes())
    bodies = {name: (ROOT / name).read_bytes() for name in set(catalog["sources"]) | set(checkout.FLYWHEEL_145_EXTRA_FILES)}
    assert len(bodies) == 61
    for index, name in enumerate(workers):
        record = fixture["files"][name]
        body = record["text"].encode()
        assert (len(body), hashlib.sha256(body).hexdigest()) == checkout.FLYWHEEL_145_EXTRA_FILES[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
        assert body == (ROOT / name).read_bytes()
        bodies[name] = body if mask & (1 << index) else previous["files"][name]["text"].encode()
    for name, body in bodies.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    if mask in (0, 7):
        result = checkout.refresh(tmp_path)
        assert result["checked"] == 61 and result["needsRefresh"] == []
        assert result["applied"] is False and result["backupDirectory"] is None
    else:
        with pytest.raises(ValueError, match="unexpected capability bytes"):
            checkout.refresh(tmp_path)
    assert {name: (tmp_path / name).read_bytes() for name in bodies} == bodies
