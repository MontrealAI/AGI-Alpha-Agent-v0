# SPDX-License-Identifier: Apache-2.0
"""Tests for webhook alert integration."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import pytest

from alpha_factory_v1.core import orchestrator
from alpha_factory_v1.core.utils import alerts, config
from alpha_factory_v1.common.utils import messaging
from alpha_factory_v1.core.agents.base_agent import BaseAgent


class DummyLedger:
    def __init__(self, *_a, **_kw) -> None:
        self.events = []

    def log(self, env) -> None:  # type: ignore[override]
        self.events.append(env.payload.get("event"))

    def start_merkle_task(self, *_a, **_kw) -> None:  # pragma: no cover - test stub
        pass

    async def stop_merkle_task(self) -> None:  # pragma: no cover - test stub
        pass

    def close(self) -> None:  # pragma: no cover - test stub
        pass


class DummyAgent(BaseAgent):
    NAME = "dummy"

    def __init__(self, bus: messaging.A2ABus, ledger: DummyLedger) -> None:
        super().__init__("dummy", bus, ledger)

    async def run_cycle(self) -> None:
        raise RuntimeError("boom")

    async def handle(self, _env) -> None:
        pass


def test_restart_alert(monkeypatch) -> None:
    sent: dict[str, object] = {}

    def fake_post(url: str, *, json=None, timeout=None):
        sent["url"] = url
        sent["payload"] = json
        return type("R", (), {"status_code": 200})()

    monkeypatch.setattr(alerts, "requests", type("M", (), {"post": fake_post}))
    monkeypatch.setattr(orchestrator, "Ledger", DummyLedger)
    monkeypatch.setattr(orchestrator.Orchestrator, "_init_agents", lambda self: [])

    settings = config.Settings(bus_port=0, alert_webhook_url="http://hook")
    orch = orchestrator.Orchestrator(settings)
    runner = orchestrator.AgentRunner(DummyAgent(orch.bus, orch.ledger))

    orch._record_restart(runner)

    assert sent["url"] == "http://hook"
    assert (
        sent["payload"].get("text") == "dummy restarted"
        if "text" in sent["payload"]
        else sent["payload"].get("content") == "dummy restarted"
    )


def test_agent_failure_alert(monkeypatch) -> None:
    sent: dict[str, object] = {}

    def fake_post(url: str, *, json=None, timeout=None):
        sent["url"] = url
        sent["payload"] = json
        return type("R", (), {"status_code": 200})()

    monkeypatch.setattr(alerts, "requests", type("M", (), {"post": fake_post}))
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "http://hook")

    bus = messaging.A2ABus(config.Settings(bus_port=0))
    ledger = DummyLedger()
    runner = orchestrator.AgentRunner(DummyAgent(bus, ledger))

    async def run() -> None:
        task = asyncio.create_task(runner.loop(bus, ledger))
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    asyncio.run(run())

    assert sent["url"] == "http://hook"
    assert "failed" in (sent["payload"].get("text") or sent["payload"].get("content", ""))


def test_alert_warning(monkeypatch, caplog: pytest.LogCaptureFixture) -> None:
    def fake_post(*_a, **_kw):
        return type("R", (), {"status_code": 500})()

    monkeypatch.setattr(alerts, "requests", type("M", (), {"post": fake_post}))

    caplog.set_level(logging.WARNING)
    alerts.send_alert("oops", "http://hook")
    assert any("status 500" in r.getMessage() for r in caplog.records)
