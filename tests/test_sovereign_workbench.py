# SPDX-License-Identifier: Apache-2.0
"""Exercise dependency gating, durable recovery, signed evidence and HTTP boundaries."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import uuid

from cryptography.exceptions import InvalidSignature
from fastapi.testclient import TestClient
import pytest

from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.store import Conflict, Journal, digest
from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.models import Mandate
from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.service import create_app, examples, parse_json
from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.workbench import (
    STAGES,
    Workbench,
    check_stage,
    verify_packet,
)


@pytest.fixture
def bench(tmp_path):
    return Workbench(Journal.initialize(tmp_path / "workspace"))


def create(bench, case="balanced"):
    ident = str(uuid.uuid4())
    bench.create(Mandate.model_validate(examples()[case]), ident)
    return ident


def approve(bench, ident):
    snapshot = bench.snapshot(ident)
    job = snapshot["jobs"][snapshot["next_stage"]]
    return bench.review(ident, job["revision"], digest(job["result"]), True, "Automated test fixture review")


def complete(bench, case="balanced"):
    ident = create(bench, case)
    for stage in STAGES:
        snapshot = bench.advance(ident)
        assert snapshot["state"] == "review" and snapshot["next_stage"] == stage
        approve(bench, ident)
    return ident


@pytest.mark.parametrize("case", list(examples()))
def test_complete_dependency_bound_workflow(bench, case):
    packet = bench.export(complete(bench, case))
    proof = verify_packet(packet, bench.journal.public)
    assert proof["verified"] and proof["checks"]["portfolio"]["optimality_gap"] == 0
    receipts = packet["body"]["receipts"]
    portfolio = receipts["portfolio"]["receipt"]["body"]["document"]["result"]
    schedule = receipts["schedule"]["receipt"]["body"]["document"]["request"]["work"]
    assert {job["id"] for job in schedule["jobs"]} == set(portfolio["selected"])
    if case == "balanced":
        assert set(portfolio["selected"]) == {"contracts", "catalog"}
        assert portfolio["value"] == 2200 and portfolio["baseline_value"] == 1850
    raw = json.dumps(packet)
    assert "api.token" not in raw and "identity.key" not in raw
    assert (bench.journal.root / "api.token").read_text() not in raw


def test_no_implicit_approval_or_export(bench):
    ident = create(bench)
    bench.advance(ident)
    with pytest.raises(Conflict):
        bench.advance(ident)
    with pytest.raises(Conflict):
        bench.export(ident)
    assert len(bench.snapshot(ident)["jobs"]) == 1


def test_rejection_stops_work_and_is_retained(bench):
    ident = create(bench)
    job = bench.advance(ident)["jobs"]["portfolio"]
    bench.review(ident, job["revision"], digest(job["result"]), False, "Assumptions need measurement")
    assert Workbench(Journal(bench.journal.root)).snapshot(ident)["state"] == "rejected"
    with pytest.raises(Conflict):
        bench.advance(ident)
    with pytest.raises(Conflict):
        bench.recover(ident)


@pytest.mark.parametrize("changed", ["revision", "hash"])
def test_review_binds_exact_result(bench, changed):
    ident = create(bench)
    job = bench.advance(ident)["jobs"]["portfolio"]
    with pytest.raises(Conflict):
        bench.review(
            ident,
            job["revision"] + (changed == "revision"),
            "0" * 64 if changed == "hash" else digest(job["result"]),
            True,
            "Review",
        )
    assert bench.snapshot(ident)["state"] == "review"


def test_idempotency_and_submission_crash_recovery(bench, monkeypatch):
    ident = create(bench)
    spec = Mandate.model_validate(examples()["balanced"])
    before = bench.journal.verify()["events"]
    bench.create(spec, ident)
    assert bench.journal.verify()["events"] == before
    with pytest.raises(Conflict):
        bench.create(spec.model_copy(update={"budget": 11}), ident)
    original = bench.journal.submit

    def fail_after_submit(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("Simulated crash after durable submission")

    monkeypatch.setattr(bench.journal, "submit", fail_after_submit)
    with pytest.raises(RuntimeError):
        bench.advance(ident)
    restarted = Workbench(Journal(bench.journal.root))
    assert restarted.advance(ident)["state"] == "review"
    assert len(restarted.journal.missions()) == 1


def test_failure_is_visible_and_explicitly_recoverable(bench, monkeypatch):
    from alpha_factory_v1.core.runtime import work

    ident = create(bench)
    original = work.allocation

    def fail(*args, **kwargs):
        raise RuntimeError("provider-secret")

    monkeypatch.setattr(work, "allocation", fail)
    with pytest.raises(RuntimeError):
        bench.advance(ident)
    snapshot = bench.snapshot(ident)
    assert snapshot["state"] == "failed" and "provider-secret" not in json.dumps(snapshot)
    with pytest.raises(Conflict):
        bench.advance(ident)
    monkeypatch.setattr(work, "allocation", original)
    assert bench.recover(ident)["state"] == "queued"
    assert bench.advance(ident)["state"] == "review"


def test_pause_persists_across_restart_and_blocks_review(bench):
    ident = create(bench)
    bench.advance(ident)
    bench.journal.control(True)
    restarted = Workbench(Journal(bench.journal.root))
    assert restarted.snapshot(ident)["control"] == "paused"
    with pytest.raises(Conflict):
        approve(restarted, ident)
    restarted.journal.control(False)
    assert approve(restarted, ident)["next_stage"] == "schedule"


def test_reviewed_memory_is_reused_but_unreviewed_is_not(bench):
    first = create(bench)
    bench.advance(first)
    second = create(bench)
    assert bench.advance(second)["jobs"]["portfolio"]["stages"][1]["detail"]["parent"] is None
    approve(bench, first)
    third = create(bench)
    job = bench.advance(third)["jobs"]["portfolio"]
    assert job["stages"][1]["detail"]["parent"] == bench.snapshot(first)["jobs"]["portfolio"]["id"]


def test_packet_rejects_tampering_wrong_key_and_dependency_substitution(bench):
    packet = bench.export(complete(bench))
    with pytest.raises(ValueError):
        verify_packet(packet, "00" * 32)
    edited = copy.deepcopy(packet)
    edited["body"]["mandate"]["budget"] += 1
    with pytest.raises(ValueError):
        verify_packet(edited, bench.journal.public)
    edited["sha256"] = digest(edited["body"])
    with pytest.raises(InvalidSignature):
        verify_packet(edited, bench.journal.public)
    edited["signature"] = base64.b64encode(bench.journal.key.sign(bytes.fromhex(edited["sha256"]))).decode()
    with pytest.raises(ValueError, match="predecessors"):
        verify_packet(edited, bench.journal.public)


@pytest.mark.parametrize("field,value", [("budget", True), ("budget", 0), ("max_risk", -1), ("budget", 1.5)])
def test_invalid_mandate_bounds(field, value):
    document = examples()["balanced"]
    document[field] = value
    with pytest.raises(ValueError):
        Mandate.model_validate(document)


def test_duplicate_and_unaffordable_projects_rejected():
    document = examples()["balanced"]
    document["projects"][1]["id"] = document["projects"][0]["id"]
    with pytest.raises(ValueError):
        Mandate.model_validate(document)
    document = examples()["balanced"]
    document["budget"] = 1
    with pytest.raises(ValueError, match="No project"):
        Mandate.model_validate(document)


def test_http_auth_origin_limits_and_literal_inputs(bench):
    headers = {"Authorization": "Bearer " + (bench.journal.root / "api.token").read_text()}
    with TestClient(create_app(bench.journal)) as client:
        assert client.get("/api/status").status_code == 401
        assert client.get("/", headers={"Host": "attacker.invalid"}).status_code == 400
        assert (
            client.post(
                "/api/control", json={"state": "paused"}, headers={**headers, "Origin": "https://attacker.invalid"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/validate",
                content='{"budget":1,"budget":2}',
                headers={**headers, "Content-Type": "application/json"},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/validate", content="x" * (512 * 1024 + 1), headers={**headers, "Content-Type": "application/json"}
            ).status_code
            == 413
        )
        assert client.get("/../../api.token", headers=headers).status_code == 404
        response = client.post(
            "/api/workflows", json={"id": str(uuid.uuid4()), "mandate": examples()["balanced"]}, headers=headers
        )
        assert response.status_code == 201
        ident = response.json()["id"]
        assert client.post(f"/api/workflows/{ident}/advance", json={}, headers=headers).json()["state"] == "review"
        assert client.get(f"/api/workflows/{ident}/export", headers=headers).status_code == 409
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_strict_json(raw):
    with pytest.raises(ValueError):
        parse_json(raw)


def test_originals_are_preserved():
    root = Path(__file__).resolve().parents[1] / "alpha_factory_v1/demos/sovereign_agentic_agialpha_agent_v0/archive"
    manifest = json.loads((root / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize(
    "stage,field",
    [
        ("portfolio", "baseline_value"),
        ("portfolio", "optimal_value"),
        ("schedule", "baseline_makespan"),
        ("schedule", "order"),
        ("brief", "sources"),
    ],
)
def test_independent_checks_reject_false_comparison_or_provenance(bench, stage, field):
    job = bench.snapshot(complete(bench))["jobs"][stage]
    result = copy.deepcopy(job["result"])
    result[field] = [] if field in {"order", "sources"} else result[field] + 1
    with pytest.raises(ValueError):
        check_stage(Mission.model_validate(job["request"]), result)


def test_simultaneous_workers_cannot_duplicate_execution(bench, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from alpha_factory_v1.core.runtime import work

    entered, release = Event(), Event()
    original = work.allocation

    def blocking(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(work, "allocation", blocking)
    ident = create(bench)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(bench.advance, ident)
        try:
            assert entered.wait(10)
            with pytest.raises(Conflict):
                Workbench(Journal(bench.journal.root)).advance(ident)
        finally:
            release.set()
        assert first.result(timeout=10)["state"] == "review"
    assert len(bench.journal.missions()) == 1


def test_cli_smoke_stops_before_approval_and_refuses_overwrite(tmp_path, capsys):
    from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.__main__ import main

    target = tmp_path / "review.json"
    assert main(["smoke", "--output", str(target)]) == 0
    snapshot = json.loads(target.read_text())
    assert snapshot["state"] == "review" and len(snapshot["jobs"]) == 1
    original = target.read_bytes()
    assert main(["smoke", "--output", str(target)]) == 2
    assert target.read_bytes() == original
    assert main(["verify", str(target), "--public-key", "00" * 32]) == 2


def test_public_release_gate_requires_exact_six_packets():
    from scripts.sovereign_evidence import verify_report

    root = Path(__file__).resolve().parents[1]
    demo = "sovereign_agentic_agialpha_agent_v0"
    cases = json.loads((root / "alpha_factory_v1/demos" / demo / "recorded.json").read_text())["cases"]
    report = {
        "schema": "sovereign-browser-v1",
        "passed": True,
        "origin": "https://example.invalid/",
        "native_workflow": False,
        "browser_errors": [],
        "axe_checked": True,
        "mobile_no_overflow": True,
        "release": {"commit": "a" * 40, "version": "1.22.0"},
        "scenarios": [
            {
                "route": prefix + demo + "/",
                "case": name,
                "verified": True,
                "sha256": json.loads(case["packet_json"])["sha256"],
            }
            for prefix in ("", "alpha_factory_v1/demos/")
            for name, case in cases.items()
        ],
    }
    verify_report(report, "a" * 40, "1.22.0", "https://example.invalid/")
    for field, value in [
        ("passed", False),
        ("axe_checked", False),
        ("browser_errors", ["failure"]),
        ("release", {"commit": "b" * 40, "version": "1.22.0"}),
        ("scenarios", report["scenarios"][:5]),
    ]:
        with pytest.raises(ValueError):
            verify_report({**report, field: value}, "a" * 40, "1.22.0", "https://example.invalid/")
    report["scenarios"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        verify_report(report, "a" * 40, "1.22.0", "https://example.invalid/")


def test_preserved_shell_entry_does_not_import_from_working_directory(tmp_path):
    import os
    import shutil
    import subprocess
    import sys

    if not shutil.which("bash"):
        pytest.skip("Bash wrapper; Python module is the cross-platform entry point")
    root = Path(__file__).resolve().parents[1]
    shadow = tmp_path / "alpha_factory_v1"
    shadow.mkdir()
    marker = tmp_path / "shadow-imported"
    (shadow / "__init__.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
    script = (
        root
        / "alpha_factory_v1/demos/sovereign_agentic_agialpha_agent_v0/deploy_sovereign_agentic_agialpha_agent_v0.sh"
    )
    result = subprocess.run(
        ["bash", str(script), "smoke", "--output", str(tmp_path / "result.json")],
        cwd=tmp_path,
        env={**os.environ, "PYTHON": sys.executable},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert json.loads((tmp_path / "result.json").read_text())["state"] == "review"
