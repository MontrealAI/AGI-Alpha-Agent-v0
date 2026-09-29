# SPDX-License-Identifier: Apache-2.0
"""Behavioral regressions for the real learned-model planning path."""
from __future__ import annotations

import json
import math
from pathlib import Path
import random

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("gymnasium")
from alpha_factory_v1.demos.muzero_planning.minimuzero import MiniMu, Node, _select_child, search
from alpha_factory_v1.demos.muzero_planning.training import (
    Config,
    MiniChoice,
    Trajectory,
    checkpoint,
    experiment,
    load_checkpoint,
    update,
    value_targets,
)
from collections import deque


@pytest.fixture(autouse=True)
def one_cpu_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def test_selection_includes_immediate_reward_and_discount():
    root = Node(
        1.0,
        visit_count=10,
        children={
            0: Node(0.5, reward=2, visit_count=2, value_sum=0),
            1: Node(0.5, reward=0, visit_count=2, value_sum=6),
        },
    )
    assert _select_child(root, discount=0.1)[0] == 0
    assert _select_child(root, discount=1.0)[0] == 1
    with pytest.raises(ValueError, match="unexpanded"):
        _select_child(Node(1))


class KnownModel:
    action_dim = 2

    def initial(self, obs):
        return torch.tensor([0.0]), torch.tensor(0.0), torch.zeros(2)

    def recurrent(self, state, action):
        # Only the first transition pays; later predictions are an absorbing state.
        reward = float(action == 1) if float(state[0]) == 0 else 0.0
        return torch.tensor([1.0]), torch.tensor(reward), torch.tensor(0.0), torch.zeros(2)


def test_search_visits_rewarding_branch_and_accounts_for_every_simulation():
    root = search(KnownModel(), [0], 64, max_depth=4)
    assert root.visit_count == sum(c.visit_count for c in root.children.values()) == 64
    assert root.children[1].visit_count > root.children[0].visit_count
    assert math.isfinite(root.value())


@pytest.mark.parametrize("budget", [0, -1, True, 1.5, 513])
def test_search_rejects_invalid_budget(budget):
    with pytest.raises(ValueError):
        search(KnownModel(), [0], budget)


def test_nonfinite_model_predictions_rejected():
    class Invalid(KnownModel):
        def initial(self, obs):
            return torch.ones(1), torch.tensor(float("nan")), torch.zeros(2)

    with pytest.raises(ValueError, match="non-finite"):
        search(Invalid(), [0])


def test_depth_cap_prevents_unbounded_expansion():
    class Counting(KnownModel):
        calls = 0

        def recurrent(self, state, action):
            self.calls += 1
            return super().recurrent(state, action)

    net = Counting()
    search(net, [0], 128, max_depth=1)
    assert net.calls == 2


def test_bootstrap_distinguishes_termination_from_time_limit():
    assert value_targets([1, 2], 0, 0.5) == [2, 2, 0]
    assert value_targets([1, 2], 4, 0.5) == [3, 4, 4]


def test_training_changes_representation_dynamics_and_prediction_heads():
    agent = MiniMu("MiniChoice-v0", render_mode=None)
    before = {k: v.clone() for k, v in agent.net.state_dict().items()}
    trajectory = Trajectory(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        [1, 1],
        [0.0, 1.0],
        [[0.0, 1.0], [0.0, 1.0], [0.5, 0.5]],
        [0.997, 1.0, 0.0],
        True,
    )
    optimizer = torch.optim.Adam(agent.net.parameters(), lr=0.003)
    losses = [update(agent, deque([trajectory]), optimizer, random.Random(1)) for _ in range(50)]
    assert sum(losses[-1].values()) < sum(losses[0].values())
    for name in ("repr.0.weight", "dyn.weight", "policy_head.weight", "value_head.weight"):
        assert not torch.equal(before[name], agent.net.state_dict()[name]), name
    agent.env.close()


def test_seed_does_not_mutate_global_torch_rng():
    before = torch.random.get_rng_state().clone()
    agent = MiniMu("MiniChoice-v0", seed=7, render_mode=None)
    assert torch.equal(before, torch.random.get_rng_state())
    agent.env.close()


