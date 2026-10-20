# SPDX-License-Identifier: Apache-2.0
"""Check actual public-source execution and independent failure-sensitive evidence."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from scripts.reproduce_public_preparation_pilot import FIXTURES, check_summary, load_input, run_pilot
from tests.runtime import test_transformation_model

local_provider = test_transformation_model.local_provider


def test_actual_public_document_artifact_comparators_and_successful_reverse_import(tmp_path):
    report = run_pilot(tmp_path / "native")
    native = report["native"]
    assert native["phase"] == "completed"
    assert native["result"]["beats_unrestricted"] is False
    assert native["result"]["decision"] == "propose-reuse-pending-independent-review"
    assert native["review"] == {"status": "pending", "independent": False}
    assert len(report["development_attempts"]) == 5
    assert set(report["independent_checks"]) == {
        "candidate",
        "lead-order",
        "audit-after-draft",
        "weighted-without-dependencies",
        "unrestricted-exact-search",
    }
    assert report["independent_checks"]["candidate"]["all_selected_prerequisites_present"]
    assert not report["independent_checks"]["weighted-without-dependencies"]["all_selected_prerequisites_present"]
    assert report["recovery"]["reopened_identically"] and report["recovery"]["history_imported"]
    assert report["recovery"]["verified_journal_events"]["valid"]
    assert report["recovery"]["imported_authority"] is None
    assert report["model"] is None and report["costs"]["paid_model_calls"] == 0
    assert report["costs"]["human_effort_seconds"] is None
    assert report["costs"]["timing"]["process_cpu_microseconds"] > 0
    assert "calibrated" in " ".join(report["limitations"])


@pytest.mark.parametrize("target", ["ubuntu-ephemeral-creator.md", "input.json"])
def test_replaced_source_or_annotation_rejected_before_private_state_and_artifact(tmp_path, target):
    folder = tmp_path / "inputs"
    shutil.copytree(FIXTURES, folder)
    (folder / target).write_bytes((folder / target).read_bytes() + b"\nmodified")
    with pytest.raises(ValueError, match="checksum mismatch"):
        run_pilot(tmp_path / "native", fixtures=folder)
    assert not (tmp_path / "native").exists()
    assert not (tmp_path / "native-independent-import").exists()


@pytest.fixture
def completed(tmp_path):
    report = run_pilot(tmp_path / "native")
    return load_input()["documents"]["confirmation"], report["native"]["result"]["results"]["candidate"][0]


@pytest.mark.parametrize("edit", ["text", "references", "score", "dependency", "duplicate", "unknown", "too-long"])
def test_independent_checker_rejects_source_sink_and_score_forgeries(completed, edit):
    document, original = completed
    result = copy.deepcopy(original)
    if edit == "text":
        result["text"] += " This is a general intelligence breakthrough."
    elif edit == "references":
        result["references"][0]["provenance"] = "unverified newer source"
    elif edit == "score":
        result["score_millionths"] = 1_000_000
    elif edit == "dependency":
        result["supported_claims"] = []
    elif edit == "duplicate":
        result["selected"][1] = result["selected"][0]
    elif edit == "unknown":
        result["selected"][0] = "invented"
    else:
        result["selected"] = [item["id"] for item in document["claims"]]
    with pytest.raises(ValueError):
        check_summary(document, result, 3)


def test_same_actual_pilot_through_labeled_http_contract_fixture(tmp_path, local_provider):
    config, trace, _ = local_provider
    config_file = tmp_path / "local-model.json"
    config_file.write_text(config.model_dump_json())
    report = run_pilot(tmp_path / "native", model_config=config_file)
    assert len(trace) == 1
    assert report["model"]["provider_evidence"]["reported_model"] == "http-contract-fixture"
    assert report["model"]["costs"]["consumed_model_calls"] == 1
    assert report["independent_checks"]["candidate"]["source_exact"]
    request_text = trace[0][2]["messages"][1]["content"]
    assert "A new creator does not invalidate" not in request_text
    assert report["native"]["result"]["beats_unrestricted"] is False


def test_paid_or_remote_provider_not_supported_even_when_pilot_requested(tmp_path):
    config_file = tmp_path / "remote.json"
    config_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "endpoint": "https://example.com/v1",
                "model": "unsupported",
                "declared_revision": "unknown",
                "no_charge": True,
            }
        )
    )
    with pytest.raises(ValueError):
        run_pilot(tmp_path / "native", model_config=config_file)
    assert not (tmp_path / "native").exists()


def test_model_failure_retains_consumed_call_without_false_success(tmp_path, local_provider):
    from scripts.reproduce_public_preparation_pilot import PilotFailure

    config, trace, response = local_provider
    response.clear()
    response["unsupported"] = "not a model proposal"
    config_file = tmp_path / "local-model.json"
    config_file.write_text(config.model_dump_json())
    with pytest.raises(PilotFailure) as failure:
        run_pilot(tmp_path / "native", model_config=config_file)
    assert len(trace) == 1
    assert failure.value.evidence["retained_state"] == "uncertain"
    assert failure.value.evidence["call_permit_consumed"]
    assert failure.value.evidence["retry_allowed"] is False
    assert failure.value.evidence["authority"] == "none"
    assert "native" not in failure.value.evidence


def test_rejected_credential_configuration_does_not_echo_secret_or_create_state(tmp_path):
    config_file = tmp_path / "local.json"
    config_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "endpoint": "http://operator:sensitive-value@127.0.0.1/v1",
                "model": "local",
                "declared_revision": "unknown",
                "no_charge": True,
            }
        )
    )
    with pytest.raises(ValueError) as failure:
        run_pilot(tmp_path / "native", model_config=config_file)
    assert "sensitive-value" not in str(failure.value)
    assert not (tmp_path / "native").exists()


def test_release_real_weight_job_requires_actual_ti_pilot_and_cannot_soft_fail():
    import yaml

    root = Path(__file__).resolve().parents[2]
    release = yaml.load((root / ".github/workflows/agent-release.yml").read_text(), Loader=yaml.BaseLoader)
    assert "real-model" in release["jobs"]["package"]["needs"]
    model_job = release["jobs"]["real-model"]
    assert "if" not in model_job and "continue-on-error" not in model_job
    command = next(step for step in model_job["steps"] if "scripts.validate_agent_model" in step.get("run", ""))
    assert "--with-ti-public-pilot" in command["run"]
    assert "if" not in command and "continue-on-error" not in command
    assert "3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597" in command["run"]


@pytest.mark.parametrize("action,expected", [("pause", "paused-consumed"), ("cancel", "canceled")])
def test_late_actual_http_response_after_control_preserves_failure_evidence(tmp_path, monkeypatch, action, expected):
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from scripts.reproduce_public_preparation_pilot import PilotFailure
    from alpha_factory_v1.core.runtime.successor.transformation_model import ModelDiscovery

    calls, captured, controls, control_finished = [], [], [], []
    control_done = threading.Event()
    original_create = ModelDiscovery.create

    def capture_create(self, request, config):
        result = original_create(self, request, config)
        captured.append((self, request.campaign_id))
        return result

    monkeypatch.setattr(ModelDiscovery, "create", capture_create)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            # Apply control after the actual request arrives and before its response.
            # Cold native setup is outside this ordering contract and has no fixture timer.
            driver, campaign_id = captured[0]
            driver.control(campaign_id, action)
            controls.append(action)
            control_finished.append(time.monotonic())
            control_done.set()
            proposal = {
                "schema_version": 1,
                "candidates": [
                    {
                        "schema_version": 1,
                        "program": {
                            "schema_version": 1,
                            "schema": "selection-program/v1",
                            "representation": "argument-graph",
                            "production": "closure-search",
                        },
                        "hypothesis": "Retain prerequisite closure.",
                    }
                ],
            }
            body = json.dumps(
                {
                    "model": "delayed-http-contract-fixture",
                    "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal)}}],
                    "usage": {},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config_file = tmp_path / "local.json"
    config_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "endpoint": f"http://127.0.0.1:{server.server_port}/v1",
                "model": "local-fixture",
                "declared_revision": "fixture",
                "no_charge": True,
            }
        )
    )
    try:
        with pytest.raises(PilotFailure) as failure:
            run_pilot(tmp_path / "native", model_config=config_file)
        finished = time.monotonic()
        assert control_done.wait(timeout=5)
        assert len(control_finished) == 1
        # Cancellation may finish before control returns; a later failure must finish within five seconds.
        assert finished <= control_finished[0] + 5
        driver, campaign_id = captured[0]
        assert controls == [action]
        assert failure.value.evidence["retained_state"] == expected
        assert failure.value.evidence["call_permit_consumed"]
        assert failure.value.evidence["retry_allowed"] is False
        assert driver.show(campaign_id)["proposal"] is None
        assert len(calls) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
