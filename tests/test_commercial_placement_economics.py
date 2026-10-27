# SPDX-License-Identifier: Apache-2.0
"""Independent financial identities for the conditional placement offering."""

from fractions import Fraction

import pytest

from contrib.resilient_placement_delivery.economics import UNIT_COSTS, USD, amount, model, scenario


def test_scenario_retains_attempt_costs_and_reconciles_cash_and_profit() -> None:
    row = scenario()
    assert row["booked_orders"] == 2
    expected = Fraction(3, 4) * 2 * (Fraction(9, 10) * 250 * USD - Fraction(95, 100) * 7_800_000)
    expected -= 2 * sum(UNIT_COSTS.values()) + 500 * USD
    assert amount(row["expected_operating_profit_micro_usd"]) == expected < 0
    for branch in row["assessment"]["branches"]:
        assert branch["cash_contribution_micro_usd"] == (
            branch["projected_collections_micro_usd"] - branch["cash_costs_micro_usd"] - branch["refunds_micro_usd"]
        )
        assert branch["terminal_cash_micro_usd"] == 1000 * USD + branch["cash_contribution_micro_usd"]
        assert branch["cost_buckets_micro_usd"]["B"] == branch["cost_buckets_micro_usd"]["C"] == 0
    assert {
        branch["cash_costs_micro_usd"] >= 500 * USD + 2 * sum(UNIT_COSTS.values())
        for branch in row["assessment"]["branches"]
    } == {True}


def test_demand_is_recomputed_and_zero_demand_does_not_erase_fixed_cost() -> None:
    assert [scenario(price_usd=price)["booked_orders"] for price in (150, 250, 400)] == [4, 2, 0]
    zero = scenario(opportunities=0)
    assert zero["booked_orders"] == 0
    assert amount(zero["expected_operating_profit_micro_usd"]) == -500 * USD
    assert zero["break_even_acceptance_fraction"] is None


def test_equal_scope_human_outside_option_limits_purchase_without_a_premium() -> None:
    row = scenario(price_usd=400)
    assert row["buyer_caps_usd"][-1] == 450
    assert row["effective_buyer_caps_micro_usd"][-1] == 360 * USD
    assert all(participant["price_cap_micro_usd"] <= 360 * USD for participant in row["arrangement"]["participants"])
    assert row["booked_orders"] == 0
    assert all(not branch["receipts"] for branch in row["arrangement"]["scenarios"])
    assert amount(row["expected_operating_profit_micro_usd"]) == -500 * USD
    assert scenario(price_usd=360)["booked_orders"] == 1
    assert scenario(price_usd=361)["booked_orders"] == 0


def test_profit_does_not_create_funding_or_actual_revenue() -> None:
    data = model()
    row = data["profitable_but_underfunded_example"]
    assert amount(row["expected_operating_profit_micro_usd"]) > 0
    assert not row["assessment"]["liquidity_feasible"]
    assert row["assessment"]["decision"] == "hold"
    assert data["actual"]["collections_micro_usd"] == 0
    assert data["actual"]["profit_micro_usd"] is None
    assert data["actual"]["complete_cost_micro_usd"] is None
    assert all(price["full_project_profit_micro_usd"] is None for price in data["price_hypotheses"])


def test_break_even_boundary_and_acceptance_zero_are_explicit() -> None:
    row = scenario(opportunities=24)
    n = row["break_even_booked_orders_at_unchanged_price_quality_cost"]
    unit = amount(row["expected_unit_direct_contribution_micro_usd"])
    assert unit * n >= row["fixed_operating_cost_micro_usd"] > unit * (n - 1)
    rejected = scenario(acceptance_percent=0)
    assert amount(rejected["expected_operating_profit_micro_usd"]) == -(
        rejected["fixed_operating_cost_micro_usd"]
        + rejected["booked_orders"] * rejected["direct_cost_per_attempt_micro_usd"]
    )
    assert rejected["break_even_booked_orders_at_unchanged_price_quality_cost"] is None
    assert not scenario()["acceptance_alone_can_break_even_at_fixed_bookings"]
    assert scenario(opportunities=24)["acceptance_alone_can_break_even_at_fixed_bookings"]


@pytest.mark.parametrize("q", (0, 50, 75, 100))
def test_probability_mass_receivables_refunds_and_attempt_costs(q: int) -> None:
    row = scenario(acceptance_percent=q, opportunities=12)
    branches = row["arrangement"]["scenarios"]
    assert sum(branch["probability_ppm"] for branch in branches) == 1_000_000
    expected_profit = Fraction()
    for branch, assessed in zip(branches, row["assessment"]["branches"]):
        costs = sum(cost["cash_micro_usd"] for cost in branch["costs"])
        collected = sum(
            receipt["amount_micro_usd"] for receipt in branch["receipts"] if receipt["collected_at"] is not None
        )
        refunds = sum(refund["amount_micro_usd"] for refund in branch["refunds"])
        assert assessed["cash_contribution_micro_usd"] == collected - costs - refunds
        expected_profit += Fraction(branch["probability_ppm"], 1_000_000) * (collected - costs - refunds)
        identities = [cost["activity_id"] for cost in branch["costs"]]
        assert len(set(identities)) == len(identities)
        if branch["scenario_id"] in {"rejected-common", "withdrawal-stress"}:
            assert branch["receipts"] == []
        if branch["scenario_id"] == "accepted-default":
            assert assessed["projected_collections_micro_usd"] == 0
            assert assessed["defaulted_receivables_micro_usd"] == len(branch["receipts"]) * 250 * USD
        if branch["scenario_id"] == "accepted-refunded":
            assert collected == refunds
    assert expected_profit == amount(row["expected_operating_profit_micro_usd"])


@pytest.mark.parametrize(
    "changes",
    [
        {"opportunities": 33},
        {"acceptance_percent": 101},
        {"price_usd": True},
        {"collection_day": 6},
        {"workload_percent": 0},
    ],
)
def test_invalid_model_inputs_refuse(changes: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        scenario(**changes)
