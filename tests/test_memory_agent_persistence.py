# SPDX-License-Identifier: Apache-2.0
import asyncio
from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import memory_agent
from alpha_factory_v1.common.utils import config, messaging, logging


def test_memory_agent_persists_records(tmp_path):
    mem_file = tmp_path / "mem.log"
    cfg = config.Settings(bus_port=0, memory_path=str(mem_file))
    bus = messaging.A2ABus(cfg)
    led = logging.Ledger(str(tmp_path / "ledger.db"))
    agent = memory_agent.MemoryAgent(bus, led, str(mem_file))
    env = messaging.Envelope(sender="a", recipient="memory", payload={"v": 1}, ts=0.0)

    async def run() -> None:
        async with bus, led:
            await agent.handle(env)

    asyncio.run(run())
    agent2 = memory_agent.MemoryAgent(bus, led, str(mem_file))
    assert agent2.records and agent2.records[0]["v"] == 1
