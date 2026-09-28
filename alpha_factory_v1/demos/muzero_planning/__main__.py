# SPDX-License-Identifier: Apache-2.0
"""Launch the local dashboard or run a finite, reproducible learning experiment."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ...utils.disclaimer import print_disclaimer


def main(argv: list[str] | None = None) -> None:
    """Keep --help dependency-free and report invalid inputs with nonzero exit status."""
    parser = argparse.ArgumentParser(description="MuZero planning demo — train, inspect and compare")
    parser.add_argument("--env", default=os.getenv("MUZERO_ENV_ID", "MiniChoice-v0"))
    parser.add_argument("--episodes", type=int, default=os.getenv("MUZERO_EPISODES", "32"))
    parser.add_argument("--port", type=int, default=os.getenv("HOST_PORT", "7861"))
    parser.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1", "0.0.0.0"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--simulations", type=int, default=32)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--headless", action="store_true", help="Train and evaluate, then exit; no server or API keys")
    parser.add_argument("--output", type=Path, help="New JSON report path (refuses overwrite)")
    parser.add_argument("--checkpoint", type=Path, help="New portable JSON weights path (refuses overwrite)")
    args = parser.parse_args(argv)
    try:
        from .minimuzero import bounded_int, require_dependencies

        bounded_int("port", args.port, 1, 65535)
        require_dependencies()
        from .training import Config, experiment, checkpoint_bytes

        config = Config(args.env, args.seed, args.episodes, args.simulations, args.max_steps)
        if not args.headless and (args.output or args.checkpoint):
            raise ValueError("--output and --checkpoint require --headless")
        outputs = [p.resolve() for p in (args.output, args.checkpoint) if p]
        if len(set(outputs)) != len(outputs) or any(p.exists() for p in outputs):
            raise ValueError("Choose distinct, new output paths; existing files are never overwritten")
        print_disclaimer()
        if args.headless:
            report = {}
            for report in experiment(config):
                if report["status"] == "training":
                    print(f"Training {report['completed']}/{report['total']}", flush=True)
            for mode, scores in report["evaluation"].items():
                print(f"{mode}: mean reward {sum(scores) / len(scores):.3f} ({len(scores)} held-out episodes)")
            for path, data in ((args.output, report), (args.checkpoint, report["checkpoint"])):
                if path:
                    if path == args.checkpoint:
                        with path.open("xb") as target_bytes:
                            target_bytes.write(checkpoint_bytes(data))
                    else:
                        with path.open("x", encoding="utf-8") as target:
                            json.dump(data, target, indent=2, allow_nan=False)
                            target.write("\n")
                    print(f"Saved {path}")
        else:
            from .agent_muzero_entrypoint import launch_dashboard

            launch_dashboard(config=config, host=args.host, port=args.port)
    except (ValueError, RuntimeError, ImportError, OSError) as exc:
        parser.exit(2, f"MuZero: {exc}\n")


if __name__ == "__main__":
    main()
