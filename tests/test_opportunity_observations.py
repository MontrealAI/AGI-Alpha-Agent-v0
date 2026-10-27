# SPDX-License-Identifier: Apache-2.0
"""Connected observation delivery and honest conditional economics."""

from __future__ import annotations

import hashlib
from fractions import Fraction
from pathlib import Path

from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import EvidenceRef
from scripts.observation_economics import USD, projection, sensitivity
from scripts.record_opportunity_observations import record

ROOT = Path(__file__).resolve().parents[1]
REF = EvidenceRef(journal_key="@authored-sensitivity", record_digest="a" * 64)


def test_positive_projection_is_separate_from_liquidity_and_actual_commitment() -> None:
    item = projection(REF, price=500, jobs=4, construction=100, delivery=50, willingness=1000, seed=0)
    report = item["assessment"]
    amount = report["expected_economic_contribution_micro_usd"]
    assert Fraction(int(amount["numerator"]), amount["denominator"]) == 1103 * USD
    assert report["required_prefunding_micro_usd"] == 380 * USD
    assert not report["liquidity_feasible"] and report["decision"] == "hold"
    assert report["actual_collections_micro_usd"] is None and report["authority_granted"] is False
    assert "uncommitted-participant:hypothetical-recipient" in report["blockers"]
    funded = projection(REF, price=500, jobs=4, construction=100, delivery=50, willingness=1000, seed=5000)[
        "assessment"
    ]
    assert funded["liquidity_feasible"] and funded["decision"] == "hold"
    assert funded["expected_economic_contribution_micro_usd"] == amount


def test_nonparticipation_has_no_fabricated_construction_or_sales() -> None:
    report = projection(REF, price=500, jobs=4, construction=1000, delivery=50, willingness=50, seed=5000)["assessment"]
    branch = report["branches"][0]
    assert branch["scenario_id"] == "nonparticipation" and branch["projected_collections_micro_usd"] == 0
    assert branch["cost_buckets_micro_usd"] == {"A": 0, "B": 10 * USD, "C": 0}


def test_failure_refund_default_and_disjoint_sunk_costs_remain_visible() -> None:
    report = projection(REF, price=500, jobs=4, construction=100, delivery=50, willingness=1000, seed=5000)[
        "assessment"
    ]
    branches = {r["scenario_id"]: r for r in report["branches"]}
    assert branches["payment-default"]["defaulted_receivables_micro_usd"] == 2000 * USD
    assert branches["payment-default"]["projected_collections_micro_usd"] == 0
    assert branches["common-technical-failure"]["cost_buckets_micro_usd"] == {"A": 0, "B": 10 * USD, "C": 100 * USD}
    assert branches["refund"]["refunds_micro_usd"] == 2000 * USD
    assert branches["refund"]["cash_contribution_micro_usd"] == -330 * USD
    assert sum(row["probability_ppm"] for row in report["branches"]) == 1_000_000


def test_entire_sensitivity_is_labeled_and_cannot_post_revenue() -> None:
    report = sensitivity(REF)
    assert len(report["rows"]) == 48 and not report["calibrated"]
    assert report["actual_collections_micro_usd"] == 0 and not report["authority_granted"]
    assert {row["decision"] for row in report["rows"]} == {"hold"}
    assert any(row["liquidity_feasible"] for row in report["rows"])
    assert any(not row["liquidity_feasible"] for row in report["rows"])


def test_actual_tool_path_reuses_parent_lifecycle_and_exact_recipient_artifact() -> None:
    report = record()
    assert report["native_execution"]["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    assert report["native_bundle"]["status"] == "paused-uncertain"
    assert report["native_decision"]["spec"]["disposition"] == "stop"
    assert report["accounting"]["unknown_costs"] and report["accounting"]["complete_cost_profit"] is None
    assert report["conclusion"]["conventional_control"] == "tie"
    assert report["conclusion"]["customer_collections_micro_usd"] == 0
    for name, expected in report["sources"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    donor, recipient = report["families"]
    assert donor["invocation"]["process_id"] != recipient["invocation"]["process_id"]
    assert recipient["invocation"]["retained_source_sha256"] == report["freeze_before_pilot"]["retained_artifact"]
    for family in report["families"]:
        assert family["child_exit"] == 23 and family["child_acknowledgement_bytes"] == 0
        assert family["actual_write_attempts"] == 1 and family["plan"]["probes"] == ["digest"]
        for case in family["cases"]:
            assert (case["finding"]["outcome"] == "satisfied-in-model") == case["independent_byte_acceptance"]
            assert case["finding"]["authority"] == [] and case["write_retried"] is False
    assert report["frontier_comparisons"] == {name: {"status": "not-run"} for name in ("H", "U", "E", "E+")}
