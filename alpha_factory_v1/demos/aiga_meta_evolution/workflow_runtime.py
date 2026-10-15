# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

End-to-end Alpha Factory workflow demo.

This script chains the ``alpha_discovery`` and ``alpha_conversion``
stubs via the OpenAI Agents runtime. It is compatible with either the
``openai_agents`` package or the ``agents`` backport. The demo works
offline when ``OPENAI_API_KEY`` is unset and can publish the agent over
the Google ADK gateway when the ``ALPHA_FACTORY_ENABLE_ADK`` environment
variable is set.
"""
from __future__ import annotations

try:
    from openai_agents import Agent, AgentRuntime, OpenAIAgent as _OpenAIAgent, Tool
except ImportError:
    try:  # pragma: no cover - fallback for legacy package
        from agents import Agent, AgentRuntime, OpenAIAgent as _OpenAIAgent, Tool
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "openai-agents or agents package is required. Install with `pip install openai-agents`"
        ) from exc

from .utils import build_llm
import os

from .alpha_opportunity_stub import identify_alpha
from .alpha_conversion_stub import convert_alpha

OpenAIAgent = _OpenAIAgent

try:
    from alpha_factory_v1.backend import adk_bridge
    from alpha_factory_v1.backend.adk_bridge import auto_register, maybe_launch

    ADK_AVAILABLE = True
except Exception:  # pragma: no cover - optional
    ADK_AVAILABLE = False

# ---------------------------------------------------------------------------
# LLM setup -----------------------------------------------------------------
# ---------------------------------------------------------------------------
LLM = build_llm()


@Tool(name="discover_alpha", description="List market opportunities in a domain")
async def discover_alpha(domain: str = "finance") -> str:
    """Return LLM-discovered opportunities for ``domain``."""
    return await identify_alpha(domain)


@Tool(name="convert_alpha", description="Turn an opportunity into an execution plan")
async def convert_alpha_tool(alpha: str) -> dict:
    """Convert an opportunity string into a JSON plan."""
    return convert_alpha(alpha)


class WorkflowAgent(Agent):
    """Simple agent chaining discovery and conversion."""

    name = "alpha_workflow"
    tools = [discover_alpha, convert_alpha_tool]

    async def policy(self, obs, ctx):  # type: ignore[override]
        domain = obs.get("domain", "finance") if isinstance(obs, dict) else "finance"
        alphas = await discover_alpha(domain)
        first = alphas.split("\n")[0].strip()
        plan = await convert_alpha_tool(first)
        return {"alpha": first, "plan": plan}


AGENT_PORT = int(os.getenv("AGENTS_RUNTIME_PORT", "5001"))


def main() -> None:
    """Run the workflow agent with a local runtime."""
    runtime = AgentRuntime(llm=LLM, port=AGENT_PORT)
    agent = WorkflowAgent()
    runtime.register(agent)
    print("Registered WorkflowAgent with runtime")

    if ADK_AVAILABLE and adk_bridge.adk_enabled():
        auto_register([agent])
        maybe_launch()
        print("WorkflowAgent exposed via ADK gateway")

    runtime.run()


if __name__ == "__main__":  # pragma: no cover
    main()
