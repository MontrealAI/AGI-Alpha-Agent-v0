# SPDX-License-Identifier: Apache-2.0
"""A–L decision regressions and independent auditor corruption controls."""
from __future__ import annotations

import copy
from typing import Any

import pytest

from .verify import audit_events

UNIT = 1_000_000


def events(*rows: tuple[str, int | None, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"id": f"event-{index}", "seq": index, "day": index, "type": kind,
         "amount_micro_usd": None if amount is None else amount * UNIT,
         "order_id": fields.pop("order_id", "order-1"), **fields}
        for index, (kind, amount, fields) in enumerate(rows, 1)
    ]


def income(amount: int) -> list[tuple[str, int | None, dict[str, Any]]]:
    return [("acceptance", 0, {"details": {"accepted": True}}), ("earned", amount, {}), ("collect", amount, {})]


def cost(activity: str, amount: int, allocation: str = "production", paid: bool = True) -> list[tuple[str, int | None, dict[str, Any]]]:
    rows: list[tuple[str, int | None, dict[str, Any]]] = [
        ("accrue_cost", amount, {"activity_id": activity, "allocation": allocation})
    ]
    if paid:
        rows.append(("pay_cost", amount, {"activity_id": activity}))
    return rows


def result(rows: list[tuple[str, int | None, dict[str, Any]]]) -> dict[str, Any]:
    report = audit_events(events(*rows))
    if not report["passed"]:
        raise AssertionError(report["errors"])
    return dict(report["summary"])


def investment(
    summary: dict[str, Any], amount: int, expected_increment: int, *, technical_advantage: bool = False,
    blue_sky: str = "GO", allocation: str = "commercial_probe", remaining: int = 100, protected: int = 20,
) -> dict[str, bool | str]:
    profitable = summary["profit_micro_usd"] > 0 and summary["unknown_cost_count"] == 0
    qualified = profitable and summary["unrestricted_cash_micro_usd"] >= 25 * UNIT and summary["liability_micro_usd"] == 0
    from .operate import investment_gate

    funding_source = "earned_profit" if amount * UNIT <= summary["profit_micro_usd"] else "opening_capital"
    facts = dict(summary, funding_source=funding_source,
                 remaining_periods=1 if remaining >= protected + 1 else 0,
                 allocation="bounded_commercial_probe" if allocation == "commercial_probe" else allocation)
    protocol = {"opening_capital_usd": summary["capital_micro_usd"] / UNIT,
                "protected_closeout_usd": 0, "hold_probe_investment_cap_usd": 1000,
                "permitted_funding_sources": ["earned_profit", "opening_capital"]}
    proposal = {"cost_micro_usd": amount * UNIT, "expected_incremental_value_micro_usd": expected_increment * UNIT,
                "eligible": expected_increment > 0}
    permit = investment_gate(facts, proposal, protocol)
    profit_funding = permit and funding_source == "earned_profit"
    return {"commercial_qualified": qualified, "accounting_profitable": profitable,
            "technical_advantage": technical_advantage,
            "investment_permitted": permit, "profit_funding": profit_funding,
            "funding_source": "earned_profit" if profit_funding else "opening_capital_or_debt",
            "project_payback": summary["cumulative_project_payback_micro_usd"] >= 0}


def test_A_conventional_profitable_and_funded() -> None:
    summary = result([("opening_capital", 100, {}), *cost("dev", 10, "development"), *income(50), *cost("run", 5)])
    decision = investment(summary, 5, 12)
    assert decision["commercial_qualified"] and decision["investment_permitted"] and decision["profit_funding"]
    assert not decision["technical_advantage"]


def test_B_technical_winner_economic_loss() -> None:
    summary = result([("opening_capital", 100, {}), *income(10), *cost("run", 20)])
    decision = investment(summary, 5, 10, technical_advantage=True)
    assert decision["technical_advantage"] and not decision["commercial_qualified"]
    assert summary["profit_micro_usd"] == -10 * UNIT


def test_C_profitable_base_reject_optional_uneconomic_specialist() -> None:
    summary = result([("opening_capital", 100, {}), *income(50), *cost("run", 5)])
    decision = investment(summary, 10, -1)
    assert decision["commercial_qualified"] and not decision["investment_permitted"]


