# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
# NOTE: This demo is a research prototype and does not implement real AGI.
"""OpenAI Agents SDK bridge for the solving_agi_governance demo."""
from __future__ import annotations

import argparse
import logging
import asyncio
import os
from typing import Sequence

from .governance_sim import run_sim

logger = logging.getLogger(__name__)

try:
    from openai_agents import Agent, AgentRuntime, Tool

    HAS_OAI = True
except ModuleNotFoundError:  # pragma: no cover - optional dep
    HAS_OAI = False


@Tool(name="run_sim", description="Run governance simulation")
async def run_sim_tool(
    agents: int = 100,
    rounds: int = 1000,
    delta: float = 0.8,
    stake: float = 2.5,
) -> float:
    """Run the governance simulation in a thread."""
    return await asyncio.to_thread(run_sim, agents, rounds, delta, stake)


class GovernanceSimAgent(Agent):
    """Agent exposing the governance simulation."""

    name = "governance_sim"
    tools = [run_sim_tool]

    async def policy(self, obs: object, ctx: object) -> float:
        """Return the simulation result for ``obs`` parameters.

        ``openai_agents`` does not ship type hints, so both ``obs`` and ``ctx``
        are typed as :class:`object` to match the base ``Agent.policy``
        signature.
        """
        if isinstance(obs, dict):
            return await self.tools.run_sim(
                int(obs.get("agents", 100)),
                int(obs.get("rounds", 1000)),
                float(obs.get("delta", 0.8)),
                float(obs.get("stake", 2.5)),
            )
        return await self.tools.run_sim()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Expose the governance simulation via OpenAI Agents runtime")
    ap.add_argument("-N", "--agents", type=int, default=100, help="agents when offline")
    ap.add_argument("-r", "--rounds", type=int, default=1000, help="rounds when offline")
    ap.add_argument("--delta", type=float, default=0.8, help="discount factor when offline")
    ap.add_argument("--stake", type=float, default=2.5, help="stake penalty when offline")
    ap.add_argument(
        "--enable-adk",
        action="store_true",
        help="Expose agent via ADK gateway",
    )
    ap.add_argument(
        "--port",
        type=int,
        help="Custom port for the Agents runtime",
    )
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args(argv)
    disable_agents = os.getenv("OPENAI_AGENTS_DISABLE", "").lower() in {"1", "true", "yes"}
    if not HAS_OAI or disable_agents:
        print("openai-agents package is missing. Running offline demo...")
        coop = run_sim(args.agents, args.rounds, args.delta, args.stake)
        print(f"mean cooperation \u2248 {coop:.3f}")
        return

    if args.port is not None:
        runtime = AgentRuntime(port=args.port, api_key=None)
    else:
        runtime = AgentRuntime(api_key=None)
    agent = GovernanceSimAgent()
    runtime.register(agent)
    logger.info("Registered GovernanceSimAgent with runtime")
    if args.enable_adk:
        logger.info("ADK bridge enabled for GovernanceSimAgent")
        try:
            from alpha_factory_v1.backend.adk_bridge import auto_register, maybe_launch

            auto_register([agent])
            maybe_launch()
        except Exception as exc:  # pragma: no cover - ADK optional
            logger.warning(f"ADK bridge unavailable: {exc}")
    if hasattr(runtime, "run"):
        runtime.run()
        return
    if hasattr(runtime, "serve"):
        runtime.serve()
        return
    logger.info("AgentRuntime run loop unavailable; exiting after registration")


if __name__ == "__main__":  # pragma: no cover
    main()
