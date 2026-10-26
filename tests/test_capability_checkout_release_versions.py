# SPDX-License-Identifier: Apache-2.0
"""Preserve coherent release cache editions without importing held native tests."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import stat

import pytest

from scripts import refresh_capability_checkout as checkout

ROOT = Path(__file__).resolve().parents[1]
WORKERS = (
    "docs/service-worker.js",
    "docs/assets/service-worker.js",
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)
HISTORICAL = {
    "142": (
        "aedc92779c142bded5bf552ecfb3e0b6ba8f8fba",
        "22d11bd0bf799d000c8f82dc9cc108cd5c01ec42",
        "475b146a164d079854d2f2226c37bd51d9d374f01bc69edbf5d8aa24db789178",
    ),
    "143": (
        "5499495911bf8822ac0aa8c9007f00789c1132b5",
        "2258d812b2397cad3055fd56d88183b55ad731f5",
        "12d76aeec92b5efa96f62c54d385aa219b336f109c14905c04d96f095a7dc519",
    ),
    "144": (
        "ff1e5f0a6db7a4858de92927948024b727423606",
        "b1f350271535668f7bf9db259b075fb0d59629ad",
        "a36cee1a48c7ddef5c4ed9eecebde04a65d1cf8ea4324bc5439eb769ef23aa81",
    ),
}
PROFILES = {
    "142": checkout.TI_GUIDE_142_EXTRA_FILES,
    "143": checkout.SOURCE_OPERATION_143_EXTRA_FILES,
    "144": checkout.STRATEGY_144_EXTRA_FILES,
}


def historical_workers(version: str) -> dict[str, bytes]:
    """Load reviewed inert worker bodies; no Git lookup or worker execution."""
    commit, tree, digest = HISTORICAL[version]
    raw = (ROOT / f"tests/fixtures/capability-checkout-release-{version}-workers.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    fixture = json.loads(raw)
    assert fixture["sourceCommit"] == commit
    assert fixture["sourceTree"] == tree
    assert fixture["sourceHash"] == checkout.ENTERPRISE_SOURCE_HASH
    assert set(fixture["files"]) == set(WORKERS)
    result = {}
    for name, record in fixture["files"].items():
        body = record["text"].encode()
        assert len(body) == record["bytes"]
        assert hashlib.sha256(body).hexdigest() == record["sha256"]
        assert PROFILES[version][name] == (record["bytes"], record["sha256"])
        result[name] = body
    return result


def edition_files(version: str) -> dict[str, bytes]:
    catalog = json.loads((ROOT / checkout.CATALOG).read_bytes())
    assert len(catalog["sources"]) == 53
    assert catalog["sourceHash"] == checkout.ENTERPRISE_SOURCE_HASH
    files = {name: (ROOT / name).read_bytes() for name in set(catalog["sources"]) | set(PROFILES[version])}
    if version in HISTORICAL:
        files.update(historical_workers(version))
    assert len(files) == 61
    for name, body in files.items():
        assert b"\r" not in body
        expected = PROFILES[version].get(name)
        if expected is not None:
            assert (len(body), hashlib.sha256(body).hexdigest()) == expected
        else:
            assert hashlib.sha256(body).hexdigest() == catalog["sources"][name]
    return files


def write_files(root: Path, files: dict[str, bytes]) -> None:
    for name, body in files.items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(body)


def snapshot(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("version", PROFILES)
def test_complete_release_edition_repairs_with_exact_backup_and_is_idempotent(tmp_path: Path, version: str) -> None:
    canonical = edition_files(version)
    converted = {name: body.replace(b"\n", b"\r\n") for name, body in canonical.items()}
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, converted)
    before = snapshot(root)

    dry = checkout.refresh(root)
    assert dry["checked"] == 61
    assert dry["sourceHash"] == checkout.ENTERPRISE_SOURCE_HASH
    assert set(dry["needsRefresh"]) == {name for name in canonical if canonical[name] != converted[name]}
    assert dry["applied"] is False and dry["backupDirectory"] is None
    assert snapshot(root) == before and list(backups.iterdir()) == []

    applied = checkout.refresh(root, apply=True, backup_parent=backups)
    assert applied["applied"] is True and applied["checked"] == 61
    assert applied["backupDirectory"] is not None
    backup = Path(applied["backupDirectory"])
    assert backup.parent == backups
    if os.name != "nt":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o700
    manifest = json.loads((backup / "manifest.json").read_bytes())
    assert manifest["sourceHash"] == checkout.ENTERPRISE_SOURCE_HASH
    assert {record["path"] for record in manifest["files"]} == set(before)
    for record in manifest["files"]:
        original = before[record["path"]]
        assert (backup / "files" / record["path"]).read_bytes() == original
        assert record["bytes"] == len(original)
        assert record["sha256"] == hashlib.sha256(original).hexdigest()
    assert json.loads((backup / "result.json").read_bytes())["complete"] is True
    assert snapshot(root) == canonical
    assert checkout.refresh(root)["needsRefresh"] == []
    assert len(list(backups.iterdir())) == 1


@pytest.mark.parametrize("source,donor", itertools.permutations(PROFILES, 2))
@pytest.mark.parametrize("worker", WORKERS)
def test_mixed_release_workers_refuse_before_any_write(tmp_path: Path, source: str, donor: str, worker: str) -> None:
    files = edition_files(source)
    files[worker] = edition_files(donor)[worker]
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    with pytest.raises(ValueError, match="unexpected capability bytes"):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert snapshot(root) == files
    assert list(backups.iterdir()) == []


@pytest.mark.parametrize("damage", ["worker", "source", "catalog", "mixed-line-endings"])
def test_unknown_release_bytes_refuse_the_whole_plan_before_backup(tmp_path: Path, damage: str) -> None:
    files = edition_files("144")
    if damage == "worker":
        files[WORKERS[0]] += b"// unreviewed\n"
    elif damage == "source":
        catalog = json.loads(files[checkout.CATALOG])
        name = sorted(catalog["sources"])[0]
        files[name] += b"\n"
    elif damage == "catalog":
        catalog = json.loads(files[checkout.CATALOG])
        catalog["sourceHash"] = "0" * 64
        files[checkout.CATALOG] = json.dumps(catalog).encode()
    else:
        files[WORKERS[0]] = files[WORKERS[0]].replace(b"\n", b"\r\n", 1)
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_files(root, files)
    with pytest.raises(ValueError):
        checkout.refresh(root, apply=True, backup_parent=backups)
    assert snapshot(root) == files
    assert list(backups.iterdir()) == []
