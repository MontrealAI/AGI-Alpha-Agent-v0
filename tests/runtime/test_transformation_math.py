# SPDX-License-Identifier: Apache-2.0
"""Exact finite mathematical checks and durable driver authority/cost regressions."""
from __future__ import annotations

import copy
import itertools
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import ValidationError

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest
from alpha_factory_v1.core.runtime.successor import transformation_math as m


def case(**changes):
    return m.AffineCase.model_validate(
        {"modulus": 5, "multiplier": 2, "increment": 1, "initial": 0, "steps": 31, **changes}
    )


def request(development=None, confirmation=None, **charter_changes):
    development = development or [case(modulus=7, steps=127)]
    confirmation = confirmation or [case(steps=127)]
    charter = {"permitted_actions": ["construct-bounded", "evaluate-local", "write-artifact"], **charter_changes}
    return m.MathRequest(
        campaign_id="a013d055-8f61-44ec-8a33-99013116e501",
        charter=m.MathCharter.model_validate(charter),
        development=development,
        confirmation_digest=digest("affine-confirmation", confirmation),
        confirmation_count=len(confirmation),
    )


def prepared(tmp_path, req=None):
    req = req or request()
    loop = m.AffineDiscovery(Journal.initialize(tmp_path / "state"))
    queued = loop.create(req)
    loop.approve(req.campaign_id, queued["binding_digest"])
    return loop, req


def matrix_reference(c):
    # Separately expressed 2x2 integer matrix powers, not the driver's pair formula.
    result = [[1, 0], [0, 1]]
    base = [[c.multiplier, c.increment], [0, 1]]
    for _ in range(c.steps):
        result = [[sum(base[i][k] * result[k][j] for k in range(2)) % c.modulus for j in range(2)] for i in range(2)]
    return (result[0][0] * c.initial + result[0][1]) % c.modulus


def test_exhaustive_small_domains_and_independent_matrix_check():
    checked = 0
    for modulus in range(2, 7):
        for a, b, x in itertools.product(range(modulus), repeat=3):
            for steps in range(17):
                c = case(modulus=modulus, multiplier=a, increment=b, initial=x, steps=steps)
                values = [
                    m.execute(c, m.MathProgram(algorithm=name), m.Meter(1_000_000))["value"] for name in m.PROGRAMS
                ]
                assert len(set(values)) == 1
                if steps in (0, 3, 16):
                    assert values[0] == matrix_reference(c)
                checked += 1
    assert checked == 7480


def test_algebraic_composition_identity_associativity_and_binary_invariant():
    for modulus in range(2, 6):
        pairs = list(itertools.product(range(modulus), repeat=2))
        for p, q in itertools.product(pairs, repeat=2):
            composed = m._compose(p, q, modulus, m.Meter(1_000_000))
            for x in range(modulus):
                assert (composed[0] * x + composed[1]) % modulus == (
                    p[0] * ((q[0] * x + q[1]) % modulus) + p[1]
                ) % modulus
        for p, q, r in itertools.product(pairs, repeat=3):
            meter = m.Meter(1_000_000)
            assert m._compose(p, m._compose(q, r, modulus, meter), modulus, meter) == m._compose(
                m._compose(p, q, modulus, meter), r, modulus, meter
            )
    # Finite tests supplement the printed general algebraic argument; they are no proof-assistant certificate.


def test_exact_cost_arithmetic_and_cycle_tail_control():
    for n in range(65):
        c = case(steps=n)
        direct = m.execute(c, m.MathProgram(algorithm="direct"), m.Meter(1_000_000))
        pair = m.execute(c, m.MathProgram(algorithm="representation-only"), m.Meter(1_000_000))
        binary = m.execute(c, m.MathProgram(algorithm="affine-compose"), m.Meter(1_000_000))
        assert direct["units"] == 4 * n
        assert pair["units"] == 6 * n + (3 if n else 0)
        assert binary["units"] == (8 * n.bit_length() + 5 * n.bit_count() - 2 if n else 0)
    c = case(modulus=8, multiplier=2, increment=0, initial=1, steps=4096)
    assert m.execute(c, m.MathProgram(algorithm="cycle"), m.Meter(1_000_000))["value"] == 0
    assert m.execute(c, m.MathProgram(algorithm="affine-compose"), m.Meter(1_000_000))["value"] == 0


def test_production_without_closed_representation_and_unsafe_period_shortcut_refused():
    with pytest.raises(ValidationError):
        m.MathProgram.model_validate({"algorithm": "scalar-binary"})
    # Dropping the affine state and assuming period=m is false, even in the admitted domain.
    c = case(modulus=5, multiplier=2, increment=0, initial=1, steps=5)
    shortcut = c.model_copy(update={"steps": c.steps % c.modulus})
    assert m.execute(c, m.MathProgram(algorithm="direct"), m.Meter(100))["value"] == 2
    assert m.execute(shortcut, m.MathProgram(algorithm="direct"), m.Meter(100))["value"] == 1


