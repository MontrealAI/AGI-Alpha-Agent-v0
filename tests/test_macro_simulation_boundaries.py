# SPDX-License-Identifier: Apache-2.0
"""Finite supplied-input scenarios and non-executing draft boundaries."""
import math

import pytest

from alpha_factory_v1.demos.macro_sentinel import simulation_core as core

EVENT = {"yield_10y": 4.0, "yield_3m": 4.5, "stable_flow": 10.0}


@pytest.mark.parametrize("fallback", [False, True])
def test_event_sensitivity_and_repeatability(monkeypatch, fallback):
    if fallback:
        monkeypatch.setattr(core, "np", None)
        monkeypatch.setattr(core, "pd", None)
    first = list(core.MonteCarloSimulator(20, 3, seed=11).simulate(EVENT))
    repeat = list(core.MonteCarloSimulator(20, 3, seed=11).simulate(EVENT))
    changed = list(core.MonteCarloSimulator(20, 3, seed=11).simulate({**EVENT, "stable_flow": 100}))
    assert first == repeat
    ratio = math.exp(3 * 90 * 9.7e-5)
    assert changed == pytest.approx([x * ratio for x in first])
    assert all(math.isfinite(x) and x > 0 for x in first)


def test_shared_quantiles_and_constant_skew(monkeypatch):
    values = [0.5, 0.8, 1.0, 1.2]
    expected = core.MonteCarloSimulator.var(values)
    expected_tail = core.MonteCarloSimulator.cvar(values)
    monkeypatch.setattr(core, "np", None)
    monkeypatch.setattr(core, "pd", None)
    assert expected == pytest.approx(0.545 - 1)
    assert expected_tail == -0.5
    assert core.MonteCarloSimulator.var(values) == expected
    assert core.MonteCarloSimulator.cvar(values) == expected_tail
    assert core.MonteCarloSimulator.skew([1, 1, 1]) == 0
    assert core.MonteCarloSimulator(1, 1).scenario_table([1]) == [
        {"Scenario": name, "ES factor": 1.0} for name in ("Median", "VaR 5 %", "Stress 1 %")
    ]


@pytest.mark.parametrize("value", [0, 1, -1, 49999, -49999, 50000, -50000, 125000])
def test_draft_never_rounds_into_unrequested_contract(value):
    draft = core.draft_order({"es_notional": value})
    assert draft["qty"] == abs(value) // 50000
    assert draft["executionAuthorized"] is False
    assert draft["side"] == (("SELL" if value > 0 else "BUY") if draft["qty"] else "NONE")


@pytest.mark.parametrize("value", [True, "0", None, float("nan"), float("inf"), -float("inf"), 1e16])
def test_draft_rejects_invalid_notional(value):
    with pytest.raises(ValueError):
        core.draft_order({"es_notional": value})


@pytest.mark.parametrize("value", [True, "4", None, float("nan"), float("inf"), 1e7])
def test_simulator_rejects_bad_observations(value):
    with pytest.raises(ValueError):
        core.MonteCarloSimulator(2, 2).simulate({**EVENT, "yield_10y": value})


@pytest.mark.parametrize("data", [[], [0], [-1], [True], [float("nan")], [float("inf")], [10**1000], [1e101]])
def test_metrics_reject_invalid_scenarios(data):
    for method in (core.MonteCarloSimulator.var, core.MonteCarloSimulator.cvar, core.MonteCarloSimulator.skew):
        with pytest.raises(ValueError):
            method(data)


@pytest.mark.parametrize("paths,horizon", [(0, 1), (True, 1), (1, 0), (1, True), (100001, 1), (1, 366)])
def test_simulation_dimensions_are_bounded(paths, horizon):
    with pytest.raises(ValueError):
        core.MonteCarloSimulator(paths, horizon)


def test_entrypoint_tools_use_safe_drafts_and_fallback_rows(monkeypatch):
    import asyncio
    import importlib
    import sys
    from types import ModuleType

    sdk = ModuleType("openai_agents")
    sdk.Agent = object
    sdk.OpenAIAgent = lambda **kwargs: object()
    sdk.Tool = lambda *args: (lambda function: function)
    monkeypatch.setitem(sys.modules, "openai_agents", sdk)
    name = "alpha_factory_v1.demos.macro_sentinel.agent_macro_entrypoint"
    previous = sys.modules.pop(name, None)
    try:
        module = importlib.import_module(name)
        monkeypatch.setattr(core, "np", None)
        monkeypatch.setattr(core, "pd", None)
        monkeypatch.setattr(module, "simulator", core.MonteCarloSimulator(5, 2, seed=3))
        risk = asyncio.run(module.mc_risk(EVENT, portfolio=0))
        assert isinstance(risk["scenarios"], list)
        draft = asyncio.run(module.order_stub(risk["hedge"]))
        assert draft["qty"] == 0
        assert draft["side"] == "NONE"
        assert draft["executionAuthorized"] is False
    finally:
        sys.modules.pop(name, None)
        if previous is not None:
            sys.modules[name] = previous


def test_aggregate_allocation_bound_precedes_rng_creation(monkeypatch):
    if core.np is not None:
        monkeypatch.setattr(core.np.random, "default_rng", lambda *_: pytest.fail("allocated before validation"))
    with pytest.raises(ValueError, match="times horizon"):
        core.MonteCarloSimulator(100_000, 21)
    with pytest.raises(ValueError, match="times horizon"):
        core.MonteCarloSimulator(100_000, 365)


def test_aggregate_boundary_and_default_remain_valid():
    assert core.MonteCarloSimulator(100_000, 20).n == 100_000
    assert core.MonteCarloSimulator().n * core.MonteCarloSimulator().h <= core.MAX_PATH_STEPS
    assert core.draft_order({"es_notional": 0})["assumedContractNotionalUsd"] == 50_000


def test_metric_input_count_bound():
    with pytest.raises(ValueError):
        core.MonteCarloSimulator.var([1] * 100_001)
