# SPDX-License-Identifier: Apache-2.0
"""Source-bound historical flood evidence; no risk or true-loss certification."""

from __future__ import annotations

import csv
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any

EVENT_TYPES = ["Coastal Flood", "Flash Flood", "Flood", "Lakeshore Flood"]
POLICY = "noaa-source-records-unknown-is-not-zero/v1"
BASE_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
INPUTS = Path(__file__).resolve().parent / "inputs"


class _BoundedReader(io.RawIOBase):
    def __init__(self, stream):
        self.stream = stream
        self.count = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        raw = self.stream.read(min(len(buffer), 200_000_001 - self.count))
        self.count += len(raw)
        if self.count > 200_000_000:
            raise ValueError("uncompressed source byte cap")
        buffer[: len(raw)] = raw
        return len(raw)


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def task_for(path: Path, year: int) -> dict[str, Any]:
    return {
        "schema": "agialpha/noaa-readiness-task/v1",
        "id": f"noaa-flood-readiness-{year}",
        "source_filename": path.name,
        "source_sha256": sha_file(path),
        "source_url": BASE_URL + path.name,
        "year": year,
        "event_types": EVENT_TYPES,
        "policy": POLICY,
    }


def validate_task(task: Any) -> None:
    keys = {
        "schema",
        "id",
        "source_filename",
        "source_sha256",
        "source_url",
        "year",
        "event_types",
        "policy",
    }
    if (
        not isinstance(task, dict)
        or set(task) != keys
        or task["schema"] != "agialpha/noaa-readiness-task/v1"
    ):
        raise ValueError("readiness task schema")
    if type(task["year"]) is not int or not 2000 <= task["year"] <= 2025:
        raise ValueError("source year")
    pattern = rf"StormEvents_details-ftp_v1\.0_d{task['year']}_c[0-9]{{8}}\.csv\.gz"
    if not isinstance(task["source_filename"], str) or not re.fullmatch(
        pattern, task["source_filename"]
    ):
        raise ValueError("fixed source basename")
    if (
        task["source_url"] != BASE_URL + task["source_filename"]
        or task["id"] != f"noaa-flood-readiness-{task['year']}"
    ):
        raise ValueError("source identity")
    if not re.fullmatch(r"[0-9a-f]{64}", task["source_sha256"]):
        raise ValueError("source hash")
    if task["event_types"] != EVENT_TYPES or task["policy"] != POLICY:
        raise ValueError("selection or missingness policy changed")


def parse_damage(raw: str) -> tuple[int | None, str]:
    text = raw.strip()
    if not text:
        return None, "missing"
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([KMB]?)", text)
    if not match:
        return None, "invalid"
    amount = (
        Decimal(match[1])
        * {"": 1, "K": 1000, "M": 1000000, "B": 1000000000}[match[2]]
        * 100
    )
    if amount != amount.to_integral_value():
        return None, "invalid"
    return int(amount), "reported_zero" if amount == 0 else "reported_nonzero"


def group_label(state: str, event_type: str) -> str:
    return (
        re.sub(r"[^A-Z0-9]+", "_", state.upper()).strip("_")
        + "__"
        + re.sub(r"[^A-Z0-9]+", "_", event_type.upper()).strip("_")
    )


