# SPDX-License-Identifier: Apache-2.0
"""Independent exact enumeration of the declared finite archival worlds."""

from __future__ import annotations

import argparse
from fractions import Fraction
from itertools import combinations, product
import json
from math import comb, prod
from pathlib import Path
from typing import Any, Iterator

MAX_WORLDS = 2_000_000
SCHEMA = "agialpha.archive-claim.v1"


def number(value: Any) -> Fraction:
    """Parse a finite bounded rational from a declared string."""
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        raise ValueError("Numbers must be nonempty decimal or rational strings of at most 256 characters")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("Invalid exact rational") from exc
    if result.numerator.bit_length() > 512 or result.denominator.bit_length() > 512:
        raise ValueError("Exact rational exceeds the oracle arithmetic bound")
    return result


def identifier(value: Any) -> str:
    """Require an ordinary bounded identifier."""
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError("A nonempty identifier of at most 128 characters is required")
    return value


def alternatives(value: Any) -> tuple[Fraction, ...]:
    """Treat numerically identical alternatives as one possible value."""
    if not isinstance(value, list) or not 1 <= len(value) <= 64:
        raise ValueError("Each variable requires 1 through 64 alternatives")
    return tuple(dict.fromkeys(number(item) for item in value))


def prepare(case: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, Fraction]:
    """Validate only the declared model, without consulting another solver."""
    if not isinstance(case, dict) or case.get("schema") != SCHEMA or case.get("source_model") != "research-authored":
        raise ValueError("Unsupported oracle input model")
    identifier(case.get("id"))
    identifier(case.get("unit"))
    if not isinstance(case.get("rows"), list) or not 1 <= len(case["rows"]) <= 64:
        raise ValueError("The oracle accepts 1 through 64 rows")
    if not isinstance(case.get("calibrations"), list) or not 1 <= len(case["calibrations"]) <= 64:
        raise ValueError("The oracle requires 1 through 64 declared calibration groups")
    groups: list[dict[str, Any]] = []
    group_ids: set[str] = set()
    for item in case["calibrations"]:
        name = identifier(item["id"])
        if name in group_ids:
            raise ValueError("Duplicate calibration ID")
        group_ids.add(name)
        groups.append({"id": name, "alternatives": alternatives(item["alternatives"])})
    rows: list[dict[str, Any]] = []
    row_ids: set[str] = set()
    for item in case["rows"]:
        name, group = identifier(item["id"]), identifier(item["group_id"])
        if name in row_ids or group not in group_ids:
            raise ValueError("Duplicate row or undeclared calibration group")
        row_ids.add(name)
        bound = number(item["error_bound"])
        if bound < 0:
            raise ValueError("Error bounds cannot be negative")
        rows.append(
            {
                "id": name,
                "source_id": identifier(item["source_id"]),
                "group_id": group,
                "alternatives": alternatives(item["alternatives"]),
                "weight": number(item["weight"]),
                "error_bound": bound,
            }
        )
    budget = case.get("error_budget")
    if type(budget) is not int or not 0 <= budget <= len(rows):
        raise ValueError("Error budget must be an integer between zero and the row count")
    return rows, groups, budget, number(case["threshold"])


def error_vectors(rows: list[dict[str, Any]], budget: int) -> Iterator[dict[int, Fraction]]:
    """Enumerate sparse signed row-error assignments, including the empty one."""
    nonzero = [index for index, row in enumerate(rows) if row["error_bound"] > 0]
    for count in range(min(budget, len(nonzero)) + 1):
        for selected in combinations(nonzero, count):
            for signs in product((-1, 1), repeat=count):
                yield {index: rows[index]["error_bound"] * sign for index, sign in zip(selected, signs)}


def solve(case: dict[str, Any], max_worlds: int = MAX_WORLDS) -> dict[str, Any]:
    """Enumerate every allowed assignment and retain exact extremal witnesses."""
    if type(max_worlds) is not int or not 1 <= max_worlds <= MAX_WORLDS:
        raise ValueError("Oracle budget must be between 1 and 2,000,000 worlds")
    rows, groups, budget, threshold = prepare(case)
    nonzero = sum(row["error_bound"] > 0 for row in rows)
    error_count = sum(comb(nonzero, count) * 2**count for count in range(min(budget, nonzero) + 1))
    expected_worlds = (
        prod(len(row["alternatives"]) for row in rows)
        * prod(len(group["alternatives"]) for group in groups)
        * error_count
    )
    if expected_worlds > max_worlds:
        raise ValueError(f"Oracle world budget exceeded: {expected_worlds} > {max_worlds}")
    lower: Fraction | None = None
    upper: Fraction | None = None
    lower_witness: dict[str, Any] | None = None
    upper_witness: dict[str, Any] | None = None
    visited = 0
    for glyphs in product(*(row["alternatives"] for row in rows)):
        for offsets in product(*(group["alternatives"] for group in groups)):
            calibration = {group["id"]: offset for group, offset in zip(groups, offsets)}
            base_values = [glyph + calibration[row["group_id"]] for row, glyph in zip(rows, glyphs)]
            base = sum((row["weight"] * value for row, value in zip(rows, base_values)), Fraction(0))
            for errors in error_vectors(rows, budget):
                value = base + sum((rows[index]["weight"] * error for index, error in errors.items()), Fraction(0))
                visited += 1
                is_low, is_high = lower is None or value < lower, upper is None or value > upper
                if is_low or is_high:
                    witness = {
                        "glyph_values": {row["id"]: str(glyph) for row, glyph in zip(rows, glyphs)},
                        "calibration_offsets": {name: str(offset) for name, offset in calibration.items()},
                        "row_errors": {
                            row["id"]: str(errors.get(index, Fraction(0))) for index, row in enumerate(rows)
                        },
                        "row_values": {
                            row["id"]: str(base_values[index] + errors.get(index, Fraction(0)))
                            for index, row in enumerate(rows)
                        },
                        "query_value": str(value),
                    }
                    if is_low:
                        lower, lower_witness = value, witness
                    if is_high:
                        upper, upper_witness = value, witness
    if visited != expected_worlds or lower is None or upper is None:
        raise AssertionError("Enumeration did not traverse the complete nonempty world set")
    decision = "TRUE" if lower > threshold else "FALSE" if upper <= threshold else "UNRESOLVED"
    return {
        "id": case["id"],
        "lower": str(lower),
        "upper": str(upper),
        "decision": decision,
        "world_count": visited,
        "lower_witness": lower_witness,
        "upper_witness": upper_witness,
        "method": "independent exhaustive finite-world enumeration",
    }


def main() -> None:
    """Evaluate one JSON case through the independent enumeration oracle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-worlds", type=int, default=MAX_WORLDS)
    args = parser.parse_args()
    result = solve(json.loads(args.input.read_text()), args.max_worlds)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
