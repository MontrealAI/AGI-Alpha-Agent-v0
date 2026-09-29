# SPDX-License-Identifier: Apache-2.0
"""Minimal MuZero utilities used by the planning demo."""

from __future__ import annotations

import math
import random

try:
    import numpy as np  # for policy arrays when torch absent
except (ModuleNotFoundError, OSError):  # pragma: no cover - optional dependency
    np = None
try:
    import gymnasium as gym
except ModuleNotFoundError:  # pragma: no cover - lightweight stub

    class _StubEnv:
        observation_space = type("obs", (), {"shape": (4,)})
        action_space = type("act", (), {"n": 2})

        def reset(self, *, seed=None):
            return [0.0] * 4, {}

        def step(self, action):
            return [0.0] * 4, 0.0, True, False, {}

        def render(self):
            return []

        def close(self):
            pass

    def make(env_id, render_mode=None):
        return _StubEnv()

    gym = type("gym", (), {"make": make, "Env": _StubEnv})

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    _TORCH = True
except (ModuleNotFoundError, OSError):  # pragma: no cover - optional dependency
    _TORCH = False
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


if _TORCH:

    class MiniMuNet(nn.Module):
        """Lightweight world model with representation, dynamics and prediction."""

        def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 32) -> None:
            super().__init__()
            self.action_dim = action_dim
            self.repr = nn.Sequential(nn.Linear(obs_dim, hidden_dim), nn.Tanh())
            self.dyn = nn.Linear(hidden_dim + action_dim, hidden_dim + 1)
            self.policy_head = nn.Linear(hidden_dim, action_dim)
            self.value_head = nn.Linear(hidden_dim, 1)

        def initial(self, obs) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            with torch.no_grad():
                x = torch.as_tensor(obs, dtype=torch.float32)
                state = self.repr(x)
                policy = self.policy_head(state)
                value = self.value_head(state)
            return state, value, policy

        def recurrent(
            self, state: torch.Tensor, action: int
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
            with torch.no_grad():
                a = F.one_hot(torch.tensor(action), num_classes=self.action_dim).float()
                x = torch.cat([state, a], dim=-1)
                out = self.dyn(x)
                reward = out[..., :1]
                next_state = torch.tanh(out[..., 1:])
                policy = self.policy_head(next_state)
                value = self.value_head(next_state)
            return next_state.detach(), reward, value, policy

else:  # pragma: no cover - torch missing

    class MiniMuNet:  # type: ignore[misc]
        def __init__(self, *a, **kw) -> None:
            self.action_dim = kw.get("action_dim", 2)

        def initial(self, obs):
            return None, 0.0, None

        def recurrent(self, state, action):
            return None, 0.0, 0.0, None


@dataclass
class Node:
    prior: float
    state: torch.Tensor | None = None
    reward: float = 0.0
    visit_count: int = 0
    value_sum: float = 0.0
    children: Dict[int, "Node"] | None = None

    def expanded(self) -> bool:
        return self.children is not None

    def value(self) -> float:
        return self.value_sum / self.visit_count if self.visit_count else 0.0


def _select_child(node: Node) -> Tuple[int, Node]:
    """Pick child with highest UCB score."""
    best_score = -float("inf")
    best_action = 0
    best_child = None
    for action, child in node.children.items():
        ucb = child.value() + 1.5 * child.prior * math.sqrt(node.visit_count + 1) / (1 + child.visit_count)
        if ucb > best_score:
            best_score = ucb
            best_action = action
            best_child = child
    return best_action, best_child


def mcts_policy(net: MiniMuNet, env: gym.Env, obs, num_simulations: int = 64):
    """Return policy via MuZero-style MCTS (random if torch unavailable)."""
    if not _TORCH:
        n = env.action_space.n
        if np is not None:
            return np.full(n, 1 / n)

        class _P(list):
            def sum(self):  # minimal numpy-like API
                from builtins import sum as _sum

                return _sum(self)

        return _P([1 / n] * n)

    with torch.no_grad():
        state, value, policy_logits = net.initial(obs)
        root = Node(prior=1.0, state=state)
        root.children = {a: Node(prior=float(p)) for a, p in enumerate(torch.softmax(policy_logits, dim=-1))}
        root.visit_count = 1
        discount = 0.997

        for _ in range(num_simulations):
            node = root
            search_path = [node]
            actions_taken: List[int] = []

            while node.expanded():
                action, node = _select_child(node)
                actions_taken.append(action)
                search_path.append(node)

            parent = search_path[-2]
            state, reward, value, policy_logits = net.recurrent(parent.state, actions_taken[-1])
            node.state = state
            node.reward = float(reward)
            node.children = {a: Node(prior=float(p)) for a, p in enumerate(torch.softmax(policy_logits, dim=-1))}
            leaf_value = float(value)

            for n in reversed(search_path):
                n.visit_count += 1
                n.value_sum += leaf_value
                leaf_value = n.reward + discount * leaf_value

        visits = torch.tensor([c.visit_count for c in root.children.values()], dtype=torch.float32)
        policy = visits / visits.sum()
    return policy


class MiniMu:
    """Convenience wrapper around ``MiniMuNet`` and a Gymnasium environment."""

    def __init__(self, env_id: str = "CartPole-v1") -> None:
        self.env = gym.make(env_id, render_mode="rgb_array")
        obs_dim = math.prod(self.env.observation_space.shape)
        self.action_dim = self.env.action_space.n
        self.net = MiniMuNet(obs_dim, self.action_dim)

    def policy(self, obs: Sequence[float] | torch.Tensor | np.ndarray) -> torch.Tensor:
        if _TORCH:
            with torch.no_grad():
                return mcts_policy(self.net, self.env, obs)
        return mcts_policy(self.net, self.env, obs)

    def act(self, obs) -> int:
        policy = self.policy(obs)
        if _TORCH:
            return int(torch.multinomial(policy, 1).item())
        return random.randrange(self.action_dim)

    def reset(self) -> np.ndarray:
        obs, _ = self.env.reset()
        return obs


def play_episode(agent: MiniMu, render: bool = True, max_steps: int = 500) -> Tuple[List, float]:
    """Run at most ``max_steps`` transitions and always close the environment."""
    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    frames: List = []
    total_reward = 0.0
    try:
        obs = agent.reset()
        for _ in range(max_steps):
            if render:
                frames.append(agent.env.render())
            action = agent.act(obs)
            obs, reward, done, truncated, _ = agent.env.step(action)
            total_reward += float(reward)
            if done or truncated:
                break
        if render:
            frames.append(agent.env.render())
    finally:
        agent.env.close()
    return frames, total_reward
