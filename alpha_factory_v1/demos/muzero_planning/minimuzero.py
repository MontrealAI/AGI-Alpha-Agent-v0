# SPDX-License-Identifier: Apache-2.0
"""Bounded, single-player MuZero-style search over a learned latent model.

This educational implementation uses scalar reward/value heads, not the full
paper's categorical supports, distributed actors or Atari training recipe.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Any, Sequence
import warnings

try:
    import numpy as np
except (ModuleNotFoundError, OSError):  # pragma: no cover - optional dependency
    np = None  # type: ignore[assignment]
try:
    import gymnasium as gym
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    gym = None
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    _TORCH = True
except (ModuleNotFoundError, OSError):  # pragma: no cover - optional dependency
    _TORCH = False


def bounded_int(name: str, value: int, low: int, high: int) -> int:
    """Reject booleans, fractional values and unbounded work requests."""
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")
    return value


def require_dependencies() -> None:
    """Fail closed for real experiments; compatibility stubs are never training."""
    if not _TORCH or gym is None or np is None:
        raise RuntimeError("Install the MuZero demo requirements: torch, numpy and gymnasium[classic-control]")


if _TORCH:

    class MiniMuNet(nn.Module):  # type: ignore[misc]
        """Differentiable representation, dynamics, reward, policy and value heads."""

        def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 32) -> None:
            super().__init__()
            self.obs_dim = bounded_int("obs_dim", obs_dim, 1, 4096)
            self.action_dim = bounded_int("action_dim", action_dim, 2, 32)
            self.hidden_dim = bounded_int("hidden_dim", hidden_dim, 8, 256)
            self.repr = nn.Sequential(nn.Linear(obs_dim, hidden_dim), nn.Tanh())
            self.dyn = nn.Linear(hidden_dim + action_dim, hidden_dim + 1)
            self.policy_head = nn.Linear(hidden_dim, action_dim)
            self.value_head = nn.Linear(hidden_dim, 1)

        def initial(self, obs: Any) -> tuple[Any, Any, Any]:
            x = torch.as_tensor(obs, dtype=torch.float32, device=self.value_head.weight.device)
            state = self.repr(x)
            return state, self.value_head(state), self.policy_head(state)

        def recurrent(self, state: Any, action: Any) -> tuple[Any, Any, Any, Any]:
            a = torch.as_tensor(action, dtype=torch.long, device=state.device)
            a = F.one_hot(a, num_classes=self.action_dim).to(state.dtype)
            out = self.dyn(torch.cat([state, a], dim=-1))
            next_state = torch.tanh(out[..., 1:])
            return next_state, out[..., :1], self.value_head(next_state), self.policy_head(next_state)

else:  # pragma: no cover - compatibility for historical minimal-install callers

    class MiniMuNet:  # type: ignore[no-redef]
        def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 32) -> None:
            self.action_dim = action_dim


@dataclass
class Node:
    prior: float
    state: Any = None
    reward: float = 0.0
    visit_count: int = 0
    value_sum: float = 0.0
    children: dict[int, Node] = field(default_factory=dict)

    def expanded(self) -> bool:
        return bool(self.children)

    def value(self) -> float:
        return self.value_sum / self.visit_count if self.visit_count else 0.0


@dataclass
class MinMaxStats:
    minimum: float = math.inf
    maximum: float = -math.inf

    def update(self, value: float) -> None:
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

    def normalize(self, value: float) -> float:
        if self.maximum > self.minimum:
            return (value - self.minimum) / (self.maximum - self.minimum)
        return value


def _select_child(node: Node, discount: float = 0.997, stats: MinMaxStats | None = None) -> tuple[int, Node]:
    """PUCT uses the incoming reward plus discounted child state value."""
    if not node.children:
        raise ValueError("Cannot select from an unexpanded node")
    stats = stats or MinMaxStats()

    def score(child: Node) -> float:
        q = stats.normalize(child.reward + discount * child.value()) if child.visit_count else 0.0
        pb_c = math.log((node.visit_count + 19653) / 19652) + 1.25
        return q + pb_c * child.prior * math.sqrt(node.visit_count + 1) / (1 + child.visit_count)

    # Stable action order breaks exact ties reproducibly.
    action = max(node.children, key=lambda a: score(node.children[a]))
    return action, node.children[action]


def _expand(node: Node, state: Any, reward: float, value: float, logits: Any, actions: int) -> None:
    if not math.isfinite(reward) or not math.isfinite(value):
        raise ValueError("Model returned a non-finite reward or value")
    if logits.shape != (actions,) or not torch.isfinite(logits).all() or not torch.isfinite(state).all():
        raise ValueError("Model returned invalid latent state or policy logits")
    node.state, node.reward = state, reward
    node.children = {a: Node(float(p)) for a, p in enumerate(torch.softmax(logits, dim=-1))}


def search(
    net: Any,
    obs: Any,
    num_simulations: int = 64,
    *,
    discount: float = 0.997,
    max_depth: int = 16,
    exploration_rng: random.Random | None = None,
) -> Node:
    """Search only model predictions: never call the real environment in the tree."""
    bounded_int("num_simulations", num_simulations, 1, 512)
    bounded_int("max_depth", max_depth, 1, 64)
    if not math.isfinite(discount) or not 0 <= discount <= 1:
        raise ValueError("discount must be finite and in [0, 1]")
    if not _TORCH:
        raise RuntimeError("torch is required for learned-model search")
    stats = MinMaxStats()
    with torch.no_grad():
        state, value, logits = net.initial(obs)
        root = Node(1.0)
        _expand(root, state, 0.0, float(value), logits, net.action_dim)
        if exploration_rng is not None:
            noise = [exploration_rng.gammavariate(0.3, 1.0) for _ in root.children]
            total = sum(noise)
            for child, sample in zip(root.children.values(), noise):
                child.prior = 0.75 * child.prior + 0.25 * sample / total
        for _ in range(num_simulations):
            node, path = root, [root]
            while node.expanded() and len(path) <= max_depth:
                parent = node
                action, node = _select_child(parent, discount, stats)
                path.append(node)
                if not node.expanded():
                    state, reward, value, logits = net.recurrent(parent.state, action)
                    _expand(node, state, float(reward), float(value), logits, net.action_dim)
                    break
            else:
                # At the depth cap, use the current state estimate without expanding.
                value = node.value()
            backed_value = float(value)
            for visited in reversed(path):
                visited.visit_count += 1
                visited.value_sum += backed_value
                stats.update(visited.reward + discount * visited.value())
                backed_value = visited.reward + discount * backed_value
    return root


class _Policy(list[float]):
    def sum(self) -> float:
        return sum(self)


def mcts_policy(net: Any, env: Any, obs: Any, num_simulations: int = 64) -> Any:
    """Return normalized root visits; minimal installs retain a labeled uniform fallback."""
    bounded_int("num_simulations", num_simulations, 1, 512)
    if not _TORCH:
        n = env.action_space.n
        return np.full(n, 1 / n) if np is not None else _Policy([1 / n] * n)
    root = search(net, obs, num_simulations)
    return torch.tensor([c.visit_count / num_simulations for c in root.children.values()])


class _CompatibilityEnv:
    """Explicitly synthetic fallback retained for older lightweight callers."""

    observation_space = type("Observation", (), {"shape": (4,)})
    action_space = type("Action", (), {"n": 2})

    def reset(self, *, seed: int | None = None) -> tuple[list[float], dict[str, Any]]:
        return [0.0] * 4, {"synthetic": True}

    def step(self, action: int) -> tuple[list[float], float, bool, bool, dict[str, Any]]:
        return [0.0] * 4, 0.0, True, False, {"synthetic": True}

    def render(self) -> list[Any]:
        return []

    def close(self) -> None:
        pass


class MiniMu:
    """Seeded CPU model and discrete-action environment; untrained until optimized."""

    def __init__(
        self,
        env_id: str = "CartPole-v1",
        *,
        seed: int = 42,
        simulations: int = 64,
        render_mode: str | None = "rgb_array",
    ) -> None:
        self.seed = bounded_int("seed", seed, 0, 2**31 - 1)
        self.simulations = bounded_int("simulations", simulations, 1, 512)
        self.env_id = env_id
        self.rng = random.Random(seed)
        self.synthetic = gym is None
        if self.synthetic:
            warnings.warn("Gymnasium unavailable: synthetic compatibility environment, not CartPole", RuntimeWarning)
            self.env: Any = _CompatibilityEnv()
        elif env_id == "MiniChoice-v0":
            from .training import MiniChoice

            self.env = MiniChoice(render_mode=render_mode)
        else:
            self.env = gym.make(env_id, render_mode=render_mode)
        try:
            self.obs_dim = math.prod(self.env.observation_space.shape)
            if getattr(self.env.action_space, "start", 0) != 0:
                raise ValueError("Actions must be zero-based")
            self.action_dim = int(self.env.action_space.n)
            bounded_int("action_dim", self.action_dim, 2, 32)
            if _TORCH:
                # Initialization and action sampling do not mutate process-global RNG state.
                with torch.random.fork_rng(devices=[]):
                    torch.manual_seed(seed)
                    self.net = MiniMuNet(self.obs_dim, self.action_dim)
            else:
                warnings.warn("PyTorch unavailable: uniform policy, no learned model", RuntimeWarning)
                self.net = MiniMuNet(self.obs_dim, self.action_dim)
        except (AttributeError, TypeError, ValueError):
            self.env.close()
            raise ValueError("MiniMu requires flat numeric observations and 2–32 discrete actions") from None

    def policy(self, obs: Sequence[float] | Any) -> Any:
        if np is not None:
            obs = np.asarray(obs, dtype=np.float32).reshape(-1)
            if obs.size != self.obs_dim or not np.isfinite(obs).all():
                raise ValueError("Observation must have the expected size and finite values")
        return mcts_policy(self.net, self.env, obs, self.simulations)

    def act(self, obs: Any) -> int:
        policy = self.policy(obs)
        return self.rng.choices(range(self.action_dim), weights=[float(p) for p in policy], k=1)[0]

    def reset(self, *, seed: int | None = None) -> Any:
        obs, _ = self.env.reset(seed=self.seed if seed is None else seed)
        return obs


def play_episode(agent: MiniMu, render: bool = True, max_steps: int = 500) -> tuple[list[Any], float]:
    """Run at most 500 transitions and always close the environment."""
    frames: list[Any] = []
    total_reward = 0.0
    try:
        bounded_int("max_steps", max_steps, 1, 500)
        obs = agent.reset()
        for _ in range(max_steps):
            if render:
                frames.append(agent.env.render())
            obs, reward, done, truncated, _ = agent.env.step(agent.act(obs))
            total_reward += float(reward)
            if done or truncated:
                break
        if render:
            frames.append(agent.env.render())
    finally:
        agent.env.close()
    return frames, total_reward
