# SPDX-License-Identifier: Apache-2.0
"""Bounded offline comparison of supplied opportunity assessments, not forecasts."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.store import digest
from alpha_factory_v1.core.simulation.mats import Individual, pareto_front

DIMENSIONS = ("benefit", "confidence", "effort", "risk")
MAX_BYTES = 1024 * 1024
EXAMPLE = Path(__file__).with_name("opportunities.example.json")
LIMITATIONS = [
    "Ratings and evidence are supplied assessments, not independently verified facts.",
    "Scores compare priorities only; they do not estimate revenue, returns or probability of success.",
    "No provider, market data, evidence URL or external service is contacted. Human review is required.",
]


def _keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label}: expected exactly {', '.join(sorted(expected))}")


def _rating(value: Any, label: str) -> None:
    if type(value) is not int or not 0 <= value <= 100:  # noqa: E721 - reject bools and integer subclasses
        raise ValueError(f"{label}: expected an integer from 0 to 100")


def _text(value: Any, limit: int, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip().strip("\ufeff") or len(value) > limit:
        raise ValueError(f"{label}: expected trimmed nonempty text of at most {limit} characters")
    if any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError(f"{label}: control characters and unpaired surrogates are not allowed")


def validate_input(data: Any) -> None:
    """Reject unknown fields and coerced ratings before computing anything."""
    _keys(data, {"schema_version", "weights", "constraints", "opportunities"}, "input")
    if data["schema_version"] != "cross-industry-input-v1":
        raise ValueError("unsupported schema_version")
    _keys(data["weights"], set(DIMENSIONS), "weights")
    for key in DIMENSIONS:
        _rating(data["weights"][key], f"weights.{key}")
    if not sum(data["weights"].values()):
        raise ValueError("weights must have a positive sum")
    _keys(data["constraints"], {"max_risk", "min_confidence"}, "constraints")
    for key, value in data["constraints"].items():
        _rating(value, f"constraints.{key}")
    rows = data["opportunities"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("opportunities: expected 1 to 100 candidates")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        label = f"opportunities[{index}]"
        _keys(row, {"id", "sector", "opportunity", "evidence", *DIMENSIONS}, label)
        if not isinstance(row["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", row["id"]):
            raise ValueError(f"{label}.id: expected 1 to 64 ASCII letters, digits, underscores or hyphens")
        if row["id"] in seen:
            raise ValueError(f"duplicate opportunity id: {row['id']}")
        seen.add(row["id"])
        _text(row["sector"], 120, f"{label}.sector")
        _text(row["opportunity"], 500, f"{label}.opportunity")
        for key in DIMENSIONS:
            _rating(row[key], f"{label}.{key}")
        if not isinstance(row["evidence"], list) or not 1 <= len(row["evidence"]) <= 10:
            raise ValueError(f"{label}.evidence: expected 1 to 10 source references or assessment notes")
        for note in row["evidence"]:
            _text(note, 500, f"{label}.evidence")


def _round_ratio(numerator: int, denominator: int) -> float:
    """Round a nonnegative rational half-up to six decimal places."""
    return ((2 * numerator * 1_000_000 + denominator) // (2 * denominator)) / 1_000_000


def compare_opportunities(data: Any) -> dict[str, Any]:
    """Return a reproducible evidence-preserving ranking without writes or network IO."""
    validate_input(data)
    weights = data["weights"]
    total = sum(weights.values())
    constraints = data["constraints"]
    rows = []
    population = []
    for index, candidate in enumerate(data["opportunities"]):
        values = {k: candidate[k] if k in ("benefit", "confidence") else 100 - candidate[k] for k in DIMENSIONS}
        numerators = {k: weights[k] * values[k] for k in DIMENSIONS}
        reasons = []
        if candidate["risk"] > constraints["max_risk"]:
            reasons.append("risk exceeds max_risk")
        if candidate["confidence"] < constraints["min_confidence"]:
            reasons.append("confidence below min_confidence")
        rows.append(
            {
                **candidate,
                "evidence": list(candidate["evidence"]),
                "score": _round_ratio(sum(numerators.values()), total),
                "contributions": {k: _round_ratio(numerators[k], total) for k in DIMENSIONS},
                "eligible": not reasons,
                "exclusion_reasons": reasons,
                "rank": None,
                "pareto_optimal": False,
            }
        )
        if not reasons:
            population.append(
                Individual(
                    genome=[index],
                    fitness=(-candidate["benefit"], -candidate["confidence"], candidate["effort"], candidate["risk"]),
                )
            )
    for item in pareto_front(population):
        rows[int(item.genome[0])]["pareto_optimal"] = True
    rows.sort(key=lambda row: (not row["eligible"], -row["score"] if row["eligible"] else 0, row["id"]))
    for index, row in enumerate(rows):
        if row["eligible"]:
            row["rank"] = index + 1
    return {
        "schema_version": "cross-industry-report-v1",
        "mode": "supplied-input",
        "input_sha256": digest(data),
        "normalized_weights": {k: _round_ratio(weights[k], total) for k in DIMENSIONS},
        "constraints": dict(constraints),
        "ranking": rows,
        "selected_id": rows[0]["id"] if rows[0]["eligible"] else None,
        "limitations": list(LIMITATIONS),
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_input(path: Path) -> dict[str, Any]:
    """Read at most 1 MiB of strict UTF-8 JSON, rejecting duplicate keys."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("input exceeds 1 MiB")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    validate_input(data)
    return data


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="supplied assessment JSON file")
    source.add_argument("--example", action="store_true", help="compare the bundled synthetic fixture")
    args = parser.parse_args(argv)
    try:
        report = compare_opportunities(load_input(EXAMPLE if args.example else args.input))
    except (ValueError, OSError, RecursionError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if args.example:
        report["mode"] = "synthetic-example"
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
