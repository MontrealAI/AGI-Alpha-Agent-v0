# SPDX-License-Identifier: Apache-2.0
"""Reviewed pure adapter for already retained model proposals; no inference here."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .transformation import DiscoveryRequest, SelectionProgram, _checked_source_bytes


class FrozenProgramsOperator:
    """Expose only the closed native selector language to the discovery engine."""

    def __init__(self, candidates: list[dict[str, Any]], proposal_digest: str) -> None:
        self.identity = "local-model-proposals"
        source_path = Path(__file__)
        content = _checked_source_bytes(
            source_path,
            source_path.read_bytes(),
            source_loader=globals().get("__loader__"),
        )
        self.source_digest = hashlib.sha256(content).hexdigest()
        self.programs = [SelectionProgram.model_validate(item["program"]).model_dump() for item in candidates]
        self.proposal_digest = proposal_digest

    def propose(self, request: DiscoveryRequest) -> list[SelectionProgram]:
        """Return typed programs, never external code, outcomes or authority."""
        return [SelectionProgram.model_validate(item) for item in self.programs]
