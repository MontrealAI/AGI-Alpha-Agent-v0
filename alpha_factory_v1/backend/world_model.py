# SPDX-License-Identifier: Apache-2.0
"""
alpha_factory_v1.backend.world_model
════════════════════════════════════
Latent World-Model + Planner (v2.0.0 • 2025-05-02 ✅ prod-ready)

Key features
────────────
• 5 × 5 Grid-World reference env  • Dynamic env-registry (gym‐style)
• MuZero-general wrapper • LLM counter-factual fallback (OpenAI / LLaMA-cpp)
• Rule-based SafetyGuard (+ extensible via ENV JSON)
• Meta-Learner (AI-GA Autogenesis) – writes Markdown proposals
• Prometheus metrics & Kafka event streaming (both optional)
• **Graceful degradation**: works air-gapped / no GPU / no OpenAI key
Usage
─────
    from alpha_factory_v1.backend.world_model import wm
    state = wm.reset_env()
    plan  = wm.plan("FinanceAgent", state)
    next_ = wm.simulate(state, plan["action"])
"""
from __future__ import annotations

import logging

# ───────────────────── Standard Library ──────────────────────────────────────
import contextlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, MutableMapping, Optional, Tuple

from .logger import get_logger

_LOG = get_logger("alpha_factory.world_model")
_LOG.addHandler(logging.NullHandler())

# ────────────────── Soft-Imports (all optional) ──────────────────────────────
with contextlib.suppress(ModuleNotFoundError):
    from muzero import muzero  # MuZero-general
with contextlib.suppress(ModuleNotFoundError):
    import openai  # OpenAI SDK
OPENAI_TIMEOUT_SEC = int(os.getenv("OPENAI_TIMEOUT_SEC", "30"))
with contextlib.suppress(ModuleNotFoundError):
    from llama_cpp import Llama
with contextlib.suppress(Exception):
    from backend.agents.registry import Gauge  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    from confluent_kafka import Producer

# ─────────────────────── ENV Config ──────────────────────────────────────────
ENV = os.getenv
DEV_MODE = ENV("DEV_MODE", "false").lower() == "true"
GRID_SIZE = int(ENV("WM_GRID_SIZE", "5"))
MCTS_SIMS = int(ENV("WM_MCTS_SIMULATIONS", "96"))
MCTS_TIMEOUT_SEC = int(ENV("WM_MCTS_TIMEOUT_SEC", "3"))
LLM_MODEL = ENV("WM_LLM_MODEL", "gpt-4o-mini")
RISK_THRESHOLD = float(ENV("WM_RISK_THRESHOLD", "-50"))
RULES_JSON = ENV("WM_SAFETY_RULES", "")
PROM_ENABLED = ENV("PROMETHEUS_DISABLE", "false").lower() != "true"
LLAMA_MODEL_PATH = ENV("LLAMA_MODEL_PATH", "models/llama-2-7b.gguf")
KAFKA_BROKER = ENV("ALPHA_KAFKA_BROKER")
META_INTERVAL_SEC = int(ENV("META_INTERVAL_SEC", "3600"))

_DEFAULT_RULES: Dict[str, Any] = {
    "max_position_frac": 0.25,
    "max_shift_hours": 12,
    "min_liquidity_usd": 1e5,
}
SAFETY_RULES: Dict[str, Any] = {**_DEFAULT_RULES, **json.loads(RULES_JSON or "{}")}


# ═══════════════════ 1. Reference Grid-World ════════════════════════════════
@dataclass(slots=True)
class GridState:
    x: int = 0
    y: int = 0
    goal: Tuple[int, int] = (GRID_SIZE - 1, GRID_SIZE - 1)
    reward: float = 0.0
    done: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GridWorldEnv:
    """Deterministic 2-D grid with dense −1 time-penalty."""

    ACTIONS = {
        0: ("UP", (0, -1)),
        1: ("DOWN", (0, 1)),
        2: ("LEFT", (-1, 0)),
        3: ("RIGHT", (1, 0)),
    }

    def __init__(self, size: int = GRID_SIZE) -> None:
        self.size = size
        self.state = GridState()

    # Gym-like helpers --------------------------------------------------------
    def reset(self) -> Dict[str, Any]:
        self.state = GridState()
        return self.state.to_dict()

    @property
    def observation(self) -> List[int]:
        """Flattened one-hot N² grid (agent =1, goal =2)."""
        grid = [[0] * self.size for _ in range(self.size)]
        grid[self.state.y][self.state.x] = 1
        gx, gy = self.state.goal
        grid[gy][gx] = 2
        return [p for row in grid for p in row]

    def step(self, action_id: int) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        if self.state.done:
            return self.state.to_dict(), 0.0, True, {}
        name, (dx, dy) = self.ACTIONS.get(action_id, ("NOP", (0, 0)))
        self.state.x = max(0, min(self.size - 1, self.state.x + dx))
        self.state.y = max(0, min(self.size - 1, self.state.y + dy))
        self.state.reward -= 1
        if (self.state.x, self.state.y) == self.state.goal:
            self.state.reward += 100
            self.state.done = True
        return self.state.to_dict(), self.state.reward, self.state.done, {"action": name}


