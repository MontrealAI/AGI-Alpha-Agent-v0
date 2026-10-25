# SPDX-License-Identifier: Apache-2.0
"""Local identity/history checks; no provider, generated patch or Docker execution."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any
from unittest.mock import Mock

import pytest

from alpha_factory_v1.core.archive import manager
from alpha_factory_v1.core.archive.db import ArchiveDB, ArchiveEntry
from alpha_factory_v1.core.governance.stake_registry import StakeRegistry
from alpha_factory_v1.core.self_evolution import harness

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def memory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    # Do this BEFORE executing the module: its singleton normally probes optional backends.
    monkeypatch.chdir(tmp_path)
    for name in ("PGHOST", "PGUSER", "PGPASSWORD", "NEO4J_URI", "NEO4J_PASSWORD", "NEO4J_PASS", "OPENAI_API_KEY"):
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("VECTOR_STORE_USE_SQLITE", "false")
    for name in ("sentence_transformers", "openai", "psycopg2", "neo4j", "faiss", "prometheus_client", "opentelemetry"):
        monkeypatch.setitem(sys.modules, name, None)
    spec = importlib.util.spec_from_file_location(
        "controlled_memory_identity_fixture", ROOT / "alpha_factory_v1/backend/memory_fabric.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    assert not module.CFG.PGHOST and not module.CFG.NEO4J_URI
    assert module.mem.vector._mode == "ram"
    module._EMBED = lambda _content: [1.0] + [0.0] * (module.CFG.VECTOR_DIM - 1)
    yield module
    module.mem.close()


def test_ram_identity_binds_agent_and_content_and_rejects_conflicts(
    memory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = memory._VectorStore()
    store.add("a", "first")
    store.add("a", "first")
    store.add("b", "first")
    assert store.recent("a") == ["first"] and store.recent("b") == ["first"]
    identity = memory._hash_content("first", "a")
    assert identity.startswith("memory-content-v2:sha256:")
    assert identity != memory._hash_content("first", "b")
    monkeypatch.setattr(memory, "_hash_content", lambda *_args: identity)
    with pytest.raises(memory.MemoryIdentityConflict):
        store.add("a", "different")
    assert store.recent("a") == ["first"] and store._mode == "ram"


def test_sqlite_legacy_rows_ids_and_bytes_survive_additive_identity_column(
    memory: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "legacy.sqlite"
    vector = memory.np.asarray(memory._EMBED("legacy"), dtype="float32").tobytes()
    old = ("1" * 40, "owner", "2020-01-01", vector, "legacy")
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE memories(hash TEXT PRIMARY KEY,agent TEXT,ts TEXT,vec BLOB,content TEXT)")
        connection.execute("INSERT INTO memories VALUES(?,?,?,?,?)", old)
    monkeypatch.setenv("VECTOR_STORE_USE_SQLITE", "true")
    monkeypatch.setenv("VECTOR_SQLITE_PATH", str(path))
    store = memory._VectorStore()
    assert store._mode == "sqlite"
    store.add("owner", "legacy")
    store.add("owner", "fresh")
    store.add("other-owner", "legacy")
    assert (
        store._sql.execute("SELECT hash,agent,ts,vec,content FROM memories WHERE hash=?", (old[0],)).fetchone() == old
    )
    assert store._sql.execute("SELECT content_id FROM memories WHERE hash=?", (old[0],)).fetchone() == (None,)
    assert store._sql.execute("SELECT COUNT(*) FROM memories").fetchone() == (3,)
    assert store._sql.execute(
        "SELECT COUNT(*) FROM memories WHERE hash IS NULL AND content_id LIKE 'memory-content-v2:sha256:%'"
    ).fetchone() == (2,)
    identity = memory._hash_content("fresh", "owner")
    store.close()
    reopened = memory._VectorStore()
    monkeypatch.setattr(memory, "_hash_content", lambda *_args: identity)
    with pytest.raises(memory.MemoryIdentityConflict):
        reopened.add("owner", "forged different body")
    assert reopened._mode == "sqlite" and reopened._sql.execute("SELECT COUNT(*) FROM memories").fetchone() == (3,)
    reopened.close()


def test_sqlite_duplicate_delivery_across_connections_keeps_one_body(
    memory: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("VECTOR_STORE_USE_SQLITE", "true")
    monkeypatch.setenv("VECTOR_SQLITE_PATH", str(tmp_path / "concurrent.sqlite"))
    memory._VectorStore().close()

    def insert(_: int) -> None:
        store = memory._VectorStore()
        try:
            store.add("owner", "same exact body")
            assert store._mode == "sqlite"
        finally:
            store.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(insert, range(2)))
    with sqlite3.connect(tmp_path / "concurrent.sqlite") as connection:
        assert connection.execute("SELECT COUNT(*) FROM memories").fetchone() == (1,)


def manager_fixture(monkeypatch: pytest.MonkeyPatch, path: Path) -> manager.PatchManager:
    monkeypatch.setattr(manager, "run_preflight", Mock())
    monkeypatch.setattr(manager, "_tool_roundtrip", Mock(return_value=True))
    return manager.PatchManager(path)


def test_archive_preserves_legacy_ids_parent_links_and_idempotent_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mgr = manager_fixture(monkeypatch, tmp_path / "archive.sqlite")
    root = ArchiveEntry("1" * 40, None, 7, 2, True, 1)
    legacy = ArchiveEntry("2" * 40, root.hash, 9, 3, True, 2)
    for row in (root, legacy):
        mgr.db.add(row)
    old_body = json.dumps({"diff": "legacy", "parent": root.hash})
    mgr.db.set_state("patch:" + legacy.hash, old_body)
    assert mgr.admit("new patch text", legacy.hash)
    identity = manager.patch_identity("new patch text", legacy.hash)
    original = mgr.db.get(identity)
    assert identity.startswith("archive-patch-v2:sha256:")
    assert identity != manager.patch_identity("new patch text", root.hash)
    assert mgr.admit("new patch text", legacy.hash)
    assert mgr.db.get(identity) == original
    assert mgr.db.get(legacy.hash) == legacy and mgr.db.get(root.hash) == root
    assert mgr.db.get_state("patch:" + legacy.hash) == old_body
    assert [row.hash for row in mgr.db.history(identity)] == [identity, legacy.hash, root.hash]
    reopened = ArchiveDB(tmp_path / "archive.sqlite")
    assert reopened.get(identity) == original


def test_archive_forced_identity_conflict_rejects_without_overwrite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mgr = manager_fixture(monkeypatch, tmp_path / "archive.sqlite")
    assert mgr.admit("original", "parent-a")
    identity = manager.patch_identity("original", "parent-a")
    row, body = mgr.db.get(identity), mgr.db.get_state("patch:" + identity)
    monkeypatch.setattr(manager, "patch_identity", lambda *_args: identity)
    assert not mgr.admit("different", "parent-b")
    assert mgr.db.get(identity) == row and mgr.db.get_state("patch:" + identity) == body


def test_archive_partial_retained_state_cannot_be_overwritten(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mgr = manager_fixture(monkeypatch, tmp_path / "archive.sqlite")
    identity = manager.patch_identity("patch", "parent")
    mgr.db.set_state("patch:" + identity, "independently retained old record")
    assert not mgr.admit("patch", "parent")
    assert mgr.db.get(identity) is None
    assert mgr.db.get_state("patch:" + identity) == "independently retained old record"


def test_archive_two_connections_atomically_keep_first_accepted_record(tmp_path: Path) -> None:
    path = tmp_path / "archive.sqlite"
    ArchiveDB(path)
    entry = ArchiveEntry("archive-patch-v2:sha256:" + "3" * 64, "parent", 0, 0, True, 1)

    def insert(_: int) -> bool:
        return ArchiveDB(path).add_patch_once(entry, '{"diff":"same","parent":"parent"}')

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(insert, range(2)))
    assert sorted(results) == [False, True]
    assert ArchiveDB(path).get(entry.hash) == entry


def repo_fixture(tmp_path: Path, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    (repo / "metric.txt").write_text("1\n")
    (repo / "source.txt").write_text("source-v1")
    return repo


def mock_harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Mock:
    def apply(_repo: Path, _diff: str, *, expected_source_fingerprint: str | None = None) -> tuple[bool, Path]:
        assert expected_source_fingerprint == harness._source_fingerprint(_repo)
        destination = tmp_path / "fixed-mock-result"
        destination.mkdir()
        (destination / "metric.txt").write_text("0.5\n")
        return True, destination

    callback = Mock(side_effect=apply)
    monkeypatch.setattr(harness, "apply_patch", callback)
    monkeypatch.setattr(harness, "_run_tests", Mock(side_effect=AssertionError("must not execute tests")))
    monkeypatch.setattr(harness, "run_preflight", Mock(side_effect=AssertionError("must not execute preflight")))
    return callback


def test_proposal_binds_source_repo_baseline_and_diff(tmp_path: Path) -> None:
    repo = repo_fixture(tmp_path)
    original, _ = harness.proposal_identity(repo, "patch", "1\n")
    assert original.startswith("self-evolution-v2:sha256:")
    assert original == harness.proposal_identity(repo, "patch", "1\n")[0]
    (repo / "source.txt").write_text("source-v2")
    assert original != harness.proposal_identity(repo, "patch", "1\n")[0]
    assert original != harness.proposal_identity(repo_fixture(tmp_path, "other"), "patch", "1\n")[0]
    assert original != harness.proposal_identity(repo, "different patch", "1\n")[0]


def test_legacy_votes_are_retained_but_never_transferred(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = repo_fixture(tmp_path)
    callback = mock_harness(monkeypatch, tmp_path)
    legacy = "a" * 40
    registry = StakeRegistry(stakes={"old-reviewer": 9, "orch": 1}, votes={legacy: {"old-reviewer": True}})
    assert not harness.vote_and_merge(repo, "patch", registry)
    assert registry.votes[legacy] == {"old-reviewer": True}
    new = next(key for key in registry.votes if key != legacy)
    assert registry.votes[new] == {"orch": True}
    assert (repo / "metric.txt").read_text() == "1\n"
    callback.assert_called_once()


def test_unbound_new_votes_or_conflicting_bindings_cannot_be_borrowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = repo_fixture(tmp_path)
    callback = mock_harness(monkeypatch, tmp_path)
    identity, _ = harness.proposal_identity(repo, "patch", "1\n")
    registry = StakeRegistry(stakes={"orch": 1}, votes={identity: {"orch": True}})
    assert not harness.vote_and_merge(repo, "patch", registry)
    callback.assert_not_called()
    registry.votes.clear()
    setattr(registry, "_self_evolution_proposal_bodies", {identity: "different binding"})
    assert not harness.vote_and_merge(repo, "patch", registry)
    callback.assert_not_called()


def test_forced_proposal_collision_rejects_a_second_body(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = repo_fixture(tmp_path)
    callback = mock_harness(monkeypatch, tmp_path)
    registry = StakeRegistry(stakes={"orch": 1, "reviewer": 9})
    original = harness.proposal_identity
    monkeypatch.setattr(
        harness,
        "proposal_identity",
        lambda repo, diff, baseline: ("fixed-strong-test-id", original(repo, diff, baseline)[1]),
    )
    assert not harness.vote_and_merge(repo, "first body", registry)
    before = {key: dict(value) for key, value in registry.votes.items()}
    assert not harness.vote_and_merge(repo, "second body", registry)
    assert registry.votes == before and callback.call_count == 1


@pytest.mark.parametrize("kind", ["file-link", "directory-link", "oversized", "too-many", "fifo"])
def test_proposal_snapshot_refuses_unsafe_or_unbounded_sources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str
) -> None:
    repo = repo_fixture(tmp_path)
    if kind == "file-link":
        (repo / "link").symlink_to(tmp_path / "outside")
    elif kind == "directory-link":
        (repo / "link").symlink_to(tmp_path, target_is_directory=True)
    elif kind == "oversized":
        monkeypatch.setattr(harness, "MAX_SOURCE_FILE_BYTES", 1)
    elif kind == "too-many":
        monkeypatch.setattr(harness, "MAX_SOURCE_FILES", 1)
    else:
        import os

        os.mkfifo(repo / "fifo")
    with pytest.raises((OSError, ValueError)):
        harness.proposal_identity(repo, "patch", "1\n")


def test_proposal_snapshot_detects_source_change_during_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = repo_fixture(tmp_path)
    original = harness.os.fstat
    calls = 0

    def changed(descriptor: int) -> Any:
        nonlocal calls
        calls += 1
        if calls == 2:
            (repo / "source.txt").write_text("different source during snapshot")
        return original(descriptor)

    monkeypatch.setattr(harness.os, "fstat", changed)
    with pytest.raises(ValueError, match="changed"):
        harness.proposal_identity(repo, "patch", "1\n")


def test_faiss_identity_python_route_checks_bodies_before_duplicate_drop(
    memory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = memory._VectorStore()
    store._mode, store._faiss, store._meta, store._vectors = "faiss", Mock(), [], []
    store.add("a", "body")
    store.add("a", "body")
    store.add("b", "body")
    assert store._faiss.add.call_count == 2 and len(store._meta) == 2
    identity = memory._hash_content("body", "a")
    monkeypatch.setattr(memory, "_hash_content", lambda *_args: identity)
    with pytest.raises(memory.MemoryIdentityConflict):
        store.add("a", "different")
    assert store._faiss.add.call_count == 2


@pytest.mark.parametrize("when", ["during-patch", "before-copy"])
def test_source_change_abstains_before_using_votes_or_copying(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, when: str
) -> None:
    repo = repo_fixture(tmp_path)
    callback = mock_harness(monkeypatch, tmp_path)
    registry = StakeRegistry(stakes={"orch": 1})
    archive_accept = Mock()
    monkeypatch.setattr(registry, "archive_accept", archive_accept)
    if when == "during-patch":
        original = callback.side_effect

        def changed(*args: Any, **kwargs: Any) -> tuple[bool, Path]:
            result = original(*args, **kwargs)
            (repo / "source.txt").write_text("changed after snapshot")
            return result

        callback.side_effect = changed
    else:

        def changed_accept(_proposal: str) -> bool:
            (repo / "source.txt").write_text("changed before copying")
            return True

        monkeypatch.setattr(registry, "accepted", changed_accept)
    assert not harness.vote_and_merge(repo, "patch", registry)
    assert (repo / "metric.txt").read_text() == "1\n"
    if when == "during-patch":
        assert registry.votes == {}
    archive_accept.assert_not_called()


@pytest.mark.parametrize("mode", ["ram", "sqlite"])
def test_existing_agent_quota_remains_effective_with_new_identities(
    memory: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str
) -> None:
    monkeypatch.setattr(memory.CFG, "MEM_MAX_PER_AGENT", 1)
    monkeypatch.setenv("VECTOR_STORE_USE_SQLITE", "true" if mode == "sqlite" else "false")
    monkeypatch.setenv("VECTOR_SQLITE_PATH", str(tmp_path / "quota.sqlite"))
    store = memory._VectorStore()
    store.add("owner", "first")
    store.add("owner", "second")
    assert store.recent("owner") == ["second"]
    store.add("owner", "first")
    assert store.recent("owner") == ["first"]
    store.close()


@pytest.mark.parametrize("kind", ["changed-file", "outside-symlink"])
def test_transient_source_change_copied_then_restored_cannot_borrow_proposal_votes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str
) -> None:
    repo = repo_fixture(tmp_path)
    expected = harness._source_fingerprint(repo)
    original = (repo / "source.txt").read_text()
    original_copytree = harness.shutil.copytree
    copied: list[Path] = []
    outside = tmp_path / "outside-inert-fixture.txt"
    outside.write_text("outside inert fixture")

    def copy_transient(src: Path, dst: Path, **kwargs: Any) -> Any:
        copied.append(Path(dst))
        if kind == "changed-file":
            (repo / "source.txt").write_text("transient source copied into sandbox")
        else:
            (repo / "source.txt").unlink()
            (repo / "source.txt").symlink_to(outside)
        try:
            return original_copytree(src, dst, **kwargs)
        finally:
            if (repo / "source.txt").is_symlink():
                (repo / "source.txt").unlink()
            (repo / "source.txt").write_text(original)

    def fixed_patch(_diff: str, *, repo_path: str) -> None:
        (Path(repo_path) / "metric.txt").write_text("0.5\n")

    patch = Mock(side_effect=fixed_patch)
    preflight, tests = Mock(), Mock(return_value=0)
    monkeypatch.setattr(harness.shutil, "copytree", copy_transient)
    monkeypatch.setattr(harness.patcher_core, "apply_patch", patch)
    monkeypatch.setattr(harness, "run_preflight", preflight)
    monkeypatch.setattr(harness, "_run_tests", tests)
    legacy = "a" * 40
    registry = StakeRegistry(stakes={"orch": 1}, votes={legacy: {"orch": True}})
    assert not harness.vote_and_merge(repo, "fixed inert fixture patch", registry)
    assert harness._source_fingerprint(repo) == expected
    assert (repo / "source.txt").read_text() == original
    assert (repo / "metric.txt").read_text() == "1\n"
    assert registry.votes == {legacy: {"orch": True}}
    assert copied and all(not path.exists() for path in copied)
    patch.assert_not_called()
    preflight.assert_not_called()
    tests.assert_not_called()


def test_copied_base_binding_is_verified_before_fixed_patch_and_legacy_calls_stay_compatible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = repo_fixture(tmp_path)
    expected = harness._source_fingerprint(repo)
    seen: list[str] = []

    def fixed_patch(_diff: str, *, repo_path: str) -> None:
        assert harness._source_fingerprint(Path(repo_path)) == expected
        seen.append("fixed patch")

    monkeypatch.setattr(harness.patcher_core, "apply_patch", fixed_patch)
    monkeypatch.setattr(harness, "run_preflight", Mock())
    monkeypatch.setattr(harness, "_run_tests", Mock(return_value=0))
    ok, copied = harness.apply_patch(repo, "fixed fixture", expected_source_fingerprint=expected)
    assert ok and seen == ["fixed patch"]
    harness.shutil.rmtree(copied)
    # This is the original execution API, not a proposal or a vote/authority grant.
    ok, copied = harness.apply_patch(repo, "fixed fixture")
    assert ok and len(seen) == 2
    harness.shutil.rmtree(copied)
