# SPDX-License-Identifier: Apache-2.0
"""Exact teaching targets for the finite, deterministic MiniWorld demo.

This is synthetic oracle supervision, not MuZero self-play or a learned planner.
The network is local to one fixed maze, whose layout is not in its observation.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class Transition:
    """A validated, copied environment transition with explicit teaching targets."""

    obs: np.ndarray
    action: int
    reward: float
    next_obs: np.ndarray
    done: bool
    value: float
    policy: np.ndarray
    next_value: float
    next_policy: np.ndarray


class MiniWorldTargets:
    """Shortest-path Bellman oracle with absorbing goal and discount in (0, 1)."""

    def __init__(
        self, size: int, obstacles: Iterable[tuple[int, int]], goal: tuple[int, int], discount: float = 0.99
    ) -> None:
        if not isinstance(size, int) or not 2 <= size <= 64:
            raise ValueError("MiniWorld training requires an integer grid size from 2 to 64")
        if not math.isfinite(discount) or not 0 < discount < 1:
            raise ValueError("discount must be finite and strictly between zero and one")
        self.size = size
        self.discount = discount
        self.obstacles = frozenset(tuple(cell) for cell in obstacles)
        self.goal = tuple(goal)
        cells = {(x, y) for x in range(size) for y in range(size)}
        if not self.obstacles <= cells or self.goal not in cells or self.goal in self.obstacles:
            raise ValueError("Maze obstacles and unblocked goal must be inside the grid")
        self.distances = {self.goal: 0}
        queue = deque([self.goal])
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                cell = (x + dx, y + dy)
                if cell in cells and cell not in self.obstacles and cell not in self.distances:
                    self.distances[cell] = self.distances[(x, y)] + 1
                    queue.append(cell)

    def state(self, obs: np.ndarray) -> tuple[int, int]:
        obs = np.asarray(obs)
        if obs.shape != (self.size**2,) or not np.isfinite(obs).all():
            raise ValueError("Observation must be a finite flat size**2 one-hot vector")
        if np.count_nonzero(obs == 1) != 1 or np.count_nonzero(obs) != 1:
            raise ValueError("Observation must be one-hot")
        cell = divmod(int(obs.argmax()), self.size)
        if cell in self.obstacles:
            raise ValueError("Observation places agent in an obstacle")
        return cell

    def successor(self, cell: tuple[int, int], action: int) -> tuple[int, int]:
        dx, dy = ((0, 1), (1, 0), (0, -1), (-1, 0))[action]
        nxt = (max(0, min(self.size - 1, cell[0] + dx)), max(0, min(self.size - 1, cell[1] + dy)))
        return cell if nxt in self.obstacles else nxt

    def value(self, cell: tuple[int, int]) -> float:
        distance = self.distances.get(cell)
        if distance == 0:
            return 0.0  # no reward after termination
        if distance is None:
            return -0.01 / (1 - self.discount)  # unreachable: infinite step penalties
        # distance-1 penalties, followed by a terminal reward of one
        power = self.discount ** (distance - 1)
        return -0.01 * (1 - power) / (1 - self.discount) + power

    def targets(self, cell: tuple[int, int]) -> tuple[float, np.ndarray]:
        if cell == self.goal:
            return 0.0, np.zeros(4, dtype=np.float32)  # terminal policy is masked
        q = []
        for action in range(4):
            nxt = self.successor(cell, action)
            q.append(1.0 if nxt == self.goal else -0.01 + self.discount * self.value(nxt))
        best: np.ndarray = np.isclose(q, max(q), rtol=0, atol=1e-12).astype(np.float32)
        return self.value(cell), best / best.sum()

    def transition(self, obs: np.ndarray, action: int, reward: float, next_obs: np.ndarray, done: bool) -> Transition:
        state, nxt = self.state(obs), self.state(next_obs)
        if isinstance(action, bool) or not isinstance(action, (int, np.integer)) or not 0 <= action < 4:
            raise ValueError("action must be an integer from zero through three")
        if not isinstance(done, (bool, np.bool_)):
            raise ValueError("done must be a boolean")
        if state == self.goal:
            raise ValueError("Cannot replay an action after terminal state; reset first")
        expected_done = nxt == self.goal
        expected_reward = 1.0 if expected_done else -0.01
        if nxt != self.successor(state, action) or done != expected_done:
            raise ValueError("Transition does not match this learner's fixed MiniWorld")
        if not math.isfinite(reward) or not math.isclose(reward, expected_reward, abs_tol=1e-8):
            raise ValueError("Reward does not match MiniWorld transition")
        value, policy = self.targets(state)
        next_value, next_policy = self.targets(nxt)
        return Transition(
            np.asarray(obs, dtype=np.float32).copy(),
            int(action),
            float(reward),
            np.asarray(next_obs, dtype=np.float32).copy(),
            bool(done),
            value,
            policy,
            next_value,
            next_policy,
        )
