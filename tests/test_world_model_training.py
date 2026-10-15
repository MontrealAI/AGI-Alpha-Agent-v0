# SPDX-License-Identifier: Apache-2.0
"""Finite MiniWorld target oracles and optional real CPU gradient qualification."""
from __future__ import annotations

import importlib
import math

import numpy as np
import pytest

from alpha_factory_v1.demos.alpha_asi_world_model.training import MiniWorldTargets


def observation(size, cell):
    obs = np.zeros(size**2, dtype=np.float32)
    obs[cell[0] * size + cell[1]] = 1
    return obs


def test_exact_small_case_targets():
    oracle = MiniWorldTargets(2, [], (1, 1), discount=0.9)
    value, policy = oracle.targets((0, 0))
    assert value == pytest.approx(0.89)  # -0.01 + 0.9 * 1
    np.testing.assert_array_equal(policy, [0.5, 0.5, 0, 0])
    value, policy = oracle.targets((0, 1))
    assert value == 1
    np.testing.assert_array_equal(policy, [0, 1, 0, 0])
    assert oracle.targets((1, 1))[0] == 0
    assert oracle.targets((1, 1))[1].sum() == 0


def test_targets_match_independent_value_iteration():
    oracle = MiniWorldTargets(3, [(1, 0), (1, 1)], (2, 2), 0.9)
    cells = [(x, y) for x in range(3) for y in range(3) if (x, y) not in oracle.obstacles]
    values = dict.fromkeys(cells, 0.0)
    for _ in range(300):
        updated = {}
        for cell in cells:
            q = []
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nxt = (max(0, min(2, cell[0] + dx)), max(0, min(2, cell[1] + dy)))
                if nxt in oracle.obstacles:
                    nxt = cell
                q.append(1.0 if nxt == (2, 2) else -0.01 + 0.9 * values[nxt])
            updated[cell] = 0.0 if cell == (2, 2) else max(q)
        values = updated
    for cell in cells:
        assert oracle.value(cell) == pytest.approx(values[cell], abs=1e-10)
    unreachable = MiniWorldTargets(3, [(1, 0), (1, 1), (1, 2)], (2, 2), 0.9)
    assert unreachable.value((0, 0)) == pytest.approx(-0.1)
    np.testing.assert_array_equal(unreachable.targets((0, 0))[1], [0.25] * 4)


def test_replay_targets_validate_and_copy():
    oracle = MiniWorldTargets(2, [], (1, 1), 0.9)
    obs, nxt = observation(2, (0, 1)), observation(2, (1, 1))
    row = oracle.transition(obs, 1, 1.0, nxt, True)
    obs[:] = 0
    nxt[:] = 0
    assert row.obs.sum() == row.next_obs.sum() == 1
    assert row.next_value == 0 and row.next_policy.sum() == 0
    assert row.value == 1 and row.policy.sum() == 1
    for action, reward, done in [(4, 1, True), (True, 1, True), (1, math.nan, True), (1, 1, False)]:
        with pytest.raises(ValueError):
            oracle.transition(row.obs, action, reward, row.next_obs, done)
    with pytest.raises(ValueError, match="one-hot"):
        oracle.state(np.full(4, 0.25))
    with pytest.raises(ValueError, match="size"):
        oracle.state(np.zeros((1, 4)))
    with pytest.raises(ValueError, match="terminal"):
        oracle.transition(row.next_obs, 1, 1, row.next_obs, True)


@pytest.mark.parametrize("discount", [0, 1, -1, float("nan"), float("inf")])
def test_invalid_discount(discount):
    with pytest.raises(ValueError, match="discount"):
        MiniWorldTargets(2, [], (1, 1), discount)


@pytest.fixture
def runtime(monkeypatch):
    try:
        import torch
    except (ImportError, OSError):
        pytest.skip("Real CPU PyTorch required; oracle tests alone do not qualify training")
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("ALPHA_ASI_DISABLE_AGENT_THREADS", "1")
    module = importlib.import_module("alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo")
    torch.set_num_threads(1)
    torch.manual_seed(17)
    for key, value in {
        "device": "cpu",
        "hidden": 32,
        "train_batch": 12,
        "buffer_limit": 24,
        "lr": 0.02,
        "discount": 0.9,
    }.items():
        monkeypatch.setattr(module.CFG, key, value)
    return module


def fill_replay(module, learner):
    env = module.MiniWorld(2, [], (1, 1))
    for cell in [(0, 0), (0, 1), (1, 0)]:
        for action in range(4):
            env.agent = cell
            obs = env._obs()
            nxt, reward, done, _ = env.step(action)
            learner.remember(obs, action, reward, nxt, done)


