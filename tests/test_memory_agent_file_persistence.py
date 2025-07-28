# SPDX-License-Identifier: Apache-2.0
import asyncio
import json
from pathlib import Path

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import memory_agent
from alpha_factory_v1.common.utils import config, messaging, logging
import pytest


def test_memory_agent_file_cap(tmp_path: Path) -> None:
    mem_file = tmp_path / "mem.log"
    cfg = config.Settings(bus_port=0, memory_path=str(mem_file))
    bus = messaging.A2ABus(cfg)
    ledger = logging.Ledger(str(tmp_path / "ledger.db"))
    agent = memory_agent.MemoryAgent(bus, ledger, str(mem_file), memory_limit=2)

    envs = [messaging.Envelope(sender="a", recipient="memory", payload={"v": i}, ts=0.0) for i in range(3)]

    async def _run() -> None:
        async with bus, ledger:
            for env in envs:
                await agent.handle(env)

    asyncio.run(_run())

    entries = [json.loads(line) for line in mem_file.read_text(encoding="utf-8").splitlines()]
    assert [e["v"] for e in entries] == [1, 2]

    agent2 = memory_agent.MemoryAgent(bus, ledger, str(mem_file), memory_limit=2)
    assert [r["v"] for r in agent2.records] == [1, 2]


def test_memory_agent_env_var_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mem_file = tmp_path / "mem.log"
    monkeypatch.setenv("AGI_INSIGHT_MEMORY_LIMIT", "2")
    cfg = config.Settings(bus_port=0, memory_path=str(mem_file))
    bus = messaging.A2ABus(cfg)
    ledger = logging.Ledger(str(tmp_path / "ledger.db"))
    agent = memory_agent.MemoryAgent(bus, ledger, str(mem_file))

    envs = [messaging.Envelope(sender="a", recipient="memory", payload={"i": i}, ts=0.0) for i in range(3)]

    async def _run() -> None:
        async with bus, ledger:
            for env in envs:
                await agent.handle(env)

    asyncio.run(_run())

    entries = [json.loads(line) for line in mem_file.read_text(encoding="utf-8").splitlines()]
    assert [e["i"] for e in entries] == [1, 2]
