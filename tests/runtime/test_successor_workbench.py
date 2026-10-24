# SPDX-License-Identifier: Apache-2.0
"""Real domain work, execution binding, artifact use and native recovery checks."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import hashlib
import json
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import workbench

FAMILIES = ["reliability", "performance", "documentation", "public-data", "numerical"]


def test_concurrent_first_use_waits_for_complete_local_roles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A second real request must not mistake an in-progress first initialization for corruption."""
    from alpha_factory_v1.core.runtime import store

    home = tmp_path / "home"
    journal = Journal.initialize(home)
    spec = workbench.invoke({"operation": "example", "family": "numerical"})
    first_id, second_id = str(uuid.uuid4()), str(uuid.uuid4())
    first_writing, release_writer, second_freezing = threading.Event(), threading.Event(), threading.Event()
    write, freeze = store.private_write, workbench.freeze

    def pause_first_key(path: Path, data: bytes) -> None:
        if path == home / "workbench-principals/local-controller.key":
            first_writing.set()
            assert release_writer.wait(10), "Test driver must release the first creator"
        write(path, data)

    def observe_freeze(current: Journal, submitted: dict[str, Any], run_id: str) -> dict[str, Any]:
        if run_id == second_id:
            second_freezing.set()
        return freeze(current, submitted, run_id)

    monkeypatch.setattr(store, "private_write", pause_first_key)
    monkeypatch.setattr(workbench, "freeze", observe_freeze)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(workbench.execute, home, spec, first_id)
        try:
            assert first_writing.wait(5)
            second = pool.submit(workbench.execute, home, spec, second_id)
            assert second_freezing.wait(5)
            try:
                second.result(timeout=0.5)
            except FutureTimeoutError:
                pass
        finally:
            release_writer.set()
        records = [first.result(timeout=10), second.result(timeout=10)]
    assert [record["state"] for record in records] == ["review", "review"]
    assert {record["run_id"] for record in records} == {first_id, second_id}
    assert all(record["request"] == record["result"]["spec"] == spec for record in records)
    assert journal.verify()["valid"]


@pytest.mark.parametrize("missing", ["principals.json", "local-verifier.key"])
def test_genuinely_partial_work_roles_remain_rejected(missing: str, tmp_path: Path) -> None:
    """Serialization must not turn damaged retained key state into permission to regenerate it."""
    home = tmp_path / "home"
    spec = workbench.invoke({"operation": "example", "family": "numerical"})
    retained_work = workbench.execute(home, spec, str(uuid.uuid4()))
    journal = Journal(home)
    checkpoint = journal.verify()
    roles = home / "workbench-principals"
    (roles / missing).unlink()
    remaining = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in roles.iterdir()}
    with pytest.raises(ValueError, match="incomplete"):
        workbench.execute(home, spec, str(uuid.uuid4()))
    assert not (roles / missing).exists()
    assert {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in roles.iterdir()} == remaining
    assert journal.verify() == checkpoint
    assert journal.latest("@successor-work:" + retained_work["run_id"])["state"] == "review"


