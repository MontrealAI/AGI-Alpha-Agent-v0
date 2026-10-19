# SPDX-License-Identifier: Apache-2.0
"""Reviewed pure adapter for already retained model proposals; no inference here."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .transformation import DiscoveryRequest, SelectionProgram


class FrozenProgramsOperator:
    """Expose only the closed native selector language to the discovery engine."""

    def __init__(self, candidates: list[dict[str, Any]], proposal_digest: str) -> None:
        self.identity = "local-model-proposals"
        self.source_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.programs = [SelectionProgram.model_validate(item["program"]).model_dump() for item in candidates]
        self.proposal_digest = proposal_digest

    def propose(self, request: DiscoveryRequest) -> list[SelectionProgram]:
        """Return typed programs, never external code, outcomes or authority."""
        return [SelectionProgram.model_validate(item) for item in self.programs]
