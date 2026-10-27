# SPDX-License-Identifier: Apache-2.0
"""Accounting invariants for the supplemental three-method comparison."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import compute_economics as study


def row(ratio=0.5, seconds=0.1):
    return {"valid": True, "objective_ratio": ratio, "solve_seconds": seconds}


def test_common_quote_requires_only_development_records():
    # The function has no argument through which protected outcomes can enter.
    development = [row() for _ in range(24)]
    quote = study.choose_common_quote(development, 0.3, "nominal", study.economics.DEFAULTS)
    assert quote["development_successes"] == 24
    assert quote["price_usd"] > 0


def test_primary_acceptance_is_not_mutated_by_secondary_contract():
    original = dict(row(0.8), accepted=True)
    assert not study.accepted(original, 0.3)
    assert original["accepted"] is True


def test_cpu_replacement_is_charged_once_including_expected_correction():
    cfg = copy.deepcopy(study.economics.DEFAULTS)
    base = study.delivery(row(), row(), 0.2, "nominal", 1000, cfg)
    more = study.delivery(row(seconds=3.7), row(), 0.2, "nominal", 1000, cfg)
    extra_cpu = 3.6 * cfg["cpu_usd_per_hour"] / 3600
    assert more["incremental_scheduler_cpu_usd"] == pytest.approx(extra_cpu)
    assert more["expected_delivery_A_usd"] - base["expected_delivery_A_usd"] == pytest.approx(
        extra_cpu * (1 + (1 - cfg["systemic_success_prior"]) * cfg["failure_correction_fraction"]))


def test_failure_refund_and_correction_costs_are_included():
    cfg = copy.deepcopy(study.economics.DEFAULTS)
    failed = study.delivery(row(1.2), row(), 0, "nominal", 1000, cfg)
    assert failed["technical_accepted"] is False
    assert failed["expected_collections_usd"] == 1000 * cfg["correction_recovery_probability"]
    assert failed["correction_A_usd"] > 0
    assert failed["refund_A_usd"] == pytest.approx(cfg["refund_processing_usd"] * (1 - cfg["correction_recovery_probability"]))
    assert failed["residual_human_A_usd"] > 0


def test_no_positive_reuse_break_even_for_a_negative_increment():
    assert study.break_even(0.005, -0.01) is None
    assert study.break_even(0.005, 0) is None
    assert study.break_even(700, 200) == 4


def test_unknown_program_cost_cannot_be_booked_as_free():
    with pytest.raises(ValueError):
        study.break_even(float("nan"), 10)
