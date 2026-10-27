# SPDX-License-Identifier: Apache-2.0
"""Executed transport/lifecycle tests with explicitly modeled production and identity."""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from alpha_factory_v1.core.runtime.store import Conflict, digest as runtime_digest
from alpha_factory_v1.core.runtime.successor.flywheel_execution import (
    KEY,
    DockerComputerEnvironment,
    ExecutionMission,
    ExecutionPermit,
    ExecutionProfile,
    HTTPToolEnvironment,
    MissionExecutor,
    ResponsesTransport,
    ToolEndpoint,
)
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record
import test_flywheel_protected as protected_fixtures
from test_flywheel_protected import ZERO, account


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return protected_fixtures.setup.__wrapped__(tmp_path)


def mission() -> ExecutionMission:
    return ExecutionMission(
        mission_id="systems-rd-1",
        beneficiary="Distributed service engineering team",
        goal="Develop and test an exact failure-resilient placement prototype",
        challenged_assumption="Cheapest placement may fail correlated rack loss",
        deliverable="Executable solver, independently checked placements and failure cases",
        acceptance_criteria=["No capacity violation", "Each service survives one rack loss"],
        inputs={"synthetic": True},
        sharing_rights="Apache-2.0 synthetic fixture",
        stop_conditions=["Stop on capacity or permission refusal"],
        mode="hybrid",
        components={
            "model": "simulated",
            "tools": "executed-local",
            "identity": "simulated",
            "acceptance": "unqualified",
            "market": "simulated",
        },
    )


def profile() -> ExecutionProfile:
    return ExecutionProfile(
        model_id="SCRIPTED-PROTOCOL-FIXTURE",
        reasoning_effort="high",
        supported_efforts=["high"],
        qualification_digest=ZERO,
        tools=[
            {
                "type": "function",
                "name": "experiment",
                "description": "Run bounded tests",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                "strict": True,
            }
        ],
    )


def response(output: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": "fixture-response",
        "model": profile().model_id,
        "status": "completed",
        "output": output,
        "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
    }


def done() -> dict[str, Any]:
    return response(
        [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "deliverable": "fixture artifact",
                                "verification": "unverified model claim",
                                "limitations": ["modeled model"],
                                "artifacts": [],
                            }
                        ),
                    }
                ],
            }
        ]
    )


class ScriptedTransport:
    component = "simulated"

    def __init__(self, outputs: list[dict[str, Any]]) -> None:
        self.outputs = copy.deepcopy(outputs)
        self.requests: list[dict[str, Any]] = []

    def respond(self, payload: dict[str, Any], active: Any, remaining: float) -> dict[str, Any]:
        assert active() and remaining > 0
        self.requests.append(copy.deepcopy(payload))
        return self.outputs.pop(0)


class LocalExperiment:
    component = "executed-local"
    identity = {"fixture": "bounded experiment implementation/v1"}

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def perform(self, name: str, arguments: dict[str, Any], active: Any) -> dict[str, Any]:
        assert name == "experiment" and not arguments and active()
        self.calls.append(arguments)
        return {"actually_executed": sum(range(100)), "accepted": False}


def permit(s: dict[str, Any], task: ExecutionMission, p: ExecutionProfile, env: Any, op: str = "fixture-run") -> Any:
    account(
        s,
        "capital",
        {
            "record_id": "execution-funding",
            "mission_id": task.mission_id,
            "amount_micro_usd": 1_000_000,
            "evidence_digest": ZERO,
        },
        "execution-funding",
    )
    terms = ExecutionPermit(
        operation_id=op,
        request_digest=digest("flywheel-execution-request", task),
        profile_digest=digest("flywheel-execution-profile", p),
        environment_digest=digest("flywheel-execution-environment-contract", env.identity),
        config_digest=runtime_digest(s["journal"].config.model_dump()),
        quota_evidence_digest=ZERO,
        pricing_evidence_digest=ZERO,
        max_authorized_micro_usd=1000,
        expires_at=int(time.time()) + 3600,
        bucket="A",
    )
    return sign_record(
        s["keys"]["controller"],
        "controller",
        "flywheel-execution-permit",
        {"journal_identity": s["journal"].identity, "permit": terms.model_dump()},
    )


