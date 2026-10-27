# SPDX-License-Identifier: Apache-2.0
"""Independent event and native-boundary controls for the study adapter."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "src" / "native_integration.py"
SPEC = importlib.util.spec_from_file_location("study_native", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.mark.parametrize("amount", ["NaN", "Infinity", -1, True, "0.0000001", "1000000001"])
def test_invalid_money_is_refused(amount):
    with pytest.raises(ValueError):
        module.micro_usd(amount)


def test_decimal_money_is_exact():
    assert module.micro_usd("12.345678") == 12345678


def test_duplicate_activity_cannot_move_between_buckets():
    event = {"event_id": "one", "bucket": "A", "amount_usd": "2", "activity": "production"}
    with pytest.raises(ValueError, match="unique"):
        module.normalize({"events": [event, {**event, "bucket": "C"}]})


def test_native_replay_and_independent_signature_verification(tmp_path):
    payload = {"events": [
        {"event_id": "paid-work", "bucket": "A", "amount_usd": "12.23", "activity": "production", "category": "compute"},
        {"event_id": "assessment", "bucket": "B", "amount_usd": "3.01", "activity": "assessment", "category": "acceptance"},
        {"event_id": "gym", "bucket": "C", "amount_usd": "1.11", "activity": "Gym", "category": "compute"}],
        "capital_usd": "100", "collections_usd": "25", "reserve_usd": "10"}
    result = module.replay_account(payload, tmp_path)
    report = result["report"]
    assert report["complete_cost_profit"] == 8650000
    assert report["cash"] == 108650000
    assert report["available_funds"] == 98650000
    exported = json.loads((tmp_path / "journal-public.json").read_text())
    assert module.independently_verify_export(exported) > 60
    broken = copy.deepcopy(exported)
    broken["events"][1]["body"]["document"]["charges"] = {"tampered": 1}
    with pytest.raises(ValueError):
        module.independently_verify_export(broken)


def test_existing_native_authority_and_scope_refusals(tmp_path):
    result = module.run_controls(tmp_path)
    assert result["access"]["different_wallets"]
    assert result["access"]["replay_refusals"] == 2
    assert result["access"]["network_requests"] == 0
    assert result["unsupported_scheduling_scope_refused"]
