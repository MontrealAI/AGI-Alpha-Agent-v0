# SPDX-License-Identifier: Apache-2.0
"""Agent performing lightweight safety checks.

The safety agent inspects generated code for obvious issues before data is
persisted by the :class:`MemoryAgent`. Only minimal pattern checks are
implemented for demonstration purposes.
"""

from __future__ import annotations

from alpha_factory_v1.core.agents.base_agent import BaseAgent
from alpha_factory_v1.common.utils import messaging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.core.utils.tracing import span
from google.protobuf import json_format
from alpha_factory_v1.core.utils.opa_policy import violates_insider_policy, violates_exfil_policy


class SafetyGuardianAgent(BaseAgent):
    """Validate generated code before persistence."""

    def __init__(
        self,
        bus: messaging.A2ABus,
        ledger: "Ledger",
        *,
        backend: str = "gpt-4o",
        island: str = "default",
    ) -> None:
        super().__init__("safety", bus, ledger, backend=backend, island=island)

    async def run_cycle(self) -> None:
        """No-op periodic check."""
        with span("safety.run_cycle"):
            return None

    async def handle(self, env: messaging.Envelope) -> None:
        """Validate payload before persistence."""
        with span("safety.handle"):
            payload = env.payload
            if hasattr(payload, "fields"):
                payload_dict = json_format.MessageToDict(payload, preserving_proto_field_name=True)
            elif isinstance(payload, dict):
                payload_dict = payload
            else:
                payload_dict = {}
            code = str(payload_dict.get("code", ""))
            text_parts = [str(v) for v in payload_dict.values() if isinstance(v, str)]
            text = " ".join(text_parts)
            status = "ok"
            if "import os" in code or violates_insider_policy(text) or violates_exfil_policy(text):
                status = "blocked"
            payload_dict["status"] = status
            await self.emit("memory", payload_dict)
