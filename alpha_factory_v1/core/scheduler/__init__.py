# SPDX-License-Identifier: Apache-2.0
"""Async self-improvement scheduler using Rocketry."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Set

import random

from rocketry import Rocketry
from rocketry.conds import every

from alpha_factory_v1.core.self_evolution import self_improver
from alpha_factory_v1.core.monitoring import metrics


@dataclass(slots=True)
class Job:
    """Definition of a self-improvement job."""

    repo: str
    patch: str
    metric: str = "metric.txt"
    log: str = "improver_log.json"
    tokens: int = 0


class SelfImprovementScheduler:
    """Launch self-improvement jobs with quotas and failure recycling."""

    def __init__(
        self,
        jobs: Iterable[Job],
        *,
        tokens_quota: int | None = None,
        time_quota: float | None = None,
        interval: str = "1 second",
        max_workers: int = 1,
    ) -> None:
        self.queue: asyncio.Queue[Job] = asyncio.Queue()
        self._initial_jobs = list(jobs)
        for job in self._initial_jobs:
            self.queue.put_nowait(job)
        self._results: Dict[Job, float] = {}
        self._stats: Dict[Job, tuple[int, int]] = {}
        self._active_jobs: list[Job] = []
        self._first_round_done = False
        self.tokens_quota = tokens_quota
        self.time_quota = time_quota
        self.max_workers = max_workers
        self.tokens_used = 0
        self.start_time = 0.0
        self.running: Set[asyncio.Task[None]] = set()
        self._interval_seconds = _parse_interval(interval)
        self._use_rocketry = False
        self._finish: Callable[[], None] = lambda: None
        try:
            self.app = Rocketry(execution="async")
        except TypeError:
            self.app = Rocketry()

        if hasattr(self.app, "task"):
            self._use_rocketry = True
            self._finish = self.app.session.finish

            @self.app.task(every(interval))
            async def _spawn():  # pragma: no cover - Rocketry callback
                await self._spawn_jobs()

    async def _spawn_jobs(self) -> None:
        """Spawn new worker tasks until quotas or limits are hit."""
        if self.time_quota and time.time() - self.start_time >= self.time_quota:
            self._finish()
            return
        if self.tokens_quota is not None and self.tokens_used >= self.tokens_quota:
            self._finish()
            return
        # schedule initial evaluation or bandit-selected jobs
        while len(self.running) < self.max_workers:
            if not self._first_round_done:
                if self.queue.empty():
                    break
                job = await self.queue.get()
            else:
                if not self._active_jobs:
                    self._finish()
                    break
                job = self._select_job()
            task = asyncio.create_task(self._run_job(job))
            self.running.add(task)
            task.add_done_callback(self.running.discard)

    async def _run_job(self, job: Job) -> None:
        start = time.perf_counter()
        try:
            delta, _ = await asyncio.to_thread(
                self_improver.improve_repo,
                job.repo,
                job.patch,
                job.metric,
                job.log,
            )
            self.tokens_used += job.tokens
            gpu_hours = (time.perf_counter() - start) / 3600
            metrics.dgm_gpu_hours_total.inc(gpu_hours)
            if delta > 0:
                metrics.dgm_fitness_gain_total.inc(delta)
            if metrics.dgm_fitness_gain_total._value.get() > 0:
                ratio = metrics.dgm_gpu_hours_total._value.get() / metrics.dgm_fitness_gain_total._value.get()
                metrics.dgm_gpu_hours_per_gain.set(ratio)
            if not self._first_round_done:
                self._results[job] = delta
            else:
                suc, fail = self._stats.get(job, (0, 0))
                if delta > 0:
                    suc += 1
                else:
                    fail += 1
                self._stats[job] = (suc, fail)
        except Exception:  # noqa: BLE001
            await self.queue.put(job)
        if not self._first_round_done and len(self._results) == len(self._initial_jobs):
            self._finalize_first_round()

    def _select_job(self) -> Job:
        samples: Dict[Job, float] = {}
        for job in self._active_jobs:
            suc, fail = self._stats.get(job, (1, 1))
            samples[job] = random.betavariate(suc, fail)
        best = max(samples, key=samples.get)
        return best

    def _finalize_first_round(self) -> None:
        deltas = list(self._results.values())
        if not deltas:
            self._first_round_done = True
            return
        threshold = sorted(deltas)[len(deltas) // 4]
        for job, delta in self._results.items():
            if delta > threshold:
                self._active_jobs.append(job)
                self._stats[job] = (1 if delta > 0 else 0, 0 if delta > 0 else 1)
        self._first_round_done = True

    async def serve(self) -> None:
        """Run the scheduler until quotas are exhausted or queue is empty."""
        self.start_time = time.time()
        if self._use_rocketry:
            await self.app.serve()
            if (
                not self._results
                and not self.running
                and self.queue.qsize() == len(self._initial_jobs)
                and not self._first_round_done
            ):
                await self._serve_fallback()
            # wait for running tasks to finish
            if self.running:
                await asyncio.gather(*self.running, return_exceptions=True)
            return
        await self._serve_fallback()

    async def _serve_fallback(self) -> None:
        while True:
            await self._spawn_jobs()
            if self.running:
                await asyncio.gather(*self.running, return_exceptions=True)
            if (self.tokens_quota is not None and self.tokens_used >= self.tokens_quota) or (
                self.time_quota and time.time() - self.start_time >= self.time_quota
            ):
                break
            if self._first_round_done and not self._active_jobs and self.queue.empty():
                break
            await asyncio.sleep(self._interval_seconds)


__all__ = ["Job", "SelfImprovementScheduler"]


def _parse_interval(interval: str) -> float:
    """Parse a simple '<float> second' interval string."""
    try:
        return float(interval.split()[0])
    except (ValueError, IndexError):
        return 1.0
