# SPDX-License-Identifier: Apache-2.0

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.bench_targets.import_case import ping


def test_ping() -> None:
    assert ping() == "pong"
