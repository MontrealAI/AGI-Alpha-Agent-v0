# SPDX-License-Identifier: Apache-2.0
"""Keep partial failures reviewable without weakening the all-demo launch gate."""

import json
import subprocess
import sys

from scripts import validate_demo_catalog as validator


def test_failures_and_timeouts_do_not_hide_later_demo_results(monkeypatch):
    names = ["blocked", "failed", "timeout", "healthy", "reference"]
    entries = [{"id": name, "mode": "Test", "smoke": name != "reference"} for name in names]
    monkeypatch.setattr(validator, "entries", lambda: entries)
    monkeypatch.setattr(validator, "prerequisites_for", lambda entry: {"passed": entry["id"] != "blocked"})
    monkeypatch.setattr(validator, "environment_for", lambda *args: {})
    monkeypatch.setattr(validator, "command_for", lambda entry, output: [entry["id"]])
    launched = []

    def run(command, **kwargs):
        launched.append(command[0])
        if command[0] == "timeout":
            raise subprocess.TimeoutExpired(command, 90, output=b"partial output", stderr=b"\xff")
        return subprocess.CompletedProcess(command, 1 if command[0] == "failed" else 0, "observed result", "")

    monkeypatch.setattr(validator.subprocess, "run", run)
    records = validator.smoke()
    assert [record["status"] for record in records] == ["blocked", "failed", "timeout", "passed"]
    assert launched == ["failed", "timeout", "healthy"]
    assert records[0]["runs"] == 0 and records[1]["exit_codes"] == [1]
    assert records[2]["stdout"] == "partial output"
    json.dumps(records)


def test_failed_smoke_writes_evidence_and_exits_nonzero(tmp_path, monkeypatch):
    output = tmp_path / "evidence/report.json"
    monkeypatch.setattr(sys, "argv", ["validate-demo", "--smoke", "--output", str(output)])
    monkeypatch.setattr(validator, "validate_inventory", lambda: ["failed", "reference"])
    monkeypatch.setattr(validator, "smoke", lambda: [{"demo": "failed", "status": "blocked"}])
    monkeypatch.setattr(validator, "entries", lambda: [{"id": "reference", "smoke": False}])
    assert validator.main() == 1
    report = json.loads(output.read_text())
    assert report["passed"] is False and report["smoke_requested"] is True
    assert report["separate_acceptance"] == ["reference"]


def test_inventory_only_does_not_claim_commands_were_exercised(tmp_path, monkeypatch):
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["validate-demo", "--output", str(output)])
    monkeypatch.setattr(validator, "validate_inventory", lambda: ["demo"])
    monkeypatch.setattr(validator, "entries", lambda: [{"id": "demo", "smoke": True}])
    assert validator.main() == 0
    report = json.loads(output.read_text())
    assert report["smoke_requested"] is False and report["smoke"] == []
