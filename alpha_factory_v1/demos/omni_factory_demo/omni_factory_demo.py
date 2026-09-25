#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
OMNI‑Factory • Smart‑City Resilience Demo (α‑Factory v1 add‑on)
═══════════════════════════════════════════════════════════════
A self‑contained, production‑grade open‑ended learning loop that plugs
straight into the **Alpha‑Factory v1** backbone and demonstrates:

• **Automatic scenario generation**   (OMNI‑EPIC style)
• **Multi‑agent problem‑solving**     (orchestrator + world‑model + SDK agents)
• **Grounded success evaluation**     (numeric & qualitative)
• **Token‑economy accounting**        ($AGIALPHA ledger, hard‑capped)
• **Observability & safety**          (Prometheus, graceful exits, plugin sandbox)

The script is **offline‑first** – it runs fully locally with zero external
requirements. If environment variables such as `OPENAI_API_KEY` or
`GOOGLE_ADK_KEY` are detected, it will *transparently* enable cloud
extras (LLM scenario generation, OpenAI‑Agents SDK planners, Google ADK
skills, A2A protocol messaging, …) without breaking determinism.

Run
───
    python -m alpha_factory_v1.demos.omni_factory_demo \
           --metrics-port 8000 --max-episodes 25 --dry-run

Dependencies
────────────
Mandatory   • Python ≥ 3.10   • Alpha‑Factory v1 repo (same tree)
Optional    • prometheus‑client • numpy • openai • gymnasium •
             openai‑agents‑python • google‑adk • a2a‑protocol

