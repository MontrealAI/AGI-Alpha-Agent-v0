# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
# NOTE: This demo is a research prototype and does not implement real AGI.
"""OpenAI Agents SDK bridge for the alpha_agi_business_v1 demo.

This utility registers a small helper agent that interacts with the
local orchestrator. It works offline when no API key is configured.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict

# allow running this script directly from its folder
SCRIPT_DIR = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:  # prefer httpx when available
    from httpx import AsyncClient, ConnectError  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - offline shim
    from alpha_factory_v1 import af_requests as requests  # type: ignore

    class AsyncClient:  # type: ignore
        """Minimal async wrapper around the sync af_requests API."""

        async def __aenter__(self) -> "AsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return False

        async def get(self, url: str, **kwargs):
            return requests.get(url, **kwargs)

        async def post(self, url: str, **kwargs):
            return requests.post(url, **kwargs)

    ConnectError = requests.RequestException  # type: ignore


# ---------------------------------------------------------------------------
# Lazy dependency bootstrap
# ---------------------------------------------------------------------------
def _require_openai_agents() -> bool:
    """Ensure the ``openai_agents`` package is available.

    Attempts an automatic install via :mod:`check_env` when the package is
    missing so the bridge remains usable in fresh environments or Colab
    runtimes.  Returns ``True`` when the package can be imported, ``False``
    otherwise without raising ``SystemExit``.  This allows the demo to run in
    fully offline environments where installation may fail.
    """

    try:  # soft dependency
        import openai_agents  # type: ignore

        return True
    except ModuleNotFoundError:  # pragma: no cover - optional dep
        try:
            import check_env

            print("ℹ️  openai_agents missing – attempting auto-install…")
            check_env.main(["--auto-install"])
            import openai_agents  # type: ignore  # noqa: F401

            return True
        except Exception as exc:  # pragma: no cover - install failed
            sys.stderr.write(f"\n⚠️  openai_agents unavailable: {exc}\n")
            if isinstance(exc, ConnectError):
                sys.stderr.write(
                    "   Network appears unreachable. Install 'openai_agents' "
                    "manually or provide a local wheel via WHEELHOUSE.\n"
                )
            sys.stderr.write("   Continuing without OpenAI Agents bridge.\n")
            return False


_OPENAI_AGENTS_AVAILABLE = _require_openai_agents()
if _OPENAI_AGENTS_AVAILABLE:
    from openai_agents import Agent, AgentRuntime, Tool  # type: ignore
else:  # pragma: no cover - offline fallback
    Agent = object  # type: ignore

    class AgentRuntime:  # type: ignore
        def __init__(self, *a, **kw) -> None:
            pass

        def register(self, *a, **kw) -> None:
            pass

        def run(self) -> None:
            print("OpenAI Agents bridge disabled.")

    def Tool(*_args, **_kw):  # type: ignore
        def _decorator(func):
            return func

        return _decorator


try:
    # Optional ADK bridge
    from alpha_factory_v1.backend.adk_bridge import auto_register, maybe_launch

    ADK_AVAILABLE = True
except ImportError:  # pragma: no cover - ADK not installed
    ADK_AVAILABLE = False

HOST = os.getenv("BUSINESS_HOST", "http://localhost:8000")
AGENT_PORT = int(os.getenv("AGENTS_RUNTIME_PORT", "5001"))
HEADERS: Dict[str, str] = {}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expose alpha_agi_business_v1 via OpenAI Agents runtime")
    parser.add_argument(
        "--host",
        default=HOST,
        help="Orchestrator host URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=AGENT_PORT,
        help=f"Port for the Agents runtime (default: {AGENT_PORT})",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for orchestrator readiness",
    )
    parser.add_argument(
        "--wait-secs",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="How long to wait for orchestrator health check (default: 5)",
    )
    parser.add_argument(
        "--token",
        help="REST API bearer token (defaults to API_TOKEN env var)",
    )
    parser.add_argument(
        "--open-ui",
        action="store_true",
        help="Open the Agents runtime URL in the default browser",
    )
    return parser.parse_args(argv)


@Tool(name="list_agents", description="List active orchestrator agents")
async def list_agents() -> list[str]:
    async with AsyncClient() as client:
        resp = await client.get(f"{HOST}/agents", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return resp.json()


@Tool(name="trigger_discovery", description="Trigger the AlphaDiscoveryAgent")
async def trigger_discovery() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/alpha_discovery/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "alpha_discovery queued"


@Tool(name="trigger_opportunity", description="Trigger the AlphaOpportunityAgent")
async def trigger_opportunity() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/alpha_opportunity/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "alpha_opportunity queued"


@Tool(
    name="trigger_best_alpha",
    description="Explain required inputs before evaluating a ranked demo opportunity",
)
async def trigger_best_alpha() -> str:
    """Fail closed: ranking scores do not supply cost, benefit or loss assumptions."""
    raise ValueError(
        "Bundled score-only opportunities cannot be submitted for business evaluation. "
        "Use submit_job with agent='alpha_execution' and a state containing budget, "
        "max_loss and opportunities with id, cost, benefit and worst_loss. "
        "Nothing was queued or executed."
    )


@Tool(name="trigger_execution", description="Trigger the AlphaExecutionAgent")
async def trigger_execution() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/alpha_execution/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "alpha_execution queued"


@Tool(name="trigger_risk", description="Trigger the AlphaRiskAgent")
async def trigger_risk() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/alpha_risk/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "alpha_risk queued"


@Tool(name="trigger_compliance", description="Trigger the AlphaComplianceAgent")
async def trigger_compliance() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/alpha_compliance/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "alpha_compliance queued"


@Tool(name="trigger_portfolio", description="Trigger the AlphaPortfolioAgent")
async def trigger_portfolio() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/alpha_portfolio/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "alpha_portfolio queued"


@Tool(name="trigger_planning", description="Trigger the PlanningAgent")
async def trigger_planning() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/planning/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "planning queued"


@Tool(name="trigger_research", description="Trigger the ResearchAgent")
async def trigger_research() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/research/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "research queued"


@Tool(name="trigger_strategy", description="Trigger the StrategyAgent")
async def trigger_strategy() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/strategy/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "strategy queued"


@Tool(name="trigger_market_analysis", description="Trigger the MarketAnalysisAgent")
async def trigger_market_analysis() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/market_analysis/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "market_analysis queued"


@Tool(name="trigger_memory", description="Trigger the MemoryAgent")
async def trigger_memory() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/memory/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "memory queued"


@Tool(name="trigger_safety", description="Trigger the SafetyAgent")
async def trigger_safety() -> str:
    async with AsyncClient() as client:
        resp = await client.post(f"{HOST}/agent/safety/trigger", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return "safety queued"


@Tool(name="check_health", description="Return orchestrator health status")
async def check_health() -> str:
    """Check orchestrator /healthz endpoint."""
    async with AsyncClient() as client:
        resp = await client.get(f"{HOST}/healthz", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return resp.text


@Tool(
    name="submit_job",
    description="Evaluate a supplied Business1 state without queuing or external actions",
)
async def submit_job(job: dict) -> str:
    """Accept exactly {agent: 'alpha_execution', state: <business input>}.

    The authenticated endpoint evaluates this state synchronously; a scheduling
    acknowledgement is never treated as evaluation or execution evidence.
    """
    if not isinstance(job, dict) or set(job) != {"agent", "state"} or job["agent"] != "alpha_execution":
        raise ValueError("submit_job requires agent='alpha_execution' and a complete state object")
    from alpha_factory_v1.demos.alpha_agi_business_v1.evaluation import evaluate_submission

    # Validate locally too and bind the response to the exact input digest.
    expected = evaluate_submission(json.dumps(job["state"], allow_nan=False).encode("utf-8"))
    async with AsyncClient() as client:
        resp = await client.post(
            f"{HOST}/agent/alpha_execution/evaluate",
            json=job["state"],
            headers=HEADERS,
            timeout=5,
        )
    resp.raise_for_status()
    result = resp.json()
    if (
        not isinstance(result, dict)
        or result.get("status") != "evaluated_supplied_assumptions"
        or result.get("input_id") != expected["input_id"]
        or result.get("external_actions_performed") is not False
        or result.get("evaluation") != expected["evaluation"]
    ):
        raise RuntimeError("Server response does not match the submitted-input evaluation")
    return json.dumps(result, sort_keys=True)


@Tool(
    name="recent_alpha",
    description="Return recently discovered alpha opportunities",
)
async def recent_alpha(limit: int = 5) -> list[str]:
    """Fetch the latest alpha items from the orchestrator memory."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"{HOST}/memory/alpha_opportunity/recent",
            params={"n": limit},
            headers=HEADERS,
            timeout=5,
        )
    resp.raise_for_status()
    return resp.json()


