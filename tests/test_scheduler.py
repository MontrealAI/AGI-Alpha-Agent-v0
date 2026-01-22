# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from unittest.mock import patch

import pydantic
import pytest

if int(pydantic.__version__.split(".", maxsplit=1)[0]) >= 2:
    pytest.skip("rocketry requires pydantic<2", allow_module_level=True)

rocketry = pytest.importorskip("rocketry")
from alpha_factory_v1.core import scheduler  # noqa: E402


@pytest.mark.asyncio
async def test_scheduler_runs_jobs(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs = [
        {"repo": "r1", "patch": "p1", "tokens": 5},
        {"repo": "r2", "patch": "p2", "tokens": 5},
    ]
    jobs_file.write_text(json.dumps(jobs))

    called = []

    def fake_improve(repo, patch, metric, log):
        called.append(repo)
        return 1.0, Path(repo)

    with patch.object(scheduler.self_improver, "improve_repo", side_effect=fake_improve):
        sch = scheduler.SelfImprovementScheduler(
            [scheduler.Job(**j) for j in jobs], tokens_quota=10, time_quota=2, interval="0.1 second"
        )
        await sch.serve()

    assert called == ["r1", "r2"]
    assert sch.tokens_used == 10


@pytest.mark.asyncio
async def test_scheduler_recycles_failures(tmp_path):
    job = scheduler.Job(repo="r", patch="p", tokens=3)
    calls = 0

    def flaky(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")
        return 1.0, Path("r")

    with patch.object(scheduler.self_improver, "improve_repo", side_effect=flaky):
        sch = scheduler.SelfImprovementScheduler([job], tokens_quota=3, time_quota=2, interval="0.1 second")
        await sch.serve()

    assert calls == 2
    assert sch.tokens_used == 3