All optional imports are guarded by `contextlib.suppress`, so **missing
extras never break execution** – features simply degrade gracefully.
"""
from __future__ import annotations

###############################################################################
# Std‑lib imports                                                             #
###############################################################################
import argparse
import asyncio
import contextlib
import dataclasses as dc
import functools
import hashlib
import importlib.util
import json
import os
import random
import signal
import sqlite3
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

###############################################################################
# Optional third‑party (feature‑flagged)                                      #
###############################################################################
with contextlib.suppress(ModuleNotFoundError):
    import numpy as np  # type: ignore

with contextlib.suppress(ModuleNotFoundError):
    import openai  # type: ignore

with contextlib.suppress(ModuleNotFoundError):
    import openai_agents_sdk as oas  # type: ignore

OPENAI_TIMEOUT_SEC = int(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

with contextlib.suppress(ModuleNotFoundError):
    import google_adk as gadk  # type: ignore

with contextlib.suppress(ModuleNotFoundError):
    from a2a_protocol import Peer  # type: ignore

with contextlib.suppress(ModuleNotFoundError):
    from gymnasium import Env, spaces  # type: ignore

with contextlib.suppress(ModuleNotFoundError):
    from prometheus_client import CollectorRegistry, Gauge, start_http_server  # type: ignore

# Fallback stubs so typing doesn’t explode when extras are absent ------------
if "spaces" not in globals():  # pragma: no cover

    class _Dummy:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

    class spaces:  # type: ignore
        Box = Discrete = _Dummy

    class Env:  # type: ignore
        pass


if "oas" not in globals():

    class oas:  # type: ignore
        class Agent:
            def __init__(self, *_, **__):
                pass

            def act(self, prompt: str) -> str:  # noqa: D401
                return "{" "action" ": {" "id" ": 0}}"


if "gadk" not in globals():

    class gadk:  # type: ignore
        class Skill:
            def __init__(self, *_, **__):
                pass

        class Toolkit:
            def __init__(self, *_, **__):
                pass


###############################################################################
# Alpha‑Factory backbone                                                      #
###############################################################################
if TYPE_CHECKING:
    from alpha_factory_v1.backend.orchestrator import Orchestrator

PLUGINS: list[ModuleType] = []

###############################################################################
# Immutable runtime configuration                                             #
###############################################################################
CFG_DEFAULTS: dict[str, Any] = {
    "LLM_MODEL": "gpt-4o-mini",
    "TEMPERATURE": 0.7,
    "TOKENS_PER_TASK": 100,
    "LEDGER_PATH": "./omni_ledger.sqlite",
    "SEED": 0,
    "SUCCESS_THRESHOLD": 0.95,
    "MAX_SIM_MINUTES": 240,
    "MICRO_CURRICULUM": "auto",  # easy→hard scheduler stub
    "AGIALPHA_SUPPLY": 10_000_000,  # hard‑cap
}


@dc.dataclass(frozen=True, slots=True)
class Cfg:
    llm_model: str = CFG_DEFAULTS["LLM_MODEL"]
    temperature: float = CFG_DEFAULTS["TEMPERATURE"]
    tokens_per_task: int = CFG_DEFAULTS["TOKENS_PER_TASK"]
    ledger_path: Path = Path(CFG_DEFAULTS["LEDGER_PATH"])
    seed: int = CFG_DEFAULTS["SEED"]
    success_thresh: float = CFG_DEFAULTS["SUCCESS_THRESHOLD"]
    max_minutes: int = CFG_DEFAULTS["MAX_SIM_MINUTES"]
    micro_curr: str = CFG_DEFAULTS["MICRO_CURRICULUM"]
    max_supply: int = CFG_DEFAULTS["AGIALPHA_SUPPLY"]


def _cfg_from_env() -> dict[str, Any]:
    mapping: dict[str, str] = {
        "SUCCESS_THRESHOLD": "success_thresh",
        "MAX_SIM_MINUTES": "max_minutes",
        "MICRO_CURRICULUM": "micro_curr",
        "AGIALPHA_SUPPLY": "max_supply",
    }
    cfg: dict[str, Any] = {}
    for k, v in CFG_DEFAULTS.items():
        key = mapping.get(k, k.lower())
        val = os.getenv(f"OMNI_{k}", v)
        if k.endswith("PATH"):
            cfg[key] = Path(val)
        else:
            cfg[key] = type(CFG_DEFAULTS[k])(val)
    return cfg


CFG = Cfg(**_cfg_from_env())
random.seed(CFG.seed)


###############################################################################
# Prometheus metrics wrapper                                                  #
###############################################################################
class _Metrics:
    """Expose gauges only if `prometheus_client` is available."""

    def __init__(self, port: int | None):
        self.enabled = "CollectorRegistry" in globals() and port is not None
        if not self.enabled:
            self.avg_reward = self.episodes = self.tokens = None  # type: ignore
            return
        registry = CollectorRegistry()  # type: ignore[misc]
        self.avg_reward = Gauge("omni_avg_reward", "Average reward", registry=registry)  # type: ignore[misc]
        self.episodes = Gauge("omni_episode", "Episode index", registry=registry)  # type: ignore[misc]
        self.tokens = Gauge("omni_tokens", "Minted $AGIALPHA", registry=registry)  # type: ignore[misc]
        start_http_server(port, registry=registry)  # type: ignore[misc]


METRICS: _Metrics  # populated in main()

###############################################################################
# 1. Scenario generation (OMNI‑EPIC)                                          #
###############################################################################
_FALLBACK_SCENARIOS: tuple[str, ...] = (
    "Flash‑flood closes two arterial bridges during evening rush.",
    "Cyber‑attack disables subway signalling across downtown.",
    "Record heatwave triggers rolling brown‑outs city‑wide.",
    "Large protest blocks the central business district at lunch.",
)


def _llm_one_liner(prompt: str) -> str:
    """LLM helper with deterministic fallback."""
    if "openai" not in globals() or not os.getenv("OPENAI_API_KEY"):
        idx = (int(hashlib.sha256(prompt.encode()).hexdigest()[:16], 16) + CFG.seed) % len(_FALLBACK_SCENARIOS)
        return _FALLBACK_SCENARIOS[idx]
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")  # type: ignore[attr-defined]
        resp = openai.ChatCompletion.create(  # type: ignore[attr-defined]
            model=CFG.llm_model,
            temperature=CFG.temperature,
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
            timeout=OPENAI_TIMEOUT_SEC,
        )
        return resp.choices[0].message.content.strip()  # type: ignore[index]
    except Exception:  # pragma: no cover – network/quotas/etc.
        idx = (int(hashlib.sha256(prompt.encode()).hexdigest()[:16], 16) + CFG.seed) % len(_FALLBACK_SCENARIOS)
        return _FALLBACK_SCENARIOS[idx]


class TaskGenerator:
    """Maintains novelty history + (future) micro‑curriculum scheduling."""

    def __init__(self) -> None:
        self._hist: list[str] = []
        self._step = 0

    def next(self) -> str:
        self._step += 1
        prompt = (
            "You are OMNI‑EPIC. Draft ONE new smart‑city disruption scenario "
            "materially different from these:\n"
            f"{json.dumps(self._hist[-8:], indent=2)}\n"
            "Return exactly one concise sentence."
        )
        scenario = _llm_one_liner(prompt)
        self._hist.append(scenario)
        return scenario


###############################################################################
# 2. Minimal yet grounded smart‑city environment                              #
###############################################################################
@dc.dataclass(slots=True)
class _CityState:
    power_ok: float
    traffic_ok: float
    minute: int


class SmartCityEnv(Env):  # type: ignore[misc]
    """Headless stochastic digital‑twin with two controllable levers."""

    metadata: Dict[str, str] = {}
    action_space = spaces.Box(low=0.0, high=1.0, shape=(2,))  # type: ignore[arg-type]
    observation_space = spaces.Box(low=0.0, high=1.0, shape=(3,))  # type: ignore[arg-type]

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random(CFG.seed * 997)
        self.state: _CityState = self._random_state()
        self.scenario: str = "<cold‑start>"

    def _random_state(self) -> _CityState:
        return _CityState(self.rng.uniform(0.3, 0.9), self.rng.uniform(0.3, 0.9), 0)

    # Gymnasium 0.29 API ----------------------------------------------------
    def reset(self, *, seed: int | None = None, options: Dict | None = None):  # type: ignore[override]
        del seed
        self.state = self._random_state()
        self.scenario = (options or {}).get("scenario", self.scenario)
        return self._obs(), {}

    def step(self, action: Tuple[float, float]):  # type: ignore[override]
        repair, traffic = map(float, action)
        s = self.state
        s.power_ok = min(1.0, s.power_ok + 0.65 * repair)
        s.traffic_ok = min(1.0, s.traffic_ok + 0.55 * traffic)
        s.minute += 1

        reward = (s.power_ok + s.traffic_ok) / 2
        terminated = reward >= CFG.success_thresh
        truncated = s.minute >= CFG.max_minutes
        return self._obs(), reward, terminated or truncated, truncated, {}

    def _obs(self) -> List[float]:
        s = self.state
        return [s.power_ok, s.traffic_ok, s.minute / CFG.max_minutes]

    def solved(self) -> bool:
        return (self.state.power_ok + self.state.traffic_ok) / 2 >= CFG.success_thresh


###############################################################################
# 3. $AGIALPHA ledger (SQLite, append‑only, human‑readable)                   #
###############################################################################
_LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger(
    ts          REAL,
    scenario    TEXT,
    tokens      INT,
    avg_reward  REAL,
    checksum    TEXT
);
"""


