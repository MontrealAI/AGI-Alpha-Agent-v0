# SPDX-License-Identifier: Apache-2.0
"""Preserve the exact reader release while preparing proposed successor metadata."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = "3947e4ec8fd74ad40e13e8ff825a149fa98a10e9"
METADATA_SHA256 = "bf142629d793cafa6a2434902156999905c43be69ddecfabd9a89e8faf2d2293"
HELD_GUARD_SHA256 = "c91da6e0f18974f219a3b3bbad03a1a048a895328c6ef02fc2ee13f83cc6e054"


def predecessor() -> dict:
    raw = (ROOT / "tests/fixtures/protected-flywheel-1461-release-metadata.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == METADATA_SHA256
    result = json.loads(raw)
    assert result["sourceCommit"] == PREDECESSOR
    return result


def test_1461_metadata_snapshot_retains_every_exact_body_and_git_identity() -> None:
    frozen = predecessor()
    assert set(frozen["files"]) == {
        "pyproject.toml",
        "scripts/strategy_research_e721_compatibility_v2.json",
        "scripts/check_strategy_research_compatibility_v2.py",
    }
    assert set(frozen["versionFiles"]) == {"alpha_factory_v1/__init__.py", "alpha_factory_v1/demos/catalog.json"}
    bodies = {**frozen["files"], **frozen["versionFiles"]}
    assert set(bodies) == set(frozen["identities"])
    for name, text in bodies.items():
        raw = text.encode()
        assert frozen["identities"][name] == {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
        }


def test_147_changes_only_version_and_its_exact_compatibility_commitments() -> None:
    previous = predecessor()["files"]
    project = (ROOT / "pyproject.toml").read_bytes()
    assert project.count(b'version = "1.47.0"') == 1
    assert project.replace(b'version = "1.47.0"', b'version = "1.46.1"', 1) == previous["pyproject.toml"].encode()
    raw = (ROOT / "scripts/strategy_research_e721_compatibility_v2.json").read_bytes()
    profile, old = json.loads(raw), json.loads(previous["scripts/strategy_research_e721_compatibility_v2.json"])
    assert profile["files"]["pyproject.toml"] == {"bytes": len(project), "sha256": hashlib.sha256(project).hexdigest()}
    profile["files"]["pyproject.toml"] = old["files"]["pyproject.toml"]
    assert profile == old
    assert (
        raw.replace(hashlib.sha256(project).hexdigest().encode(), old["files"]["pyproject.toml"]["sha256"].encode(), 1)
        == previous["scripts/strategy_research_e721_compatibility_v2.json"].encode()
    )
    old_hash = (
        hashlib.sha256(previous["scripts/strategy_research_e721_compatibility_v2.json"].encode()).hexdigest().encode()
    )
    new_hash = hashlib.sha256(raw).hexdigest().encode()
    guard = (ROOT / "scripts/check_strategy_research_compatibility_v2.py").read_bytes()
    assert guard.count(new_hash) == 1
    assert (
        guard.replace(new_hash, old_hash, 1) == previous["scripts/check_strategy_research_compatibility_v2.py"].encode()
    )


def test_147_package_version_preserves_init_and_complete_demo_inventory() -> None:
    previous = predecessor()["versionFiles"]
    source = (ROOT / "alpha_factory_v1/__init__.py").read_bytes()
    assert source.count(b'__version__ = "1.47.0"') == 1
    assert (
        source.replace(b'__version__ = "1.47.0"', b'__version__ = "1.46.1"', 1)
        == previous["alpha_factory_v1/__init__.py"].encode()
    )
    raw = (ROOT / "alpha_factory_v1/demos/catalog.json").read_bytes()
    assert raw.count(b'"release": "1.47.0"') == 1
    assert (
        raw.replace(b'"release": "1.47.0"', b'"release": "1.46.1"', 1)
        == previous["alpha_factory_v1/demos/catalog.json"].encode()
    )


def test_147_keeps_the_exact_held_source_guard_and_all_five_inert_identities() -> None:
    guard = ROOT / "scripts/check_held_native_source.py"
    assert hashlib.sha256(guard.read_bytes()).hexdigest() == HELD_GUARD_SHA256
    namespace = runpy.run_path(str(guard), run_name="_147_static_held_source_guard")
    assert namespace["BASELINE_COMMIT"] == "f9d2e3ff90ba6c8f1fcf85a3160d820e5dcb80c9"
    assert len(namespace["PINNED_FILES"]) == 5
    checks = namespace["check_identities"](ROOT, namespace["PINNED_FILES"])
    assert len(checks) == 5 and all(row["matched"] is True for row in checks)
