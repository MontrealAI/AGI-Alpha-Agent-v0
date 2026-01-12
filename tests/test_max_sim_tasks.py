# SPDX-License-Identifier: Apache-2.0
import asyncio
import importlib
from pathlib import Path

import pytest

pytest.importorskip("fastapi")


def test_max_sim_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIM_RESULTS_DIR", str(tmp_path))
    monkeypatch.setenv("MAX_SIM_TASKS", "1")
    from alpha_factory_v1.core.interface import api_server as api

    api = importlib.reload(api)

    cfg = api.SimRequest(horizon=1, pop_size=2, generations=1)
    counter = {"current": 0, "max": 0}

    async def stub(sim_id: str, _cfg: api.SimRequest) -> None:
        counter["current"] += 1
        counter["max"] = max(counter["max"], counter["current"])
        await asyncio.sleep(0.05)
        counter["current"] -= 1

    monkeypatch.setattr(api, "_background_run", stub)

    async def _run_all() -> None:
        await asyncio.gather(api._bounded_run("a", cfg), api._bounded_run("b", cfg))

    asyncio.run(_run_all())

    assert counter["max"] == 1
