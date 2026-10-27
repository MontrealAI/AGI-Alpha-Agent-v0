# SPDX-License-Identifier: Apache-2.0
"""Independent accounting and information-boundary checks on small synthetic worlds."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("invention_economics", HERE / "economics.py")
assert SPEC is not None and SPEC.loader is not None
econ = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(econ)


def config() -> dict:
    cfg = json.loads((HERE / "economic_protocol.json").read_text())
    cfg["horizon_weeks"] = 12
    cfg["runoff_weeks"] = 12
    return cfg


def timings() -> dict:
    ordinary = {"direct": 0.012, "ilu_gmres": 0.008, "spectral_pcg": 0.006, "v1": 0.005, "v2": 0.004}
    return {
        "thermal": dict(ordinary),
        "transfer": dict(ordinary),
        "ood": dict(ordinary),
        "composition": {
            "competent_generalist": 0.2,
            "fixed_sensor_ablation": 0.16,
            "solver_only": 0.12,
            "v1_combination": 0.18,
            "combination": 0.15,
        },
    }


def profile(cfg: dict) -> dict:
    return {
        **cfg["profiles"]["reference"],
        "weekly_opportunities": 6,
        "quality": 0.99,
        "trust": 1,
        "obsolescence_week": 999,
        "collection_default": 0,
        "correlated_error": 0,
    }


def run(
    policy: str = "beta",
    *,
    cfg: dict | None = None,
    scenario: dict | None = None,
    measured: dict | None = None,
    force: bool = False,
    campaign: dict | None = None,
) -> tuple:
    cfg = cfg or config()
    return econ.run_world(
        3333,
        policy,
        scenario or profile(cfg),
        cfg,
        {family: 0.3 for family in cfg["offerings"]},
        timings(),
        measured or timings(),
        force_candidate=force,
        trace=True,
        campaign=campaign,
    )


def test_tariff_bundles_reconcile_and_invalid_context_is_refused() -> None:
    cfg = config()
    assert {family: econ.model_bundle_cost(offer, cfg) for family, offer in cfg["offerings"].items()} == {
        "thermal": 66,
        "transfer": 96,
        "composition": 138,
    }
    bad = copy.deepcopy(cfg["offerings"]["thermal"])
    bad["model_token_bundle"][0]["calls"] = 1
    with pytest.raises(ValueError, match="short-context"):
        econ.model_bundle_cost(bad, cfg)


def test_subcent_cost_is_retained_exactly() -> None:
    assert econ.money(0.002) == 2_000_000
    assert econ.usd(500 * econ.money(0.002)) == 1.0
    assert econ.money(0.003 * 3.52 / 3600) > 0


def test_nested_inverse_missions_are_not_replaced_by_single_forward_solve(tmp_path: Path) -> None:
    path = tmp_path / "measurements.json"
    path.write_text(
        json.dumps(
            {
                "records": [
                    {"family": "thermal", "method": "direct", "complete_s": 0.01},
                    {"family": "transfer", "method": "direct", "complete_s": 0.02},
                ],
                "composition": {
                    "mission_records": [
                        {
                            "family": "composition",
                            "method": "competent_generalist",
                            "complete_s": 3.0,
                            "accepted": False,
                        }
                    ]
                },
            }
        )
    )
    table = econ.timing_table(path)
    assert table["composition"]["competent_generalist"] == 3
    assert econ.technical_choices(table)["composition"] == "competent_generalist"
    assert econ.acceptance_table(econ.sample_table(path))["composition"]["competent_generalist"] == 0


def test_complete_ledger_reconstructs_cash_and_excludes_seed_from_profit() -> None:
    row, events = run("shared_gym_composition", force=True)
    assert econ.audit_history(row, events)["verified"]
    expenses = sum(e["amount_nano_usd"] for e in events if e["event"] == "cost")
    collected = sum(e["amount_nano_usd"] for e in events if e["event"] == "collection")
    refunds = sum(e["amount_nano_usd"] for e in events if e["event"] == "refund")
    assert row["profit"] == econ.usd(collected - refunds - expenses)
    assert row["cash"] == pytest.approx(config()["initial_cash"] + row["profit"])
    assert any(e["event"] == "cost" and e["kind"] == "enterprise_setup" for e in events)
    assert row["cash"] >= row["reserve"]


def test_capacity_declines_do_not_pay_serving_and_cannot_consume_a_technical_use() -> None:
    cfg = config()
    cfg["weekly_capacity_hours"] = 6
    scenario = profile(cfg)
    scenario["weekly_opportunities"] = 30
    row, events = run("shared", cfg=cfg, scenario=scenario, force=True)
    denied = {e["job"] for e in events if e["event"] == "order_declined_capacity"}
    served = [e for e in events if e["event"] == "cost" and e["kind"] == "specialist_serving"]
    assert denied and served
    assert not denied.intersection(e["job"] for e in served)
    assert row["technical_uses"] == len(served)


def test_no_credit_closure_preserves_cash_and_paid_commitments() -> None:
    cfg = config()
    cfg["initial_cash"] = cfg["setup_hours"] * cfg["setup_rate"] + 900
    row, events = run(cfg=cfg)
    assert row["closed"] == 1
    assert row["cash"] >= 0
    assert row["cash_rejected"] > 0
    assert econ.audit_history(row, events)["verified"]
    assert not any(e["event"] == "cost" and e["kind"] == "specialist_serving" for e in events)


def test_actual_future_obsolescence_cannot_change_initial_candidate_forecast() -> None:
    cfg = config()
    early, late = profile(cfg), profile(cfg)
    early["obsolescence_week"], late["obsolescence_week"] = 7, 20
    _, a = run("private_gym", cfg=cfg, scenario=early)
    _, b = run("private_gym", cfg=cfg, scenario=late)
    decision_a = next(e for e in a if e["event"] == "candidate_decision")
    decision_b = next(e for e in b if e["event"] == "candidate_decision")
    assert decision_a["week"] < 7
    assert decision_a == decision_b


def test_confirmation_regression_is_realized_not_filtered_from_candidate_selection() -> None:
    measured = timings()
    for family in ["thermal", "transfer", "ood"]:
        measured[family]["v1"] = 0.6
    row, events = run("shared", measured=measured, force=True)
    assert row["technical_uses"] > 0
    assert row["negative_transfer_uses"] == row["technical_uses"]
    assert row["negative_transfer_incremental_cost"] > row["technical_uses"] * 0.002
    decision = next(e for e in events if e["event"] == "candidate_decision")
    assert decision["options"][0]["routes"]["transfer"] == "v1"


def test_unprofitable_optional_training_is_declined_without_a_mandatory_gym_charge() -> None:
    beta, _ = run()
    row, events = run("shared_gym_composition")
    assert row["retained"] == row["trained"] == row["shared"] == 0
    assert row["C"] == 0
    assert row["B"] == config()["candidate_screen_usd"]
    assert beta["profit"] - row["profit"] == pytest.approx(config()["candidate_screen_usd"])
    assert any(e["event"] == "decline_candidate" for e in events)
    decision = next(e for e in events if e["event"] == "candidate_decision")
    assert decision["candidate_outcomes_consulted"] is False


def test_screening_bound_needs_no_candidate_or_future_training_result() -> None:
    cfg = config()
    ordinary_only = {
        family: {
            method: value
            for method, value in methods.items()
            if method in econ.ORDINARY or method == "competent_generalist"
        }
        for family, methods in timings().items()
    }
    first = econ.screening_upper_bound("shared_gym_composition", cfg, timings(), 0)
    second = econ.screening_upper_bound("shared_gym_composition", cfg, ordinary_only, 0)
    assert first == second
    assert first["net_upper_bound_usd"] < 0


def test_forced_gym_pays_all_rank_assessments_once_in_B_and_development_in_C() -> None:
    campaign = econ.zero_campaign()
    campaign.update(
        {
            "founder_delivery_s": 0.7,
            "founder_solution_s": 0.5,
            "founder_basis_construction_s": 0.2,
            "gym_enrichment_s": 5,
            "all_rank_search_assessment_s": 7,
            "candidate_ranks_paid_for": [20, 28, 36, 44],
        }
    )
    row, events = run("private_gym", force=True, campaign=campaign)
    search = [e for e in events if e.get("kind") == "all_rank_search_assessment_compute"]
    assert len(search) == 1 and search[0]["bucket"] == "B"
    assert search[0]["ranks"] == [20, 28, 36, 44]
    assert search[0]["amount_usd"] == pytest.approx(7 * 3.52 / 3600)
    assert row["C"] == pytest.approx(168 + 5 * 3.52 / 3600, abs=2e-9)
    founder = [e for e in events if e.get("founder_solution_generation")]
    assert len(founder) == 1 and founder[0]["bucket"] == "A"
    assert founder[0]["numerical_usd"] == pytest.approx(0.7 * 3.52 / 3600)
    assert not any("extraction" in e.get("kind", "") for e in events)


def test_competent_recipient_keeps_ordinary_sensor_design() -> None:
    routes = econ.candidate_routes("v2", False, timings(), force=True)
    assert routes["composition"] == "combination"
    row, events = run("shared_gym_composition", force=True)
    assert row["trained"] == row["composed"] == 1
    assert any(e.get("kind") == "composition_human_assessment" for e in events)
    assert any(e.get("kind") == "specialist_serving" and e.get("includes_composition") for e in events)


def test_unsettled_receivables_do_not_disappear_because_future_default_is_known_to_simulator() -> None:
    cfg = config()
    cfg["horizon_weeks"], cfg["runoff_weeks"] = 2, 0
    scenario = profile(cfg)
    scenario.update({"collection_default": 1, "collection_delay": 16})
    row, _ = run(cfg=cfg, scenario=scenario)
    assert row["invoices"] > 0
    assert row["receivables"] == row["invoices"]
    assert row["collections"] == row["collection_defaults"] == 0
    assert row["collection_fee_reserve"] > 0


def test_refunds_and_processing_fees_survive_false_acceptance() -> None:
    cfg = config()
    cfg["refund_discovery_probability"] = 1
    scenario = profile(cfg)
    scenario.update({"quality": 0, "correlated_error": 1})
    row, events = run(cfg=cfg, scenario=scenario)
    assert row["bad_accepted"] > 0 and row["refunds"] > 0
    assert any(e.get("kind") == "payment_processing" and e["amount_usd"] > 0 for e in events)
    assert econ.audit_history(row, events)["verified"]


def test_zero_useful_denominators_are_missing_not_fabricated_unit_outcomes() -> None:
    cfg = config()
    scenario = profile(cfg)
    scenario["weekly_opportunities"] = 0
    row, _ = run(cfg=cfg, scenario=scenario)
    assert row["B"] == row["C"] == 0
    assert row["cost_per_useful"] is None
    summary = econ.summarize([row])["beta"]
    assert summary["cost_per_useful_pooled"] is None
    assert summary["false_pass_share"] is None


def test_export_audit_detects_missing_setup_transaction() -> None:
    row, events = run()
    damaged = [e for e in events if e.get("kind") != "enterprise_setup"]
    with pytest.raises(AssertionError, match="disagrees"):
        econ.audit_history(row, damaged)
