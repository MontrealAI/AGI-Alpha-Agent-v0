# SPDX-License-Identifier: Apache-2.0
"""Adversarial control tests use labeled supplier/actuator doubles, never claim live qualification."""

from __future__ import annotations

import base64
import argparse
import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.computer import (
    ComputerTask,
    DockerComputer,
    HTTPAdvisor,
    ReadBroker,
    commitment,
    run_session,
    handle,
    validate_action,
)


def task() -> ComputerTask:
    return ComputerTask(
        goal="Type useful work into the box",
        html='<input aria-label="Result" id="result">',
        input_rights="synthetic",
        license="Apache-2.0",
        max_turns=3,
    )


class ScriptedAdvisor:
    identity = {"mode": "CONTROLLED_TEST_DOUBLE", "model": "fixed-script", "endpoint": "none"}

    def __init__(self) -> None:
        self.calls = 0

    def next(self, task: ComputerTask, observation: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return (
            {
                "actions": [
                    {"type": "click", "button": "left", "x": 80, "y": 16},
                    {"type": "type", "text": "useful work"},
                ],
                "done": False,
                "summary": "",
            }
            if self.calls == 1
            else {"actions": [], "done": True, "summary": "Unverified scripted completion"}
        )


class TestComputer:
    __test__ = False

    def __init__(self, *args: Any) -> None:
        self.closed = False

    def observe(self) -> dict[str, Any]:
        return {
            "type": "observation",
            "png": base64.b64encode(b"\x89PNG\r\n\x1a\nTEST_DOUBLE").decode(),
            "text": "test-double observation",
            "url": "about:blank",
        }

    def act(self, action: dict[str, Any]) -> dict[str, Any]:
        return self.observe()

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    "action",
    [
        {"type": "shell", "command": "id"},
        {"type": "type", "text": "x", "authority": True},
        {"type": "click", "x": True, "y": 1, "button": "left"},
        {"type": "click", "x": 1024, "y": 1, "button": "left"},
        {"type": "keypress", "keys": ["CTRL", "L"]},
        {"type": "keypress", "keys": ["META", "R"]},
        {"type": "drag", "path": []},
        {"type": "scroll", "x": 1, "y": 1, "scroll_x": 0, "scroll_y": 10_000},
    ],
)
def test_hostile_or_unbounded_advice_is_not_executable(action: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        validate_action(action)


def test_provider_substitution_invalidates_permission(tmp_path: Path) -> None:
    advisor = ScriptedAdvisor()
    image = "sha256:" + "a" * 64
    permit = commitment(task(), advisor, image)
    advisor.identity = {**advisor.identity, "model": "other"}
    with pytest.raises(ValueError, match="permit"):
        run_session(
            Journal.initialize(tmp_path / "home"),
            task(),
            advisor,
            image,
            tmp_path / "out",
            permit,
            factory=TestComputer,
        )
    assert not (tmp_path / "out").exists()


def test_reservations_and_untrusted_completion_retained(tmp_path: Path) -> None:
    journal, advisor = Journal.initialize(tmp_path / "home"), ScriptedAdvisor()
    image = "sha256:" + "a" * 64
    result = run_session(
        journal, task(), advisor, image, tmp_path / "out", commitment(task(), advisor, image), factory=TestComputer
    )
    receipt = json.loads((tmp_path / "out/receipt.json").read_text())
    assert result["state"] == "review" and result["verified"] is False
    assert receipt["turns_reserved"] == 2 and receipt["actions_reserved"] == 2
    assert len(receipt["screenshots"]) == 3
    assert receipt["authority"] == [] and receipt["billing"] == "UNKNOWN"
    journal.verify()


def test_failure_preserves_uncertain_effect_and_cleanup(tmp_path: Path) -> None:
    class BrokenComputer(TestComputer):
        def act(self, action: dict[str, Any]) -> dict[str, Any]:
            raise OSError("connection lost after an uncertain effect")

    journal, advisor = Journal.initialize(tmp_path / "home"), ScriptedAdvisor()
    image = "sha256:" + "a" * 64
    with pytest.raises(OSError):
        run_session(
            journal,
            task(),
            advisor,
            image,
            tmp_path / "out",
            commitment(task(), advisor, image),
            factory=BrokenComputer,
        )
    receipt = json.loads((tmp_path / "out/receipt.json").read_text())
    assert receipt["state"] == "interrupted"
    assert receipt["actions_reserved"] == 1 and receipt["pending"] == "action"
    assert receipt["events"][-1]["status"] == "reserved"
    with pytest.raises(ValueError, match="reconcile"):
        run_session(
            journal,
            task(),
            ScriptedAdvisor(),
            image,
            tmp_path / "retry",
            commitment(task(), ScriptedAdvisor(), image),
            factory=TestComputer,
        )


def test_egress_blocks_private_dns_and_unapproved_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = ReadBroker(["https://example.org/public"])
    with pytest.raises(ValueError):
        broker.fetch("https://example.org/public?stolen=secret", "GET")
    with pytest.raises(ValueError):
        broker.fetch("https://example.org/public", "POST")
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="nonpublic"):
        broker.fetch("https://example.org/public", "GET")


