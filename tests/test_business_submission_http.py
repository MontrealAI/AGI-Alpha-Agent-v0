# SPDX-License-Identifier: Apache-2.0
"""Real loopback HTTP tests of authenticated, stateless Business1 evaluation.

No orchestrator scheduling loop, SDK server, provider or broker is started.
"""
from __future__ import annotations

import json
import socket
import threading
import time
from types import SimpleNamespace

import httpx
import pytest
import uvicorn


@pytest.fixture
def service(monkeypatch, tmp_path):
    monkeypatch.setenv("API_TOKEN", "local-submission-test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ALPHA_BUSINESS_ALLOW_PROVIDER", "0")
    monkeypatch.delenv("ALPHA_KAFKA_BROKER", raising=False)
    # A stale valid file must never be used as fallback for a submitted request.
    stale = tmp_path / "periodic.json"
    stale.write_text(json.dumps(supplied("stale", 900)))
    monkeypatch.setenv("ALPHA_BUSINESS_STATE_FILE", str(stale))
    original_connect = socket.socket.connect

    def loopback_only(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1"}:
            raise AssertionError(f"Network egress forbidden: {address}")
        return original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", loopback_only)
    from alpha_factory_v1.backend.api_server import build_rest
    from alpha_factory_v1.demos.alpha_agi_business_v1.alpha_agi_business_v1 import AlphaExecutionAgent

    runner = SimpleNamespace(inst=AlphaExecutionAgent(), next_ts=12345)
    app = build_rest(
        {"alpha_execution": runner, "unsupported": SimpleNamespace(inst=object(), next_ts=9)}, mem=object()
    )
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() >= deadline:
                raise AssertionError("loopback server failed to start")
            time.sleep(0.01)
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=5) as client:
            yield client, runner, stale
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
        assert not thread.is_alive(), "loopback service failed to stop"


def supplied(ident="a", benefit=90):
    return {
        "budget": 100,
        "max_loss": 20,
        "opportunities": [{"id": ident, "cost": 60, "benefit": benefit, "worst_loss": 15}],
    }


AUTH = {"Authorization": "Bearer local-submission-test-token"}
PATH = "/agent/alpha_execution/evaluate"


def test_real_http_inputs_bound_to_evaluator_and_no_stale_reuse(service):
    client, runner, stale = service
    a = client.post(PATH, json=supplied("a", 90), headers=AUTH)
    b = client.post(PATH, json=supplied("b", 110), headers=AUTH)
    assert a.status_code == b.status_code == 200
    a, b = a.json(), b.json()
    assert a["status"] == b["status"] == "evaluated_supplied_assumptions"
    assert a["input_id"] != b["input_id"]
    assert a["evaluation"]["execution"]["selected"]["id"] == "a"
    assert b["evaluation"]["execution"]["selected"]["id"] == "b"
    assert a["evaluation"]["execution"]["selected"]["net_benefit"] == 30
    assert b["evaluation"]["execution"]["selected"]["net_benefit"] == 50
    assert all(not report["external_actions_performed"] for report in b["evaluation"].values())
    assert b["evaluation"]["business"]["incorporated"] is False
    assert b["evaluation"]["compliance"]["certified"] is False
    for payload in [{}, {"alpha": "new", "score": 99}, {"budget": 0}, None]:
        bad = client.post(PATH, content=json.dumps(payload), headers={**AUTH, "Content-Type": "application/json"})
        assert bad.status_code == 422
        assert "evaluation" not in bad.json() and "input_id" not in bad.json()
    c = client.post(PATH, json=supplied("c", 40), headers=AUTH).json()
    assert c["evaluation"]["execution"]["status"] == "no_eligible_proposal"
    assert c["evaluation"]["execution"]["selected"] is None
    assert runner.next_ts == 12345
    assert json.loads(stale.read_text()) == supplied("stale", 900)


def test_real_http_auth_and_trigger_compatibility(service):
    client, runner, _ = service
    for headers in [{}, {"Authorization": "Bearer incorrect"}]:
        assert client.post(PATH, json=supplied(), headers=headers).status_code in {401, 403}
        assert client.post("/agent/alpha_execution/trigger", headers=headers).status_code in {401, 403}
    assert runner.next_ts == 12345
    rejected = client.post("/agent/alpha_execution/trigger", json=supplied(), headers=AUTH)
    assert rejected.status_code == 422
    assert runner.next_ts == 12345
    assert client.post("/agent/alpha_execution/trigger", headers=AUTH).json() == {"queued": True}
    assert runner.next_ts == 0
    assert client.post("/agent/unsupported/evaluate", json=supplied(), headers=AUTH).status_code == 501
    assert client.post("/agent/missing/evaluate", json=supplied(), headers=AUTH).status_code == 404


