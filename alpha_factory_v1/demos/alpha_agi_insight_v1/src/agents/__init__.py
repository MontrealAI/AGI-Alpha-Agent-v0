# SPDX-License-Identifier: Apache-2.0
"""Collection of minimal agents used in the Insight scenario.

The package exposes small, single‑responsibility agents. Each agent
subclasses :class:`~alpha_factory_v1.core.agents.base_agent.BaseAgent` and cooperates via the
:class:`~alpha_factory_v1.common.utils.messaging.A2ABus`.
"""

from .adk_adapter import ADKAdapter
from .mcp_adapter import MCPAdapter
from alpha_factory_v1.core.agents import base_agent as base_agent

BaseAgent = base_agent.BaseAgent
from .research_agent import ResearchAgent
from .adk_summariser_agent import ADKSummariserAgent
from .chaos_agent import ChaosAgent

__all__ = [
    "ADKAdapter",
    "MCPAdapter",
    "ResearchAgent",
    "ADKSummariserAgent",
    "ChaosAgent",
]
