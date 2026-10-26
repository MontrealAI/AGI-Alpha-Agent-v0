# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("source_worker", HERE / "source_worker.py")
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SourceAssuranceWorker = module.SourceAssuranceWorker


@pytest.fixture
def rig(tmp_path):
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    registry = tmp_path / "scopes.json"
    registry.write_text(
        json.dumps(
            {
                "schema": "alpha-source-assurance-candidate-profile/v1",
                "maxSeconds": 20,
                "scopes": {"public-guide": {"manifestPath": "docs/try/sources.json", "sourceRef": commit}},
            }
        )
    )
    worker = SourceAssuranceWorker(
        registry,
        tmp_path / "source-assurance",
        node=Path(shutil.which("node")),
        git=Path(shutil.which("git")),
        python=Path(sys.executable),
    )
    now = datetime.now(timezone.utc)

    def fmt(date):
        return date.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    payload = worker.prepare_input(
        "public-guide", "candidate-isolated-1", created_at=fmt(now), expires_at=fmt(now + timedelta(minutes=10))
    )
    limits = {
        "service_work": 1,
        "improvement_work": 0,
        "native_calls": 0,
        "native_solve_seconds": 0,
        "wall_seconds": 45,
        "allow_native": False,
        "source_hash": "a" * 64,
    }
    return worker, payload, limits


def test_real_fixed_runner_independent_verifier_and_customer_zip(rig):
    worker, payload, limits = rig
    charged = []
    outcome = worker.execute("run-mission", payload, limits, lambda **units: charged.append(units))
    assert outcome["verified"] is True
    assert outcome["result"]["operationalAdoption"] == "NOT APPROVED"
    acceptance = outcome["result"]["independentAcceptance"]
    assert acceptance["accepted"] is True and acceptance["checks"] > 100
    assert charged.count({"service_work": 1}) == 1
    bundle = base64.b64decode(outcome["result"]["download"]["base64"], validate=True)
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        assert set(archive.namelist()) == {*module.PAYLOADS, "independent-acceptance.json"}
        assert "committed source identities checked" in archive.read("report.md").decode()
    assert (worker.output_root / payload["plan"]["runId"] / "COMPLETE.json").is_file()


def test_same_source_attempt_cannot_be_silently_replayed_or_renewed(rig):
    worker, payload, limits = rig
    worker.execute("run-mission", payload, limits, lambda **units: None)
    with pytest.raises(ValueError, match="fixed child refused"):
        worker.execute("run-mission", payload, limits, lambda **units: None)
    attempts = list((worker.output_root / payload["plan"]["runId"]).glob("reservation-*.json"))
    assert len(attempts) == 1


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(scope_id="not-installed"),
        lambda value: value["plan"].update(manifestPath="private/inventory.json"),
        lambda value: value["plan"].update(sourceRef="0" * 40),
        lambda value: value["plan"].update(maxAttempts=2),
        lambda value: value["plan"].update(maxTotalSeconds=40),
        lambda value: value.update(approval_digest="b" * 64),
        lambda value: value.update(endpoint="https://example.com"),
    ],
)
def test_changed_scope_paths_budget_digest_or_operations_refuse(rig, change):
    worker, payload, limits = rig
    change(payload)
    with pytest.raises(ValueError):
        worker.execute("run-mission", payload, limits, lambda **units: None)
    assert not worker.output_root.exists()


@pytest.mark.parametrize(
    "field,value", [("allow_native", True), ("native_calls", 1), ("service_work", 2), ("wall_seconds", 5)]
)
def test_unapproved_allowance_refuses_before_writing(rig, field, value):
    worker, payload, limits = rig
    limits[field] = value
    with pytest.raises(ValueError):
        worker.execute("run-mission", payload, limits, lambda **units: None)
    assert not worker.output_root.exists()


def test_registry_change_refuses_before_execution(rig):
    worker, payload, limits = rig
    worker.registry.write_text("{}")
    with pytest.raises(ValueError, match="registry changed"):
        worker.execute("run-mission", payload, limits, lambda **units: None)
    assert not worker.output_root.exists()


def test_linked_output_parent_refuses(rig, tmp_path):
    worker, payload, limits = rig
    target = tmp_path / "target"
    target.mkdir()
    worker.output_root.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="linked"):
        worker.execute("run-mission", payload, limits, lambda **units: None)
    assert not list(target.iterdir())


