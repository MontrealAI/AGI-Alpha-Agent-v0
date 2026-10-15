# SPDX-License-Identifier: Apache-2.0
"""Real CPU neuroevolution/plasticity qualification, never stub-based training."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import partial
import math
import os
import random

import numpy as np
import pytest

from tests.test_aiga_reproducibility import probe, run_probe


@pytest.fixture
def runtime(monkeypatch):
    try:
        import torch
        from alpha_factory_v1.demos.aiga_meta_evolution import curriculum_env as ce
    except (ImportError, OSError) as exc:
        if os.getenv("AIGA_REQUIRE_CPU_TRAINING") == "1":
            pytest.fail(f"CPU qualification requires real torch and gymnasium: {exc}")
        pytest.skip("Real CPU Torch/Gymnasium unavailable; this does not qualify training")
    from alpha_factory_v1.demos.aiga_meta_evolution import meta_evolver as me

    assert me._TORCH, "The lightweight stub cannot qualify training"
    monkeypatch.setattr(me, "_A2A", None)
    monkeypatch.setattr(me, "_HAS_RAY", False)
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    yield me, ce, torch
    torch.set_num_threads(previous_threads)


def factory(ce):
    return partial(ce.CurriculumEnv, genome=ce.EnvGenome(max_steps=6), size=6)


def engine(runtime, path, seed=17, env_cls=None):
    me, ce, _ = runtime
    return me.MetaEvolver(
        env_cls or factory(ce), pop_size=4, elitism=1, parallel=False, checkpoint_dir=path, seed=seed, device="cpu"
    )


def test_owned_torch_initialization_preserves_global_state(runtime):
    me, _, torch = runtime
    before = torch.random.get_rng_state().clone()

    def weights(seed):
        net = me.EvoNet(9, 4, me.Genome(layers=(4, 6)), seed=seed)
        return torch.cat([value.detach().flatten() for value in net.parameters()])

    with ThreadPoolExecutor(max_workers=4) as pool:
        a, b, c, d = list(pool.map(weights, [17, 18, 17, 18]))
    assert torch.equal(a, c) and torch.equal(b, d) and not torch.equal(a, b)
    me.EvoNet(9, 4, me.Genome())  # Unseeded standalone construction also owns its RNG.
    assert torch.equal(torch.random.get_rng_state(), before)


def test_hebbian_plasticity_performs_real_finite_weight_updates(runtime):
    me, _, torch = runtime
    net = me.EvoNet(9, 4, me.Genome(layers=(4,), activation="sigmoid", hebbian=True), seed=17)
    before = net.model[0].weight.detach().clone()
    with torch.no_grad():
        output = net(torch.ones(9))
    assert torch.isfinite(output).all() and torch.isfinite(net.fast_0).all()
    assert not torch.equal(before, net.model[0].weight)
    assert torch.count_nonzero(net.fast_0) > 0 and float(net.fast_0.abs().max()) <= 0.020001


def test_rollout_matches_independent_environment_replay(runtime, tmp_path):
    me, ce, _ = runtime
    actions, constructor_seeds = [], []

    class RecordingEnv(ce.CurriculumEnv):
        def __init__(self, seed=None):
            constructor_seeds.append(seed)
            super().__init__(genome=ce.EnvGenome(max_steps=6), size=6, seed=seed)

        def step(self, action):
            actions.append(action)
            return super().step(action)

    ev = engine(runtime, tmp_path, env_cls=RecordingEnv)
    genome = me.Genome(layers=(4,), activation="tanh", novelty_weight=0.25)
    ev._archive = [np.zeros(9)]
    score, behavior = ev._simulate(genome, seed=42)
    assert constructor_seeds == [42] and 1 <= len(actions) <= 6
    env = factory(ce)(seed=42)
    env.reset(seed=42)
    observations, total = [], 0.0
    for action in actions:
        obs, reward, done, truncated, _ = env.step(action)
        observations.append(obs)
        total += reward
    expected = np.mean(observations, axis=0)
    np.testing.assert_array_equal(behavior, expected)
    assert score == pytest.approx(total + 0.25 * np.linalg.norm(expected))
    assert done or truncated


def test_real_generations_select_elite_and_preserve_global_rng(runtime, tmp_path):
    _, _, torch = runtime
    ev = engine(runtime, tmp_path)
    population = list(ev.population)
    py_before, np_before, torch_before = random.getstate(), np.random.get_state(), torch.random.get_rng_state().clone()
    ev.run_generations(1)
    best_idx = int(np.argmax(ev._last_scores))
    assert ev.population[0].to_json() == population[best_idx].to_json()
    assert ev.best_genome.to_json() == population[best_idx].to_json()
    ev.run_generations(1)
    assert ev.gen == 2 and len(ev.history) == 2 and len(ev._archive) == 8
    assert len(ev.population) == 4 and all(math.isfinite(score) for score in ev._last_scores)
    assert ev.best_genome is not None and math.isfinite(ev.best_fitness)
    assert ev.history[-1][1] == pytest.approx(np.mean(ev._last_scores))
    assert random.getstate() == py_before
    after = np.random.get_state()
    assert np_before[0] == after[0] and np_before[2:] == after[2:]
    np.testing.assert_array_equal(np_before[1], after[1])
    assert torch.equal(torch.random.get_rng_state(), torch_before)


def test_no_argument_factory_is_seeded_through_reset(runtime, tmp_path):
    _, ce, _ = runtime
    seeded = engine(runtime, tmp_path / "seeded")
    legacy = engine(runtime, tmp_path / "legacy", env_cls=lambda: factory(ce)())
    assert seeded._thread_eval() == legacy._thread_eval()
    np.testing.assert_array_equal(seeded._archive, legacy._archive)


def test_process_and_thread_evaluation_match(runtime, tmp_path):
    threaded = engine(runtime, tmp_path / "thread")
    process = engine(runtime, tmp_path / "process")
    assert threaded._thread_eval() == process._mp_eval()
    np.testing.assert_array_equal(threaded._archive, process._archive)


def test_real_training_repeats_in_fresh_processes(runtime, tmp_path):
    first = run_probe(tmp_path / "first", 1, training=True)
    assert first == run_probe(tmp_path / "second", 839, training=True)
    assert first != run_probe(tmp_path / "different", 1, seed=18, training=True)


def test_real_checkpoint_resume_matches_uninterrupted(runtime, tmp_path):
    ev = engine(runtime, tmp_path / "uninterrupted")
    for genome in ev.population:
        genome.novelty_weight = 0.5
    ev._archive = [np.linspace(0.1, 0.9, 9, dtype=np.float32)]
    ev.run_generations(1)
    saved = ev.ckpt_dir / "gen_0001.json"
    ev.run_generations(2)
    resumed = engine(runtime, tmp_path / "resumed", seed=99)
    resumed.load(saved)
    resumed.run_generations(2)
    assert probe.snapshot(ev) == probe.snapshot(resumed)


def test_curriculum_reset_rewinds_layout_and_action_space(runtime):
    _, ce, _ = runtime
    env = factory(ce)(seed=17)
    obs, info = env.reset(seed=42)
    grid, actions = env.grid.copy(), [env.action_space.sample() for _ in range(10)]
    env.reset()
    replay, replay_info = env.reset(seed=42)
    np.testing.assert_array_equal(obs, replay)
    np.testing.assert_array_equal(grid, env.grid)
    assert actions == [env.action_space.sample() for _ in range(10)]
    assert info == replay_info and "genome_id" in info and math.isfinite(info["difficulty"])
