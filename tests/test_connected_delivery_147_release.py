# SPDX-License-Identifier: Apache-2.0
"""Bind the combined edition while retaining each owner's exact frozen closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import refresh_capability_checkout as checkout
from tests.test_flywheel_147_workers import closure as child_edition_files
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

FIXTURE = "tests/fixtures/capability-checkout-connected-delivery-147-workers.json"
FIXTURE_SHA256 = "b52776ac53127b8c19f3f04168d9ac5867b2788a748933fed0577d2c2726e0cb"
PREDECESSOR_NAMES = (
    *HISTORICAL_PROFILES,
    "INSIGHT_FRONTIER_147_EXTRA_FILES",
    "INSIGHT_FRONTIER_147_POST_GUARD_EXTRA_FILES",
    "INSIGHT_FRONTIER_147_REVIEW_AUTHORITY_EXTRA_FILES",
    "FLYWHEEL_147_EXTRA_FILES",
    "RECONCILED_FLYWHEEL_147_EXTRA_FILES",
    "INSIGHT_FRONTIER_147_ENTERPRISE_ACCEPTANCE_EXTRA_FILES",
)
PREDECESSOR_SHA256 = "a28136ab1dac6c4c34f63af33f5fa7c4c6d0e2a212373e03006a79f7138576d7"


def fixture() -> dict:
    raw = (ROOT / FIXTURE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    value = json.loads(raw)
    assert value["version"] == "1.47.0"
    assert value["orderedParents"] == [
        "509376b62f46973ac730e39cbc809c528ee495fa",
        "dae93bd3ed5fc8978e83d8d53f98594e0e9125a0",
    ]
    assert (
        value["generatorSha256"] == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    )
    assert (
        value["enterpriseModuleSha256"]
        == hashlib.sha256(
            (ROOT / "alpha_factory_v1/core/runtime/successor/flywheel_enterprise.py").read_bytes()
        ).hexdigest()
    )
    assert set(value["files"]) == set(WORKERS)
    return value


def current_files() -> dict[str, bytes]:
    catalog = json.loads((ROOT / checkout.CATALOG).read_bytes())
    names = set(catalog["sources"]) | set(checkout.CONNECTED_DELIVERY_147_EXTRA_FILES)
    assert len(names) == 61
    rows = fixture()["files"]
    return {name: rows[name]["text"].encode() if name in rows else (ROOT / name).read_bytes() for name in names}


def test_connected_historical_edition_preserves_its_frozen_source_and_both_histories() -> None:
    value = fixture()
    profiles = {name: getattr(checkout, name) for name in PREDECESSOR_NAMES}
    assert len(profiles) == 25
    assert hashlib.sha256(json.dumps(profiles, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == (
        PREDECESSOR_SHA256
    )
    historical_page = ROOT / "tests/fixtures/connected-delivery-147-page.html.txt"
    assert value["pageSha256"] == hashlib.sha256(historical_page.read_bytes()).hexdigest()
    before = current_files()
    for name, record in value["files"].items():
        body = before[name]
        assert body == record["text"].encode()
        assert (len(body), hashlib.sha256(body).hexdigest()) == checkout.CONNECTED_DELIVERY_147_EXTRA_FILES[name]
        assert (record["bytes"], record["sha256"]) == checkout.CONNECTED_DELIVERY_147_EXTRA_FILES[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
    report = checkout.refresh(ROOT)
    assert report["checked"] == 61 and report["needsRefresh"] == []
    assert report["applied"] is False and report["backupDirectory"] is None
    assert current_files() == before


@pytest.mark.parametrize(
    "predecessor", ["latest-owner", "reconciled-child", "owner", "child", "post-guard", "original", "readers"]
)
@pytest.mark.parametrize("mask", range(8))
def test_complete_editions_pass_and_partial_cross_owner_mixtures_refuse(
    tmp_path: Path, predecessor: str, mask: int
) -> None:
    old = {
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
