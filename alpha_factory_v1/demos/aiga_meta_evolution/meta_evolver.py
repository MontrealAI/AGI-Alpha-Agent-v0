# SPDX-License-Identifier: Apache-2.0
# alpha_factory_v1/demos/aiga_meta_evolution/meta_evolver.py
# © 2025 MONTREAL.AI  Apache-2.0 License
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

MetaEvolver v3.0 (2025‑04‑23)
=================================
✦ **Mission**  Self‑contained, SOC‑2‑aligned neuro‑evolution engine that scales
  from a laptop to a Kubernetes Ray cluster with zero code changes.
✦ **Pillar coverage**  Architecture, plasticity rule, and environment co‑evolve.
✦ **Observability**  Prometheus gauges, structured logs, population SHA.
✦ **Fail‑safe parallelism**  Ray ➜ multiprocessing ➜ ThreadPool cascade.
✦ **Audit hooks**  JSON checkpoints (atomic), population hash, deterministic RNG.
✦ **Extensibility**  Plug‑in novelty metrics, LLM commentary, A2A broadcast.
"""
from __future__ import annotations

import copy
import dataclasses as dc
import hashlib
import inspect
import json
import logging
import math
import os
import pathlib
import random
import contextlib
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable, List, Tuple

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback
    np = None

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    _TORCH = True
except (ModuleNotFoundError, OSError):  # pragma: no cover - CPU-only stub
    import types

    torch = types.SimpleNamespace(
        Tensor=float,
        device=lambda *_: "cpu",
        cuda=lambda: False,
        zeros_like=lambda *_: 0,
        bmm=lambda *_: 0,
        multinomial=lambda *_: 0,
        no_grad=contextlib.nullcontext,
    )

    class _DummyNN:
        Module = object

        def Linear(*_, **__):
            return None

        def Sequential(*_, **__):
            return []

    nn = _DummyNN()

    class _F:
        relu = staticmethod(lambda x: x)
        gelu = staticmethod(lambda x: x)

    F = _F
    _TORCH = False

# optional deps ------------------------------------------------------------
try:
    import ray

    _HAS_RAY = True
except ImportError:
    _HAS_RAY = False
try:
    from prometheus_client import Gauge, metrics

    _registry = metrics.REGISTRY

    def _find_metric(name: str):
        existing = _registry._names_to_collectors.get(name)  # type: ignore[attr-defined]
        if existing is not None:
            return existing
        for collector, names in _registry._collector_to_names.items():  # type: ignore[attr-defined]
            if name in names:
                return collector
        return None

    def _reuse_metric(name: str, factory):
        existing = _find_metric(name)
        if existing is not None:
            return existing
        try:
            return factory(name, "Average fitness per generation", registry=_registry)
        except ValueError:
            existing = _find_metric(name)
            if existing is not None:
                return existing
            raise

    _fitness_gauge = _reuse_metric("aiga_avg_fitness", Gauge)
except ImportError:
    _fitness_gauge = None
try:
    from a2a import A2ASocket

    _A2A = A2ASocket(
        host=os.getenv("A2A_HOST", "localhost"),
        port=int(os.getenv("A2A_PORT", "5555")),
        app_id="meta_evolver",
    )
except Exception:
    _A2A = None

# logging ------------------------------------------------------------------
LOG = logging.getLogger("MetaEvolver")
if not LOG.hasHandlers():
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)sZ %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S"))
    LOG.addHandler(h)
    LOG.setLevel(os.getenv("LOGLEVEL", "INFO").upper())

# global config ------------------------------------------------------------
if _TORCH:
    Device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _ACT: dict[str, Callable[[torch.Tensor], torch.Tensor]] = {
        "relu": F.relu,
        "tanh": torch.tanh,
        "sigmoid": torch.sigmoid,
        "gelu": F.gelu,
    }
else:  # pragma: no cover - minimal placeholders
    Device = "cpu"
    _ACT = {"relu": lambda x: x, "tanh": lambda x: x, "sigmoid": lambda x: x, "gelu": lambda x: x}
CHKPT_DIR = pathlib.Path(os.getenv("CHECKPOINT_DIR", "./checkpoints"))
CHKPT_DIR.mkdir(parents=True, exist_ok=True)


DEFAULT_SEED = int.from_bytes(b"A1GA", "big")


# ────────────────────────────── Genome ────────────────────────────────────
@dc.dataclass(slots=True)
class Genome:
    layers: Tuple[int, ...] = (32,)
    activation: str = "relu"
    hebbian: bool = False
    novelty_weight: float = 0.0  # 0–1

    # evo‑ops -------------------------------------------------------------
    def mutate(self, rng: random.Random | None = None) -> "Genome":
        """Mutate using the supplied stream without consuming the global RNG."""
        rng = rng if rng is not None else random.Random()
        g = copy.deepcopy(self)
        if rng.random() < 0.4:
            idx = rng.randrange(len(g.layers))
            delta = rng.randint(-8, 8)
            new_size = max(4, min(128, g.layers[idx] + delta))
            layers = list(g.layers)
            layers[idx] = new_size
            if rng.random() < 0.2 and len(layers) < 4:
                layers.insert(idx, rng.choice([16, 32, 64]))
            g.layers = tuple(layers)
        if rng.random() < 0.2:
            g.activation = rng.choice(list(_ACT))
        if rng.random() < 0.1:
            g.hebbian = not g.hebbian
        if rng.random() < 0.15:
            g.novelty_weight = round(min(1.0, max(0.0, g.novelty_weight + rng.uniform(-0.15, 0.15))), 2)
        return g

    # serialisation -------------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(dc.asdict(self), separators=(",", ":"))

    @staticmethod
    def from_json(js: str | dict) -> "Genome":
        data = json.loads(js) if isinstance(js, str) else dict(js)
        if "layers" in data:
            data["layers"] = tuple(data["layers"])
        return Genome(**data)

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.to_json().encode()).hexdigest()[:12]


# ───────────────────────── network wrapper ────────────────────────────────
if _TORCH:

    class _EvoLinear(nn.Linear):
        def reset_parameters(self) -> None:
            # EvoNet initializes every parameter with its own CPU generator.
            # Skipping Linear's default initializer avoids global RNG draws,
            # including races with unrelated Torch users in other threads.
            pass


class EvoNet(nn.Module):
    def __init__(self, obs_dim: int, act_dim: int, g: Genome, *, seed: int | None = None):
        super().__init__()
        if not _TORCH:
            raise RuntimeError("EvoNet requires real PyTorch")
        self._rng = torch.Generator(device="cpu")
        if seed is None:
            self._rng.seed()
        else:
            self._rng.manual_seed(seed)
        last, modules = obs_dim, []
        for h in g.layers:
            modules.append(_EvoLinear(last, h, device="cpu"))
            last = h
        modules.append(_EvoLinear(last, act_dim, device="cpu"))
        self.model = nn.ModuleList(modules)
        self.genome = g
        if g.hebbian:
            for idx, layer in enumerate(self.model[:-1]):
                self.register_buffer(f"fast_{idx}", torch.zeros_like(layer.weight))
        self._init()

    def _init(self):
        for m in self.model:
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, generator=self._rng)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor):
        act_fn = _ACT[self.genome.activation]
        h = x
        for idx, layer in enumerate(self.model):
            previous = h
            h = act_fn(layer(h))
            if self.genome.hebbian and idx < len(self.model) - 1:
                with torch.no_grad():
                    before = previous.reshape(-1, previous.shape[-1])
                    after = h.reshape(-1, h.shape[-1])
                    dw = 0.03 * after.T @ before / before.shape[0]
                    fast = getattr(self, f"fast_{idx}")
                    fast.copy_((fast + dw).clamp(-0.02, 0.02))
                    layer.weight.add_(fast)
        return h


# ────────────────────────── MetaEvolver core ──────────────────────────────
class MetaEvolver:
    def __init__(
        self,
        env_cls: Callable,
        pop_size: int = 32,
        elitism: int = 2,
        parallel: bool = True,
        checkpoint_dir: pathlib.Path = CHKPT_DIR,
        llm: Callable[[str], str] | None = None,
        *,
        start_socket: bool = False,
        seed: int = DEFAULT_SEED,
        device: str | None = None,
    ) -> None:
        """Create a meta-evolution engine.

        Args:
            env_cls: Environment class to instantiate per evaluation.
            pop_size: Number of genomes per generation.
            elitism: How many top genomes carry over unchanged.
            parallel: Whether to evaluate genomes in parallel.
            checkpoint_dir: Directory for checkpoints.
            llm: Optional LLM callback for commentary.
            start_socket: Start the optional A2A socket.
            seed: Owned evolution and evaluation seed; checkpointed for resume.
            device: Torch device override. CPU is the reproducibility qualification target.
        """
        if type(seed) is not int:
            raise ValueError("seed must be an integer")
        if type(pop_size) is not int or type(elitism) is not int or pop_size < 1 or not 0 <= elitism <= pop_size:
            raise ValueError("pop_size must be positive and elitism must be within the population")
        self.env_cls, self.pop_size, self.elitism = env_cls, pop_size, elitism
        self.device = device if device is not None else Device
        self.parallel = parallel
        self.ckpt_dir = pathlib.Path(checkpoint_dir)
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)
        self.llm = llm
        self.seed = seed
        self.rng = random.Random(seed)
        self.gen = 0
        self.history: List[Tuple[int, float]] = []
        self._archive: List[np.ndarray] = []
        self._best_fitness = -math.inf
        self.best_genome: Genome | None = None
        self._last_scores: List[float] = []
        self._init_population()
        if self.parallel and _HAS_RAY and not ray.is_initialized():
            ray.init(ignore_reinit_error=True, _temp_dir=str(self.ckpt_dir / "ray"))
        if start_socket:
            self.start_socket()
        LOG.info("Evolver ready ▶ pop=%d device=%s", self.pop_size, self.device)

    # population -----------------------------------------------------------
    def _init_population(self):
        seed = Genome()
        self.population = [seed.mutate(self.rng) for _ in range(self.pop_size)]
        self.best_genome = self.population[0]

    # A2A -----------------------------------------------------------------
    @staticmethod
    def start_socket() -> None:
        """Start the optional A2A socket if available."""
        if _A2A:
            try:
                _A2A.start()
            except Exception:  # pragma: no cover - best effort
                LOG.warning("Failed to start A2A socket", exc_info=True)

    # evaluation util ------------------------------------------------------
    def _evaluation_seed(self, g: Genome, index: int = 0) -> int:
        """Derive work-item seeds before dispatch, independent of scheduling."""
        payload = f"{self.seed}:{self.gen}:{index}:{g.sha}".encode("ascii")
        return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**63)

    def _evaluation_seeds(self) -> List[int]:
        return [self._evaluation_seed(g, i) for i, g in enumerate(self.population)]

    def _simulate(self, g: Genome, seed: int | None = None) -> Tuple[float, np.ndarray]:
        seed = self._evaluation_seed(g) if seed is None else seed
        return self._simulate_worker(self.env_cls, self._archive, g.to_json(), seed, self.device)

    @staticmethod
    def _accepts_seed(fn: Callable) -> bool:
        try:
            parameters = inspect.signature(fn).parameters.values()
        except (TypeError, ValueError):
            return False
        return any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            or (p.name == "seed" and p.kind != inspect.Parameter.POSITIONAL_ONLY)
            for p in parameters
        )

    @staticmethod
    def _simulate_worker(env_cls, archive, js: str, seed: int = DEFAULT_SEED, device=None):
        if not _TORCH or np is None:
            raise RuntimeError("Evolution requires real NumPy and PyTorch; no training was performed")
        g = Genome.from_json(js)
        constructor_seeded = MetaEvolver._accepts_seed(env_cls)
        env = env_cls(seed=seed) if constructor_seeded else env_cls()
        try:
            obs_dim, act_dim = env.observation_space.shape[0], env.action_space.n
            device = Device if device is None else device
            net = EvoNet(obs_dim, act_dim, g, seed=seed).to(device)
            if MetaEvolver._accepts_seed(env.reset):
                obs, _ = env.reset(seed=seed)
            else:
                if not constructor_seeded:
                    LOG.warning("Environment has no seed interface; reproducibility is not guaranteed")
                obs, _ = env.reset()
            total, bc = 0.0, []
            for _ in range(env.genome.max_steps):
                with torch.no_grad():
                    a = net(torch.tensor(obs, dtype=torch.float32, device=device)).argmax().item()
                obs, rew, done, truncated, _ = env.step(a)
                total += rew
                bc.append(obs)
                if done or truncated:
                    break
            bc_vec = np.mean(bc, axis=0)
            if g.novelty_weight and archive:
                novelty = float(np.mean([np.linalg.norm(bc_vec - a) for a in archive]))
                total += g.novelty_weight * novelty
            return total, bc_vec
        finally:
            close = getattr(env, "close", None)
            if close is not None:
                close()

    # -------- parallel dispatch ------------------------------------------
    def _evaluate_population(self) -> List[float]:
        if self.parallel and _HAS_RAY:
            return self._ray_eval()
        return self._mp_eval() if self.parallel else self._thread_eval()

    def _ray_eval(self):
        env_cls = self.env_cls
        archive = self._archive.copy()
        device = self.device

        @ray.remote
        def _worker(js: str, seed: int):
            return MetaEvolver._simulate_worker(env_cls, archive, js, seed, device)

        futures = [_worker.remote(g.to_json(), seed) for g, seed in zip(self.population, self._evaluation_seeds())]
        results = ray.get(futures)
        return self._post_eval(results)

    def _mp_eval(self):
        with ProcessPoolExecutor(max_workers=min(self.pop_size, os.cpu_count() or 1)) as pool:
            results = list(pool.map(self._simulate, self.population, self._evaluation_seeds()))
        return self._post_eval(results)

    def _thread_eval(self):
        with ThreadPoolExecutor(max_workers=min(self.pop_size, os.cpu_count() or 1)) as pool:
            results = list(pool.map(self._simulate, self.population, self._evaluation_seeds()))
        return self._post_eval(results)

    def _post_eval(self, results):
        scores, bcs = zip(*results)
        self._archive.extend(bcs[-64:])
        return list(scores)

    # tournament -----------------------------------------------------------
    def _select(self, scores, k=3):
        idx = max(self.rng.sample(range(self.pop_size), min(k, self.pop_size)), key=lambda i: scores[i])
        return self.population[idx]

    # evolutionary loop ----------------------------------------------------
    def run_generations(self, n: int = 5):
        """Evolve the population for ``n`` generations."""
        for _ in range(n):
            scores = self._evaluate_population()
            self._last_scores = scores
            best_idx = int(np.argmax(scores))
            if scores[best_idx] > self._best_fitness:
                self._best_fitness = scores[best_idx]
                self.best_genome = self.population[best_idx]
            avg = float(np.mean(scores))
            self.history.append((self.gen, avg))
            if _fitness_gauge:
                _fitness_gauge.set(avg)
            LOG.info("gen=%d avg=%.3f best=%.2f", self.gen, avg, self._best_fitness)
            if _A2A:
                _A2A.sendjson({"gen": self.gen, "avg": avg, "sha": self.population_sha()})
            elite_idx = sorted(range(self.pop_size), key=lambda i: scores[i], reverse=True)[: self.elitism]
            new_pop = [self.population[i] for i in elite_idx]
            while len(new_pop) < self.pop_size:
                new_pop.append(self._select(scores).mutate(self.rng))
            self.population = new_pop
            self.gen += 1
            self._save()

    # checkpoint -----------------------------------------------------------
    def _save(self):
        data = {
            "format_version": 2,
            "gen": self.gen,
            "elitism": self.elitism,
            "pop": [g.to_json() for g in self.population],
            "hist": self.history,
            "arc": [{"dtype": a.dtype.str, "values": a.tolist()} for a in self._archive],
            "seed": self.seed,
            "rng_state": self.rng.getstate(),
            "sha": self.population_sha(),
            "last_scores": self._last_scores,
            "best_fitness": self._best_fitness,
            "best_genome": self.best_genome.to_json() if self.best_genome else None,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        p = self.ckpt_dir / f"gen_{self.gen:04d}.json.tmp"
        p.write_text(json.dumps(data))
        p.replace(p.with_suffix(""))

    def save(self) -> None:
        """Public wrapper for checkpoint persistence."""
        self._save()

    def reset(self) -> None:
        """Rewind in-memory evolution to its initial seed; keep checkpoint files."""
        self.rng.seed(self.seed)
        self._init_population()
        self.gen = 0
        self.history.clear()
        self._archive.clear()
        self._best_fitness = -math.inf
        self.best_genome = self.population[0]
        self._last_scores.clear()

    def load(self, path: pathlib.Path | None = None):
        """Restore state from ``path`` or the latest checkpoint."""
        if path is None:
            latest = max(self.ckpt_dir.glob("gen_*.json"), default=None)
            if not latest:
                raise FileNotFoundError("no checkpoint found")
            path = latest
        js = json.loads(path.read_text())
        if js.get("format_version") != 2 or "rng_state" not in js:
            raise ValueError("Legacy checkpoint lacks RNG state; exact resume requires a version 2 checkpoint")
        required = {
            "gen",
            "elitism",
            "pop",
            "hist",
            "arc",
            "seed",
            "rng_state",
            "last_scores",
            "best_fitness",
            "best_genome",
            "sha",
        }
        missing = required.difference(js)
        if missing:
            raise ValueError(f"Incomplete version 2 checkpoint: missing {', '.join(sorted(missing))}")
        # Validate into local objects so an invalid checkpoint never half-loads.
        try:
            version, internal, gaussian = js["rng_state"]
            rng = random.Random()
            rng.setstate((version, tuple(internal), gaussian))
            population = [Genome.from_json(j) for j in js["pop"]]
            history = [tuple(row) for row in js["hist"]]
            archive = []
            for entry in js["arc"]:
                dtype = np.dtype(entry["dtype"])
                if dtype.kind != "f" or dtype.itemsize not in (2, 4, 8):
                    raise ValueError("Unsupported archive dtype")
                archive.append(np.array(entry["values"], dtype=dtype))
            best_genome = Genome.from_json(js["best_genome"]) if js["best_genome"] else None
            valid = (
                type(js["seed"]) is int
                and type(js["gen"]) is int
                and js["gen"] >= 0
                and type(js["elitism"]) is int
                and 0 <= js["elitism"] <= len(population)
                and bool(population)
                and len(history) == js["gen"]
                and all(len(row) == 2 and row[0] == i and math.isfinite(row[1]) for i, row in enumerate(history))
                and all(a.ndim == 1 and a.size > 0 and np.isfinite(a).all() for a in archive)
                and (not archive or all(a.shape == archive[0].shape for a in archive))
                and len(js["last_scores"]) in (0, len(population))
                and all(math.isfinite(score) for score in js["last_scores"])
                and (math.isfinite(js["best_fitness"]) or (js["gen"] == 0 and js["best_fitness"] == -math.inf))
            )
            concat = "".join(sorted(g.sha for g in population))
            valid = valid and hashlib.sha256(concat.encode()).hexdigest()[:16] == js["sha"]
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Invalid version 2 checkpoint state") from exc
        if not valid:
            raise ValueError("Invalid version 2 checkpoint state")
        self.seed, self.rng, self.gen = js["seed"], rng, js["gen"]
        self.population, self.pop_size, self.elitism = population, len(population), js["elitism"]
        self.history, self._archive = history, archive
        self._last_scores = list(js["last_scores"])
        self._best_fitness, self.best_genome = js["best_fitness"], best_genome
        if _fitness_gauge:
            _fitness_gauge.set(self._best_fitness)
        LOG.info("Loaded checkpoint gen=%d sha=%s", self.gen, js.get("sha", "?"))

    # utils ----------------------------------------------------------------
    def population_sha(self) -> str:
        """Return a hash of the current population."""
        concat = "".join(sorted(g.sha for g in self.population))
        return hashlib.sha256(concat.encode()).hexdigest()[:16]

    def history_plot(self):
        """Return the fitness history as a ``pandas`` DataFrame."""
        import pandas as pd

        return pd.DataFrame(self.history, columns=["generation", "avg_fitness"])

    def latest_log(self):
        """Return a textual summary of the best genome."""
        champ = self.best_genome or max(self.population, key=lambda g: sum(g.layers))
        msg = f"Champion {champ.sha}: {champ.to_json()}"
        if self.llm:
            msg += "\n" + self.llm(f"Critique genome {champ.to_json()} in ≤30 words.")
        return msg

    @property
    def best_fitness(self) -> float:
        """Best fitness score observed so far."""
        return self._best_fitness

    @property
    def best_architecture(self) -> str:
        """JSON representation of the champion genome."""
        return self.best_genome.to_json() if self.best_genome else ""


def cli() -> None:
    """Run a short evolutionary loop and print the champion genome."""
    import argparse

    parser = argparse.ArgumentParser(description="AI-GA Meta-Evolver demo")
    parser.add_argument("--gens", type=int, default=5, help="Generations to run")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Evolution and evaluation seed")
    parser.add_argument("--device", choices=("cpu", "cuda"), default=None, help="Torch device override")
    args = parser.parse_args()

    if np is None or not _TORCH:
        print("Champion: stub (no training; install numpy and torch for evolution)")
        return

    from .curriculum_env import CurriculumEnv

    try:
        evolver = MetaEvolver(
            env_cls=CurriculumEnv, start_socket=False, parallel=False, seed=args.seed, device=args.device
        )
        evolver.run_generations(args.gens)
        print(evolver.latest_log())

        try:
            df = evolver.history_plot()
            print(df.tail())
        except Exception:  # pragma: no cover - pandas optional
            pass
    except Exception as exc:
        parser.exit(1, f"Evolution failed: {exc}\n")


if __name__ == "__main__":  # pragma: no cover
    cli()
