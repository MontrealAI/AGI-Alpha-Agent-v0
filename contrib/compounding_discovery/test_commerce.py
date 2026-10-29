# SPDX-License-Identifier: Apache-2.0
"""Economic refusal and protected artifact delivery for the actual route offering."""

from __future__ import annotations
import json
from pathlib import Path
import pytest
from contrib.compounding_discovery import commerce

HERE = Path(__file__).resolve().parent


def test_complete_free_equivalent_rationally_rejects_every_positive_price() -> None:
    for price in commerce.PRICES:
        decision = commerce.buyer_choice("free_completed", price, 0)
        assert not decision["accepts"]
        assert decision["outside_complete_cost_assumed_microUSD"] == 0


def test_integration_sensitivity_does_not_become_observed_willingness_to_pay() -> None:
    assert commerce.buyer_choice("assumed_integration_cost", 200000, 0)["accepts"]
    assert not commerce.buyer_choice("assumed_integration_cost", 500000, 0)["accepts"]
    assert "no observed buyer" in commerce.buyer_choice("assumed_integration_cost", 200000, 0)["basis"]


@pytest.mark.parametrize("scenario", ["low_trust", "slow_settlement", "scarce_buyer_cash"])
def test_adverse_buyer_conditions_keep_refusal_possible(scenario: str) -> None:
    assert not commerce.buyer_choice(scenario, 200000, 0)["accepts"]


def test_actual_route_output_is_protected_across_crash_duplicate_and_reversal(tmp_path: Path) -> None:
    task = json.loads((HERE / "base-target.json").read_text())
    result = commerce.mechanism_checks(tmp_path / "controls", task)
    assert result["independent_audit"]["audit_passed"]
    assert result["duplicate_settlement_revenue_once"]
    assert result["restart_recovered"]
    assert result["reversal_access"] == "PermissionError"


def test_complete_costs_prevent_seed_equity_being_reclassified_as_earned(tmp_path: Path) -> None:
    task = json.loads((HERE / "base-target.json").read_text())
    result = commerce.run_world(tmp_path / "world", task, [], {}, "assumed_integration_cost", 200000, "none")
    assert result["snapshot"]["revenue"] == 800000
    assert result["snapshot"]["profit"] < 0
    assert result["snapshot"]["unrestrictedEarned"] == 0
    assert result["new_successor_authorization"] is False
    assert result["independent_audit"]["audit_passed"]
