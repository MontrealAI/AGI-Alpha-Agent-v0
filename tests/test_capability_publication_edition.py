# SPDX-License-Identifier: Apache-2.0
"""Keep each reviewed paper publication one complete three-worker byte edition."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("publication_refresh", ROOT / "scripts/refresh_capability_checkout.py")
assert SPEC is not None and SPEC.loader is not None
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
WORKERS = (
    "docs/service-worker.js",
    "docs/assets/service-worker.js",
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)
NEXT_FIXTURE_SHA256 = "551dbc6a1e43d7b89246a51c4c8dbc49090de53f4204d31b163597bffd855ec5"
PRECEDING_PUBLICATION = {
    WORKERS[0]: (23501, "d52a0859e4c4d8bf5b4c671beaa76ee44260057df59d496d6fa0d70c1b2f4438"),
    WORKERS[1]: (23938, "dd5752fa2577c376e31f4754b180c8cb1826ecfd6237c0cf10e7ea7527980b15"),
    WORKERS[2]: (26560, "09a14aca276b431cd6e2d369fcdf83dfca40c96101a21ac1027109a223a79040"),
}


def matching_profiles(records):
    raw = (ROOT / HELPER.CATALOG).read_bytes()
    return [
        extra
        for _, _, _, extra in HELPER._source_profiles(raw)
        if all(extra[name] == record for name, record in records.items())
    ]


def current_profile():
    records = {}
    for name in WORKERS:
        raw = (ROOT / name).read_bytes()
        records[name] = len(raw), hashlib.sha256(raw).hexdigest()
    matches = matching_profiles(records)
    assert len(matches) == 1
    assert matches[0] in (
        HELPER.PAPERS_20261026_EXTRA_FILES,
        HELPER.NEXT_UPGRADE_20261026_EXTRA_FILES,
        HELPER.PROFITABLE_WORK_20261027_EXTRA_FILES,
        HELPER.FLYWHEEL_145_EXTRA_FILES,
        HELPER.PROTECTED_FLYWHEEL_146_EXTRA_FILES,
        HELPER.PAPER_READERS_1461_EXTRA_FILES,
        HELPER.FLYWHEEL_147_EXTRA_FILES,
    )
    return matches[0]


def next_workers():
    raw = (ROOT / "tests/fixtures/capability-next-upgrade-20261026-workers.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == NEXT_FIXTURE_SHA256
    fixture = json.loads(raw)
    assert fixture["sourceCommit"] == "6e13a3d261773a713939c2bc6b1b3e1d2a06a0a7"
    assert fixture["sourceTree"] == "d3ae1319b660d77159cb23fd64e0530f12f007a1"
    assert set(fixture["files"]) == set(WORKERS)
    workers = {}
    for name, record in fixture["files"].items():
        body = record["text"].encode()
        assert len(body) == record["bytes"]
        assert hashlib.sha256(body).hexdigest() == record["sha256"]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
        assert HELPER.NEXT_UPGRADE_20261026_EXTRA_FILES[name] == (record["bytes"], record["sha256"])
        workers[name] = body
    return workers


def test_published_workers_have_one_complete_source_bound_edition():
    profile = current_profile()
    for name in WORKERS:
        raw = (ROOT / name).read_bytes()
        size, digest = profile[name]
        assert HELPER._canonical(raw, digest, size, name) == raw
        assert HELPER._canonical(raw.replace(b"\n", b"\r\n"), digest, size, name) == raw


def test_preceding_publication_pins_and_complete_profile_remain_unchanged():
    assert {name: HELPER.PAPERS_20261026_EXTRA_FILES[name] for name in WORKERS} == PRECEDING_PUBLICATION
    assert matching_profiles(PRECEDING_PUBLICATION) == [HELPER.PAPERS_20261026_EXTRA_FILES]


def test_exact_public_next_candidate_has_one_complete_reviewed_profile():
    records = {}
    for name, raw in next_workers().items():
        records[name] = len(raw), hashlib.sha256(raw).hexdigest()
        size, digest = HELPER.NEXT_UPGRADE_20261026_EXTRA_FILES[name]
        assert HELPER._canonical(raw, digest, size, name) == raw
        assert HELPER._canonical(raw.replace(b"\n", b"\r\n"), digest, size, name) == raw
    assert matching_profiles(records) == [HELPER.NEXT_UPGRADE_20261026_EXTRA_FILES]


@pytest.mark.parametrize("name", WORKERS)
def test_preceding_and_published_worker_identities_cannot_form_a_mixed_edition(name):
    records = {path: HELPER.PAPERS_20261026_EXTRA_FILES[path] for path in WORKERS}
    records[name] = HELPER.STRATEGY_144_EXTRA_FILES[name]
    assert matching_profiles(records) == []


@pytest.mark.parametrize("name", WORKERS)
@pytest.mark.parametrize("future_base", [False, True])
def test_new_and_preceding_publications_cannot_be_mixed(name, future_base):
    source, donor = HELPER.PAPERS_20261026_EXTRA_FILES, HELPER.NEXT_UPGRADE_20261026_EXTRA_FILES
    if future_base:
        source, donor = donor, source
    records = {path: source[path] for path in WORKERS}
    records[name] = donor[name]
    assert matching_profiles(records) == []


@pytest.mark.parametrize("name", WORKERS)
def test_published_worker_tampering_is_still_rejected(name):
    raw = (ROOT / name).read_bytes()
    size, digest = current_profile()[name]
    with pytest.raises(ValueError, match="unexpected capability bytes"):
        HELPER._canonical(raw + b"// private edit\n", digest, size, name)


@pytest.mark.parametrize("name", WORKERS)
def test_next_candidate_worker_tampering_is_rejected(name):
    raw = next_workers()[name]
    size, digest = HELPER.NEXT_UPGRADE_20261026_EXTRA_FILES[name]
    with pytest.raises(ValueError, match="unexpected capability bytes"):
        HELPER._canonical(raw + b"// private edit\n", digest, size, name)


@pytest.mark.parametrize("mixed", [None, *WORKERS])
def test_complete_next_checkout_is_read_only_and_mixed_checkout_refuses(tmp_path, mixed):
    catalog = json.loads((ROOT / HELPER.CATALOG).read_bytes())
    names = set(catalog["sources"]) | set(HELPER.NEXT_UPGRADE_20261026_EXTRA_FILES)
    bodies = {name: (ROOT / name).read_bytes() for name in names}
    bodies.update(next_workers())
    if mixed:
        # An authentic older worker is taken from its already pinned fixture.
        old_raw = (ROOT / "tests/fixtures/capability-checkout-release-144-workers.json").read_bytes()
        assert hashlib.sha256(old_raw).hexdigest() == "a36cee1a48c7ddef5c4ed9eecebde04a65d1cf8ea4324bc5439eb769ef23aa81"
        old = json.loads(old_raw)
        bodies[mixed] = old["files"][mixed]["text"].encode()
    for name, body in bodies.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    if mixed:
        with pytest.raises(ValueError, match="unexpected capability bytes"):
            HELPER.refresh(tmp_path)
    else:
        report = HELPER.refresh(tmp_path)
        assert report["checked"] == 61
        assert report["needsRefresh"] == []
        assert report["applied"] is False and report["backupDirectory"] is None
    assert {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == bodies


# Literal identities independently recomputed from the passive publication output.
PROFITABLE_WORK_SOURCE_COMMIT = "0c33e4764b72fafec963c9020daca82f3a090a1c"
PROFITABLE_WORK_PINS = {
    WORKERS[0]: (
        23501,
        "558ce6e044dfbf6f5d330f67aedfa7f02ce276b09578334ed38a9401aa4b6d47",
        "4cd48a7098d6932e72963bd5e30d346e6a7a0293",
    ),
    WORKERS[1]: (
        23938,
        "99aa41c0ca3be166621612ff5110d70a2f651459380a7ecf777c2337f6699ebf",
        "16b1247929d157d61bd08c2b95dd9ecabd0755cc",
    ),
    WORKERS[2]: (
        26560,
        "6fc4239d456bd3b0474a935e6f7d12310621513f6f82288da27ae46f2dce0854",
        "e61b83a04a5ffa1793705d1684c84fb357b10303",
    ),
}


def profitable_workers():
    """Reconstruct exact inert bytes from the unchanged authenticated 27-paper fixture."""
    old = b'const CACHE = "agialpha-gallery-3dd55926d8ce5ef5";'
    new = b'const CACHE = "agialpha-gallery-de1066a749ab5973";'
    workers = {}
    for name, previous in next_workers().items():
        assert previous.count(old) == 1
        body = previous.replace(old, new, 1)
        size, digest, blob = PROFITABLE_WORK_PINS[name]
        assert len(body) == size
        assert hashlib.sha256(body).hexdigest() == digest
        assert hashlib.sha1(b"blob " + str(size).encode() + b"\0" + body).hexdigest() == blob
        assert HELPER.PROFITABLE_WORK_20261027_EXTRA_FILES[name] == (size, digest)
        workers[name] = body
    return workers


@pytest.mark.parametrize("name", WORKERS)
def test_profitable_worker_exact_lf_and_crlf_identity(name):
    body = profitable_workers()[name]
    size, digest, _ = PROFITABLE_WORK_PINS[name]
    assert HELPER._canonical(body, digest, size, name) == body
    assert HELPER._canonical(body.replace(b"\n", b"\r\n"), digest, size, name) == body


@pytest.mark.parametrize("name", WORKERS)
@pytest.mark.parametrize("same_size", [False, True])
def test_profitable_worker_tampering_refuses(name, same_size):
    body = profitable_workers()[name]
    damaged = b"!" + body[1:] if same_size else body + b"// unreviewed\n"
    size, digest, _ = PROFITABLE_WORK_PINS[name]
    with pytest.raises(ValueError, match="unexpected capability bytes"):
        HELPER._canonical(damaged, digest, size, name)


@pytest.mark.parametrize("mask", range(8))
def test_profitable_and_next_complete_checkouts_never_admit_mixed_epochs(tmp_path, mask):
    preceding, future = next_workers(), profitable_workers()
    catalog = json.loads((ROOT / HELPER.CATALOG).read_bytes())
    names = set(catalog["sources"]) | set(HELPER.PROFITABLE_WORK_20261027_EXTRA_FILES)
    bodies = {name: (ROOT / name).read_bytes() for name in names}
    for index, name in enumerate(WORKERS):
        bodies[name] = future[name] if mask & (1 << index) else preceding[name]
    records = {name: (len(bodies[name]), hashlib.sha256(bodies[name]).hexdigest()) for name in WORKERS}
    assert len(matching_profiles(records)) == (1 if mask in (0, 7) else 0)
    for name, body in bodies.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    if mask in (0, 7):
        report = HELPER.refresh(tmp_path)
        assert report["checked"] == 61 and report["needsRefresh"] == []
        assert report["applied"] is False and report["backupDirectory"] is None
    else:
        with pytest.raises(ValueError, match="unexpected capability bytes"):
            HELPER.refresh(tmp_path)
    assert {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == bodies