@Tool(
    name="search_memory",
    description="Search orchestrator memory for a text query",
)
async def search_memory(query: str, limit: int = 5) -> list[str]:
    """Query the orchestrator memory vector store."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"{HOST}/memory/search",
            params={"q": query, "k": limit},
            headers=HEADERS,
            timeout=5,
        )
    resp.raise_for_status()
    return resp.json()


@Tool(
    name="fetch_logs",
    description="Return recent orchestrator log lines",
)
async def fetch_logs() -> list[str]:
    """Retrieve the latest orchestrator logs via the REST API."""
    async with AsyncClient() as client:
        resp = await client.get(f"{HOST}/api/logs", headers=HEADERS, timeout=5)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
#  Action dispatch helpers
# ---------------------------------------------------------------------------
POLICY_MAP: Dict[str, Callable[[dict], Awaitable[Any]]] = {
    "discover": lambda _o: trigger_discovery(),
    "opportunity": lambda _o: trigger_opportunity(),
    "best_alpha": lambda _o: trigger_best_alpha(),
    "execute": lambda _o: trigger_execution(),
    "risk": lambda _o: trigger_risk(),
    "compliance": lambda _o: trigger_compliance(),
    "portfolio": lambda _o: trigger_portfolio(),
    "planning": lambda _o: trigger_planning(),
    "research": lambda _o: trigger_research(),
    "strategy": lambda _o: trigger_strategy(),
    "market_analysis": lambda _o: trigger_market_analysis(),
    "memory": lambda _o: trigger_memory(),
    "safety": lambda _o: trigger_safety(),
    "health": lambda _o: check_health(),
    "recent_alpha": lambda _o: recent_alpha(),
    "search_memory": lambda o: search_memory(o.get("query", ""), int(o.get("limit", 5))),
    "fetch_logs": lambda _o: fetch_logs(),
    "submit_job": lambda o: submit_job(o.get("job", {})),
}


async def wait_ready(url: str, timeout: float = 5.0) -> None:
    """Block until the orchestrator healthcheck responds or timeout expires."""
    deadline = time.monotonic() + timeout
    async with AsyncClient() as client:
        while time.monotonic() < deadline:
            try:
                resp = await client.get(f"{url}/healthz", headers=HEADERS, timeout=1)
                if resp.status_code == 200:
                    return
            except Exception:
                await asyncio.sleep(0.2)
    raise RuntimeError(f"Orchestrator not reachable at {url}")


class BusinessAgent(Agent):
    """Tiny agent exposing orchestrator helper tools.

    The helper surfaces a curated set of REST endpoints via the
    OpenAI Agents runtime and optional ADK gateway.  It also supports
    vector memory search for quick retrieval of stored alpha.
    """

    name = "business_helper"
    tools = [
        list_agents,
        trigger_discovery,
        trigger_opportunity,
        trigger_best_alpha,
        trigger_execution,
        trigger_risk,
        trigger_compliance,
        trigger_portfolio,
        trigger_planning,
        trigger_research,
        trigger_strategy,
        trigger_market_analysis,
        trigger_memory,
        trigger_safety,
        check_health,
        recent_alpha,
        search_memory,
        fetch_logs,
        submit_job,
    ]

    async def policy(self, obs, ctx):  # type: ignore[override]
        if isinstance(obs, dict):
            action = obs.get("action")
            handler = POLICY_MAP.get(action)
            if handler:
                return await handler(obs)
        return await self.tools.list_agents()


def main() -> None:
    if not _OPENAI_AGENTS_AVAILABLE:
        print("OpenAI Agents SDK not available; bridge inactive.")
        return

    args = _parse_args()
    global HOST
    HOST = args.host
    global HEADERS
    token = args.token or os.getenv("API_TOKEN")
    HEADERS = {"Authorization": f"Bearer {token}"} if token else {}
    api_key = os.getenv("OPENAI_API_KEY") or None
    if not args.no_wait:
        try:
            asyncio.run(wait_ready(HOST, timeout=args.wait_secs))
        except RuntimeError as exc:
            sys.stderr.write(f"\n⚠️  {exc}\n")
            if api_key is None:
                sys.stderr.write("   continuing in offline mode...\n")
            else:
                sys.exit(1)
    runtime = AgentRuntime(api_key=api_key, port=args.port)
    agent = BusinessAgent()
    runtime.register(agent)
    print(f"Registered BusinessAgent -> {HOST} [port {args.port}]")
    if args.open_ui:
        url = f"http://localhost:{args.port}/v1/agents"
        try:
            import webbrowser

            webbrowser.open(url, new=1)
        except webbrowser.Error:
            print(f"Open {url} to access the Agents runtime")

    if ADK_AVAILABLE:
        auto_register([agent])
        maybe_launch()
        print("BusinessAgent exposed via ADK gateway")

    runtime.run()


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
