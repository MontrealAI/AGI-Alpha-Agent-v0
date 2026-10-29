# SPDX-License-Identifier: Apache-2.0
"""Independent pandas/Decimal audit of the source-bound NOAA readiness report."""

from __future__ import annotations

import csv
from decimal import Decimal
import gzip
import hashlib
from pathlib import Path
import re
from typing import Any

import pandas as pd

from .readiness import EVENT_TYPES, INPUTS, POLICY, canonical, validate_task


class BoundedGzip:
    """Meter actual decompressed bytes supplied to the conventional CSV reader."""

    def __init__(self, stream: Any) -> None:
        self.stream = stream
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(min(size if size >= 0 else 200_000_001, 200_000_001))
        self.bytes_read += len(data)
        if self.bytes_read > 200_000_000:
            raise ValueError("source uncompressed byte cap")
        return data


def damage_value(value: str) -> tuple[int | None, str]:
    """Interpret spellings lexically, separately from the producer's regex parser."""
    text = value.strip()
    if text == "":
        return None, "missing"
    exponent = 0
    if text[-1] in "KMB":
        exponent = {"K": 3, "M": 6, "B": 9}[text[-1]]
        text = text[:-1]
    pieces = text.split(".")
    if len(pieces) > 2 or any(not piece or any(c not in "0123456789" for c in piece) for piece in pieces):
        return None, "invalid"
    scaled = Decimal(text) * (Decimal(10) ** (exponent + 2))
    whole = scaled.to_integral_value()
    if whole != scaled:
        return None, "invalid"
    amount = int(whole)
    return amount, "reported_nonzero" if amount else "reported_zero"


def native_name(state: str, kind: str) -> str:
    return "_".join(re.findall(r"[A-Z0-9]+", state.upper())) + "__" + "_".join(re.findall(r"[A-Z0-9]+", kind.upper()))


