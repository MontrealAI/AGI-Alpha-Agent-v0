# SPDX-License-Identifier: Apache-2.0
"""Separate, inert supplier-browser work contract; existing compute wire is unchanged."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel
from .store import canonical
from .successor.computer import ComputerTask
from .successor.protocol import safe_json_loads

MAX_SPEC_BYTES = 64_000
MAX_RESULT_BYTES = 64_000
BEGIN = "BEGIN_SUPPLIER_COMPARISON_V1"
END = "END_SUPPLIER_COMPARISON_V1"


class Quote(StrictModel):
    supplier: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,79}$")
    quantity: int = Field(strict=True, ge=1, le=1_000_000)
    unitCents: int = Field(strict=True, ge=0, le=1_000_000_000)
    shippingCents: int = Field(strict=True, ge=0, le=1_000_000_000)
    deliveryDays: int = Field(strict=True, ge=1, le=365)


class SupplierSpec(StrictModel):
    schema_id: Literal["agialpha.supplier-browser-spec.v1"] = Field(alias="schema")
    market: Literal["agijobsv0-jobregistry-v2"]
    executor: Literal["alpha-supplier-browser-v1"]
    input_rights: Literal["synthetic"]
    quotes: list[Quote] = Field(min_length=1, max_length=16)
    maxDeliveryDays: int = Field(strict=True, ge=1, le=365)
    max_turns: int = Field(default=10, strict=True, ge=1, le=30)
    max_actions: int = Field(default=30, strict=True, ge=1, le=100)
    max_seconds: int = Field(default=180, strict=True, ge=10, le=600)

    @model_validator(mode="after")
    def unique_suppliers(self) -> SupplierSpec:
        if len({q.supplier for q in self.quotes}) != len(self.quotes):
            raise ValueError("Each supplied quote needs a unique supplier")
        if len({q.quantity for q in self.quotes}) != 1:
            raise ValueError("Compare quotes for the same quantity")
        return self


def read_spec(raw: bytes) -> tuple[SupplierSpec, str]:
    spec = SupplierSpec.model_validate(safe_json_loads(raw, max_bytes=MAX_SPEC_BYTES))
    return spec, "0x" + hashlib.sha256(raw).hexdigest()


def expected_report(spec: SupplierSpec) -> dict[str, Any]:
    """Independent integer arithmetic, never a provider's proposed verdict."""
    rows = [
        {
            "supplier": q.supplier,
            "totalCents": q.quantity * q.unitCents + q.shippingCents,
            "eligible": q.deliveryDays <= spec.maxDeliveryDays,
        }
        for q in spec.quotes
    ]
    eligible = sorted((row for row in rows if row["eligible"]), key=lambda row: (row["totalCents"], row["supplier"]))
    return {
        "maxDeliveryDays": spec.maxDeliveryDays,
        "quotes": rows,
        "recommendedSupplier": eligible[0]["supplier"] if eligible else None,
        "purchaseExecuted": False,
    }


def extract_artifacts(spec: SupplierSpec, visible_text: str) -> dict[str, Any]:
    """Require one observed comparison; recomputation cannot manufacture worker output."""
    if len(visible_text.encode("utf-8")) > MAX_RESULT_BYTES:
        raise ValueError("Observed browser text exceeds its bound")
    lines = visible_text.splitlines()
    if lines.count(BEGIN) != 1 or lines.count(END) != 1:
        raise ValueError("The browser has not produced one unambiguous comparison")
    start, end = lines.index(BEGIN), lines.index(END)
    if end <= start:
        raise ValueError("Malformed comparison markers")
    start += 1
    observed = safe_json_loads("\n".join(lines[start:end]).strip().encode(), max_bytes=MAX_RESULT_BYTES)
    expected = expected_report(spec)
    # Canonical comparison rejects bool-as-int coercion, extra fields, omitted rows and altered ordering.
    if canonical(observed) != canonical(expected):
        raise ValueError("Observed comparison fails independent supplied-quote acceptance")
    winner = observed["recommendedSupplier"]
    brief = (
        f"Recommended supplier: {winner}. No purchase executed.\n"
        if winner
        else "No eligible supplier. No purchase executed.\n"
    )
    artifacts = []
    for name, media, content in (
        ("comparison.json", "application/json", canonical(observed).decode() + "\n"),
        ("recommendation.md", "text/markdown", brief),
    ):
        artifacts.append(
            {
                "name": name,
                "mediaType": media,
                "content": content,
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
            }
        )
    return {
        "artifacts": artifacts,
        "acceptance": {
            "accepted": True,
            "reviewer": "supplied-quote integer arithmetic v1",
            "settlementApproved": False,
            "productionApproved": False,
        },
    }


def computer_task(spec: SupplierSpec) -> ComputerTask:
    """Generate a shipped, networkless interface; work files cannot supply executable HTML."""
    quotes = canonical([quote.model_dump() for quote in spec.quotes]).decode()
    options = "".join(f'<option value="{days}">{days} days</option>' for days in sorted({1, spec.maxDeliveryDays, 365}))
    template = Path(__file__).with_name("web") / "supplier-lab.html"
    page = template.read_text(encoding="utf-8").replace("OPTIONS", options).replace("QUOTES", quotes)
    return ComputerTask(
        goal=f"Select the {spec.maxDeliveryDays}-day delivery limit and compare the supplied quotes. "
        "Inspect the resulting comparison. Finish only when the comparison is visible. Do not purchase anything.",
        html=page,
        allowed_urls=[],
        input_rights="synthetic",
        license="Synthetic supplied quote laboratory",
        max_turns=spec.max_turns,
        max_actions=spec.max_actions,
        max_seconds=spec.max_seconds,
    )
