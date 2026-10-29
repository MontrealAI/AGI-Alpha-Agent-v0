# SPDX-License-Identifier: Apache-2.0
"""Actual numerical lineage and cross-route falsification for the progressive diagnostic."""

from copy import deepcopy
from pathlib import Path
import hashlib
import json
import shutil

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


@pytest.mark.parametrize("execution,cost", [(1, 0), (5, 4), (-1, 5), (True, 5), (1, False), (1, "1")])
def test_undercounted_or_malformed_resource_cost_is_refused(execution, cost):
    with pytest.raises(ValueError):
        audit.delivered_cost(execution, cost)


def test_cost_includes_execution_and_optional_serialization():
    audit.delivered_cost(123, 123)
    audit.delivered_cost(123, 145)


@pytest.mark.parametrize("seed", ["not a seed", True, -1, 2**63, None])
def test_malformed_seed_is_refused_before_reconstructing_panel(history, seed):
    with pytest.raises(ValueError, match="seed"):
        audit.expected_panel(history[0]["target"], seed)


def test_independent_seed_reconstruction_matches_each_declared_regime_and_family(history):
    base = history[0]["target"]
    expected = audit.expected_panel(base, 123456789)
    actual = []
    for stage in trial.STAGES:
        for family in ("same-route", "withheld-stops"):
            for target in trial.experiment.make_panel(base, 123456789 + stage, 2, f"evaluation-{stage}-{family}"):
                if family == "withheld-stops":
                    target = trial.withheld(target)
                actual.append({"stage": stage, "family": family, "target": trial.compact(target)})
    assert actual == expected
    assert audit.expected_panel(base, 123456790) != expected


def test_historical_mode_cannot_admit_an_unrecognized_trial(tmp_path):
    with pytest.raises(ValueError, match="unrecognized historical source freeze"):
        audit.historical_source_root(tmp_path, "0" * 64)


def repaired_fixture(tmp_path):
    published = ROOT / "evidence/progressive-experience-20261029/cycle-1"
    directory = tmp_path / "adversarial-fixture-not-confirmation"
    directory.mkdir()
    for p in published.iterdir():
        if p.is_file():
            shutil.copyfile(p, directory / p.name)
    freeze = verifier.read(directory / "freeze.json")
    for name in freeze["sources"]:
        raw = (ROOT / name).read_bytes()
        freeze["sources"][name] = hashlib.sha256(raw).hexdigest()
        target = directory / "source-snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (directory / "freeze.json").write_bytes(verifier.canonical(freeze) + b"\n")
    return directory, hashlib.sha256((directory / "freeze.json").read_bytes()).hexdigest()


def test_actual_verifier_rejects_seed_substitution(tmp_path):
    directory, freeze = repaired_fixture(tmp_path)
    seed = verifier.read(directory / "seed.json")
    seed["seed"] = "not a seed"
    (directory / "seed.json").write_bytes(verifier.canonical(seed))
    with pytest.raises(ValueError, match="seed"):
        audit.verify(directory, freeze)


def test_actual_verifier_rejects_zeroed_delivered_costs(tmp_path):
    directory, freeze = repaired_fixture(tmp_path)
    rows = [json.loads(line) for line in (directory / "costs.jsonl").read_text().splitlines()]
    for row in rows:
        row["cpu_ns"] = 0
    (directory / "costs.jsonl").write_bytes(b"\n".join(verifier.canonical(row) for row in rows) + b"\n")
    with pytest.raises(ValueError, match="understates"):
        audit.verify(directory, freeze)