@pytest.mark.parametrize("mutation_phase", ["plan", "run"])
def test_submission_captures_nested_inputs_before_validation(
    mutation_phase: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = workbench.invoke({"operation": "example", "family": "documentation"})
    submitted = json.loads(json.dumps(spec))
    original = workbench.invoke

    def mutate_caller(request: dict[str, Any], *args: Any) -> dict[str, Any]:
        if request["operation"] == mutation_phase:
            spec["inputs"]["markdown"] += "\nCaller changed the submitted document."
        return original(request, *args)

    monkeypatch.setattr(workbench, "invoke", mutate_caller)
    home, run_id = tmp_path / "home", str(uuid.uuid4())
    record = workbench.execute(home, spec, run_id)
    assert spec != submitted
    assert record["request"] == submitted
    assert record["request_digest"] == workbench.digest("workbench-request", submitted)
    assert record["result"]["spec"] == submitted
    retained = Journal(home).latest("@successor-work:" + run_id)
    assert retained["request"] == retained["result"]["spec"] == submitted
    assert workbench.execute(home, submitted, run_id)["result_digest"] == record["result_digest"]
    with pytest.raises(Conflict, match="different request"):
        workbench.execute(home, spec, run_id)


def test_large_input_reaches_a_slow_reader_while_checkpoints_continue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real delayed stdin consumption must not strand a partially sent evidence package."""
    worker = tmp_path / "delayed-reader.mjs"
    worker.write_text(
        "await new Promise(resolve=>setTimeout(resolve,350));\n"
        "process.stdin.setEncoding('utf8');let input='';\n"
        "for await(const chunk of process.stdin)input+=chunk;\n"
        "process.stdout.write(JSON.stringify({length:JSON.parse(input).data.length}));\n"
    )
    monkeypatch.setattr(workbench, "WORKER", worker)
    checks: list[bool] = []
    assert workbench.invoke({"data": "x" * 200_000}, lambda: checks.append(True)) == {"length": 200_000}
    assert len(checks) >= 2


@pytest.mark.parametrize("family", FAMILIES)
def test_real_domain_artifacts_and_seven_job_binding(family: str, tmp_path: Path) -> None:
    spec = workbench.invoke({"operation": "example", "family": family})
    pack = workbench.invoke({"operation": "run", "spec": spec})
    assert pack["evaluation"]["authority"] == []
    assert pack["evaluation"]["admission"] == "HOLD"
    assert pack["result"]["artifacts"]
    workbench.write_artifacts(pack, tmp_path / family)
    restored = workbench.invoke({"operation": "inspect", "pack": pack})
    assert restored["spec"] == spec
    assert restored["activeProof"] == restored["activeAuthority"] == []
    if family == "reliability":
        assert pack["result"]["summary"]["defects"] == 2
        result = subprocess.run(["node", str(tmp_path / family / "check.mjs")], capture_output=True, check=True)
        assert b"passed" in result.stdout
    elif family == "public-data":
        assert "295" in (tmp_path / family / "analysis.json").read_text()
    elif family == "numerical":
        assert pack["result"]["summary"]["simpson"] is True


def test_input_identity_and_cosmetic_edit() -> None:
    spec = workbench.invoke({"operation": "example", "family": "reliability"})
    original = workbench.invoke({"operation": "run", "spec": spec})
    spec["name"] = "Une autre Ω"
    renamed = workbench.invoke({"operation": "run", "spec": spec})
    assert renamed["releaseDigest"] == original["releaseDigest"]
    spec["inputs"]["source"] = "export function contains(value, low, high) { return low <= value && value <= high; }"
    changed = workbench.invoke({"operation": "run", "spec": spec})
    assert changed["releaseDigest"] != original["releaseDigest"]
    assert changed["result"]["decision"] == "RETAIN_INCUMBENT"
    assert changed["result"]["summary"]["defects"] == 0


def test_poisoned_import_and_code_are_rejected() -> None:
    spec = workbench.invoke({"operation": "example", "family": "reliability"})
    pack = workbench.invoke({"operation": "run", "spec": spec})
    pack["result"]["artifacts"][0]["name"] = "../escape.mjs"
    with pytest.raises(ValueError):
        workbench.invoke({"operation": "inspect", "pack": pack})
    spec["inputs"]["source"] += "\nprocess.exit(0);"
    with pytest.raises(ValueError, match="SOURCE_GRAMMAR"):
        workbench.invoke({"operation": "run", "spec": spec})


def test_signed_journal_idempotency_review_and_no_overwrite(tmp_path: Path) -> None:
    home, run_id = tmp_path / "operator", str(uuid.uuid4())
    spec = workbench.invoke({"operation": "example", "family": "documentation"})
    record = workbench.execute(home, spec, run_id)
    journal = Journal(home)
    head = journal.verify()
    assert record["state"] == "review"
    assert workbench.execute(home, spec, run_id)["result_digest"] == record["result_digest"]
    assert journal.verify() == head
    workbench.write_artifacts(record["result"], tmp_path / "artifacts")
    with pytest.raises(FileExistsError):
        workbench.write_artifacts(record["result"], tmp_path / "artifacts")
    spec["inputs"]["markdown"] += "\nChanged input."
    with pytest.raises(Conflict, match="different request"):
        workbench.execute(home, spec, run_id)


def test_interrupted_pure_work_requires_explicit_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = workbench.invoke({"operation": "example", "family": "numerical"})
    original, run_id = workbench.invoke, str(uuid.uuid4())

    def interrupt(request: dict[str, Any], *args: Any) -> dict[str, Any]:
        if request["operation"] == "run":
            raise KeyboardInterrupt()
        return original(request, *args)

    monkeypatch.setattr(workbench, "invoke", interrupt)
    with pytest.raises(KeyboardInterrupt):
        workbench.execute(tmp_path / "home", spec, run_id)
    with pytest.raises(Conflict, match="--resume"):
        workbench.execute(tmp_path / "home", spec, run_id)
    monkeypatch.setattr(workbench, "invoke", original)
    result = workbench.execute(tmp_path / "home", spec, run_id, resume=True)
    assert result["attempts"] == 2
    assert result["state"] == "review"


def test_worker_source_is_reproducible() -> None:
    from scripts.generate_successor_workbench import bundle

    _, source_hash, sources = bundle()
    manifest = json.loads(workbench.WORKER.with_name("workbench_sources.json").read_text())
    assert manifest["sourceHash"] == source_hash
    assert manifest["sources"] == json.loads(sources)


def test_stopped_work_cannot_resume_through_pause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, run_id = tmp_path / "home", str(uuid.uuid4())
    spec = workbench.invoke({"operation": "example", "family": "numerical"})
    original = workbench.invoke

    def interrupt(request: dict[str, Any], *args: Any) -> dict[str, Any]:
        if request["operation"] == "run":
            raise KeyboardInterrupt()
        return original(request, *args)

    monkeypatch.setattr(workbench, "invoke", interrupt)
    with pytest.raises(KeyboardInterrupt):
        workbench.execute(home, spec, run_id)
    command = argparse.Namespace(home=home, run_id=run_id, work_command="control", state="stopped")
    stopped = workbench.handle(command)
    command.state = "paused"
    with pytest.raises(Conflict, match="Stopped work"):
        workbench.handle(command)
    assert Journal(home).latest("@successor-work:" + run_id)["digest"] == stopped["digest"]
    monkeypatch.setattr(workbench, "invoke", original)
    with pytest.raises(Conflict, match="Stopped or retired"):
        workbench.execute(home, spec, run_id, resume=True)
    command.state = "retired"
    assert workbench.handle(command)["state"] == "retired"
