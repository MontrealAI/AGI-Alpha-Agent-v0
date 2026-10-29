# SPDX-License-Identifier: Apache-2.0
"""Actual numerical lineage and cross-route falsification for the progressive diagnostic."""

from copy import deepcopy
from pathlib import Path

import pytest

from alpha_factory_v1.core.runtime.retained_experience import solver, verifier
from alpha_factory_v1.core.runtime.structural_transfer import eadarp
from contrib.retained_experience import progressive as trial
from contrib.retained_experience import progressive_check as audit

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def history():
    base = verifier.read(ROOT / "contrib/compounding_discovery/base-target.json")
    result = []
    for i, scale in enumerate(("1", ".9", ".98", ".87")):
        target = deepcopy(base)
        target["id"] = f"development-{i}"
        target["updates"]["window_scale"] = "0" + scale if scale.startswith(".") else scale
        output = solver.solve(target, eadarp.compile_model(target), "highs-ds", True)
        assert verifier.check_output(target, output)["accepted"]
        result.append({"target": target, "output": output})
    return result


def test_incremental_assets_equal_same_history_reset_and_leave_prior_state_unchanged(history):
    early = trial.append_assets(solver.learn([]), history[:2])
    before = verifier.hash_value(early)
    late = trial.append_assets(early, history[2:])
    reset = solver.learn(history)
    assert late == reset
    assert verifier.hash_value(early) == before
    audit.memory_check(late, history)


def test_withheld_routes_recompute_travel_rhs_and_accept_only_the_current_route(history):
    base = history[0]["target"]
    task = trial.withheld(base)
    assert task["routes"] != base["routes"] and task["instance_sha256"] == base["instance_sha256"]
    model = eadarp.compile_model(task)
    memory = solver.learn(history[:1])
    before = eadarp.compile_model(base)
    assert any(
        old["rows"] != new["rows"] and solver.signature(old) == solver.signature(new)
        for old, new in zip(before["vehicles"], model["vehicles"])
    )
    output = solver.PreparedExperience(memory).run(task, model)
    assert verifier.check_output(task, output)["accepted"]
    assert output["artifact"]["task_hash"] == verifier.hash_value(task)


def test_frozen_memory_cannot_claim_additional_history(history):
    with pytest.raises(ValueError, match="lineage"):
        audit.memory_check(solver.learn(history[:2]), history)


def test_ordinary_cache_cannot_hide_a_truncated_point_behind_a_valid_self_hash(history):
    memory = solver.learn(history, points_only=True)
    memory["assets"][0]["point"].pop()
    memory["memory_hash"] = verifier.hash_value({k: v for k, v in memory.items() if k != "memory_hash"})
    with pytest.raises(ValueError, match="ordinary point"):
        audit.memory_check(memory, history, ordinary=True)


def test_compact_evidence_cannot_substitute_instance_or_assumptions(history):
    target = history[0]["target"]
    assert audit.target_from(target, trial.compact(target)) == target
    with pytest.raises(ValueError, match="assumptions or instance"):
        audit.target_from(target, {**trial.compact(target), "instance_sha256": "0" * 64})


def test_zero_history_cannot_contain_retained_assets(history):
    memory = solver.learn([])
    memory["assets"] = solver.learn(history)["assets"]
    memory["memory_hash"] = verifier.hash_value({k: v for k, v in memory.items() if k != "memory_hash"})
    with pytest.raises(ValueError, match="zero-history"):
        audit.memory_check(memory, [])


def test_existing_journal_and_cost_ledger_keep_unadmitted_costs_unknown_without_grants(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    trial.accounting_checkpoint(evidence, {"decision": "DEVELOPMENT_ONLY"})
    report = verifier.read(evidence / "accounting.json")
    assert report["ledger_report"]["complete_cost_profit"] is None
    assert report["ledger_report"]["complete"] is False
    assert len(report["unsigned_cost_inputs"]) == 9
    assert all(r["accrued_micro_usd"] is None for r in report["unsigned_cost_inputs"])
    assert report["grants_created"] == 0 and report["complete_monetary_cost"] is None
    assert not (evidence / "identity.key").exists() and not (evidence / "api.token").exists()
