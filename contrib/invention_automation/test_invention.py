# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.invention_automation import engine, programs
from alpha_factory_v1.core.runtime.structural_transfer.contracts import digest


def case(**changes: Any) -> dict[str, Any]:
    return {
        "id": "job1",
        "scope": "software-fault-fixture",
        "price": 1_000_000,
        "screening": 10_000,
        "measurement": 5_000,
        "production": 100_000,
        "required_value": 1_000_000,
        "buyer_cash": 2_000_000,
        "observed_value": 1_500_000,
        "measurement_valid": True,
        "settlement": "clear",
        "deadline": 100,
        **changes,
    }


def corrected() -> dict[str, Any]:
    value = programs.initial_program()
    for family in ["measurement-before-production", "collateral-and-production"]:
        value = programs.adapt(value, {"family": family, "validated": True, "candidate_hash": digest(value)})
    return value


@pytest.mark.parametrize("op", ["exec", "shell", "open", "network", "hardware", "import", "eval", "wallet"])
def test_generated_capabilities_are_rejected(op: str) -> None:
    value = programs.initial_program()
    value["steps"].insert(1, {"op": op})
    with pytest.raises(ValueError):
        programs.validate(value)


@pytest.mark.parametrize("bad", [True, -1, 10**13, "100", 0.1])
def test_strict_money_types(bad: Any, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        engine.execute(corrected(), [case(price=bad)], tmp_path / "e.db", opening=5_000_000)


def test_units_are_not_interchangeable() -> None:
    value = corrected()
    guard = next(x for x in value["steps"] if x["op"] == "guard")
    guard["test"]["unit"] = "kWh"
    with pytest.raises(ValueError):
        programs.validate(value)


def test_bad_criticism_cannot_modify_strategy(tmp_path: Path) -> None:
    p = programs.initial_program()
    with pytest.raises(ValueError):
        engine.validate_criticism(p, [case()], {"family": "more-hype"}, tmp_path / "bad.db", opening=5_000_000)
    with pytest.raises(ValueError):
        programs.adapt(p, {"family": "measurement-before-production", "validated": True, "candidate_hash": "x"})


def test_real_reproduced_witness_changes_behavior(tmp_path: Path) -> None:
    p = programs.initial_program()
    cohort = [case(observed_value=0)]
    old = engine.execute(p, cohort, tmp_path / "old.db", opening=5_000_000)
    witness = engine.failures(cohort, old)[0]
    constraint = engine.validate_criticism(p, cohort, witness, tmp_path / "rep.db", opening=5_000_000)
    new = engine.execute(programs.adapt(p, constraint), cohort, tmp_path / "new.db", opening=5_000_000)
    assert old["summary"]["expenses"] == 115_000
    assert new["summary"]["expenses"] == 15_000
    assert old["summary"]["revenue"] == new["summary"]["revenue"] == 0
    assert len(new["outcomes"]) == len(cohort)


def test_escrow_is_not_production_working_cash(tmp_path: Path) -> None:
    cohort = [case(production=500_000)]
    p = programs.adapt(
        programs.initial_program(),
        {
            "family": "measurement-before-production",
            "validated": True,
            "candidate_hash": digest(programs.initial_program()),
        },
    )
    old = engine.execute(p, cohort, tmp_path / "old.db", opening=1_200_000)
    assert old["summary"]["payables"] > 0
    witness = next(x for x in engine.failures(cohort, old) if x["critic"] == "economic")
    constraint = engine.validate_criticism(p, cohort, witness, tmp_path / "rep.db", opening=1_200_000)
    new = engine.execute(programs.adapt(p, constraint), cohort, tmp_path / "new.db", opening=1_200_000)
    assert new["summary"]["payables"] == new["summary"]["revenue"] == 0
    assert new["summary"]["profit"] == -15_000
    assert new["outcomes"][0]["outcome"] == "DEFERRED"


@pytest.mark.parametrize("settlement", ["clear", "withhold", "interrupt"])
def test_settlement_and_restricted_funds(settlement: str, tmp_path: Path) -> None:
    out = engine.execute(corrected(), [case(settlement=settlement)], tmp_path / "e.db", opening=5_000_000)
    if settlement == "clear":
        assert out["summary"]["revenue"] == 1_000_000
        assert out["outcomes"][0]["state"] == "released"
    else:
        assert out["summary"]["revenue"] == out["summary"]["unrestrictedEarned"] == 0
    if settlement == "withhold":
        assert out["outcomes"][0]["state"] == "refunded"
    if settlement == "interrupt":
        assert out["summary"]["custodyRestricted"] == 1_000_000


def test_entire_cohort_and_global_clock(tmp_path: Path) -> None:
    cohort = [case(id="a", observed_value=0), case(id="b"), case(id="c", buyer_cash=0)]
    out = engine.execute(corrected(), cohort, tmp_path / "e.db", opening=5_000_000)
    assert len(out["outcomes"]) == 3
    assert out["summary"]["expenses"] == 140_000
    ticks = [x["tick"] for x in out["trace"]]
    assert ticks == sorted(ticks)


def test_no_evidence_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "e.db"
    engine.execute(corrected(), [case()], path, opening=5_000_000)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        engine.execute(corrected(), [case()], path, opening=5_000_000)
    assert path.read_bytes() == before


def test_operation_budget_preserves_costs(tmp_path: Path) -> None:
    out = engine.execute(corrected(), [case()], tmp_path / "e.db", opening=5_000_000, max_operations=1)
    assert out["outcomes"][0]["outcome"] == "BUDGET_STOP"
    assert out["summary"]["expenses"] == 10_000


def test_observation_cannot_be_read_before_measurement(tmp_path: Path) -> None:
    p = corrected()
    steps = p["steps"]
    steps.remove({"op": "measure"})
    steps.insert(4, {"op": "measure"})
    out = engine.execute(p, [case()], tmp_path / "e.db", opening=5_000_000)
    assert out["outcomes"][0]["outcome"] == "REFUSED"
    assert out["summary"]["revenue"] == 0


def test_duplicate_cases_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        engine.execute(corrected(), [case(), deepcopy(case())], tmp_path / "e.db", opening=5_000_000)
