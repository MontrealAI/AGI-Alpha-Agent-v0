# SPDX-License-Identifier: Apache-2.0
import asyncio
import contextlib
import time

from alpha_factory_v1.backend import orchestrator
from alpha_factory_v1.core.monitoring import metrics


class DummyRunner:
    def __init__(self) -> None:
        self.task: asyncio.Task[None] | None = None
        self.paused_at: float | None = None
        self.next_ts = 0.0

    async def start(self) -> None:
        self._spawn()

    def _spawn(self) -> None:
        async def _run() -> None:
            while True:
                await asyncio.sleep(0.1)

        self.task = asyncio.create_task(_run())

    def resume(self) -> None:
        self.paused_at = None
        self.next_ts = 0.0
        if self.task is None or self.task.done():
            self._spawn()


async def _wait_for(predicate, timeout: float = 5.0) -> bool:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if predicate():
            return True
        await asyncio.sleep(0.1)
    return False


def test_regression_guard(monkeypatch) -> None:
    alerts: list[str] = []
    runner = DummyRunner()
    runners = {"aiga_evolver": runner}

    async def drive() -> float:
        await runner.start()
        guard = asyncio.create_task(orchestrator.regression_guard(runners, alerts.append, interval=0.1))
        start = time.time()
        sample_delay = 0.2
        for v in [1.0, 0.95, 0.6]:
            metrics.dgm_best_score.set(v)
            await asyncio.sleep(sample_delay)
        await _wait_for(lambda: bool(alerts))
        duration = time.time() - start
        guard.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await guard
        return duration

    dur = asyncio.run(drive())
    assert runner.task is not None and runner.task.cancelled()
    assert dur < 10
    assert alerts


def test_regression_guard_resumes(monkeypatch) -> None:
    alerts: list[str] = []
    runner = DummyRunner()
    runners = {"aiga_evolver": runner}

    async def drive() -> bool:
        await runner.start()
        guard = asyncio.create_task(orchestrator.regression_guard(runners, alerts.append, interval=0.1))
        sample_delay = 0.2
        for v in [1.0, 0.9, 0.6]:
            metrics.dgm_best_score.set(v)
            await asyncio.sleep(sample_delay)
        await asyncio.sleep(sample_delay)
        await _wait_for(lambda: any("paused" in a for a in alerts))
        assert runner.task is not None and runner.task.cancelled()
        for v in [0.8, 1.0]:
            metrics.dgm_best_score.set(v)
            await asyncio.sleep(sample_delay)
        await _wait_for(lambda: any("resumed" in a for a in alerts))
        guard.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await guard
        return runner.paused_at is None

    resumed = asyncio.run(drive())
    assert resumed
    assert any("resumed" in a for a in alerts)
