# SPDX-License-Identifier: Apache-2.0
"""Bind the combined edition while retaining each owner's exact frozen closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import refresh_capability_checkout as checkout
from tests.test_flywheel_147_workers import closure as child_edition_files
from tests.test_frontier_delivery_147_release import current_files as frontier_edition_files
from tests.test_connected_delivery_147_release import current_files as connected_edition_files
from tests.test_flywheel_reconciliation_147_release import current_files as reconciled_edition_files
from tests.test_insight_frontier_enterprise_acceptance_release import edition_files as latest_owner_files
from tests.test_insight_frontier_post_guard_release import edition_files as post_guard_edition_files
from tests.test_insight_frontier_release import (
    HISTORICAL_PROFILES,
    ROOT,
    WORKERS,
    edition_files as original_edition_files,
    predecessor_workers,
    snapshot,
    write_files,
)
from tests.test_insight_frontier_review_authority_release import edition_files as owner_edition_files

FIXTURE = "tests/fixtures/capability-checkout-delivery-guard-147-workers.json"
FIXTURE_SHA256 = "a5ec93aeb618dfd65b0c6692efec0d183e78f10e3370f781e6333403fab094c7"
HISTORICAL_SOURCE_SHA256 = "e421b6e8f8192dbc7ebf0ae784901fda75f8b932fb2bd9ce5e8d49a69b619346"
PREDECESSOR_NAMES = (
    *HISTORICAL_PROFILES,
    "INSIGHT_FRONTIER_147_EXTRA_FILES",
    "INSIGHT_FRONTIER_147_POST_GUARD_EXTRA_FILES",
    "INSIGHT_FRONTIER_147_REVIEW_AUTHORITY_EXTRA_FILES",
    "FLYWHEEL_147_EXTRA_FILES",
    "RECONCILED_FLYWHEEL_147_EXTRA_FILES",
    "INSIGHT_FRONTIER_147_ENTERPRISE_ACCEPTANCE_EXTRA_FILES",
    "CONNECTED_DELIVERY_147_EXTRA_FILES",
    "FRONTIER_DELIVERY_147_EXTRA_FILES",
)
PREDECESSOR_SHA256 = "b779423e2d5fb07e38d5c00c3d9e13843023e8b7bf24dc987210b1f3defcb47e"


def historical_sources() -> dict[str, bytes]:
    raw = (ROOT / "tests/fixtures/delivery-guard-147-historical-source.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == HISTORICAL_SOURCE_SHA256
    value = json.loads(raw)
    assert value["commit"] == "c5164a385f54b59a11b53d70cf491e5e21ad3b18"
    files = {name: text.encode() for name, text in value["files"].items()}
    page = (ROOT / value["page_fixture"]).read_bytes()
    assert hashlib.sha256(page).hexdigest() == value["page_sha256"]
    files["docs/flywheel/index.html"] = page
    return files


def fixture() -> dict:
    raw = (ROOT / FIXTURE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    value = json.loads(raw)
    assert value["version"] == "1.47.0"
    assert value["orderedParents"] == [
        "4be5a593ac08275fc72a446f42502f6de80cd426",
        "372e88f6274ae803c80f8b8c95c3810d52de01ca",
        "d41fc0d2687a9b44079b3c88206cf0fa2c97d59d",
    ]
    assert (
        value["generatorSha256"] == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    )
    enterprise = historical_sources()["alpha_factory_v1/core/runtime/successor/flywheel_enterprise.py"]
    assert value["enterpriseModuleSha256"] == hashlib.sha256(enterprise).hexdigest()
    assert set(value["files"]) == set(WORKERS)
    return value


def current_files() -> dict[str, bytes]:
    files = frontier_edition_files()
    files.update({name: row["text"].encode() for name, row in fixture()["files"].items()})
    assert len(files) == 61
    return files


def test_reconciled_edition_preserves_exact_historical_source_and_both_histories(tmp_path: Path) -> None:
    value = fixture()
    profiles = {name: getattr(checkout, name) for name in PREDECESSOR_NAMES}
    assert len(profiles) == 27
    assert hashlib.sha256(json.dumps(profiles, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == (
        PREDECESSOR_SHA256
    )
    archived = historical_sources()
    assert value["pageSha256"] == hashlib.sha256(archived["docs/flywheel/index.html"]).hexdigest()
    for name, raw in archived.items():
        if name.endswith("-evidence.json"):
            packet = json.loads(raw)
            for field in ("sources", "source_sha256"):
                bindings = packet.get(field)
                if isinstance(bindings, dict):
                    for source, expected in bindings.items():
                        body = archived[source] if source in archived else (ROOT / source).read_bytes()
                        assert hashlib.sha256(body).hexdigest() == expected, source
    before = current_files()
    for name, record in value["files"].items():
        body = before[name]
        assert body == record["text"].encode()
        assert (len(body), hashlib.sha256(body).hexdigest()) == checkout.DELIVERY_GUARD_147_EXTRA_FILES[name]
        assert (record["bytes"], record["sha256"]) == checkout.DELIVERY_GUARD_147_EXTRA_FILES[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
    write_files(tmp_path, before)
    report = checkout.refresh(tmp_path)
    assert report["checked"] == 61 and report["needsRefresh"] == []
    assert report["applied"] is False and report["backupDirectory"] is None
    assert current_files() == before


@pytest.mark.parametrize(
    "predecessor",
    [
        "frontier",
        "connected",
        "latest-owner",
        "reconciled-child",
        "owner",
        "child",
        "post-guard",
        "original",
        "readers",
    ],
)
@pytest.mark.parametrize("mask", range(8))
def test_complete_editions_pass_and_partial_cross_owner_mixtures_refuse(
    tmp_path: Path, predecessor: str, mask: int
) -> None:
    old = {
        "frontier": frontier_edition_files,
        "connected": connected_edition_files,
        "latest-owner": latest_owner_files,
        "reconciled-child": reconciled_edition_files,
        "owner": owner_edition_files,
        "child": child_edition_files,
        "post-guard": post_guard_edition_files,
        "original": original_edition_files,
        "readers": predecessor_workers,
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
@pytest.mark.parametrize("damage", ["same-size", "missing"])
def test_unknown_reconciled_workers_refuse_before_backup(tmp_path: Path, name: str, damage: str) -> None:
    files = current_files()
    if damage == "missing":
        del files[name]
    else:
        files[name] = b"!" + files[name][1:]
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    before = snapshot(root)
    with pytest.raises((ValueError, FileNotFoundError)):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert snapshot(root) == before and list(backups.iterdir()) == []
