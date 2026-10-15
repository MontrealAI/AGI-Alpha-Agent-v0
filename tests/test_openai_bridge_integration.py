# SPDX-License-Identifier: Apache-2.0
import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch
import json

# ruff: noqa: E402

# Provide a dummy openai_agents module so bridge imports succeed even when
# the real package is absent or conflicts with a different "agents" module.
_oai = types.ModuleType("openai_agents")


class _AgentRuntime:
    def __init__(self, *a, **kw):
        pass

    def register(self, *_a, **_kw):
        pass

    def run(self) -> None:
        pass


_oai.Agent = object
_oai.AgentRuntime = _AgentRuntime


def _tool(*_a, **_kw):
    def _decorator(func):
        return func

    return _decorator


_oai.Tool = _tool
sys.modules["openai_agents"] = _oai

# Provide a dummy google_adk module so adk_bridge imports succeed
_dummy = types.ModuleType("google_adk")
_dummy.Agent = object


class _Router:
    def __init__(self):
        self.app = types.SimpleNamespace(middleware=lambda *_a, **_k: lambda f: f)

    def register_agent(self, _agent):
        pass


_dummy.Router = _Router
_dummy.AgentException = Exception
sys.modules.setdefault("google_adk", _dummy)

from alpha_factory_v1.demos.alpha_agi_business_v1 import openai_agents_bridge as bridge


class DummyResponse:
    def __init__(self, payload=None, text="ok", status_code=200):
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


class TestBusinessAgentIntegration(unittest.TestCase):
    def test_list_agents(self):
        with patch.object(bridge, "AsyncClient") as client_cls:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.get.return_value = DummyResponse(["a"])
            client_cls.return_value = client
            result = asyncio.run(bridge.list_agents())
        client.get.assert_awaited_once_with(f"{bridge.HOST}/agents", headers=bridge.HEADERS, timeout=5)
        self.assertEqual(result, ["a"])

    def test_trigger_discovery(self):
        with patch.object(bridge, "AsyncClient") as client_cls:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.post.return_value = DummyResponse()
            client_cls.return_value = client
            result = asyncio.run(bridge.trigger_discovery())
        client.post.assert_awaited_once_with(
            f"{bridge.HOST}/agent/alpha_discovery/trigger",
            headers=bridge.HEADERS,
            timeout=5,
        )
        self.assertEqual(result, "alpha_discovery queued")

    def test_submit_job(self):
        from alpha_factory_v1.demos.alpha_agi_business_v1.evaluation import evaluate_submission

        state = {
            "budget": 100,
            "max_loss": 20,
            "opportunities": [{"id": "a", "cost": 60, "benefit": 90, "worst_loss": 15}],
        }
        expected = evaluate_submission(json.dumps(state).encode())
        job = {"agent": "alpha_execution", "state": state}
        with patch.object(bridge, "AsyncClient") as client_cls:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.post.return_value = DummyResponse(expected)
            client_cls.return_value = client
            result = asyncio.run(bridge.submit_job(job))
        client.post.assert_awaited_once_with(
            f"{bridge.HOST}/agent/alpha_execution/evaluate",
            json=state,
            headers=bridge.HEADERS,
            timeout=5,
        )
        self.assertEqual(json.loads(result), expected)

    def test_submit_job_rejects_unsupported_input(self):
        with patch.object(bridge, "AsyncClient") as client_cls:
            with self.assertRaises(ValueError):
                asyncio.run(bridge.submit_job({"agent": "alpha_discovery", "foo": 1}))
            client_cls.assert_not_called()

    def test_submit_job_does_not_accept_queue_acknowledgement(self):
        state = {
            "budget": 100,
            "max_loss": 20,
            "opportunities": [{"id": "a", "cost": 60, "benefit": 90, "worst_loss": 15}],
        }
        for payload in [{"queued": True}, {"status": "evaluated_supplied_assumptions", "input_id": "stale"}]:
            with patch.object(bridge, "AsyncClient") as client_cls:
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.post.return_value = DummyResponse(payload)
                client_cls.return_value = client
                with self.assertRaises(RuntimeError):
                    asyncio.run(bridge.submit_job({"agent": "alpha_execution", "state": state}))

    def test_trigger_best_alpha(self):
        """A score-only bundled opportunity is not a complete evaluation input."""
        with patch.object(bridge, "AsyncClient") as client_cls:
            with self.assertRaisesRegex(ValueError, "Nothing was queued or executed"):
                asyncio.run(bridge.trigger_best_alpha())
            client_cls.assert_not_called()

    def test_check_health(self):
        with patch.object(bridge, "AsyncClient") as client_cls:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.get.return_value = DummyResponse(text="healthy")
            client_cls.return_value = client
            result = asyncio.run(bridge.check_health())
        client.get.assert_awaited_once_with(f"{bridge.HOST}/healthz", headers=bridge.HEADERS, timeout=5)
        self.assertEqual(result, "healthy")

    def test_policy_dispatch_discover(self):
        agent = bridge.BusinessAgent()
        with patch.object(bridge, "trigger_discovery", new=AsyncMock(return_value="ok")) as func:
            result = asyncio.run(agent.policy({"action": "discover"}, None))
        func.assert_awaited_once_with()
        self.assertEqual(result, "ok")


if __name__ == "__main__":  # pragma: no cover - manual run
    unittest.main()
