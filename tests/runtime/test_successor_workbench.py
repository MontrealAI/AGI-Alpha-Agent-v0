# SPDX-License-Identifier: Apache-2.0
"""Real domain work, execution binding, artifact use and native recovery checks."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import workbench

FAMILIES = ["reliability", "performance", "documentation", "public-data", "numerical"]


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


def _thermal_spec(family: str = "delivered-heat") -> dict[str, Any]:
    spec = workbench.invoke({"operation": "example", "family": "thermal-witness"})
    spec["inputs"]["family"] = family
    if family == "heat-capacity":
        spec["inputs"]["extension"] = {
            "sourceId": "sample-acceptance-fixture",
            "kind": "INDEPENDENT_SIMULATED",
            "temperatureRiseUK": {"low": 20_000_000, "estimate": 20_000_000, "high": 20_000_000},
            "lossEnergyMicroJ": {"low": "600000000", "estimate": "600000000", "high": "600000000"},
            "containerEnergyMicroJ": {"low": "80000000", "estimate": "80000000", "high": "80000000"},
        }
    elif family == "heat-recovery":
        spec["inputs"]["extension"] = {
            "sourceId": "energy-acceptance-fixture",
            "kind": "INDEPENDENT_SIMULATED",
            "inputEnergyMicroJ": {"low": "5000000000", "estimate": "5000000000", "high": "5000000000"},
            "storageReleaseMicroJ": {"low": "180000000", "estimate": "180000000", "high": "180000000"},
            "minimumRecoveryPpm": 700_000,
        }
    return spec


def _interrupt_thermal(
    home: Path,
    spec: dict[str, Any],
    run_id: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    resume: bool = False,
) -> None:
    """Interrupt the actual packaged subprocess at its first execution checkpoint."""
    original = workbench.invoke

    def interrupt(request: dict[str, Any], *args: Any) -> dict[str, Any]:
        if request["operation"] == "run":

            def stop() -> None:
                raise KeyboardInterrupt()

            return original(request, stop)
        return original(request, *args)

    with monkeypatch.context() as patch:
        patch.setattr(workbench, "invoke", interrupt)
        with pytest.raises(KeyboardInterrupt):
            workbench.execute(home, spec, run_id, resume=resume)


def _changed_source_worker(destination: Path) -> Path:
    """Model a changed shipped source manifest without rewriting the retained journal."""
    destination.mkdir()
    worker = destination / "workbench_worker.mjs"
    shutil.copyfile(workbench.WORKER, worker)
    manifest = json.loads(workbench.WORKER.with_name("workbench_sources.json").read_text())
    previous = manifest["sourceHash"]
    manifest["sourceHash"] = workbench.digest("test-changed-workbench-source", manifest)
    assert manifest["sourceHash"] != previous
    worker.with_name("workbench_sources.json").write_text(json.dumps(manifest), encoding="utf-8")
    return worker


def test_thermal_example_is_available_through_existing_cli(tmp_path: Path) -> None:
    parser = argparse.ArgumentParser()
    workbench.add_commands(parser.add_subparsers(dest="command", required=True))
    output = tmp_path / "thermal.json"
    args = parser.parse_args(["successor-work", "example", "thermal-witness", "--output", str(output)])
    assert workbench.handle(args) == {"output": str(output.resolve())}
    spec = json.loads(output.read_text())
    assert spec["family"] == "thermal-witness"
    assert spec["inputs"]["family"] == "delivered-heat"
    assert spec["inputs"]["measurement"]["propertyModel"] == "CONSTANT_WITHIN_INTERVAL"


@pytest.mark.parametrize("family", ["delivered-heat", "heat-capacity", "heat-recovery"])
def test_native_thermal_quantities_and_retained_idempotency(family: str, tmp_path: Path) -> None:
    home, run_id = tmp_path / "operator", str(uuid.uuid4())
    spec = _thermal_spec(family)
    record = workbench.execute(home, spec, run_id)
    pack = record["result"]
    result = pack["result"]
    evidence = result["evidence"]
    assert record["state"] == "review" and record["attempts"] == 1
    assert result["decision"] == "CONDITIONAL_BOUNDS_MET"
    assert evidence["family"] == family and evidence["completion"] == "COMPLETE"
    # 0.000092 m3 * 1000 kg/m3 * 4000 J/kg/K * 10 K = 3680 J.
    assert evidence["quantity"]["low"] == evidence["quantity"]["estimate"] == "3680000000"
    assert evidence["quantity"]["high"] == "3680000000"
    if family == "delivered-heat":
        assert evidence["downstream"] is None
    else:
        expected = "150/1" if family == "heat-capacity" else "7/10"
        assert evidence["downstream"]["low"] == evidence["downstream"]["estimate"] == expected
        assert evidence["downstream"]["high"] == expected
    assert evidence["simulation"] is True
    assert evidence["physicalValidity"] == "NOT_ESTABLISHED"
    assert evidence["independentReview"] is False
    assert result["summary"]["acceptedCapability"] is False
    assert record["authority"] == [] and record["settlement"] == "NOT_CONNECTED"
    assert pack["evaluation"]["independentProof"] is False
    assert pack["evaluation"]["admission"] == "HOLD"
    manifest = json.loads(workbench.WORKER.with_name("workbench_sources.json").read_text())
    assert pack["frozen"]["sourceHash"] == manifest["sourceHash"]
    assert len(pack["compilation"]["graph"]["nodes"]) == 7
    journal = Journal(home)
    head = journal.verify()
    assert workbench.execute(home, spec, run_id) == record
    assert journal.verify() == head
    output = tmp_path / "artifacts"
    workbench.write_artifacts(pack, output)
    assert json.loads((output / "thermal-bounds.json").read_text()) == evidence
    restored = workbench.invoke({"operation": "inspect", "pack": pack})
    assert restored["spec"] == spec
    assert restored["activeProof"] == restored["activeAuthority"] == []


@pytest.mark.parametrize(
    ("malformed", "expected_error"),
    [
        ("missing-property-model", "Work adapter rejected"),
        ("empty-extension-key", "object keys must be nonempty printable ASCII strings"),
    ],
)
def test_malformed_thermal_request_creates_no_operator(malformed: str, expected_error: str, tmp_path: Path) -> None:
    spec = _thermal_spec()
    if malformed == "missing-property-model":
        del spec["inputs"]["measurement"]["propertyModel"]
    else:
        spec["inputs"]["extension"] = {"": {"unexpected": True}}
    home = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match=expected_error):
        workbench.execute(home, spec, str(uuid.uuid4()))
    assert not home.exists()


def test_native_thermal_interruption_requires_explicit_same_source_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, run_id = tmp_path / "operator", str(uuid.uuid4())
    spec = _thermal_spec()
    _interrupt_thermal(home, spec, run_id, monkeypatch)
    journal = Journal(home)
    interrupted = journal.latest("@successor-work:" + run_id)
    assert interrupted["state"] == "interrupted"
    assert interrupted["attempts"] == 1 and interrupted["result"] is None
    head = journal.verify()
    with pytest.raises(Conflict, match="--resume"):
        workbench.execute(home, spec, run_id)
    assert journal.verify() == head
    resumed = workbench.execute(home, spec, run_id, resume=True)
    assert resumed["state"] == "review" and resumed["attempts"] == 2
    assert resumed["request_digest"] == interrupted["request_digest"]
    assert resumed["lifecycle"] == interrupted["lifecycle"]
    assert resumed["result"]["result"]["evidence"]["quantity"]["estimate"] == "3680000000"


@pytest.mark.parametrize("decision", ["accepted", "rejected"])
def test_thermal_local_review_binds_exact_result_without_independence(decision: str, tmp_path: Path) -> None:
    home, run_id = tmp_path / "operator", str(uuid.uuid4())
    record = workbench.execute(home, _thermal_spec(), run_id)
    journal = Journal(home)
    head = journal.verify()
    command = argparse.Namespace(
        home=home,
        run_id=run_id,
        work_command="review",
        result_digest="0" * 64,
        decision=decision,
        note="Inspected the exact simulated bounds and retained limitations.",
    )
    with pytest.raises(Conflict, match="Review must bind"):
        workbench.handle(command)
    assert journal.verify() == head
    command.result_digest = record["result_digest"]
    reviewed = workbench.handle(command)
    assert reviewed["state"] == decision
    assert reviewed["review"] == {"note": command.note, "operator": journal.identity, "independent": False}
    assert reviewed["authority"] == [] and reviewed["settlement"] == "NOT_CONNECTED"
    assert reviewed["result"] == record["result"]
    assert reviewed["result_digest"] == record["result_digest"]
    assert reviewed["result"]["result"]["summary"]["acceptedCapability"] is False
    head = journal.verify()
    with pytest.raises(Conflict, match="Review must bind"):
        workbench.handle(command)
    assert journal.verify() == head


@pytest.mark.parametrize("state", ["review", "accepted", "rejected"])
def test_completed_thermal_result_is_exact_without_current_worker(
    state: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, run_id = tmp_path / "operator", str(uuid.uuid4())
    spec = _thermal_spec()
    record = workbench.execute(home, spec, run_id)
    if state != "review":
        record = workbench.handle(
            argparse.Namespace(
                home=home,
                run_id=run_id,
                work_command="review",
                result_digest=record["result_digest"],
                decision=state,
                note="Local review before the simulated software upgrade.",
            )
        )
    journal = Journal(home)
    head = journal.verify()
    changed_worker = _changed_source_worker(tmp_path / "changed-package")
    monkeypatch.setattr(workbench, "WORKER", changed_worker)

    def removed_family(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise ValueError("The upgraded worker no longer supports this request family or schema")

    monkeypatch.setattr(workbench, "invoke", removed_family)
    assert workbench.execute(home, spec, run_id) == record
    assert journal.verify() == head
    assert record["state"] == state and record["authority"] == []
    if state != "review":
        assert record["review"]["independent"] is False
    altered = json.loads(json.dumps(spec))
    altered["inputs"]["policy"]["minimumHeatMicroJ"] = "2000000"
    with pytest.raises(Conflict, match="different request"):
        workbench.execute(home, altered, run_id)
    assert journal.verify() == head


def test_changed_source_refuses_unfinished_thermal_without_consuming_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, run_id = tmp_path / "operator", str(uuid.uuid4())
    spec = _thermal_spec()
    _interrupt_thermal(home, spec, run_id, monkeypatch)
    journal = Journal(home)
    interrupted = journal.latest("@successor-work:" + run_id)
    head = journal.verify()
    changed_worker = _changed_source_worker(tmp_path / "changed-package")
    with monkeypatch.context() as patch:
        patch.setattr(workbench, "WORKER", changed_worker)
        with pytest.raises(Conflict, match="adapter source changed; unfinished work cannot resume"):
            workbench.execute(home, spec, run_id, resume=True)
        assert journal.latest("@successor-work:" + run_id) == interrupted
        assert journal.verify() == head
    # Restoring the previous software allows explicit recovery of its same frozen run.
    resumed = workbench.execute(home, spec, run_id, resume=True)
    assert resumed["state"] == "review" and resumed["attempts"] == 2
    assert resumed["lifecycle"] == interrupted["lifecycle"]


def test_native_thermal_recovery_keeps_the_three_attempt_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, run_id = tmp_path / "operator", str(uuid.uuid4())
    spec = _thermal_spec()
    for attempt in range(3):
        _interrupt_thermal(home, spec, run_id, monkeypatch, resume=attempt > 0)
    journal = Journal(home)
    record = journal.latest("@successor-work:" + run_id)
    assert record["state"] == "interrupted" and record["attempts"] == 3
    head = journal.verify()
    with pytest.raises(Conflict, match="three-attempt budget"):
        workbench.execute(home, spec, run_id, resume=True)
    assert journal.latest("@successor-work:" + run_id) == record
    assert journal.verify() == head
