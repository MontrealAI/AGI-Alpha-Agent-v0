# SPDX-License-Identifier: Apache-2.0
"""Price selection, adverse confirmation and existing-engine reconciliation."""

from fractions import Fraction

from scripts.record_customer_funds import USD, commercial, expected, projection


def test_same_offering_finite_prices_freeze_before_downside_confirmation() -> None:
    result = commercial()
    selected = result["selected"]["price_micro_usd"]
    assert result["human_reference"]["amount_micro_usd"] // 2 in [r["price_micro_usd"] for r in result["development"]]
    assert all(r["price_micro_usd"] == selected for r in result["confirmation"])
    assert expected(result["selected"]) == max(expected(r) for r in result["development"])
    assert any(expected(r) < 0 for r in result["confirmation"])
    assert any(not r["assessment"]["liquidity_feasible"] and expected(r) > 0 for r in result["confirmation"])
    assert all(r["assessment"]["decision"] == "hold" for r in result["development"] + result["confirmation"])
    assert result["actual_customer_collections_micro_usd"] == 0
    assert result["retention"]["decision"].startswith("reject")


def test_default_and_refunds_never_remove_attempt_or_processing_costs() -> None:
    result = projection(2000)
    branches = {r["scenario_id"]: r for r in result["assessment"]["branches"]}
    assert branches["common-failure"]["projected_collections_micro_usd"] == 0
    assert branches["common-failure"]["cash_costs_micro_usd"] == (600 + 120 + 3 * 500) * USD
    assert branches["success"]["cash_costs_micro_usd"] == branches["quality-refund"]["cash_costs_micro_usd"]
    assert branches["quality-refund"]["refunds_micro_usd"] == 400 * USD
    assert branches["payment-default"]["defaulted_receivables_micro_usd"] == 2000 * USD
    assert branches["withdrawal-stress"]["projected_collections_micro_usd"] == 4000 * USD
    assert expected(result) == Fraction(580_041, 200) * USD
    for row in branches.values():
        assert row["cash_contribution_micro_usd"] == (
            row["projected_collections_micro_usd"] - row["refunds_micro_usd"] - row["cash_costs_micro_usd"]
        )


def test_pricing_is_reproducible_and_savings_never_post_as_collections() -> None:
    first, second = commercial(), commercial()
    assert first == second
    for row in first["development"]:
        assert row["assessment"]["actual_collections_micro_usd"] is None
        assert row["assessment"]["authority_granted"] is False
        assert row["customer_savings_if_accepted_micro_usd"] >= 0
        assert row["horizon_days"] == 90 and row["buyers"] <= 4
