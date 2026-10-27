# SPDX-License-Identifier: Apache-2.0
"""Accept one complete proposed successor without repinning any earlier edition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import refresh_capability_checkout as checkout

ROOT = Path(__file__).resolve().parents[1]
WORKERS = (
    "docs/service-worker.js",
    "docs/assets/service-worker.js",
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)
FIXTURE_SHA256 = "0d6ad501e3b52ec5dccc7cccd1d7fbe7cb3d55691e1e01218b05686547715970"
PREDECESSOR_SHA256 = "9537d6f85cdbf220a1889e55057b3271fb512902fc30b8fe9a79a53cc176591f"


def workers() -> dict:
    raw = (ROOT / "tests/fixtures/capability-checkout-flywheel-147-workers.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    fixture = json.loads(raw)
    assert fixture["schema"] == "agialpha.exact-worker-edition.v1"
    assert fixture["version"] == "1.47.0"
    assert fixture["sourceBase"] == "3947e4ec8fd74ad40e13e8ff825a149fa98a10e9"
    assert (
        fixture["generatorSha256"]
        == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    )
    assert set(fixture["files"]) == set(WORKERS)
    return fixture


def write_closure(root: Path, bodies: dict[str, bytes]) -> None:
    for name, body in bodies.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def closure() -> dict[str, bytes]:
    catalog = json.loads((ROOT / checkout.CATALOG).read_bytes())
    bodies = {
        name: (ROOT / name).read_bytes() for name in set(catalog["sources"]) | set(checkout.FLYWHEEL_147_EXTRA_FILES)
    }
    assert len(bodies) == 61
    return bodies


def test_147_fixture_is_the_exact_current_complete_worker_profile() -> None:
    fixture = workers()
    previous = checkout.PAPER_READERS_1461_EXTRA_FILES
    successor = checkout.FLYWHEEL_147_EXTRA_FILES
    assert set(successor) == set(previous)
    assert {name: record for name, record in successor.items() if name not in WORKERS} == {
        name: record for name, record in previous.items() if name not in WORKERS
    }
    for name, record in fixture["files"].items():
        body = record["text"].encode()
        assert body == (ROOT / name).read_bytes()
        assert b"agialpha-gallery-7ba37fcd0034f367" in body
        assert (len(body), hashlib.sha256(body).hexdigest()) == successor[name]
        assert (record["bytes"], record["sha256"]) == successor[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
        assert successor[name] != previous[name]
    assert (checkout.ENTERPRISE_SOURCE_HASH, 53, 61, successor) in checkout._source_profiles(
        (ROOT / checkout.CATALOG).read_bytes()
    )


def test_147_actual_checkout_is_read_only_and_needs_no_repair() -> None:
    before = closure()
    result = checkout.refresh(ROOT)
    assert result["checked"] == 61 and result["needsRefresh"] == []
    assert result["sourceHash"] == checkout.ENTERPRISE_SOURCE_HASH
    assert result["applied"] is False and result["backupDirectory"] is None
    assert closure() == before


def test_147_and_1461_whole_editions_pass_but_every_mixture_refuses(tmp_path: Path) -> None:
    successor = workers()
    raw = (ROOT / "tests/fixtures/capability-checkout-paper-readers-1461-workers.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PREDECESSOR_SHA256
    previous = json.loads(raw)
    bodies = closure()
    write_closure(tmp_path, bodies)
    for mask in range(8):
        for index, name in enumerate(WORKERS):
            bodies[name] = (successor if mask & (1 << index) else previous)["files"][name]["text"].encode()
            (tmp_path / name).write_bytes(bodies[name])
        if mask in {0, 7}:
            result = checkout.refresh(tmp_path)
            assert result["checked"] == 61 and result["needsRefresh"] == []
            assert result["applied"] is False and result["backupDirectory"] is None
        else:
            with pytest.raises(ValueError, match="unexpected capability bytes"):
                checkout.refresh(tmp_path)
        assert {name: (tmp_path / name).read_bytes() for name in bodies} == bodies


def test_147_each_unknown_worker_refuses_without_backups_or_replacement(tmp_path: Path) -> None:
    bodies = closure()
    root, backups = tmp_path / "checkout", tmp_path / "backups"
    backups.mkdir()
    write_closure(root, bodies)
    for name in WORKERS:
        changed = bodies[name] + b"\n// unreviewed successor worker\n"
        (root / name).write_bytes(changed)
        with pytest.raises(ValueError, match="unexpected capability bytes"):
            checkout.refresh(root, apply=True, backup_parent=backups)
        assert {path: (root / path).read_bytes() for path in bodies} == {**bodies, name: changed}
        assert not list(backups.iterdir())
        (root / name).write_bytes(bodies[name])
