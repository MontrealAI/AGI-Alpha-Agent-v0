# SPDX-License-Identifier: Apache-2.0
"""Bounded inert records and exact quantities for structural transfer."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path
import re
from typing import Any, Callable

MAX_BYTES = 1_048_576
SOURCE_SCHEMA = "agialpha/structural-source/v1"
CAPTURE_SCHEMA = "agialpha/structural-capture/v1"
PRINCIPLE_SCHEMA = "agialpha/structural-principle/v1"
REQUEST_SCHEMA = "agialpha/structural-transfer-request/v1"
RESULT_SCHEMA = "agialpha/structural-transfer-result/v1"


def bounded(value: Any) -> Any:
    """Reject executable, nonfinite, excessively nested or oversized values."""
    count = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if count > 20000 or depth > 24:
            raise ValueError("JSON structural bound exceeded")
        if item is None or type(item) in {bool, int}:
            if type(item) is int and abs(item) > 10**18:
                raise ValueError("JSON integer bound exceeded")
        elif isinstance(item, str):
            if len(item) > MAX_BYTES:
                raise ValueError("JSON string bound exceeded")
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
        elif isinstance(item, dict) and all(isinstance(key, str) for key in item):
            for key, child in item.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise ValueError("inert exact JSON values required; use rational strings for quantities")

    visit(value, 0)
    if len(canonical(value)) > MAX_BYTES:
        raise ValueError("JSON byte bound exceeded")
    return value


def canonical(value: Any) -> bytes:
    """Encode the exact portable representation."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    """Hash canonical JSON."""
    return hashlib.sha256(canonical(value)).hexdigest()


def code_hash(function: Callable[..., Any]) -> str:
    """Bind inspectable implementation bytes rather than a caller assertion."""
    return hashlib.sha256(inspect.getsource(function).encode()).hexdigest()


def quantity(value: Any, *, nonnegative: bool = True) -> Fraction:
    """Read one bounded exact rational string without coercion."""
    if not isinstance(value, str) or not re.fullmatch(r"-?[0-9]{1,16}(?:/[1-9][0-9]{0,15})?", value):
        raise ValueError("bounded rational string required")
    result = Fraction(value)
    if abs(result) > 10**15 or (nonnegative and result < 0):
        raise ValueError("quantity outside supported range")
    return result


def rational(value: Fraction) -> str:
    """Return canonical rational syntax."""
    return str(value)


def identifier(value: Any) -> str:
    """Validate an explicit bounded identifier."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", value):
        raise ValueError("bounded identifier required")
    return value


def text(value: Any, limit: int = 2000) -> str:
    """Require meaningful bounded text."""
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("bounded nonempty text required")
    return value


def exact_keys(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    """Reject ambiguous contracts and unsupported claims."""
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - (optional or set()):
        raise ValueError("record schema mismatch")
    return value


def parse(raw: bytes) -> Any:
    """Read finite JSON with duplicate-key rejection and a hard byte cap."""
    if len(raw) > MAX_BYTES:
        raise ValueError("input exceeds 1 MiB")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out

    return bounded(
        json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("number")))
    )


def read(path: Path) -> Any:
    """Capture one bounded regular input, rejecting final symlinks."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular input required")
    with path.open("rb") as stream:
        return parse(stream.read(MAX_BYTES + 1))


def write_new(path: Path, value: Any) -> None:
    """Exclusively create a bounded artifact, preserving collisions."""
    raw = canonical(bounded(value))
    if path.is_symlink():
        raise ValueError("output symlink is not supported")
    with path.open("xb") as stream:
        stream.write(raw + b"\n")


def strict_acceptance(verdict: Any, task_id: str, artifact_hash: str) -> dict[str, Any]:
    """Bind independent acceptance to the exact task and artifact."""
    if (
        not isinstance(verdict, dict)
        or verdict.get("accepted") is not True
        or verdict.get("task_id") != task_id
        or verdict.get("artifact_hash") != artifact_hash
    ):
        raise ValueError("independent acceptance or immutable identity mismatch")
    bounded(verdict)
    return verdict
