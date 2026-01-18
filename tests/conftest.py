# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os

import pytest


os.environ.setdefault("PYTEST_NET_OFF", "1")


def pytest_configure() -> None:
    try:
        from hypothesis import HealthCheck, settings
    except Exception:
        return

    profile_name = os.getenv("HYPOTHESIS_PROFILE", "alpha_factory")
    try:
        settings.register_profile(
            profile_name,
            suppress_health_check=[
                HealthCheck.filter_too_much,
                HealthCheck.function_scoped_fixture,
            ],
        )
    except ValueError:
        pass
    settings.load_profile(profile_name)


@pytest.fixture
def non_network(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PYTEST_NET_OFF", "1")
