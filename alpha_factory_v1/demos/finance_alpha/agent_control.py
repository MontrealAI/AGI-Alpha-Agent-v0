#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the supported paper engine, or explicitly inspect a compatible legacy REST service."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from typing import Any

from .paper import CASES, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, default="trend")
    parser.add_argument("--legacy-rest", action="store_true", help="Read compatible legacy positions/P&L routes")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        if not 1 <= args.port <= 65535:
            raise ValueError("Port must be in 1–65535")
        if not args.legacy_rest:
            print(json.dumps(run(case=args.case)["result"]["summary"], indent=2))
            return
        token = os.getenv("API_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # These routes require a separately configured legacy service. No SDK fallback is invented.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
                raise ValueError("Legacy redirects are not allowed")

        client = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        for route in ("positions", "pnl"):
            request = urllib.request.Request(f"http://127.0.0.1:{args.port}/api/finance/{route}", headers=headers)
            with client.open(request, timeout=5) as response:
                raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("Legacy response exceeded 64 KiB")
            print(route, json.dumps(json.loads(raw), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Finance control: {exc}\n")


if __name__ == "__main__":
    main()
