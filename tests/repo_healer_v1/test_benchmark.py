# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pathlib

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.benchmark import run_seeded_benchmark


def test_seeded_benchmark_machine_readable() -> None:
    payload = run_seeded_benchmark(pathlib.Path("."))
    assert payload["total"] == 6
    assert isinstance(payload["results"], list)
    rows = payload["results"]
    assert {row["case"] for row in rows} == {
        "ruff_failure",
        "mypy_failure",
        "broken_import",
        "pytest_failure",
        "mkdocs_failure",
        "non_autofix_permissions",
    }
    for row in rows:
        assert row["status"] in {"HEALED", "NOT_HEALED", "SKIPPED_MISSING_VALIDATOR"}
        assert isinstance(row["reproducible"], bool)