def test_every_head_updates_and_finite_losses(runtime):
    module = runtime
    learner = module.Learner(module.MiniWorld(2, [], (1, 1)))
    assert learner.train_once() == 0 and learner.step_count == 0
    fill_replay(module, learner)
    before = {name: value.detach().clone() for name, value in learner.net.named_parameters()}
    total = learner.train_once()
    assert math.isfinite(total) and total > 0
    assert learner.step_count == 1
    assert set(learner.last_losses) == {"value", "policy", "reward", "next_value", "next_policy", "consistency"}
    assert total == pytest.approx(sum(learner.last_losses.values()))
    for name, parameter in learner.net.named_parameters():
        assert parameter.grad is not None and module.torch.isfinite(parameter.grad).all(), name
        assert not module.torch.equal(before[name], parameter), name
    module.CFG.train_batch = 1
    assert math.isfinite(learner.train_once())  # no scalar broadcasting at batch size one
    module.CFG.buffer_limit = 12
    fill_replay(module, learner)
    assert len(learner.buffer) == 12


def test_finite_cpu_fit_and_search_small_oracle(runtime):
    module = runtime
    learner = module.Learner(module.MiniWorld(2, [], (1, 1)))
    fill_replay(module, learner)
    first = learner.train_once()
    for _ in range(399):
        final = learner.train_once()
    assert final < first * 0.25
    assert learner.last_losses["reward"] < 0.02
    assert learner.last_losses["value"] < 0.02
    assert learner.last_losses["next_value"] < 0.02
    assert learner.last_losses["consistency"] < 0.05
    # Cross-entropy cannot reach zero for tied optimal actions. Check excess
    # above each replay target's entropy, i.e. mean target-to-prediction KL.
    for field, loss_name in [("policy", "policy"), ("next_policy", "next_policy")]:
        entropies = []
        for row in learner.buffer:
            probabilities = getattr(row, field)
            positive = probabilities[probabilities > 0]
            entropies.append(float(-(positive * np.log(positive)).sum()))
        excess = learner.last_losses[loss_name] - float(np.mean(entropies))
        assert -1e-6 <= excess < 0.05, (loss_name, excess)
    # Unique optimal actions on adjacent-to-goal states; no random act() exploration.
    assert module.mcts_policy(learner.net, observation(2, (0, 1)), 8) == 1
    assert module.mcts_policy(learner.net, observation(2, (1, 0)), 8) == 0


def test_search_uses_discount_and_never_picks_unvisited_zero(runtime):
    module = runtime

    class OracleNet:
        def initial(self, _obs):
            return module.torch.zeros(1), module.torch.zeros(1), module.torch.log(module.torch.full((4,), 0.25))

        def recurrent(self, h, action):
            assert not module.torch.is_grad_enabled()
            a = int(action.argmax())
            return (
                h,
                module.torch.tensor([-1.0 if a == 0 else -2.0]),
                module.torch.tensor([1.05 if a == 1 else 0.0]),
                action,
            )

    assert module.mcts_policy(OracleNet(), observation(2, (0, 0)), 1) == 0
    assert module.mcts_policy(OracleNet(), observation(2, (0, 0)), 8) == 0
    with pytest.raises(ValueError, match="positive"):
        module.mcts_policy(OracleNet(), observation(2, (0, 0)), 0)


def test_nonfinite_loss_aborts_before_optimizer(runtime, monkeypatch):
    module = runtime
    learner = module.Learner(module.MiniWorld(2, [], (1, 1)))
    fill_replay(module, learner)
    with module.torch.no_grad():
        learner.net.pred.v.weight.fill_(float("nan"))
    monkeypatch.setattr(learner.opt, "step", lambda: pytest.fail("Optimizer must not run after non-finite loss"))
    with pytest.raises(FloatingPointError, match="Non-finite"):
        learner.train_once()
    assert learner.step_count == 0 and learner.last_losses == {}


def test_nonfinite_gradient_aborts_before_optimizer(runtime, monkeypatch):
    module = runtime
    learner = module.Learner(module.MiniWorld(2, [], (1, 1)))
    fill_replay(module, learner)
    handle = learner.net.pred.v.weight.register_hook(lambda gradient: module.torch.full_like(gradient, float("nan")))
    monkeypatch.setattr(learner.opt, "step", lambda: pytest.fail("Optimizer must not run after non-finite gradient"))
    try:
        with pytest.raises(RuntimeError, match="non-finite"):
            learner.train_once()
    finally:
        handle.remove()
    assert learner.step_count == 0 and learner.last_losses == {}


def test_gradient_clipping_bounds_update(runtime, monkeypatch):
    module = runtime
    learner = module.Learner(module.MiniWorld(2, [], (1, 1)))
    fill_replay(module, learner)
    handles = [parameter.register_hook(lambda gradient: gradient * 10000) for parameter in learner.net.parameters()]
    clip = module.torch.nn.utils.clip_grad_norm_
    checked = []

    def inspect_clip(parameters, max_norm, *, error_if_nonfinite):
        parameters = list(parameters)
        assert max_norm == 10.0 and error_if_nonfinite is True
        before = clip(parameters, max_norm, error_if_nonfinite=error_if_nonfinite)
        after = module.torch.sqrt(sum(parameter.grad.square().sum() for parameter in parameters))
        assert before > max_norm
        assert float(after) <= max_norm + 1e-5
        checked.append(True)
        return before

    monkeypatch.setattr(module.torch.nn.utils, "clip_grad_norm_", inspect_clip)
    try:
        assert math.isfinite(learner.train_once())
    finally:
        for handle in handles:
            handle.remove()
    assert checked == [True] and learner.step_count == 1
