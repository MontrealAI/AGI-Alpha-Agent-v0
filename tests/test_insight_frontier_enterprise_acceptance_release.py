# SPDX-License-Identifier: Apache-2.0
"""Bind current enterprise acceptance while preserving every prior worker edition."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

import pytest

from scripts import refresh_capability_checkout as checkout
from tests.test_insight_frontier_review_authority_release import edition_files as authority_edition_files
from tests.test_insight_frontier_post_guard_release import edition_files as post_guard_edition_files
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

FIXTURE = "tests/fixtures/capability-checkout-insight-frontier-147-enterprise-acceptance-workers.json"
FIXTURE_SHA256 = "c750d36d109118d6c170185c6a98b5a508f67c7e8cf0c6fcbff675da6e15b2e5"
PREDECESSOR_FIXTURE_SHA256 = "659c8f56ea2d09051a92f7c2de81ca7f83b59fb868df2ab8ec0dd5d17b13b06b"
PREDECESSOR_PROFILES_SHA256 = "4e464d9330f2d57f2ff375d3934df5a7f6c5a24e5e55b1e6eea1bdab0a7e427d"


def worker_fixture() -> dict[str, Any]:
    raw = (ROOT / FIXTURE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    fixture: dict[str, Any] = json.loads(raw)
    assert fixture["version"] == "1.47.0" and fixture["edition"] == "enterprise-prototype-current-acceptance"
    assert fixture["sourceBase"] == "8b2bb77c59aaf066f2837f387c7f38d5a5fc1aff"
    assert fixture["predecessorFixtureSha256"] == PREDECESSOR_FIXTURE_SHA256
    original = ROOT / "tests/fixtures/capability-checkout-insight-frontier-147-review-authority-workers.json"
    assert hashlib.sha256(original.read_bytes()).hexdigest() == PREDECESSOR_FIXTURE_SHA256
    assert (
        fixture["generatorSha256"]
        == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    )
    assert fixture["sourceHash"] == SCIENTIFIC_SOURCE_HASH and fixture["catalogSha256"] == CATALOG_SHA256
    assert set(fixture["files"]) == set(WORKERS)
    return fixture


def edition_files() -> dict[str, bytes]:
    files = authority_edition_files()
    files.update({name: record["text"].encode() for name, record in worker_fixture()["files"].items()})
    assert len(files) == 61
    for name, record in checkout.INSIGHT_FRONTIER_147_ENTERPRISE_ACCEPTANCE_EXTRA_FILES.items():
        assert (len(files[name]), hashlib.sha256(files[name]).hexdigest()) == record
    return files


def test_enterprise_acceptance_workers_preserve_frozen_source_and_all_twenty_two_predecessors(
    tmp_path: Path,
) -> None:
    fixture = worker_fixture()
    names = (
        *HISTORICAL_PROFILES,
        "INSIGHT_FRONTIER_147_EXTRA_FILES",
        "INSIGHT_FRONTIER_147_POST_GUARD_EXTRA_FILES",
        "INSIGHT_FRONTIER_147_REVIEW_AUTHORITY_EXTRA_FILES",
    )
    assert len(names) == len(set(names)) == 22
    profiles = {name: getattr(checkout, name) for name in names}
    assert hashlib.sha256(json.dumps(profiles, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == (
        PREDECESSOR_PROFILES_SHA256
    )
    current = checkout.INSIGHT_FRONTIER_147_ENTERPRISE_ACCEPTANCE_EXTRA_FILES
    previous = checkout.INSIGHT_FRONTIER_147_REVIEW_AUTHORITY_EXTRA_FILES
    assert set(current) == set(previous)
    assert {name: row for name, row in current.items() if name not in WORKERS} == {
        name: row for name, row in previous.items() if name not in WORKERS
    }
    assert len(set(current) - set(WORKERS)) == 5
    assert fixture["pageSha256"] == "7c6144a05219319687a35e2c54e0edce1443635f89cb241c0fe7766e67094f98"
    assert (
        hashlib.sha256(
            (ROOT / "tests/fixtures/agi-alpha-insight-frontier-147-enterprise-acceptance-page.html.txt").read_bytes()
        ).hexdigest()
        == fixture["pageSha256"]
    )
    assert fixture["flywheelSourceHash"] == "3289431239790e9dfc14293d63179728f11cdbf691946f8c586fe12b65e115ba"
    assert (
        json.loads(
            (ROOT / "tests/fixtures/agi-alpha-insight-frontier-147-enterprise-acceptance.sources.json.txt").read_bytes()
        )["sourceHash"]
        == fixture["flywheelSourceHash"]
    )
    assert fixture["enterpriseModuleSha256"] == "c74494099f6d1626d4c7a53752d1510be8059970c1e3932763a75fe46f47112b"
    enterprise = ROOT / "tests/fixtures/agi-alpha-insight-frontier-147-enterprise-acceptance.module.py.txt"
    assert hashlib.sha256(enterprise.read_bytes()).hexdigest() == fixture["enterpriseModuleSha256"]
    records = {}
    for name, row in fixture["files"].items():
        body = row["text"].encode()
        assert body == edition_files()[name]
        assert b"agialpha-gallery-2d48e98fb7729779" in body
        assert (len(body), hashlib.sha256(body).hexdigest()) == (row["bytes"], row["sha256"]) == current[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == row["gitBlob"]
        records[name] = current[name]
    matches = [
        profile
        for _, _, _, profile in checkout._source_profiles((ROOT / checkout.CATALOG).read_bytes())
        if all(profile[name] == row for name, row in records.items())
    ]
    assert matches == [current]
    assert len(edition_files()) == 61
    write_files(tmp_path, edition_files())
    report = checkout.refresh(tmp_path)
    assert report["checked"] == 61 and report["needsRefresh"] == []
    assert report["applied"] is False and report["backupDirectory"] is None


def test_enterprise_acceptance_crlf_repair_retains_originals_and_is_idempotent(tmp_path: Path) -> None:
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


@pytest.mark.parametrize("predecessor", ["authority-147", "post-guard-147", "original-147", "reader-1461"])
@pytest.mark.parametrize("mask", range(8))
def test_enterprise_acceptance_partial_worker_mixtures_refuse_before_backup(
    tmp_path: Path, predecessor: str, mask: int
) -> None:
    files = edition_files()
    old = (
        authority_edition_files()
        if predecessor == "authority-147"
        else post_guard_edition_files()
        if predecessor == "post-guard-147"
        else original_edition_files()
        if predecessor == "original-147"
        else reader_workers()
    )
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
def test_enterprise_acceptance_tampered_worker_refuses_before_backup(
    tmp_path: Path, name: str, same_size: bool
) -> None:
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
def test_enterprise_acceptance_missing_worker_refuses_before_backup(tmp_path: Path, name: str) -> None:
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
def test_enterprise_acceptance_symlink_worker_refuses_before_backup(tmp_path: Path, name: str) -> None:
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
def test_enterprise_acceptance_changed_scientific_closure_refuses_before_backup(tmp_path: Path, damage: str) -> None:
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
