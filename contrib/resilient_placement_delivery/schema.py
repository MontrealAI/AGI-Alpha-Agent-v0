# SPDX-License-Identifier: Apache-2.0
"""Strict named intake, retaining the unchanged runtime's finite problem scope."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from alpha_factory_v1.core.runtime.successor.flywheel_experiments import PlacementProblem
from alpha_factory_v1.core.runtime.successor.protocol import canonical

Label = Annotated[str, Field(min_length=1, max_length=80)]
BriefID = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")]
Amount = Annotated[int, Field(strict=True, ge=1, le=1000)]
Objective = Annotated[int, Field(strict=True, ge=0, le=1_000_000)]


class IntakeModel(BaseModel):
    """Reject unknown fields and implicit conversion of customer inputs."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Host(IntakeModel):
    id: Label
    capacity: Amount
    failure_domain: Label


class Service(IntakeModel):
    id: Label
    demand: Amount
    costs: dict[str, Objective]


class PlacementBrief(IntakeModel):
    """One exact finite engagement, without infrastructure or purchase authority."""

    schema_name: Literal["resilient-placement-brief/v1"] = "resilient-placement-brief/v1"
    brief_id: BriefID
    beneficiary: Annotated[str, Field(min_length=1, max_length=500)]
    authorized_inputs: Literal[True]
    rights_basis: Annotated[str, Field(min_length=1, max_length=2000)]
    inventory_basis: Annotated[str, Field(min_length=1, max_length=2000)]
    cost_unit: Label
    price_micro_usd: Annotated[int, Field(strict=True, ge=0, le=10**12)] = 250_000_000
    hosts: Annotated[list[Host], Field(min_length=2, max_length=10)]
    services: Annotated[list[Service], Field(min_length=1, max_length=16)]
    node_budget: Annotated[int, Field(strict=True, ge=1, le=1_000_000)] = 250_000

    @field_validator("authorized_inputs", mode="before")
    @classmethod
    def exact_authorization(cls, value: Any) -> Any:
        """Require an explicit true boolean, not a numeric stand-in."""
        if value is not True:
            raise ValueError("input authority requires an explicit true boolean")
        return value

    @model_validator(mode="after")
    def scoped(self) -> PlacementBrief:
        """Keep names unambiguous and independent verification affordable."""
        names = [host.id for host in self.hosts]
        service_names = [service.id for service in self.services]
        if len(set(names)) != len(names) or len(set(service_names)) != len(service_names):
            raise ValueError("host and service identifiers must be unique within their type")
        for text in [
            self.beneficiary,
            self.rights_basis,
            self.inventory_basis,
            self.cost_unit,
            *names,
            *service_names,
            *(host.failure_domain for host in self.hosts),
        ]:
            if text != text.strip() or not text.isprintable():
                raise ValueError("labels and text must be trimmed, printable and nonempty")
        if any(set(service.costs) != set(names) for service in self.services):
            raise ValueError("each service requires exactly one objective cost for every named host")
        pairs = len(names) * (len(names) - 1) // 2
        if pairs ** len(self.services) > 100_000:
            raise ValueError("intake exceeds the independent exhaustive-check budget")
        if len(canonical(self.model_dump())) > 32_768:
            raise ValueError("named intake exceeds its 32768-byte frame")
        self.problem
        return self

    @property
    def problem(self) -> PlacementProblem:
        """Project names onto the existing unchanged numeric problem schema."""
        return PlacementProblem(
            capacities=[host.capacity for host in self.hosts],
            failure_domains=[host.failure_domain for host in self.hosts],
            demands=[service.demand for service in self.services],
            costs=[[service.costs[host.id] for host in self.hosts] for service in self.services],
            node_budget=self.node_budget,
        )


def parse_brief(raw: dict[str, Any]) -> PlacementBrief:
    """Validate a bounded JSON frame and detach intake from caller mutation."""
    encoded = canonical(raw)
    if len(encoded) > 32_768:
        raise ValueError("named intake exceeds its 32768-byte frame")
    return PlacementBrief.model_validate_json(encoded, strict=True)
