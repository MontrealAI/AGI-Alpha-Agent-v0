# SPDX-License-Identifier: Apache-2.0
"""Trusted callable-capability checks, not physical or commercial validation."""

import csv
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from alpha_factory_v1.core.runtime.invention_automation.data_probe import (
    PANEL,
    aligned_risk,
    analyze,
    calendar_blocks,
)


def test_complete_calendar_week_is_order_independent():
    values = {f"2020-01-{day:02d}": float(day) for day in range(12, 5, -1)}
    assert calendar_blocks(values) == {"2020-01-06": [float(day) for day in range(6, 13)]}


def test_only_matching_calendar_weeks_enter_covariance():
    common = {"2020-01-06": 1.0, "2020-01-13": 2.0, "2020-01-20": 3.0}
    result = aligned_risk([dict(common, **{"2020-02-03": 1000.0}), common])
    assert result["aligned_complete_calendar_weeks"] == sorted(common)
    assert float(result["observed_joint_variance_kWh2"]) == 4.0
    assert result["risk_pooling_qualified"] is False


def test_absent_or_single_common_week_never_releases_reserve():
    with pytest.raises(ValueError, match="risk panel absent"):
        aligned_risk([])
    result = aligned_risk([{"2020-01-06": 1.0}, {"2020-01-06": 2.0}])
    assert result["status"] == "INSUFFICIENT_ALIGNED_BLOCKS"
    assert result["risk_pooling_qualified"] is False
    assert "observed_joint_variance_kWh2" not in result


def test_callable_analysis_retains_honest_scope(tmp_path: Path):
    """Exercise actual CSV ingestion, fitting, calendar pairing and report output."""
    meter, weather = tmp_path / "meter.csv", tmp_path / "weather.csv"
    start = datetime.fromisoformat("2020-01-06T00:00:00-07:00")
    with meter.open("w", newline="") as m, weather.open("w", newline="") as w:
        mw, ww = csv.writer(m), csv.writer(w)
        mw.writerow(["timestamp", *PANEL])
        ww.writerow(["timestamp", "TemperatureC"])
        for hour in range(24 * 301):
            stamp = start + timedelta(hours=hour)
            mw.writerow([stamp.isoformat(), *[float(i + 1) for i in range(len(PANEL))]])
            ww.writerow([stamp.replace(tzinfo=None).isoformat(), 18.0])
    result = analyze(meter, weather)
    assert result["commercial_cohort_count"] == 0
    assert result["source_cluster_count"] == 1
    assert result["causal_savings_accepted"] is False
    assert result["portfolio"]["risk_pooling_qualified"] is False
    assert result["portfolio"]["status"] == "EXPLORATORY_ALIGNED_ONLY"
    assert len(result["sites"]) == len(PANEL)
    for site in result["sites"]:
        assert site["status"] == "EXPLORATORY"
        assert site["causal_acceptance"] is False
        assert site["test_weeks"]
        for week in site["test_weeks"]:
            begin, end = map(datetime.fromisoformat, [week["start"], week["end"]])
            assert begin.weekday() == 0
            assert (end - begin).days == 6


def test_callable_analysis_refuses_missing_registered_panel(tmp_path: Path):
    meter, weather = tmp_path / "meter.csv", tmp_path / "weather.csv"
    meter.write_text("timestamp,unregistered\n")
    weather.write_text("timestamp,TemperatureC\n")
    with pytest.raises(ValueError, match="registered panel absent"):
        analyze(meter, weather)
