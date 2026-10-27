# SPDX-License-Identifier: Apache-2.0
"""Synthetic control worlds; these tests are not empirical economic evidence."""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "src" / "economics.py"
SPEC = importlib.util.spec_from_file_location("study_economics", PATH)
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def calibration(beta_successes=12, specialist_successes=24, accepted=True):
    return {
        offering: {
            mode: {"development_n": 24,
                   "development_successes": beta_successes if mode in ("beta", "beta_plus") else specialist_successes,
                   "confirmation_records": [{"case_id": "synthetic-control", "accepted": accepted}]}
            for mode in module.MODES
        } for offering in module.OFFERS
    }


def config(**changes):
    result = copy.deepcopy(module.DEFAULTS)
    result.update(changes)
    return result


def scenario(**changes):
    return dict(module.SCENARIOS["central"], **changes)


def policy(name):
    return next(p for p in module.POLICIES if p.name == name)


def test_cash_and_accrual_are_separate_and_expenses_are_disjoint():
    cfg = config(days=3, collection_delay_days=7, robust_fraction_prior=0)
    run = module.simulate(policy("beta"), scenario(lead_probability=1, buyer_intercept=30, correlated_failure=0),
                          991, calibration(), cfg, record=True)
    assert sum(run["accepted"].values()) > 0
    assert run["collections_usd"] == 0
    assert run["earned_usd"] == pytest.approx(run["receivables_usd"])
    assert run["profit_usd"] - run["cash_profit_usd"] == pytest.approx(run["receivables_usd"])
    assert run["ending_cash_usd"] == pytest.approx(cfg["capital_usd"] + run["collections_usd"] - run["expenses_usd"])
    assert len({e["event_id"] for e in run["events"]}) == len(run["events"])
    for bucket in "ABC":
        assert run["buckets"][bucket] == pytest.approx(sum(e["amount_usd"] for e in run["events"] if e["bucket"] == bucket))


@pytest.mark.parametrize("seed", [70111, 70112, 70113])
def test_ordinary_library_is_economically_identical(seed):
    cfg = config(days=35)
    a = module.simulate(policy("opportunity"), scenario(), seed, calibration(), cfg, record=True)
    b = module.simulate(policy("library"), scenario(), seed, calibration(), cfg, record=True)
    assert a["actions"] == b["actions"]
    for field in ("profit_usd", "cash_profit_usd", "ending_cash_usd", "buckets", "stats", "attempts", "accepted"):
        assert a[field] == b[field]
    assert [{k: v for k, v in e.items() if k != "event_id"} for e in a["events"]] == [
        {k: v for k, v in e.items() if k != "event_id"} for e in b["events"]]


def test_quotes_do_not_read_hidden_outcomes_before_a_sale():
    class HiddenPool:
        def __len__(self):
            raise AssertionError("hidden outcomes were inspected before a committed sale")

        def __getitem__(self, key):
            raise AssertionError("hidden outcomes were inspected before a committed sale")

    cal = calibration()
    for modes in cal.values():
        for row in modes.values():
            row["confirmation_records"] = HiddenPool()
    run = module.simulate(policy("opportunity"), scenario(lead_probability=1, buyer_intercept=-1000),
                          233, cal, config(days=1), record=True)
    assert run["stats"]["quoted"] > 0
    assert sum(run["attempts"].values()) == 0


def test_first_investment_cannot_depend_on_future_technical_outcomes():
    cfg = config(days=1, offer_validation_usd=1)
    cfg["investment_costs"]["launch"] = 1
    a = module.simulate(policy("opportunity"), scenario(), 777, calibration(accepted=True), cfg, record=True)
    b = module.simulate(policy("opportunity"), scenario(), 777, calibration(accepted=False), cfg, record=True)
    aa = [a for a in a["actions"] if a["action"] != "production"]
    bb = [a for a in b["actions"] if a["action"] != "production"]
    assert aa == bb
    assert aa and aa[0]["action"] == "launch"


def test_unproductive_optional_capabilities_are_skipped():
    cal = calibration(beta_successes=24, specialist_successes=0, accepted=True)
    cfg = config(days=25, robust_fraction_prior=0)
    result = module.simulate(policy("shared_gym"), scenario(lead_probability=1, buyer_intercept=30, correlated_failure=0),
                             777, cal, cfg, record=True)
    assert result["stats"]["accepted_source_jobs"] >= 8
    assert not any(a["action"] in {"retain", "share", "gym", "compose"} for a in result["actions"])
    assert result["buckets"]["B"] == 0
    assert result["buckets"]["C"] == 0


