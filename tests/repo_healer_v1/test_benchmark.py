# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pathlib

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.benchmark import run_seeded_benchmark


def test_seeded_benchmark_machine_readable() -> None:
    payload = run_seeded_benchmark(pathlib.Path("."))
    assert payload["total"] == 6
    assert isinstance(payload["results"], list)