def test_D_financing_and_deposit_cash_is_not_profit() -> None:
    summary = result([("opening_capital", 100, {}), ("debt", 50, {}), ("deposit", 20, {}), *cost("run", 10)])
    assert summary["cash_micro_usd"] == 160 * UNIT
    assert summary["liability_micro_usd"] == 70 * UNIT
    assert not investment(summary, 5, 10)["commercial_qualified"]


def test_E_positive_period_profit_unrecovered_development_can_invest() -> None:
    summary = result([("opening_capital", 200, {}), *cost("dev", 100, "development"), *income(20), *cost("run", 5)])
    decision = investment(summary, 5, 10)
    assert 20 - 5 > 0 and not decision["project_payback"]
    assert decision["investment_permitted"] and not decision["profit_funding"]
    assert summary["cumulative_project_payback_micro_usd"] == -85 * UNIT


def test_F_incurred_unpaid_cost_retains_liability_and_shortfall() -> None:
    summary = result([*cost("unpaid", 10, paid=False)])
    assert summary["liability_micro_usd"] == 10 * UNIT and summary["cash_micro_usd"] == 0
    assert summary["profit_micro_usd"] == -10 * UNIT
    assert not investment(summary, 1, 10)["investment_permitted"]


def test_G_capitalized_development_one_outflow_and_amortization() -> None:
    summary = result([("opening_capital", 100, {}), ("capitalize_development", 60, {"activity_id": "asset"}),
                      ("amortize", 10, {"activity_id": "asset"}), *income(20)])
    assert summary["cash_micro_usd"] == 60 * UNIT
    assert summary["profit_micro_usd"] == 10 * UNIT
    assert summary["capitalized_asset_micro_usd"] == 50 * UNIT
    assert summary["dev_paid_micro_usd"] == 60 * UNIT


def test_H_opening_capital_or_debt_rejects_profit_funding_label() -> None:
    for financing in ("opening_capital", "debt"):
        rows = events((financing, 100, {}), ("investment_decision", 0,
            {"details": {"selected": True, "cost_micro_usd": 10 * UNIT, "funding_source": "earned_profit"}}))
        report = audit_events(rows)
        assert not report["passed"] and any("earned-profit" in error for error in report["errors"])


def test_I_failed_delivery_refund_retains_incidental_cost() -> None:
    summary = result([("opening_capital", 100, {}), *income(20), *cost("attempt", 7),
                      ("revenue_reversal", 20, {"details": {"receivable_reduction_micro_usd": 0}}), ("refund", 20, {})])
    assert summary["profit_micro_usd"] == -7 * UNIT and summary["cash_micro_usd"] == 93 * UNIT
    assert summary["liability_micro_usd"] == 0 and summary["receivable_micro_usd"] == 0


def test_J_working_inheritance_without_increment_does_not_compound() -> None:
    summary = result([("opening_capital", 100, {}), *income(20), *cost("run", 2)])
    decision = investment(summary, 2, 0)
    assert decision["commercial_qualified"] and not decision["investment_permitted"]


def test_K_accounting_profit_without_cash_defers_investment() -> None:
    summary = result([("opening_capital", 1, {}), ("acceptance", 0, {"details": {"accepted": True}}), ("earned", 20, {})])
    decision = investment(summary, 5, 10)
    assert summary["profit_micro_usd"] == 20 * UNIT and decision["accounting_profitable"]
    assert not decision["commercial_qualified"] and not decision["investment_permitted"] and summary["receivable_micro_usd"] == 20 * UNIT


def test_L_profitable_hold_probe_blocks_main_flagship_budget() -> None:
    summary = result([("opening_capital", 100, {}), *income(20), *cost("run", 2)])
    probe = investment(summary, 2, 5, blue_sky="HOLD")
    main = investment(summary, 2, 5, blue_sky="HOLD", allocation="main_flagship")
    assert probe["commercial_qualified"] and probe["investment_permitted"]
    assert main["commercial_qualified"] and not main["investment_permitted"]
    invalid = audit_events(events(("opening_capital", 100, {}), *income(20),
        ("investment_decision", 0, {"details": {"selected": True, "cost_micro_usd": 2 * UNIT,
            "funding_source": "earned_profit", "blue_sky_state": "HOLD", "allocation": "main_flagship"}})))
    assert not invalid["passed"]