@pytest.mark.parametrize(
    "change",
    [
        {"modulus": 1},
        {"steps": -1},
        {"steps": 4097},
        {"multiplier": 5},
        {"steps": True},
        {"steps": 1.0},
        {"quadratic_coefficient": 1},
        {"time_varying_increment": [0, 1]},
    ],
)
def test_non_affine_malformed_and_out_of_domain_cases_reject(change):
    with pytest.raises(ValidationError):
        case(**change)


def test_census_frozen_candidate_and_strong_controls_prevent_false_superiority(tmp_path):
    req = m.example_request("a013d055-8f61-44ec-8a33-99013116e501")
    loop, req = prepared(tmp_path, req)
    frozen = loop.freeze(req.campaign_id)
    assert frozen["freeze"]["manifest"]["selected"] == "affine-compose"
    selected = copy.deepcopy(frozen["freeze"])
    record = loop.confirm(req.campaign_id, m.confirmation_cases(), frozen["freeze"]["digest"])
    result = record["result"]
    assert result["all_exact"] and result["case_count"] == 864
    expected_path = Path(__file__).resolve().parents[2] / "examples/transformational-math/expected-results.json"
    expected = json.loads(expected_path.read_text())
    assert expected["driverSha256"] == hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
    assert result == expected["result"] and record["spent"] == expected["spent"]
    assert frozen["freeze"]["manifest"]["development_units"] == expected["developmentUnits"]
    assert (
        hashlib.sha256(
            json.dumps(record["confirmation"]["rows"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        == expected["confirmationRowsSha256"]
    )
    assert result["totals"] == {
        "direct": 242496,
        "cycle": 30204,
        "affine-compose": 43488,
        "representation-only": 365904,
        "automated": 43488,
        "unrestricted-oracle": sum(
            min(row["methods"][name]["units"] for name in m.PROGRAMS) for row in record["confirmation"]["rows"]
        ),
    }
    assert result["decision"] == "retain-stronger-cycle-control"
    assert result["gain_vs_direct_units"] == 199008
    assert result["gain_vs_hand_engineered_units"] == -13284
    assert result["beats_unrestricted"] is False
    assert result["net_one_census_units_vs_direct"] < 0
    assert record["approval"] is None and record["freeze"] == selected
    assert result["full_campaign_execution_units"] == record["spent"]["execution_units"]
    assert result["full_campaign_search_units"] == record["spent"]["search_units"]
    assert result["full_campaign_logical_units"] == sum(record["spent"].values())
    additional = result["minimum_additional_identical_workloads_to_break_even"]
    setup, baseline, chosen = (
        result["full_campaign_logical_units"],
        result["totals"]["direct"],
        result["totals"]["automated"],
    )
    assert setup + additional * chosen <= (1 + additional) * baseline
    assert additional == 0 or setup + (additional - 1) * chosen > additional * baseline
    envelope = loop.envelope(req.campaign_id)
    assert envelope["authority"] == "none" and envelope["native_v1_compatible"] is False
    assert len(canonical(envelope)) < 2_000_000
    assert (
        m.MathPackage.model_validate(record["freeze"]["manifest"]["package"]).proof_status
        == "argument-present-not-machine-checked"
    )


def test_permission_and_global_stop_precede_any_construction(tmp_path, monkeypatch):
    journal = Journal.initialize(tmp_path / "state")
    loop, req = m.AffineDiscovery(journal), request()
    queued = loop.create(req)
    monkeypatch.setattr(m, "execute", lambda *a: pytest.fail("construction occurred before permission"))
    with pytest.raises(PermissionError):
        loop.freeze(req.campaign_id)
    loop.approve(req.campaign_id, queued["binding_digest"])
    journal.control(True)
    with pytest.raises(Conflict, match="STOP"):
        loop.freeze(req.campaign_id)
    assert loop.show(req.campaign_id)["spent"] == {"execution_units": 0, "search_units": 0}


def test_changed_charter_or_instrument_requires_new_campaign_and_approval(tmp_path, monkeypatch):
    loop, req = prepared(tmp_path)
    changed = req.model_copy(
        update={"charter": req.charter.model_copy(update={"budgets": m.DiscoveryBudget(search_units=0)})}
    )
    with pytest.raises(Conflict):
        loop.create(changed)
    monkeypatch.setitem(m.COST_RULE, "scalar_add_multiply_modulo", 2)
    with pytest.raises(Conflict, match="changed"):
        loop.freeze(req.campaign_id)


def test_duplicate_freeze_and_confirmation_are_idempotent_across_restart_and_threads(tmp_path):
    loop, req = prepared(tmp_path)
    with ThreadPoolExecutor(2) as workers:
        frozen = list(workers.map(lambda _: loop.freeze(req.campaign_id), range(2)))
    assert frozen[0] == frozen[1]
    loop = m.AffineDiscovery(Journal(tmp_path / "state"))
    cases = [case(steps=127)]
    with ThreadPoolExecutor(2) as workers:
        completed = list(
            workers.map(lambda _: loop.confirm(req.campaign_id, cases, frozen[0]["freeze"]["digest"]), range(2))
        )
    assert completed[0] == completed[1]
    with pytest.raises(Conflict, match="terminal"):
        loop.confirm(req.campaign_id, [case(steps=126)], frozen[0]["freeze"]["digest"])
    assert loop.journal.verify()["events"] > 0


def test_confirmation_requires_whole_frozen_fresh_complete_input(tmp_path):
    fresh = [case(steps=127), case(steps=126)]
    loop, req = prepared(tmp_path, request(confirmation=fresh))
    frozen = loop.freeze(req.campaign_id)
    for cases in [fresh[:1], list(reversed(fresh)), [case(steps=127), case(steps=127)]]:
        with pytest.raises(ValueError, match="entire committed"):
            loop.confirm(req.campaign_id, cases, frozen["freeze"]["digest"])
    with pytest.raises(Conflict, match="freeze"):
        loop.confirm(req.campaign_id, fresh, "a" * 64)
    assert loop.show(req.campaign_id)["state"] == "frozen"
    other = tmp_path / "other"
    other.mkdir()
    reused = [case(modulus=7, steps=127)]
    loop, req = prepared(other, request(confirmation=reused))
    frozen = loop.freeze(req.campaign_id)
    with pytest.raises(ValueError, match="fresh distinct"):
        loop.confirm(req.campaign_id, reused, frozen["freeze"]["digest"])


def test_budget_partial_confirmation_is_terminal_charged_and_has_no_gain(tmp_path):
    dev, fresh = [case(steps=1)], [case(steps=127)]
    req = request(development=dev, confirmation=fresh, budgets=m.DiscoveryBudget(search_units=100, execution_units=40))
    loop, req = prepared(tmp_path, req)
    frozen = loop.freeze(req.campaign_id)
    assert frozen["state"] == "frozen"
    before = frozen["spent"]["execution_units"]
    done = loop.confirm(req.campaign_id, fresh, frozen["freeze"]["digest"])
    assert done["state"] == "completed" and done["result"]["metrics"] is None
    assert done["result"]["reason"] == "incomplete-confirmation-budget"
    assert before < done["spent"]["execution_units"] <= 40
    assert done["confirmation"]["complete"] is False and done["approval"] is None
    assert loop.confirm(req.campaign_id, fresh, frozen["freeze"]["digest"]) == done


def test_development_budget_stop_and_zero_horizon_tie_keep_incumbent(tmp_path):
    loop, req = prepared(tmp_path, request(budgets=m.DiscoveryBudget(execution_units=0)))
    done = loop.freeze(req.campaign_id)
    assert done["result"]["metrics"] is None and done["freeze"] is None
    sub = tmp_path / "tie"
    sub.mkdir()
    loop, req = prepared(sub, request(development=[case(steps=0)]))
    frozen = loop.freeze(req.campaign_id)
    assert frozen["freeze"]["manifest"]["selected"] == "direct"


def test_mutating_caller_request_after_queue_cannot_expand_stored_authority(tmp_path):
    loop, req = prepared(tmp_path)
    req.charter.permitted_actions.clear()
    assert loop.show(req.campaign_id)["request"]["charter"]["permitted_actions"]


@pytest.mark.parametrize(
    "change",
    [
        {"purpose": "Solve arbitrary recurrence"},
        {"publicOnly": 1},
        {"settlement": "USDC"},
        {"permitted_actions": ["shell"]},
    ],
)
def test_goal_permission_and_payment_expansion_reject(change):
    with pytest.raises(ValidationError):
        request(**change)


def test_computation_falsifier_is_terminal_retains_outputs_and_spent_units(tmp_path, monkeypatch):
    loop, req = prepared(tmp_path)
    frozen = loop.freeze(req.campaign_id)
    original = m.execute

    def faulty(c, program, meter):
        result = original(c, program, meter)
        if program.algorithm == "cycle":
            result["value"] = (result["value"] + 1) % c.modulus
        return result

    monkeypatch.setattr(m, "execute", faulty)
    done = loop.confirm(req.campaign_id, [case(steps=127)], frozen["freeze"]["digest"])
    assert done["result"] == {"decision": "retain-incumbent", "reason": "invalid-confirmation-result", "metrics": None}
    assert done["confirmation"]["rows"][0]["all_exact"] is False
    assert done["spent"]["execution_units"] > frozen["spent"]["execution_units"]
    assert done["approval"] is None
    assert loop.confirm(req.campaign_id, [case(steps=127)], frozen["freeze"]["digest"]) == done


@pytest.mark.parametrize(
    "setup,direct,candidate,expected",
    [(300, 100, 50, 4), (301, 100, 50, 5), (100, 100, 90, 0), (90, 100, 110, 0), (101, 100, 100, None)],
)
def test_break_even_exact_ties_and_already_amortized_campaigns(setup, direct, candidate, expected):
    assert m.additional_workloads_to_break_even(setup, direct, candidate) == expected
    if expected is not None:
        assert setup + expected * candidate <= (1 + expected) * direct
        assert expected == 0 or setup + (expected - 1) * candidate > expected * direct
