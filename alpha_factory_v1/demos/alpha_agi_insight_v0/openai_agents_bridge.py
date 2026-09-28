# SPDX-License-Identifier: Apache-2.0
"""Optional legacy runtime compatibility interface; local search is the default."""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
from typing import Any

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

from .insight_demo import offline_requested, parse_sectors, run

DEFAULT_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o")
FALLBACK_MODE_PREFIX = "fallback_mode_active: "
has_oai = False


def _truthy(value: bool | str | None) -> bool:
    return value is True or isinstance(value, str) and value.lower() in {"1", "true", "yes", "on"}


def banner() -> str:
    return "🎖️ α-AGI Insight 👁️✨ — local research demo; scores are not forecasts"


def print_banner() -> None:
    print(banner())


def refresh_runtime_availability() -> bool:
    global has_oai
    has_oai = False
    if offline_requested() or not os.getenv("OPENAI_API_KEY") or _truthy(os.getenv("OPENAI_AGENTS_DISABLE")):
        return False
    try:
        module = importlib.import_module("openai_agents")
        has_oai = (
            all(callable(getattr(getattr(module, "AgentRuntime", None), name, None)) for name in ("register", "run"))
            and isinstance(getattr(module, "Agent", None), type)
            and callable(getattr(module, "Tool", None))
        )
    except (ImportError, AttributeError):
        pass
    return has_oai


async def run_insight_search(
    episodes: int = 5,
    target: int = 3,
    model: str | None = None,
    rewriter: str | None = None,
    sectors: str | None = None,
    log_dir: str | None = None,
    exploration: float | None = None,
    seed: int | None = None,
    json_output: bool | None = None,
) -> str:
    result = run(
        episodes=episodes,
        target=target,
        model=model,
        rewriter=rewriter,
        log_dir=Path(log_dir) if log_dir else None,
        exploration=1.4 if exploration is None else exploration,
        seed=seed,
        sectors=parse_sectors(None, sectors, allow_files=False, use_env=False),
        json_output=_truthy(json_output),
    )
    return result if _truthy(json_output) or has_oai else FALLBACK_MODE_PREFIX + result


def _run_runtime(
    episodes: int,
    target: int,
    model: str | None = None,
    rewriter: str | None = None,
    log_dir: str | None = None,
    sectors: str | None = None,
    exploration: float | None = None,
    seed: int | None = None,
    json_output: bool | None = None,
    *,
    adk_host: str | None = None,
    adk_port: int | None = None,
) -> None:
    if not refresh_runtime_availability():
        raise ValueError("Legacy runtime interface is unavailable; use the local CLI")
    if adk_port is not None and not 1 <= adk_port <= 65535:
        raise ValueError("ADK port must be from 1 through 65535")
    module = importlib.import_module("openai_agents")
    defaults = dict(
        episodes=episodes,
        target=target,
        model=model,
        rewriter=rewriter,
        log_dir=log_dir,
        sectors=sectors,
        exploration=exploration,
        seed=seed,
        json_output=json_output,
    )
    tool = module.Tool(name="run_insight_search", description="Bounded numeric-target search illustration")(
        run_insight_search
    )

    class InsightAgent(module.Agent):
        name = "agi_insight_helper"
        tools = [tool]

        async def policy(self, obs: Any, _ctx: Any) -> str:
            params = dict(defaults)
            if isinstance(obs, dict):
                if set(obs) - set(params):
                    raise ValueError("Unknown search parameter")
                params.update(obs)
            # Tool requests cannot supply a server filesystem path or output destination.
            if isinstance(obs, dict) and "log_dir" in obs:
                raise ValueError("Runtime requests cannot choose server output paths")
            return await run_insight_search(**params)

    agent = InsightAgent()
    runtime = module.AgentRuntime(api_key=os.getenv("OPENAI_API_KEY"))
    runtime.register(agent)
    if _truthy(os.getenv("ALPHA_FACTORY_ENABLE_ADK")):
        from alpha_factory_v1.backend import adk_bridge

        adk_bridge.auto_register([agent])
        adk_bridge.maybe_launch(host=adk_host, port=adk_port)
    runtime.run()


def main(argv: list[str] | None = None) -> None:
    from .official_demo_final import main as launch

    launch(argv)


if __name__ == "__main__":
    main()