def test_existing_transport_checkpoint_stop_kills_child_and_retains_no_false_outcome(rig):
    worker, payload, limits = rig
    calls = []

    def stop(**units):
        calls.append(units)
        if len(calls) >= 4:
            raise RuntimeError("existing transport stopped")

    with pytest.raises(RuntimeError, match="transport stopped"):
        worker.execute("run-mission", payload, limits, stop)
    assert calls.count({"service_work": 1}) == 1
    assert not (worker.output_root / payload["plan"]["runId"] / "COMPLETE.json").exists()


def test_missing_local_git_objects_refuse_without_network_or_auto_fetch(rig):
    worker, payload, limits = rig
    worker.scopes["public-guide"]["sourceRef"] = "0" * 40
    with pytest.raises(ValueError, match="fixed child refused"):
        worker.prepare_input(
            "public-guide",
            "missing-object",
            created_at=payload["plan"]["createdAt"],
            expires_at=payload["plan"]["expiresAt"],
        )
    assert not worker.output_root.exists()


def test_descendants_are_terminated_even_after_child_leader_exits(rig, tmp_path):
    worker, _, _ = rig
    marker = tmp_path / "descendant-output"
    child = "import pathlib,time; time.sleep(.25); pathlib.Path(" + repr(str(marker)) + ").write_text('escaped')"
    parent = (
        "import subprocess,sys,json; p=subprocess.Popen([sys.executable,'-c',"
        + repr(child)
        + "]); print(json.dumps({'pid':p.pid}))"
    )
    result = worker._process([sys.executable, "-c", parent], None, 2, lambda **units: None)
    assert result["pid"] > 0
    import time

    time.sleep(0.4)
    assert not marker.exists()


def test_stderr_limit_is_checked_when_fixed_child_exits_immediately(rig):
    worker, _, _ = rig
    with pytest.raises(ValueError, match="stderr exceeded"):
        worker._process(
            [sys.executable, "-c", "import sys;sys.stderr.write('x'*65537);print('{}')"], None, 2, lambda **units: None
        )


def test_rehashed_package_cannot_replace_artifact_after_independent_verification(rig):
    worker, payload, limits = rig
    original = worker._process

    def tamper_after_verification(args, document, seconds, checkpoint):
        result = original(args, document, seconds, checkpoint)
        if document is None:
            (worker.output_root / payload["plan"]["runId"] / "report.md").write_text("incorrect replacement report")
        return result

    worker._process = tamper_after_verification
    with pytest.raises(ValueError, match="artifact changed"):
        worker.execute("run-mission", payload, limits, lambda **units: None)


def test_complete_replacement_after_verification_is_refused(rig):
    worker, payload, limits = rig
    original = worker._process

    def tamper_after_verification(args, document, seconds, checkpoint):
        result = original(args, document, seconds, checkpoint)
        if document is None:
            (worker.output_root / payload["plan"]["runId"] / "COMPLETE.json").write_text("{}")
        return result

    worker._process = tamper_after_verification
    with pytest.raises(ValueError, match="completion changed"):
        worker.execute("run-mission", payload, limits, lambda **units: None)


def test_duplicate_registry_fields_are_refused(tmp_path):
    registry = tmp_path / "registry.json"
    registry.write_text(
        '{"schema":"alpha-source-assurance-candidate-profile/v1","scopes":{},"maxSeconds":1,"maxSeconds":20}'
    )
    with pytest.raises(ValueError, match="duplicate JSON"):
        SourceAssuranceWorker(
            registry,
            tmp_path / "output",
            node=Path(shutil.which("node")),
            git=Path(shutil.which("git")),
            python=Path(sys.executable),
        )


def test_named_file_replacement_during_read_is_refused(tmp_path, monkeypatch):
    target = tmp_path / "artifact"
    target.write_bytes(b"original")
    real_read = module.os.read
    changed = []

    def replace_after_read(fd, count):
        data = real_read(fd, count)
        if data and not changed:
            replacement = tmp_path / "replacement"
            replacement.write_bytes(b"different")
            replacement.replace(target)
            changed.append(True)
        return data

    monkeypatch.setattr(module.os, "read", replace_after_read)
    with pytest.raises(ValueError, match="changed during inspection"):
        module._read(target)


def test_stale_unlisted_wheel_payload_is_rejected(tmp_path):
    source = tmp_path / "component"
    shutil.copytree(
        ROOT / "contrib/strategy_succession",
        source,
        ignore=shutil.ignore_patterns("build", "*.egg-info", "__pycache__", "receipts"),
    )
    output = tmp_path / "build"
    stale = output / "strategy_succession_engineering/worker/retired.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("unlisted stale payload")
    result = subprocess.run(
        [sys.executable, "setup.py", "build_py", "--build-lib", str(output)],
        cwd=source,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert "Build output differs from the exact manifest" in result.stderr
