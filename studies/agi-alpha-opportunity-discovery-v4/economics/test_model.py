# SPDX-License-Identifier: Apache-2.0
"""Accounting and decision-boundary checks, not simulated customer validation."""

from dataclasses import replace

from model import Buyer, Scenario, choose, evaluate_plan, realize


def buyer(**changes):
    b = Buyer("test", 30, 200, 6000, 12000, 0, False, True, True, 10, 0)
    return replace(b, **changes)


def test_original_common_failure_example_is_not_success_contribution():
    success = 4 * 300_000 - 600_000 - 4 * 75_000
    expected = 0.8 * (4 * 300_000 - 4 * 75_000) - 600_000
    prefunding = 600_000 + 4 * 75_000
    assert (success, expected, prefunding) == (300_000, 120_000, 900_000)


def test_full_refund_advance_does_not_create_spendable_capital():
    s = Scenario()
    one = evaluate_plan([buyer()], s, "expert_arranged", 2500, 0.75, 1)
    zero = evaluate_plan([buyer()], s, "expert_standard", 2500, 0, 1)
    assert one and zero
    assert one["required_opening_cash"] == zero["required_opening_cash"]
    assert one["advance_collections"] == one["unearned_at_contract"] == 1875


def test_profit_does_not_imply_liquidity():
    s = replace(Scenario(), seed_cash=10)
    p = evaluate_plan([buyer()], s, "expert_standard", 2500, 0, 1)
    assert p and p["expected_profit"] > 0 and not p["financeable"]
    assert choose([buyer()], s, "expert_standard")["action"] == "stop"


def test_efficient_incumbent_is_real_outside_option():
    b = buyer(outside_price=250, value=1000, configured=True, expert_hours=2)
    assert evaluate_plan([b], Scenario(), "expert_standard", 1000, 0, 1) is None


def test_default_is_bad_debt_not_hidden_negative_collection():
    s = Scenario()
    b = buyer()
    p = evaluate_plan([b], s, "expert_arranged", 2500, 0.5, 0.5)
    assert p
    result = realize(
        {**p, "action": "produce"}, [b], s, 1, {b.id: {"default": 0, "technical": 0, "local": 0, "withdrawal": 1}}
    )
    assert result["accepted"] == 1
    assert result["earned_revenue"] == 2500
    assert result["collections"] == 1250
    assert result["bad_debt_expense"] == 1250
    assert abs(result["cash"] - s.seed_cash - result["profit"]) < 1e-8


def test_failure_refunds_are_not_earned_revenue():
    s = Scenario()
    b = buyer()
    p = evaluate_plan([b], s, "expert_arranged", 2500, 0.5, 0.5)
    assert p
    r = realize({**p, "action": "produce"}, [b], s, 1, {b.id: {"technical": 1, "withdrawal": 1}})
    assert r["accepted"] == 0
    assert r["refunds"] == 625 and r["earned_revenue"] == 625
    assert not any(x["activity"].endswith("conditional-delivery") for x in r["ledger"])
    assert r["obligations"] == 0


def test_withdrawal_cancels_before_construction_and_preserves_assessment_cost():
    s = replace(Scenario(), withdrawal_probability=1)
    b = buyer()
    p = evaluate_plan([b], s, "expert_arranged", 2500, 0.5, 0.5)
    assert p
    r = realize({**p, "action": "produce"}, [b], s, 1, {b.id: {"withdrawal": 0}})
    assert r["action"] == "cancel_after_withdrawal"
    assert r["collections"] == r["refunds"] == 1250
    assert r["profit"] == -s.research_assessment


def test_stopped_assessment_is_not_free():
    s = Scenario()
    p = choose([buyer(rights=False)], s, "expert_standard")
    r = realize(p, [buyer(rights=False)], s, 1)
    assert r["expenses"] == s.research_assessment
    assert r["profit"] == -100 and r["accepted"] == 0


def test_uncleared_rights_and_quality_fail_before_financing():
    assert evaluate_plan([buyer(rights=False)], Scenario(), "expert_arranged", 500, 0.75, 0.5) is None
    bad = replace(Scenario(), common_quality=0.82, common_build=0, retention=0)
    assert evaluate_plan([buyer()], bad, "retained_arranged", 2500, 0.75, 0.5) is None


def test_no_compatible_recipient_is_not_retained_alpha():
    s = replace(Scenario(), common_build=0, retention=0)
    assert evaluate_plan([buyer(compatible=False)], s, "retained_arranged", 2500, 0.5, 0.5) is None


def test_all_delivery_costs_precede_any_final_collection():
    s = Scenario()
    bs = [buyer(id="first"), buyer(id="second")]
    p = evaluate_plan(bs, s, "expert_arranged", 2500, 0.5, 0.5)
    assert p
    r = realize(
        {**p, "action": "produce"},
        bs,
        s,
        1,
        {b.id: {"technical": 0, "local": 0, "default": 1, "withdrawal": 1} for b in bs},
    )
    days = [x["day"] for x in r["ledger"]]
    assert days == sorted(days)
    delivery_indices = [i for i, x in enumerate(r["ledger"]) if x["activity"].endswith("conditional-delivery")]
    collection_indices = [i for i, x in enumerate(r["ledger"]) if x["kind"] == "collect_invoice"]
    assert max(delivery_indices) < min(collection_indices)
    assert min(x["cash_after_refund_reserve"] for x in r["ledger"]) >= 0
