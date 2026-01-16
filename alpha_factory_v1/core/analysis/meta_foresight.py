# SPDX-License-Identifier: Apache-2.0
"""Aggregate replay metrics and detect anomalies."""

from __future__ import annotations

import csv
import statistics
from pathlib import Path
from typing import Iterable, Dict, List

try:
    from rocketry import Rocketry
    from rocketry.conds import every
except Exception:  # pragma: no cover - optional
    Rocketry = None  # type: ignore
    every = None  # type: ignore


_METRICS = ["f1", "auroc", "lead_time"]


def load_metrics(csv_path: str | Path = "replay_metrics.csv") -> List[Dict[str, float]]:
    """Return metric rows from ``csv_path``."""
    path = Path(csv_path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        data = []
        for row in reader:
            entry = {k: float(row[k]) for k in _METRICS if k in row}
            entry["scenario"] = row.get("scenario", "")
            data.append(entry)
        return data


def aggregate_stats(rows: Iterable[Dict[str, float]]) -> Dict[str, float]:
    """Return mean and stdev for each metric in ``rows``."""
    stats: Dict[str, float] = {}
    metrics: Dict[str, List[float]] = {m: [] for m in _METRICS}
    for row in rows:
        for m in _METRICS:
            if m in row:
                metrics[m].append(row[m])
    for m, vals in metrics.items():
        if vals:
            stats[f"{m}_mean"] = statistics.mean(vals)
            stats[f"{m}_stdev"] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return stats


def detect_anomalies(rows: Iterable[Dict[str, float]], *, z: float = 2.0) -> List[Dict[str, float]]:
    """Return rows with any metric deviating more than ``z`` standard deviations."""
    stats = aggregate_stats(rows)
    anomalies = []
    for row in rows:
        for m in _METRICS:
            mean = stats.get(f"{m}_mean", 0.0)
            st = stats.get(f"{m}_stdev", 0.0)
            if st and abs(row[m] - mean) > z * st:
                anomalies.append(row)
                break
    return anomalies


def weekly_report(csv_path: str | Path = "replay_metrics.csv") -> str:
    """Generate a plain-text weekly report and return it."""
    rows = load_metrics(csv_path)
    stats = aggregate_stats(rows)
    anomalies = detect_anomalies(rows)
    lines = ["Weekly Meta Foresight Report"]
    for m in _METRICS:
        mean = stats.get(f"{m}_mean", float("nan"))
        st = stats.get(f"{m}_stdev", float("nan"))
        lines.append(f"{m}: mean={mean:.3f} stdev={st:.3f}")
    lines.append(f"anomalies_detected={len(anomalies)}")
    return "\n".join(lines)


def create_weekly_scheduler(csv_path: str | Path = "replay_metrics.csv") -> Rocketry | None:
    """Return a ``Rocketry`` scheduler that emails the weekly report."""
    if Rocketry is None or every is None:
        return None
    try:
        app = Rocketry(execution="async")
    except TypeError:
        app = Rocketry()

    @app.task(every("1 week"))
    def _report() -> None:  # pragma: no cover - scheduler callback
        weekly_report(csv_path)

    return app


__all__ = [
    "load_metrics",
    "aggregate_stats",
    "detect_anomalies",
    "weekly_report",
    "create_weekly_scheduler",
]
