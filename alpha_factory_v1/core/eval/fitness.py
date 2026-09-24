# SPDX-License-Identifier: Apache-2.0
"""Benchmark fitness calculation utilities."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable, Mapping, Any
import logging
from pathlib import Path
import math


__all__ = ["compute_fitness", "evaluate_agent", "simulate_fitness", "CurriculumSwitcher"]


def compute_fitness(results: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    """Compute dataset pass rate and average runtime.

    Parameters
    ----------
    results:
        Iterable of benchmark result dictionaries. Each dictionary must contain
        ``task_id`` identifying the dataset (``<dataset>/task_xxx``), ``pass``
        indicating success and ``time_ms`` runtime in milliseconds.

    Returns
    -------
    dict
        Mapping from dataset name to a metrics dictionary with ``pass_rate`` and
        ``avg_ms`` keys.
    """

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for entry in results:
        try:
            task_id = entry["task_id"]
        except KeyError as exc:  # pragma: no cover - guard against bad input
            raise KeyError("task_id missing from result") from exc
        dataset = str(task_id).split("/")[0]
        if not dataset or not isinstance(entry.get("pass"), bool):
            raise ValueError("benchmark results require a dataset and a boolean pass field")
        duration = entry.get("time_ms")
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration < 0
        ):
            raise ValueError("benchmark time_ms must be finite and nonnegative")
        grouped[dataset].append(entry)

    metrics: dict[str, dict[str, float]] = {}
    for dataset, items in grouped.items():
        total = len(items)
        passed = sum(1 for i in items if i.get("pass"))
        avg_ms = sum(float(i["time_ms"]) for i in items) / total if total else 0.0
        metrics[dataset] = {"pass_rate": passed / total if total else 0.0, "avg_ms": avg_ms}

    return metrics


def simulate_fitness(code: str) -> dict[str, float]:
    """Preserve the original hash-derived DEMONSTRATION scores, not a benchmark."""

    import random
    import time
    from hashlib import blake2b

    start = time.perf_counter()
    h = blake2b(code.encode(), digest_size=8).digest()
    simhash = int.from_bytes(h, "big")
    rng = random.Random(simhash & 0xFFFF)
    accuracy = 0.5 + rng.random() * 0.5
    latency_ms = (time.perf_counter() - start) * 1000
    return {
        "accuracy": accuracy,
        "novelty_simhash": float(simhash),
        "latency_ms": latency_ms,
    }


def evaluate_agent(code: str, cases: Iterable[Mapping[str, Any]] | None = None) -> dict[str, float]:
    """Execute ``solve(*args)`` in isolation and score outputs outside the sandbox.

    Cases contain ``args`` (a JSON list) and ``expected`` (a JSON value). Expected
    answers are never mounted into the candidate container. This measures the
    supplied cases only; use separate held-out cases for promotion decisions.
    """
    import json
    import tempfile
    import time
    from hashlib import blake2b
    from alpha_factory_v1.core.utils.secure_run import secure_run

    if cases is None:
        raise ValueError("real evaluation requires benchmark cases; use simulate_fitness for the legacy demonstration")
    items = list(cases)
    if not 1 <= len(items) <= 100 or len(code.encode()) > 100000:
        raise ValueError("benchmark requires 1–100 cases and at most 100 KiB of source")
    if any(set(item) != {"args", "expected"} or not isinstance(item["args"], list) for item in items):
        raise ValueError("each case needs args and expected")
    encoded = json.dumps([item["args"] for item in items], allow_nan=False)
    if len(encoded.encode()) > 100000:
        raise ValueError("benchmark inputs exceed 100 KiB")
    harness = (
        "import json,sys,contextlib,io\n"
        "source=open(sys.argv[1]).read()\n"
        "inputs=json.load(open(sys.argv[2]))\n"
        "namespace={}\n"
        "with contextlib.redirect_stdout(io.StringIO()):\n"
        " exec(compile(source,'candidate.py','exec'),namespace)\n"
        " outputs=[namespace['solve'](*args) for args in inputs]\n"
        "print(json.dumps(outputs,allow_nan=False))\n"
    )
    with tempfile.TemporaryDirectory(prefix="alpha-benchmark-") as temporary:
        folder = Path(temporary)
        for name, content in (("candidate.py", code), ("inputs.json", encoded), ("runner.py", harness)):
            (folder / name).write_text(content)
        started = time.perf_counter()
        process = secure_run(
            ["python3", str(folder / "runner.py"), str(folder / "candidate.py"), str(folder / "inputs.json")]
        )
        elapsed = (time.perf_counter() - started) * 1000
    if process.returncode:
        raise ValueError("candidate failed isolated execution")
    outputs = json.loads(process.stdout)
    if not isinstance(outputs, list) or len(outputs) != len(items):
        raise ValueError("candidate returned an invalid output vector")
    passed = sum(
        json.dumps(actual, sort_keys=True, allow_nan=False)
        == json.dumps(item["expected"], sort_keys=True, allow_nan=False)
        for actual, item in zip(outputs, items)
    )
    fingerprint = int.from_bytes(blake2b(code.encode(), digest_size=6).digest(), "big")
    return {"accuracy": passed / len(items), "novelty_simhash": float(fingerprint), "latency_ms": elapsed}


class CurriculumSwitcher:
    """Manage dataset curriculum based on rolling pass rate."""

    MINI = "swe_mini"
    FULL = "swebench_verified_mini"
    POLYGLOT = "polyglot_lite"

    def __init__(self, db_path: str | Path, window: int = 10) -> None:
        from alpha_factory_v1.core.archive.db import ArchiveDB

        self.db = ArchiveDB(db_path)
        self.window = window
        self.history: deque[float] = deque(maxlen=window)
        self._dataset = self.db.get_state("dataset", self.MINI)
        self._log = logging.getLogger(__name__)
        self._log.info("current dataset: %s", self._dataset)

    @property
    def dataset(self) -> str:
        """Return the active dataset name."""

        return self._dataset

    def update(self, metrics: Mapping[str, Mapping[str, float]]) -> None:
        """Update rolling stats and switch datasets when thresholds pass."""

        rate = metrics.get(self._dataset, {}).get("pass_rate")
        if rate is not None:
            self.history.append(rate)
        if not self.history:
            return
        avg = sum(self.history) / len(self.history)

        if self._dataset == self.MINI and avg >= 0.40:
            self._dataset = self.FULL
            self.history.clear()
            self.db.set_state("dataset", self._dataset)
            self._log.info("switched dataset to %s", self._dataset)
        elif self._dataset == self.FULL and avg >= 0.60:
            self._dataset = self.POLYGLOT
            self.history.clear()
            self.db.set_state("dataset", self._dataset)
            self._log.info("switched dataset to %s", self._dataset)
