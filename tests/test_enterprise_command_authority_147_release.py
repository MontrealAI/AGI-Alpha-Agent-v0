# SPDX-License-Identifier: Apache-2.0
"""Bind the current authority repair without changing any historical admission."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

import pytest

from scripts import refresh_capability_checkout as checkout
from tests.test_delivery_guard_147_release import current_files as guard_files
from tests.test_frontier_delivery_147_release import current_files as frontier_files
from tests.test_insight_frontier_enterprise_acceptance_release import edition_files as enterprise_files
from tests.test_insight_frontier_release import (
    CATALOG_SHA256,
    ROOT,
    SCIENTIFIC_SOURCE_HASH,
    WORKERS,
    edition_files as original_files,
    predecessor_workers as reader_workers,
    snapshot,
    write_files,
)

FIXTURE = "tests/fixtures/capability-checkout-enterprise-command-authority-147-workers.json"
FIXTURE_SHA256 = "15020dce09c00ba5a805e3908fa3c09daa1f6d9ceab8ee01b63fa9d6285e61c7"
PREDECESSOR_FIXTURE_SHA256 = "a5ec93aeb618dfd65b0c6692efec0d183e78f10e3370f781e6333403fab094c7"
PREDECESSOR_PROFILES_SHA256 = "09298ff51cdb064700028ccf66f813cf143936d75fb8ededaf5ea2f34f75de33"


def fixture() -> dict[str, Any]:
    raw = (ROOT / FIXTURE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    value: dict[str, Any] = json.loads(raw)
    assert value["version"] == "1.47.0" and value["edition"] == "enterprise-command-current-authority"
    assert value["sourceBase"] == "c5164a385f54b59a11b53d70cf491e5e21ad3b18"
    assert value["predecessorFixtureSha256"] == PREDECESSOR_FIXTURE_SHA256
    previous = ROOT / "tests/fixtures/capability-checkout-delivery-guard-147-workers.json"
    assert hashlib.sha256(previous.read_bytes()).hexdigest() == PREDECESSOR_FIXTURE_SHA256
    assert value["catalogSha256"] == CATALOG_SHA256 and value["sourceHash"] == SCIENTIFIC_SOURCE_HASH
    assert set(value["files"]) == set(WORKERS)
    return value


def current_files() -> dict[str, bytes]:
    raw = (ROOT / checkout.CATALOG).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CATALOG_SHA256
    catalog = json.loads(raw)
    assert len(catalog["sources"]) == 53 and catalog["sourceHash"] == SCIENTIFIC_SOURCE_HASH
    profile = checkout.ENTERPRISE_COMMAND_AUTHORITY_147_EXTRA_FILES
    files = {name: (ROOT / name).read_bytes() for name in set(catalog["sources"]) | set(profile)}
    assert len(files) == 61
    for name, body in files.items():
        assert b"\r" not in body
        if name in profile:
            assert (len(body), hashlib.sha256(body).hexdigest()) == profile[name]
        else:
            assert hashlib.sha256(body).hexdigest() == catalog["sources"][name]
    return files


def test_current_authority_edition_preserves_all_twenty_eight_profiles_and_source_bindings() -> None:
    value = fixture()
    profiles = {name: getattr(checkout, name) for name in value["predecessorProfiles"]}
    assert len(profiles) == 28
    assert value["predecessorProfilesSha256"] == PREDECESSOR_PROFILES_SHA256
    assert hashlib.sha256(json.dumps(profiles, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == (
        PREDECESSOR_PROFILES_SHA256
    )
    for name, expected in value["predecessorProfiles"].items():
        body = json.dumps(profiles[name], sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(body).hexdigest() == expected, name
    current, previous = checkout.ENTERPRISE_COMMAND_AUTHORITY_147_EXTRA_FILES, checkout.DELIVERY_GUARD_147_EXTRA_FILES
    assert set(current) == set(previous) and len(set(current) - set(WORKERS)) == 5
    assert {name: row for name, row in current.items() if name not in WORKERS} == {
        name: row for name, row in previous.items() if name not in WORKERS
    }
    assert value["generatorSha256"] == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    manifest_raw = (ROOT / "docs/flywheel/sources.json").read_bytes()
    manifest = json.loads(manifest_raw)
    assert hashlib.sha256(manifest_raw).hexdigest() == value["sourceManifestSha256"]
    assert manifest["sourceHash"] == value["flywheelSourceHash"]
    assert len(manifest["sources"]) == 20
    for name, expected in manifest["sources"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    assert len(value["runtimeSources"]) == 75
    for name, expected in value["runtimeSources"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    assert value["enterpriseModuleSha256"] == value["runtimeSources"][
        "alpha_factory_v1/core/runtime/successor/flywheel_enterprise.py"
    ] == "ac9601e0b76c3c425ef854ea2ce48e7462fd99b0777b040b09b16eb4e20cfab6"
    assert len(value["packetIdentities"]) == 8
    binding_count = 0
    for name, record in value["packetIdentities"].items():
        raw = (ROOT / name).read_bytes()
        assert (len(raw), hashlib.sha256(raw).hexdigest()) == (record["bytes"], record["sha256"])
        for source, expected in record["sourceBindings"].items():
            assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == expected, source
            binding_count += 1
    assert binding_count == 433
    assert value["pageSha256"] == hashlib.sha256((ROOT / "docs/flywheel/index.html").read_bytes()).hexdigest()
    records = {}
    before = current_files()
    for name, row in value["files"].items():
        body = before[name]
        assert body == row["text"].encode() and b"agialpha-gallery-a2739388a5a2d8b3" in body
        assert (len(body), hashlib.sha256(body).hexdigest()) == (row["bytes"], row["sha256"]) == current[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == row["gitBlob"]
        records[name] = current[name]
    matches = [
        profile
        for _, _, _, profile in checkout._source_profiles((ROOT / checkout.CATALOG).read_bytes())
        if all(profile[name] == row for name, row in records.items())
    ]
    assert matches == [current]
    report = checkout.refresh(ROOT)
    assert report["checked"] == 61 and report["needsRefresh"] == []
    assert report["applied"] is False and report["backupDirectory"] is None
    assert current_files() == before


def test_current_authority_crlf_repair_preserves_originals_and_is_idempotent(tmp_path: Path) -> None:
    canonical = current_files()
    converted = {name: body.replace(b"\n", b"\r\n") for name, body in canonical.items()}
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, converted)
    before = snapshot(root)
    dry = checkout.refresh(root)
    assert dry["checked"] == 61 and dry["applied"] is False
    assert set(dry["needsRefresh"]) == {name for name in canonical if canonical[name] != converted[name]}
    assert snapshot(root) == before and list(backups.iterdir()) == []
    applied = checkout.refresh(root, apply=True, backup_parent=backups)
    assert applied["checked"] == 61 and applied["applied"] is True and applied["backupDirectory"] is not None
    backup = Path(applied["backupDirectory"])
    assert backup.parent == backups
    if os.name != "nt":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o700
    manifest = json.loads((backup / "manifest.json").read_bytes())
    assert manifest["sourceHash"] == SCIENTIFIC_SOURCE_HASH
    assert {row["path"] for row in manifest["files"]} == set(before)
    for row in manifest["files"]:
        original = before[row["path"]]
        assert (backup / "files" / row["path"]).read_bytes() == original
        assert (row["bytes"], row["sha256"]) == (len(original), hashlib.sha256(original).hexdigest())
    assert json.loads((backup / "result.json").read_bytes())["complete"] is True
    assert snapshot(root) == canonical
    assert checkout.refresh(root)["needsRefresh"] == [] and len(list(backups.iterdir())) == 1


@pytest.mark.parametrize("predecessor", ["guard", "frontier", "enterprise", "original", "reader"])
@pytest.mark.parametrize("mask", range(8))
def test_complete_authority_editions_pass_and_partial_mixtures_refuse(
    tmp_path: Path, predecessor: str, mask: int
) -> None:
    old = {
        "guard": guard_files,
        "frontier": frontier_files,
        "enterprise": enterprise_files,
        "original": original_files,
        "reader": reader_workers,
    }[predecessor]()
    files = current_files()
    for index, name in enumerate(WORKERS):
        if not mask & (1 << index):
            files[name] = old[name]
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    before = snapshot(root)
    if mask in {0, 7}:
        report = checkout.refresh(root)
        assert report["checked"] == 61 and report["needsRefresh"] == []
        assert report["applied"] is False and report["backupDirectory"] is None
    else:
        with pytest.raises(ValueError, match="unexpected capability bytes"):
            checkout.refresh(root, apply=True, backup_parent=backups)
    assert snapshot(root) == before and list(backups.iterdir()) == []


@pytest.mark.parametrize("name", WORKERS)
@pytest.mark.parametrize("damage", ["same-size", "appended", "missing"])
def test_unknown_authority_worker_refuses_before_backup(tmp_path: Path, name: str, damage: str) -> None:
    files = current_files()
    if damage == "missing":
        del files[name]
    else:
        files[name] = b"!" + files[name][1:] if damage == "same-size" else files[name] + b"// unreviewed\n"
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    before = snapshot(root)
    with pytest.raises((ValueError, FileNotFoundError)):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert snapshot(root) == before and list(backups.iterdir()) == []


@pytest.mark.parametrize("name", WORKERS)
def test_current_authority_symlink_refuses_at_read_boundary_and_before_mutation(tmp_path: Path, name: str) -> None:
    files = current_files()
    body = files.pop(name)
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    outside = tmp_path / "outside-worker.js"
    outside.write_bytes(body)
    link = root / name
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"OS cannot create this test symlink: {error}")
    before = snapshot(root)
    with pytest.raises(ValueError, match="bounded regular file"):
        checkout._read(root, name)
    with pytest.raises(ValueError):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert link.is_symlink() and link.readlink() == outside
    assert snapshot(root) == before and outside.read_bytes() == body and list(backups.iterdir()) == []


@pytest.mark.parametrize("damage", ["scientific-source", "catalogue"])
def test_current_authority_changed_scientific_closure_refuses_before_backup(tmp_path: Path, damage: str) -> None:
    files = current_files()
    catalog = json.loads(files[checkout.CATALOG])
    name = next(iter(catalog["sources"])) if damage == "scientific-source" else checkout.CATALOG
    files[name] = b"!" + files[name][1:]
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    before = snapshot(root)
    with pytest.raises(ValueError, match="unexpected capability bytes"):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert snapshot(root) == before and list(backups.iterdir()) == []
