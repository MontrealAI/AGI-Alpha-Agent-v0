# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import csv
import hashlib
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

PANEL = ("Office_Abigail", "Office_Alannah", "Office_Allyson", "Office_Amelia")
ZONE = ZoneInfo("America/Phoenix")


def number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("nonfinite probe output")
    return format(float(value), ".12g")


def calendar_blocks(values: dict[str, float]) -> dict[str, list[float]]:
    out = {}
    for day in sorted(values):
        start = datetime.fromisoformat(day)
        if start.weekday() != 0:
            continue
        week = [(start + timedelta(days=i)).date().isoformat() for i in range(7)]
        if all(d in values for d in week):
            out[day] = [values[d] for d in week]
    return out


def aligned_risk(blocks: list[dict[str, float]]) -> dict[str, Any]:
    if not blocks:
        raise ValueError("risk panel absent")
    common = sorted(set.intersection(*(set(x) for x in blocks)))
    out: dict[str, Any] = {
        "aligned_complete_calendar_weeks": common,
        "risk_pooling_qualified": False,
        "reason": "shared provenance and unvalidated loss distribution; no reserve release",
    }
    if len(common) < 2:
        out["status"] = "INSUFFICIENT_ALIGNED_BLOCKS"
        return out
    matrix = np.array([[x[day] for x in blocks] for day in common])
    covariance = np.cov(matrix, rowvar=False, ddof=1)
    out.update(
        status="EXPLORATORY_ALIGNED_ONLY",
        independence_assumption_variance_kWh2=number(np.trace(covariance)),
        observed_joint_variance_kWh2=number(np.sum(covariance)),
        joint_block_error_envelope_daily_kWh=number(max(abs(np.sum(matrix, axis=1)))),
    )
    return out


def analyze(meter_path: Path, weather_path: Path) -> dict[str, Any]:
    if meter_path.stat().st_size > 60_000_000 or weather_path.stat().st_size > 2_000_000:
        raise ValueError("registered input size cap")
    loads: dict[str, dict[str, dict[str, float]]] = {k: {} for k in PANEL}
    invalid = {k: 0 for k in PANEL}
    with meter_path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not set(PANEL) <= set(reader.fieldnames or []):
            raise ValueError("registered panel absent")
        for row in reader:
            stamp = datetime.fromisoformat(row["timestamp"]).astimezone(ZONE)
            day = stamp.date().isoformat()
            for name in PANEL:
                if not row[name]:
                    continue
                try:
                    value = float(row[name])
                    if not math.isfinite(value) or value < 0:
                        raise ValueError("invalid meter")
                    if stamp.isoformat() in loads[name].setdefault(day, {}):
                        raise ValueError("duplicate hour")
                    loads[name][day][stamp.isoformat()] = value
                except ValueError:
                    invalid[name] += 1
    temperatures: dict[str, list[float]] = {}
    with weather_path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            stamp = datetime.fromisoformat(row["timestamp"]).replace(tzinfo=ZONE)
            try:
                value = float(row["TemperatureC"])
                if math.isfinite(value) and -60 <= value <= 60:
                    temperatures.setdefault(stamp.date().isoformat(), []).append(value)
            except ValueError:
                continue
    result: dict[str, Any] = {
        "scope": "historical observed load, exploratory forecast-error diagnostic; no known treatment",
        "source_cluster_count": 1,
        "commercial_cohort_count": 0,
        "causal_savings_accepted": False,
        "fit": "OLS weekday indicators plus heating/cooling degrees at 18 Celsius; NOT full CalTRACK qualification",
        "envelope": "maximum absolute mean of complete Monday-Sunday calibration blocks; no coverage guarantee",
        "inputs": {
            p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in [meter_path, weather_path]
        },
        "sites": [],
    }
    block_errors = []
    for name in PANEL:
        days = sorted(d for d, vals in loads[name].items() if len(vals) == 24 and len(temperatures.get(d, [])) >= 20)
        site: dict[str, Any] = {
            "id": name,
            "eligible_complete_days": len(days),
            "invalid_values": invalid[name],
            "incomplete_or_weather_missing_days": len(loads[name]) - len(days),
        }
        result["sites"].append(site)
        if len(days) < 280:
            site["status"] = "INSUFFICIENT_DATA"
            continue
        y = np.array([sum(loads[name][d].values()) for d in days])
        temp = np.array([np.mean(temperatures[d]) for d in days])
        weekdays = [datetime.fromisoformat(d).weekday() for d in days]
        x = np.array(
            [[int(w == k) for k in range(7)] + [max(18 - t, 0), max(t - 18, 0)] for w, t in zip(weekdays, temp)]
        )
        beta = np.linalg.lstsq(x[:182], y[:182], rcond=None)[0]
        predicted = x @ beta
        residuals = predicted - y
        blocks = calendar_blocks({d: float(e) for d, e in zip(days[182:273], residuals[182:273])})
        if not blocks:
            site["status"] = "INSUFFICIENT_CALIBRATION_BLOCKS"
            continue
        block_means = {d: float(np.mean(v)) for d, v in blocks.items()}
        means = np.array(list(block_means.values()))
        envelope = float(max(abs(means)))
        test_mean = float(np.mean(predicted[273:]))
        if test_mean <= 0:
            site["status"] = "INVALID_PREDICTION"
            continue
        observed = []
        test_blocks = calendar_blocks({d: float(e) for d, e in zip(days[273:], residuals[273:])})
        for day in test_blocks:
            i = days.index(day)
            p, actual = predicted[i : i + 7], y[i : i + 7]
            observed.append(
                {
                    "start": days[i],
                    "end": days[i + 6],
                    "predicted_kWh": number(sum(p)),
                    "observed_kWh": number(sum(actual)),
                    "apparent_difference_kWh": number(sum(p - actual)),
                    "within_calibration_envelope": bool(abs(np.mean(p - actual)) <= envelope),
                }
            )
        site.update(
            status="EXPLORATORY",
            training=[days[0], days[181]],
            calibration=[days[182], days[272]],
            evaluation=[days[273], days[-1]],
            training_daily_kWh_mean=number(float(np.mean(y[:182]))),
            test_daily_kWh_mean=number(float(np.mean(y[273:]))),
            calibration_block_daily_error_kWh={d: number(v) for d, v in block_means.items()},
            empirical_error_envelope_daily_kWh=number(envelope),
            error_envelope_fraction_of_prediction=number(envelope / test_mean),
            test_apparent_difference_fraction=number(sum(residuals[273:]) / sum(predicted[273:])),
            injected_signal_resolvable_under_envelope={
                "3pct": envelope < 0.03 * test_mean,
                "5pct": envelope < 0.05 * test_mean,
            },
            test_weeks=observed,
            causal_acceptance=False,
        )
        block_errors.append(block_means)
    if len(block_errors) == len(PANEL):
        result["portfolio"] = aligned_risk(block_errors)
    return result
