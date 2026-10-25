# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest
from fastapi.testclient import TestClient

from alpha_factory_v1.core.runtime.store import Conflict, Journal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("source_candidate_launcher", HERE / "serve_candidate.py")
assert spec is not None and spec.loader is not None
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def exact_date(value):
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


@pytest.fixture
def rig(tmp_path):
    import alpha_factory_v1

    assert not Path(alpha_factory_v1.__file__).is_relative_to(ROOT)
    assert importlib.metadata.version("alpha-factory-v1") == "1.42.0"
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
    journal = Journal.initialize(tmp_path / "journal")
    app = launcher.create_candidate_app(
        journal, registry, node=Path(shutil.which("node")), git=Path(shutil.which("git")), python=Path(sys.executable)
    )
    token = (journal.root / "api.token").read_text().strip()
    headers = {"Authorization": "Bearer " + token, "Origin": "http://testserver"}
    now = datetime.now(timezone.utc)
    payload = app.state.source_assurance_worker.prepare_input(
        "public-guide", "api-source-1", created_at=exact_date(now), expires_at=exact_date(now + timedelta(minutes=10))
    )
    return app, journal, registry, payload, headers


def call(client, action, payload, headers):
    result = client.post("/api/strategy-executor/" + action, json=payload, headers=headers)
    assert result.status_code == 200, result.text
    return result.json()


