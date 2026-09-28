# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""Legacy objective aggregation, Pareto comparison and optional lineage export.

Callable candidates are trusted local Python functions, not JSON-loaded programs.
Provider and graph integrations require optional dependencies. The finite
curriculum lab supplies the reproducible, independently evaluated default workflow.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence


# Fallback optional imports
try:
    import litellm  # Unified thin wrapper around many LLM providers
except ImportError:  # pragma: no cover — litellm optional
    litellm = None  # type: ignore

__all__ = [
    "ModelProvider",
    "OpenAIProvider",
    "OpenWeightsProvider",
    "objective",
    "TaskResult",
    "EvaluationError",
    "MultiObjectiveScorer",
]

###############################################################
# Exceptions & data containers                                #
###############################################################


class EvaluationError(RuntimeError):
    """Raised when an objective fails irrecoverably."""


@dataclass
class TaskResult:
    """Container for objective results of a single candidate on a single task."""

    candidate_id: str
    objective_values: Dict[str, float]
    meta: Dict[str, Any] = field(default_factory=dict)


###############################################################
# Model provider abstraction                                   #
###############################################################


class ModelProvider:
    """Abstract base wrapper. Sub‑class to support a new backend."""

    def __init__(self, model: str, **kw: Any) -> None:  # noqa: D401
        self.model = model
        self.kw = kw

    # ---------------------------------------------------------------------
    def chat(self, messages: List[Dict[str, str]], **options: Any) -> str:  # noqa: D401
        raise NotImplementedError

    # ---------------------------------------------------------------------
    @staticmethod
    def from_name(name: str, model: str, **kw: Any) -> "ModelProvider":
        name = name.lower()
        if name in {"openai", "open_ai", "gpt"}:
            return OpenAIProvider(model, **kw)
        if name in {"open_weights", "local", "ollama", "vllm"}:
            return OpenWeightsProvider(model, **kw)
        raise ValueError(f"Unknown provider: {name}")


class OpenAIProvider(ModelProvider):
    def __init__(self, model: str, **kw: Any):
        super().__init__(model, **kw)
        if litellm is None:
            raise RuntimeError("litellm must be installed for OpenAIProvider")

    # ------------------------------------------------------------------
    def chat(self, messages: List[Dict[str, str]], **options: Any) -> str:
        resp = litellm.completion(
            model=self.model,
            messages=messages,
            stream=False,
            **self.kw,
            **options,
        )
        return resp["choices"][0]["message"]["content"].strip()


class OpenWeightsProvider(ModelProvider):
    """Assumes an open‑weights model served via Ollama, local Llama.cpp or similar."""

    def __init__(self, model: str, host: str = "http://localhost:11434", **kw: Any):
        super().__init__(model, **kw)
        self.host = host
        try:
            import ollama  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("`pip install ollama` required for open‑weights provider") from exc
        self.client = ollama.Client(host=host)

    # ------------------------------------------------------------------
    def chat(self, messages: List[Dict[str, str]], **options: Any) -> str:
        prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
        completion = self.client.generate(model=self.model, prompt=prompt, **options)
        return completion["response"].strip()


###############################################################
# Objective system                                             #
###############################################################


_OBJECTIVE_REGISTRY: Dict[str, Callable[[Mapping[str, Any]], float]] = {}


def objective(name: str | None = None):  # noqa: D401
    """Decorator to register a scoring objective."""

    def _decorator(fn: Callable[[Mapping[str, Any]], float]):
        _OBJECTIVE_REGISTRY[name or fn.__name__] = fn
        return fn

    return _decorator


@objective("task_accuracy")
def _acc(obj: Mapping[str, Any]) -> float:  # noqa: D401
    return float(obj.get("correct", 0))


@objective("cost")
def _cost(obj: Mapping[str, Any]) -> float:  # noqa: D401 — lower is better
    return -float(obj.get("cost_usd", 0.0))


@objective("latency")
def _lat(obj: Mapping[str, Any]) -> float:  # noqa: D401
    return -float(obj.get("latency", 0.0))


@objective("novelty")
def _novelty(obj: Mapping[str, Any]) -> float:  # noqa: D401
    return float(obj.get("novelty", 0.0))


@objective("risk_score")
def _risk(obj: Mapping[str, Any]) -> float:  # noqa: D401 — lower risk preferred
    return -float(obj.get("risk_score", 0.0))


###############################################################
# Lineage tracker                                              #
###############################################################


class LineageTracker:
    def __init__(self):
        import networkx as nx

        self.graph = nx.DiGraph()

    # ------------------------------------------------------------------
    def add_evaluation(
        self,
        parent_ids: Sequence[str],
        candidate_id: str,
        objective_values: Mapping[str, float],
    ) -> None:
        self.graph.add_node(candidate_id, **objective_values)
        for p in parent_ids:
            self.graph.add_edge(p, candidate_id)

    # ------------------------------------------------------------------
    def export(self, path: str | os.PathLike[str]) -> None:
        import importlib.util
        import networkx as nx

        if importlib.util.find_spec("pydot") is None:
            raise RuntimeError("`pip install pydot` required for export")
        dot = nx.nx_pydot.to_pydot(self.graph)
        dot.write_svg(str(path))