def test_actual_tool_result_flows_back_to_model_and_durable_history(setup: dict[str, Any]) -> None:
    s, task, p, env = setup, mission(), profile(), LocalExperiment()
    transport = ScriptedTransport(
        [response([{"type": "function_call", "name": "experiment", "call_id": "call-1", "arguments": "{}"}]), done()]
    )
    signed = permit(s, task, p, env)
    executor = MissionExecutor(s["journal"], s["trust"], s["costs"], transport, env)
    result = executor.run(task, p, signed)
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    assert len(env.calls) == 1 and result["actions"] == 1 and len(result["usage_events"]) == 2
    reply = transport.requests[1]["input"][-1]
    assert reply["call_id"] == "call-1" and json.loads(reply["output"])["actually_executed"] == 4950
    assert transport.requests[0]["reasoning"] == {"effort": "high"}
    assert result["acceptance"] == "unqualified" and not result["live_network_qualified"]
    assert s["costs"].report()["available_funds"] is None
    assert s["journal"].latest(KEY + "fixture-run")["result"] == result["result"]
    with pytest.raises(Conflict, match="already attempted"):
        executor.run(task, p, signed)
    assert len(transport.requests) == 2


@pytest.mark.parametrize("attack", ["tool", "model", "safety", "replay", "actions", "effort", "mode", "expiry"])
def test_refusal_preserves_failure_without_hidden_execution(setup: dict[str, Any], attack: str) -> None:
    s, task, p, env = setup, mission(), profile(), LocalExperiment()
    call = {"type": "function_call", "name": "experiment", "call_id": "call-1", "arguments": "{}"}
    body = response([call])
    if attack == "tool":
        call["name"] = "send_payment"
    elif attack == "model":
        body["model"] = "silently-weaker-model"
    elif attack == "safety":
        call["pending_safety_checks"] = [{"id": "requires-review"}]
    elif attack == "actions":
        task = task.model_copy(update={"max_actions": 0})
    transport = ScriptedTransport([body, body, done()])
    signed = permit(s, task, p, env)
    executor = MissionExecutor(s["journal"], s["trust"], s["costs"], transport, env)
    if attack in {"effort", "mode", "expiry"}:
        if attack == "effort":
            p = p.model_copy(update={"reasoning_effort": "max"})
        elif attack == "mode":
            task = task.model_copy(update={"mode": "live"})
        else:
            changed = copy.deepcopy(signed.payload)
            changed["permit"]["expires_at"] = int(time.time()) - 1
            signed = sign_record(s["keys"]["controller"], "controller", "flywheel-execution-permit", changed)
        with pytest.raises(ValueError):
            executor.run(task, p, signed)
        assert not transport.requests
    else:
        result = executor.run(task, p, signed)
        assert result["status"] == "failed-or-uncertain"
        assert len(env.calls) == (1 if attack == "replay" else 0)
        assert s["costs"].report()["unknown_costs"]


def test_stop_after_tool_keeps_unknown_attempt_and_no_retry(setup: dict[str, Any]) -> None:
    s, task, p, env = setup, mission(), profile(), LocalExperiment()
    transport = ScriptedTransport(
        [response([{"type": "function_call", "name": "experiment", "call_id": "call-1", "arguments": "{}"}]), done()]
    )
    original = env.perform

    def stop(name: str, args: Any, active: Any) -> dict[str, Any]:
        value = original(name, args, active)
        with s["journal"].transaction() as cx:
            control = s["journal"].document(s["journal"].latest("@control", cx))
            s["journal"].append(cx, "@control", {**control, "state": "paused"})
        return value

    env.perform = stop
    signed = permit(s, task, p, env)
    result = MissionExecutor(s["journal"], s["trust"], s["costs"], transport, env).run(task, p, signed)
    assert result["status"] == "failed-or-uncertain" and len(transport.requests) == 1
    assert result["pending"].startswith("tool/") and s["costs"].report()["unknown_costs"]


def test_responses_wire_transport_uses_real_protocol_without_paid_calls(
    setup: dict[str, Any], monkeypatch: Any
) -> None:
    from alpha_factory_v1.core.runtime.models import RuntimeConfig

    s = setup
    s["journal"].config = RuntimeConfig(llm_url="https://api.example/v1", llm_model="fixture", allow_remote_llm=True)
    monkeypatch.setenv("ALPHA_AGENT_LLM_KEY", "fictional-test-credential")
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=done())

    client_type = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    assert ResponsesTransport(s["journal"]).respond({"model": "fixture"}, lambda: True, 1)["status"] == "completed"
    assert str(requests[0].url) == "https://api.example/v1/responses"
    assert json.loads(requests[0].content) == {"model": "fixture"}
    assert requests[0].headers["authorization"] == "Bearer fictional-test-credential"


