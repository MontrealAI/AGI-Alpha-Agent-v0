# SPDX-License-Identifier: Apache-2.0
"""Small exact-byte bounded work specification shared by native/Fleet adapters."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import Field
from .models import Mission, StrictModel

MAX_BYTES = 512_000
SPEC_SCHEMA = "agialpha.bounded-work-spec.v1"


class WorkSpec(StrictModel):
    """Precommission work, excluding job assignment and imported authority."""

    schema_id: Literal["agialpha.bounded-work-spec.v1"] = Field(alias="schema")
    market: Literal["agijobsv0-jobregistry-v2"]
    executor: Literal["alpha-native-v1", "fleet-linux-v1"]
    mission: Mission


def read_spec(raw: bytes) -> tuple[WorkSpec, str]:
    """Reject ambiguous/nonfinite/oversized JSON; hash exact bytes, not a rewrite."""
    if len(raw) > MAX_BYTES:
        raise ValueError("Work specification exceeds its bounded size")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate work specification key")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError("Nonfinite work specification value")

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    return WorkSpec.model_validate(value), "0x" + hashlib.sha256(raw).hexdigest()