@pytest.mark.parametrize("amount", [-1.0, float("nan"), float("inf")])
def test_invalid_expense_does_not_become_zero(amount):
    with pytest.raises(ValueError, match="expense"):
        module.simulate(policy("beta"), scenario(lead_probability=0), 1, calibration(),
                        config(days=1, daily_overhead_usd=amount))


def test_unprofitable_operation_stops_with_cash_remaining():
    cfg = config(days=90, lead_probability_prior=0, buyer_intercept_prior=-3)
    result = module.simulate(policy("beta"), scenario(lead_probability=0), 999, calibration(), cfg, record=True)
    assert result["stats"]["stopped_day"] == cfg["stop_after_days"]
    assert result["ending_cash_usd"] > cfg["reserve_usd"]
    stops = [a for a in result["actions"] if a["action"] == "stop"]
    assert len(stops) == 1
    assert all(e["day"] < stops[0]["day"] for e in result["events"])
    expected = cfg["common_automation_setup_usd"] + cfg["daily_overhead_usd"] * cfg["stop_after_days"]
    assert result["expenses_usd"] == expected


def test_retention_waits_for_eight_successful_source_engagements():
    cfg = config(days=30, robust_fraction_prior=0)
    cfg["campaign_success_probability"]["retain"] = 1.0
    result = module.simulate(module.Policy("source-gate", retain=True),
                             scenario(lead_probability=1, buyer_intercept=30, correlated_failure=0),
                             777, calibration(beta_successes=4), cfg, record=True)
    retained = [a for a in result["actions"] if a["action"] == "retain"]
    assert len(retained) == 1
    earlier = [a for a in result["actions"] if a["action"] == "production" and a["day"] < retained[0]["day"]
               and a["agent"] == 0 and a["offer"] == "nominal" and a["accepted"]]
    assert len(earlier) >= 8


def test_failed_campaign_is_charged_once_and_never_silently_admitted():
    cfg = config(days=30, robust_fraction_prior=0)
    result = module.simulate(module.Policy("failed-retention", retain=True),
                             scenario(lead_probability=1, buyer_intercept=30, correlated_failure=0,
                                      campaign_probability_scale=0),
                             777, calibration(beta_successes=4), cfg, record=True)
    campaigns = [a for a in result["actions"] if a["action"] == "retain"]
    assert len(campaigns) == 1 and campaigns[0]["candidate_accepted"] is False
    assert result["buckets"]["B"] == cfg["investment_costs"]["retain"]
    assert all(a["mode"] == "beta" for a in result["actions"] if a["action"] == "production")


def test_correction_cannot_rewrite_the_observed_first_pass_rate(monkeypatch):
    probabilities = []
    original = module.best_quote

    def record_quote(offer, p, *args, **kwargs):
        probabilities.append((offer, p))
        return original(offer, p, *args, **kwargs)

    monkeypatch.setattr(module, "best_quote", record_quote)
    cal = calibration(beta_successes=12, accepted=False)
    cfg = config(days=3, robust_fraction_prior=0, correction_recovery_probability=1)
    result = module.simulate(policy("beta"), scenario(lead_probability=1, buyer_intercept=30, correlated_failure=0),
                             777, cal, cfg, record=True)
    assert result["accepted"]["nominal"] == result["attempts"]["nominal"] > 0
    initial = sum(module.prior(cal, "nominal", "beta")[:1]) / sum(module.prior(cal, "nominal", "beta"))
    observed = [p for offer, p in probabilities if offer == "nominal"]
    assert max(observed) <= initial
    assert min(observed) < initial


def test_seed_cash_cannot_finance_the_surplus_expansion_arm():
    # Enough seed cash, congestion and capacity to tempt expansion, but high
    # avoidable overhead prevents any collected operating surplus.
    cfg = config(days=35, capital_usd=800000, daily_capacity_hours=2,
                 daily_overhead_usd=6000, robust_fraction_prior=0)
    result = module.simulate(module.Policy("earned-funding-only", expand=True),
                             scenario(lead_probability=1, buyer_intercept=30, correlated_failure=0),
                             10191, calibration(beta_successes=24), cfg, record=True)
    assert result["stats"]["capacity_declined"] >= 5
    assert result["cash_profit_usd"] < 0
    assert result["ending_cash_usd"] > cfg["reserve_usd"] + cfg["expansion_usd"]
    assert not any(action["action"] == "expand" for action in result["actions"])
