# SPDX-License-Identifier: Apache-2.0
"""Bind one complete publication edition without changing historical identities."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import refresh_capability_checkout as checkout
from tests.test_enterprise_command_authority_147_release import current_files as historical_files
from tests.test_insight_frontier_release import ROOT, WORKERS, snapshot, write_files

FIXTURE = "tests/fixtures/capability-checkout-invention-publication-20261029-workers.json"
FIXTURE_SHA256 = "e685582d438520f700542c6801f200b44a7ada1c06194e9ce4949eb59b33153c"


def publication_files() -> dict[str, bytes]:
    raw = (ROOT / FIXTURE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    fixture = json.loads(raw)
    assert fixture["sourceCommit"] == "562d5eb1043278946b728e6a1fc159f9eb47c287"
    assert fixture["catalogSha256"] == hashlib.sha256((ROOT / checkout.CATALOG).read_bytes()).hexdigest()
    assert fixture["sourceHash"] == checkout.ENTERPRISE_SOURCE_HASH
    assert set(fixture["files"]) == set(WORKERS)
    files = historical_files()
    for name, row in fixture["files"].items():
        body = row["text"].encode()
        assert (len(body), hashlib.sha256(body).hexdigest()) == (row["bytes"], row["sha256"])
        assert (row["bytes"], row["sha256"]) == checkout.INVENTION_PUBLICATION_20261029_EXTRA_FILES[name]
        files[name] = body
    return files


def test_publication_preserves_all_historical_profiles_and_only_changes_three_workers() -> None:
    fixture = json.loads((ROOT / FIXTURE).read_bytes())
    assert len(fixture["predecessorProfiles"]) == 29
    for name, digest in fixture["predecessorProfiles"].items():
        raw = json.dumps(getattr(checkout, name), sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(raw).hexdigest() == digest
    new = checkout.INVENTION_PUBLICATION_20261029_EXTRA_FILES
    old = checkout.ENTERPRISE_COMMAND_AUTHORITY_147_EXTRA_FILES
    assert set(new) == set(old)
    assert {name for name in new if new[name] != old[name]} == set(WORKERS)
    assert fixture["generatorSha256"] == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    files = publication_files()
    for name in WORKERS:
        assert files[name] == (ROOT / name).read_bytes()
        assert b'const RELEASE = "1.47.0";' in files[name]
    result = checkout.refresh(ROOT)
    assert result["checked"] == 61 and result["needsRefresh"] == []
    assert not result["applied"] and result["backupDirectory"] is None


@pytest.mark.parametrize("mask", range(8))
def test_complete_old_or_new_editions_pass_but_all_six_mixtures_refuse(tmp_path: Path, mask: int) -> None:
    files, old = publication_files(), historical_files()
    for index, name in enumerate(WORKERS):
        if not mask & (1 << index):
            files[name] = old[name]
    write_files(tmp_path, files)
    before = snapshot(tmp_path)
    if mask in (0, 7):
        assert checkout.refresh(tmp_path)["needsRefresh"] == []
    else:
        with pytest.raises(ValueError, match="unexpected capability bytes"):
            checkout.refresh(tmp_path, apply=True)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("name", WORKERS)
@pytest.mark.parametrize("mutation", ["same-size", "append"])
def test_modified_publication_workers_refuse_without_writing(tmp_path: Path, name: str, mutation: str) -> None:
    files = publication_files()
    body = files[name]
    files[name] = (b"!" + body[1:]) if mutation == "same-size" else body + b"\n"
    write_files(tmp_path, files)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="unexpected capability bytes"):
        checkout.refresh(tmp_path, apply=True)
    assert snapshot(tmp_path) == before


def test_publication_crlf_repair_retains_originals_and_is_idempotent(tmp_path: Path) -> None:
    files = publication_files()
    original = {name: raw.replace(b"\n", b"\r\n") for name, raw in files.items()}
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, original)
    result = checkout.refresh(root, apply=True, backup_parent=backups)
    assert result["checked"] == 61 and result["applied"]
    backup = Path(result["backupDirectory"])
    assert snapshot(backup / "files") == original
    assert snapshot(root) == files
    assert checkout.refresh(root)["needsRefresh"] == []
    assert len(list(backups.iterdir())) == 1
