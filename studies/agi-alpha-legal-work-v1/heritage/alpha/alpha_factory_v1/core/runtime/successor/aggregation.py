# SPDX-License-Identifier: Apache-2.0
"""Pure, bounded aggregation engines; the candidate language has no code or effects."""

from __future__ import annotations

import itertools
from typing import Any

MAX_EVENTS = 20_000
MAX_DURATION_US = 1_000_000_000
EVENT_KEYS = {"day", "service", "duration_us", "ok"}
PROGRAM_KEYS = {"version", "layout", "cache_last", "update"}
CURRENT = {"version": 1, "engine": "current-dictionary"}
BETA = {"version": 1, "engine": "beta-sorted-groupby"}


def validate_events(events: Any) -> list[dict[str, Any]]:
    """Reject the whole input before work; keys use exact Unicode scalar equality."""
    # Exact builtin types reject bool/int substitution and arbitrary subclasses.
    if type(events) is not list or len(events) > MAX_EVENTS:  # noqa: E721
        raise ValueError("events must be a list of at most 20000 records")
    for event in events:
        if type(event) is not dict or set(event) != EVENT_KEYS:  # noqa: E721
            raise ValueError("event must contain exactly day, service, duration_us and ok")
        for key in ("day", "service"):
            value = event[key]
            if type(value) is not str or not 1 <= len(value) <= 64:  # noqa: E721
                raise ValueError("day and service must contain 1..64 Unicode scalar values")
            if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
                raise ValueError("surrogate code points are not Unicode scalar values")
        if type(event["duration_us"]) is not int or not 0 <= event["duration_us"] <= MAX_DURATION_US:  # noqa: E721
            raise ValueError("duration_us must be an integer in 0..1000000000")
        if type(event["ok"]) is not bool:  # noqa: E721
            raise ValueError("ok must be Boolean")
    return events


def validate_program(program: Any) -> dict[str, Any]:
    """Validate the closed, non-general-purpose composition language."""
    if type(program) is not dict or set(program) != PROGRAM_KEYS:  # noqa: E721
        raise ValueError("candidate must have exactly version, layout, cache_last and update")
    if type(program["version"]) is not int or program["version"] != 1:  # noqa: E721
        raise ValueError("unsupported aggregation program version")
    if program["layout"] not in ("tuple", "nested") or type(program["layout"]) is not str:  # noqa: E721
        raise ValueError("unsupported grouping layout")
    if type(program["cache_last"]) is not bool:  # noqa: E721
        raise ValueError("cache_last must be Boolean")
    if program["update"] not in ("branch", "builtin") or type(program["update"]) is not str:  # noqa: E721
        raise ValueError("unsupported update operator")
    return dict(program)


def _row(day: str, service: str, value: list[int]) -> dict[str, Any]:
    return {
        "day": day,
        "service": service,
        "count": value[0],
        "total_duration_us": value[1],
        "max_duration_us": value[2],
        "error_count": value[3],
    }


def current(events: Any) -> list[dict[str, Any]]:
    """Competent incumbent: a one-pass tuple-key dictionary and sorted output."""
    records = validate_events(events)
    groups: dict[tuple[str, str], list[int]] = {}
    for event in records:
        key = (event["day"], event["service"])
        duration = event["duration_us"]
        value = groups.get(key)
        if value is None:
            groups[key] = [1, duration, duration, int(not event["ok"])]
        else:
            value[0] += 1
            value[1] += duration
            value[2] = max(value[2], duration)
            value[3] += not event["ok"]
    return [_row(day, service, groups[(day, service)]) for day, service in sorted(groups)]


def beta(events: Any) -> list[dict[str, Any]]:
    """Independent sort/reduce alternative with C-level sorting and groupby."""
    records = validate_events(events)
    rows = sorted((item["day"], item["service"], item["duration_us"], item["ok"]) for item in records)
    result = []
    for key, group in itertools.groupby(rows, key=lambda item: (item[0], item[1])):
        count = total = maximum = errors = 0
        for _, _, duration, ok in group:
            count += 1
            total += duration
            if duration > maximum:  # noqa: PLR1730 - independently measured branch implementation
                maximum = duration
            if not ok:
                errors += 1
        result.append(_row(key[0], key[1], [count, total, maximum, errors]))
    return result


def aggregate(events: Any, program: dict[str, Any]) -> list[dict[str, Any]]:
    """Interpret fixed grouping operators; no imported functions, eval or arbitrary code."""
    config = validate_program(program)
    records = validate_events(events)
    tuples: dict[tuple[str, str], list[int]] = {}
    nested: dict[str, dict[str, list[int]]] = {}
    last_key: tuple[str, str] | None = None
    last_value: list[int] | None = None
    for event in records:
        day, service = event["day"], event["service"]
        key = (day, service)
        duration = event["duration_us"]
        if config["cache_last"] and key == last_key:
            value = last_value
        elif config["layout"] == "nested":
            bucket = nested.get(day)
            if bucket is None:
                bucket = nested[day] = {}
            value = bucket.get(service)
            if value is None:
                value = bucket[service] = [0, 0, 0, 0]
        else:
            value = tuples.get(key)
            if value is None:
                value = tuples[key] = [0, 0, 0, 0]
        assert value is not None
        value[0] += 1
        value[1] += duration
        if config["update"] == "branch":
            if duration > value[2]:  # noqa: PLR1730 - this is the grammar's distinct branch operator
                value[2] = duration
        else:
            value[2] = max(value[2], duration)
        value[3] += not event["ok"]
        last_key, last_value = key, value
    if config["layout"] == "nested":
        return [_row(day, service, nested[day][service]) for day in sorted(nested) for service in sorted(nested[day])]
    return [_row(day, service, tuples[(day, service)]) for day, service in sorted(tuples)]


def execute(events: Any, artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Dispatch only exact built-in comparators or validated grammar artifacts."""
    if artifact == CURRENT and type(artifact.get("version")) is int:  # noqa: E721
        return current(events)
    if artifact == BETA and type(artifact.get("version")) is int:  # noqa: E721
        return beta(events)
    return aggregate(events, artifact)


def contract() -> dict[str, Any]:
    """Machine-readable mission contract shared by the frozen experiment."""
    return {
        "version": 1,
        "mission": "streaming-metrics-v1",
        "input": {"container": "list", "max_events": MAX_EVENTS, "exact_fields": sorted(EVENT_KEYS)},
        "keys": "1..64 Unicode scalar values, exact equality, no normalization; codepoint lexical output order",
        "duration_us": {"type": "strict-integer", "minimum": 0, "maximum": MAX_DURATION_US},
        "ok": "strict-boolean",
        "output": ["day", "service", "count", "total_duration_us", "max_duration_us", "error_count"],
        "empty": [],
        "malformed": "reject entire input with ValueError before aggregating",
        "effects": [],
        "bounds": "At most 20000 groups; totals <=20000000000000, exact integers",
    }
