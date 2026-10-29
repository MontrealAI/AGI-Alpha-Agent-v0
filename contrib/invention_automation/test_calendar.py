# SPDX-License-Identifier: Apache-2.0
from alpha_factory_v1.core.runtime.invention_automation.data_probe import aligned_risk, calendar_blocks


def test_equal_length_is_not_calendar_alignment():
    result = aligned_risk([{"2020-01-06": 1.0, "2020-01-13": 2.0}, {"2020-02-03": 1.0, "2020-02-10": 2.0}])
    assert result["status"] == "INSUFFICIENT_ALIGNED_BLOCKS"
    assert "observed_joint_variance_kWh2" not in result
    assert result["risk_pooling_qualified"] is False


def test_missing_day_cannot_be_rolled_into_a_seven_day_block():
    values = {f"2020-01-{n:02d}": float(n) for n in [6, 7, 8, 9, 10, 11, 13]}
    assert calendar_blocks(values) == {}


def test_common_calendar_covariance_preserves_joint_error():
    values = {"2020-01-06": 1.0, "2020-01-13": 2.0, "2020-01-20": 3.0}
    result = aligned_risk([values, values])
    assert float(result["observed_joint_variance_kWh2"]) == 4.0
    assert float(result["independence_assumption_variance_kWh2"]) == 2.0
    assert result["risk_pooling_qualified"] is False