def test_resource_limit_closeout_protects_finalization() -> None:
    summary = result([("opening_capital", 100, {}), *income(20)])
    assert not investment(summary, 2, 5, remaining=20, protected=20)["investment_permitted"]


def test_unknown_cost_refuses_discretionary_work() -> None:
    summary = result([("opening_capital", 100, {}), *income(20),
                      ("accrue_cost", None, {"activity_id": "uncertain", "basis": "unknown"})])
    assert summary["unknown_cost_count"] == 1
    assert not investment(summary, 2, 5)["investment_permitted"]


def test_unpaid_refund_retained_at_cutoff() -> None:
    summary = result([("opening_capital", 100, {}), *income(20),
                      ("revenue_reversal", 20, {"details": {"receivable_reduction_micro_usd": 0}})])
    assert summary["cash_micro_usd"] == 120 * UNIT and summary["liability_micro_usd"] == 20 * UNIT
    assert summary["unsettled_refunds_micro_usd"] == 20 * UNIT


def test_duplicate_charge_and_overpayment_refused() -> None:
    original = events(("accrue_cost", 5, {"activity_id": "work"}), ("pay_cost", 5, {"activity_id": "work"}))
    duplicate = copy.deepcopy(original)
    duplicate.append({**duplicate[0], "id": "event-3", "seq": 3, "day": 3})
    assert not audit_events(duplicate)["passed"]
    original[1]["amount_micro_usd"] = 6 * UNIT
    assert not audit_events(original)["passed"]


def test_unaccepted_sale_and_duplicate_sequence_refused() -> None:
    assert not audit_events(events(("earned", 20, {})))["passed"]
    rows = events(("opening_capital", 10, {}), ("reserve", 2, {}))
    rows[1]["seq"] = 1
    assert not audit_events(rows)["passed"]


def test_chain_tamper_detected() -> None:
    import hashlib
    from .verify import canonical

    rows = events(("opening_capital", 100, {}), *income(20))
    previous = "0" * 64
    for row in rows:
        row["previous"] = previous
        row["hash"] = hashlib.sha256(canonical(row)).hexdigest()
        previous = row["hash"]
    assert audit_events(rows)["passed"]
    rows[0]["amount_micro_usd"] += 1
    assert not audit_events(rows)["passed"]


def test_artifact_and_rollback_external_acceptance() -> None:
    from .catalog_product import apply_patch, reconcile, rollback
    from .verify import validate_delivery

    before = 'sku,description,price\r\na,"Montréal, QC",10\r\nb,=1+1,20\r\n'
    after = 'sku,description,price\na,Québec,12\nc,Paris,30\n'
    package = reconcile(before, after, ["sku"])
    assert validate_delivery(before, after, ["sku"], 0, package)["accepted"]
    with pytest.raises(ValueError):
        apply_patch(before + "x", package, authorized=True)
    with pytest.raises(PermissionError):
        apply_patch(before, package, authorized=False)
    applied = apply_patch(before, package, authorized=True)
    with pytest.raises(ValueError):
        rollback(applied + "x", package, authorized=True)
    package["output_csv"] = package["output_csv"].replace("12", "13")
    assert not validate_delivery(before, after, ["sku"], 0, package)["accepted"]


def test_actual_policy_rejects_unpermitted_capital_funding_and_unknown_cost() -> None:
    from .operate import investment_gate

    facts = {"cash_micro_usd": 100 * UNIT, "liability_micro_usd": 0, "reserves_micro_usd": 0,
             "profit_micro_usd": 0, "unknown_cost_count": 0, "funding_source": "opening_capital"}
    protocol = {"opening_capital_usd": 100, "protected_closeout_usd": 5,
                "hold_probe_investment_cap_usd": 50, "permitted_funding_sources": ["earned_profit"]}
    proposal = {"cost_micro_usd": 5 * UNIT, "eligible": True, "expected_incremental_value_micro_usd": 10 * UNIT}
    assert not investment_gate(facts, proposal, protocol)
    facts["funding_source"] = "earned_profit"
    assert not investment_gate(facts, proposal, protocol)
    facts.update(cash_micro_usd=150 * UNIT, profit_micro_usd=50 * UNIT)
    assert investment_gate(facts, proposal, protocol)
    facts["unknown_cost_count"] = 1
    assert not investment_gate(facts, proposal, protocol)


