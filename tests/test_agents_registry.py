# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
import unittest
import asyncio
import io
import logging
import os
import sys
import subprocess

from alpha_factory_v1.backend.agents.registry import (
    AGENT_REGISTRY,
    CAPABILITY_GRAPH,
    AgentMetadata,
    register_agent,
    list_agents,
    capability_agents,
    get_agent,
)
from alpha_factory_v1.backend.agents.base import AgentBase


class TestAgentRegistryFunctions(unittest.TestCase):
    def setUp(self):
        self._registry_backup = AGENT_REGISTRY.copy()
        self._cap_backup = {k: v[:] for k, v in CAPABILITY_GRAPH.items()}
        AGENT_REGISTRY.clear()
        CAPABILITY_GRAPH.clear()

    def tearDown(self):
        AGENT_REGISTRY.clear()
        AGENT_REGISTRY.update(self._registry_backup)
        CAPABILITY_GRAPH.clear()
        for cap, agents in self._cap_backup.items():
            for name in agents:
                CAPABILITY_GRAPH.add(cap, name)

    def test_register_and_get(self):
        class DummyAgent(AgentBase):
            NAME = "dummy_test"
            CAPABILITIES = ["foo"]

            async def step(self):
                return None

        meta = AgentMetadata(
            name=DummyAgent.NAME,
            cls=DummyAgent,
            version="0.1",
            capabilities=DummyAgent.CAPABILITIES,
            compliance_tags=[],
        )
        register_agent(meta)

        self.assertIn(DummyAgent.NAME, list_agents())
        self.assertEqual(capability_agents("foo"), [DummyAgent.NAME])
        agent = get_agent(DummyAgent.NAME)
        self.assertIsInstance(agent, DummyAgent)

    def test_list_and_detail_counts_match(self):
        # registry should return same number of agents regardless of detail flag
        names = list_agents()
        details = list_agents(detail=True)
        self.assertEqual(len(names), len(details))

    def test_ping_capability_present(self):
        # diagnostics capability should map to the ping agent
        from alpha_factory_v1.backend.agents.ping_agent import PingAgent

        meta = AgentMetadata(
            name=PingAgent.NAME,
            cls=PingAgent,
            version="0",
            capabilities=PingAgent.CAPABILITIES,
            compliance_tags=[],
        )
        register_agent(meta)
        agents = capability_agents("diagnostics")
        self.assertIn("ping", agents)

    def test_list_agents_sorted(self):
        class AAgent(AgentBase):
            NAME = "a_a"

            async def step(self):
                return None

        class BAgent(AgentBase):
            NAME = "b_b"

            async def step(self):
                return None

        register_agent(AgentMetadata(name=BAgent.NAME, cls=BAgent))
        register_agent(AgentMetadata(name=AAgent.NAME, cls=AAgent))

        names = list_agents()
        self.assertEqual(names, sorted(names))

    def test_get_agent_health_queue(self):
        from alpha_factory_v1.backend import agents as agents_mod
        from alpha_factory_v1.backend.agents import registry as registry_mod
        from queue import Queue

        saved_agents_q = agents_mod._HEALTH_Q
        saved_registry_q = registry_mod._HEALTH_Q
        tmp_q = Queue()
        agents_mod._HEALTH_Q = tmp_q
        registry_mod._HEALTH_Q = tmp_q

        class WrapAgent(AgentBase):
            NAME = "wrap"

            async def step(self):
                return "ok"

        register_agent(AgentMetadata(name=WrapAgent.NAME, cls=WrapAgent))

        while not agents_mod._HEALTH_Q.empty():
            agents_mod._HEALTH_Q.get()

        agent = get_agent(WrapAgent.NAME)
        asyncio.run(agent.step())
        name, latency, ok = agents_mod._HEALTH_Q.get(timeout=2)
        self.assertEqual(name, WrapAgent.NAME)
        self.assertTrue(ok)
        self.assertIsInstance(latency, float)

        agents_mod._HEALTH_Q = saved_agents_q
        registry_mod._HEALTH_Q = saved_registry_q

    def test_list_agents_detail(self):
        class DAgent(AgentBase):
            NAME = "detail"
            CAPABILITIES = ["bar"]

            async def step(self):
                return None

        meta = AgentMetadata(
            name=DAgent.NAME,
            cls=DAgent,
            version="1.2",
            capabilities=DAgent.CAPABILITIES,
            compliance_tags=["x"],
        )
        register_agent(meta)
        detail = list_agents(detail=True)
        self.assertEqual(detail[0]["name"], DAgent.NAME)
        self.assertEqual(detail[0]["version"], "1.2")
        self.assertIn("bar", detail[0]["capabilities"])


