# SPDX-License-Identifier: Apache-2.0
"""Admit only the complete frozen Insight worker edition and preserve its predecessors."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

import pytest

from scripts import refresh_capability_checkout as checkout

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "tests/fixtures/capability-checkout-insight-frontier-147-workers.json"
FIXTURE_SHA256 = "7323b478b7d2e901b32411062683f50ab6a059823d7891134555b39eaa86725b"
PREDECESSOR_SHA256 = "9537d6f85cdbf220a1889e55057b3271fb512902fc30b8fe9a79a53cc176591f"
CATALOG_SHA256 = "d1c3cb9a5c3eb96e9e5eb111b83a713786ec18ed1213a407cd77bbaf018c5adb"
SCIENTIFIC_SOURCE_HASH = "54769dbfde99ae13708a33292866f0ca7e6b8b7792a7a944f76bf2fbf1de1358"
HISTORICAL_PROFILES_SHA256 = "92d26e329cc63a75bef08f51b92c7f2593ccd16580f22f2a2513ec3952a5f379"
HISTORICAL_PROFILES = (
    "COMPANION_141_EXTRA_FILES",
    "ENTERPRISE_139_EXTRA_FILES",
    "ENTERPRISE_139_PRESENTATION_EXTRA_FILES",
    "ENTERPRISE_139_RELEASE_EXTRA_FILES",
    "ENTERPRISE_EXTRA_FILES",
    "ENTERPRISE_PARENT_EXTRA_FILES",
    "EXTRA_FILES",
    "FLYWHEEL_145_EXTRA_FILES",
    "FOUNDRY_140_EXTRA_FILES",
    "NEXT_UPGRADE_20261026_EXTRA_FILES",
    "PAPERS_20261026_EXTRA_FILES",
    "PAPER_READERS_1461_EXTRA_FILES",
    "PROFITABLE_WORK_20261027_EXTRA_FILES",
    "PROTECTED_FLYWHEEL_146_EXTRA_FILES",
    "RESEARCH_GUIDES_140_EXTRA_FILES",
    "SOURCE_OPERATION_143_EXTRA_FILES",
    "STRATEGY_144_EXTRA_FILES",
    "TI_GUIDE_142_EXTRA_FILES",
    "WORKBENCH_1411_EXTRA_FILES",
)
WORKERS = (
    "docs/service-worker.js",
    "docs/assets/service-worker.js",
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)


def worker_fixture() -> dict[str, Any]:
    raw = (ROOT / FIXTURE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    fixture: dict[str, Any] = json.loads(raw)
    assert fixture["version"] == "1.47.0"
    assert fixture["sourceBase"] == "095c11fe33522be6c0e2d7a00043d7bbb5bcb457"
    assert fixture["upstreamReaderCommit"] == "e6c9265ad1d2c86ebee665166f46ffdd10636ee8"
    assert (
        fixture["generatorSha256"]
        == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    )
    assert fixture["sourceHash"] == SCIENTIFIC_SOURCE_HASH
    assert fixture["catalogSha256"] == CATALOG_SHA256
    assert set(fixture["files"]) == set(WORKERS)
    return fixture


def predecessor_workers() -> dict[str, bytes]:
    raw = (ROOT / "tests/fixtures/capability-checkout-paper-readers-1461-workers.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PREDECESSOR_SHA256
    fixture = json.loads(raw)
    return {name: record["text"].encode() for name, record in fixture["files"].items()}


def edition_files() -> dict[str, bytes]:
    raw = (ROOT / checkout.CATALOG).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CATALOG_SHA256
    catalog = json.loads(raw)
    assert len(catalog["sources"]) == 53
    assert catalog["sourceHash"] == SCIENTIFIC_SOURCE_HASH == checkout.ENTERPRISE_SOURCE_HASH
    assert hashlib.sha256(
        json.dumps(catalog["sources"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest() == (SCIENTIFIC_SOURCE_HASH)
    profile = checkout.INSIGHT_FRONTIER_147_EXTRA_FILES
    files = {name: (ROOT / name).read_bytes() for name in set(catalog["sources"]) | set(profile)}
    assert len(files) == 61
    files.update({name: record["text"].encode() for name, record in worker_fixture()["files"].items()})
    for name, body in files.items():
        assert b"\r" not in body
        if name in profile:
            assert (len(body), hashlib.sha256(body).hexdigest()) == profile[name]
        else:
            assert hashlib.sha256(body).hexdigest() == catalog["sources"][name]
    return files


def write_files(root: Path, files: dict[str, bytes]) -> None:
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def snapshot(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_frozen_original_147_workers_preserve_their_own_source_and_every_historical_profile(tmp_path: Path) -> None:
    fixture = worker_fixture()
    profiles = {name: getattr(checkout, name) for name in HISTORICAL_PROFILES}
    assert hashlib.sha256(json.dumps(profiles, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == (
        HISTORICAL_PROFILES_SHA256
    )
    current, previous = checkout.INSIGHT_FRONTIER_147_EXTRA_FILES, checkout.PAPER_READERS_1461_EXTRA_FILES
    assert set(current) == set(previous)
    assert {name: record for name, record in current.items() if name not in WORKERS} == {
        name: record for name, record in previous.items() if name not in WORKERS
    }
    assert len(set(current) - set(WORKERS)) == 5
    records = {}
    for name, record in fixture["files"].items():
        body = record["text"].encode()
        # Preserve the original candidate independently of a separately admitted successor.
        assert b"agialpha-gallery-75b76c33b2d213bd" in body
        assert (len(body), hashlib.sha256(body).hexdigest()) == (record["bytes"], record["sha256"]) == current[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
        records[name] = current[name]
    matches = [
        profile
        for _, _, _, profile in checkout._source_profiles((ROOT / checkout.CATALOG).read_bytes())
        if all(profile[name] == record for name, record in records.items())
    ]
    assert matches == [current]
    write_files(tmp_path, edition_files())
    report = checkout.refresh(tmp_path)
    assert report["checked"] == 61 and report["needsRefresh"] == []
    assert report["applied"] is False and report["backupDirectory"] is None


def test_147_crlf_repair_preserves_every_original_and_is_idempotent(tmp_path: Path) -> None:
    canonical = edition_files()
    converted = {name: body.replace(b"\n", b"\r\n") for name, body in canonical.items()}
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, converted)
    before = snapshot(root)
    dry = checkout.refresh(root)
    assert dry["checked"] == 61
    assert set(dry["needsRefresh"]) == {name for name in canonical if canonical[name] != converted[name]}
    assert snapshot(root) == before and list(backups.iterdir()) == []
    applied = checkout.refresh(root, apply=True, backup_parent=backups)
    assert applied["checked"] == 61 and applied["applied"] is True
    assert applied["backupDirectory"] is not None
    backup = Path(applied["backupDirectory"])
    assert backup.parent == backups
    if os.name != "nt":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o700
    manifest = json.loads((backup / "manifest.json").read_bytes())
    assert manifest["sourceHash"] == SCIENTIFIC_SOURCE_HASH
    assert {record["path"] for record in manifest["files"]} == set(before)
    for record in manifest["files"]:
        original = before[record["path"]]
        assert (backup / "files" / record["path"]).read_bytes() == original
        assert (record["bytes"], record["sha256"]) == (len(original), hashlib.sha256(original).hexdigest())
    assert json.loads((backup / "result.json").read_bytes())["complete"] is True
    assert snapshot(root) == canonical
    assert checkout.refresh(root)["needsRefresh"] == [] and len(list(backups.iterdir())) == 1


@pytest.mark.parametrize("mask", range(8))
def test_147_and_1461_partial_worker_mixtures_refuse_before_backup(tmp_path: Path, mask: int) -> None:
    files, old = edition_files(), predecessor_workers()
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
@pytest.mark.parametrize("same_size", [False, True])
def test_147_unknown_worker_refuses_before_backup(tmp_path: Path, name: str, same_size: bool) -> None:
    files = edition_files()
    files[name] = b"!" + files[name][1:] if same_size else files[name] + b"// unreviewed\n"
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    before = snapshot(root)
    with pytest.raises(ValueError, match="unexpected capability bytes"):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert snapshot(root) == before and list(backups.iterdir()) == []


@pytest.mark.parametrize("name", WORKERS)
def test_147_missing_worker_refuses_before_backup(tmp_path: Path, name: str) -> None:
    files = edition_files()
    del files[name]
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    before = snapshot(root)
    with pytest.raises(FileNotFoundError):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert snapshot(root) == before and list(backups.iterdir()) == []


@pytest.mark.parametrize("name", WORKERS)
def test_147_symlink_worker_refuses_before_backup(tmp_path: Path, name: str) -> None:
    files = edition_files()
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
    # A later profile may fail on another worker before reaching this symlink.
    # Its final diagnostic is not the public refusal or mutation contract.
    with pytest.raises(ValueError):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert link.is_symlink() and link.readlink() == outside
    assert snapshot(root) == before and outside.read_bytes() == body and list(backups.iterdir()) == []
