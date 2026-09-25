# SPDX-License-Identifier: Apache-2.0
"""Strict, bounded inputs shared by the CLI, API and mission engine."""

from __future__ import annotations

import math
from typing import Annotated, Literal, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Reject unknown configuration and implicit type coercions."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Source(StrictModel):
    """Operator-supplied evidence; URLs are citations, never fetched implicitly."""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=20000)
    url: str = Field(default="", max_length=2048)


class Research(StrictModel):
    """Research over a fixed, attributable corpus."""

    kind: Literal["research"] = "research"
    sources: list[Source] = Field(min_length=1, max_length=20)


class Opportunity(StrictModel):
    """A resource allocation item, in operator-defined integer units."""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    cost: int = Field(ge=1, le=10**12)
    value: int = Field(ge=0, le=10**12)
    risk: int = Field(default=0, ge=0, le=10000)


class Allocation(StrictModel):
    """Bounded binary allocation; values are assumptions, not realized revenue."""

    kind: Literal["allocation"] = "allocation"
    items: list[Opportunity] = Field(min_length=1, max_length=18)
    budget: int = Field(ge=1, le=10**13)
    max_risk: int = Field(default=180000, ge=0, le=180000)
    unit: str = Field(default="planning units", min_length=1, max_length=60)


class Operation(StrictModel):
    """One non-preemptive manufacturing operation."""

    machine: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    duration: int = Field(ge=1, le=100000)


class Job(StrictModel):
    """Ordered operations with an optional due time."""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    operations: list[Operation] = Field(min_length=1, max_length=20)
    due: int = Field(default=10000000, ge=1, le=10000000)


class Schedule(StrictModel):
    """A job-shop scenario whose output can be checked independently."""

    kind: Literal["schedule"] = "schedule"
    jobs: list[Job] = Field(min_length=1, max_length=30)
    unit: str = Field(default="minutes", min_length=1, max_length=30)


class Forecast(StrictModel):
    """Observed series with an untouched temporal holdout."""

    kind: Literal["forecast"] = "forecast"
    observations: list[float] = Field(min_length=12, max_length=5000)
    horizon: int = Field(default=3, ge=1, le=100)
    holdout: int = Field(default=4, ge=2, le=1000)
    season: int = Field(default=1, ge=1, le=365)
    unit: str = Field(default="observed units", min_length=1, max_length=60)

    @model_validator(mode="after")
    def validate_series(self) -> Forecast:
        """Require enough training data and finite measurements."""
        if self.holdout > len(self.observations) // 3:
            raise ValueError("holdout must be at most one third of the observations")
        if self.season > (len(self.observations) - self.holdout) // 2:
            raise ValueError("training data must include two full seasons")
        if not all(math.isfinite(x) and abs(x) <= 10**15 for x in self.observations):
            raise ValueError("observations must be finite and bounded by 1e15")
        return self


class CodeCase(StrictModel):
    """Host-owned benchmark input and expected output."""

    args: list[Any] = Field(max_length=20)
    expected: Any


class Coding(StrictModel):
    """A bounded solve-function task with cases withheld from the model."""

    kind: Literal["code"] = "code"
    examples: list[CodeCase] = Field(default_factory=list, max_length=10)
    heldout: list[CodeCase] = Field(min_length=1, max_length=100)
    candidate: str = Field(default="", max_length=100000)


Work = Annotated[Research | Allocation | Schedule | Forecast | Coding, Field(discriminator="kind")]


class Mission(StrictModel):
    """An immutable goal and its authorized input data."""

    goal: str = Field(min_length=3, max_length=2000)
    work: Work
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    population: int = Field(default=20, ge=4, le=50)
    generations: int = Field(default=12, ge=1, le=50)

    @model_validator(mode="after")
    def unique_ids(self) -> Mission:
        """Reject ambiguous references before any work starts."""
        records = (
            self.work.sources
            if isinstance(self.work, Research)
            else (
                self.work.items
                if isinstance(self.work, Allocation)
                else self.work.jobs
                if isinstance(self.work, Schedule)
                else []
            )
        )
        ids = [r.id for r in records]
        if len(ids) != len(set(ids)):
            raise ValueError("input IDs must be unique")
        return self


class ChainConfig(StrictModel):
    """An explicitly selected chain and pinned token implementation."""

    rpc_url: str
    chain_id: int = Field(default=1, ge=1)
    token_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmations: int = Field(default=12, ge=1, le=10000)
    reinvest_bps: int = Field(default=0, ge=0, le=10000)

    @model_validator(mode="after")
    def validate_rpc(self) -> ChainConfig:
        """Allow cleartext RPC only on a loopback development chain."""
        from urllib.parse import urlsplit

        url = urlsplit(self.rpc_url)
        local = url.hostname in {"127.0.0.1", "localhost", "::1"}
        if not url.hostname or url.username or url.password or url.fragment:
            raise ValueError("invalid RPC URL")
        if url.scheme != "https" and not (url.scheme == "http" and local and self.chain_id != 1):
            raise ValueError("mainnet and remote RPC require HTTPS")
        return self


class RuntimeConfig(StrictModel):
    """Operator configuration, separate from untrusted mission input."""

    name: str = Field(default="alpha-agent", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    llm_url: str = ""
    llm_model: str = ""
    llm_key_env: str = Field(default="ALPHA_AGENT_LLM_KEY", pattern=r"^[A-Z][A-Z0-9_]{0,80}$")
    llm_timeout: int = Field(default=120, ge=1, le=300)
    max_output_tokens: int = Field(default=1200, ge=64, le=4096)
    max_source_chars: int = Field(default=60000, ge=1000, le=100000)
    max_evaluations: int = Field(default=10000, ge=20, le=20000)
    allow_remote_llm: bool = False
    allow_code_execution: bool = False
    chain: ChainConfig | None = None

    @model_validator(mode="after")
    def validate_provider(self) -> RuntimeConfig:
        """Remote data disclosure requires explicit operator configuration."""
        from urllib.parse import urlsplit

        if bool(self.llm_url) != bool(self.llm_model):
            raise ValueError("llm_url and llm_model must be configured together")
        if self.llm_url:
            url = urlsplit(self.llm_url)
            local = url.hostname in {"127.0.0.1", "localhost", "::1"}
            if url.username or url.password or url.query or url.fragment or not url.hostname:
                raise ValueError("invalid provider URL")
            if url.scheme not in {"http", "https"} or (url.scheme == "http" and not local):
                raise ValueError("remote providers require HTTPS")
            if not local and not self.allow_remote_llm:
                raise ValueError("set allow_remote_llm to authorize sending source data to this provider")
        return self
