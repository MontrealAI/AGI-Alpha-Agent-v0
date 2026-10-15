#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# [See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
"""Queue supplied, eligible assessments or explicitly requested samples.

Use --dry-run to inspect jobs without contacting the orchestrator. Queueing is
an external action and requires operator authorization. No provider is called.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Mapping
from pathlib import Path

from alpha_factory_v1.demos.alpha_agi_marketplace_v1 import MarketplaceClient
from .cross_alpha_discovery_stub import discover_alpha
from .opportunity_comparison import compare_opportunities, load_input

DEFAULT_AGENT = "finance"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000


def make_job(opportunity: Mapping[str, Any], agent: str = DEFAULT_AGENT) -> Mapping[str, Any]:
    """Return a job dict for the marketplace."""
    note = f"Evaluate opportunity: {opportunity['opportunity']} ({opportunity['sector']})"
    if "evidence" in opportunity:
        note += "\nSupplied assessment for human review, not authorization or a forecast."
        note += "\nAssessment: " + json.dumps(dict(opportunity), ensure_ascii=False, sort_keys=True)
    return {"agent": agent, "note": note}


def queue_opportunities(
    num: int,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    agent: str = DEFAULT_AGENT,
    model: str | None = None,
    dry_run: bool = False,
    supplied: dict[str, Any] | None = None,
    sample: bool = False,
) -> List[Mapping[str, Any]]:
    """Discover opportunities and queue them on the orchestrator."""
    if supplied is not None and sample:
        raise ValueError("choose supplied inputs or sample mode, not both")
    if num < 1:
        raise ValueError("num must be >= 1")
    if supplied is not None:
        report = compare_opportunities(supplied)
        opps = [row for row in report["ranking"] if row["eligible"]][:num]
    else:
        opps = discover_alpha(num=num, ledger=None, model=model, sample=sample)
    client = MarketplaceClient(host, port)
    jobs = [make_job(o, agent=agent) for o in opps]
    for job in jobs:
        if dry_run:
            print(json.dumps(job, indent=2))
        else:
            resp = client.queue_job(job)
            print(f"Queued: {resp.status_code} -> {job['note']}")
    return jobs


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="supplied opportunity assessments")
    source.add_argument("--sample", action="store_true", help="explicit illustrative samples")
    ap.add_argument("-n", "--num", type=int, default=1, help="number of opportunities")
    ap.add_argument("--model", help="deprecated compatibility option; samples do not call a provider")
    ap.add_argument("--agent", default=DEFAULT_AGENT, help="target agent name")
    ap.add_argument("--host", default=DEFAULT_HOST, help="orchestrator host")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help="orchestrator port")
    ap.add_argument("--dry-run", action="store_true", help="print jobs without queueing")
    return ap.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        queue_opportunities(
            args.num,
            host=args.host,
            port=args.port,
            agent=args.agent,
            model=args.model,
            dry_run=args.dry_run,
            supplied=load_input(args.input) if args.input else None,
            sample=args.sample,
        )
    except (ValueError, OSError, RecursionError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":  # pragma: no cover
    main()
