# SPDX-License-Identifier: Apache-2.0
"""Simple in-memory storage for agent artefacts.

The ``MemoryAgent`` collects payloads from other agents and exposes them via
its :pyattr:`records` attribute. The :meth:`run_cycle` hook reports the number
of stored items back to the orchestrator.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

from google.protobuf import json_format
from google.protobuf.message import Message

from alpha_factory_v1.common.utils import logging as insight_logging
from alpha_factory_v1.common.utils import messaging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.core.agents.base_agent import BaseAgent
from alpha_factory_v1.core.utils.tracing import span

log = insight_logging.logging.getLogger(__name__)


JSONValue = dict[str, object] | list[object] | str | int | float | bool | None


def _coerce_payload(payload: object) -> JSONValue:
    if isinstance(payload, Message):
        return cast(JSONValue, json_format.MessageToDict(payload, preserving_proto_field_name=True))
    return cast(JSONValue, payload)


class MemoryAgent(BaseAgent):
    """Persist artefacts produced by other agents."""

    def __init__(
        self,
        bus: messaging.A2ABus,
        ledger: "Ledger",
        store_path: str | None = None,
        *,
        backend: str = "gpt-4o",
        island: str = "default",
        memory_limit: int | None = None,
    ) -> None:
        super().__init__("memory", bus, ledger, backend=backend, island=island)
        if memory_limit is None:
            raw = os.getenv("AGI_INSIGHT_MEMORY_LIMIT")
            if raw:
                try:
                    memory_limit = int(raw)
                except ValueError:
                    log.warning("invalid AGI_INSIGHT_MEMORY_LIMIT=%s", raw)
                    memory_limit = None
        self._limit = memory_limit
        self.records: list[JSONValue] = []
        self._store = Path(store_path) if store_path else None
        if self._store and self._store.exists():
            for line in self._store.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    self.records.append(json.loads(line))
                except Exception as exc:  # noqa: BLE001 - ignore bad records
                    log.warning("invalid record: %s", exc)
        if self._limit is not None and len(self.records) > self._limit:
            self.records = self.records[-self._limit :]
            if self._store:
                with self._store.open("w", encoding="utf-8") as fh:
                    for rec in self.records:
                        fh.write(json.dumps(rec) + "\n")

    async def run_cycle(self) -> None:
        """Periodically report memory size."""
        with span("memory.run_cycle"):
            await self.emit("orch", {"stored": len(self.records)})

    async def handle(self, env: messaging.Envelope) -> None:
        """Store payload for later retrieval."""
        with span("memory.handle"):
            payload = _coerce_payload(env.payload)
            self.records.append(payload)
            if self._limit is not None and len(self.records) > self._limit:
                excess = len(self.records) - self._limit
                self.records = self.records[excess:]
                if self._store:
                    with self._store.open("w", encoding="utf-8") as fh:
                        for rec in self.records:
                            fh.write(json.dumps(rec) + "\n")
            else:
                if self._store:
                    with self._store.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(payload) + "\n")
