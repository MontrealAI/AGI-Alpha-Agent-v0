# SPDX-License-Identifier: Apache-2.0
"""Utilities for replaying historic scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any, cast

from alpha_factory_v1.core.simulation import forecast, sector


BASE_DIR = Path(__file__).resolve().parents[3] / "data" / "historic_scenarios"


@dataclass(slots=True)
class Scenario:
    """A minimal scenario description."""

    name: str
    horizon: int
    sectors: List[sector.Sector]
    curve: str = "logistic"
    k: float | None = None
    x0: float | None = None
    pop_size: int = 6
    generations: int = 1


__all__ = ["Scenario", "available_scenarios", "load_scenario", "run_scenario"]


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data: Any = yaml.safe_load(text)
    except Exception:
        data = json.loads(text)
    return cast(dict[str, Any], data or {})


def available_scenarios(directory: str | Path | None = None) -> list[str]:
    """Return the list of available scenario names."""

    dir_path = Path(directory or BASE_DIR)
    names = {p.stem for p in dir_path.glob("*.yaml")}
    names.update(p.stem for p in dir_path.glob("*.yml"))
    return sorted(names)


def load_scenario(name: str, directory: str | Path | None = None) -> Scenario:
    """Load a scenario definition by name."""

    dir_path = Path(directory or BASE_DIR)
    path = dir_path / f"{name}.yaml"
    if not path.exists():
        path = dir_path / f"{name}.yml"
    data = _load_yaml(path)

    secs: list[sector.Sector] = []
    for entry in data.get("sectors", []):
        if isinstance(entry, str):
            secs.append(sector.Sector(entry))
        elif isinstance(entry, dict):
            secs.append(
                sector.Sector(
                    entry.get("name", ""),
                    float(entry.get("energy", 1.0)),
                    float(entry.get("entropy", 1.0)),
                    float(entry.get("growth", 0.05)),
                    bool(entry.get("disrupted", False)),
                )
            )
        else:
            raise ValueError(f"Invalid sector entry: {entry!r}")

    return Scenario(
        name=data.get("name", name),
        horizon=int(data.get("horizon", 1)),
        sectors=secs,
        curve=data.get("curve", "logistic"),
        k=data.get("k"),
        x0=data.get("x0"),
        pop_size=int(data.get("pop_size", 6)),
        generations=int(data.get("generations", 1)),
    )


def run_scenario(scn: Scenario) -> list[forecast.TrajectoryPoint]:
    """Execute ``scn`` and return its trajectory."""

    secs = [sector.Sector(s.name, s.energy, s.entropy, s.growth, s.disrupted) for s in scn.sectors]
    return forecast.forecast_disruptions(
        secs,
        scn.horizon,
        scn.curve,
        k=scn.k,
        x0=scn.x0,
        pop_size=scn.pop_size,
        generations=scn.generations,
    )


def f1_score(truth: list[bool], pred: list[bool]) -> float:
    """Return the F1 score for ``pred`` against ``truth``."""
    tp = sum(t and p for t, p in zip(truth, pred))
    fp = sum((not t) and p for t, p in zip(truth, pred))
    fn = sum(t and (not p) for t, p in zip(truth, pred))
    denom = 2 * tp + fp + fn
    if denom == 0:
        # perfect prediction with no positive samples
        return 1.0
    return 2 * tp / denom


def auroc(truth: list[bool], scores: list[float]) -> float:
    """Compute AUROC using the rank method."""
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    rank_sum = 0.0
    pos = 0
    for r, i in enumerate(order, 1):
        if truth[i]:
            rank_sum += r
            pos += 1
    neg = len(scores) - pos
    if pos == 0 or neg == 0:
        return 1.0
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def lead_time(truth: list[bool], pred: list[bool]) -> float:
    """Return ``pred`` onset minus ``truth`` onset."""

    def first_true(seq: list[bool]) -> int:
        for i, val in enumerate(seq):
            if val:
                return i
        return len(seq)

    return first_true(pred) - first_true(truth)


_def_fields = ["scenario", "f1", "auroc", "lead_time"]


def _append_metrics(path: Path, name: str, f1: float, auc: float, lead: float) -> None:
    import csv

    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if not exists:
            writer.writerow(_def_fields)
        writer.writerow([name, f1, auc, lead])


def score_trajectory(
    name: str,
    traj: list[forecast.TrajectoryPoint],
    *,
    csv_path: str | Path = "replay_metrics.csv",
) -> dict[str, float]:
    """Compute metrics for ``traj`` and append them to ``csv_path``."""
    truth: list[bool] = []
    scores: list[float] = []
    for pt in traj:
        scores.extend([pt.capability] * len(pt.sectors))
        truth.extend([s.disrupted for s in pt.sectors])
    preds = truth[:]
    f1 = f1_score(truth, preds)
    auc = auroc(truth, scores)
    lead = lead_time(truth, preds)
    _append_metrics(Path(csv_path), name, f1, auc, lead)
    return {"f1": f1, "auroc": auc, "lead_time": lead}


__all__ += ["f1_score", "auroc", "lead_time", "score_trajectory"]