def reconstruct(task: dict[str, Any], source: Path | None = None) -> tuple[dict[str, Any], str]:
    """Reconstruct every accepted field using a separate tabular implementation."""
    validate_task(task)
    source = source or INPUTS / task["source_filename"]
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 25_000_000:
        raise ValueError("bounded regular source")
    with source.open("rb") as f:
        actual_sha = hashlib.file_digest(f, "sha256").hexdigest()
    if actual_sha != task["source_sha256"]:
        raise ValueError("source bytes changed")
    required = ["EVENT_ID", "STATE", "YEAR", "EVENT_TYPE", "CZ_TYPE", "DAMAGE_PROPERTY", "DAMAGE_CROPS"]
    with gzip.open(source, "rt", encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f), None)
    if header is None or len(set(header)) != len(header) or not set(required) <= set(header):
        raise ValueError("source columns")
    selected_frames = []
    seen_ids: set[str] = set()
    raw_rows = 0
    with gzip.open(source, "rb") as f:
        for frame in pd.read_csv(
            BoundedGzip(f), dtype=str, keep_default_na=False, chunksize=10000, encoding="utf-8-sig"
        ):
            raw_rows += len(frame)
            if raw_rows > 200000:
                raise ValueError("source row cap")
            if not frame["YEAR"].eq(str(task["year"])).all():
                raise ValueError("source year mismatch")
            identifiers = frame["EVENT_ID"].tolist()
            if any(not i.isdigit() for i in identifiers) or len(set(identifiers)) != len(identifiers):
                raise ValueError("duplicate or invalid event ID")
            if seen_ids.intersection(identifiers):
                raise ValueError("duplicate or invalid event ID")
            seen_ids.update(identifiers)
            selected_frames.append(frame.loc[frame["EVENT_TYPE"].isin(EVENT_TYPES), required].copy())
    data = pd.concat(selected_frames, ignore_index=True) if selected_frames else pd.DataFrame(columns=required)
    if (data["STATE"] == "").any() or not data["CZ_TYPE"].isin(["C", "Z", "M"]).all():
        raise ValueError("geography category")
    for column, label in [("DAMAGE_PROPERTY", "property"), ("DAMAGE_CROPS", "crop")]:
        parsed = [damage_value(raw) for raw in data[column].tolist()]
        data[label + "_amount"] = pd.Series([v for v, _ in parsed], dtype=object)
        data[label + "_status"] = [s for _, s in parsed]
    groups = []
    for (state, kind), frame in data.groupby(["STATE", "EVENT_TYPE"], sort=True):
        item: dict[str, Any] = {
            "state": state,
            "event_type": kind,
            "native_group": native_name(state, kind),
            "records": len(frame),
            "geography": {v: int(frame["CZ_TYPE"].eq(v).sum()) for v in ["C", "Z", "M"]},
        }
        for label in ["property", "crop"]:
            amounts = frame[label + "_amount"].tolist()
            statuses = frame[label + "_status"]
            item[label] = {
                "known_cents": sum(v for v in amounts if v is not None),
                **{
                    status: int(statuses.eq(status).sum())
                    for status in ["missing", "invalid", "reported_zero", "reported_nonzero"]
                },
            }
        groups.append(item)
    labels = [g["native_group"] for g in groups]
    if len(labels) != len(set(labels)) or any(len(s) > 80 for s in labels):
        raise ValueError("native group mapping collision")
    if len(groups) > 1000 or any(g["records"] > 1000000 for g in groups):
        raise ValueError("native count route cap")
    native = "group,amount\n" + "".join(f"{g['native_group']},{g['records']}\n" for g in groups)
    states = []
    for state, frame in data.groupby("STATE", sort=True):
        unknown = frame["property_status"].isin(["missing", "invalid"])
        states.append(
            {
                "state": state,
                "records": len(frame),
                "known_property_cents": sum(v for v in frame["property_amount"].tolist() if v is not None),
                "property_unknown": int(unknown.sum()),
                "missing_event_ids": frame.loc[unknown, "EVENT_ID"].tolist(),
            }
        )
    counterexample = None
    for a in states:
        if a["property_unknown"] == 0:
            continue
        bigger = sorted(
            (b for b in states if b["known_property_cents"] > a["known_property_cents"]),
            key=lambda b: (b["known_property_cents"], b["state"]),
        )
        if not bigger:
            continue
        b = bigger[0]
        added = b["known_property_cents"] - a["known_property_cents"] + 100
        counterexample = {
            "state_A": a["state"],
            "state_B": b["state"],
            "actual_unknown_event_id": min(a["missing_event_ids"], key=int),
            "A_known_property_cents": a["known_property_cents"],
            "B_known_property_cents": b["known_property_cents"],
            "completion_0": "All unknown amounts zero: A has smaller recorded-plus-completed sum than B",
            "completion_1_unknown_A_cents": added,
            "completion_1_A_total_cents": a["known_property_cents"] + added,
            "completion_1_B_total_cents": b["known_property_cents"],
            "is_imputation_or_bound": False,
            "meaning": "A logical sensitivity witness, not an estimate or claim of plausibility; source supplies no upper bound for the blank field",
        }
        break
    summary = {
        "source_rows": raw_rows,
        "selected_records": len(data),
        "groups": len(groups),
        "states": len(states),
        "property_unknown_records": int(data["property_status"].isin(["missing", "invalid"]).sum()),
        "crop_unknown_records": int(data["crop_status"].isin(["missing", "invalid"]).sum()),
        "geography_counts": {v: int(data["CZ_TYPE"].eq(v).sum()) for v in ["C", "Z", "M"]},
        "native_count_csv_sha256": hashlib.sha256(native.encode()).hexdigest(),
    }
    report = {
        "schema": "agialpha/noaa-flood-readiness/v1",
        "task_sha256": hashlib.sha256(canonical(task)).hexdigest(),
        "source": {key: task[key] for key in ["source_filename", "source_sha256", "source_url", "year"]},
        "filters": {"event_types": EVENT_TYPES, "policy": POLICY},
        "summary": summary,
        "groups": groups,
        "states": states,
        "ranking_counterexample": counterexample,
        "decision": {
            "economic_risk_or_resource_allocation_ranking_qualified": False,
            "missing_property_completion_ranking_identified": summary["property_unknown_records"] == 0,
            "reason": "Reported nominal estimates are not true or exposure-normalized economic risk; unknown fields have no supplied upper bound; counties and forecast zones remain distinct",
            "useful_output": "Historical source-record counts, known reported sums and explicit data-readiness/refusal evidence only",
        },
        "amount_unit": "nominal_estimate_USD_cents; encoding precision is not measurement accuracy",
        "native_amount_unit": "event_record_count; not currency, exposure-normalized frequency or settlement amount",
    }
    return report, native


def verify(
    task: dict[str, Any], artifact: Any, source: Path | None = None, native_csv: str | None = None
) -> dict[str, Any]:
    """Accept only a complete source-recomputed report and optional exact native data."""
    try:
        actual = canonical(artifact)
        if len(actual) > 200000:
            raise ValueError("report byte cap")
        expected, native = reconstruct(task, source)
        if actual != canonical(expected):
            raise ValueError("report differs from independent source reconstruction")
        if native_csv is not None and native_csv != native:
            raise ValueError("native CSV differs from independent source reconstruction")
        return {
            "accepted": True,
            "decisive": True,
            "reason": "Complete exact source/selection/sum/missingness/geography/counterexample match",
            "checker": "independent pandas and Decimal reconstruction",
            "risk_ranking_qualified": False,
        }
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as error:
        return {"accepted": False, "decisive": False, "reason": str(error)}
