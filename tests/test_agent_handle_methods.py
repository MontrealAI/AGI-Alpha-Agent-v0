# SPDX-License-Identifier: Apache-2.0
import asyncio
import random
from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import (
    memory_agent,
    strategy_agent,
    planning_agent,
    market_agent,
    research_agent,
    safety_agent,
    codegen_agent,
)
from alpha_factory_v1.common.utils import config, messaging


class DummyBus:
    def __init__(self, settings: config.Settings) -> None:
        self.settings = settings
        self.published: list[tuple[str, messaging.Envelope]] = []

    def publish(self, topic: str, env: messaging.Envelope) -> None:
        self.published.append((topic, env))

    def subscribe(self, topic: str, handler):
        pass


class DummyLedger:
    def __init__(self) -> None:
        self.logged: list[messaging.Envelope] = []

    def log(self, env: messaging.Envelope) -> None:  # type: ignore[override]
        self.logged.append(env)

    def start_merkle_task(self, *a, **kw):
        pass

    async def stop_merkle_task(self) -> None:  # pragma: no cover - interface
        pass

    def close(self) -> None:
        pass


def test_memory_agent_handle_appends() -> None:
    cfg = config.Settings(bus_port=0)
    bus = DummyBus(cfg)
    led = DummyLedger()
    agent = memory_agent.MemoryAgent(bus, led)
    env = messaging.Envelope(sender="a", recipient="memory", payload={"v": 1}, ts=0.0)
    asyncio.run(agent.handle(env))
    assert agent.records == [{"v": 1}]


def test_planning_agent_handle_logs() -> None:
    cfg = config.Settings(bus_port=0)
    bus = DummyBus(cfg)
    led = DummyLedger()
    agent = planning_agent.PlanningAgent(bus, led)
    env = messaging.Envelope(sender="a", recipient="planning", payload={"plan": "x"}, ts=0.0)
    asyncio.run(agent.handle(env))
    assert led.logged and led.logged[0] is env


def test_strategy_agent_emits_market() -> None:
    cfg = config.Settings(bus_port=0)
    bus = DummyBus(cfg)
    led = DummyLedger()
    agent = strategy_agent.StrategyAgent(bus, led)
    env = messaging.Envelope(sender="research", recipient="strategy", payload={"research": "foo"}, ts=0.0)
    asyncio.run(agent.handle(env))
    assert bus.published
    topic, sent = bus.published[-1]
    assert topic == "market"
    assert "strategy" in sent.payload


def test_market_agent_emits_codegen() -> None:
    cfg = config.Settings(bus_port=0)
    bus = DummyBus(cfg)
    led = DummyLedger()
    agent = market_agent.MarketAgent(bus, led)
    env = messaging.Envelope(sender="strategy", recipient="market", payload={"strategy": "foo"}, ts=0.0)
    asyncio.run(agent.handle(env))
    assert bus.published[-1][0] == "codegen"


def test_research_agent_emits_strategy(monkeypatch) -> None:
    cfg = config.Settings(bus_port=0, openai_api_key="k")
    bus = DummyBus(cfg)
    led = DummyLedger()
    agent = research_agent.ResearchAgent(bus, led)
    monkeypatch.setattr(random, "random", lambda: 0.5)
    env = messaging.Envelope(sender="planning", recipient="research", payload={"plan": "y"}, ts=0.0)
    asyncio.run(agent.handle(env))
    assert bus.published[-1][0] == "strategy"


def test_safety_agent_emits_status() -> None:
    cfg = config.Settings(bus_port=0)
    bus = DummyBus(cfg)
    led = DummyLedger()
    agent = safety_agent.SafetyGuardianAgent(bus, led)
    env = messaging.Envelope(sender="codegen", recipient="safety", payload={"code": "import os"}, ts=0.0)
    asyncio.run(agent.handle(env))
    assert bus.published[-1][1].payload["status"] == "blocked"


def test_codegen_agent_emits_to_safety(monkeypatch) -> None:
    cfg = config.Settings(bus_port=0)
    bus = DummyBus(cfg)
    led = DummyLedger()
    agent = codegen_agent.CodeGenAgent(bus, led)
    monkeypatch.setattr(agent, "execute_in_sandbox", lambda code: ("", ""))
    env = messaging.Envelope(sender="market", recipient="codegen", payload={"analysis": "x"}, ts=0.0)
    asyncio.run(agent.handle(env))
    assert bus.published[-1][0] == "safety"
