# SPDX-License-Identifier: Apache-2.0
"""Base class shared by all Insight demo agents.

The class wires each agent into the :class:`~alpha_factory_v1.common.utils.messaging.A2ABus` and
provides helper methods for sending and receiving envelopes. Subclasses
implement :meth:`handle` to process messages and :meth:`run_cycle` for
periodic behaviour.
"""
from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING
from google.protobuf import struct_pb2

try:
    from alpha_factory_v1.backend.utils.llm_provider import LLMProvider
except Exception:  # pragma: no cover - optional
    LLMProvider = None

from ...common.utils import messaging

ADKAdapter = None
MCPAdapter = None

if TYPE_CHECKING:  # pragma: no cover - type hint only
    from ...common.utils.logging import Ledger

try:
    from openai.agents import AgentContext as _AgentContext

    AgentContext: type | None = _AgentContext
except Exception:  # pragma: no cover - optional
    AgentContext = None


class BaseAgent:
    """Abstract agent type used by specialised agents."""

    name: str

    def __init__(
        self,
        name: str,
        bus: messaging.A2ABus,
        ledger: "Ledger",
        *,
        backend: str = "gpt-4o",
        island: str = "default",
    ) -> None:
        self.island = island
        self.backend = backend
        self.name = f"{name}_{island}" if island != "default" else name
        self.bus = bus
        self.ledger = ledger
        self.llm = None
        if backend.startswith("gpt") and AgentContext is not None:
            try:
                self.oai_ctx = AgentContext(
                    model=bus.settings.model_name,
                    temperature=bus.settings.temperature,
                    context_window=bus.settings.context_window,
                )
            except TypeError:
                try:
                    self.oai_ctx = AgentContext(
                        model=bus.settings.model_name,
                        temperature=bus.settings.temperature,
                    )
                except Exception:
                    self.oai_ctx = AgentContext()
        else:
            self.oai_ctx = None
            if LLMProvider is not None:
                try:
                    self.llm = LLMProvider(
                        temperature=bus.settings.temperature,
                        max_tokens=bus.settings.context_window,
                    )
                except Exception:
                    self.llm = LLMProvider() if LLMProvider is not None else None
        global ADKAdapter, MCPAdapter
        if ADKAdapter is None:
            try:  # pragma: no cover - optional dependency
                from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents.adk_adapter import (
                    ADKAdapter as _ADKAdapter,
                )

                ADKAdapter = _ADKAdapter
            except Exception:
                ADKAdapter = None
        if MCPAdapter is None:
            try:  # pragma: no cover - optional dependency
                from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents.mcp_adapter import (
                    MCPAdapter as _MCPAdapter,
                )

                MCPAdapter = _MCPAdapter
            except Exception:
                MCPAdapter = None
        self.adk = ADKAdapter() if ADKAdapter and ADKAdapter.is_available() else None
        self.mcp = MCPAdapter() if MCPAdapter and MCPAdapter.is_available() else None
        self._handler = self._on_envelope
        self.bus.subscribe(self.name, self._handler)

    async def _on_envelope(self, env: messaging.Envelope) -> None:
        await self.handle(env)

    async def emit(self, recipient: str, payload: Any) -> None:
        env = messaging.Envelope(
            sender=self.name,
            recipient=recipient,
            payload=struct_pb2.Struct(),
            ts=time.time(),
        )
        if isinstance(payload, dict):
            env.payload.update(payload)
        self.ledger.log(env)
        self.bus.publish(recipient, env)

    def close(self) -> None:
        """Unsubscribe the agent from the bus."""
        self.bus.unsubscribe(self.name, self._handler)

    async def handle(self, env: messaging.Envelope) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def run_cycle(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError
