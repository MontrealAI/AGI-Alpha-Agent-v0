# SPDX-License-Identifier: Apache-2.0
"""Bounded enterprise mandates; inputs grant no filesystem, network or spending authority."""
from __future__ import annotations

from pydantic import Field, model_validator

from alpha_factory_v1.core.runtime.models import Operation, Source, StrictModel


class Project(StrictModel):
    """One indivisible project with supplied value, resource needs and evidence."""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    title: str = Field(min_length=3, max_length=120)
    cost: int = Field(ge=1, le=1000000)
    value: int = Field(ge=1, le=1000000000)
    risk: int = Field(ge=0, le=10000)
    due: int = Field(ge=1, le=1000000)
    operations: list[Operation] = Field(min_length=1, max_length=6)
    evidence: Source


class Mandate(StrictModel):
    """Explicit assumptions for a portfolio, resource schedule and evidence brief."""

    title: str = Field(min_length=3, max_length=120)
    goal: str = Field(min_length=10, max_length=1500)
    provenance: str = Field(min_length=10, max_length=1000)
    budget: int = Field(ge=1, le=10000000)
    max_risk: int = Field(ge=0, le=100000)
    cost_unit: str = Field(min_length=1, max_length=40)
    value_unit: str = Field(min_length=1, max_length=60)
    time_unit: str = Field(default="hours", min_length=1, max_length=30)
    projects: list[Project] = Field(min_length=2, max_length=10)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def distinct_inputs(self) -> Mandate:
        """Reject ambiguous projects/evidence and a mandate with no feasible work."""
        for ids in ([p.id for p in self.projects], [p.evidence.id for p in self.projects]):
            if len(ids) != len(set(ids)):
                raise ValueError("Project and evidence IDs must each be unique")
        if not any(p.cost <= self.budget and p.risk <= self.max_risk for p in self.projects):
            raise ValueError("No project fits both budget and risk limits; revise the mandate")
        if any(not p.evidence.text.strip() for p in self.projects):
            raise ValueError("Evidence text cannot be blank")
        if any(len(p.evidence.text) > 6000 for p in self.projects):
            raise ValueError("Each evidence source is limited to 6,000 characters")
        return self
