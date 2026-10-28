# SPDX-License-Identifier: Apache-2.0
"""Control tests for supplementary contract projection; no empirical claims."""

import copy
import importlib
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))
frontier = importlib.import_module("expansion_frontier")


def raw_fixture():
    raw = {"offerings": {}}
    for offering in ("nominal", "robust"):
        raw["offerings"][offering] = {}
        for mode in ("beta", "v1", "v2", "composed", "beta_plus", "shuffled"):
            ratio = 0.75 if mode == "v2" else 0.9
            data = {}
            for split in ("development", "confirmation"):
                data[split + "_records"] = [
                    {"case_id": split + "-good", "objective_ratio": ratio, "objective": ratio,
                     "accepted": True, "valid": True},
                    {"case_id": split + "-invalid", "objective_ratio": 0.1, "objective": 0.1,
                     "accepted": False, "valid": False},
                ]
                data[split + "_n"] = 2
                data[split + "_successes"] = 1
            raw["offerings"][offering][mode] = data
    return raw


def test_all_methods_receive_same_strict_tier_and_primary_is_untouched():
    raw = raw_fixture()
    original = copy.deepcopy(raw)
    result = frontier.tier_calibration(raw, 0.25)
    assert raw == original
    for modes in result["offerings"].values():
        for mode, data in modes.items():
            assert data["confirmation_successes"] == (1 if mode == "v2" else 0)
            assert data["confirmation_records"][0]["primary_accepted"] is True
            assert data["confirmation_records"][1]["accepted"] is False


def test_hypothetical_catchup_is_explicit_and_applied_in_both_splits():
    raw = raw_fixture()
    result = frontier.tier_calibration(raw, 0.25, catchup=True)
    for modes in result["offerings"].values():
        for split in ("development", "confirmation"):
            row = modes["beta"][split + "_records"][0]
            assert row["catchup_source_mode"] == "v2"
            assert row["hypothetical_beta"] is True
            assert row["accepted"] is True
            assert modes["beta"][split + "_successes"] == 1


def test_unmatched_case_pools_refuse():
    raw = raw_fixture()
    raw["offerings"]["nominal"]["v1"]["confirmation_records"][0]["case_id"] = "different"
    with pytest.raises(ValueError, match="identical unique cases"):
        frontier.tier_calibration(raw, 0.2)


def test_pairing_requires_identical_seed_order():
    with pytest.raises(ValueError, match="not matched"):
        frontier.paired([{"seed": 1, "profit_usd": 10}], [{"seed": 2, "profit_usd": 10}])
