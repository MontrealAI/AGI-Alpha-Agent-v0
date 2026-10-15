#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# [See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
"""Legacy illustrative idea helper; use opportunity_comparison for supplied evidence.

Samples require --sample; external generation requires --generate explicitly.
Provider failure never silently substitutes canned findings.
Neither mode verifies opportunities or constitutes financial advice.
"""
from __future__ import annotations

import argparse
import json
import random
import os
import contextlib
import logging
from pathlib import Path
from typing import List, Dict
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)

# Timeout (seconds) for OpenAI API requests
OPENAI_TIMEOUT_SEC = int(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

try:
    from filelock import FileLock
except Exception:  # pragma: no cover - optional dependency
    FileLock = None

with contextlib.suppress(ModuleNotFoundError):
    import openai

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

DEFAULT_LEDGER = Path.home() / ".alpha_factory" / "cross_alpha_log.json"


def _ledger_path(path: str | os.PathLike[str] | None) -> Path:
    if path:
        resolved = Path(path).expanduser().resolve()
    else:
        env = os.getenv("CROSS_ALPHA_LEDGER")
        if env:
            resolved = Path(env).expanduser().resolve()
        else:
            resolved = DEFAULT_LEDGER.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def discover_alpha(
    num: int = 1,
    *,
    seed: int | None = None,
    ledger: Path | None = None,
    model: str = "gpt-4o-mini",
    sample: bool = False,
    generate: bool = False,
) -> List[Dict[str, str]]:
    """Generate cross-industry opportunities and log them.

    Args:
        num: Number of opportunities to return.
        seed: Optional RNG seed for reproducible output.
        ledger: Ledger file to write to. When ``None`` no file is written.
        sample: Explicitly select illustrative bundled examples.
        generate: Explicitly request unverified provider ideas (no fallback).
        model: OpenAI model used only with generate=True. ``main`` reads the default
            from ``CROSS_ALPHA_MODEL``.

    Environment variables:
        CROSS_ALPHA_LEDGER: Default ledger path used by :func:`main` when
            ``--ledger`` is not supplied.
        CROSS_ALPHA_MODEL: Default model used by :func:`main`.

    Returns:
        A list of dictionaries with ``sector`` and ``opportunity`` keys.
    """
    if sample == generate:
        raise ValueError("choose explicit sample=True or generate=True; use opportunity_comparison for supplied inputs")
    if generate and ("openai" not in globals() or not os.getenv("OPENAI_API_KEY")):
        raise ValueError("explicit generation requires the OpenAI package and OPENAI_API_KEY")
    if num < 1:
        raise ValueError("num must be >= 1")

    rng = random.Random(seed)
    picks: List[Dict[str, str]] = []
    if generate:
        prompt = f"List {num} short cross-industry investment opportunities as JSON"
        try:
            if hasattr(openai, "chat") and hasattr(openai.chat, "completions"):
                create = openai.chat.completions.create
            else:
                create = openai.ChatCompletion.create

            resp = create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=OPENAI_TIMEOUT_SEC,
            )
            picks = json.loads(resp.choices[0].message.content)
            if isinstance(picks, dict):
                picks = [picks]
        except Exception as exc:
            logger.warning("OpenAI request failed: %s", exc)
            raise ValueError("provider generation failed; no sample fallback") from exc
        if (
            not isinstance(picks, list)
            or not picks
            or any(
                not isinstance(item, dict)
                or not all(isinstance(item.get(k), str) and item[k].strip() for k in ("sector", "opportunity"))
                for item in picks
            )
        ):
            raise ValueError("provider returned invalid ideas; no sample fallback")
    if sample:
        if seed is not None and num == 1:
            picks = [SAMPLE_ALPHA[seed % len(SAMPLE_ALPHA)]]
        else:
            picks = rng.sample(SAMPLE_ALPHA, k=min(num, len(SAMPLE_ALPHA)))

    if ledger is not None:
        path = _ledger_path(ledger)
        lock_ctx = FileLock(str(path) + ".lock") if FileLock is not None else contextlib.nullcontext()
        with lock_ctx:
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
            with NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
                json.dump(existing, tmp, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp.name, path)
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
    modes = p.add_mutually_exclusive_group()
    modes.add_argument("--sample", action="store_true", help="explicit illustrative catalog sampling")
    modes.add_argument(
        "--generate", action="store_true", help="explicit external provider generation; unverified ideas"
    )
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

    if not args.sample and not args.generate:
        p.error("choose --sample or --generate; for supplied evidence use opportunity_comparison --input FILE")
    ledger = None if args.no_log else _ledger_path(args.ledger)
    try:
        picks = discover_alpha(
            args.num, seed=args.seed, ledger=ledger, model=args.model, sample=args.sample, generate=args.generate
        )
    except ValueError as exc:
        p.error(str(exc))

    print(json.dumps(picks[0] if args.num == 1 else picks, indent=2))
    if ledger is not None:
        print(f"Logged to {ledger}")
    else:
        print("Ledger write skipped")


if __name__ == "__main__":  # pragma: no cover
    main()