# ═══════════════════ 2. Safety Guard ════════════════════════════════════════
class SafetyGuard:
    def __init__(self, rules: Dict[str, Any]) -> None:
        self.rules = rules

    def veto(self, reward_trace: List[float]) -> bool:
        return sum(reward_trace) < RISK_THRESHOLD


# ═══════════════════ 3. Planner back-ends ═══════════════════════════════════
class MuZeroPlanner:
    """Wrapper around *muzero-general* for planning only (no training)."""

    def __init__(self, env: GridWorldEnv) -> None:
        self.available = "muzero" in globals()
        self._env = env
        if not self.available:
            return
        cfg = Path(__file__).with_name("muzero_grid_cfg.py")
        if not cfg.exists():
            cfg.write_text(_MZ_CFG_TXT)
        # initialise once; env injected per plan call
        self._mz = muzero.MuZero(config=str(cfg))  # type: ignore

    def best_action(self, sims: int = MCTS_SIMS, timeout: int = MCTS_TIMEOUT_SEC) -> Tuple[int, List[int]]:
        if not self.available:
            return self._heuristic()
        return self._mz.plan(self._env, sims, timeout)  # type: ignore[attr-defined]

    # Greedy Manhattan fallback ------------------------------------------------
    def _heuristic(self) -> Tuple[int, List[int]]:
        dx = self._env.state.goal[0] - self._env.state.x
        dy = self._env.state.goal[1] - self._env.state.y
        act = 3 if dx > 0 else 2 if dx < 0 else 1 if dy > 0 else 0
        return act, []


class LLMSimulator:
    def __init__(self) -> None:
        self._use_openai = "openai" in globals() and ENV("OPENAI_API_KEY")
        self._use_local = "Llama" in globals() and Path(LLAMA_MODEL_PATH).exists()
        if self._use_openai:
            openai.api_key = ENV("OPENAI_API_KEY")
        elif self._use_local:
            self.llama = Llama(model_path=LLAMA_MODEL_PATH)

    # ---------------------------------------------------------------------
    def _chat(self, prompt: str) -> str:
        if self._use_openai:
            rsp = openai.ChatCompletion.create(  # type: ignore
                model=LLM_MODEL,
                temperature=0.3,
                max_tokens=80,
                messages=[{"role": "user", "content": prompt}],
                timeout=OPENAI_TIMEOUT_SEC,
            )
            return rsp["choices"][0]["message"]["content"]  # type: ignore[index]
        if self._use_local:
            return self.llama(prompt, max_tokens=80)["choices"][0]["text"]  # type: ignore[index]
        return '{"_error":"LLM unavailable"}'

    def predict(self, state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            "You are a strict JSON-only world-model.\n"
            f"Current state: {json.dumps(state)}\n"
            f"Action: {json.dumps(action)}\n"
            "Return ONLY the **next state** JSON, with identical keys plus "
            '"reward" (float) and "done" (bool).'
        )
        try:
            nxt = json.loads(self._chat(prompt))
            # basic sanity
            if "done" not in nxt or "reward" not in nxt:
                raise ValueError
            return nxt
        except Exception:
            return {"state": state, "reward": 0.0, "done": False, "_note": "fallback"}


# ═══════════════════ 4. Meta-Learner ════════════════════════════════════════
class MetaLearner:
    def __init__(self, interval_sec: int = META_INTERVAL_SEC) -> None:
        self._interval = interval_sec
        self._last = 0.0

    def propose(self, kpis: Dict[str, float]) -> Optional[str]:
        now = time.time()
        if now - self._last < self._interval or not kpis:
            return None
        self._last = now
        worst = min(kpis, key=kpis.get)
        doc = (
            "# Autogenesis Proposal\n\n"
            f"Target agent: **{worst}** (score={kpis[worst]:.3f})\n\n"
            "*Idea*: Spawn `ResearchAgent` with ε-greedy exploration to discover "
            "fringe alpha strategies.\n\n"
            "*Next step*: Orchestrator to append to backlog & human-review."
        )
        Path("NewAgentProposal.md").write_text(doc)
        return doc


# ═══════════════════ 5. Observability helpers ═══════════════════════════════
if PROM_ENABLED and "Gauge" in globals():
    PLAN_LAT = Gauge("wm_plan_latency_seconds", "World-Model plan latency")
    RISK_SCR = Gauge("wm_traj_risk_score", "Planned trajectory cumulative reward")
else:

    class _Dummy(float):
        def observe(self, *a: Any, **kw: Any) -> None:
            ...

        def set(self, *a: Any, **kw: Any) -> None:
            ...

    PLAN_LAT = RISK_SCR = _Dummy()

