#!/usr/bin/env python3
"""Minimal Meta-Agentic Tree Search demo."""
from __future__ import annotations

import argparse
import os
import random
from pathlib import Path
from typing import List, Optional

try:  # PyYAML optional for offline environments
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback parser
    yaml = None

from .mats.tree import Node, Tree
from .mats.meta_rewrite import meta_rewrite, openai_rewrite
from .mats.evaluators import evaluate
from .mats.env import NumberLineEnv


def verify_environment() -> None:
    """Best-effort runtime dependency check."""
    try:
        import check_env  # type: ignore

        check_env.main([])
    except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover - optional helper
        print(f"Environment verification failed: {exc}")
    except Exception as exc:
        print(f"Unexpected error during environment verification: {exc}")
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
) -> tuple[list[int], float]:
    """Run a toy tree search for a small number of episodes and return the best result.

    Parameters
    ----------
    episodes:
        Number of tree search iterations.
    exploration:
        Exploration constant for UCB1.
    rewriter:
        Which rewrite strategy to use: ``"random"`` or ``"openai"``.
    log_dir:
        Optional directory where a ``scores.csv`` log is written.
    seed:
        Optional RNG seed for reproducible runs.
    model:
        Optional OpenAI model override used by :func:`openai_rewrite`.

    Returns
    -------
    tuple[list[int], float]
        The best policy discovered and its average score.
    """
    if seed is not None:
        random.seed(seed)

    root_agents: List[int] = [0, 0, 0, 0]
    env = NumberLineEnv(target=target)
    tree = Tree(Node(root_agents), exploration=exploration)
    if rewriter is None:
        rewriter = "openai" if os.getenv("OPENAI_API_KEY") else "random"
    if rewriter == "openai":
        rewrite_fn = lambda ag: openai_rewrite(ag, model=model)
    else:
        rewrite_fn = meta_rewrite
    log_fh = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_dir / "scores.csv", "w", encoding="utf-8")
        log_fh.write("episode,candidate,reward\n")
    for _ in range(episodes):
        node = tree.select()
        improved = rewrite_fn(node.agents)
        reward = evaluate(improved, env)
        child = Node(improved, reward=reward)
        tree.add_child(node, child)
        tree.backprop(child)
        print(f"Episode {_+1:>3}: candidate {improved} → reward {reward:.3f}")
        if log_fh:
            log_fh.write(f"{_+1},{improved},{reward:.6f}\n")
    best = tree.best_leaf()
    score = best.reward / (best.visits or 1)
    print(f"Best agents: {best.agents} score: {score:.3f}")
    if log_fh:
        log_fh.write(f"best,{best.agents},{score:.6f}\n")
        log_fh.close()
    return best.agents, score


def load_config(path: Path) -> dict:
    """Load a YAML configuration file with a minimal fallback parser."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(text) or {}
    cfg: dict[str, object] = {}
    for line in text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            val = val.strip()
            if val.replace('.', '', 1).isdigit():
                cfg[key.strip()] = float(val) if "." in val else int(val)
            else:
                cfg[key.strip()] = val
    return cfg


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Meta-Agentic Tree Search demo")
    parser.add_argument("--episodes", type=int, help="Number of search iterations")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"), help="YAML configuration")
    parser.add_argument(
        "--rewriter",
        choices=["random", "openai"],
        help="Rewrite strategy",
    )
    parser.add_argument("--target", type=int, help="Target integer for the environment")
    parser.add_argument("--seed", type=int, help="Optional RNG seed")
    parser.add_argument("--model", type=str, help="OpenAI model for the rewriter")
    parser.add_argument("--log-dir", type=Path, help="Optional directory to store episode logs")
    parser.add_argument(
        "--verify-env",
        action="store_true",
        help="Check runtime dependencies before running",
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.config)

    if args.verify_env:
        verify_environment()
    episodes = args.episodes or int(cfg.get("episodes", 10))
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
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