class TestPingAgentDisabled(unittest.TestCase):
    def test_ping_agent_skipped_when_env_set(self):
        code = "import alpha_factory_v1.backend.agents as mod; print('ping' in mod.AGENT_REGISTRY)"
        env = os.environ.copy()
        env["AF_DISABLE_PING_AGENT"] = "true"
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        self.assertEqual(result.stdout.strip(), "False")


class TestRegisterDecorator(unittest.TestCase):
    def setUp(self):
        self._registry_backup = AGENT_REGISTRY.copy()
        AGENT_REGISTRY.clear()

    def tearDown(self):
        AGENT_REGISTRY.clear()
        AGENT_REGISTRY.update(self._registry_backup)

    def test_condition_false(self):
        from alpha_factory_v1.backend.agents.registry import register, _agent_base

        Base = _agent_base()

        @register(condition=False)
        class SkipAgent(Base):
            NAME = "skip"

            async def step(self):
                return None

        self.assertNotIn("skip", AGENT_REGISTRY)

    def test_condition_true(self):
        from alpha_factory_v1.backend.agents.registry import register, _agent_base

        Base = _agent_base()

        @register
        class OkAgent(Base):
            NAME = "ok"

            async def step(self):
                return None

        self.assertIn("ok", AGENT_REGISTRY)


class TestHealthQuarantine(unittest.TestCase):
    def setUp(self):
        self._registry_backup = AGENT_REGISTRY.copy()
        AGENT_REGISTRY.clear()

    def tearDown(self):
        AGENT_REGISTRY.clear()
        AGENT_REGISTRY.update(self._registry_backup)

    def test_stub_after_errors(self):
        from alpha_factory_v1.backend.agents.registry import (
            _HEALTH_Q,
            StubAgent,
            _ERR_THRESHOLD,
        )
        from alpha_factory_v1.backend.agents.health import (
            start_background_tasks,
            stop_background_tasks,
        )

        class FailingAgent(AgentBase):
            NAME = "fail"

            async def step(self):
                raise RuntimeError("boom")

        meta = AgentMetadata(name="fail", cls=FailingAgent, version="0", capabilities=[])  # type: ignore[list-item]
        register_agent(meta)

        async def _run() -> None:
            await start_background_tasks()
            # Pre-set error count to threshold -1
            object.__setattr__(AGENT_REGISTRY["fail"], "err_count", _ERR_THRESHOLD - 1)
            _HEALTH_Q.put(("fail", 0.0, False))
            await asyncio.sleep(0.05)
            self.assertIs(AGENT_REGISTRY["fail"].cls, StubAgent)
            await stop_background_tasks()

        asyncio.run(_run())


class TestVersionOverride(unittest.TestCase):
    def setUp(self):
        self._backup = AGENT_REGISTRY.copy()
        AGENT_REGISTRY.clear()

    def tearDown(self):
        AGENT_REGISTRY.clear()
        AGENT_REGISTRY.update(self._backup)

    def test_higher_version_replaces(self):
        class AgentV1(AgentBase):
            NAME = "dup"
            VERSION = "1.0"

            async def step(self):
                return None

        class AgentV2(AgentBase):
            NAME = "dup"
            VERSION = "1.1"

            async def step(self):
                return None

        register_agent(AgentMetadata(name="dup", cls=AgentV1, version="1.0"))
        register_agent(AgentMetadata(name="dup", cls=AgentV2, version="1.1"))

        self.assertIs(AGENT_REGISTRY["dup"].cls, AgentV2)
        self.assertEqual(AGENT_REGISTRY["dup"].version, "1.1")

    def test_lower_version_ignored(self):
        class AgentV1(AgentBase):
            NAME = "dup"
            VERSION = "1.0"

            async def step(self):
                return None

        class AgentOld(AgentBase):
            NAME = "dup"
            VERSION = "0.9"

            async def step(self):
                return None

        register_agent(AgentMetadata(name="dup", cls=AgentV1, version="1.0"))
        register_agent(AgentMetadata(name="dup", cls=AgentOld, version="0.9"))

        self.assertIs(AGENT_REGISTRY["dup"].cls, AgentV1)
        self.assertEqual(AGENT_REGISTRY["dup"].version, "1.0")


class TestDiscoverLocalIdempotent(unittest.TestCase):
    def test_no_duplicate_logs(self):
        from alpha_factory_v1.backend import agents as agents_mod

        logger = logging.getLogger("alpha_factory.agents")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        agents_mod._discover_local()  # first call may log agents
        stream.truncate(0)
        stream.seek(0)
        agents_mod._discover_local()  # second call should be quiet
        logger.removeHandler(handler)
        logs = stream.getvalue()
        self.assertNotIn("Duplicate agent name", logs)
        self.assertNotIn("\u2713 agent", logs)


if __name__ == "__main__":
    unittest.main()
