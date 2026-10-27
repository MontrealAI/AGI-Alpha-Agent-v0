# SPDX-License-Identifier: Apache-2.0
"""Real ledger transactions with fictional payments and local accepted deliveries."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge
from alpha_factory_v1.core.runtime.successor.flywheel_customer import CustomerDeposit, balances
from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record
import test_flywheel_protected as f
import test_flywheel_enterprise as e


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def deposit(identity: str = "service-receipt", mode: str = "synthetic", **changes: Any) -> dict[str, Any]:
    return {
        "receipt_id": identity,
        "mission_id": f.ORIGIN,
        "amount_micro_usd": 100,
        "purpose": "service",
        "service_price_micro_usd": 100,
        "mode": mode,
        "evidence_digest": digest("customer-fixture-payment", {"id": identity}),
        "note": "Fictional payment conformance; no customer or bank transaction",
        **changes,
    }


def earn(state: dict[str, Any], identity: str = "earn-one", **changes: Any) -> dict[str, Any]:
    record = state["journal"].latest(f.ORIGIN)
    return {
        "event_id": identity,
        "receipt_id": "service-receipt",
        "amount_micro_usd": 100,
        "delivery_kind": "native",
        "operation_id": None,
        "execution_record_digest": record["digest"],
        "acceptance_record_digest": digest("native-delivery-review", record["review"]),
        **changes,
    }


def refund(identity: str = "refund-one", **changes: Any) -> dict[str, Any]:
    return {
        "event_id": identity,
        "receipt_id": "service-receipt",
        "amount_micro_usd": 20,
        "allocation": "unearned",
        "evidence_digest": digest("customer-fixture-refund", {"id": identity}),
        "reason": "Fictional refund conformance",
        **changes,
    }


def apply(state: dict[str, Any], action: str, record: dict[str, Any], operation: str | None = None) -> None:
    f.account(state, action, record, operation or str(record.get("event_id", record.get("receipt_id"))))


def test_live_deposit_is_cash_and_a_liability_until_qualified_acceptance(setup: dict[str, Any]) -> None:
    before = setup["costs"].report()
    apply(setup, "customer-deposit", deposit(mode="live"))
    after = setup["costs"].report()
    assert after["cash"] == before["cash"] + 100
    assert after["customer_obligations"] == 100 and after["collected_revenue"] == 0
    assert after["available_funds"] == before["available_funds"]
    apply(setup, "customer-refund", refund())
    final = setup["costs"].report()
    assert final["cash"] == after["cash"] - 20 and final["customer_obligations"] == 80
    assert final["available_funds"] == before["available_funds"]


@pytest.mark.parametrize("mode", ["recorded", "synthetic", "calibrated"])
def test_nonlive_funds_never_increase_operating_cash_or_permission(setup: dict[str, Any], mode: str) -> None:
    before = setup["costs"].report()
    control = setup["journal"].latest("@control")["digest"]
    f.paid_origin(setup)
    funded = setup["costs"].report()
    apply(setup, "customer-deposit", deposit(mode=mode))
    apply(setup, "customer-earn", earn(setup))
    after = setup["costs"].report()
    for field in ("cash", "available_funds", "collected_revenue", "accepted_service_revenue"):
        assert after[field] == funded[field]
    assert after["customer_funds_by_mode"][mode]["earned_revenue"] == 100
    assert before["cash"] == 0 and setup["journal"].latest("@control")["digest"] == control


def test_partial_earning_and_both_refund_allocations_reconcile_once(setup: dict[str, Any]) -> None:
    f.paid_origin(setup)
    apply(setup, "customer-deposit", deposit())
    apply(setup, "customer-earn", earn(setup, amount_micro_usd=60))
    apply(setup, "customer-refund", refund(amount_micro_usd=25))
    apply(setup, "customer-refund", refund("earned-refund", amount_micro_usd=15, allocation="earned"))
    row = setup["costs"].snapshot()["customer_deposits"]["service-receipt"]
    assert balances(row) == {
        "gross_collections": 100,
        "refunds": 40,
        "net_cash": 60,
        "earned_revenue": 45,
        "unearned_service": 15,
        "pass_through_custody": 0,
        "customer_obligations": 15,
        "pending_refunds": 0,
    }
    assert balances(row)["net_cash"] == balances(row)["earned_revenue"] + balances(row)["customer_obligations"]
    assert setup["journal"].verify()["valid"]


def test_passthrough_cannot_be_earned_and_stays_reserved(setup: dict[str, Any]) -> None:
    f.paid_origin(setup)
    before = setup["costs"].report()
    apply(setup, "customer-deposit", deposit(mode="live", purpose="pass-through", service_price_micro_usd=0))
    with pytest.raises(ValueError, match="custody"):
        apply(setup, "customer-earn", earn(setup))
    assert setup["costs"].report()["available_funds"] == before["available_funds"]
    with pytest.raises(ValueError, match="allocation"):
        apply(setup, "customer-refund", refund())
    apply(setup, "customer-refund", refund(allocation="pass-through", amount_micro_usd=100))
    assert setup["costs"].report()["cash"] == before["cash"]


@pytest.mark.parametrize("action", ["customer-deposit", "customer-earn", "customer-refund"])
def test_exact_retry_is_idempotent_and_new_operation_cannot_repeat_event(setup: dict[str, Any], action: str) -> None:
    f.paid_origin(setup)
    record = deposit()
    if action != "customer-deposit":
        apply(setup, "customer-deposit", record)
        record = earn(setup, amount_micro_usd=60) if action == "customer-earn" else refund()
    apply(setup, action, record, "same-operation")
    before = setup["costs"].snapshot()
    apply(setup, action, record, "same-operation")
    assert setup["costs"].snapshot() == before
    with pytest.raises(Conflict, match="already allocated"):
        apply(setup, action, record, "different-operation")
    assert setup["costs"].snapshot() == before


@pytest.mark.parametrize("allocation,amount", [("unearned", 101), ("earned", 1), ("pass-through", 1)])
def test_invalid_refunds_are_atomic(setup: dict[str, Any], allocation: str, amount: int) -> None:
    apply(setup, "customer-deposit", deposit())
    before = setup["costs"].snapshot()
    with pytest.raises(ValueError, match="allocation"):
        apply(setup, "customer-refund", refund(allocation=allocation, amount_micro_usd=amount))
    assert setup["costs"].snapshot() == before


@pytest.mark.parametrize("attack", ["wrong-mission", "wrong-delivery", "wrong-acceptance", "native-live"])
def test_unrelated_or_unqualified_acceptance_cannot_earn(setup: dict[str, Any], attack: str) -> None:
    f.paid_origin(setup)
    payment = deposit(mode="live" if attack == "native-live" else "synthetic")
    if attack == "wrong-mission":
        payment["mission_id"] = "other-mission"
    apply(setup, "customer-deposit", payment)
    terms = earn(setup)
    if attack == "wrong-delivery":
        terms["execution_record_digest"] = f.ZERO
    if attack == "wrong-acceptance":
        terms["acceptance_record_digest"] = f.ZERO
    before = setup["costs"].snapshot()
    with pytest.raises((KeyError, Conflict, ValueError)):
        apply(setup, "customer-earn", terms)
    assert setup["costs"].snapshot() == before


def test_general_earning_uses_actual_existing_acceptance_and_mission(setup: dict[str, Any]) -> None:
    result = e.launch(setup)
    terms = deposit(mission_id="placement-origin")
    apply(setup, "customer-deposit", terms)
    earning = {
        "event_id": "general-earned",
        "receipt_id": terms["receipt_id"],
        "amount_micro_usd": 100,
        "delivery_kind": "general",
        "operation_id": "placement-origin",
        "execution_record_digest": result["digest"],
        "acceptance_record_digest": f.ZERO,
    }
    with pytest.raises(KeyError):
        apply(setup, "customer-earn", earning)
    e.accept(setup, result)
    earning["acceptance_record_digest"] = setup["journal"].latest(ACCEPTANCE_KEY + "placement-origin")["digest"]
    apply(setup, "customer-earn", earning)
    assert setup["costs"].report()["customer_funds_by_mode"]["synthetic"]["earned_revenue"] == 100
    live = deposit("live-receipt", mode="live", mission_id="a-different-live-mission")
    apply(setup, "customer-deposit", live)
    with pytest.raises(ValueError, match="different missions"):
        apply(setup, "customer-earn", {**earning, "event_id": "cross-scope", "receipt_id": "live-receipt"})


def test_hybrid_general_acceptance_cannot_be_relabelled_live(setup: dict[str, Any]) -> None:
    result = e.launch(setup)
    e.accept(setup, result)
    apply(setup, "customer-deposit", deposit(mode="live", mission_id="placement-origin"))
    with pytest.raises(ValueError, match="cannot earn live"):
        apply(
            setup,
            "customer-earn",
            {
                "event_id": "hybrid-live",
                "receipt_id": "service-receipt",
                "amount_micro_usd": 100,
                "delivery_kind": "general",
                "operation_id": "placement-origin",
                "execution_record_digest": result["digest"],
                "acceptance_record_digest": setup["journal"].latest(ACCEPTANCE_KEY + "placement-origin")["digest"],
            },
        )
    assert setup["costs"].report()["accepted_service_revenue"] == 0


@pytest.mark.parametrize("direction", ["new-first", "legacy-first", "cost-first", "refund-first"])
def test_payment_evidence_cannot_be_recredited_across_accounting_paths(setup: dict[str, Any], direction: str) -> None:
    payment = deposit(mode="live")
    old = {
        "record_id": "legacy-money",
        "mission_id": f.ORIGIN,
        "amount_micro_usd": 100,
        "evidence_digest": payment["evidence_digest"],
    }
    if direction == "legacy-first":
        f.account(setup, "capital", old, "legacy")
    elif direction == "cost-first":
        f.account(
            setup,
            "charge",
            Charge(
                activity_id="expense",
                mission_id=f.ORIGIN,
                bucket="A",
                category="compute",
                accrued_micro_usd=100,
                paid_micro_usd=0,
                basis="attested",
                evidence_digest=f.ZERO,
                note="Fictional expense",
            ).model_dump(),
            "expense",
        )
        f.account(
            setup,
            "payment",
            {
                "payment_id": "cost-paid",
                "activity_id": "expense",
                "amount_micro_usd": 100,
                "evidence_digest": payment["evidence_digest"],
            },
            "cost-paid",
        )
    else:
        apply(setup, "customer-deposit", payment)
        if direction == "refund-first":
            returned = refund()
            apply(setup, "customer-refund", returned)
            old["evidence_digest"] = returned["evidence_digest"]
    before = setup["costs"].snapshot()
    with pytest.raises(Conflict, match="evidence"):
        if direction in {"legacy-first", "cost-first"}:
            apply(setup, "customer-deposit", payment)
        else:
            f.account(setup, "collection", old, "legacy")
    assert setup["costs"].snapshot() == before


def test_price_mode_and_lifetime_deposit_caps_cannot_be_changed(setup: dict[str, Any]) -> None:
    apply(setup, "customer-deposit", deposit(amount_micro_usd=60))
    for changes in [{"amount_micro_usd": 41}, {"service_price_micro_usd": 200}, {"mode": "live"}]:
        with pytest.raises(ValueError):
            apply(setup, "customer-deposit", deposit("second", **changes))
    apply(setup, "customer-deposit", deposit("second", amount_micro_usd=40))
    report = setup["costs"].report("unrelated")
    assert report["customer_funds_by_mode"]["synthetic"]["gross_collections"] == 0


def test_unknown_delivery_costs_stay_unknown_with_customer_funds(setup: dict[str, Any]) -> None:
    f.account(
        setup,
        "charge",
        Charge(
            activity_id="uncertain",
            mission_id=f.ORIGIN,
            bucket="A",
            category="model",
            accrued_micro_usd=None,
            paid_micro_usd=5,
            basis="unknown",
            evidence_digest=f.ZERO,
            note="Unknown final bill",
        ).model_dump(),
        "unknown",
    )
    apply(setup, "customer-deposit", deposit(mode="live"))
    report = setup["costs"].report()
    assert report["available_funds"] is None and report["complete_cost_profit"] is None
    assert report["known_obligations"] == 100 and report["unknown_costs"]


def test_customer_commands_keep_accounting_role_and_exact_operation_terms(setup: dict[str, Any]) -> None:
    terms = deposit()
    with pytest.raises(ValueError):
        setup["costs"].apply(
            sign_record(
                setup["keys"]["controller"],
                "controller",
                "flywheel-cost-command",
                {
                    "journal_identity": setup["journal"].identity,
                    "operation_id": "wrong-role",
                    "action": "customer-deposit",
                    "record": terms,
                },
            )
        )
    apply(setup, "customer-deposit", terms, "same-operation")
    changed = copy.deepcopy(terms)
    changed["amount_micro_usd"] = 50
    with pytest.raises(Conflict, match="different terms"):
        apply(setup, "customer-deposit", changed, "same-operation")


@pytest.mark.parametrize(
    "change",
    [
        {"amount_micro_usd": True},
        {"amount_micro_usd": 1.5},
        {"amount_micro_usd": -1},
        {"unexpected": 1},
        {"mode": "production"},
    ],
)
def test_customer_wire_refuses_coercion_and_malformed_fields(change: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        CustomerDeposit.model_validate(deposit(**change))


def test_interrupted_commit_rolls_back_cash_evidence_and_retry_identity(
    setup: dict[str, Any], monkeypatch: Any
) -> None:
    before = setup["costs"].snapshot()
    persist = setup["costs"]._persist

    def interrupted(*args: Any) -> None:
        raise OSError("simulated interruption before ledger commit")

    monkeypatch.setattr(setup["costs"], "_persist", interrupted)
    with pytest.raises(OSError, match="interruption"):
        apply(setup, "customer-deposit", deposit(mode="live"))
    assert setup["costs"].snapshot() == before
    monkeypatch.setattr(setup["costs"], "_persist", persist)
    apply(setup, "customer-deposit", deposit(mode="live"))
    assert setup["costs"].report()["cash"] == 100
    assert setup["costs"].report()["available_funds"] == 0


def test_durable_event_survives_operation_cache_compaction(setup: dict[str, Any]) -> None:
    apply(setup, "customer-deposit", deposit(mode="live"), "000-first-deposit")
    for i in range(130):
        f.account(setup, "reserve", 0, f"compact-{i}")
    assert "000-first-deposit" not in setup["costs"].snapshot()["operations"]
    apply(setup, "customer-deposit", deposit(mode="live"), "000-first-deposit")
    assert setup["costs"].report()["cash"] == 100
    with pytest.raises(Conflict, match="already allocated"):
        apply(setup, "customer-deposit", deposit(mode="live"), "new-operation")


def test_event_identity_is_shared_by_deposit_earning_and_refund(setup: dict[str, Any]) -> None:
    apply(setup, "customer-deposit", deposit())
    apply(setup, "customer-refund", refund("used-event"))
    with pytest.raises(Conflict, match="event identity"):
        apply(setup, "customer-deposit", deposit("used-event", mission_id="other"), "different-operation")


def test_due_earned_refund_reduces_income_before_payment_without_double_expense(setup: dict[str, Any]) -> None:
    f.paid_origin(setup)
    apply(setup, "customer-deposit", deposit())
    apply(setup, "customer-earn", earn(setup))
    apply(setup, "customer-refund-due", refund("refund-due", allocation="earned", amount_micro_usd=30))
    due = setup["costs"].report()["customer_funds_by_mode"]["synthetic"]
    assert due["earned_revenue"] == 70 and due["net_cash"] == 100 and due["customer_obligations"] == 30
    with pytest.raises(ValueError, match="allocation"):
        apply(setup, "customer-refund-due", refund("over-due", allocation="earned", amount_micro_usd=71))
    apply(setup, "customer-refund", refund("first-payment", allocation="earned", amount_micro_usd=10))
    partial = setup["costs"].report()["customer_funds_by_mode"]["synthetic"]
    assert partial["earned_revenue"] == 70 and partial["customer_obligations"] == 20
    apply(setup, "customer-refund", refund("last-payment", allocation="earned", amount_micro_usd=20))
    paid = setup["costs"].report()["customer_funds_by_mode"]["synthetic"]
    assert paid["earned_revenue"] == 70 and paid["net_cash"] == 70 and paid["customer_obligations"] == 0


def test_unearned_refund_due_cannot_be_earned_or_reserved_twice(setup: dict[str, Any]) -> None:
    f.paid_origin(setup)
    apply(setup, "customer-deposit", deposit())
    apply(setup, "customer-refund-due", refund("due", amount_micro_usd=30))
    with pytest.raises(ValueError, match="unearned"):
        apply(setup, "customer-earn", earn(setup, amount_micro_usd=71))
    with pytest.raises(ValueError, match="allocation"):
        apply(setup, "customer-refund-due", refund("due-again", amount_micro_usd=71))
    apply(setup, "customer-earn", earn(setup, amount_micro_usd=70))
    apply(setup, "customer-refund", refund(amount_micro_usd=30))
    report = setup["costs"].report()["customer_funds_by_mode"]["synthetic"]
    assert report["earned_revenue"] == report["net_cash"] == 70 and report["pending_refunds"] == 0
