#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Minimal Meta-Agentic Tree Search demo."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import logging
import math
import os
import random
import sys
import pathlib
from pathlib import Path
from typing import Any, List, Optional, cast

logger = logging.getLogger(__name__)

if __package__ is None:  # pragma: no cover - allow execution via `python run_demo.py`
    # Add repository root so package imports resolve when executed directly
    sys.path.append(str(pathlib.Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.meta_agentic_tree_search_v0"

if importlib.util.find_spec("yaml"):
    import yaml as yaml_module  # type: ignore

    yaml: Any | None = yaml_module
else:  # pragma: no cover - fallback parser
    yaml = None

from .mats.tree import Node, Tree  # noqa: E402
from .mats.meta_rewrite import meta_rewrite, openai_rewrite, anthropic_rewrite  # noqa: E402
from .mats.evaluators import evaluate  # noqa: E402
from .mats.env import NumberLineEnv, LiveBrokerEnv  # noqa: E402


def verify_environment() -> None:
    """Best-effort runtime dependency check."""
    try:
        import check_env

        check_env.main([])
    except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover - optional helper
        logger.warning("Environment verification failed: %s", exc)
    except Exception as exc:
        logger.warning("Unexpected error during environment verification: %s", exc)
        raise


def run(
    episodes: int = 10,
    exploration: float = 1.4,
    rewriter: str | None = None,
    log_dir: Path | None = None,
    *,
    target: int = 5,
    seed: Optional[int] = None,
    model: str | None = None,
    market_data: list[int] | None = None,
) -> None:
    """Run a toy tree search for a small number of episodes.

    Parameters
    ----------
    episodes:
        Number of tree search iterations.
    exploration:
        Exploration constant for UCB1.
    rewriter:
        Which rewrite strategy to use: ``"random"``, ``"openai"`` or ``"anthropic"``.
    log_dir:
        Optional directory where a ``scores.csv`` log is written.
    seed:
        Optional RNG seed for reproducible runs.
    model:
        Optional model override used by the rewriter.
    market_data:
        Optional list of integers representing a market price feed.
    """
    if type(episodes) is not int or not 1 <= episodes <= 10000:
        raise ValueError("Episodes must be an integer from 1 through 10000")
    if not math.isfinite(exploration) or exploration < 0:
        raise ValueError("Exploration must be finite and nonnegative")
    if type(target) is not int or not -10000 <= target <= 10000:
        raise ValueError("Target must be an integer from -10000 through 10000")
    if market_data is not None and (
        len(market_data) > 10000 or any(type(v) is not int or abs(v) > 10000 for v in market_data)
    ):
        raise ValueError("Market replay supports at most 10000 bounded integer targets")
    rng = random.Random(seed)

    root_agents: List[int] = [0, 0, 0, 0]
    env = (
        LiveBrokerEnv(target=target, market_data=market_data, rng=rng)
        if market_data
        else NumberLineEnv(target=target, rng=rng)
    )
    tree = Tree(Node(root_agents), exploration=exploration)
    if rewriter is None:
        rewriter = (
            os.getenv("MATS_REWRITER")
            or ("openai" if os.getenv("OPENAI_API_KEY") else None)
            or ("anthropic" if os.getenv("ANTHROPIC_API_KEY") else None)
            or "random"
        )
    if rewriter not in {"random", "openai", "anthropic"}:
        raise ValueError("Unknown rewrite strategy")
    from typing import Callable

    rewrite_fn: Callable[[List[int]], List[int]]
    if rewriter == "openai":

        def rewrite_fn(ag: List[int]) -> List[int]:
            """Rewrite agents using the OpenAI model."""
            return cast(List[int], openai_rewrite(ag, model=model, target=target, rng=rng))

    elif rewriter == "anthropic":

        def rewrite_fn(ag: List[int]) -> List[int]:
            """Rewrite agents using the Anthropic model."""
            return cast(List[int], anthropic_rewrite(ag, model=model, target=target, rng=rng))

    else:
        rewrite_fn = lambda ag: meta_rewrite(ag, rng=rng)
    log_fh = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_dir / "scores.csv", "w", encoding="utf-8", newline="")
        csv.writer(log_fh).writerow(["episode", "candidate", "reward"])
    try:
        for episode in range(episodes):
            node = tree.select()
            improved = rewrite_fn(node.agents)
            reward = evaluate(improved, env)
            child = Node(improved, reward=reward)
            tree.add_child(node, child)
            tree.backprop(child)
            logger.info("Episode %3d: candidate %s → reward %.3f", episode + 1, improved, reward)
            if log_fh:
                csv.writer(log_fh).writerow([episode + 1, improved, f"{reward:.6f}"])
        best = tree.best_leaf()
        score = best.reward / (best.visits or 1)
        logger.info("Best agents: %s score: %.3f", best.agents, score)
        if log_fh:
            csv.writer(log_fh).writerow(["best", best.agents, f"{score:.6f}"])
    finally:
        if log_fh:
            log_fh.close()


def load_config(path: Path) -> dict[str, Any]:
    """Load a YAML configuration file with a minimal fallback parser."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as stream:
        text = stream.read(1_000_001)
    if len(text) > 1_000_000:
        raise ValueError("Configuration exceeds 1 MB")
    if yaml:
        result = yaml.safe_load(text) or {}
        if not isinstance(result, dict):
            raise ValueError("Configuration must be a mapping")
        return result
    cfg: dict[str, object] = {}
    for line in text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            val = val.strip()
            if val.replace(".", "", 1).isdigit():
                cfg[key.strip()] = float(val) if "." in val else int(val)
            else:
                cfg[key.strip()] = val
    return cfg


def main(argv: List[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run the Meta-Agentic Tree Search demo")
    parser.add_argument("--episodes", type=int, help="Number of search iterations")
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("configs") / "default.yaml", help="YAML configuration"
    )
    parser.add_argument(
        "--rewriter",
        choices=["random", "openai", "anthropic"],
        help="Rewrite strategy",
    )
    parser.add_argument("--target", type=int, help="Target integer for the environment")
    parser.add_argument("--seed", type=int, help="Optional RNG seed")
    parser.add_argument(
        "--model",
        type=str,
        help="Model name for the rewriter (OpenAI or Anthropic)",
    )
    parser.add_argument(
        "--market-data",
        type=Path,
        help="CSV file with comma-separated integers for LiveBrokerEnv",
    )
    parser.add_argument("--log-dir", type=Path, help="Optional directory to store episode logs")
    parser.add_argument(
        "--verify-env",
        action="store_true",
        help="Check runtime dependencies before running",
    )
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)

        market_data: list[int] | None = None
        if args.market_data:
            with args.market_data.open(encoding="utf-8") as stream:
                text = stream.read(1_000_001)
            if len(text) > 1_000_000:
                raise ValueError("Market replay exceeds 1 MB")
            market_data = [int(x) for x in text.split(",") if x.strip()]

        if args.verify_env:
            verify_environment()
        episodes = args.episodes if args.episodes is not None else int(cfg.get("episodes", 10))
        exploration = float(cfg.get("exploration", 1.4))
        rewriter = args.rewriter or cfg.get("rewriter", "random")
        target = args.target if args.target is not None else int(cfg.get("target", 5))
        seed = args.seed if args.seed is not None else cfg.get("seed")
        seed = int(seed) if seed is not None else None
        model = args.model or cfg.get("model")
        run(
            episodes,
            exploration,
            rewriter,
            target=target,
            seed=seed,
            log_dir=args.log_dir,
            model=model,
            market_data=market_data,
        )
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
