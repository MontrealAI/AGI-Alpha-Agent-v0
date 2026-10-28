# SPDX-License-Identifier: Apache-2.0
"""Admit one post-guard worker edition without mutating any predecessor."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

import pytest

from scripts import refresh_capability_checkout as checkout
from tests.test_insight_frontier_release import (
    CATALOG_SHA256,
    HISTORICAL_PROFILES,
    ROOT,
    SCIENTIFIC_SOURCE_HASH,
    WORKERS,
    edition_files as original_edition_files,
    predecessor_workers as reader_workers,
    snapshot,
    write_files,
)

FIXTURE = "tests/fixtures/capability-checkout-insight-frontier-147-post-guard-workers.json"
FIXTURE_SHA256 = "d4a8b72e3e8c46a9cf162e4cc2cfc5fac1edbc8c4cc122184e18102b54c47308"
PREDECESSOR_FIXTURE_SHA256 = "7323b478b7d2e901b32411062683f50ab6a059823d7891134555b39eaa86725b"
PREDECESSOR_PROFILES_SHA256 = "eacf1f54607a7649e86096560293422c2a740ec080bb2b2106fafc4a61e9929f"


def worker_fixture() -> dict[str, Any]:
    raw = (ROOT / FIXTURE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    fixture: dict[str, Any] = json.loads(raw)
    assert fixture["version"] == "1.47.0" and fixture["edition"] == "post-execution-receipt-guard"
    assert fixture["sourceBase"] == "1028d7bc9ae68f6201849c84d3d9a224fa38edaa"
    assert fixture["predecessorFixtureSha256"] == PREDECESSOR_FIXTURE_SHA256
    original = ROOT / "tests/fixtures/capability-checkout-insight-frontier-147-workers.json"
    assert hashlib.sha256(original.read_bytes()).hexdigest() == PREDECESSOR_FIXTURE_SHA256
    assert (
        fixture["generatorSha256"]
        == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    )
    assert fixture["sourceHash"] == SCIENTIFIC_SOURCE_HASH and fixture["catalogSha256"] == CATALOG_SHA256
    assert set(fixture["files"]) == set(WORKERS)
    return fixture


def edition_files() -> dict[str, bytes]:
    files = original_edition_files()
    files.update({name: record["text"].encode() for name, record in worker_fixture()["files"].items()})
    assert len(files) == 61
    for name, record in checkout.INSIGHT_FRONTIER_147_POST_GUARD_EXTRA_FILES.items():
        assert (len(files[name]), hashlib.sha256(files[name]).hexdigest()) == record
    return files


def test_historical_post_guard_workers_preserve_their_own_source_and_all_twenty_predecessors(tmp_path: Path) -> None:
    fixture = worker_fixture()
    names = (*HISTORICAL_PROFILES, "INSIGHT_FRONTIER_147_EXTRA_FILES")
    assert len(names) == len(set(names)) == 20
    profiles = {name: getattr(checkout, name) for name in names}
    assert hashlib.sha256(json.dumps(profiles, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == (
        PREDECESSOR_PROFILES_SHA256
    )
    current, original = checkout.INSIGHT_FRONTIER_147_POST_GUARD_EXTRA_FILES, checkout.INSIGHT_FRONTIER_147_EXTRA_FILES
    assert set(current) == set(original)
    assert {name: record for name, record in current.items() if name not in WORKERS} == {
        name: record for name, record in original.items() if name not in WORKERS
    }
    assert len(set(current) - set(WORKERS)) == 5
    records = {}
    for name, record in fixture["files"].items():
        body = record["text"].encode()
        # A later separately pinned candidate must not rewrite this complete edition.
        assert b"agialpha-gallery-84e195a76403cf05" in body
        assert (len(body), hashlib.sha256(body).hexdigest()) == (record["bytes"], record["sha256"]) == current[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
        records[name] = current[name]
    matches = [
        profile
        for _, _, _, profile in checkout._source_profiles((ROOT / checkout.CATALOG).read_bytes())
        if all(profile[name] == record for name, record in records.items())
    ]
    assert matches == [current]
    assert len(edition_files()) == 61
    write_files(tmp_path, edition_files())
    report = checkout.refresh(tmp_path)
    assert report["checked"] == 61 and report["needsRefresh"] == []
    assert report["applied"] is False and report["backupDirectory"] is None


def test_post_guard_crlf_repair_retains_originals_and_is_idempotent(tmp_path: Path) -> None:
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
    assert applied["checked"] == 61 and applied["applied"] is True and applied["backupDirectory"] is not None
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


@pytest.mark.parametrize("predecessor", ["original-147", "reader-1461"])
@pytest.mark.parametrize("mask", range(8))
def test_post_guard_partial_worker_mixtures_refuse_before_backup(tmp_path: Path, predecessor: str, mask: int) -> None:
    files = edition_files()
    old = original_edition_files() if predecessor == "original-147" else reader_workers()
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
def test_post_guard_tampered_worker_refuses_before_backup(tmp_path: Path, name: str, same_size: bool) -> None:
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
def test_post_guard_missing_worker_refuses_before_backup(tmp_path: Path, name: str) -> None:
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
def test_post_guard_symlink_worker_refuses_before_backup(tmp_path: Path, name: str) -> None:
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
    # Later candidates can report a different earlier byte mismatch; refusal stays mandatory.
    with pytest.raises(ValueError):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert link.is_symlink() and link.readlink() == outside
    assert snapshot(root) == before and outside.read_bytes() == body and list(backups.iterdir()) == []


@pytest.mark.parametrize("damage", ["scientific-source", "catalogue"])
def test_post_guard_changed_scientific_closure_refuses_before_backup(tmp_path: Path, damage: str) -> None:
    files = edition_files()
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