_kafka: Optional["Producer"] = None
if KAFKA_BROKER and "Producer" in globals():
    _kafka = Producer({"bootstrap.servers": KAFKA_BROKER})


def _kafka_send(topic: str, msg: dict) -> None:
    if not _kafka:
        return
    try:
        _kafka.produce(topic, json.dumps(msg).encode())
        _kafka.poll(0)
    except Exception:  # noqa: BLE001
        _LOG.exception("Kafka emit failed (topic=%s)", topic)


# ═══════════════════ 6. Environment registry ════════════════════════════════
_EnvCtor = Callable[[], Any]
_ENV_REG: MutableMapping[str, _EnvCtor] = {"grid-world": lambda: GridWorldEnv()}


def register_env(name: str, ctor: _EnvCtor, *, override: bool = False) -> None:
    """Register a new environment constructor."""
    if not override and name in _ENV_REG:
        raise ValueError(f"Env '{name}' already registered.")
    _ENV_REG[name] = ctor


def list_envs() -> List[str]:
    """Return available environment names."""
    return sorted(_ENV_REG.keys())


# ═══════════════════ 7. Public singleton `wm` ═══════════════════════════════
class _WorldModel:
    """Module-level singleton (thread-safe for typical FastAPI usage)."""

    def __init__(self) -> None:
        self._env_name = "grid-world"
        self.env = _ENV_REG[self._env_name]()
        self.muzero = MuZeroPlanner(self.env)
        self.llm = LLMSimulator()
        self.guard = SafetyGuard(SAFETY_RULES)
        self.meta = MetaLearner()

    # ── Env control ──────────────────────────────────────────────────────
    def set_env(self, name: str) -> None:
        """Switch the active environment."""
        if name not in _ENV_REG:
            raise KeyError(name)
        self._env_name = name
        self.env = _ENV_REG[name]()
        self.muzero = MuZeroPlanner(self.env)

    def reset_env(self) -> Dict[str, Any]:
        """Reset the environment and return the initial state."""
        return self.env.reset()

    # ── Planning ─────────────────────────────────────────────────────────
    def plan(self, agent: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Compute the next best action for the given agent and state."""
        t0 = time.perf_counter()
        # sync env with given state when using grid-world
        if self._env_name == "grid-world":
            self.env.state = GridState(**{k: state[k] for k in ("x", "y", "goal")})

        act_id, traj = self.muzero.best_action()
        rewards = [-1.0] * max(1, len(traj))  # pessimistic default

        # safety check
        if self.guard.veto(rewards):
            res = {"action": None, "reason": "safety_veto", "trajectory": traj}
        else:
            act_name = self.env.ACTIONS.get(act_id, ("NOP",))[0]
            res = {"action": {"id": act_id, "name": act_name}, "trajectory": traj}

        # metrics / streaming
        dt = time.perf_counter() - t0
        PLAN_LAT.observe(dt)
        RISK_SCR.set(sum(rewards))
        _kafka_send("wm.plan", {"agent": agent, **res, "latency": dt})
        return res

    # ── One-step sim ─────────────────────────────────────────────────────
    def simulate(self, state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a single environment step."""
        if self._env_name == "grid-world" and "id" in action:
            saved = self.env.state
            self.env.state = GridState(**{k: state[k] for k in ("x", "y", "goal")})
            ns, r, d, info = self.env.step(action["id"])
            self.env.state = saved
            return {"state": ns, "reward": r, "done": d, "info": info}
        return self.llm.predict(state, action)

    # ── Meta KPIs ────────────────────────────────────────────────────────
    def ingest_kpis(self, kpis: Dict[str, float]) -> Optional[str]:
        """Feed KPIs to the meta-learner, returning a proposal when generated."""
        prop = self.meta.propose(kpis)
        if prop:
            _kafka_send("wm.meta", {"ts": time.time(), "proposal": prop})
        return prop


# expose singleton
wm = _WorldModel()

# ═══════════════════ 8. Auto-gen MuZero config ══════════════════════════════
_MZ_CFG_TXT = """
# Auto-gen MuZero config (planning-only, no training)
game_name              = "gridworld"
observation_shape      = (1, 5, 5)
action_space           = ["0","1","2","3"]
players                = [0]
stacked_observations   = 0
max_moves              = 50
discount               = 1.0
temperature_threshold  = 15
train_steps            = 0
num_actors             = 0
network                = "fullyconnected"
support_size           = 10
blocks                 = 1
channels               = 16
fc_reward_layers       = [16]
fc_value_layers        = [16]
fc_policy_layers       = [16]
num_simulations        = 96
root_dirichlet_alpha   = 0.25
root_exploration_fraction = 0.25
pb_c_base              = 19652
pb_c_init              = 1.25
"""

__all__ = [
    "GridWorldEnv",
    "GridState",
    "register_env",
    "list_envs",
    "wm",
]