###############################################################
# Multi‑objective scorer                                       #
###############################################################


class MultiObjectiveScorer:
    def __init__(
        self,
        provider: ModelProvider,
        objectives: Sequence[str] | None = None,
        lineage: LineageTracker | None = None,
    ) -> None:
        self.provider = provider
        self.objective_fns = {name: _OBJECTIVE_REGISTRY[name] for name in (objectives or _OBJECTIVE_REGISTRY)}
        self.lineage = lineage or LineageTracker()

    # ------------------------------------------------------------------
    def evaluate_candidate(
        self,
        candidate: Mapping[str, Any],
        tasks: Iterable[Mapping[str, Any]],
        parent_ids: Sequence[str] | None = None,
    ) -> TaskResult:
        start = time.perf_counter()
        scores: Dict[str, List[float]] = {k: [] for k in self.objective_fns}
        meta: Dict[str, Any] = {"latency": None, "cost_usd": 0.0}

        for t in tasks:
            # Example single metric: correctness
            correct = candidate["fn"](t)  # type: ignore
            obj_input = {
                "correct": correct,
                "cost_usd": 0.0,  # Extend with accounting
                "latency": 0.0,
                "novelty": candidate.get("novelty", 0.0),
                "risk_score": candidate.get("risk", 0.0),
            }
            for name, fn in self.objective_fns.items():
                try:
                    scores[name].append(fn(obj_input))
                except Exception as exc:  # noqa: BLE001
                    raise EvaluationError(name) from exc

        if not any(scores.values()):
            raise ValueError("At least one validation task is required")
        meta["latency"] = time.perf_counter() - start
        agg = {k: mean(v) for k, v in scores.items()}
        cid = candidate.get("id", str(uuid.uuid4())[:8])
        self.lineage.add_evaluation(parent_ids or [], cid, agg)
        return TaskResult(candidate_id=cid, objective_values=agg, meta=meta)


###############################################################
# Pareto frontier util                                         #
###############################################################


def compute_pareto(results: List[TaskResult], maximize: Sequence[str]):
    """Return nondominated indices, maximizing named and minimizing other metrics."""
    if not results:
        return []
    fields = set(results[0].objective_values)
    if not set(maximize).issubset(fields) or any(set(r.objective_values) != fields for r in results):
        raise ValueError("Pareto comparisons require matching objective fields")
    import math

    if any(not math.isfinite(v) for r in results for v in r.objective_values.values()):
        raise ValueError("Pareto objectives must be finite")

    def oriented(result):
        return [result.objective_values[k] * (1 if k in maximize else -1) for k in sorted(fields)]

    vectors = [oriented(result) for result in results]
    return [
        i
        for i, a in enumerate(vectors)
        if not any(
            all(y >= x for x, y in zip(a, b)) and any(y > x for x, y in zip(a, b))
            for j, b in enumerate(vectors)
            if i != j
        )
    ]


###############################################################
# Command‑line interface                                       #
###############################################################


def _load_candidates(path: Path) -> List[Dict[str, Any]]:
    with path.open() as f:
        return json.load(f)


def _dump_json(obj: Any, path: Path):
    path.write_text(json.dumps(obj, indent=2))


def main(argv: Sequence[str] | None = None):  # noqa: D401
    p = argparse.ArgumentParser(description="Multi‑objective scorer for Alpha‑Factory agents")
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--val_data", type=Path, required=True)
    p.add_argument("--provider", default="open_weights")
    p.add_argument("--model", default="llama3")
    p.add_argument("--objectives", nargs="*", default=["task_accuracy", "cost", "latency"])
    p.add_argument("--out", type=Path, default=Path("scores"))
    args = p.parse_args(argv)

    provider = ModelProvider.from_name(args.provider, args.model)
    scorer = MultiObjectiveScorer(provider, objectives=args.objectives)

    candidates = _load_candidates(args.candidates)
    tasks = _load_candidates(args.val_data)

    results: List[TaskResult] = []
    for cand in candidates:
        try:
            res = scorer.evaluate_candidate(cand, tasks)
            results.append(res)
        except EvaluationError as exc:
            print(f"[WARN] Candidate {cand.get('id')} failed objective {exc}")

    args.out.mkdir(parents=True, exist_ok=True)
    _dump_json([r.__dict__ for r in results], args.out / "scores.json")

    front_idx = compute_pareto(results, maximize=args.objectives)
    pareto = [results[i].__dict__ for i in front_idx]
    _dump_json(pareto, args.out / "pareto.json")

    scorer.lineage.export(args.out / "lineage.svg")
    print(f"Wrote results to {args.out}")


if __name__ == "__main__":  # pragma: no cover
    main()