def test_actual_policy_covers_liabilities_reserves_and_capacity_closeout() -> None:
    from .operate import investment_gate

    protocol = {"opening_capital_usd": 100, "protected_closeout_usd": 25,
                "hold_probe_investment_cap_usd": 50}
    proposal = {"cost_micro_usd": 5 * UNIT, "eligible": True, "expected_incremental_value_micro_usd": 10 * UNIT}
    facts = {"cash_micro_usd": 140 * UNIT, "liability_micro_usd": 10 * UNIT,
             "reserves_micro_usd": 5 * UNIT, "profit_micro_usd": 50 * UNIT, "unknown_cost_count": 0}
    assert investment_gate(facts, proposal, protocol)
    facts["liability_micro_usd"] = 36 * UNIT
    assert not investment_gate(facts, proposal, protocol)
    facts["liability_micro_usd"] = 0
    facts["remaining_periods"] = 0
    assert not investment_gate(facts, proposal, protocol)


def test_actual_resource_budget_guard_preserves_testing_settlement_finalization() -> None:
    from .operate import investment_gate

    protocol = {"opening_capital_usd": 100, "protected_closeout_usd": 25,
                "hold_probe_investment_cap_usd": 50}
    proposal = {"cost_micro_usd": 5 * UNIT, "eligible": True, "expected_incremental_value_micro_usd": 10 * UNIT}
    facts = {"cash_micro_usd": 150 * UNIT, "liability_micro_usd": 0, "reserves_micro_usd": 0,
             "profit_micro_usd": 50 * UNIT, "unknown_cost_count": 0,
             "remaining_resource_units": 20, "protected_resource_units": 20, "work_resource_units": 1}
    assert not investment_gate(facts, proposal, protocol)
    facts["remaining_resource_units"] = 21
    assert investment_gate(facts, proposal, protocol)
    del facts["protected_resource_units"]
    assert not investment_gate(facts, proposal, protocol)


def test_reference_construction_refuses_stale_equal_amount_reservation(tmp_path: Any) -> None:
    from .operate import CAMPAIGN, ROOT, Recorder, construct, file_hash

    recorder = Recorder(tmp_path, "independent-receipt-fixture")
    recorder.add("opening_capital", 0, 100 * UNIT)
    old_reserve = recorder.add("reserve", 0, 530000, investment_id="generation-2")
    recorder.add("release_reserve", 0, 530000, investment_id="generation-2")
    decision = recorder.add("investment_decision", 1, 0, selected=True, target_generation=3, cost_micro_usd=530000)
    current_reserve = recorder.add("reserve", 1, 530000, investment_id="generation-3")
    state = {"pending_investment": {"target_generation": 3, "cost_micro_usd": 530000}, "generation": 2}
    receipt = {"campaign_id": CAMPAIGN, "generation": 3, "source_sha256": file_hash(ROOT / "catalog_product.py"),
               "funding_decision_event_id": decision["id"], "funding_decision_event_hash": decision["hash"],
               "funding_reserve_event_id": old_reserve["id"], "funding_reserve_event_hash": old_reserve["hash"]}
    count = len(recorder.events)
    with pytest.raises(ValueError, match="exact generation"):
        construct(recorder, state, {}, 3, 1, receipt, reference=True)
    assert len(recorder.events) == count
    receipt.update(funding_reserve_event_id=current_reserve["id"], funding_reserve_event_hash=current_reserve["hash"])
    recorder.add("release_reserve", 1, 530000, investment_id="generation-3")
    count = len(recorder.events)
    with pytest.raises(ValueError, match="released"):
        construct(recorder, state, {}, 3, 1, receipt, reference=True)
    assert len(recorder.events) == count
    recorder.add("reserve", 1, 530000, investment_id="generation-3")
    recorder.add("investment_decision", 1, 0, selected=False, target_generation=3, cost_micro_usd=530000)
    count = len(recorder.events)
    with pytest.raises(ValueError, match="superseded"):
        construct(recorder, state, {}, 3, 1, receipt, reference=True)
    assert len(recorder.events) == count
