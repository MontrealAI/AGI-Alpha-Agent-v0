# SPDX-License-Identifier: Apache-2.0
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from alpha_factory_v1.demos.solving_agi_governance import run_sim, summarise_with_agent


class TestGovernanceSim(unittest.TestCase):
    def test_basic_convergence(self) -> None:
        coop = run_sim(agents=50, rounds=500, delta=0.85, stake=2.5, seed=1)
        self.assertGreater(coop, 0.7)

    def test_summary_offline(self) -> None:
        text = summarise_with_agent(0.8, agents=10, rounds=100, delta=0.9, stake=1.0)
        self.assertIsInstance(text, str)
        self.assertIn("mean cooperation", text)

    def test_summary_with_openai_mock(self) -> None:
        completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("openai.OpenAI") as mock_client:
                mock_client.return_value.chat.completions.create.return_value = completion
                text = summarise_with_agent(
                    0.9,
                    agents=5,
                    rounds=10,
                    delta=0.8,
                    stake=1.0,
                )
        self.assertEqual(text, "ok")
        mock_client.assert_called_once()
        self.assertEqual(mock_client.call_args.kwargs.get("timeout"), 30)
        kwargs = mock_client.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs.get("timeout"), 30)

    def test_summary_auth_error(self) -> None:
        import openai
        import httpx

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("openai.OpenAI") as mock_client:
                request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
                response = httpx.Response(401, request=request)
                mock_client.return_value.chat.completions.create.side_effect = openai.AuthenticationError(
                    "bad key",
                    response=response,
                    body=None,
                )
                text = summarise_with_agent(
                    0.5,
                    agents=2,
                    rounds=10,
                    delta=0.9,
                    stake=1.0,
                )
        self.assertIn("OPENAI_API_KEY not set", text)
        self.assertIn("offline summary", text)

    def test_summary_api_connection_error(self) -> None:
        import openai
        import httpx

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("openai.OpenAI") as mock_client:
                request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
                mock_client.return_value.chat.completions.create.side_effect = openai.APIConnectionError(
                    message="fail",
                    request=request,
                )
                text = summarise_with_agent(
                    0.5,
                    agents=2,
                    rounds=10,
                    delta=0.9,
                    stake=1.0,
                )
        self.assertIn("offline summary", text)
        self.assertIn("connection", text)

    def test_summary_rate_limit_error(self) -> None:
        import openai
        import httpx

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("openai.OpenAI") as mock_client:
                request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
                response = httpx.Response(429, request=request)
                mock_client.return_value.chat.completions.create.side_effect = openai.RateLimitError(
                    "limit",
                    response=response,
                    body=None,
                )
                text = summarise_with_agent(
                    0.5,
                    agents=2,
                    rounds=10,
                    delta=0.9,
                    stake=1.0,
                )
        self.assertIn("offline summary", text)
        self.assertIn("rate limit", text)

    def test_agents_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            run_sim(agents=0, rounds=10, delta=0.5, stake=1.0)
        with self.assertRaises(ValueError):
            run_sim(agents=-1, rounds=10, delta=0.5, stake=1.0)

    def test_rounds_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            run_sim(agents=1, rounds=0, delta=0.5, stake=1.0)
        with self.assertRaises(ValueError):
            run_sim(agents=1, rounds=-5, delta=0.5, stake=1.0)

    def test_delta_must_be_within_range(self) -> None:
        with self.assertRaises(ValueError):
            run_sim(agents=1, rounds=10, delta=-0.1, stake=1.0)
        with self.assertRaises(ValueError):
            run_sim(agents=1, rounds=10, delta=1.1, stake=1.0)

    def test_stake_must_not_be_negative(self) -> None:
        with self.assertRaises(ValueError):
            run_sim(agents=1, rounds=10, delta=0.5, stake=-0.1)


if __name__ == "__main__":
    unittest.main()
