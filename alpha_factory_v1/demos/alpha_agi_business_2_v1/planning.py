# SPDX-License-Identifier: Apache-2.0
"""Bounded evidence review and exact portfolio planning over supplied observations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, cast

# Reuse the enterprise demo's bounded JSON reader and canonical commitments.
from alpha_factory_v1.demos.alpha_agi_business_3_v1.enterprise import digest, read_json

SCHEMA = "agialpha.business2.input.v1"
REPORT_SCHEMA = "agialpha.business2.report.v1"
MAX_INPUT_BYTES = 128_000
SCOPE = (
    "Supplied observations and value-point assumptions only; sources are labels, not independently verified research. "
    "No live data, model inference, revenue forecast, execution or payment. Positive change is not causation."
)


def _keys(value: Any, keys: str, label: str) -> None:
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise ValueError(f"{label} requires exactly: {keys}")


def _text(value: Any, label: str, maximum: int = 200) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} requires nonempty text of at most {maximum} characters")
    if any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError(f"{label} contains invalid characters")


def _integer(value: Any, low: int, high: int, label: str) -> None:
    if type(value) is not int or not low <= value <= high:  # noqa: E721 - exact integers exclude bool
        raise ValueError(f"{label} must be an integer in [{low}, {high}]")


def _id(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", value):
        raise ValueError("IDs require 1–40 lowercase letters, digits or hyphens, starting with a letter")


def validate(source: Any) -> dict[str, Any]:
    """Validate the complete input before doing bounded combinatorial work."""
    _keys(source, "schema id provenance policy observations opportunities", "Input")
    if source["schema"] != SCHEMA:
        raise ValueError("Unsupported Business 2 schema")
    _id(source["id"])
    _keys(source["provenance"], "kind note", "Provenance")
    if source["provenance"]["kind"] not in ("constructed", "supplied"):
        raise ValueError("Provenance kind must be constructed or supplied")
    _text(source["provenance"]["note"], "Provenance note", 500)
    _keys(source["policy"], "effortHours maxProjects minSupportingSources", "Policy")
    for key, low, high in (("effortHours", 0, 100_000), ("maxProjects", 0, 16), ("minSupportingSources", 1, 64)):
        _integer(source["policy"][key], low, high, key)
    for collection, maximum in (("observations", 64), ("opportunities", 16)):
        values = source[collection]
        if not isinstance(values, list) or not 1 <= len(values) <= maximum:
            raise ValueError(f"{collection} requires 1–{maximum} entries")
        ids: set[str] = set()
        for value in values:
            if collection == "observations":
                _keys(value, "id source metric unit baseline current direction", "Observation")
                for key in ("source", "metric", "unit"):
                    _text(value[key], key)
                for key in ("baseline", "current"):
                    _integer(value[key], 0, 1_000_000_000, key)
                if value["direction"] not in ("increase", "decrease"):
                    raise ValueError("direction must be increase or decrease")
            else:
                _keys(value, "id title effortHours valuePoints evidenceIds", "Opportunity")
                _text(value["title"], "title")
                _integer(value["effortHours"], 1, 100_000, "effortHours")
                _integer(value["valuePoints"], 0, 1_000_000, "valuePoints")
                refs = value["evidenceIds"]
                if not isinstance(refs, list) or not 1 <= len(refs) <= 64:
                    raise ValueError("evidenceIds requires 1–64 observation IDs")
                for ref in refs:
                    _id(ref)
                if len(refs) != len(set(refs)):
                    raise ValueError("Duplicate evidence reference")
            _id(value["id"])
            if value["id"] in ids:
                raise ValueError(f"Duplicate {collection} ID")
            ids.add(value["id"])
    observation_ids = {row["id"] for row in source["observations"]}
    for row in source["opportunities"]:
        if not set(row["evidenceIds"]) <= observation_ids:
            raise ValueError("Unknown observation reference")
    return cast(dict[str, Any], source)


def evaluate(source: Any) -> dict[str, Any]:
    """Review evidence and maximize supplied points, breaking ties by effort then IDs."""
    source = validate(source)
    observations = []
    for row in sorted(source["observations"], key=lambda r: r["id"]):
        delta = row["current"] - row["baseline"]
        observations.append(
            {**row, "delta": delta, "supports": delta > 0 if row["direction"] == "increase" else delta < 0}
        )
    by_id = {row["id"]: row for row in observations}
    reviewed = []
    for row in sorted(source["opportunities"], key=lambda r: r["id"]):
        supports = sorted({by_id[ref]["source"].strip() for ref in row["evidenceIds"] if by_id[ref]["supports"]})
        eligible = len(supports) >= source["policy"]["minSupportingSources"]
        reviewed.append({**row, "supportingSources": supports, "eligible": eligible})
    eligible_rows = [row for row in reviewed if row["eligible"]]
    best: tuple[int, int, tuple[str, ...]] = (0, 0, ())
    for mask in range(1 << len(eligible_rows)):
        chosen = [row for i, row in enumerate(eligible_rows) if mask & (1 << i)]
        hours = sum(row["effortHours"] for row in chosen)
        if hours > source["policy"]["effortHours"] or len(chosen) > source["policy"]["maxProjects"]:
            continue
        score = sum(row["valuePoints"] for row in chosen)
        candidate = (-score, hours, tuple(row["id"] for row in chosen))
        if candidate < best:
            best = candidate
    selected = list(best[2])
    for row in reviewed:
        row["selected"] = row["id"] in selected
        row["reason"] = (
            "selected" if row["selected"] else "insufficient_support" if not row["eligible"] else "portfolio_tradeoff"
        )
    report = {
        "schema": REPORT_SCHEMA,
        "inputDigest": digest(source),
        "id": source["id"],
        "provenance": source["provenance"],
        "scope": SCOPE,
        "research": {"observations": observations, "opportunities": reviewed},
        "plan": {
            "selectedIds": selected,
            "totalValuePoints": -best[0],
            "totalEffortHours": best[1],
            "remainingEffortHours": source["policy"]["effortHours"] - best[1],
            "policy": source["policy"],
            "subsetsEvaluated": 1 << len(eligible_rows),
            "objective": "maximize supplied valuePoints; ties: minimum effortHours, then lexicographic IDs",
        },
    }
    return {**report, "reportDigest": digest(report)}


def load_report(path: Path) -> dict[str, Any]:
    """Read one bounded JSON document and compute its evidence report."""
    return evaluate(read_json(path, MAX_INPUT_BYTES))


def main(argv: list[str] | None = None) -> int:
    """Run once without importing the service, starting providers or writing files."""
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--input", type=Path, help="Supplied JSON input (at most 128,000 bytes)")
    choice.add_argument("--example", action="store_true", help="Use the explicitly synthetic bundled example")
    args = parser.parse_args(argv)
    try:
        report = load_report(Path(__file__).with_name("example.json") if args.example else args.input)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
