# SPDX-License-Identifier: Apache-2.0
import unittest
import asyncio
import os
import time
from typing import Any

from alpha_factory_v1.demos.era_of_experience import agent_experience_entrypoint as demo
from alpha_factory_v1.demos.era_of_experience import reward_backends
from alpha_factory_v1.demos.era_of_experience.simulation import SimpleExperienceEnv
from alpha_factory_v1.demos.era_of_experience.stub_agents import (
    ExperienceAgent,
    FederatedExperienceAgent,
)


class TestEraOfExperience(unittest.TestCase):
    def test_experience_stream_yields_event(self) -> None:
        async def get_event() -> dict[str, Any]:
            gen = demo.experience_stream()
            return await anext(gen)

        evt = asyncio.run(get_event())
        self.assertIsInstance(evt, dict)
        self.assertIn("kind", evt)
        self.assertIn("payload", evt)

    def test_stream_rate_env_controls_interval(self) -> None:
        os.environ["STREAM_RATE_HZ"] = "5"

        async def grab_two() -> float:
            gen = demo.experience_stream()
            t1 = time.perf_counter()
            await anext(gen)
            t2 = time.perf_counter()
            await anext(gen)
            t3 = time.perf_counter()
            return (t2 - t1 + t3 - t2) / 2

        avg = asyncio.run(grab_two())
        del os.environ["STREAM_RATE_HZ"]
        self.assertLess(avg, 0.6)
        self.assertGreater(avg, 0.1)

    def test_reward_backends_produce_floats(self) -> None:
        names = reward_backends.list_rewards()
        self.assertTrue(names)
        for name in names:
            val = reward_backends.reward_signal(name, {}, None, {})
            self.assertIsInstance(val, float)
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)

    def test_fitness_reward_parses_sleep(self) -> None:
        evt = {"payload": {"activity": "Sleep 7 h 45 m"}}
        val = demo._fitness_reward(evt)
        self.assertIsInstance(val, float)

    def test_simple_env_runs(self) -> None:
        env = SimpleExperienceEnv()
        state = env.reset()
        self.assertEqual(state, 0)
        state, reward, done, info = env.step("act")
        self.assertIsInstance(reward, float)

    def test_stub_agents_instantiable(self) -> None:
        exp = ExperienceAgent()
        fed = FederatedExperienceAgent()
        self.assertTrue(hasattr(exp, "act"))
        self.assertTrue(hasattr(fed, "handle_request"))

    def test_ingest_and_step_concurrent(self) -> None:
        async def run_tasks() -> None:
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

            async def ingest_loop() -> None:
                async for evt in demo.experience_stream():
                    await queue.put(evt)
                    break

            async def step_once() -> None:
                evt = await queue.get()
                self.assertIsInstance(evt, dict)

            await asyncio.gather(ingest_loop(), step_once())

        try:
            asyncio.run(run_tasks())
        except RuntimeError as exc:  # pragma: no cover - fail if raised
            self.fail(f"RuntimeError raised: {exc}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