def test_provisioned_sandbox_adapter_binds_call_and_return(monkeypatch: Any) -> None:
    monkeypatch.setenv("TEST_SANDBOX_KEY", "fictional-test-credential")
    endpoint = ToolEndpoint(
        endpoint="https://sandbox.example/execute",
        credential_env="TEST_SANDBOX_KEY",
        sandbox_revision=ZERO,
        session_id="fixture-session",
        permitted_tools=["experiment"],
    )
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        value = json.loads(request.content)
        seen.append(value)
        return httpx.Response(200, json={"request_id": value["request_id"], "result": {"executed": True}})

    client_type = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    tools = HTTPToolEnvironment(endpoint)
    assert tools.perform("experiment", {}, lambda: True) == {"executed": True}
    with pytest.raises(ValueError, match="allowlist"):
        tools.perform("host_shell", {}, lambda: True)
    assert len(seen) == 1 and seen[0]["sequence"] == 1 and seen[0]["sandbox_revision"] == ZERO


def test_computer_adapter_executes_validated_action_before_observation() -> None:
    import base64

    class Computer:
        def __init__(self) -> None:
            self.actions = []

        def act(self, action: dict[str, Any]) -> dict[str, Any]:
            self.actions.append(action)
            return {"png": base64.b64encode(b"\x89PNG\r\n\x1a\nFICTIONAL-TEST-PNG").decode()}

    computer = Computer()
    environment = DockerComputerEnvironment(computer, {"image": "fixture", "worker_sha256": ZERO, "task_digest": ZERO})
    value = environment.perform("computer", {"type": "click", "button": "left", "x": 4, "y": 8}, lambda: True)
    assert len(computer.actions) == 1 and value["type"] == "computer_screenshot"
    with pytest.raises(ValueError):
        environment.perform("computer", {"type": "click", "button": "left", "x": 10000, "y": 8}, lambda: True)
    assert len(computer.actions) == 1


def test_new_systems_solver_has_independent_acceptance_and_mutation_rejection() -> None:
    import random
    from alpha_factory_v1.core.runtime.successor.flywheel_experiments import (
        PlacementProblem,
        solve_placement,
        verify_placement,
    )

    for seed in range(36):
        rng = random.Random(seed)
        problem = PlacementProblem(
            capacities=[rng.randint(2, 8) for _ in range(4)],
            failure_domains=["a", "b", "c", "a"],
            demands=[rng.randint(1, 3) for _ in range(4)],
            costs=[[rng.randint(0, 15) for _ in range(4)] for _ in range(4)],
        )
        result = solve_placement(problem)
        assert verify_placement(problem, result)["accepted_finite_result"]
        if result["placement"] is not None:
            corrupted = copy.deepcopy(result)
            corrupted["placement"][0] = [0, 0]
            assert not verify_placement(problem, corrupted)["accepted_finite_result"]
            corrupted = {**result, "cost": result["cost"] + 1}
            assert not verify_placement(problem, corrupted)["accepted_finite_result"]
        limited = problem.model_copy(update={"node_budget": 1})
        assert solve_placement(limited)["status"] in {"incomplete", "infeasible"}


def test_external_state_change_cannot_be_overwritten(setup: dict[str, Any]) -> None:
    s, task, p, env = setup, mission(), profile(), LocalExperiment()
    transport = ScriptedTransport([done()])
    signed = permit(s, task, p, env)
    original = transport.respond

    def competing(payload: Any, active: Any, remaining: float) -> dict[str, Any]:
        value = original(payload, active, remaining)
        with s["journal"].transaction() as cx:
            s["journal"].append(cx, KEY + "fixture-run", {"status": "controller-hold"})
        return value

    transport.respond = competing
    with pytest.raises(Conflict, match="competing record"):
        MissionExecutor(s["journal"], s["trust"], s["costs"], transport, env).run(task, p, signed)
    assert s["journal"].latest(KEY + "fixture-run")["status"] == "controller-hold"


def test_stalled_provider_is_cancelled_on_total_deadline(setup: dict[str, Any], monkeypatch: Any) -> None:
    import asyncio
    from alpha_factory_v1.core.runtime.models import RuntimeConfig

    s, closed = setup, []
    s["journal"].config = RuntimeConfig(llm_url="https://api.example/v1", llm_model="fixture", allow_remote_llm=True)
    monkeypatch.setenv("ALPHA_AGENT_LLM_KEY", "fictional-test-credential")

    async def handler(request: httpx.Request) -> httpx.Response:
        try:
            await asyncio.sleep(10)
        finally:
            closed.append(True)
        return httpx.Response(200, json=done())

    client_type = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    before = time.monotonic()
    with pytest.raises(TimeoutError):
        ResponsesTransport(s["journal"]).respond({}, lambda: True, 0.03)
    assert time.monotonic() - before < 0.5 and closed
