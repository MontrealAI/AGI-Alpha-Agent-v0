# SPDX-License-Identifier: Apache-2.0
"""Small replay learner with recurrent reward, value and search-policy targets."""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any, Iterator

import gymnasium as gym
import numpy as np
import torch
import torch.nn.functional as F

from .minimuzero import MiniMu, bounded_int, require_dependencies, search

ENVIRONMENTS = ("MiniChoice-v0", "CartPole-v1", "MountainCar-v0", "Acrobot-v1")
DISCOUNT = 0.997


class MiniChoice(gym.Env):  # type: ignore[misc]
    """Two-step delayed-reward task; transition rules stay outside the search model."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 4}

    def __init__(self, render_mode: str | None = None) -> None:
        self.observation_space = gym.spaces.Box(0, 1, (3,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(2)
        self.render_mode = render_mode
        self.position = 0

    def _obs(self) -> Any:
        return np.eye(3, dtype=np.float32)[self.position]

    def reset(self, *, seed: int | None = None, options: Any = None) -> tuple[Any, dict[str, Any]]:
        super().reset(seed=seed)
        self.position = 0
        return self._obs(), {}

    def step(self, action: int) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        if self.position == 2:
            raise RuntimeError("Reset after termination")
        if not self.action_space.contains(action):
            raise ValueError("Action must be 0 or 1")
        if self.position == 0 and action == 1:
            self.position, reward = 1, 0.0
        else:
            reward = 0.3 if self.position == 0 else (1.0 if action == 1 else -0.2)
            self.position = 2
        return self._obs(), reward, self.position == 2, False, {}

    def render(self) -> Any:
        canvas: Any = np.full((120, 360, 3), (17, 28, 46), dtype=np.uint8)
        for index in range(3):
            left, right = 20 + index * 120, 100 + index * 120
            canvas[40:80, left:right] = (72, 211, 183) if index == self.position else (59, 74, 100)
        return canvas


@dataclass(frozen=True)
class Config:
    env_id: str = "MiniChoice-v0"
    seed: int = 42
    episodes: int = 32
    simulations: int = 32
    max_steps: int = 200
    updates_per_episode: int = 16
    evaluation_episodes: int = 5

    def __post_init__(self) -> None:
        if self.env_id not in ENVIRONMENTS:
            raise ValueError(f"env_id must be one of {ENVIRONMENTS}")
        for name, low, high in (
            ("seed", 0, 2**31 - 1000),
            ("episodes", 0, 100),
            ("simulations", 2, 128),
            ("max_steps", 2, 500),
            ("updates_per_episode", 1, 32),
            ("evaluation_episodes", 1, 20),
        ):
            bounded_int(name, getattr(self, name), low, high)
        if self.episodes * self.max_steps * self.simulations > 1_000_000:
            raise ValueError("Training budget exceeds 1,000,000 simulations; reduce episodes, steps or simulations")


@dataclass
class Trajectory:
    observations: list[Any]
    actions: list[int]
    rewards: list[float]
    policies: list[list[float]]
    values: list[float]
    terminated: bool


def value_targets(rewards: list[float], bootstrap: float, discount: float = DISCOUNT) -> list[float]:
    """Termination uses zero; an external time limit bootstraps the final state."""
    values = [bootstrap]
    for reward in reversed(rewards):
        values.append(reward + discount * values[-1])
    return list(reversed(values))


def collect(agent: MiniMu, config: Config, episode: int) -> Trajectory:
    obs = agent.reset(seed=config.seed + episode)
    observations, actions, rewards, policies = [np.asarray(obs).reshape(-1).tolist()], [], [], []
    terminated = False
    for _ in range(config.max_steps):
        root = search(agent.net, np.asarray(obs).reshape(-1), config.simulations, exploration_rng=agent.rng)
        policy = [child.visit_count / config.simulations for child in root.children.values()]
        # Warm-up random behavior plus root Dirichlet noise ensures the replay sees alternatives.
        action = (
            agent.rng.randrange(agent.action_dim)
            if agent.rng.random() < (1.0 if episode < 8 else 0.5)
            else agent.rng.choices(range(agent.action_dim), weights=policy, k=1)[0]
        )
        obs, reward, terminated, truncated, _ = agent.env.step(action)
        actions.append(action)
        rewards.append(float(reward))
        policies.append(policy)
        observations.append(np.asarray(obs).reshape(-1).tolist())
        if terminated or truncated:
            break
    with torch.no_grad():
        bootstrap = 0.0 if terminated else float(agent.net.initial(observations[-1])[1])
    policies.append([1 / agent.action_dim] * agent.action_dim)
    return Trajectory(observations, actions, rewards, policies, value_targets(rewards, bootstrap), terminated)


def update(agent: MiniMu, replay: deque[Trajectory], optimizer: Any, rng: random.Random) -> dict[str, float]:
    """Three-step recurrent unroll; learn an absorbing state only for true termination."""
    samples = [(rng.choice(replay), 0) for _ in range(16)]
    samples = [(episode, rng.randrange(len(episode.actions) + int(episode.terminated))) for episode, _ in samples]
    states, values, logits = agent.net.initial([e.observations[t] for e, t in samples])
    losses: dict[str, Any] = {"reward": torch.tensor(0.0), "value": torch.tensor(0.0), "policy": torch.tensor(0.0)}
    count = 0
    for step in range(4):
        indices = [min(t + step, len(e.actions)) for e, t in samples]
        mask = torch.tensor([float(t + step <= len(e.actions) or e.terminated) for e, t in samples])
        policy_mask = torch.tensor([float(t + step < len(e.actions)) for e, t in samples])
        targets = torch.tensor(
            [e.values[i] if t + step <= len(e.actions) else 0.0 for (e, t), i in zip(samples, indices)]
        )
        probabilities = torch.tensor([e.policies[i] for (e, _), i in zip(samples, indices)])
        losses["value"] += ((values.squeeze(-1) - targets).square() * mask).mean()
        losses["policy"] += (-(probabilities * F.log_softmax(logits, dim=-1)).sum(-1) * policy_mask).mean()
        count += 1
        if step < 3:
            action = torch.tensor(
                [
                    e.actions[i] if i < len(e.actions) else rng.randrange(agent.action_dim)
                    for (e, _), i in zip(samples, indices)
                ]
            )
            states, reward, values, logits = agent.net.recurrent(states, action)
            reward_target = torch.tensor(
                [e.rewards[i] if i < len(e.actions) else 0.0 for (e, _), i in zip(samples, indices)]
            )
            reward_mask = torch.tensor([float(t + step < len(e.actions) or e.terminated) for e, t in samples])
            losses["reward"] += ((reward.squeeze(-1) - reward_target).square() * reward_mask).mean()
    loss = sum(losses.values()) / count
    if not torch.isfinite(loss):
        raise RuntimeError("Training diverged; no checkpoint was produced")
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(agent.net.parameters(), 5.0, error_if_nonfinite=True)
    optimizer.step()
    return {name: float(value.detach()) / count for name, value in losses.items()}


def evaluate(agent: MiniMu, config: Config, mode: str = "search") -> list[float]:
    """Evaluate without updates on the same held-out reset seeds for every policy."""
    totals: list[float] = []
    rng = random.Random(config.seed + 10000)
    for episode in range(config.evaluation_episodes):
        obs = agent.reset(seed=config.seed + 10000 + episode)
        total = 0.0
        for _ in range(config.max_steps):
            if mode == "random":
                action = rng.randrange(agent.action_dim)
            elif mode == "policy":
                with torch.no_grad():
                    action = int(agent.net.initial(np.asarray(obs).reshape(-1))[2].argmax())
            else:
                action = int(agent.policy(obs).argmax())
            obs, reward, terminated, truncated, _ = agent.env.step(action)
            total += float(reward)
            if terminated or truncated:
                break
        totals.append(total)
    return totals


def inspect_search(agent: MiniMu) -> list[dict[str, Any]]:
    root = search(agent.net, np.asarray(agent.reset()).reshape(-1), agent.simulations)
    return [
        {
            "action": a,
            "prior": round(c.prior, 6),
            "visits": c.visit_count,
            "predicted_reward": round(c.reward, 6),
            "value": round(c.value(), 6),
            "q": round(c.reward + DISCOUNT * c.value(), 6),
        }
        for a, c in root.children.items()
    ]


def checkpoint(agent: MiniMu) -> dict[str, Any]:
    """Portable JSON weights: never unpickle uploaded model files."""
    return {
        "schema": "minimu-weights-v1",
        "env_id": agent.env_id,
        "weights": {key: value.detach().cpu().tolist() for key, value in agent.net.state_dict().items()},
    }


def checkpoint_bytes(data: dict[str, Any]) -> bytes:
    """Canonical exported weights: sorted compact JSON followed by one LF."""
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def load_checkpoint(agent: MiniMu, path: Path) -> None:
    """Bound input bytes, keys, shapes and finite values before replacing any weights."""
    with path.open("rb") as source:
        raw = source.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Checkpoint exceeds 2 MB")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate checkpoint key")
            result[key] = value
        return result

    try:
        data = json.loads(raw, object_pairs_hook=unique)
        if set(data) != {"schema", "env_id", "weights"} or data["schema"] != "minimu-weights-v1":
            raise ValueError("Unsupported checkpoint schema")
        if data["env_id"] != agent.env_id or set(data["weights"]) != set(agent.net.state_dict()):
            raise ValueError("Checkpoint environment or weight names do not match")
        converted = {}
        for name, expected in agent.net.state_dict().items():
            tensor = torch.tensor(data["weights"][name], dtype=torch.float32)
            if tensor.shape != expected.shape or not torch.isfinite(tensor).all():
                raise ValueError("Invalid checkpoint weight shape or value")
            converted[name] = tensor
        agent.net.load_state_dict(converted, strict=True)
    except (TypeError, KeyError, RuntimeError, RecursionError, OverflowError) as exc:
        raise ValueError("Invalid checkpoint") from exc


def experiment(config: Config) -> Iterator[dict[str, Any]]:
    """Yield bounded progress, then measured baselines, training losses and JSON weights."""
    require_dependencies()
    agent = MiniMu(config.env_id, seed=config.seed, simulations=config.simulations, render_mode=None)
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        before = inspect_search(agent)
        baselines = {"random": evaluate(agent, config, "random"), "untrained_search": evaluate(agent, config)}
        optimizer = torch.optim.Adam(agent.net.parameters(), lr=0.003, weight_decay=0.0001)
        replay: deque[Trajectory] = deque(maxlen=64)
        rng = random.Random(config.seed)
        history = []
        for episode in range(config.episodes):
            trajectory = collect(agent, config, episode)
            replay.append(trajectory)
            losses = {}
            for _ in range(config.updates_per_episode):
                losses = update(agent, replay, optimizer, rng)
            history.append(
                {
                    "episode": episode + 1,
                    "reward": sum(trajectory.rewards),
                    **{f"loss_{k}": v for k, v in losses.items()},
                }
            )
            yield {"status": "training", "completed": episode + 1, "total": config.episodes, "history": list(history)}
        agent.net.eval()
        baselines["trained_policy"] = evaluate(agent, config, "policy")
        baselines["trained_search"] = evaluate(agent, config)
        weights = checkpoint(agent)
        digest = hashlib.sha256(checkpoint_bytes(weights)).hexdigest()
        yield {
            "schema": "minimu-experiment-v1",
            "status": "complete",
            "config": asdict(config),
            "versions": {"torch": torch.__version__, "gymnasium": gym.__version__, "numpy": np.__version__},
            "history": history,
            "evaluation": baselines,
            "search_before": before,
            "search_after": inspect_search(agent),
            "checkpoint": weights,
            "checkpoint_sha256": digest,
            "scope": "CPU educational MuZero-style model; no CartPole-solving or AGI guarantee.",
        }
    finally:
        agent.env.close()
        torch.set_num_threads(previous_threads)


def preview_episode(report: dict[str, Any]) -> list[tuple[Any, str]]:
    """Render at most 12 snapshots of a bounded, trained-policy evaluation episode."""
    config = Config(**report["config"])
    agent = MiniMu(config.env_id, seed=config.seed, simulations=config.simulations)
    try:
        agent.net.load_state_dict(
            {name: torch.tensor(value) for name, value in report["checkpoint"]["weights"].items()}
        )
        obs = agent.reset(seed=config.seed + 10000)
        frames: list[tuple[Any, str]] = []
        total = 0.0
        limit = min(config.max_steps, 60)
        stride = max(1, math.ceil(limit / 10))
        frames.append((agent.env.render(), "Start · reward 0"))
        for step in range(limit):
            action = int(agent.policy(obs).argmax())
            obs, reward, terminated, truncated, _ = agent.env.step(action)
            total += float(reward)
            if (step + 1) % stride == 0 or terminated or truncated or step + 1 == limit:
                frames.append((agent.env.render(), f"Step {step + 1} · action {action} · reward {total:.2f}"))
            if terminated or truncated:
                break
        return frames
    finally:
        agent.env.close()
