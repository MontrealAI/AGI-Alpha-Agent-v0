# SPDX-License-Identifier: Apache-2.0
"""Frozen evaluation, source binding and bounded admission controls."""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
from .instrument import canonical, digest, write_new


def freeze(paths: list[Path], policy: dict[str, Any], output: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "policy": policy,
        "sources": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    }
    record["hash"] = digest(record)
    write_new(output, record)
    return record


def check_freeze(record: dict[str, Any], policy: dict[str, Any]) -> None:
    if digest({k: v for k, v in record.items() if k != "hash"}) != record["hash"] or record["policy"] != policy:
        raise ValueError("frozen policy changed")
    for path, expected in record["sources"].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError("frozen source changed")


def admit(candidate: dict[str, Any], authority: dict[str, Any], lane: str) -> bool:
    if authority.get("external_spend", 0) != 0 or authority.get("remote_action", False):
        return False
    if lane == "meta":
        return bool(authority.get("seed_budget", 0) > 0)
    if lane == "probe":
        return bool(authority.get("probe_budget", 0) > 0 and candidate.get("cost", 0) <= authority["probe_budget"])
    return lane == "flagship" and all(
        candidate.get(k, False)
        for k in ["need", "residual_constraint", "why_now", "constructed_means", "bridge", "accepted_outcome"]
    )


def training_view(task: dict[str, Any]) -> dict[str, Any]:
    if any(k in task for k in ["truth", "solution", "holdout_label", "private"]):
        raise ValueError("held-out solution leak")
    return dict(task)


def compare_complete(attempts: list[dict[str, Any]], expected_ids: list[str], strongest: str) -> dict[str, Any]:
    if [a["id"] for a in attempts] != expected_ids or any(a.get("comparator") != strongest for a in attempts):
        raise ValueError("missing denominator or comparator substitution")
    return {
        "attempted": len(attempts),
        "failed": sum(a["status"] != "accepted" for a in attempts),
        "cost": sum(a["cost"] for a in attempts),
    }


def research_admission(claim: str, physical: bool, implemented: bool, accepted: bool) -> str:
    if claim not in {"independently_checked", "formally_verified_model", "replicated"}:
        return "HOLD"
    if physical and claim == "formally_verified_model":
        return "HOLD"
    return "CONTINUE" if implemented and accepted else "HOLD"
