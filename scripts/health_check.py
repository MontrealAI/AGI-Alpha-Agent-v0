#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
"""Simple orchestrator health check.

This script verifies that the orchestrator's health and readiness
endpoints respond with status code ``200``. It is useful for quick
liveness checks in production or CI pipelines.
"""

from __future__ import annotations

import argparse
import sys

import httpx


def _probe(url: str) -> bool:
    try:
        r = httpx.get(url, timeout=5.0)
        if r.status_code == 200:
            return True
        print(f"{url} -> {r.status_code}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"{url} failed: {exc}", file=sys.stderr)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Check orchestrator health")
    parser.add_argument("--host", default="http://localhost:8000", help="Orchestrator base URL")
    args = parser.parse_args()
    base = args.host.rstrip("/")
    ok = True
    for path in ("/healthz", "/readiness"):
        url = f"{base}{path}"
        if _probe(url):
            print(f"OK: {url}")
        else:
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":  # pragma: no cover
    main()