def test_actual_installed_runtime_auth_exact_approval_download_and_reconnect(rig):
    app, journal, registry, payload, headers = rig
    with TestClient(app) as client:
        assert client.get("/api/strategy-executor/status").status_code == 401
        assert (
            client.post(
                "/api/strategy-executor/prepare", json={}, headers={**headers, "Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert "NON APPROUVÉE" in client.get("/").text
        for path in ("/strategy.js", "/strategy.css"):
            assert client.get(path).status_code == 200
        prepared = call(
            client, "prepare", {"method": "run-mission", "input": payload, "request_id": "source-api-1"}, headers
        )
        ref = {key: prepared[key] for key in ("plan_id", "plan_digest")}
        assert client.post("/api/strategy-executor/run", json=ref, headers=headers).status_code == 409
        call(client, "approve", ref, headers)
        outcome = call(client, "run", ref, headers)
        assert outcome["state"] == "completed" and outcome["outcome"]["verified"] is True
        assert outcome["outcome"]["result"]["operationalAdoption"] == "NOT APPROVED"
        download = outcome["outcome"]["result"]["download"]
        raw = base64.b64decode(download["base64"], validate=True)
        assert len(raw) == download["bytes"] and hashlib.sha256(raw).hexdigest() == download["sha256"]
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert set(archive.namelist()) == {*launcher.worker_module.PAYLOADS, "independent-acceptance.json"}
            assert json.loads(archive.read("independent-acceptance.json"))["accepted"] is True
        exported = client.get("/api/strategy-executor/export/" + ref["plan_id"], headers=headers).json()
        assert exported["body"]["production_authority"] is False
        assert (journal.root / "api.token").read_text().strip() not in json.dumps(exported)
        completed_digest = outcome["outcome_hash"]
    reopened = launcher.create_candidate_app(
        Journal(journal.root),
        registry,
        node=Path(shutil.which("node")),
        git=Path(shutil.which("git")),
        python=Path(sys.executable),
    )
    with TestClient(reopened) as client:
        duplicate = call(client, "run", ref, headers)
        assert duplicate["outcome_hash"] == completed_digest
        status = client.get("/api/strategy-executor/status", headers=headers).json()
        assert len(status["plans"]) == 1 and status["spent"]["service_work"] == 1
    assert len(list((journal.root / "source-assurance" / payload["plan"]["runId"]).glob("reservation-*.json"))) == 1
    journal.verify()


def test_existing_profile_binding_refuses_changed_candidate_registry(rig):
    app, journal, registry, payload, headers = rig
    registry.write_text(registry.read_text().replace('"maxSeconds": 20', '"maxSeconds": 21'))
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/strategy-executor/prepare",
                json={"method": "run-mission", "input": payload, "request_id": "changed-profile"},
                headers=headers,
            ).status_code
            == 422
        )
    with pytest.raises(Conflict, match="policy changed"):
        launcher.create_candidate_app(
            Journal(journal.root),
            registry,
            node=Path(shutil.which("node")),
            git=Path(shutil.which("git")),
            python=Path(sys.executable),
        )


def test_source_policy_does_not_open_new_journal_or_implicitly_adopt_planning_home(rig):
    _, journal, registry, _, _ = rig
    worker = launcher.worker_module.SourceAssuranceWorker(
        registry,
        journal.root / "elsewhere",
        node=Path(shutil.which("node")),
        git=Path(shutil.which("git")),
        python=Path(sys.executable),
    )
    with pytest.raises(ValueError, match="inside the existing journal"):
        launcher.worker_module.candidate_policy(journal, worker)
    assert not worker.output_root.exists()


def test_interruption_after_inner_completion_remains_unknown_on_worker_restart(rig):
    app, journal, registry, payload, headers = rig
    worker = app.state.source_assurance_worker
    original = worker._process

    def interrupt(args, document, seconds, checkpoint):
        result = original(args, document, seconds, checkpoint)
        if document and document.get("operation") == "run":
            raise RuntimeError("simulated interruption before outer verified commit")
        return result

    worker._process = interrupt
    with TestClient(app) as client:
        prepared = call(
            client, "prepare", {"method": "run-mission", "input": payload, "request_id": "interrupted-api"}, headers
        )
        ref = {key: prepared[key] for key in ("plan_id", "plan_digest")}
        call(client, "approve", ref, headers)
        assert client.post("/api/strategy-executor/run", json=ref, headers=headers).status_code == 502
        status = client.get("/api/strategy-executor/status", headers=headers).json()
        assert status["plans"][ref["plan_id"]]["state"] == "unknown"
        assert status["reserved"]["service_work"] == 1 and status["spent"]["service_work"] == 0
    assert (journal.root / "source-assurance" / payload["plan"]["runId"] / "COMPLETE.json").is_file()
    reopened = launcher.create_candidate_app(
        Journal(journal.root),
        registry,
        node=Path(shutil.which("node")),
        git=Path(shutil.which("git")),
        python=Path(sys.executable),
    )
    with TestClient(reopened) as client:
        assert client.post("/api/strategy-executor/run", json=ref, headers=headers).status_code == 409
        reconciled = call(
            client,
            "reconcile",
            {
                "plan_id": ref["plan_id"],
                "record_digest": status["digest"],
                "note": "Inspected isolated interruption; retain uncertain reservation, no replay.",
            },
            headers,
        )
        assert reconciled["state"] == "reconciled"
        after = client.get("/api/strategy-executor/status", headers=headers).json()
        assert after["reserved"]["service_work"] == 1
    assert len(list((journal.root / "source-assurance" / payload["plan"]["runId"]).glob("reservation-*.json"))) == 1


def test_missing_result_after_inner_completion_cannot_be_committed(rig):
    app, journal, _, payload, headers = rig
    worker = app.state.source_assurance_worker
    original = worker._process

    def remove_artifact(args, document, seconds, checkpoint):
        result = original(args, document, seconds, checkpoint)
        if document and document.get("operation") == "run":
            (worker.output_root / payload["plan"]["runId"] / "report.md").unlink()
        return result

    worker._process = remove_artifact
    with TestClient(app) as client:
        prepared = call(
            client, "prepare", {"method": "run-mission", "input": payload, "request_id": "missing-api"}, headers
        )
        ref = {key: prepared[key] for key in ("plan_id", "plan_digest")}
        call(client, "approve", ref, headers)
        assert client.post("/api/strategy-executor/run", json=ref, headers=headers).status_code == 422
        status = client.get("/api/strategy-executor/status", headers=headers).json()
        assert status["plans"][ref["plan_id"]]["state"] == "unknown"
        assert status["reserved"]["service_work"] == 1
        assert "outcome" not in status["plans"][ref["plan_id"]]


def test_concurrent_authenticated_request_refused_without_second_reservation(rig):
    import threading

    app, journal, _, payload, headers = rig
    worker = app.state.source_assurance_worker
    original = worker._process
    entered, release = threading.Event(), threading.Event()

    def hold(args, document, seconds, checkpoint):
        if document and document.get("operation") == "run":
            entered.set()
            if not release.wait(3):
                raise RuntimeError("isolated control did not release")
        return original(args, document, seconds, checkpoint)

    worker._process = hold
    with TestClient(app) as client:
        prepared = call(
            client, "prepare", {"method": "run-mission", "input": payload, "request_id": "concurrent-1"}, headers
        )
        ref = {key: prepared[key] for key in ("plan_id", "plan_digest")}
        call(client, "approve", ref, headers)
        other_payload = json.loads(json.dumps(payload))
        other_payload["plan"]["runId"] = "api-source-concurrent-2"
        other_payload["approval_digest"] = hashlib.sha256(
            launcher.worker_module._canonical(other_payload["plan"])
        ).hexdigest()
        second = call(
            client, "prepare", {"method": "run-mission", "input": other_payload, "request_id": "concurrent-2"}, headers
        )
        ref_second = {key: second[key] for key in ("plan_id", "plan_digest")}
        call(client, "approve", ref_second, headers)
        responses = []
        thread = threading.Thread(
            target=lambda: responses.append(client.post("/api/strategy-executor/run", json=ref, headers=headers))
        )
        thread.start()
        try:
            assert entered.wait(3)
            assert client.post("/api/strategy-executor/run", json=ref_second, headers=headers).status_code == 409
            status = client.get("/api/strategy-executor/status", headers=headers).json()
            assert status["reserved"]["service_work"] == 1
        finally:
            release.set()
            thread.join(5)
        assert responses[0].status_code == 200
        assert not (journal.root / "source-assurance" / "api-source-concurrent-2").exists()


def test_candidate_factory_refuses_wrong_selected_node(rig):
    _, journal, registry, _, _ = rig
    with pytest.raises(ValueError, match="selected Node"):
        launcher.create_candidate_app(
            Journal(journal.root),
            registry,
            node=Path(sys.executable),
            git=Path(shutil.which("git")),
            python=Path(sys.executable),
        )


def test_candidate_factory_refuses_wrong_git_version(rig, tmp_path):
    _, journal, registry, _, _ = rig
    fake = tmp_path / "bin" / "git"
    fake.parent.mkdir()
    fake.write_text("#!/bin/sh\nprintf 'git version 0.0.0\\n'\n")
    fake.chmod(0o700)
    with pytest.raises(ValueError, match="Git 2.51.1"):
        launcher.create_candidate_app(
            Journal(journal.root), registry, node=Path(shutil.which("node")), git=fake, python=Path(sys.executable)
        )


def test_candidate_factory_refuses_changed_public_runtime_source(rig, tmp_path, monkeypatch):
    import alpha_factory_v1

    _, journal, registry, _, _ = rig
    fake = tmp_path / "different-runtime" / "__init__.py"
    fake.parent.mkdir()
    fake.write_text("changed public runtime")
    monkeypatch.setattr(alpha_factory_v1, "__file__", str(fake))
    with pytest.raises(ValueError, match="runtime source differs"):
        launcher.create_candidate_app(
            Journal(journal.root),
            registry,
            node=Path(shutil.which("node")),
            git=Path(shutil.which("git")),
            python=Path(sys.executable),
        )
