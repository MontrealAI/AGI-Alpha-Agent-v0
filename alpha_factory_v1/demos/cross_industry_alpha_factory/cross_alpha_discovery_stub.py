#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cross‑Industry alpha discovery helper.

This script is part of a research prototype and does not implement real AGI.

This minimal command‑line tool surfaces potential "alpha" opportunities
across industries. It works **fully offline** using a small sample set but
will query OpenAI when an ``OPENAI_API_KEY`` is configured for live ideas.
Discovered items are logged to ``cross_alpha_log.json`` by default.  The
queried model defaults to ``gpt-4o-mini`` but can be overridden with
``--model`` or ``CROSS_ALPHA_MODEL``.

The suggestions returned by this stub are purely illustrative examples and
should **not** be considered financial advice.
"""
from __future__ import annotations

import argparse
import json
import random
import os
import contextlib
from pathlib import Path
from typing import List, Dict

with contextlib.suppress(ModuleNotFoundError):
    import openai  # type: ignore

SAMPLE_ALPHA: List[Dict[str, str]] = [
    {
        "sector": "Energy",
        "opportunity": "Battery storage arbitrage between solar overproduction and evening peak demand",
    },
    {"sector": "Supply Chain", "opportunity": "Reroute shipping from congested port to alternate harbor to cut delays"},
    {"sector": "Finance", "opportunity": "Hedge currency exposure using futures due to predicted FX volatility"},
    {"sector": "Manufacturing", "opportunity": "Optimize machine maintenance schedule to reduce unplanned downtime"},
    {"sector": "Biotech", "opportunity": "Repurpose existing drug for new therapeutic target"},
    {"sector": "Agriculture", "opportunity": "Precision irrigation to save water during drought conditions"},
    {"sector": "Retail", "opportunity": "Dynamic pricing to clear excess seasonal inventory"},
    {"sector": "Transportation", "opportunity": "Last-mile delivery optimization with electric micro-vehicles"},
    {"sector": "Construction", "opportunity": "Modular prefab builds to reduce on-site waste"},
    {"sector": "Telecom", "opportunity": "Lease dark fiber to data-intensive startups"},
]

DEFAULT_LEDGER = Path(__file__).with_name("cross_alpha_log.json")

def _ledger_path(path: str | os.PathLike | None) -> Path:
    if path:
        return Path(path).expanduser().resolve()
    env = os.getenv("CROSS_ALPHA_LEDGER")
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_LEDGER


def discover_alpha(
    num: int = 1,
    *,
    seed: int | None = None,
    ledger: Path | None = None,
    model: str = "gpt-4o-mini",
) -> List[Dict[str, str]]:
    """Generate cross-industry opportunities and log them.

    Args:
        num: Number of opportunities to return.
        seed: Optional RNG seed for reproducible output.
        ledger: Ledger file to write to. When ``None``, ``CROSS_ALPHA_LEDGER`` or
            ``cross_alpha_log.json`` is used.
        model: OpenAI model to query when available. ``main`` reads the default
            from ``CROSS_ALPHA_MODEL``.

    Environment variables:
        CROSS_ALPHA_LEDGER: Default ledger path when ``ledger`` is ``None``.
        CROSS_ALPHA_MODEL: Default model used by :func:`main`.

    Returns:
        A list of dictionaries with ``sector`` and ``opportunity`` keys.
    """
    if seed is not None:
        random.seed(seed)
    picks: List[Dict[str, str]] = []
    if "openai" in globals() and os.getenv("OPENAI_API_KEY"):
        prompt = (
            "List "
            f"{num} short cross-industry investment opportunities as JSON"
        )
        try:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            picks = json.loads(resp.choices[0].message.content)  # type: ignore[index]
            if isinstance(picks, dict):
                picks = [picks]
        except Exception:
            picks = []
    if not picks:
        picks = [random.choice(SAMPLE_ALPHA) for _ in range(max(1, num))]

    path = _ledger_path(ledger) if ledger else DEFAULT_LEDGER
    existing: List[Dict[str, str]] = []
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                existing = [data]
            elif isinstance(data, list):
                existing = data
    except (json.JSONDecodeError, OSError):
        existing = []

    existing.extend(picks if num != 1 else [picks[0]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2))
    return picks


def main(argv: List[str] | None = None) -> None:  # pragma: no cover - CLI wrapper
    """Command-line entry point.

    Args:
        argv: Optional command-line arguments.

    Environment variables:
        CROSS_ALPHA_MODEL: Default model when ``--model`` is not supplied.
        CROSS_ALPHA_LEDGER: Default ledger path when ``--ledger`` is absent.

    Returns:
        ``None``
    """
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-n", "--num", type=int, default=1, help="number of opportunities to sample")
    p.add_argument("--list", action="store_true", help="list all sample opportunities and exit")
    p.add_argument("--seed", type=int, help="seed RNG for reproducible output")
    p.add_argument("--ledger", help="path to ledger JSON file")
    p.add_argument("--no-log", action="store_true", help="do not write to ledger")
    p.add_argument(
        "--model",
        default=os.getenv("CROSS_ALPHA_MODEL", "gpt-4o-mini"),
        help="OpenAI model to query when API key available",
    )
    args = p.parse_args(argv)

    if args.list:
        print(json.dumps(SAMPLE_ALPHA, indent=2))
        return

    ledger = _ledger_path(args.ledger)
    picks = discover_alpha(args.num, seed=args.seed, ledger=ledger, model=args.model)
    if args.no_log:
        ledger.unlink(missing_ok=True)
    print(json.dumps(picks[0] if args.num == 1 else picks, indent=2))
    print(f"Logged to {ledger}" if not args.no_log else "Ledger write skipped")


if __name__ == "__main__":  # pragma: no cover
    main()
