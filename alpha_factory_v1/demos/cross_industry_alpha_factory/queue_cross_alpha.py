#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# [See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
"""Queue cross‑industry opportunities on the α‑AGI Marketplace.

This helper script discovers potential opportunities using
:func:`cross_alpha_discovery_stub.discover_alpha` and submits them as
jobs to the orchestrator via :class:`MarketplaceClient`. It can operate
fully offline when no OpenAI key is configured.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, List, Mapping

from alpha_factory_v1.demos.alpha_agi_marketplace_v1 import MarketplaceClient
from .cross_alpha_discovery_stub import discover_alpha

DEFAULT_AGENT = "finance"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000


def make_job(opportunity: Mapping[str, str], agent: str = DEFAULT_AGENT) -> Mapping[str, Any]:
    """Return a job dict for the marketplace."""
    note = f"Evaluate opportunity: {opportunity['opportunity']} ({opportunity['sector']})"
    return {"agent": agent, "note": note}


def queue_opportunities(
    num: int,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    agent: str = DEFAULT_AGENT,
    model: str | None = None,
    dry_run: bool = False,
) -> List[Mapping[str, Any]]:
    """Discover opportunities and queue them on the orchestrator."""
    opps = discover_alpha(num=num, ledger=None, model=model)
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
    ap.add_argument("-n", "--num", type=int, default=1, help="number of opportunities")
    ap.add_argument("--model", help="OpenAI model when API key is available")
    ap.add_argument("--agent", default=DEFAULT_AGENT, help="target agent name")
    ap.add_argument("--host", default=DEFAULT_HOST, help="orchestrator host")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help="orchestrator port")
    ap.add_argument("--dry-run", action="store_true", help="print jobs without queueing")
    return ap.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    queue_opportunities(
        args.num,
        host=args.host,
        port=args.port,
        agent=args.agent,
        model=args.model,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
