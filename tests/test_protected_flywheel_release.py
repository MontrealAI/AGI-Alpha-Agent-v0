# SPDX-License-Identifier: Apache-2.0
"""Preserve predecessor metadata and whole worker editions while qualifying this source."""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pytest
from scripts import refresh_capability_checkout as checkout

ROOT = Path(__file__).resolve().parents[1]
METADATA_SHA256 = "6573b3f3ceacfc257a51fee6a0f89465de9c8418c9163a45e8282b85083cb716"
PATCH_PREDECESSOR_SHA256 = "c9d1d2819b4e01712523040132b9b354e3c8637154a64b13b166fa0a75167dce"
WORKERS_SHA256 = "b383cccd051215c2454c0696b1a1ce5d58716b94cee21286bfd6c69783364dfc"
READER_METADATA_SHA256 = "bf142629d793cafa6a2434902156999905c43be69ddecfabd9a89e8faf2d2293"


def _preserved_146_metadata() -> dict[str, str]:
    raw = (ROOT / "tests/fixtures/protected-flywheel-146-release-metadata.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PATCH_PREDECESSOR_SHA256
    preserved = json.loads(raw)
    assert preserved["sourceCommit"] == "80b345828f34fd8a6e592977dd17ef37141305f4"
    return preserved["files"]


def test_146_changes_only_version_in_the_145_lint_configuration() -> None:
    raw = (ROOT / "tests/fixtures/protected-flywheel-145-release-metadata.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == METADATA_SHA256
    preserved = json.loads(raw)
    assert preserved["sourceCommit"] == "95051ed4a58b2f3ded9e392ead5539a90bd8df13"
    previous = preserved["files"]
    historical = _preserved_146_metadata()
    project = historical["pyproject.toml"].encode()
    assert project.count(b'version = "1.46.0"') == 1
    assert project.replace(b'version = "1.46.0"', b'version = "1.45.0"', 1) == previous["pyproject.toml"].encode()
    profile_raw = historical["scripts/strategy_research_e721_compatibility_v2.json"].encode()
    profile, old = json.loads(profile_raw), json.loads(previous["scripts/strategy_research_e721_compatibility_v2.json"])
    assert profile["files"]["pyproject.toml"] == {"bytes": len(project), "sha256": hashlib.sha256(project).hexdigest()}
    profile["files"]["pyproject.toml"] = old["files"]["pyproject.toml"]
    assert profile == old
    guard = historical["scripts/check_strategy_research_compatibility_v2.py"].encode()
    old_hash = (
        hashlib.sha256(previous["scripts/strategy_research_e721_compatibility_v2.json"].encode()).hexdigest().encode()
    )
    current_hash = hashlib.sha256(profile_raw).hexdigest().encode()
    assert guard.count(current_hash) == 1
    assert (
        guard.replace(current_hash, old_hash, 1)
        == previous["scripts/check_strategy_research_compatibility_v2.py"].encode()
    )


def test_146_complete_workers_and_predecessor_mixtures(tmp_path: Path) -> None:
    raw = (ROOT / "tests/fixtures/capability-checkout-release-146-workers.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == WORKERS_SHA256
    fixture = json.loads(raw)
    previous = json.loads((ROOT / "tests/fixtures/capability-checkout-release-145-workers.json").read_bytes())
    catalog = json.loads((ROOT / checkout.CATALOG).read_bytes())
    bodies = {
        name: (ROOT / name).read_bytes()
        for name in set(catalog["sources"]) | set(checkout.PROTECTED_FLYWHEEL_146_EXTRA_FILES)
    }
    assert len(bodies) == 61
    for name, record in fixture["files"].items():
        body = record["text"].encode()
        # Historical 1.46 remains exact even after a separately qualified successor.
        bodies[name] = body
        assert (len(body), hashlib.sha256(body).hexdigest()) == checkout.PROTECTED_FLYWHEEL_146_EXTRA_FILES[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
    for mask in range(8):
        selected = dict(bodies)
        for index, name in enumerate(fixture["files"]):
            selected[name] = (fixture if mask & 1 << index else previous)["files"][name]["text"].encode()
        root = tmp_path / str(mask)
        for name, body in selected.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        if mask in {0, 7}:
            result = checkout.refresh(root)
            assert result["checked"] == 61 and result["needsRefresh"] == []
            assert result["applied"] is False
        else:
            with pytest.raises(ValueError, match="unexpected capability bytes"):
                checkout.refresh(root)
        assert {name: (root / name).read_bytes() for name in selected} == selected


def test_1461_changes_only_version_in_the_146_lint_configuration() -> None:
    previous = _preserved_146_metadata()
    raw = (ROOT / "tests/fixtures/protected-flywheel-1461-release-metadata.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == READER_METADATA_SHA256
    preserved = json.loads(raw)
    assert preserved["sourceCommit"] == "3947e4ec8fd74ad40e13e8ff825a149fa98a10e9"
    historical = preserved["files"]
    project = historical["pyproject.toml"].encode()
    assert project.count(b'version = "1.46.1"') == 1
    assert project.replace(b'version = "1.46.1"', b'version = "1.46.0"', 1) == previous["pyproject.toml"].encode()
    profile_raw = historical["scripts/strategy_research_e721_compatibility_v2.json"].encode()
    profile, old = json.loads(profile_raw), json.loads(previous["scripts/strategy_research_e721_compatibility_v2.json"])
    assert profile["files"]["pyproject.toml"] == {"bytes": len(project), "sha256": hashlib.sha256(project).hexdigest()}
    profile["files"]["pyproject.toml"] = old["files"]["pyproject.toml"]
    assert profile == old
    guard = historical["scripts/check_strategy_research_compatibility_v2.py"].encode()
    old_hash = (
        hashlib.sha256(previous["scripts/strategy_research_e721_compatibility_v2.json"].encode()).hexdigest().encode()
    )
    current_hash = hashlib.sha256(profile_raw).hexdigest().encode()
    assert guard.count(current_hash) == 1
    assert (
        guard.replace(current_hash, old_hash, 1)
        == previous["scripts/check_strategy_research_compatibility_v2.py"].encode()
    )
    assert '__version__ = "1.46.1"' in preserved["versionFiles"]["alpha_factory_v1/__init__.py"]
    assert json.loads(preserved["versionFiles"]["alpha_factory_v1/demos/catalog.json"])["release"] == "1.46.1"