def test_reconciliation_binds_exact_inactive_record(tmp_path: Path) -> None:
    home = tmp_path / "home"
    journal, advisor = Journal.initialize(home), ScriptedAdvisor()
    image = "sha256:" + "a" * 64
    result = run_session(
        journal, task(), advisor, image, tmp_path / "out", commitment(task(), advisor, image), factory=TestComputer
    )
    record = journal.latest("@successor-computer:" + result["run_id"])
    args = argparse.Namespace(
        home=home,
        computer_command="reconcile",
        run_id=result["run_id"],
        record_digest="0" * 64,
        note="Observed local draft; no external writes occurred",
    )
    with pytest.raises(ValueError):
        handle(args)
    args.record_digest = record["digest"]
    assert handle(args)["state"] == "reconciled"
    advisor = ScriptedAdvisor()
    assert (
        run_session(
            journal,
            task(),
            advisor,
            image,
            tmp_path / "second",
            commitment(task(), advisor, image),
            factory=TestComputer,
        )["state"]
        == "review"
    )


def test_failed_cleanup_quarantines_completed_claim(tmp_path: Path) -> None:
    class LeakedComputer(TestComputer):
        def close(self) -> None:
            raise ValueError("controlled cleanup failure")

    journal, advisor = Journal.initialize(tmp_path / "home"), ScriptedAdvisor()
    image = "sha256:" + "a" * 64
    with pytest.raises(ValueError, match="cleanup"):
        run_session(
            journal,
            task(),
            advisor,
            image,
            tmp_path / "out",
            commitment(task(), advisor, image),
            factory=LeakedComputer,
        )
    receipt = json.loads((tmp_path / "out/receipt.json").read_text())
    assert receipt["state"] == "quarantined" and receipt["cleanup"] == "FAILED"
    assert receipt["elapsed_milliseconds"] >= 0


def test_current_responses_wire_format_and_safety_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    original = httpx.Client
    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "computer_call",
                        "call_id": "one",
                        "actions": [{"type": "screenshot"}],
                        "pending_safety_checks": [] if len(requests) == 1 else ["review"],
                    }
                ],
            },
        )

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    advisor = HTTPAdvisor("responses", "operator-selected-model", "https://api.openai.com/v1", "TEST_ONLY")
    observation = TestComputer().observe()
    assert advisor.next(task(), observation)["actions"] == [{"type": "screenshot"}]
    with pytest.raises(ValueError, match="safety review"):
        advisor.next(task(), observation)
    assert requests[0]["tools"] == [{"type": "computer"}]
    assert requests[0]["store"] is False
    assert requests[1]["input"][-1]["output"]["type"] == "computer_screenshot"
    assert requests[1]["input"][-1]["call_id"] == "one"


@pytest.mark.parametrize(
    "output",
    [
        [],
        [{"type": "reasoning", "summary": []}],
        [{"type": "message", "phase": "commentary", "content": [{"type": "output_text", "text": "Working"}]}],
        [{"type": "message", "content": [{"type": "output_text", "text": " "}]}],
        [{"type": "message", "content": [{"type": "refusal", "refusal": "Cannot proceed"}]}],
    ],
)
def test_responses_without_a_final_message_do_not_claim_completion(
    monkeypatch: pytest.MonkeyPatch, output: Any
) -> None:
    original = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"status": "completed", "output": output}))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=transport, **kwargs))
    advisor = HTTPAdvisor("responses", "explicit-test-model", "https://api.openai.com/v1", "TEST_ONLY")
    with pytest.raises(ValueError, match="no final completion"):
        advisor.next(task(), TestComputer().observe())
    assert advisor.usage_events[0]["cost"] is None


def test_responses_final_answer_clears_pending_call_and_excludes_commentary(monkeypatch: pytest.MonkeyPatch) -> None:
    original = httpx.Client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {"type": "message", "phase": "commentary", "content": [{"type": "output_text", "text": "Working"}]},
                    {"type": "message", "phase": "final_answer", "content": [{"type": "output_text", "text": "Claim"}]},
                ],
            },
        )
    )
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=transport, **kwargs))
    advisor = HTTPAdvisor("responses", "explicit-test-model", "https://api.openai.com/v1", "TEST_ONLY")
    advisor.history = [{"type": "computer_call", "call_id": "one", "actions": [{"type": "screenshot"}]}]
    advisor.pending = "one"
    assert advisor.next(task(), TestComputer().observe()) == {"actions": [], "done": True, "summary": "Claim"}
    assert advisor.pending is None


