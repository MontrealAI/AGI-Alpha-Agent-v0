# SPDX-License-Identifier: Apache-2.0
"""Inert rational-polynomial contracts and collision-safe file operations."""

from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path
from typing import Any

TASK_SCHEMA = "agialpha/claim-probe/v1"
RESULT_SCHEMA = "agialpha/claim-probe-result/v1"
MAX_BYTES = 2_000_000


def rational(value: Any) -> Fraction:
    """Read a bounded exact rational, refusing floats and oversized syntax."""
    if not isinstance(value, str) or not re.fullmatch(r"-?[0-9]{1,13}(?:/[1-9][0-9]{0,11})?", value):
        raise ValueError("bounded rational string required")
    out = Fraction(value)
    if abs(out.numerator) > 10**12 or out.denominator > 10**12:
        raise ValueError("rational magnitude")
    return out


def canonical(value: Any) -> bytes:
    """Encode inert finite JSON with no nonfinite numbers."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    """Bind exactly the canonical input."""
    return hashlib.sha256(canonical(value)).hexdigest()


def validate(task: Any) -> tuple[list[Fraction], Fraction, Fraction]:
    """Validate the fixed claim, numeric domain and resource scope."""
    keys = {"schema", "id", "coefficients", "domain", "claim", "sources", "scope", "limits"}
    if not isinstance(task, dict) or set(task) != keys or task["schema"] != TASK_SCHEMA:
        raise ValueError("task schema")
    if not isinstance(task["id"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", task["id"]):
        raise ValueError("task identity")
    if task["claim"] != "nonnegative-throughout-domain" or task["scope"] != "declared-mathematical-model-only":
        raise ValueError("claim scope cannot be relaxed")
    coefficients = task["coefficients"]
    if not isinstance(coefficients, list) or not 1 <= len(coefficients) <= 9:
        raise ValueError("polynomial degree cap")
    c = [rational(x) for x in coefficients]
    domain = task["domain"]
    if not isinstance(domain, list) or len(domain) != 2:
        raise ValueError("domain")
    a, b = map(rational, domain)
    if not a < b or max(abs(a), abs(b)) > 10**6:
        raise ValueError("domain order or magnitude")
    limits = task["limits"]
    if not isinstance(limits, dict) or set(limits) != {"cells", "depth", "seconds"}:
        raise ValueError("resource contract")
    for key, lo, hi in [("cells", 1, 4096), ("depth", 0, 24), ("seconds", 1, 10)]:
        if type(limits[key]) is not int or not lo <= limits[key] <= hi:
            raise ValueError("resource cap")
    if not isinstance(task["sources"], list) or not 1 <= len(task["sources"]) <= 8:
        raise ValueError("source provenance")
    if any(not isinstance(x, str) or len(x) > 1000 or not x.startswith("https://") for x in task["sources"]):
        raise ValueError("source reference")
    if len(canonical(task)) > 32_000:
        raise ValueError("task byte cap")
    while len(c) > 1 and not c[-1]:
        c.pop()
    return c, a, b


def read(path: Path) -> Any:
    """Read a bounded regular input without following a final symlink."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular input required")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("input byte cap")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON field")
            out[key] = value
        return out

    return json.loads(
        raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("number"))
    )


def write_new(path: Path, value: Any) -> None:
    """Create one artifact exclusively; an existing output is preserved."""
    raw = canonical(value)
    if len(raw) > MAX_BYTES or path.is_symlink():
        raise ValueError("output scope")
    with path.open("xb") as stream:
        stream.write(raw + b"\n")
