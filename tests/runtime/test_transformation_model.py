# SPDX-License-Identifier: Apache-2.0
"""Exercise a real local HTTP provider contract without a paid or claimed real model."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.transformation import DiscoveryRequest, pilot_document, pilot_request
from alpha_factory_v1.core.runtime.successor.transformation_model import (
    KEY,
    LocalModelConfig,
    ModelDiscovery,
    ModelProposal,
    ProviderEvidence,
    NO_KEY_ENV,
    validate_model_envelope,
)


@pytest.fixture
def local_provider():
    trace = []
    reply = {
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
                "hypothesis": "Prerequisite closure may improve declared coverage.",
            }
        ],
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            trace.append(
                (self.path, dict(self.headers), json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            )
            body = json.dumps(
                {
                    "model": "http-contract-fixture",
                    "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(reply)}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 30},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield LocalModelConfig(
        endpoint=f"http://127.0.0.1:{server.server_port}/v1",
        model="configured-local-model",
        declared_revision="operator-declared-not-attested",
        no_charge=True,
    ), trace, reply
    server.shutdown()
    server.server_close()
    thread.join()


def prepare(tmp_path, config):
    driver = ModelDiscovery(Journal.initialize(tmp_path / "agent"))
    raw = pilot_request().model_dump()
    raw["operator_ids"] = ["local-model-proposals"]
    request = DiscoveryRequest.model_validate(raw)
    record = driver.create(request, config)
    return driver, request, record


def accepted(tmp_path, config):
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    driver.propose(request.campaign_id)
    return driver, request


def test_actual_http_call_then_independent_native_complete_campaign(tmp_path, local_provider):
    config, trace, _ = local_provider
    driver, request, record = prepare(tmp_path, config)
    assert trace == []
    with pytest.raises(PermissionError):
        driver.propose(request.campaign_id)
    with pytest.raises(Conflict):
        driver.approve(request.campaign_id, "0" * 64)
    driver.approve(request.campaign_id, record["binding_digest"])
    proposed = driver.propose(request.campaign_id)
    assert proposed["state"] == "proposed" and len(trace) == 1
    path, headers, payload = trace[0]
    assert path == "/v1/chat/completions" and "Authorization" not in headers
    assert "confirmation" not in payload["messages"][1]["content"]
    assert payload["max_tokens"] == config.max_output_tokens
    loop, _ = driver.native(request.campaign_id)
    queued = loop.show(request.campaign_id)
    with pytest.raises(PermissionError):
        loop.step(request.campaign_id, operation_id="without-second-permit")
    loop.approve(request.campaign_id, queued["binding_digest"])
    for phase in ("diagnose", "develop", "freeze"):
        frozen = loop.step(request.campaign_id, operation_id=phase)
    envelope = driver.compare(request.campaign_id, [pilot_document(confirmation=True)], frozen["freeze"]["digest"])
    assert validate_model_envelope(envelope) == envelope
    assert envelope["native_envelope"]["result"]["beats_unrestricted"] is False
    assert envelope["native_envelope"]["review"]["status"] == "pending"
    assert envelope["costs"]["consumed_model_calls"] == 1
    resumed = ModelDiscovery(Journal(driver.journal.root))
    resumed.propose(request.campaign_id)
    assert resumed.envelope(request.campaign_id) == envelope and len(trace) == 1


def test_model_projection_keeps_original_provenance_in_native_binding(tmp_path, local_provider):
    from alpha_factory_v1.core.runtime.successor.protocol import canonical
    from alpha_factory_v1.core.runtime.successor.transformation_model import _payload

    config, trace, _ = local_provider
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    driver.propose(request.campaign_id)
    payload = trace[0][2]
    shown = json.loads(payload["messages"][1]["content"])
    assert shown["charter"] == request.charter.model_dump()
    assert "Propose exactly one program." in payload["messages"][0]["content"]
    assert len(canonical(shown)) < len(canonical({"charter": request.charter, "development": request.development}))
    for projected, original in zip(shown["development"], request.development, strict=True):
        assert projected["title"] == original.title and projected["source_url"] == original.source_url
        for clause, source in zip(projected["claims"], original.claims, strict=True):
            assert clause == {
                "id": source.id,
                "text": source.text,
                "weight": source.weight,
                "depends_on": source.depends_on,
            }
            assert "provenance" not in clause and "schema_version" not in clause
    assert record["binding"]["request"] == request.model_dump()
    loop, _ = driver.native(request.campaign_id)
    assert loop.envelope(request.campaign_id)["bindings"]["request"] == request.model_dump()
    altered = request.model_dump()
    altered["development"][0]["claims"][0]["provenance"] += " retained public annotation revision"
    changed = DiscoveryRequest.model_validate(altered)
    assert _payload(changed, config) == _payload(request, config)
    with pytest.raises(Conflict, match="another model, source"):
        driver.create(changed, config)
    assert driver.show(request.campaign_id)["binding"]["request"] == request.model_dump()


def test_one_model_call_cannot_expand_its_requested_program_count(tmp_path, local_provider):
    config, trace, reply = local_provider
    second = copy.deepcopy(reply["candidates"][0])
    second["program"]["production"] = "weighted"
    reply["candidates"].append(second)
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    with pytest.raises(ValueError, match="retained uncertain"):
        driver.propose(request.campaign_id)
    assert len(trace) == 1
    retained = driver.show(request.campaign_id)
    assert retained["state"] == "uncertain" and retained["proposal"] is None


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://example.com/v1",
        "http://localhost/v1",
        "http://127.0.0.1/v1?key=x",
        "http://u:p@127.0.0.1/v1",
        "http://127.0.0.1/other",
        "http://127.0.0.1:0/v1",
        "http://127.0.0.1:99999/v1",
    ],
)
def test_only_explicit_credential_free_numeric_loopback_endpoint(endpoint):
    with pytest.raises(ValueError):
        LocalModelConfig(endpoint=endpoint, model="local", declared_revision="v1", no_charge=True)


def test_uncertain_call_is_retained_and_never_retried(tmp_path, local_provider):
    config, trace, reply = local_provider
    driver, request, record = prepare(tmp_path, config)
    reply.clear()
    reply["unexpected"] = "not a program"
    driver.approve(request.campaign_id, record["binding_digest"])
    with pytest.raises(ValueError, match="retained uncertain"):
        driver.propose(request.campaign_id)
    assert driver.show(request.campaign_id)["state"] == "uncertain"
    with pytest.raises(Conflict, match="already consumed"):
        driver.propose(request.campaign_id)
    assert len(trace) == 1


def test_process_crash_after_call_started_cannot_retry(tmp_path, local_provider):
    config, trace, _ = local_provider
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    with driver.journal.transaction() as cx:
        data = Journal.document(driver.show(request.campaign_id))
        data.update(state="in-flight", approval=None)
        driver.journal.append(cx, KEY + request.campaign_id, data)
    with pytest.raises(Conflict, match="already consumed"):
        ModelDiscovery(Journal(driver.journal.root)).propose(request.campaign_id)
    assert not trace


def test_stop_and_credentials_prevent_network_before_consuming_call(tmp_path, local_provider, monkeypatch):
    config, trace, _ = local_provider
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    monkeypatch.setenv(NO_KEY_ENV, "synthetic-test-value")
    with pytest.raises(PermissionError, match="refuses"):
        driver.propose(request.campaign_id)
    assert driver.show(request.campaign_id)["state"] == "queued" and not trace
    monkeypatch.delenv(NO_KEY_ENV)
    with driver.journal.transaction() as cx:
        driver.journal.append(cx, "@control", {"state": "stopped"})
    with pytest.raises(Conflict, match="STOP"):
        driver.propose(request.campaign_id)
    assert not trace


def test_charter_permission_is_checked_before_any_model_construction(tmp_path, local_provider):
    config, trace, _ = local_provider
    raw = pilot_request().model_dump()
    raw["operator_ids"] = ["local-model-proposals"]
    raw["charter"]["permitted_actions"] = ["read-public-source"]
    driver = ModelDiscovery(Journal.initialize(tmp_path / "agent"))
    with pytest.raises(PermissionError):
        driver.create(DiscoveryRequest.model_validate(raw), config)
    assert not trace


def test_changed_code_invalidates_call_permit(tmp_path, local_provider, monkeypatch):
    config, trace, _ = local_provider
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    monkeypatch.setattr(
        "alpha_factory_v1.core.runtime.successor.transformation_model._source_binding", lambda: "a" * 64
    )
    with pytest.raises(Conflict, match="binding changed"):
        driver.propose(request.campaign_id)
    assert not trace


@pytest.mark.parametrize(
    "edit",
    ["payment", "scope", "provider", "program", "request", "valid-other-program", "request-hash", "boolean-cost"],
)
def test_rehashed_import_does_not_authorize_forged_semantics(tmp_path, local_provider, edit):
    config, _, _ = local_provider
    driver, request = accepted(tmp_path, config)
    envelope = copy.deepcopy(driver.envelope(request.campaign_id))
    if edit == "payment":
        envelope["costs"]["money_minor"] = 1
    elif edit == "scope":
        envelope["scope"] = "general intelligence proven"
    elif edit == "provider":
        envelope["provider_evidence"]["provider"] = "https://example.com/v1"
    elif edit == "program":
        envelope["proposal"]["candidates"][0]["program"]["production"] = "arbitrary-code"
        envelope["proposal_digest"] = digest("ti-model-proposal", envelope["proposal"])
    elif edit == "request":
        envelope["model_binding"]["request"]["charter"]["purpose"] = "another purpose"
        envelope["model_binding_digest"] = digest("ti-model-call-permit", envelope["model_binding"])
    elif edit == "valid-other-program":
        envelope["proposal"]["candidates"][0]["program"]["production"] = "weighted"
        envelope["proposal_digest"] = digest("ti-model-proposal", envelope["proposal"])
    elif edit == "request-hash":
        envelope["provider_evidence"]["request_hash"] = "0" * 64
    else:
        envelope["costs"]["consumed_model_calls"] = True
    envelope["digest"] = digest("ti-model-wrapper", {key: value for key, value in envelope.items() if key != "digest"})
    with pytest.raises(ValueError):
        validate_model_envelope(envelope)


def test_model_has_no_evaluator_or_tool_fields():
    with pytest.raises(ValueError):
        ModelProposal.model_validate({"candidates": [], "score": 1, "tools": ["shell"]})


def test_no_charge_integer_does_not_substitute_for_explicit_attestation(local_provider):
    config, _, _ = local_provider
    raw = config.model_dump()
    raw["no_charge"] = 1
    with pytest.raises(ValueError, match="explicit boolean"):
        LocalModelConfig.model_validate(raw)


def test_queued_pause_and_cancel_revoke_model_permits(tmp_path, local_provider):
    config, trace, _ = local_provider
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    assert driver.control(request.campaign_id, "pause")["approval"] is None
    with pytest.raises(Conflict):
        driver.propose(request.campaign_id)
    driver.control(request.campaign_id, "resume")
    with pytest.raises(PermissionError):
        driver.propose(request.campaign_id)
    driver.approve(request.campaign_id, record["binding_digest"])
    assert driver.control(request.campaign_id, "cancel")["state"] == "canceled"
    with pytest.raises(Conflict):
        driver.propose(request.campaign_id)
    assert not trace


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_inflight_control_cannot_be_overwritten_by_response(tmp_path, local_provider, monkeypatch, action):
    config, _, _ = local_provider
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    entered, release = threading.Event(), threading.Event()

    def held_call(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        raise TimeoutError("synthetic interrupted response")

    monkeypatch.setattr(
        "alpha_factory_v1.core.runtime.successor.transformation_model.provider.complete_json", held_call
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(driver.propose, request.campaign_id)
        assert entered.wait(10)
        controlled = driver.control(request.campaign_id, action)
        release.set()
        assert future.result()["state"] == controlled["state"]
    assert driver.show(request.campaign_id)["approval"] is None
    with pytest.raises(Conflict):
        driver.propose(request.campaign_id)


@pytest.mark.parametrize("action", ["pause", "cancel", "global-stop", "global-stop-resume"])
def test_controls_close_actual_inflight_http_without_waiting_for_valid_reply(tmp_path, local_provider, action):
    config, _, reply = local_provider
    entered, release = threading.Event(), threading.Event()
    calls = []

    class HeldHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(self.rfile.read(int(self.headers["Content-Length"])))
            entered.set()
            assert release.wait(10)
            body = json.dumps(
                {
                    "model": "delayed-http-fixture",
                    "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(reply)}}],
                    "usage": {},
                }
            ).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), HeldHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = config.model_copy(update={"endpoint": f"http://127.0.0.1:{server.server_port}/v1", "timeout_seconds": 10})
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(driver.propose, request.campaign_id)
            try:
                assert entered.wait(5)
                if action.startswith("global"):
                    driver.journal.control(True)
                    if action.endswith("resume"):
                        driver.journal.control(False)
                else:
                    driver.control(request.campaign_id, action)
                retained = future.result(timeout=2)
                assert not release.is_set()
                assert retained["state"] == ("canceled" if action == "cancel" else "paused-consumed")
                assert retained["proposal"] is None and retained["approval"] is None
            finally:
                release.set()
        with pytest.raises(Conflict):
            driver.propose(request.campaign_id)
        assert len(calls) == 1
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join()


def test_final_response_commit_rechecks_global_control_revision(tmp_path, local_provider, monkeypatch):
    config, _, reply = local_provider
    driver, request, record = prepare(tmp_path, config)
    driver.approve(request.campaign_id, record["binding_digest"])

    def valid_late_reply(payload, runtime, **kwargs):
        driver.journal.control(True)
        driver.journal.control(False)
        return reply, {
            "configured_model": config.model,
            "reported_model": "late-fixture",
            "request_hash": "0" * 64,
            "response_hash": "1" * 64,
            "usage": {},
            "finish_reason": "stop",
            "provider": config.endpoint,
            "mode": "local_inference",
        }

    monkeypatch.setattr(
        "alpha_factory_v1.core.runtime.successor.transformation_model.provider.complete_json", valid_late_reply
    )
    retained = driver.propose(request.campaign_id)
    assert retained["state"] == "paused-consumed"
    assert retained["proposal"] is None and retained["provider_evidence"] is None


def test_product_cli_runs_same_model_then_native_lifecycle(tmp_path, local_provider):
    config, trace, _ = local_provider
    request = pilot_request().model_dump()
    request["operator_ids"] = ["local-model-proposals"]
    request_path, config_path = tmp_path / "request.json", tmp_path / "model.json"
    request_path.write_text(json.dumps(request))
    config_path.write_text(config.model_dump_json())

    def cli(*arguments):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.core.runtime.cli",
                "--home",
                str(tmp_path / "cli-agent"),
                "successor-model",
                *map(str, arguments),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return json.loads(completed.stdout)

    campaign_id = request["campaign_id"]
    queued = cli("create", request_path, config_path)
    assert queued["state"] == "queued" and trace == []
    cli("approve", campaign_id, "--binding", queued["binding_digest"])
    assert cli("propose", campaign_id)["state"] == "proposed"
    native = cli("prepare-native", campaign_id)
    cli("approve-native", campaign_id, "--binding", native["binding_digest"])
    for phase in ("diagnose", "develop", "freeze"):
        native = cli("step", campaign_id, "--operation-id", phase)
    confirmation = tmp_path / "confirmation.json"
    from alpha_factory_v1.core.runtime.successor.transformation import pilot_document

    confirmation.write_text(json.dumps({"documents": [pilot_document(confirmation=True).model_dump()]}))
    result = cli("confirm", campaign_id, confirmation, "--freeze", native["freeze"]["digest"])
    assert result["native_envelope"]["result"]["beats_unrestricted"] is False
    output = tmp_path / "model-evidence.json"
    cli("export", campaign_id, "--output", output)
    assert validate_model_envelope(json.loads(output.read_text())) == result
    assert len(trace) == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"response_hash": None},
        {"response_hash": "not-a-digest"},
        {"reported_model": {"independently_verified": True}},
        {"usage": "claimed"},
        {"usage": {"completion_tokens": -1}},
        {"usage": {"prompt_tokens": True}},
    ],
)
def test_provider_evidence_has_only_bounded_reported_fields(bad):
    raw = {
        "configured_model": "local",
        "reported_model": "reported-local",
        "request_hash": "0" * 64,
        "response_hash": "1" * 64,
        "usage": {},
        "finish_reason": "stop",
        "provider": "http://127.0.0.1/v1",
        "mode": "local_inference",
    }
    raw.update(bad)
    with pytest.raises(ValueError):
        ProviderEvidence.model_validate(raw)
