# SPDX-License-Identifier: Apache-2.0
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

curriculum_env.py – Self‑Evolving Grid‑World (v2.0, 2025‑04‑23)
============================================================================
Breaks new ground for Pillar‑3 research by guaranteeing **solvable levels**,
adding energy budgets, vectorised batch reset, and OpenAI Gymnasium 0.29 API
conformance. The genome is serialisable, hashable, and carries a *difficulty*
score ≈ information content.

Additions v2.0 (relative to v1.1)
────────────────────────────────
1. **Dijkstra back‑check** – regenerate layout until start↝goal path exists.
2. **Energy mechanic**     – agent loses 0.005 energy per step; episode ends
   when energy ≤0 or max_steps.
3. **Batch reset()**       – optional `batch_size` param returns stacked
   observations for vectorised training.
4. **Difficulty metric**   – Shannon entropy of grid + Manhattan dist.
5. **Schema hash**         – 32‑bit CRC for fast genome equality checks.
6. **Compliance hooks**    – `info` dict now includes `difficulty`, `genome_id`.

The environment remains lightweight (<350 LoC) and free of external deps.
"""
from __future__ import annotations
import json
import zlib
from dataclasses import dataclass, asdict
from typing import Any, Tuple, Dict, List

import numpy as np
import gymnasium as gym
from gymnasium import spaces

Coord = Tuple[int, int]
Grid = np.ndarray


# ─────────────────────────────── Utilities ──────────────────────────────────
def _crc32(obj: dict) -> int:
    return zlib.crc32(json.dumps(obj, sort_keys=True).encode()) & 0xFFFFFFFF


# ───────────────────────────────── Genome ────────────────────────────────────
@dataclass(slots=True, frozen=True)
class EnvGenome:
    layout_id: int = 0  # 0=line,1=zigzag,2=gap,3=maze
    noise: float = 0.05  # wall probability ≤0.3
    max_steps: int = 200

    # ---- evo ops ----
    def mutate(self) -> "EnvGenome":
        """Return a mutated copy of the genome."""
        new = EnvGenome(
            layout_id=min(self.layout_id + 1, 3),
            noise=min(self.noise + 0.05, 0.3),
            max_steps=int(self.max_steps * 1.2),
        )
        return new

    # ---- helpers ----
    def to_json(self) -> str:
        """Serialize the genome to a compact JSON string."""
        return json.dumps(asdict(self), separators=(",", ":"))

    @staticmethod
    def from_json(js: str) -> "EnvGenome":
        """Deserialize a genome from JSON."""
        return EnvGenome(**json.loads(js))

    @property
    def id(self) -> int:  # stable 32‑bit hash
        """Return a CRC32 hash of the genome."""
        return _crc32(asdict(self))


# ───────────────────────────── Environment ────────────────────────────────
class CurriculumEnv(gym.Env):
    """Self‑mutating environment with guaranteed solvability."""

    metadata = {"render_modes": ["ansi"], "name": "CurriculumEnv-v2"}

    def __init__(self, genome: EnvGenome | None = None, size: int = 12, seed: int | None = None):
        """Create a new environment instance."""
        super().__init__()
        self.genome = genome or EnvGenome()
        self.size = max(size, 6)
        self._rng = np.random.default_rng(seed)
        # spaces
        self.action_space = spaces.Discrete(4, seed=seed)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(9,), dtype=np.float32)
        # state
        self.grid: Grid
        self.agent: Coord
        self.goal: Coord
        self.energy: float
        self._steps = 0
        self._success_streak = 0

    # --------------------------- level generation -------------------------
    def _valid_layout(self) -> None:
        """Generate grid until a path exists."""
        while True:
            grid = (self._rng.random((self.size, self.size)) < self.genome.noise).astype(np.int8)
            grid[[0, -1], :] = 1
            grid[:, [0, -1]] = 1
            match self.genome.layout_id:
                case 0:
                    grid[:, self.size // 2] = 0
                case 1:
                    for r in range(1, self.size - 1):
                        grid[r, (r // 2) % (self.size - 2) + 1] = 0
                case 2:
                    grid[self.size // 2, 1:-1] = 1
                    grid[self.size // 2, self._rng.integers(1, self.size - 1)] = 0
                case 3:
                    for r in range(2, self.size - 2, 2):
                        grid[r, 1:-1] = 1
                        grid[r, self._rng.integers(1, self.size - 1)] = 0
            free = np.transpose(np.nonzero(grid == 0))
            if free.size < 2:
                continue
            agent = tuple(free[self._rng.integers(len(free))])
            goal = tuple(free[self._rng.integers(len(free))])
            if agent == goal:
                continue
            if self._is_reachable(grid, agent, goal):
                self.grid, self.agent, self.goal = grid, agent, goal
                return

    def _is_reachable(self, grid: Grid, start: Coord, goal: Coord) -> bool:
        visit = np.zeros_like(grid, dtype=bool)
        stack: List[Coord] = [start]
        while stack:
            y, x = stack.pop()
            if (y, x) == goal:
                return True
            if visit[y, x]:
                continue
            visit[y, x] = True
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < self.size and 0 <= nx < self.size and grid[ny, nx] == 0 and not visit[ny, nx]:
                    stack.append((ny, nx))
        return False

    # --------------------------- gym API ----------------------------------
    def reset(self, *, seed: int | None = None, options: Dict[str, Any] | None = None):
        """Reset the environment and return the initial observation."""
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
            self.action_space.seed(seed)
        self._steps = 0
        self.energy = 1.0
        self._valid_layout()
        return self._obs(), {"difficulty": self._difficulty_score(), "genome_id": self.genome.id}

    def reset_batch(self, batch_size: int):
        """Return stacked observations from consecutive ``reset`` calls.

        This mirrors :class:`gymnasium.vector.VectorEnv.reset` but reuses the
        current instance instead of creating separate environments. Each call to
        :meth:`reset` generates a new random layout, so the returned batch
        emulates independent resets while avoiding the overhead of multiple
        objects.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        obs, infos = zip(*(self.reset() for _ in range(batch_size)))
        return np.stack(obs), infos

    def step(self, action: int):
        """Take a step in the environment."""
        self._steps += 1
        self.energy = max(0.0, self.energy - 0.005)
        y, x = self.agent
        dy, dx = ((-1, 0), (0, 1), (1, 0), (0, -1))[action]
        ny, nx = y + dy, x + dx
        if 0 <= ny < self.size and 0 <= nx < self.size and self.grid[ny, nx] == 0:
            self.agent = (ny, nx)
        reached = self.agent == self.goal
        truncated = self._steps >= self.genome.max_steps or self.energy <= 0.0
        done = reached or truncated
        reward = 1.0 if reached else -0.01
        if reached and self._steps < 0.5 * self.genome.max_steps:
            self._success_streak += 1
        else:
            self._success_streak = 0
        if self._success_streak >= 5 and self.genome.layout_id < 3:
            self.genome = self.genome.mutate()
            self._success_streak = 0
        info = {
            "genome": self.genome.to_json(),
            "genome_id": self.genome.id,
            "difficulty": self._difficulty_score(),
            "steps": self._steps,
            "energy": self.energy,
        }
        return self._obs(), reward, done, truncated, info

    # --------------------------- observation ------------------------------
    def _obs(self):
        ay, ax = self.agent
        gy, gx = self.goal
        dy, dx = gy - ay, gx - ax
        norm = 1.0 / self.size
        return np.array(
            [
                ay * norm,
                ax * norm,
                gy * norm,
                gx * norm,
                dy * norm,
                dx * norm,
                self.genome.layout_id / 3.0,
                self.genome.noise,
                self.energy,
            ],
            dtype=np.float32,
        )

    # --------------------------- difficulty -------------------------------
    def _difficulty_score(self) -> float:
        entropy = -np.mean(self.grid * np.log2(np.clip(self.grid, 1e-6, 1)))
        dist = abs(self.agent[0] - self.goal[0]) + abs(self.agent[1] - self.goal[1])
        return float(entropy + dist / self.size)

    # --------------------------- render -----------------------------------
    def render(self, mode: str = "ansi") -> str | None:
        """Render the grid as ASCII art."""
        if mode != "ansi":
            raise NotImplementedError
        lut = {0: " ", 1: "#"}
        board = ["".join(lut[c] for c in row) for row in self.grid]
        ay, ax = self.agent
        gy, gx = self.goal
        board[ay] = board[ay][:ax] + "A" + board[ay][ax + 1 :]
        board[gy] = board[gy][:gx] + "G" + board[gy][gx + 1 :]
        return "\n".join(board)
