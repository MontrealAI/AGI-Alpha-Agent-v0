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

    OpenAIAgent = getattr(_oa, "OpenAIAgent", getattr(_oa, "Agent", object))  # type: ignore[assignment]
    Agent = getattr(_oa, "Agent", OpenAIAgent)  # type: ignore[assignment]
    Tool = getattr(_oa, "Tool", lambda *a, **k: (lambda f: f))  # type: ignore[assignment]
except Exception as exc:  # pragma: no cover - fallback stub

    class Agent:  # type: ignore[misc]  # pragma: no cover - lightweight fallback
        name = "agent"
        tools: list[object] = []

    def Tool(*_a, **_k):  # type: ignore[misc]
        def dec(func):
            return func

        return dec

    class OpenAIAgent:  # type: ignore[misc]
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def __call__(self, *_: object, **__: object) -> str:
            return "ok"

    AgentRuntime = None
else:
    AgentRuntime = getattr(_oa, "AgentRuntime", None)


try:  # ensure Tool is a callable decorator even with unusual exports
    Tool(lambda x: x)
except Exception:
    Tool = lambda *a, **k: (lambda f: f)  # type: ignore[misc,assignment]

if AgentRuntime is None or not hasattr(AgentRuntime, "run"):

    class AgentRuntime:  # type: ignore[misc]
        def __init__(self, *_: object, **__: object) -> None:
            self._agent: Agent | None = None

        def register(self, agent: Agent) -> None:
            self._agent = agent

        def run(self) -> None:
            import asyncio

            async def _idle() -> None:
                while True:
                    await asyncio.sleep(3600)

            asyncio.run(_idle())


def _noop_register(_agents: list[Agent]) -> None:  # pragma: no cover - optional
    return None


def _noop_launch() -> None:  # pragma: no cover - optional
    return None


ADK_AVAILABLE = False
auto_register = _noop_register
maybe_launch = _noop_launch

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
    runtime = AgentRuntime(api_key=None, port=AGENT_PORT)
    agent = EvolverAgent()
    runtime.register(agent)
    print("Registered EvolverAgent with runtime", flush=True)

    if ADK_AVAILABLE:
        auto_register([agent])
        maybe_launch()
        print("EvolverAgent exposed via ADK gateway", flush=True)
    else:
        print("EvolverAgent exposed via ADK gateway (ADK disabled)", flush=True)

    runtime.run()


if __name__ == "__main__":  # pragma: no cover
    main()
