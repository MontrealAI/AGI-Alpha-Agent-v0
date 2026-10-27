# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from pydantic import Field, model_validator

from alpha_factory_v1.core.runtime.successor.protocol import StrictModel, canonical, digest


class State(StrictModel):
    state_id: str = Field(min_length=1, max_length=128)
    secret_value: int = Field(ge=0, le=255, strict=True)
    observer_view: str = Field(min_length=1, max_length=128)
    outputs: list[int] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def bits(self) -> State:
        if any(type(bit) is not int or bit not in (0, 1) for bit in self.outputs):
            raise ValueError("outputs must be exact integer bits")
        return self


class Packet(StrictModel):
    schema_name: Literal["reserve-output-boundary/v1"] = "reserve-output-boundary/v1"
    mode: Literal["public-synthetic-only"] = "public-synthetic-only"
    opportunity_id: str = Field(min_length=1, max_length=128)
    mission_id: str = Field(min_length=1, max_length=128)
    worker_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    minimum_alternatives: int = Field(ge=2, le=256, strict=True)
    required_state_ids: list[str] = Field(min_length=2, max_length=4096)
    states: list[State] = Field(min_length=2, max_length=4096)

    @model_validator(mode="after")
    def complete_declared_table(self) -> Packet:
        ids = [state.state_id for state in self.states]
        if len(set(ids)) != len(ids) or len(set(self.required_state_ids)) != len(self.required_state_ids):
            raise ValueError("duplicate declared state")
        if set(ids) != set(self.required_state_ids):
            raise ValueError("an explicitly required hypothetical state is missing or substituted")
        if len({len(state.outputs) for state in self.states}) != 1:
            raise ValueError("all possible states require the complete fixed batch")
        return self


def audit(packet: Packet) -> dict[str, Any]:
    before: dict[str, set[int]] = defaultdict(set)
    after: dict[tuple[str, tuple[int, ...]], set[int]] = defaultdict(set)
    witnesses: dict[tuple[str, tuple[int, ...]], list[str]] = defaultdict(list)
    for state in packet.states:
        before[state.observer_view].add(state.secret_value)
        key = state.observer_view, tuple(state.outputs)
        after[key].add(state.secret_value)
        witnesses[key].append(state.state_id)
    fibers: list[dict[str, Any]] = [
        {
            "observer_view": view,
            "outputs": list(outputs),
            "prior_alternatives": len(before[view]),
            "remaining_alternatives": len(values),
            "state_ids": witnesses[(view, outputs)],
        }
        for (view, outputs), values in sorted(after.items())
    ]
    eligible = all(fiber["remaining_alternatives"] >= packet.minimum_alternatives for fiber in fibers)
    return {
        "schema": "reserve-output-boundary-assessment/v1",
        "mode": packet.mode,
        "packet_digest": digest("reserve-output-boundary-packet", packet.model_dump(mode="json")),
        "opportunity_id": packet.opportunity_id,
        "mission_id": packet.mission_id,
        "worker_sha256": packet.worker_sha256,
        "decision": "eligible-for-separate-authorization" if eligible else "refuse-entire-batch",
        "minimum_alternatives": min(fiber["remaining_alternatives"] for fiber in fibers),
        "nonconstant": any(
            len({tuple(state.outputs) for state in packet.states if state.observer_view == view}) > 1 for view in before
        ),
        "fibers": fibers,
        "denial_basis": "All declared public hypotheses, never the actual private state or observed answer.",
        "authority": "none",
        "limitation": "Finite declared hypotheses only; not differential privacy, zero information, or production assurance.",
    }


def verify_assessment(packet: Packet, assessment: dict[str, Any]) -> None:
    if canonical(audit(packet)) != canonical(assessment):
        raise ValueError("assessment is stale, modified, incomplete or belongs to another mission/source")
