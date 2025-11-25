# SPDX-License-Identifier: Apache-2.0
"""Benchmark the simulation runtime and token usage."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
from pathlib import Path
from statistics import quantiles
from typing import Any

import pytest
from importlib import import_module

pytest.importorskip("pytest_benchmark")


def _token_usage() -> int:
    try:
        llm_provider = import_module("alpha_factory_v1.backend.utils.llm_provider")
    except Exception:
        return 0

    total = 0
    for metric in llm_provider._CNT_TOK.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                total += int(sample.value)
    return total


@pytest.mark.benchmark(group="simulation")  # type: ignore[misc]
def test_simulation_benchmark(tmp_path: Path, benchmark: Any) -> None:
    os.environ["SIM_RESULTS_DIR"] = str(tmp_path)
    os.environ.setdefault("API_TOKEN", "test-token")
    from alpha_factory_v1.core.interface import api_server

    api = importlib.reload(api_server)
    cfg = api.SimRequest(horizon=1, pop_size=2, generations=1)

    def run() -> None:
        asyncio.run(api._background_run("bench", cfg))

    result = benchmark(run)
    stats = getattr(result, "stats", None)
    p95 = quantiles(stats["data"], n=20)[18] if stats and stats.get("data") else 0.0
    data = {"p95": p95, "tokens": _token_usage()}
    bench_dir = Path(__file__).parent / "benchmarks"
    bench_dir.mkdir(exist_ok=True)
    (bench_dir / "latest.json").write_text(json.dumps(data))
