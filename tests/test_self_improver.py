# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

import pytest
from alpha_factory_v1.core.self_evolution import self_improver
from typing import Any

pytest.importorskip("prometheus_client")

git = pytest.importorskip("git")


def _init_repo(path: Path) -> Any:
    repo = git.Repo.init(path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "CI User")
        writer.set_value("user", "email", "ci@example.com")
    (path / "metric.txt").write_text("1\n")
    repo.git.add("metric.txt")
    repo.index.commit("init")
    return repo


def test_improve_repo(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _init_repo(repo_dir)

    patch = """--- a/metric.txt\n+++ b/metric.txt\n@@ -1 +1 @@\n-1\n+2\n"""
    patch_file = tmp_path / "patch.diff"
    patch_file.write_text(patch)
    log_file = tmp_path / "log.json"

    delta, clone = self_improver.improve_repo(
        str(repo_dir), str(patch_file), "metric.txt", str(log_file), cleanup=False
    )

    assert delta == 1
    assert (clone / "metric.txt").read_text().strip() == "2"
    data = json.loads(log_file.read_text())
    assert data and data[0]["delta"] == 1


def test_improve_repo_invalid_patch(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _init_repo(repo_dir)

    patch_file = tmp_path / "patch.diff"
    patch_file.write_text("")
    log_file = tmp_path / "log.json"

    with pytest.raises(ValueError):
        self_improver.improve_repo(str(repo_dir), str(patch_file), "metric.txt", str(log_file))


def test_improve_repo_cleanup(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _init_repo(repo_dir)

    patch = """--- a/metric.txt\n+++ b/metric.txt\n@@ -1 +1 @@\n-1\n+2\n"""
    patch_file = tmp_path / "patch.diff"
    patch_file.write_text(patch)
    log_file = tmp_path / "log.json"

    delta, clone = self_improver.improve_repo(str(repo_dir), str(patch_file), "metric.txt", str(log_file), cleanup=True)

    assert delta == 1
    assert not clone.exists()


def test_improve_repo_requires_git(monkeypatch, tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    patch_file = tmp_path / "p.diff"
    patch_file.write_text("dummy")
    log_file = tmp_path / "log.json"

    monkeypatch.setattr(self_improver, "git", None)
    with pytest.raises(RuntimeError):
        self_improver.improve_repo(str(repo_dir), str(patch_file), "metric.txt", str(log_file))


from alpha_factory_v1.common.utils import config, messaging  # noqa: E402
from alpha_factory_v1.core.agents.self_improver_agent import SelfImproverAgent  # noqa: E402
from prometheus_client import REGISTRY  # noqa: E402


class DummyLedger:
    def log(self, _env) -> None:
        pass

    def start_merkle_task(self, *_a, **_kw) -> None:
        pass

    async def stop_merkle_task(self) -> None:
        pass

    def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_self_improver_agent_apply(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _init_repo(repo_dir)
    patch = """--- a/metric.txt\n+++ b/metric.txt\n@@ -1 +1 @@\n-1\n+2\n"""
    patch_file = tmp_path / "p.diff"
    patch_file.write_text(patch)
    bus = messaging.A2ABus(config.Settings(bus_port=0))
    agent = SelfImproverAgent(bus, DummyLedger(), str(repo_dir), str(patch_file), allowed=["metric.txt"])
    await agent.run_cycle()
    assert (repo_dir / "metric.txt").read_text().strip() == "2"
    REGISTRY._names_to_collectors.clear()
    REGISTRY._collector_to_names.clear()


@pytest.mark.asyncio
async def test_self_improver_agent_rollback(monkeypatch, tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _init_repo(repo_dir)
    patch = """--- a/metric.txt\n+++ b/metric.txt\n@@ -1 +1 @@\n-1\n+2\n"""
    patch_file = tmp_path / "p.diff"
    patch_file.write_text(patch)
    bus = messaging.A2ABus(config.Settings(bus_port=0))
    agent = SelfImproverAgent(bus, DummyLedger(), str(repo_dir), str(patch_file), allowed=["metric.txt"])
    orig_commit = git.Repo(repo_dir).head.commit.hexsha

    def fail_commit(self, *a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(git.index.base.IndexFile, "commit", fail_commit)
    with pytest.raises(RuntimeError):
        await agent.run_cycle()
    assert git.Repo(repo_dir).head.commit.hexsha == orig_commit
    assert (repo_dir / "metric.txt").read_text().strip() == "1"
    REGISTRY._names_to_collectors.clear()
    REGISTRY._collector_to_names.clear()