@pytest.mark.parametrize(
    "body,status",
    [
        (b"", 422),
        (b"{", 422),
        (b'{"budget":1,"budget":2}', 422),
        (b'{"budget":NaN}', 422),
        (b"\xff", 422),
        (b"x" * 256001, 413),
    ],
)
def test_real_http_invalid_new_input_never_evaluates_old_state(service, body, status):
    client, runner, _ = service
    assert client.post(PATH, json=supplied(), headers=AUTH).status_code == 200
    response = client.post(PATH, content=body, headers={**AUTH, "Content-Type": "application/json"})
    assert response.status_code == status
    assert "evaluation" not in response.json()
    assert runner.next_ts == 12345


def test_real_http_stream_bound_and_content_type(service):
    client, runner, _ = service
    assert client.post(PATH, content=b"{}", headers=AUTH).status_code == 415
    response = client.post(
        PATH, content=iter([b"x" * 128000] * 3), headers={**AUTH, "Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert runner.next_ts == 12345


def test_bridge_submits_two_inputs_over_real_http(service, monkeypatch):
    """SDK registration is inert; bridge HTTP and evaluator are real."""
    import asyncio
    import sys
    from types import ModuleType

    shim = ModuleType("openai_agents")
    shim.Agent = object
    shim.AgentRuntime = object
    shim.Tool = lambda *args, **kwargs: lambda function: function
    monkeypatch.setitem(sys.modules, "openai_agents", shim)
    from alpha_factory_v1.demos.alpha_agi_business_v1 import openai_agents_bridge as bridge

    client, runner, _ = service
    monkeypatch.setattr(bridge, "HOST", str(client.base_url).rstrip("/"))
    monkeypatch.setattr(bridge, "HEADERS", AUTH)
    # Use actual httpx with proxies disabled, never a mocked HTTP response.
    monkeypatch.setattr(bridge, "AsyncClient", lambda: httpx.AsyncClient(trust_env=False))
    first = json.loads(asyncio.run(bridge.submit_job({"agent": "alpha_execution", "state": supplied("one", 90)})))
    second = json.loads(asyncio.run(bridge.submit_job({"agent": "alpha_execution", "state": supplied("two", 110)})))
    assert first["input_id"] != second["input_id"]
    assert first["evaluation"]["execution"]["selected"]["id"] == "one"
    assert second["evaluation"]["execution"]["selected"]["id"] == "two"
    with pytest.raises(ValueError):
        asyncio.run(bridge.submit_job({"agent": "alpha_execution", "state": {}}))
    with pytest.raises(ValueError):
        asyncio.run(bridge.trigger_best_alpha())
    assert runner.next_ts == 12345


def test_shell_helper_real_http_and_unsupported_job(service, tmp_path):
    import os
    from pathlib import Path
    import shutil
    import subprocess

    if not shutil.which("jq") or not shutil.which("curl"):
        pytest.skip("shell helper requires installed jq and curl")
    client, runner, _ = service
    demo = Path(__file__).resolve().parents[1] / "alpha_factory_v1/demos/alpha_agi_business_v1"
    env = {
        **os.environ,
        "HOST": "127.0.0.1",
        "PORT": str(client.base_url.port),
        "API_TOKEN": "local-submission-test-token",
        "NO_PROXY": "127.0.0.1",
        "no_proxy": "127.0.0.1",
    }
    job = tmp_path / "job.json"
    for ident, benefit in [("shell-a", 90), ("shell-b", 110)]:
        job.write_text(json.dumps({"agent": "alpha_execution", "state": supplied(ident, benefit)}))
        result = subprocess.run(
            ["bash", str(demo / "scripts/post_alpha_job.sh"), str(job)],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        assert json.loads(result.stdout)["evaluation"]["execution"]["selected"]["id"] == ident
    job.write_text('{"agent":"planning","note":"old unsupported job"}')
    result = subprocess.run(
        ["bash", str(demo / "scripts/post_alpha_job.sh"), str(job)], env=env, capture_output=True, text=True, timeout=10
    )
    assert result.returncode != 0
    assert "Nothing was submitted" in result.stderr
    assert runner.next_ts == 12345