def test_portable_checkpoint_roundtrip_and_atomic_rejection(tmp_path):
    agent = MiniMu("MiniChoice-v0", render_mode=None)
    other = MiniMu("MiniChoice-v0", seed=8, render_mode=None)
    path = tmp_path / "weights.json"
    data = checkpoint(agent)
    path.write_text(json.dumps(data))
    load_checkpoint(other, path)
    assert checkpoint(other) == data
    data["weights"]["value_head.bias"] = [float("inf")]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_checkpoint(other, path)
    assert checkpoint(other) == checkpoint(agent)
    path.write_text('{"schema":1,"schema":2}')
    with pytest.raises(ValueError, match="Duplicate"):
        load_checkpoint(other, path)
    agent.env.close()
    other.env.close()


def test_minichoice_rewards_and_terminal_boundary():
    env = MiniChoice()
    env.reset(seed=1)
    assert env.step(0)[1:3] == (0.3, True)
    with pytest.raises(RuntimeError):
        env.step(1)
    env.reset()
    assert env.step(1)[1:3] == (0.0, False)
    assert env.step(1)[1:3] == (1.0, True)


@pytest.mark.parametrize(
    "values",
    [
        {"episodes": -1},
        {"seed": True},
        {"env_id": "Pendulum-v1"},
        {"episodes": 100, "simulations": 128, "max_steps": 500},
    ],
)
def test_invalid_experiments_are_rejected_before_work(values):
    with pytest.raises(ValueError):
        Config(**values)


def test_real_learning_experiment_records_measured_returns_and_losses():
    report = list(experiment(Config(episodes=32, simulations=32, max_steps=8)))[-1]
    assert report["status"] == "complete"
    assert report["evaluation"]["trained_search"] == [1.0] * 5
    assert len(report["history"]) == 32
    assert all(row["reward"] in [-0.2, 0.3, 1.0] for row in report["history"])
    assert all(math.isfinite(row["loss_reward"]) for row in report["history"])


def test_original_research_and_diagram_preserved():
    root = Path(__file__).resolve().parents[1]
    demo = root / "alpha_factory_v1/demos/muzero_planning"
    original = (demo / "archive/README.original.md").read_text()
    diagram = original.split("```text\n", 1)[1].split("```", 1)[0]
    assert diagram in (demo / "README.md").read_text()


def test_cancelled_training_closes_environment_and_restores_threads(monkeypatch):
    from alpha_factory_v1.demos.muzero_planning import training

    instances = []
    original = training.MiniMu

    def tracked(*args, **kwargs):
        agent = original(*args, **kwargs)
        agent.env.closed = False
        agent.env.close = lambda: setattr(agent.env, "closed", True)
        instances.append(agent)
        return agent

    monkeypatch.setattr(training, "MiniMu", tracked)
    threads = torch.get_num_threads()
    run = training.experiment(Config(episodes=2, max_steps=8))
    next(run)
    run.close()
    assert instances[0].env.closed
    assert torch.get_num_threads() == threads


def test_archive_matches_preserved_manifest():
    import hashlib

    archive = Path(__file__).resolve().parents[1] / "alpha_factory_v1/demos/muzero_planning/archive"
    manifest = json.loads((archive / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((archive / name).read_bytes()).hexdigest() == digest


def test_real_cartpole_preview_is_bounded():
    from alpha_factory_v1.demos.muzero_planning.training import preview_episode

    pytest.importorskip("pygame")
    report = list(experiment(Config(env_id="CartPole-v1", episodes=0, max_steps=8, evaluation_episodes=1)))[-1]
    frames = preview_episode(report)
    assert 2 <= len(frames) <= 12
    assert all(image.ndim == 3 and image.shape[-1] == 3 for image, _ in frames)
    assert frames[0][1] == "Start · reward 0"


def test_cli_checkpoint_digest_binds_exported_bytes(tmp_path):
    import hashlib
    from alpha_factory_v1.demos.muzero_planning.__main__ import main

    report_path, weights_path = tmp_path / "report.json", tmp_path / "weights.json"
    main(
        [
            "--headless",
            "--episodes",
            "0",
            "--max-steps",
            "8",
            "--output",
            str(report_path),
            "--checkpoint",
            str(weights_path),
        ]
    )
    report = json.loads(report_path.read_text())
    assert report["checkpoint_sha256"] == hashlib.sha256(weights_path.read_bytes()).hexdigest()
    assert json.loads(weights_path.read_bytes()) == report["checkpoint"]
    with pytest.raises(SystemExit) as error:
        main(["--headless", "--output", str(report_path)])
    assert error.value.code == 2
