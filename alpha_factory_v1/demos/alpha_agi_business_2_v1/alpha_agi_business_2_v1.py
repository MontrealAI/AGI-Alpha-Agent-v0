#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# NOTE: This demo is a research prototype. References to "AGI" or "superintelligence" describe aspirational goals and do not indicate the presence of real general intelligence. Use at your own risk. Nothing herein constitutes financial advice.
"""Legacy service adapter for the finite supplied-input Business 2 planner.

Use ``planning --input`` for offline execution; this module preserves service topics.
Commentary requires explicit opt-in and a real compatible provider SDK.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

from alpha_factory_v1.backend import orchestrator
from alpha_factory_v1.backend.agents import (
    AgentMetadata,
    register_agent,
)

from alpha_factory_v1.backend.agents.base import AgentBase
from .planning import load_report


def _report() -> dict[str, Any]:
    path = os.getenv("BUSINESS2_INPUT")
    if not path:
        raise ValueError("Set BUSINESS2_INPUT to a validated scenario JSON file; no fixture fallback")
    return load_report(Path(path))


class PlanningAgent(AgentBase):
    """Publish an exact bounded portfolio from the configured supplied input."""

    NAME = "planning"
    CAPABILITIES = ["plan"]
    __slots__ = ()

    async def step(self) -> None:
        """Publish a computed plan and its input commitment on the existing topic."""
        report = _report()
        await self.publish(
            "alpha.plan",
            {"plan": report["plan"], "inputDigest": report["inputDigest"], "provenance": report["provenance"]},
        )


class ResearchAgent(AgentBase):
    """Review supplied observations without fetching or inventing research."""

    NAME = "research"
    CAPABILITIES = ["research"]
    CYCLE_SECONDS = 90
    __slots__ = ()

    async def step(self) -> None:
        """Publish computed evidence under the existing summary envelope."""
        report = _report()
        await self.publish(
            "alpha.research",
            {
                "summary": report["research"],
                "inputDigest": report["inputDigest"],
                "provenance": report["provenance"],
                "scope": report["scope"],
            },
        )


class LLMCommentAgent(AgentBase):
    """Optional LLM-powered commentary agent."""

    NAME = "llm_comment"
    CAPABILITIES = ["insight"]
    REQUIRES_API_KEY = False
    __slots__ = ()

    async def step(self) -> None:
        """Request commentary only when explicitly enabled; never fabricate fallback text."""
        if os.getenv("BUSINESS2_COMMENTARY", "0") != "1":
            return
        import openai_agents

        if getattr(openai_agents, "__alpha_factory_stub__", False) or "Minimal stub" in (openai_agents.__doc__ or ""):
            raise RuntimeError("The bundled openai_agents compatibility stub cannot provide model commentary")
        report = _report()
        agent = openai_agents.OpenAIAgent(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=None if os.getenv("OPENAI_API_KEY") else "http://ollama:11434/v1",
        )
        insight = await agent(
            "Comment only on these supplied assumptions; do not claim live research: "
            + json.dumps(report, ensure_ascii=False)
        )
        if not isinstance(insight, str) or not insight.strip() or len(insight) > 8000:
            raise ValueError("Provider returned invalid or oversized commentary")
        await self.publish(
            "alpha.insight", {"insight": insight, "mode": "provider_commentary", "inputDigest": report["inputDigest"]}
        )


def register_demo_agents() -> None:
    """Register built-in demo agents with the framework."""

    register_agent(
        AgentMetadata(
            name=PlanningAgent.NAME,
            cls=PlanningAgent,
            version="1.0.0",
            capabilities=PlanningAgent.CAPABILITIES,
        )
    )

    register_agent(
        AgentMetadata(
            name=LLMCommentAgent.NAME,
            cls=LLMCommentAgent,
            version="1.0.0",
            capabilities=LLMCommentAgent.CAPABILITIES,
            requires_api_key=LLMCommentAgent.REQUIRES_API_KEY,
        )
    )

    register_agent(
        AgentMetadata(
            name=ResearchAgent.NAME,
            cls=ResearchAgent,
            version="1.0.0",
            capabilities=ResearchAgent.CAPABILITIES,
        )
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Return parsed CLI arguments."""

    parser = argparse.ArgumentParser(description="Run the α‑AGI Business demo")
    parser.add_argument(
        "--loglevel",
        default=os.getenv("LOGLEVEL", "INFO"),
        help="Logging verbosity (default: INFO)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Launch the orchestrator with demo agents registered."""

    args = _parse_args(argv)
    logging.basicConfig(
        level=args.loglevel.upper(),
        format="%(asctime)s %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    _report()  # Fail before starting a service if input is missing or invalid.
    register_demo_agents()

    try:
        orchestrator.Orchestrator().run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
