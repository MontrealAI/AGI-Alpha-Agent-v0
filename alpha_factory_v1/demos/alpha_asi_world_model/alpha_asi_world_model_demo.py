# SPDX-License-Identifier: Apache-2.0
# alpha_asi_world_model_demo.py – Alpha‑Factory v1 👁
# =============================================================================
# This demo is a conceptual research prototype. References to "AGI" and
# "superintelligence" describe aspirational goals and do not indicate the
# presence of a real general intelligence. Use at your own risk.
# Production‑grade α‑ASI world‑model demo.
# POET‑style curriculum with MuZero learner (light MCTS), orchestrated by
# ≥5 Alpha‑Factory agents. Local‑first design with optional cloud helpers.
# Python 3.11+, PyTorch ≥2.2. Runs on CPU or GPU.
#
# Quick start .................  python -m alpha_asi_world_model_demo --demo
# Docker .....................  python -m alpha_asi_world_model_demo --emit-docker
# Helm .......................  python -m alpha_asi_world_model_demo --emit-helm
# Notebook ...................  python -m alpha_asi_world_model_demo --emit-notebook
# UI ..........................  http://localhost:7860
# =============================================================================
"""Open‑ended world‑model curriculum with strict defaults and enterprise
readiness. Configurable via `config.yaml` or environment variables;
integrates structured logging, safety guards and minimal ops helpers.

Key features
------------
* Config.yaml loader with automatic envvar override
* Structured logging (optional JSON mode)
* Lightweight MCTS for MuZeroTiny
* Multi‑environment batches (`Config.env_batch`)
* Testable hooks and graceful shutdown
* External LLM calls sandboxed with explicit timeouts
* Zero mandatory cloud dependencies
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim

try:
    import yaml  # soft‑dep; config file
except ImportError:
    yaml = None

# -----------------------------------------------------------------------------
# 0. Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("ALPHA_ASI_LOGLEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y‑%m‑%d %H:%M:%S",
)
LOG = logging.getLogger("alpha_asi_demo")

# =============================================================================
# 1.  Deterministic seed for reproducibility
# =============================================================================
_SEED = int(os.getenv("ALPHA_ASI_SEED", "42"))
random.seed(_SEED)
np.random.seed(_SEED)
torch.manual_seed(_SEED)


def _set_seed(val: int) -> None:
    global _SEED
    _SEED = val
    random.seed(val)
    np.random.seed(val)
    torch.manual_seed(val)


# =============================================================================
# 2.  Typed runtime configuration
#     Loads defaults → overrides with config.yaml → overrides with env vars.
# =============================================================================
@dataclass
class Config:
    env_batch: int = 2
    buffer_limit: int = 100_000
    hidden: int = 256
    lr: float = 5e-4
    train_batch: int = 256
    ui_tick: int = 100
    max_steps: int = 200_000
    mcts_simulations: int = 16
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    log_json: bool = False
    host: str = "127.0.0.1"
    port: int = 7860
    min_size: int = 5
    max_size: int = 10
    obstacle_density: float = 0.15
    mc_min: float = 0.2
    mc_max: float = 0.8
    mc_episodes: int = 3

    def update(self, **kw):
        for k, v in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)


def _str_to_bool(v: str) -> bool:
    """Return True for truthy strings."""
    return v.lower() in {"1", "true", "yes", "on"}


def _load_cfg() -> Config:
    cfg = Config()
    seed_raw = os.getenv("ALPHA_ASI_SEED", "42")
    # yaml config file optional
    if yaml:
        for p in (Path.cwd() / "config.yaml", Path.cwd() / "alpha_asi.yaml"):
            if p.exists():
                try:
                    data = yaml.safe_load(p.read_text())
                    if isinstance(data, dict):
                        if isinstance(data.get("general"), dict) and "seed" in data["general"]:
                            seed_raw = data["general"].get("seed", seed_raw)
                        for section in data.values():
                            if isinstance(section, dict):
                                cfg.update(**section)
                        cfg.update(**{k: v for k, v in data.items() if not isinstance(v, dict)})
                    LOG.info("Loaded config from %s", p)
                except Exception as e:
                    LOG.warning("Failed to parse %s: %s", p, e)
    # env overrides
    for k in cfg.__dict__.keys():
        env_key = "ALPHA_ASI_" + k.upper()
        if env_key in os.environ:
            val = os.environ[env_key]
            default = getattr(cfg, k)
            if isinstance(default, bool):
                val = _str_to_bool(val)
            else:
                try:
                    val = type(default)(val)
                except Exception:
                    pass
            setattr(cfg, k, val)
    # map 'auto' → 'cuda' if available else 'cpu'
    if isinstance(cfg.device, str) and cfg.device.lower() == "auto":
        cfg.device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        seed = int(seed_raw)
    except Exception:  # pragma: no cover - rarely triggered
        LOG.warning("Invalid seed %r; falling back to default", seed_raw)
        seed = 42
    _set_seed(seed)
    return cfg


CFG = _load_cfg()


# =============================================================================
# 3.  A2A message bus (in‑proc pub‑sub)
# =============================================================================
class A2ABus:
    _subs: Dict[str, List[Callable[[dict], None]]] = {}
    _lock = threading.Lock()

    @classmethod
    def publish(cls, topic: str, msg: dict):
        with cls._lock:
            callbacks = list(cls._subs.get(topic, []))
        for cb in callbacks:
            try:
                cb(msg)
            except Exception as exc:  # pragma: no cover
                LOG.error("[A2A] handler error on %s: %s", topic, exc)

    @classmethod
    def subscribe(cls, topic: str, cb: Callable[[dict], None]):
        with cls._lock:
            cls._subs.setdefault(topic, []).append(cb)

    @classmethod
    def unsubscribe(cls, topic: str, cb: Callable[[dict], None]):
        """Remove a previously registered callback."""
        with cls._lock:
            handlers = cls._subs.get(topic)
            if not handlers:
                return
            try:
                handlers.remove(cb)
            except ValueError:
                return
            if not handlers:
                cls._subs.pop(topic, None)


class Agent:
    """Base‑class for micro‑agents. Override .handle."""

    def __init__(self, name: str):
        self.name = name
        self._cb = self._on
        A2ABus.subscribe(name, self._cb)

    def _on(self, msg: dict):
        try:
            self.handle(msg)
        except Exception as exc:
            LOG.exception("[%s] crash: %s", self.name, exc)

    def emit(self, topic: str, msg: dict):
        A2ABus.publish(topic, msg)

    def close(self) -> None:
        """Unsubscribe the agent from the message bus."""
        A2ABus.unsubscribe(self.name, self._cb)

    # -----------------------------------------------------------------
    def handle(self, msg: dict):  # to be overridden
        raise NotImplementedError


# ---- dynamic loader ---------------------------------------------------------
REQUIRED = [
    "planning_agent.PlanningAgent",
    "research_agent.ResearchAgent",
    "strategy_agent.StrategyAgent",
    "market_agent.MarketAnalysisAgent",
    "codegen_agent.CodeGenAgent",
    "safety_agent.SafetyAgent",
]
MODROOT = "alpha_factory_v1.backend.agents."
AGENTS: Dict[str, Agent] = {}


def _boot(path: str) -> None:
    module_path, cls_name = (MODROOT + path).rsplit(".", 1)
    try:
        cls = getattr(importlib.import_module(module_path), cls_name)
        inst = cls()  # type: ignore[call-arg]
        name = getattr(inst, "name", getattr(inst, "NAME", cls_name))

        if not hasattr(inst, "handle") and hasattr(inst, "step"):
            step_fn = getattr(inst, "step")
            interval = getattr(inst, "CYCLE_SECONDS", 60) or 60

            class StepAdapter(Agent):
                def __init__(self, start_loop: bool = True) -> None:
                    super().__init__(name)
                    self._stop_event = threading.Event()
                    self._thread: Optional[threading.Thread] = None
                    if start_loop:
                        self._thread = threading.Thread(target=self._loop, daemon=True)
                        self._thread.start()

                def handle(self, _msg: dict) -> None:  # noqa: D401
                    pass

                def _loop(self) -> None:
                    while not self._stop_event.is_set():
                        try:
                            res = step_fn()
                            if asyncio.iscoroutine(res):
                                asyncio.run(res)
                        except Exception as exc:  # pragma: no cover
                            LOG.debug("[Adapter:%s] step error: %s", name, exc)
                        time.sleep(max(1, interval))

                def close(self) -> None:
                    self._stop_event.set()
                    if self._thread:
                        self._thread.join(timeout=1)
                    super().close()

            disable_threads = os.getenv("ALPHA_ASI_DISABLE_AGENT_THREADS", "0") in {"1", "true", "yes"}
            if os.getenv("PYTEST_CURRENT_TEST"):
                disable_threads = True
            inst = StepAdapter(start_loop=not disable_threads)
        else:
            if not hasattr(inst, "name"):
                inst.name = name  # type: ignore[attr-defined]
        LOG.info("[BOOT] loaded real agent %s", name)
    except Exception as exc:
        name = cls_name

        class Stub(Agent):
            def handle(self, _msg: dict) -> None:  # noqa: D401
                LOG.debug("[Stub:%s] ← %s", cls_name, _msg)

        inst = Stub(name)
        LOG.warning("[BOOT] stubbed %s (%s)", cls_name, exc)

    AGENTS[name] = inst


for _p in REQUIRED:
    _boot(_p)
while len(AGENTS) < 5:
    idx = len(AGENTS) + 1

    class Fallback(Agent):
        def handle(self, _msg):
            LOG.debug("[Fallback%d] ← %s", idx, _msg)

    AGENTS[f"Fallback{idx}"] = Fallback(f"Fallback{idx}")


# =============================================================================
# 4.  MuZeroTiny with lightweight MCTS
# =============================================================================
class Repr(nn.Module):
    def __init__(self, input_dim: int, hidden: int):
        super().__init__()
        self.l = nn.Linear(input_dim, hidden)

    def forward(self, x):
        return torch.tanh(self.l(x))


class Dyn(nn.Module):
    def __init__(self, hidden: int, act_dim: int):
        super().__init__()
        self.r = nn.Linear(hidden + act_dim, 1)
        self.h = nn.Linear(hidden + act_dim, hidden)

    def forward(self, h, a):
        x = torch.cat([h, a], -1)
        return self.r(x), torch.tanh(self.h(x))


class Pred(nn.Module):
    def __init__(self, hidden: int, act_dim: int):
        super().__init__()
        self.v = nn.Linear(hidden, 1)
        self.p = nn.Linear(hidden, act_dim)

    def forward(self, h):
        return self.v(h), torch.log_softmax(self.p(h), -1)


class MuZeroTiny(nn.Module):
    def __init__(self, obs_dim: int, act_dim: int):
        super().__init__()
        self.repr = Repr(obs_dim, CFG.hidden)
        self.dyn = Dyn(CFG.hidden, act_dim)
        self.pred = Pred(CFG.hidden, act_dim)

    def initial(self, obs):
        h = self.repr(obs)
        v, p = self.pred(h)
        return h, v, p

    def recurrent(self, h, a_onehot):
        r, h2 = self.dyn(h, a_onehot)
        v, p = self.pred(h2)
        return h2, r, v, p


# -------------------------------- MCTS ---------------------------------------
def mcts_policy(net: MuZeroTiny, obs: np.ndarray, simulations: int = 16) -> int:
    """Very small UCB‑based MCTS on top of MuZeroTiny."""
    act_dim = 4
    with torch.no_grad():
        h, v0, p0 = net.initial(torch.tensor(obs, device=CFG.device, dtype=torch.float32))
    N = np.zeros(act_dim)
    W = np.zeros(act_dim)
    P = p0.exp().cpu().numpy()
    for _ in range(simulations):
        a = np.argmax(P * (np.sqrt(N.sum() + 1e-8) / (1 + N)))
        a_one = F.one_hot(torch.tensor(a), num_classes=act_dim).float().to(CFG.device)
        h2, r, v, p = net.recurrent(h, a_one)
        q = (r + v).item()
        N[a] += 1
        W[a] += q
    best = int(np.argmax(W / (N + 1e-8)))
    return best


# =============================================================================
# 5.  MiniWorld + POET generator
# =============================================================================
@dataclass
class MiniWorld:
    size: int
    obstacles: List[Tuple[int, int]]
    goal: Tuple[int, int]
    agent: Tuple[int, int] = field(default=(0, 0))

    def reset(self):
        self.agent = (0, 0)
        return self._obs()

    def _clip(self, v):
        return max(0, min(self.size - 1, v))

    def step(self, act: int):
        dx, dy = [(0, 1), (1, 0), (0, -1), (-1, 0)][act % 4]
        nx, ny = self._clip(self.agent[0] + dx), self._clip(self.agent[1] + dy)
        if (nx, ny) in self.obstacles:
            nx, ny = self.agent
        self.agent = (nx, ny)
        done = self.agent == self.goal
        reward = 1.0 if done else -0.01
        return self._obs(), reward, done, {}

    def _obs(self):
        vec = np.zeros(self.size * self.size, dtype=np.float32)
        vec[self.agent[0] * self.size + self.agent[1]] = 1.0
        return vec


class POETGenerator:
    def __init__(self):
        self.pool: List[MiniWorld] = []

    def _mc_eval(self, env: MiniWorld, policy: Callable[[np.ndarray], int], episodes: int) -> float:
        scores = []
        for _ in range(episodes):
            obs = env.reset()
            total = 0.0
            for _ in range(env.size * env.size * 4):
                a = policy(obs)
                obs, r, done, _ = env.step(a)
                total += r
                if done:
                    break
            scores.append(total)
        return float(np.mean(scores))

    def propose(self) -> MiniWorld:
        def policy(_o: np.ndarray) -> int:
            """Random baseline policy used for Monte Carlo evaluation."""
            return random.randint(0, 3)

        attempts = 5
        env = None
        for _ in range(attempts):
            size = random.randint(CFG.min_size, CFG.max_size)
            num_obs = int(size * size * CFG.obstacle_density)
            obstacles = {(random.randint(1, size - 2), random.randint(1, size - 2)) for _ in range(num_obs)}
            env = MiniWorld(size, list(obstacles), (size - 1, size - 1))
            score = self._mc_eval(env, policy, CFG.mc_episodes)
            if CFG.mc_min <= score <= CFG.mc_max:
                break
        assert env is not None
        self.pool.append(env)
        return env


# =============================================================================
# 6.  Learner wrapper
# =============================================================================
class Learner:
    """MuZero learner that optimizes a policy for a single environment."""

    def __init__(self, env: MiniWorld):
        """Initialize the learner for ``env``."""
        self.net = MuZeroTiny(env.size**2, 4).to(CFG.device)
        self.opt = optim.Adam(self.net.parameters(), CFG.lr)
        self.buffer: List[Tuple[np.ndarray, float]] = []
        self.step_count = 0

    def act(self, obs):
        # epsilon‑greedy w/ MCTS fallback
        if random.random() < 0.1:
            return random.randint(0, 3)
        return mcts_policy(self.net, obs, CFG.mcts_simulations)

    def remember(self, obs, reward):
        self.buffer.append((obs, reward))
        if len(self.buffer) > CFG.buffer_limit:
            self.buffer.pop(0)

    def train_once(self) -> float:
        if len(self.buffer) < CFG.train_batch:
            return 0.0
        obs, rew = zip(*random.sample(self.buffer, CFG.train_batch))
        obs_t = torch.tensor(obs, device=CFG.device, dtype=torch.float32)
        rew_t = torch.tensor(rew, device=CFG.device)
        _, v, _ = self.net.initial(obs_t)
        loss = F.mse_loss(v.squeeze(), rew_t)
        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        return float(loss.item())


# =============================================================================
# 7.  Orchestrator (multi‑env batch)
# =============================================================================
class Orchestrator:
    """Coordinates multiple learners and manages environment lifecycles."""

    def __init__(self):
        """Initialize the orchestrator and subscribe to control commands."""
        self.gen = POETGenerator()
        self.envs = [self.gen.propose() for _ in range(CFG.env_batch)]
        self.learners = [Learner(e) for e in self.envs]
        self.stop = False
        A2ABus.subscribe("orch", self._on_cmd)
        LOG.info("Orchestrator online with %d envs", CFG.env_batch)

    def _on_cmd(self, msg):
        if msg.get("cmd") == "new_env":
            idx = random.randrange(len(self.envs))
            self.envs[idx] = self.gen.propose()
            self.learners[idx] = Learner(self.envs[idx])
            LOG.info("Replaced env #%d", idx)
        elif msg.get("cmd") == "stop":
            self.stop = True

    # --------------------------------------------------------------
    def loop(self):
        obs = [e.reset() for e in self.envs]
        for t in range(CFG.max_steps):
            if self.stop:
                break
            total_r = 0.0
            total_loss = 0.0
            for i, (env, learner) in enumerate(zip(self.envs, self.learners)):
                a = learner.act(obs[i])
                nxt, r, done, _ = env.step(a)
                learner.remember(obs[i], r)
                loss = learner.train_once()
                obs[i] = env.reset() if done else nxt
                total_r += r
                total_loss += loss
            if t % CFG.ui_tick == 0:
                count = max(1, len(self.envs))
                A2ABus.publish(
                    "ui",
                    {
                        "t": t,
                        "r": total_r / count,
                        "loss": total_loss / count,
                    },
                )
        LOG.info("Orchestrator loop exit at t=%d", t)


# =============================================================================
# 8. Safety agent
# =============================================================================
class BasicSafetyAgent(Agent):
    """Monitors learner metrics and issues stop commands on anomalies."""

    def __init__(self):
        """Register the agent on the bus under the ``safety`` topic."""
        super().__init__("safety")

    def handle(self, msg):
        if "loss" in msg and (np.isnan(msg["loss"]) or msg["loss"] > 1e3):
            LOG.warning("[SAFETY] triggered – halting learner")
            self.emit("orch", {"cmd": "stop"})


existing_safety = AGENTS.get("safety")
existing_handlers = A2ABus._subs.get("safety") or []
if not existing_handlers:
    if isinstance(existing_safety, Agent):
        A2ABus.subscribe("safety", existing_safety._cb)
    else:
        AGENTS["safety"] = BasicSafetyAgent()

# =============================================================================
# 9. Optional LLM planner
# =============================================================================
if os.getenv("OPENAI_API_KEY") and not os.getenv("NO_LLM"):
    try:
        import openai
        import concurrent.futures

        class LLMPlanner(Agent):
            """Asks an external LLM for high level plans and forwards them."""

            def __init__(self):
                """Register the planner under the ``llm_planner`` topic."""
                super().__init__("llm_planner")

            def _safe_call(self, prompt: str, timeout: int = 15) -> str:
                """Invoke the LLM with a timeout to avoid hanging."""

                with concurrent.futures.ThreadPoolExecutor() as ex:
                    fut = ex.submit(
                        lambda: openai.ChatCompletion.create(
                            model=os.getenv("ALPHA_ASI_LLM_MODEL", "gpt-4o-mini"),
                            messages=[{"role": "user", "content": prompt}],
                            timeout=timeout,
                        )
                    )
                    return fut.result().choices[0].message.content

            def handle(self, msg):
                if "ask_plan" in msg:
                    try:
                        plan = self._safe_call(msg["ask_plan"])
                        self.emit("planning_agent", {"llm_plan": plan})
                    except Exception as e:
                        LOG.warning("LLMPlanner error: %s", e)

        LLMPlanner()
        LOG.info("LLM planner active")
    except Exception as exc:
        LOG.warning("LLM planner unavailable: %s", exc)

# =============================================================================
# 🔟  FastAPI UI / REST / Web‑Socket endpoint
# =============================================================================
from fastapi import FastAPI, WebSocket  # noqa: E402
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
import uvicorn  # noqa: E402

app = FastAPI(title="Alpha‑ASI World Model")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orch: Optional[Orchestrator] = None
loop_thread: Optional[threading.Thread | _LoopThreadStub] = None


class _LoopThreadStub:
    """Minimal thread-like stub used when threads cannot start under pytest."""

    def __init__(self) -> None:
        self._alive = False

    def start(self) -> None:
        self._alive = True

    def join(self, timeout: float | None = None) -> None:
        del timeout
        self._alive = False

    def is_alive(self) -> bool:
        return self._alive


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    global orch, loop_thread
    orch = Orchestrator()
    try:
        loop_thread = threading.Thread(target=orch.loop, daemon=True)
        loop_thread.start()
    except RuntimeError as exc:
        if os.getenv("PYTEST_CURRENT_TEST"):
            LOG.warning("Falling back to stubbed loop thread in tests: %s", exc)
            loop_thread = _LoopThreadStub()
            loop_thread.start()
        else:
            raise
    try:
        yield
    finally:
        if orch:
            orch.stop = True
        if loop_thread:
            loop_thread.join(timeout=1)
        for agent in list(AGENTS.values()):
            if hasattr(agent, "close"):
                agent.close()
        A2ABus._subs = {}
        orch = None
        loop_thread = None


app.router.lifespan_context = lifespan


@app.get("/agents")
async def list_agents():
    agent_names = set(AGENTS.keys())
    agent_names.update(agent.__class__.__name__ for agent in AGENTS.values())
    agent_names.update(path.rsplit(".", 1)[-1] for path in REQUIRED)
    return list(agent_names)


@app.post("/command")
async def send_cmd(cmd: Dict[str, str]):
    A2ABus.publish("orch", cmd)
    return {"ok": True}


@app.websocket("/ws")
async def ws_endpoint(sock: WebSocket):
    await sock.accept()
    q: List[dict] = []
    A2ABus.subscribe("ui", lambda m: q.append(m))
    try:
        while True:
            if q:
                await sock.send_text(json.dumps(q.pop(0)))
            await asyncio.sleep(0.1)
    except Exception:
        pass


# =============================================================================
# 11.  Dev‑ops helpers (Dockerfile / Helm / Notebook emitters)
# =============================================================================
DOCKERFILE = """FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic torch numpy nbformat PyYAML
EXPOSE 7860
CMD [\"python\", \"-m\", \"alpha_asi_world_model_demo\", \"--demo\", \"--host\", \"0.0.0.0\", \"--port\", \"7860\"]
"""

HELM_VALUES = """replicaCount: 1
image:
  repository: alpha_asi_world_model
  tag: latest
service:
  port: 80
"""


def emit_docker(fp: Path = Path("Dockerfile")):
    fp.write_text(DOCKERFILE)
    print("Dockerfile →", fp)


def emit_helm(dir_: Path = Path("helm_chart")):
    dir_.mkdir(exist_ok=True)
    (dir_ / "values.yaml").write_text(HELM_VALUES)
    (dir_ / "Chart.yaml").write_text("apiVersion: v2\nname: alpha-asi-demo\nversion: 0.1.0\n")
    print("Helm chart →", dir_)


def emit_notebook(fp: Path = Path("alpha_asi_world_model_demo.ipynb")):
    import nbformat as nbf

    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# α‑ASI demo – quickstart"),
        nbf.v4.new_code_cell("!python -m alpha_asi_world_model_demo --demo &"),
    ]
    nbf.write(nb, fp)
    print("Notebook →", fp)


# =============================================================================
# 12.  CLI
# =============================================================================
def _main():
    p = argparse.ArgumentParser(prog="alpha_asi_world_model_demo")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--emit-docker", action="store_true")
    p.add_argument("--emit-helm", action="store_true")
    p.add_argument("--emit-notebook", action="store_true")
    p.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable the optional LLM planner regardless of OPENAI_API_KEY",
    )
    p.add_argument("--host", default=CFG.host)
    p.add_argument("--port", type=int, default=CFG.port)
    args = p.parse_args()
    if args.emit_docker:
        emit_docker()
    elif args.emit_helm:
        emit_helm()
    elif args.emit_notebook:
        emit_notebook()
    elif args.demo:
        if args.no_llm:
            os.environ["NO_LLM"] = "1"
        uvicorn.run(
            "alpha_asi_world_model_demo:app",
            host=args.host,
            port=args.port,
            log_level="info",
        )
    else:
        p.print_help()


if __name__ == "__main__":
    _main()
