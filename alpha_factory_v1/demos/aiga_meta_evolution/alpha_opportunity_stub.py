# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

Alpha opportunity discovery agent stub.

This lightweight example exposes a single tool via the OpenAI Agents SDK
(compatible with either the ``openai_agents`` package or the ``agents``
backport) that requests the LLM to list live market inefficiencies. It
falls back to a local model when no ``OPENAI_API_KEY`` is configured.
"""
from __future__ import annotations

try:
    from openai_agents import Agent, AgentRuntime, OpenAIAgent as _OpenAIAgent, Tool
except ImportError:
    try:  # pragma: no cover - fallback for legacy package
        from agents import Agent, AgentRuntime, OpenAIAgent as _OpenAIAgent, Tool
    except Exception as exc:  # pragma: no cover - optional dependency
        raise SystemExit(
            "openai-agents or agents package is required. Install with `pip install openai-agents`"
        ) from exc

from .utils import build_llm
import os

OpenAIAgent = _OpenAIAgent

LLM = build_llm()


@Tool(name="identify_alpha", description="Suggest current inefficiencies in a domain")
async def identify_alpha(domain: str = "finance") -> str:
    """List promising opportunities in ``domain``."""
    if os.getenv("AIGA_ALLOW_DISCOVERY_PROVIDER") != "1":
        raise RuntimeError("Discovery inference requires explicit AIGA_ALLOW_DISCOVERY_PROVIDER=1 opt-in")
    prompt = (
        f"List three emerging opportunities or inefficiencies in the {domain} domain "
        "that a small team could exploit for outsized value."
    )
    return await LLM(prompt)


class AlphaDiscoveryAgent(Agent):
    """Minimal agent exposing the ``identify_alpha`` tool."""

    name = "alpha_discovery"
    tools = [identify_alpha]

    async def policy(self, obs, ctx):  # type: ignore[override]
        domain = obs.get("domain", "finance") if isinstance(obs, dict) else "finance"
        return await identify_alpha(domain)


def main(argv: list[str] | None = None) -> None:
    """Launch the agent runtime or run a single query."""
    import argparse
    import asyncio

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="finance", help="domain to scan")
    ap.add_argument(
        "--once",
        action="store_true",
        help="run a single identify_alpha call and exit",
    )
    args = ap.parse_args(argv)

    if args.once:
        result = asyncio.run(identify_alpha(args.domain))
        print(result)
        return

    agent_port = int(os.getenv("AGENTS_RUNTIME_PORT", "5001"))
    runtime = AgentRuntime(api_key=None, port=agent_port)
    agent = AlphaDiscoveryAgent()
    runtime.register(agent)
    print("Registered AlphaDiscoveryAgent with runtime")
    runtime.run()


if __name__ == "__main__":  # pragma: no cover
    main()
