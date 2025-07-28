#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# NOTE: This demo is a research prototype. References to "AGI" or "superintelligence" describe aspirational goals and do not indicate the presence of real general intelligence. Use at your own risk. Nothing herein constitutes financial advice.
"""Local launcher for the Alpha‑AGI Business v1 demo.

Runs the orchestrator directly without Docker and optionally starts the
OpenAI Agents bridge when available. This script is intended for quick
experimentation on a developer workstation or inside a Colab runtime.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser

# allow running this script directly from its folder
SCRIPT_DIR = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import check_env


def _set_business_host(host: str) -> None:
    """Propagate the orchestrator base URL to the bridge module.

    This helper updates the ``BUSINESS_HOST`` environment variable and
    mirrors the value inside :mod:`openai_agents_bridge` when that module
    is available.  It keeps the launcher functional even when the bridge
    was imported prior to setting the environment variable.
    """

    os.environ["BUSINESS_HOST"] = host
    try:  # soft dependency
        from alpha_factory_v1.demos.alpha_agi_business_v1 import (
            openai_agents_bridge,
        )

        openai_agents_bridge.HOST = host
    except Exception:
        pass


def _start_bridge(host: str, runtime_port: int) -> None:
    """Start the OpenAI Agents bridge in a background thread.

    Parameters
    ----------
    host:
        Base URL for the orchestrator that the bridge should
        communicate with (e.g. ``"http://localhost:8000"``).
    """
    os.environ["AGENTS_RUNTIME_PORT"] = str(runtime_port)
    try:
        from alpha_factory_v1.demos.alpha_agi_business_v1 import openai_agents_bridge
    except Exception as exc:  # pragma: no cover - optional dep
        print(f"⚠️  OpenAI bridge not available: {exc}")
        return
    _set_business_host(host=host)
    thread = threading.Thread(target=openai_agents_bridge.main, daemon=True)
    thread.start()


def _open_browser_when_ready(url: str, timeout: float = 5.0) -> None:
    """Open *url* in the default browser once the orchestrator responds.

    Parameters
    ----------
    url : str
        The URL to open in the browser.
    timeout : float, optional
        The maximum time to wait (in seconds) for the orchestrator to respond
        before falling back to opening the URL anyway. Default is 5.0 seconds.

    Fallback Behavior
    -----------------
    If the orchestrator does not respond within the specified timeout, the
    URL will still be opened in the browser as a fallback.
    """

    def _wait_and_open() -> None:
        import af_requests as requests  # type: ignore

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if requests.get(f"{url.rstrip('/')}/healthz", timeout=1).status_code == 200:
                    webbrowser.open(url, new=1)
                    return
            except Exception:
                time.sleep(0.2)
        # fallback: open anyway
        webbrowser.open(url, new=1)

    threading.Thread(target=_wait_and_open, daemon=True).start()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run alpha_agi_business_v1 locally")
    parser.add_argument(
        "--bridge",
        action="store_true",
        help="Launch OpenAI Agents bridge if available",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Expose orchestrator on this port (default: 8000)",
    )
    parser.add_argument(
        "--runtime-port",
        type=int,
        default=5001,
        metavar="PORT",
        help="Expose Agents runtime on this port (default: 5001)",
    )
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Attempt automatic installation of missing packages",
    )
    parser.add_argument(
        "--wheelhouse",
        help="Optional local wheelhouse path for offline installs",
    )
    parser.add_argument(
        "--open-ui",
        action="store_true",
        help="Open the REST docs in a web browser once ready",
    )
    args = parser.parse_args(argv)

    check_opts: list[str] = []
    if args.auto_install:
        check_opts.append("--auto-install")
    if args.wheelhouse:
        check_opts.extend(["--wheelhouse", args.wheelhouse])

    check_env.main(check_opts)

    if args.port:
        os.environ["PORT"] = str(args.port)
        os.environ.setdefault("BUSINESS_HOST", f"http://localhost:{args.port}")

    # Configure the environment so the orchestrator picks up the ALPHA_ENABLED_AGENTS value at module import time.
    if not os.getenv("ALPHA_ENABLED_AGENTS"):
        os.environ["ALPHA_ENABLED_AGENTS"] = ",".join(
            [
                "IncorporatorAgent",
                "AlphaDiscoveryAgent",
                "AlphaOpportunityAgent",
                "AlphaExecutionAgent",
                "AlphaRiskAgent",
                "AlphaComplianceAgent",
                "AlphaPortfolioAgent",
                "PlanningAgent",
                "ResearchAgent",
                "StrategyAgent",
                "MarketAnalysisAgent",
                "MemoryAgent",
                "SafetyAgent",
            ]
        )

    from alpha_factory_v1.demos.alpha_agi_business_v1 import alpha_agi_business_v1

    if args.bridge:
        host = os.getenv("BUSINESS_HOST", f"http://localhost:{args.port}")
        os.environ["AGENTS_RUNTIME_PORT"] = str(args.runtime_port)
        _start_bridge(host, args.runtime_port)

    if args.open_ui:
        url = os.getenv("BUSINESS_HOST", f"http://localhost:{args.port}") + "/docs"
        _open_browser_when_ready(url)

    alpha_agi_business_v1.main()


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