def build_report(
    task: dict[str, Any], source: Path | None = None
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    validate_task(task)
    source = source or INPUTS / task["source_filename"]
    if (
        source.is_symlink()
        or not source.is_file()
        or source.stat().st_size > 25_000_000
    ):
        raise ValueError("bounded regular source")
    if sha_file(source) != task["source_sha256"]:
        raise ValueError("source bytes changed")
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}
    ids = set()
    selected = []
    raw_count = 0
    with (
        gzip.open(source, "rb") as raw,
        io.TextIOWrapper(
            io.BufferedReader(_BoundedReader(raw)), encoding="utf-8-sig", newline=""
        ) as stream,
    ):
        reader = csv.DictReader(stream)
        required = {
            "EVENT_ID",
            "STATE",
            "YEAR",
            "EVENT_TYPE",
            "CZ_TYPE",
            "DAMAGE_PROPERTY",
            "DAMAGE_CROPS",
        }
        if (
            reader.fieldnames is None
            or len(set(reader.fieldnames)) != len(reader.fieldnames)
            or not required <= set(reader.fieldnames)
        ):
            raise ValueError("source columns")
        for row in reader:
            raw_count += 1
            if raw_count > 200000:
                raise ValueError("source row cap")
            if row["YEAR"] != str(task["year"]):
                raise ValueError("source year mismatch")
            ident = row["EVENT_ID"]
            if not ident.isdigit() or ident in ids:
                raise ValueError("duplicate or invalid event ID")
            ids.add(ident)
            event_type = row["EVENT_TYPE"]
            if event_type not in EVENT_TYPES:
                continue
            state = row["STATE"]
            if not state or row["CZ_TYPE"] not in {"C", "Z", "M"}:
                raise ValueError("geography category")
            key = (state, event_type)
            if key not in groups:
                groups[key] = {
                    "state": state,
                    "event_type": event_type,
                    "native_group": group_label(*key),
                    "records": 0,
                    "geography": {"C": 0, "Z": 0, "M": 0},
                    "property": {
                        "known_cents": 0,
                        "missing": 0,
                        "invalid": 0,
                        "reported_zero": 0,
                        "reported_nonzero": 0,
                    },
                    "crop": {
                        "known_cents": 0,
                        "missing": 0,
                        "invalid": 0,
                        "reported_zero": 0,
                        "reported_nonzero": 0,
                    },
                }
            group = groups[key]
            group["records"] += 1
            group["geography"][row["CZ_TYPE"]] += 1
            if state not in states:
                states[state] = {
                    "state": state,
                    "records": 0,
                    "known_property_cents": 0,
                    "property_unknown": 0,
                    "missing_event_ids": [],
                }
            states[state]["records"] += 1
            trace = {
                "event_id": ident,
                "state": state,
                "event_type": event_type,
                "geography": row["CZ_TYPE"],
            }
            for field, column in [
                ("property", "DAMAGE_PROPERTY"),
                ("crop", "DAMAGE_CROPS"),
            ]:
                amount, status = parse_damage(row[column])
                group[field][status] += 1
                if amount is not None:
                    group[field]["known_cents"] += amount
                trace[field] = {"raw": row[column], "status": status, "cents": amount}
                if field == "property":
                    if amount is None:
                        states[state]["property_unknown"] += 1
                        states[state]["missing_event_ids"].append(ident)
                    else:
                        states[state]["known_property_cents"] += amount
            selected.append(trace)
    ordered_groups = [groups[k] for k in sorted(groups)]
    labels = [g["native_group"] for g in ordered_groups]
    if len(labels) != len(set(labels)) or any(len(x) > 80 for x in labels):
        raise ValueError("native group mapping collision")
    if len(ordered_groups) > 1000 or any(
        g["records"] > 1000000 for g in ordered_groups
    ):
        raise ValueError("native count route cap")
    native = "group,amount\n" + "".join(
        f"{g['native_group']},{g['records']}\n" for g in ordered_groups
    )
    ordered_states = [states[k] for k in sorted(states)]
    counterexample = None
    for a in ordered_states:
        if not a["property_unknown"]:
            continue
        eligible = [
            b
            for b in ordered_states
            if b["known_property_cents"] > a["known_property_cents"]
        ]
        if not eligible:
            continue
        b = min(eligible, key=lambda x: (x["known_property_cents"], x["state"]))
        gap = b["known_property_cents"] - a["known_property_cents"]
        counterexample = {
            "state_A": a["state"],
            "state_B": b["state"],
            "actual_unknown_event_id": sorted(a["missing_event_ids"], key=int)[0],
            "A_known_property_cents": a["known_property_cents"],
            "B_known_property_cents": b["known_property_cents"],
            "completion_0": "All unknown amounts zero: A has smaller recorded-plus-completed sum than B",
            "completion_1_unknown_A_cents": gap + 100,
            "completion_1_A_total_cents": a["known_property_cents"] + gap + 100,
            "completion_1_B_total_cents": b["known_property_cents"],
            "is_imputation_or_bound": False,
            "meaning": "A logical sensitivity witness, not an estimate or claim of plausibility; source supplies no upper bound for the blank field",
        }
        break
    summary = {
        "source_rows": raw_count,
        "selected_records": len(selected),
        "groups": len(ordered_groups),
        "states": len(ordered_states),
        "property_unknown_records": sum(
            g["property"]["missing"] + g["property"]["invalid"] for g in ordered_groups
        ),
        "crop_unknown_records": sum(
            g["crop"]["missing"] + g["crop"]["invalid"] for g in ordered_groups
        ),
        "geography_counts": {
            c: sum(g["geography"][c] for g in ordered_groups) for c in ["C", "Z", "M"]
        },
        "native_count_csv_sha256": hashlib.sha256(native.encode()).hexdigest(),
    }
    report = {
        "schema": "agialpha/noaa-flood-readiness/v1",
        "task_sha256": hashlib.sha256(canonical(task)).hexdigest(),
        "source": {
            k: task[k]
            for k in ["source_filename", "source_sha256", "source_url", "year"]
        },
        "filters": {"event_types": EVENT_TYPES, "policy": POLICY},
        "summary": summary,
        "groups": ordered_groups,
        "states": ordered_states,
        "ranking_counterexample": counterexample,
        "decision": {
            "economic_risk_or_resource_allocation_ranking_qualified": False,
            "missing_property_completion_ranking_identified": summary[
                "property_unknown_records"
            ]
            == 0,
            "reason": "Reported nominal estimates are not true or exposure-normalized economic risk; unknown fields have no supplied upper bound; counties and forecast zones remain distinct",
            "useful_output": "Historical source-record counts, known reported sums and explicit data-readiness/refusal evidence only",
        },
        "amount_unit": "nominal_estimate_USD_cents; encoding precision is not measurement accuracy",
        "native_amount_unit": "event_record_count; not currency, exposure-normalized frequency or settlement amount",
    }
    return report, native, selected


def write_outputs(task: dict[str, Any], destination: Path) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=False)
    report, native, trace = build_report(task)
    (destination / "task.json").write_bytes(canonical(task) + b"\n")
    (destination / "readiness-report.json").write_bytes(canonical(report) + b"\n")
    (destination / "native-counts.csv").write_text(native)
    with (destination / "selected-record-trace.jsonl").open("x") as f:
        for row in trace:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    return report
