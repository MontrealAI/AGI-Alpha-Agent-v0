# SPDX-License-Identifier: Apache-2.0
"""Dependency-light CLI for the evidence and planning lab."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...utils.disclaimer import print_disclaimer


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="MuZero × MCTS × LLM — retrieve, propose, measure")
    parser.add_argument("--headless", action="store_true", help="Run a finite experiment and exit")
    parser.add_argument("--question", default="Which first action maximizes delayed reward?")
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--simulations", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="", help="Explicit installed local Ollama model; default disables LLM")
    parser.add_argument("--port", type=int, default=7862)
    parser.add_argument("--output", type=Path, help="New JSON report path, requires --headless")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.port <= 65535:
            raise ValueError("Port must be in 1–65535")
        if args.output and not args.headless:
            raise ValueError("--output requires --headless")
        if args.output and args.output.exists():
            raise ValueError("Output already exists; choose a new path")
        from .lab import retrieve, run
        from ..muzero_planning.training import Config

        retrieve(args.question)
        Config("MiniChoice-v0", args.seed, args.episodes, args.simulations, 2)
        print_disclaimer()
        if args.headless:
            for event in run(
                args.question, episodes=args.episodes, simulations=args.simulations, seed=args.seed, model=args.model
            ):
                if event["status"] == "training":
                    print(f"Training {event['completed']}/{event['total']}", flush=True)
            if args.output:
                with args.output.open("x", encoding="utf-8") as target:
                    json.dump(event, target, indent=2, allow_nan=False)
                    target.write("\n")
            print(
                json.dumps(
                    {
                        key: event[key]
                        for key in ("search_action", "advice", "counterfactuals", "decision", "execution")
                    },
                    indent=2,
                )
            )
        else:
            from .ui import launch

            launch(args)
    except (ValueError, RuntimeError, ImportError, OSError) as exc:
        parser.exit(2, f"Planning lab: {exc}\n")


if __name__ == "__main__":
    main()
