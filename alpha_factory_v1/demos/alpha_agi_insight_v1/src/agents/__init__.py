# SPDX-License-Identifier: Apache-2.0
"""Collection of minimal agents used in the Insight scenario.

The package exposes small, single‑responsibility agents. Each agent
subclasses :class:`~alpha_factory_v1.core.agents.base_agent.BaseAgent` and cooperates via the
:class:`~alpha_factory_v1.common.utils.messaging.A2ABus`.
"""

from .adk_adapter import ADKAdapter
from .mcp_adapter import MCPAdapter

# Importing BaseAgent from the core package during module import triggers a
# circular dependency because ``base_agent`` itself loads this package.  The
# individual agents directly import :class:`~alpha_factory_v1.core.agents.base_agent.BaseAgent`,
# so re-exporting here is unnecessary.  Avoid the early import to prevent a
# partially initialised module during start-up.
from .research_agent import ResearchAgent
from .adk_summariser_agent import ADKSummariserAgent
from .chaos_agent import ChaosAgent

# Re-export the base_agent module for convenience in tests
from alpha_factory_v1.core.agents import base_agent

__all__ = [
    "ADKAdapter",
    "MCPAdapter",
    "ResearchAgent",
    "ADKSummariserAgent",
    "ChaosAgent",
    "base_agent",
]
