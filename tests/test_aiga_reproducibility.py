# SPDX-License-Identifier: Apache-2.0
"""Owned RNG and checkpoint fixtures; these tests do not qualify neural training."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys

import numpy as np
import pytest

from alpha_factory_v1.demos.aiga_meta_evolution import meta_evolver as me

PROBE = Path(__file__).parent / "fixtures/aiga_reproducibility_probe.py"
_spec = importlib.util.spec_from_file_location("aiga_reproducibility_probe", PROBE)
assert _spec is not None and _spec.loader is not None
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


@pytest.fixture
def evolver(tmp_path, monkeypatch):
    monkeypatch.setattr(me, "_A2A", None)
    return probe.FixtureEvolver(
        lambda: None, pop_size=4, elitism=1, parallel=False, checkpoint_dir=tmp_path, seed=17, device="cpu"
    )


def run_probe(tmp_path, global_seed, *, seed=17, training=False):
    env = {
        **os.environ,
        "PYTHONHASHSEED": str(global_seed),
        "PYTHONPATH": str(PROBE.parents[2]),
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "CHECKPOINT_DIR": str(tmp_path / "import"),
    }
    command = [
        sys.executable,
        str(PROBE),
        "--seed",
        str(seed),
        "--global-seed",
        str(global_seed),
        "--checkpoint-dir",
        str(tmp_path),
    ]
    if training:
        command.append("--training")
    result = subprocess.run(command, env=env, capture_output=True, text=True, check=True, timeout=60)
    return json.loads(result.stdout)


def test_mutation_owns_rng():
    before = random.getstate()
    a, b = random.Random(1), random.Random(1)
    assert [me.Genome().mutate(a).to_json() for _ in range(20)] == [me.Genome().mutate(b).to_json() for _ in range(20)]
    me.Genome().mutate()
    assert random.getstate() == before


def test_fresh_process_fixture_is_independent_of_global_seeds(tmp_path):
    first = run_probe(tmp_path / "first", 1)
    assert first == run_probe(tmp_path / "second", 839)
    assert first != run_probe(tmp_path / "other", 1, seed=18)


def test_evolution_and_save_do_not_consume_global_rng(evolver, tmp_path):
    before = random.getstate()
    np_before = np.random.get_state()
    me.MetaEvolver(lambda: None, parallel=False, checkpoint_dir=tmp_path / "another")
    evolver.run_generations(3)
    evolver.save()
    assert random.getstate() == before
    after = np.random.get_state()
    assert np_before[0] == after[0] and np_before[2:] == after[2:]
    np.testing.assert_array_equal(np_before[1], after[1])


def test_save_is_observational_and_reset_rewinds(evolver):
    initial = [g.to_json() for g in evolver.population]
    evolver.run_generations(2)
    state = evolver.rng.getstate()
    evolver.save()
    evolver.save()
    assert evolver.rng.getstate() == state
    result = probe.snapshot(evolver)
    evolver.reset()
    assert [g.to_json() for g in evolver.population] == initial
    assert evolver.gen == 0 and not evolver._archive and not evolver.history
    evolver.run_generations(2)
    assert probe.snapshot(evolver) == result


def test_resume_matches_uninterrupted_including_long_archive(evolver, tmp_path):
    evolver.run_generations(67)
    assert len(evolver._archive) > 256
    saved = tmp_path / "gen_0067.json"
    evolver.run_generations(2)
    resumed = probe.FixtureEvolver(lambda: None, parallel=False, checkpoint_dir=tmp_path / "resumed", seed=99)
    resumed.load(saved)
    resumed.run_generations(2)
    assert probe.snapshot(resumed) == probe.snapshot(evolver)
    assert resumed.pop_size == 4 and resumed.elitism == 1 and resumed.seed == 17


def test_legacy_checkpoint_rejected_without_changing_state(evolver, tmp_path):
    before = probe.snapshot(evolver)
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"gen": 9, "seed": 0.123, "pop": []}))
    with pytest.raises(ValueError, match="Legacy checkpoint lacks RNG state"):
        evolver.load(legacy)
    assert probe.snapshot(evolver) == before


def test_evaluation_seed_is_stable_and_work_item_specific(evolver):
    seeds = evolver._evaluation_seeds()
    assert seeds == evolver._evaluation_seeds() and len(set(seeds)) == evolver.pop_size
    evolver.gen += 1
    assert seeds != evolver._evaluation_seeds()


@pytest.mark.parametrize("size", [1, 2])
def test_small_population_tournament(size, tmp_path):
    evolver = probe.FixtureEvolver(lambda: None, pop_size=size, elitism=0, parallel=False, checkpoint_dir=tmp_path)
    evolver.run_generations(1)
    assert len(evolver.population) == size


@pytest.mark.parametrize("size,elitism", [(0, 0), (2, -1), (2, 3)])
def test_invalid_population_rejected(size, elitism, tmp_path):
    with pytest.raises(ValueError, match="pop_size"):
        me.MetaEvolver(lambda: None, pop_size=size, elitism=elitism, parallel=False, checkpoint_dir=tmp_path)


def test_seed_signature_detection():
    assert me.MetaEvolver._accepts_seed(lambda seed=None: None)
    assert me.MetaEvolver._accepts_seed(lambda **kwargs: None)
    assert not me.MetaEvolver._accepts_seed(lambda: None)
    assert not me.MetaEvolver._accepts_seed(lambda seed, /: None)


@pytest.mark.parametrize(
    "damage", ["missing_arc", "bad_rng", "bad_hash", "bad_history", "bad_archive_dtype", "bad_archive_shape"]
)
def test_invalid_v2_checkpoint_does_not_partially_load(evolver, tmp_path, damage):
    evolver.run_generations(1)
    before = probe.snapshot(evolver)
    path = tmp_path / "gen_0001.json"
    data = json.loads(path.read_text())
    if damage == "missing_arc":
        del data["arc"]
    elif damage == "bad_rng":
        data["rng_state"] = [3, [1], None]
    elif damage == "bad_hash":
        data["sha"] = "incorrect"
    elif damage == "bad_archive_dtype":
        data["arc"][0]["dtype"] = "O"
    elif damage == "bad_archive_shape":
        data["arc"][0]["values"] = [[1, 2]]
    else:
        data["hist"] = [[99, 0.0]]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="checkpoint"):
        evolver.load(path)
    assert probe.snapshot(evolver) == before


def test_archive_dtype_and_exact_novelty_survive_checkpoint(evolver, tmp_path):
    evolver._archive = [np.array([0.1, 0.2, 0.3], dtype=np.float32)]
    descriptor = np.array([0.7, 0.4, 0.1], dtype=np.float32)
    before = float(np.mean([np.linalg.norm(descriptor - a) for a in evolver._archive]))
    evolver.save()
    restored = probe.FixtureEvolver(lambda: None, parallel=False, checkpoint_dir=tmp_path / "restored")
    restored.load(tmp_path / "gen_0000.json")
    assert restored._archive[0].dtype == np.dtype("float32")
    after = float(np.mean([np.linalg.norm(descriptor - a) for a in restored._archive]))
    assert after == before
