# SPDX-License-Identifier: Apache-2.0
"""Cross-version forecast arithmetic; exact wire vectors remain mandatory."""
from fractions import Fraction
import math

import pytest

from alpha_factory_v1.core.runtime import work
from alpha_factory_v1.core.runtime.models import Forecast, Mission
from alpha_factory_v1.core.runtime.store import canonical


@pytest.mark.parametrize(
    "values",
    [
        [1e15, 0.01, -1e15],
        [-1e15, 0.01, 1e15],
        [0.0, -0.0],
        [5e-324, 5e-324, -5e-324],
        [1e15, 1e15, -1e15, -1e15, 0.5],
    ],
)
def test_mean_uses_accurate_explicit_summation(values):
    exact_sum = sum((Fraction.from_float(value) for value in values), Fraction())
    expected = float(exact_sum) / len(values)
    actual = work._predict(values, "mean", 1, 3)
    assert actual == [expected] * 3
    assert canonical(actual) == canonical([expected] * 3)
    assert math.copysign(1.0, actual[0]) == math.copysign(1.0, expected)


def test_forecast_never_uses_version_dependent_builtin_sum(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("forecast must not use Python-version-dependent float sum")

    monkeypatch.setattr(work, "sum", forbidden, raising=False)
    series = [0.0, -0.0, 1.0, 1.5, -2.5, 1e-7, 10000000.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    mission = Mission(goal="Verify explicit forecast arithmetic", work=Forecast(observations=series))
    result = work.forecast(mission)
    errors = [abs(a - b) for a, b in zip(result["holdout_actual"], result["holdout_predictions"])]
    exact_sum = sum((Fraction.from_float(value) for value in errors), Fraction())
    assert result["holdout_mae"] == float(exact_sum) / len(errors)
    assert canonical(result) == canonical(work.forecast(mission))
    assert work.verify_result(mission, result)["passed"]
