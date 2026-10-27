# SPDX-License-Identifier: Apache-2.0
"""Scientific-cost assay coverage, precision, and native exemplar boundaries."""

import csv
import gzip
import json
from decimal import Decimal
from pathlib import Path

import pytest

from run_research_lifecycle import (
    HERE,
    actual_research_ledger,
    enterprise_exemplar,
    measurement_inventory,
    observed_assay,
)


def paired(count: int = 36) -> tuple[list[dict], list[dict]]:
    cases = [{"case_id": f"transfer-fixture-{i}", "family": "transfer"} for i in range(count)]
    records = [
        {**case, "method": method, "complete_s": seconds, "accepted": True}
        for case in cases
        for method, seconds in [("spectral_pcg", 0.002), ("v2", 0.001)]
    ]
    return records, cases


def test_all_cases_enter_fixed_modulo_clusters_and_no_cent_rounding_win() -> None:
    records, cases = paired()
    result = observed_assay(records, cases, "spectral_pcg", "v2", compute_increment_usd=Decimal("0.01"))
    assert result["cases_included"] == 36
    assert [row["count"] for row in result["clusters"]] == [3] * 12
    assert [row["cluster"] for row in result["case_assignment"]] == list(range(12)) * 3
    assert Decimal(result["mean_advantage_usd_per_mission"]) > 0
    assert Decimal(result["compute_only_lower_lifetime_net_usd"]) < 0
    assert result["conditional_gate"] == "reject"
    assert all(
        row["candidate"]["netMissionValueCents"] <= row["baseline"]["netMissionValueCents"]
        for row in result["integer_cent_projection_pairs"]
    )


def test_failed_outcome_is_retained_and_blocks_equivalence() -> None:
    records, cases = paired(24)
    records[1]["accepted"] = False
    result = observed_assay(records, cases, "spectral_pcg", "v2")
    assert result["cases_included"] == 24
    assert not result["all_equivalent_outcomes_accepted"]
    assert result["conditional_gate"] == "reject"
    assert result["actual_complete_economic_gate"] == "UNKNOWN_REAL_RESEARCH_COSTS_NOT_ADMISSIBLE"


def test_missing_duplicate_extra_arms_and_small_populations_fail_closed() -> None:
    records, cases = paired()
    with pytest.raises(ValueError, match="Missing paired arm"):
        observed_assay(records[:-1], cases, "spectral_pcg", "v2")
    with pytest.raises(ValueError, match="Duplicate observed"):
        observed_assay(records + [records[0]], cases, "spectral_pcg", "v2")
    with pytest.raises(ValueError, match="population differs"):
        observed_assay(records + [{**records[0], "case_id": "unmanifested"}], cases, "spectral_pcg", "v2")
    records, cases = paired(11)
    with pytest.raises(ValueError, match="At least twelve"):
        observed_assay(records, cases, "spectral_pcg", "v2")


def test_real_cost_unknowns_are_not_zero_and_observed_proxy_is_unpaid() -> None:
    result = actual_research_ledger(
        {"elapsed_s": {"A": "1", "B": "2", "C": "3"}, "unknown_compute": "unmetered research"}, Decimal("3.52")
    )
    assert result["verified_journal"]["valid"]
    assert result["report"]["complete_cost_profit"] is None
    assert result["report"]["available_funds"] is None
    assert result["report"]["collected_revenue"] == 0
    charge_rows = [command["record"] for command in result["commands"] if command["action"] == "charge"]
    assert all(row["paid_micro_usd"] == 0 for row in charge_rows)
    assert sum(row["accrued_micro_usd"] is None for row in charge_rows) == 25


def test_assessment_counts_reference_once_and_each_executed_design_once() -> None:
    rows = [
        {"case_id": "one", "complete_s": 1, "assessment_reference_s": 0.5, "complete_cpu_s": 0.9},
        {"case_id": "one", "complete_s": 2, "assessment_reference_s": 0.5, "complete_cpu_s": 1.9},
    ]
    composition = {
        "solver_records": [{"case_id": "two", "complete_s": 3, "assessment_reference_s": 0.2, "complete_cpu_s": 2.9}],
        "mission_records": [
            {"case_id": "inverse", "sensor_design": "d_optimal", "design_s": value, "inverse_s": 0.01}
            for value in [0.1, 0.2, 0.3]
        ],
    }
    result = measurement_inventory(
        {"paid_founder_snapshot_s": 2, "extra_gym_s": 3},
        {"development_total_s": 10},
        {
            "records": rows,
            "ood_records": [],
            "composition": composition,
            "domain_build_s": 0.1,
            "warmup_s": 0.1,
            "artifact_build_s": 0.1,
        },
    )
    assert Decimal(result["elapsed_s"]["B"]) == Decimal("12.63")
    assert result["true_process_cpu_s"]["B_confirmation_solver_subtotal"] == "5.7"


def test_one_simulated_exemplar_reconciles_gross_collections_and_refunds(tmp_path: Path) -> None:
    cfg = json.loads((HERE / "economic_protocol.json").read_text())
    setup = cfg["setup_hours"] * cfg["setup_rate"]
    a = Decimal(setup + 100) + Decimal("0.000001234")
    b, c, refund, collections = 20, 50, 100, 20000
    profit = collections - refund - a - b - c
    cash = cfg["initial_cash"] + profit
    reserve = cfg["reserve_weeks"] * cfg["weekly_overhead"]
    row = {
        "profile": "reference",
        "world": 900000,
        "policy": "shared_gym_composition",
        "A": a,
        "B": b,
        "C": c,
        "refunds": refund,
        "obligations": 0,
        "collections": collections,
        "profit": profit,
        "cash": cash,
        "reserve": reserve,
        "available_funds": cash - reserve,
    }
    with (tmp_path / "worlds.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    history = {
        "profile": "reference",
        "world": 900000,
        "policy": "shared_gym_composition",
        "events": [
            {"event": "cost", "bucket": bucket, "amount_nano_usd": int(Decimal(str(amount)) * 1_000_000_000)}
            for bucket, amount in [("A", a), ("B", b), ("C", c)]
        ]
        + [
            {"event": kind, "amount_nano_usd": amount * 1_000_000_000}
            for kind, amount in [("seed_capital", cfg["initial_cash"]), ("collection", collections), ("refund", refund)]
        ]
        + [
            {
                "event": "closing_balance",
                "cash_nano_usd": int(cash * 1_000_000_000),
                "base_reserve_nano_usd": reserve * 1_000_000_000,
                "collection_fee_reserve_nano_usd": 0,
                "refund_exposure_nano_usd": 0,
            }
        ],
    }
    with gzip.open(tmp_path / "example_histories.json.gz", "wt") as stream:
        json.dump([history], stream)
    (tmp_path / "results.json").write_text("{}")
    result = enterprise_exemplar(tmp_path)
    assert result["worlds_replayed"] == 1
    assert not result["population_native_replay"]
    assert all(result["reconciliation"].values())
    assert result["native"]["report"]["complete"]
    assert result["native"]["actual_collections_micro_usd"] == 0
    assert result["conversions"]["A"]["rounding_delta_nano_usd"] == -234
    assert result["reconciliation_delta_nano_usd"]["cash"] == 234
