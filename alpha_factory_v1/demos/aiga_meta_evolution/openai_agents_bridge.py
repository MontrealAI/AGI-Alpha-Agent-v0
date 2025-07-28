# SPDX-License-Identifier: Apache-2.0
# NOTE: This demo is a research prototype and does not implement real AGI.
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

OpenAI Agents SDK bridge for the AI-GA Meta-Evolution demo.

This script registers a minimal agent capable of driving the evolutionary
loop via the OpenAI Agents runtime. It works fully offline when no
``OPENAI_API_KEY`` is configured by falling back to the local Ollama
instance started by ``run_aiga_demo.sh``.
"""
from __future__ import annotations

try:  # optional dependency
    import openai_agents as _oa
    from openai_agents import Agent, Tool

    if not hasattr(_oa, "OpenAIAgent"):
        raise AttributeError
    OpenAIAgent = _oa.OpenAIAgent  # type: ignore[misc]
    AgentRuntime = getattr(_oa, "AgentRuntime", None)
    if AgentRuntime is None:
        from agents.run import Runner

        class AgentRuntime:  # type: ignore[misc]
            def __init__(self, *_: object, **__: object) -> None:
                self._runner = Runner()
                self._agent: Agent | None = None

            def register(self, agent: Agent) -> None:
                self._agent = agent

            def run(self) -> None:
                import asyncio

                if self._agent is None:
                    raise RuntimeError("No agent registered")

                asyncio.run(self._runner.run(self._agent, ""))

except Exception as exc:  # pragma: no cover - fallback stub
    raise ModuleNotFoundError("OpenAI Agents SDK is required to run the meta-evolution demo") from exc


try:
    from alpha_factory_v1.backend.adk_bridge import auto_register, maybe_launch

    ADK_AVAILABLE = True
except Exception:  # pragma: no cover - optional
    ADK_AVAILABLE = False

if __package__ is None:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent))
    __package__ = "alpha_factory_v1.demos.aiga_meta_evolution"

import os
from typing import cast

from .meta_evolver import MetaEvolver

try:
    from .curriculum_env import CurriculumEnv
except ModuleNotFoundError:  # gymnasium optional

    class CurriculumEnv:  # type: ignore[misc]
        pass


from .utils import build_llm


# ---------------------------------------------------------------------------
# LLM setup -----------------------------------------------------------------
# ---------------------------------------------------------------------------
LLM = build_llm()

# single MetaEvolver instance reused across tool invocations
EVOLVER: MetaEvolver | None = None


def _get_evolver() -> MetaEvolver:
    """Return the lazily created MetaEvolver instance."""
    global EVOLVER
    if EVOLVER is None:
        EVOLVER = MetaEvolver(env_cls=CurriculumEnv, llm=LLM)
    return EVOLVER


@Tool(name="evolve", description="Run N generations of evolution")  # type: ignore[misc]
async def evolve(generations: int = 1) -> str:
    """Advance the evolver by ``generations`` and return the latest log."""
    evolver = _get_evolver()
    evolver.run_generations(generations)
    return str(evolver.latest_log())


@Tool(name="best_alpha", description="Return current best architecture")  # type: ignore[misc]
async def best_alpha() -> dict[str, float | str]:
    """Return the best architecture seen so far."""
    evolver = _get_evolver()
    return {
        "architecture": evolver.best_architecture,
        "fitness": evolver.best_fitness,
    }


@Tool(name="checkpoint", description="Persist current state to disk")  # type: ignore[misc]
async def checkpoint() -> str:
    """Persist the current population to disk."""
    evolver = _get_evolver()
    evolver.save()
    return "checkpoint saved"


@Tool(
    name="history",
    description="Return evolution history as a list of (generation, avg_fitness)",
)  # type: ignore[misc]
async def history() -> dict[str, list[tuple[int, float]]]:
    """Return the recorded fitness history."""
    evolver = _get_evolver()
    return {"history": evolver.history}


@Tool(name="reset", description="Reset evolution to generation zero")  # type: ignore[misc]
async def reset() -> str:
    """Reset the evolver to its initial state."""
    evolver = _get_evolver()
    evolver.reset()
    return "evolver reset"


class EvolverAgent(Agent):  # type: ignore[misc]
    """Tiny agent exposing the meta-evolver tools."""

    name = "aiga_evolver"
    tools = [evolve, best_alpha, checkpoint, reset, history]

    async def policy(self, obs: object, ctx: object) -> dict[str, float | str]:
        gens = int(obs.get("gens", 1)) if isinstance(obs, dict) else 1
        await evolve(gens)
        return cast(dict[str, float | str], await best_alpha())


AGENT_PORT = int(os.getenv("AGENTS_RUNTIME_PORT", "5001"))


def main() -> None:
    """Run the Evolver agent via the OpenAI Agents runtime."""
    _get_evolver()
    runtime = AgentRuntime(api_key=None, port=AGENT_PORT)
    agent = EvolverAgent()
    runtime.register(agent)
    print("Registered EvolverAgent with runtime", flush=True)

    if ADK_AVAILABLE:
        auto_register([agent])
        maybe_launch()
        print("EvolverAgent exposed via ADK gateway", flush=True)

    runtime.run()


if __name__ == "__main__":  # pragma: no cover
    main()
