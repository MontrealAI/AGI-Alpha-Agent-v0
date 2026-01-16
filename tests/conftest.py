# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for Hypothesis defaults."""

from __future__ import annotations

try:
    from hypothesis import HealthCheck, settings
except Exception:  # pragma: no cover - optional dependency
    settings = None
else:
    settings.register_profile(
        "ci",
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.function_scoped_fixture],
    )
    settings.load_profile("ci")


import pytest


@pytest.fixture
def non_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure network access is disabled in tests that require offline mode."""
    monkeypatch.setenv("PYTEST_NET_OFF", "1")


@pytest.fixture
def scenario(request: pytest.FixtureRequest):
    from alpha_factory_v1.core.simulation import replay

    name = str(request.param)
    if name.startswith("scenario_"):
        name = name[len("scenario_") :]
    return replay.load_scenario(name)


@pytest.fixture
def scenario_1994_web():
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("1994_web")


@pytest.fixture
def scenario_2001_genome():
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("2001_genome")


@pytest.fixture
def scenario_2008_mobile():
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("2008_mobile")


@pytest.fixture
def scenario_2012_dl():
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("2012_dl")


@pytest.fixture
def scenario_2020_mrna():
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("2020_mrna")