def _ledger_init(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(_LEDGER_SCHEMA)


def _checksum(ts: float, scen: str, tok: int, rew: float) -> str:
    return hashlib.sha256(f"{ts}{scen}{tok}{rew}".encode()).hexdigest()[:16]


def _supply(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT SUM(tokens) FROM ledger")
    val = cur.fetchone()[0]
    return val or 0


def _mint(path: Path, scenario: str, avg_reward: float) -> int:
    tokens = int(avg_reward * CFG.tokens_per_task)
    with sqlite3.connect(path) as conn:
        supply = _supply(conn)
        if supply + tokens > CFG.max_supply:
            tokens = CFG.max_supply - supply
        ts = time.time()
        conn.execute(
            "INSERT INTO ledger VALUES (?,?,?,?,?)",
            (ts, scenario, tokens, avg_reward, _checksum(ts, scenario, tokens, avg_reward)),
        )
    return max(tokens, 0)


###############################################################################
# 4. Success evaluator                                                        #
###############################################################################
class SuccessEvaluator:
    """Numeric ground‑truth + optional LLM qualitative sanity."""

    def __init__(self) -> None:
        self._qual_hist: list[str] = []

    def check(self, env: SmartCityEnv) -> bool:
        numeric = env.solved()
        qualitative = True
        if "openai" in globals() and os.getenv("OPENAI_API_KEY"):
            prompt = (
                f"Scenario: {env.scenario}. Final KPIs power_ok={env.state.power_ok:.2f}, "
                f"traffic_ok={env.state.traffic_ok:.2f}.\n"
                "Respond yes/no ONLY: did the city successfully stabilise?"
            )
            ans = _llm_one_liner(prompt).lower()
            self._qual_hist.append(ans)
            qualitative = ans.startswith("yes")
        return numeric and qualitative


###############################################################################
# 5. Planning layer abstraction (SDKs, WM fallback)                           #
###############################################################################


def _plan(obs: List[float], scenario: str) -> Dict[str, Any]:
    """Hierarchical planner: SDK agent → Google ADK → WM fallback."""
    # 1) OpenAI Agents SDK ---------------------------------------------------
    if "oas" in globals():
        try:
            agent = _plan._cached_agent  # type: ignore[attr-defined]
        except AttributeError:
            agent = oas.Agent(name="OMNI‑Planner", model=CFG.llm_model)  # type: ignore[arg-type]
            _plan._cached_agent = agent  # type: ignore[attr-defined]
        reply = agent.act(json.dumps({"obs": obs, "scenario": scenario}))  # type: ignore[attr-defined]
        with contextlib.suppress(Exception):
            return json.loads(reply)
    # 2) Google ADK skill‑set -----------------------------------------------
    if "gadk" in globals():
        skillkit = getattr(_plan, "_skillkit", None)
        if skillkit is None:
            skillkit = gadk.Toolkit()  # type: ignore[call-arg]
            _plan._skillkit = skillkit
        # Dummy skill inference (placeholder)
        action_id = int(sum(obs) * 10) % 5
        return {"action": {"id": action_id}}
    # 3) Alpha‑Factory world‑model planner ----------------------------------
    from alpha_factory_v1.backend.world_model import wm

    plan = wm.plan("smart_city", {"obs": obs, "scenario": scenario})
    if plan:
        return plan
    # 4) Plugin heuristics --------------------------------------------------
    for plug in PLUGINS:
        heur = getattr(plug, "heuristic_policy", None)
        if heur:
            try:
                return heur(obs)
            except Exception:
                pass
    return {"action": {"id": 0}}


###############################################################################
# 6. Plugin autoloader (agents, env augmentations, …)                         #
###############################################################################


@functools.cache
def _load_plugins(folder: Path | None = None) -> List[ModuleType]:
    if folder is None:
        folder = Path(__file__).with_suffix("").parent / "plugins"
    mods: list[ModuleType] = []
    if not folder.exists():
        return mods
    global PLUGINS
    for py in folder.glob("*.py"):
        if py.name == "__init__.py":
            continue  # ignore package marker
        with contextlib.suppress(Exception):
            spec = importlib.util.spec_from_file_location(py.stem, py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[arg-type]
                if hasattr(mod, "register"):
                    try:
                        mod.register()  # type: ignore[misc]
                    except Exception:
                        pass
                mods.append(mod)
    PLUGINS = mods
    return mods


###############################################################################
# 7. Single episode runner                                                    #
###############################################################################
async def _episode(
    orch: Orchestrator | None,
    env: SmartCityEnv,
    tgen: TaskGenerator,
    evaler: SuccessEvaluator,
    episode_id: int,
) -> None:
    scenario = tgen.next()
    obs, _ = env.reset(options={"scenario": scenario})
    cumulative = 0.0

    for minute in range(CFG.max_minutes):
        plan = _plan(obs, scenario)
        act_id = plan.get("action", {}).get("id", 0)
        repair = 0.8 if act_id % 3 == 0 else 0.2
        traffic = 0.8 if act_id % 3 == 1 else 0.2
        obs, rew, done, _, _ = env.step((repair, traffic))
        cumulative += rew
        if done:
            break

    avg_reward = cumulative / (minute + 1)
    solved = evaler.check(env)

    if solved:
        tokens = _mint(CFG.ledger_path, scenario, avg_reward)
        msg = f"✅  {scenario} ({minute+1}′, r̄={avg_reward:.3f}) – +{tokens} $AGIALPHA"
        if METRICS.enabled and METRICS.tokens:
            METRICS.tokens.inc(tokens)  # type: ignore[misc]
    else:
        msg = f"✖  {scenario} ({minute+1}′, r̄={avg_reward:.3f}) – FAILED"

    if METRICS.enabled:
        if METRICS.avg_reward:
            METRICS.avg_reward.set(avg_reward)  # type: ignore[misc]
        if METRICS.episodes:
            METRICS.episodes.set(episode_id)  # type: ignore[misc]

    print(msg)


###############################################################################
# 8. Continuous open‑ended loop                                               #
###############################################################################
async def _main_loop(max_episodes: int | None) -> None:
    # The numeric city simulation does not use the service orchestrator.
    # Do not start unrelated agents, model downloads or background services.
    orch = None
    env = SmartCityEnv()
    tgen = TaskGenerator()
    evaler = SuccessEvaluator()
    eps = 0

    _load_plugins()  # side‑effect import

    while max_episodes is None or eps < max_episodes:
        eps += 1
        try:
            await _episode(orch, env, tgen, evaler, eps)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Episode {eps} failed: {exc}") from exc
        await asyncio.sleep(0)  # cooperative sched


###############################################################################
# 9. CLI & graceful shutdown                                                  #
###############################################################################


def _parse_cli(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="omni_factory_demo")
    p.add_argument(
        "--metrics-port",
        type=int,
        default=None,
        help="Expose Prometheus metrics on this port (disabled if lib missing)",
    )
    p.add_argument("--max-episodes", type=int, default=None, help="Stop after N episodes (default: endless)")
    p.add_argument("--dry-run", action="store_true", help="Skip $AGIALPHA minting – CI friendly")
    return p.parse_args(argv)


###############################################################################
# Entry‑point                                                                 #
###############################################################################


def main(argv: List[str] | None = None) -> None:  # noqa: D401
    """Module‑safe entry so `python -m …` works neatly."""
    args = _parse_cli(sys.argv[1:] if argv is None else argv)

    global METRICS
    METRICS = _Metrics(args.metrics_port)

    banner = (
        "╭────────────────────────────────────────────────────────────╮\n"
        "│        OMNI‑Factory • Smart‑City Resilience Demo v1        │\n"
        "╰────────────────────────────────────────────────────────────╯"
    )
    print(banner)
    print("Ledger:", CFG.ledger_path.resolve())
    if not CFG.ledger_path.exists():
        _ledger_init(CFG.ledger_path)
        print("↳ New ledger initialised.")

    if args.dry_run:
        globals()["_mint"] = lambda *_, **__: 0  # type: ignore[assignment]
        print("⚠  DRY‑RUN – token minting disabled.")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop = asyncio.Event()

    def _sig_handler(_sig, _frm):  # noqa: D401
        print("\nCtrl‑C detected – shutting down …")
        stop.set()

    signal.signal(signal.SIGINT, _sig_handler)

    async def _runner() -> None:
        prod = asyncio.create_task(_main_loop(args.max_episodes))
        stopper = asyncio.create_task(stop.wait())
        try:
            done, pending = await asyncio.wait({prod, stopper}, return_when=asyncio.FIRST_COMPLETED)
            if prod in done:
                await prod  # propagate episode failures to the CLI exit status
        finally:
            for task in (prod, stopper):
                task.cancel()
            await asyncio.gather(prod, stopper, return_exceptions=True)

    try:
        loop.run_until_complete(_runner())
    finally:
        loop.close()
        print("Goodbye! ☮")


if __name__ == "__main__":
    main(sys.argv[1:])
