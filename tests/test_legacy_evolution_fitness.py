# SPDX-License-Identifier: Apache-2.0
"""Regression checks for slotted fitness records; no candidate code executes."""

import csv
import math
from pathlib import Path

from alpha_factory_v1.demos.meta_agentic_agi_v3.meta_agentic_search.archive import (
    Candidate,
    Fitness,
    crowding_distance,
    load_jsonl,
    save_csv,
    save_jsonl,
)


def candidate(index: int) -> Candidate:
    """Create a tradeoff record, without generated source or provider access."""
    value = index / 8
    return Candidate(index, 1, "fixture", "", Fitness(value, value, value, value, value))


def test_nine_slotted_records_receive_crowding_distances() -> None:
    front = [candidate(index) for index in range(9)]
    assert not hasattr(front[0].fitness, "__dict__")
    crowding_distance(front)
    assert front[0].fitness.crowd == math.inf
    assert front[-1].fitness.crowd == math.inf
    assert all(record.fitness.crowd == 1.25 for record in front[1:-1])


def test_empty_and_singleton_fronts() -> None:
    crowding_distance([])
    front = [candidate(1)]
    crowding_distance(front)
    assert front[0].fitness.crowd == math.inf


def test_csv_exports_objectives_not_ranking_metadata(tmp_path: Path) -> None:
    front = [candidate(index) for index in range(9)]
    crowding_distance(front)
    path = tmp_path / "lineage.csv"
    save_csv(front, path)
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        assert reader.fieldnames == ["id", "gen", "ts", "code", "accuracy", "latency", "cost", "carbon", "novelty"]
    assert len(rows) == 9
    assert rows[-1]["accuracy"] == "1.0"


def test_csv_empty_front_has_stable_header(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    save_csv([], path)
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        assert list(reader) == []
        assert reader.fieldnames is not None and "accuracy" in reader.fieldnames


def test_jsonl_round_trip_keeps_runtime_metadata(tmp_path: Path) -> None:
    front = [candidate(1)]
    front[0].fitness.rank = 2
    front[0].fitness.crowd = 0.75
    path = tmp_path / "nested" / "lineage.jsonl"
    save_jsonl(front, path)
    restored = load_jsonl(path)
    assert restored == front
    assert restored[0].fitness.rank == 2
    assert restored[0].fitness.crowd == 0.75
