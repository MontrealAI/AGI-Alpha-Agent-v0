# SPDX-License-Identifier: Apache-2.0
import asyncio
import json
import time
from unittest import mock

from alpha_factory_v1.demos.alpha_agi_insight_v1.src import orchestrator
from alpha_factory_v1.common.utils import config

import pytest

np = pytest.importorskip("numpy")


def test_concurrent_experiments(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ARCHIVE_PATH", str(tmp_path / "arch.db"))
    monkeypatch.setenv("SOLUTION_ARCHIVE_PATH", str(tmp_path / "sol.duckdb"))
    settings = config.Settings(bus_port=0)
    with mock.patch.object(orchestrator.Orchestrator, "_init_agents", lambda self: []):
        orch = orchestrator.Orchestrator(settings)

    monkeypatch.setattr(
        "alpha_factory_v1.core.evaluators.novelty.embed",
        lambda _t: np.zeros((1, 1), dtype="float32"),
    )
    monkeypatch.setattr(
        "alpha_factory_v1.core.simulation.surrogate_fitness.aggregate",
        lambda vals, **kw: [0.0 for _ in vals],
    )
    times = []

    def dummy_run(*_a, **_kw):
        times.append(time.perf_counter())
        time.sleep(0.2)
        ind = orchestrator.mats.Individual([0.0])
        ind.score = 0.0
        return [ind]

    monkeypatch.setattr(orchestrator.mats, "run_evolution", dummy_run)

    def fn(genome: list[float]) -> tuple[float]:
        time.sleep(0.2)
        return (sum(genome),)

    async def run() -> None:
        await asyncio.gather(
            orch.evolve("a", fn, 1, experiment_id="exp1", population_size=2, generations=1),
            orch.evolve("b", fn, 1, experiment_id="exp2", population_size=2, generations=1),
        )

    asyncio.run(run())
    assert len(times) == 2
    assert abs(times[0] - times[1]) < 0.05
    assert "exp1" in orch.experiment_pops
    assert "exp2" in orch.experiment_pops
    assert orch.experiment_pops["exp1"] is not orch.experiment_pops["exp2"]

    specs = [json.loads(row[0])["experiment_id"] for row in orch.archive.conn.execute("SELECT spec FROM entries")]
    assert {"exp1", "exp2"} <= set(specs)
