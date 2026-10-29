# SPDX-License-Identifier: Apache-2.0
"""Installed adapter registry; task files never choose executable code or authority."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .contracts import digest
from . import eadarp, eadarp_check, reserve_source


def adapter_spec(adapter_id: str) -> dict[str, Any]:
    if adapter_id == "reserve-experience/v1":
        names, dimension, unit, assumptions = ["cash", "obligations", "free"], "currency", "microUSD", []
    elif adapter_id == "eadarp-temporal/v1":
        names, dimension, unit, assumptions = (
            ["total_energy", "consumed_energy", "terminal_energy"],
            "energy",
            "kWh",
            eadarp.ASSUMPTIONS,
        )
    else:
        raise ValueError("unsupported installed adaptation; no prebuilt successor capability")
    return {
        "adapter_id": adapter_id,
        "family": "linear-capacity",
        "variables": [
            {"name": name, "dimension": dimension, "unit": unit, "role": role}
            for name, role in zip(names, ["capacity", "reserved", "remaining"])
        ],
        "relations": [{"kind": "conservation", "inputs": [names[1], names[2]], "output": names[0]}],
        "assumptions": assumptions,
        "required_inputs": ["id"],
        "boundary_conditions": [
            "Type-parametric capacity accounting only; no currency-to-energy numerical conversion",
            "New target constraints require independent construction and acceptance",
            "No field safety, legal compliance, deployment or empirical demand inference",
        ],
    }


def implementation_hashes(adapter_id: str) -> dict[str, str]:
    adapter_spec(adapter_id)
    modules = (
        [Path(__file__), Path(reserve_source.__file__)]
        if adapter_id == "reserve-experience/v1"
        else [Path(__file__), Path(eadarp.__file__), Path(eadarp_check.__file__)]
    )
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}


def construct(
    adapter_id: str, *, principle: dict[str, Any], target: dict[str, Any], mapping: dict[str, Any]
) -> dict[str, Any]:
    adapter_spec(adapter_id)
    if adapter_id != "eadarp-temporal/v1":
        raise ValueError("historical source audit is not a target construction")
    return {
        "schema": "agialpha/eadarp-adaptation/v1",
        "adapter_id": adapter_id,
        "task_hash": digest(target),
        "principle_hash": digest(principle),
        "mapping_hash": digest(mapping),
        "model": eadarp.compile_model(target),
        "new_target_constraints": [
            "per-vehicle nonfungible energy",
            "time precedences",
            "seat capacity",
            "passenger-free charging",
            "maximum rides",
            "intermediate and terminal battery",
        ],
    }


def execute(adapter_id: str, constructed: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    adapter_spec(adapter_id)
    if adapter_id == "reserve-experience/v1":
        return reserve_source.snapshot(target)
    if constructed["task_hash"] != digest(target) or constructed["adapter_id"] != adapter_id:
        raise ValueError("constructed task binding")
    return eadarp.solve_model(target, constructed["model"])


def check(
    adapter_id: str, *, target: dict[str, Any], artifact: dict[str, Any], constructed: dict[str, Any]
) -> dict[str, Any]:
    adapter_spec(adapter_id)
    if adapter_id == "reserve-experience/v1":
        return reserve_source.verify(target, artifact)
    return eadarp_check.check(target, artifact, constructed)
