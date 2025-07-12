# SPDX-License-Identifier: Apache-2.0
import asyncio

import pytest

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import codegen_agent
from alpha_factory_v1.common.utils import config, messaging
from alpha_factory_v1.common.utils.logging import Ledger


class DummyBus:
    def __init__(self, settings: config.Settings) -> None:
        self.settings = settings
        self.published = []

    def publish(self, topic: str, env: messaging.Envelope) -> None:
        self.published.append((topic, env))

    def subscribe(self, topic: str, handler) -> None:  # pragma: no cover - stub
        pass


class DummyLedger:
    def log(self, env: messaging.Envelope) -> None:  # pragma: no cover - stub
        pass

    def start_merkle_task(self, *a, **kw) -> None:  # pragma: no cover - stub
        pass

    async def stop_merkle_task(self) -> None:  # pragma: no cover - stub
        pass

    def close(self) -> None:  # pragma: no cover - stub
        pass


def test_skip_unsafe_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = config.Settings(bus_port=0)
    bus = DummyBus(cfg)
    ledger = DummyLedger()
    agent = codegen_agent.CodeGenAgent(bus, ledger)

    called = False

    def fake_exec(code: str) -> tuple[str, str]:
        nonlocal called
        called = True
        return "", ""

    monkeypatch.setattr(codegen_agent, "is_code_safe", lambda c: False)
    monkeypatch.setattr(agent, "execute_in_sandbox", fake_exec)

    env = messaging.Envelope(sender="market", recipient="codegen", ts=0.0)
    env.payload.update({"analysis": "x"})
    asyncio.run(agent.handle(env))
    assert not called