@pytest.mark.skipif(
    not os.environ.get("SUCCESSOR_COMPUTER_IMAGE"), reason="real Docker image must be explicitly provided"
)
def test_real_container_keyboard_screenshot_and_cleanup(tmp_path: Path) -> None:
    journal, advisor, mission = Journal.initialize(tmp_path / "home"), ScriptedAdvisor(), task()
    mission = mission.model_copy(
        update={
            "html": '<input id="result" oninput="document.querySelector(\'output\').textContent=this.value">'
            "<output></output>"
        }
    )
    image = os.environ["SUCCESSOR_COMPUTER_IMAGE"]
    result = run_session(
        journal, mission, advisor, image, tmp_path / "out", commitment(mission, advisor, image), factory=DockerComputer
    )
    assert result["state"] == "review"
    assert "useful work" in (tmp_path / "out/visible-text.txt").read_text()
    assert (tmp_path / "out/screen-002.png").stat().st_size > 100


@pytest.mark.parametrize(
    "usage,expected",
    [
        ({"input_tokens": 17, "output_tokens": 3, "total_tokens": 20}, "PROVIDER_REPORTED"),
        ({"input_tokens": True, "output_tokens": 3, "total_tokens": 4}, "UNKNOWN"),
        ({"input_tokens": -1, "output_tokens": 3, "total_tokens": 2}, "UNKNOWN"),
        (None, "UNKNOWN"),
    ],
)
def test_provider_usage_is_observed_not_invoiced(monkeypatch, tmp_path, usage, expected):
    original = httpx.Client

    def respond(request):
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "usage": usage,
                "output": [{"type": "message", "content": [{"type": "output_text", "text": "Unverified completion"}]}],
            },
        )

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    advisor = HTTPAdvisor("responses", "explicit-test-model", "https://api.openai.com/v1", "TEST_ONLY")
    journal = Journal.initialize(tmp_path / "home")
    mission = task()
    image = "sha256:" + "a" * 64
    result = run_session(
        journal, mission, advisor, image, tmp_path / "out", commitment(mission, advisor, image), factory=TestComputer
    )
    receipt = json.loads((tmp_path / "out/receipt.json").read_text())
    assert receipt["provider_usage"][0]["status"] == expected
    assert receipt["provider_usage"][0]["cost"] is None
    assert result["billing"] == "UNKNOWN"
    assert type(receipt["elapsed_milliseconds"]) is int  # noqa: E721
    assert receipt["elapsed_milliseconds"] >= 0


def test_failed_provider_attempt_retains_unknown_cost(monkeypatch, tmp_path):
    original = httpx.Client

    def fail(request):
        raise httpx.ReadTimeout("uncertain provider response")

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(fail), **kwargs))
    advisor = HTTPAdvisor("responses", "explicit-test-model", "https://api.openai.com/v1", "TEST_ONLY")
    journal = Journal.initialize(tmp_path / "home")
    mission = task()
    image = "sha256:" + "a" * 64
    with pytest.raises(httpx.ReadTimeout):
        run_session(
            journal,
            mission,
            advisor,
            image,
            tmp_path / "out",
            commitment(mission, advisor, image),
            factory=TestComputer,
        )
    receipt = json.loads((tmp_path / "out/receipt.json").read_text())
    assert receipt["provider_usage"] == [{"attempt": 1, "status": "UNKNOWN", "cost": None}]
    assert receipt["state"] == "interrupted"
    assert receipt["cleanup"] == "VERIFIED"
    assert receipt["turns_reserved"] == 1


def test_stop_during_provider_response_retains_usage_and_never_completes(monkeypatch, tmp_path):
    from alpha_factory_v1.core.runtime.store import Conflict
    from alpha_factory_v1.core.runtime.successor.computer import _change

    original = httpx.Client
    journal = Journal.initialize(tmp_path / "home")
    output = tmp_path / "out"

    def respond(request):
        run_id = json.loads((output / "run.json").read_text())["run_id"]
        key = "@successor-computer:" + run_id
        latest = journal.latest(key)
        _change(journal, key, latest["revision"], state="stopped")
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "usage": {"input_tokens": 17, "output_tokens": 3, "total_tokens": 20},
                "output": [{"type": "message", "content": [{"type": "output_text", "text": "untrusted done"}]}],
            },
        )

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    advisor = HTTPAdvisor("responses", "explicit-test-model", "https://api.openai.com/v1", "TEST_ONLY")
    image = "sha256:" + "a" * 64
    with pytest.raises(Conflict):
        run_session(journal, task(), advisor, image, output, commitment(task(), advisor, image), factory=TestComputer)
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["state"] == "stopped" and receipt["actions_reserved"] == 0
    assert receipt["provider_usage"][0]["status"] == "PROVIDER_REPORTED"
    assert receipt["billing"] == "UNKNOWN" and receipt["cleanup"] == "VERIFIED"
