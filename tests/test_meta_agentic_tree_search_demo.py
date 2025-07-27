# SPDX-License-Identifier: Apache-2.0
import subprocess
import sys
import unittest
import pytest
from alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge import (
    DEFAULT_MODEL_NAME,
)


class TestMetaAgenticTreeSearchDemo(unittest.TestCase):
    """Ensure the MATS demo entrypoint runs successfully."""

    def test_run_demo_short(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo",
                "--episodes",
                "3",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Best agents", result.stderr)

    def test_run_demo_openai_rewriter(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo",
                "--episodes",
                "2",
                "--rewriter",
                "openai",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Best agents", result.stderr)

    def test_run_demo_anthropic_rewriter(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo",
                "--episodes",
                "2",
                "--rewriter",
                "anthropic",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Best agents", result.stderr)

    def test_env_rollout(self) -> None:
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0.mats.env import (
            NumberLineEnv,
            LiveBrokerEnv,
        )

        env = NumberLineEnv(target=3)
        reward = env.rollout([3, 3, 3])
        self.assertGreaterEqual(reward, -0.1)

        live = LiveBrokerEnv(target=2, market_data=[2, 2])
        live_reward = live.rollout([2, 2])
        self.assertIsInstance(live_reward, float)

    def test_openai_rewrite_fallback(self) -> None:
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0.mats.meta_rewrite import (
            openai_rewrite,
        )

        out = openai_rewrite([1, 2, 3])
        self.assertEqual(len(out), 3)

    def test_anthropic_rewrite_fallback(self) -> None:
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0.mats.meta_rewrite import (
            anthropic_rewrite,
        )

        out = anthropic_rewrite([1, 2, 3])
        self.assertEqual(len(out), 3)

    def test_parse_numbers_helper(self) -> None:
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0.mats.meta_rewrite import (
            _parse_numbers,
        )

        text = "[1, 2, -3]"
        res = _parse_numbers(text, [0, 0, 0])
        self.assertEqual(res, [1, 2, -3])

        malformed = "{oops: 7}"
        res_fallback = _parse_numbers(malformed, [4, 4, 4])
        self.assertEqual(res_fallback, [5, 5, 5])

    def test_run_demo_with_target(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo",
                "--episodes",
                "2",
                "--target",
                "7",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Best agents", result.stderr)

    def test_run_demo_with_seed(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo",
                "--episodes",
                "2",
                "--seed",
                "123",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Best agents", result.stderr)

    def test_run_demo_seed_repeat(self) -> None:
        """Running the demo twice with the same seed yields identical results."""
        cmd = [
            sys.executable,
            "-m",
            "alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo",
            "--episodes",
            "2",
            "--seed",
            "321",
        ]

        first = subprocess.run(cmd, capture_output=True, text=True)
        second = subprocess.run(cmd, capture_output=True, text=True)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)

        first_line = [line for line in first.stderr.splitlines() if "Best agents" in line][-1]
        second_line = [line for line in second.stderr.splitlines() if "Best agents" in line][-1]

        self.assertEqual(first_line, second_line)

    def test_run_demo_verify_env(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo",
                "--episodes",
                "1",
                "--verify-env",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Best agents", result.stderr)

    def test_run_demo_market_data(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("6,6,6")
            feed_path = fh.name
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo",
                "--episodes",
                "2",
                "--market-data",
                feed_path,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Best agents", result.stderr)

    def test_bridge_fallback(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge",
                "--episodes",
                "1",
                "--target",
                "3",
                "--model",
                DEFAULT_MODEL_NAME,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("offline demo", result.stderr.lower())

    def test_bridge_run_search_helper(self) -> None:
        import asyncio
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0 import (
            openai_agents_bridge as bridge,
        )

        if bridge.has_oai:  # pragma: no cover - only run offline path
            self.skipTest("openai-agents installed")

        result = asyncio.run(bridge.run_search(episodes=1, target=2, model="gpt-4o"))
        self.assertIn("completed", result)

    def test_bridge_verify_env(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge",
                "--episodes",
                "1",
                "--verify-env",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bridge_market_data(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("6,6,6")
            feed_path = fh.name

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge",
                "--episodes",
                "1",
                "--market-data",
                feed_path,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bridge_market_data_output(self) -> None:
        """Bridge handles CSV input and prints agent summary."""
        import tempfile

        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("1,2,3")
            csv_file = fh.name

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge",
                "--episodes",
                "1",
                "--market-data",
                csv_file,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Best agents", result.stderr)

    def test_bridge_enable_adk(self) -> None:
        """Bridge accepts the --enable-adk flag."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge",
                "--episodes",
                "1",
                "--enable-adk",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


def test_bridge_online_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("openai_agents", minversion="0.0.17")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge",
            "--episodes",
            "1",
            "--rewriter",
            "openai",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Best agents" in result.stderr


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
