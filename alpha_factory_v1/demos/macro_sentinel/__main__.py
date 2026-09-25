# SPDX-License-Identifier: Apache-2.0
"""Run a reproducible, finite Macro Sentinel scenario from bundled sample data."""
from __future__ import annotations

import argparse
import asyncio
import json

from alpha_factory_v1.utils.disclaimer import print_disclaimer
from .data_feeds import stream_macro_events
from .simulation_core import MonteCarloSimulator


def main() -> None:
    """Print simulated risk metrics without a market connection or order submission."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", type=int, default=500)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not 1 <= args.paths <= 100000 or not 1 <= args.horizon <= 365:
        parser.error("paths must be 1–100000 and horizon 1–365")
    print_disclaimer()

    async def sample() -> dict:
        stream = stream_macro_events(live=False)
        try:
            return await anext(stream)
        finally:
            await stream.aclose()

    simulator = MonteCarloSimulator(args.paths, args.horizon, seed=args.seed)
    factors = simulator.simulate(asyncio.run(sample()))
    print(
        json.dumps(
            {
                "mode": "offline simulation",
                "seed": args.seed,
                "paths": len(factors),
                "var_5pct": simulator.var(factors),
                "cvar_5pct": simulator.cvar(factors),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
