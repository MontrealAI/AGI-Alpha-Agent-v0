# SPDX-License-Identifier: Apache-2.0
import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch
import json
from fractions import Fraction
from itertools import permutations
from pathlib import Path

from alpha_factory_v1.demos.alpha_agi_business_3_v1.enterprise import canonical, digest
from alpha_factory_v1.demos.alpha_agi_business_v1 import evaluation

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


def supplied_positions(pairs):
    """Use accepted quantity/price bounds, never an out-of-range raw notional."""
    return {
        "budget": 100,
        "max_loss": 20,
        "opportunities": [{"id": "a", "cost": 60, "benefit": 90, "worst_loss": 15}],
        "positions": [{"id": str(i), "quantity": q, "price": p} for i, (q, p) in enumerate(pairs)],
    }


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

    def test_portfolio_totals_match_exact_binary_float_oracle(self):
        # Oracle sums the already-rounded position products, matching the public
        # float contract, without relying on Python's version-dependent sum(float).
        cases = [
            [],
            [(1e8, 1e8), (1, 1), (1, 1), (-1e8, 1e8)],
            [(1e8, 1e8), (1, 1), (1, 1)],
            [(1e12, 1e12), (1, 1), (-1e12, 1e12)],
            [(0.1, 0.2), (0.3, 0.4), (-0.1, 0.2)],
        ]
        for pairs in cases:
            for ordered in set(permutations(pairs)):
                state = supplied_positions(ordered)
                values = [float(q) * float(p) for q, p in ordered]
                exact_net = float(sum((Fraction.from_float(v) for v in values), Fraction()))
                exact_gross = float(sum((abs(Fraction.from_float(v)) for v in values), Fraction()))
                with self.subTest(positions=ordered):
                    portfolio = evaluation.evaluate(state)["portfolio"]
                    self.assertEqual(portfolio["net_value"], exact_net)
                    self.assertEqual(portfolio["gross_value"], exact_gross)
                    self.assertIs(type(portfolio["net_value"]), float)
                    self.assertIs(type(portfolio["gross_value"]), float)

    def test_cross_version_canonical_report_and_bridge_binding(self):
        # Fixed complete-report hashes are shared by the mandatory 3.11/3.12/3.13
        # CI runs. A same-runtime recomputation alone cannot detect this bug.
        cases = [
            (
                [(1e8, 1e8), (1, 1), (1, 1), (-1e8, 1e8)],
                "67378d3fce2c597fa2b00b184ed7fd56c16b6b60f0dc710680e756ca156c3aeb",
            ),
            ([(1e8, 1e8), (1, 1), (1, 1)], "f4bb605ad7e602bbb0e43161ec09eb9933c1940a2e326105a0fe11513f1daea3"),
            ([], "e1d7ad7d1a2b23ff00690fe4ac5cdd9b65bae3321967810ed515e8b00d4989ae"),
        ]
        for pairs, expected_digest in cases:
            state = supplied_positions(pairs)
            peer = evaluation.evaluate_submission(json.dumps(state).encode())
            with self.subTest(positions=pairs):
                self.assertEqual(digest(peer), expected_digest)
                with patch.object(bridge, "AsyncClient") as client_cls:
                    client = AsyncMock()
                    client.__aenter__.return_value = client
                    client.post.return_value = DummyResponse(peer)
                    client_cls.return_value = client
                    result = asyncio.run(bridge.submit_job({"agent": "alpha_execution", "state": state}))
                self.assertEqual(canonical(json.loads(result)), canonical(peer))
                self.assertEqual(digest(json.loads(result)), expected_digest)
                client.post.assert_awaited_once_with(
                    f"{bridge.HOST}/agent/alpha_execution/evaluate",
                    json=state,
                    headers=bridge.HEADERS,
                    timeout=5,
                )

    def test_preserved_baseline_rejects_different_sum_without_weakening_binding(self):
        evidence = json.loads((Path(__file__).parent / "fixtures" / "business1_sum_binding_baseline.json").read_text())
        state = evidence["state"]
        peer = json.loads(evidence["peer_report_canonical_utf8"])
        legacy = json.loads(evidence["emulated_311_report_canonical_utf8"])
        self.assertEqual(digest(peer), evidence["peer_report_sha256"])
        self.assertEqual(digest(legacy), evidence["emulated_311_report_sha256"])
        self.assertEqual(canonical(evaluation.evaluate_submission(json.dumps(state).encode())), canonical(peer))
        self.assertEqual(peer["evaluation"]["portfolio"]["net_value"], 2.0)
        self.assertEqual(legacy["evaluation"]["portfolio"]["net_value"], 0.0)
        with patch.object(bridge, "AsyncClient") as client_cls:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.post.return_value = DummyResponse(legacy)
            client_cls.return_value = client
            with self.assertRaisesRegex(RuntimeError, "does not match the submitted-input evaluation"):
                asyncio.run(bridge.submit_job({"agent": "alpha_execution", "state": state}))

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
