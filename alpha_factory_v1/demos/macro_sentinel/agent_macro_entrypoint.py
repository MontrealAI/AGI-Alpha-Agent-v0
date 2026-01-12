# SPDX-License-Identifier: Apache-2.0
# alpha_factory_v1/demos/macro_sentinel/agent_macro_entrypoint.py
# © 2025 MONTREAL.AI Apache-2.0 License
"""
Macro-Sentinel entry-point
══════════════════════════
An Agentic pipeline that
1. ingests macro telemetry (offline CSV or live APIs),
2. Monte-Carlo-prices equity risk,
3. sizes a hedge,
4. explains its reasoning in prose.

OpenAI key present  → GPT-4o
No key             → Mixtral via Ollama (offline)

Deploy via Docker (run_macro_demo.sh) or directly:
    python agent_macro_entrypoint.py

This research prototype provides no financial advice.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from urllib import request
from typing import Any, AsyncIterator, Tuple, TYPE_CHECKING, cast

if TYPE_CHECKING:  # pragma: no cover - typing only
    import gradio as gr
    import pandas as pd
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn

try:
    from openai_agents import Agent, OpenAIAgent, Tool
except Exception as exc:  # pragma: no cover - optional dependency
    class Agent:  # type: ignore[no-redef]
        def __init__(self, *_a: Any, **_kw: Any) -> None:
            self.name = _kw.get("name", "agent")

    class OpenAIAgent:  # type: ignore[no-redef]
        def __init__(self, *_a: Any, **_kw: Any) -> None:
            pass

        def __call__(self, *_a: Any, **_kw: Any) -> str:
            return ""

    def Tool(*_a: Any, **_kw: Any):  # type: ignore[no-redef]
        def _decorator(func: Any) -> Any:
            return func

        return _decorator

    _ = exc
from .data_feeds import stream_macro_events
from .simulation_core import MonteCarloSimulator


def _check_ollama(url: str) -> None:
    """Verify an Ollama server is reachable."""
    base = url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    try:
        request.urlopen(f"{base}/api/tags", timeout=3)
    except Exception as exc:  # pragma: no cover - network check
        raise RuntimeError(
            f"Ollama not reachable at {base}. " "Install it from https://ollama.com and run 'ollama serve'."
        ) from exc


# ─────────────────────────── LLM bridge ─────────────────────────────
if os.getenv("OPENAI_API_KEY"):
    base_url = None
else:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")

LLM = OpenAIAgent(
    model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
    api_key=os.getenv("OPENAI_API_KEY") or None,
    base_url=base_url,
    temperature=float(os.getenv("TEMPERATURE", 0.15)),
)

# ─────────────────────────── Globals ────────────────────────────────
PORTFOLIO_USD: float = float(os.getenv("DEFAULT_PORTFOLIO_USD", "2000000"))
LIVE_FEED: bool = bool(int(os.getenv("LIVE_FEED", "0")))
simulator: MonteCarloSimulator = MonteCarloSimulator()
event_iter: AsyncIterator[dict[str, Any]] = stream_macro_events(live=LIVE_FEED)


# ─────────────────────────── Tools ──────────────────────────────────
@Tool("macro_event", "Stream the newest macro telemetry event.")  # type: ignore[misc]
async def macro_event() -> dict[str, Any]:
    """Return the next macro event from the feed.

    Returns:
        Dictionary describing the latest macro telemetry event.
    """
    return await anext(event_iter)


@Tool("mc_risk", "Run Monte-Carlo risk. Returns hedge + scenario table.")  # type: ignore[misc]
async def mc_risk(event: dict[str, Any], portfolio: float = PORTFOLIO_USD) -> dict[str, Any]:
    """Run risk simulation and size a hedge.

    Args:
        event: Latest macro event used for the simulation.
        portfolio: Portfolio value in USD.

    Returns:
        Dictionary with hedging information and return scenarios.
    """
    factors = simulator.simulate(event)
    hedge = simulator.hedge(factors, portfolio)
    scen = simulator.scenario_table(factors).to_dict(orient="records")
    return {"hedge": hedge, "scenarios": scen}


@Tool("order_stub", "Draft a JSON order for Micro-ES future.")  # type: ignore[misc]
async def order_stub(hedge: dict[str, Any]) -> dict[str, Any]:
    """Create a stub futures order based on the hedge.

    Args:
        hedge: Hedge dictionary from :func:`mc_risk`.

    Returns:
        Order parameters for a market trade in Micro‑ES.
    """
    notional = hedge["es_notional"]
    side = "SELL" if notional > 0 else "BUY"
    qty = max(int(abs(notional) // 50_000), 1)  # 50 k USD ≈ 1 MES
    return {"symbol": "MES", "qty": qty, "side": side, "type": "MKT"}


@Tool("explain", "Narrate risk & hedge for a PM.")  # type: ignore[misc]
async def explain(event: dict[str, Any], hedge: dict[str, Any]) -> str:
    """Explain the hedge rationale in prose.

    Args:
        event: Macro event driving the risk calculation.
        hedge: Hedge dictionary produced by :func:`mc_risk`.

    Returns:
        Short narrative describing the hedge decision.
    """
    prompt = (
        "You are a risk officer. In ~150 words, explain to a portfolio "
        "manager why the hedge below is sensible.\n\n"
        f"Event:\n```json\n{json.dumps(event, indent=2)}\n```\n"
        f"Hedge:\n```json\n{json.dumps(hedge, indent=2)}\n```"
    )
    return cast(str, LLM(prompt))


# ─────────────────────────── Agent ──────────────────────────────────
try:
    sentinel = Agent(name="Macro-Sentinel", llm=LLM, tools=[macro_event, mc_risk, order_stub, explain])
except TypeError:  # pragma: no cover - fallback for minimal stubs
    class _StubAgent:
        def __init__(self, name: str) -> None:
            self.name = name

    sentinel = _StubAgent("Macro-Sentinel")

# Optionally expose via Google ADK (Agent-to-Agent federation)
try:  # pragma: no cover - optional dependency
    from alpha_factory_v1.backend import adk_bridge

    adk_bridge.auto_register([sentinel])
    adk_bridge.maybe_launch()
except Exception:
    pass


# ─────────────────────────── Gradio UI ──────────────────────────────
async def launch_ui() -> None:
    try:
        import gradio as gr  # type: ignore
        import pandas as pd  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime check
        raise RuntimeError(
            "Required packages missing. Run 'python ../../check_env.py --demo macro_sentinel --auto-install'"
        ) from exc

    if base_url:
        _check_ollama(base_url)

    with gr.Blocks(title="Macro-Sentinel") as ui:
        gr.Markdown("## 📈 Macro-Sentinel — real-time macro risk radar")

        col1, col2 = gr.Row().children
        event_box = gr.Json(label="Latest macro event", elem_id="evt")
        scen_df = gr.Dataframe(label="Return scenarios (P50/P95/P99)")

        metrics_md = gr.Markdown()
        story_md = gr.Markdown()
        run_btn = gr.Button("🔄 Run Sentinel Cycle")

        async def cycle() -> Tuple[dict[str, Any], pd.DataFrame, str, str]:
            event = await macro_event()
            risk = await mc_risk(event, PORTFOLIO_USD)
            hedge = risk["hedge"]
            story = await explain(event, hedge)
            scen_df = pd.DataFrame(risk["scenarios"])

            metric = (
                f"**VaR 5 %:** {hedge['metrics']['var']:.2%} &nbsp;&nbsp;"
                f"**CVaR 5 %:** {hedge['metrics']['cvar']:.2%} &nbsp;&nbsp;"
                f"**Skew:** {hedge['metrics']['skew']:.2f}<br>"
                f"**ES notional:** ${hedge['es_notional']:,.0f}  "
                f"(Micro-ES qty ≈ {abs(int(hedge['es_notional']//50_000))})"
            )

            return event, scen_df, metric, story

        run_btn.click(cycle, outputs=[event_box, scen_df, metrics_md, story_md])

    fast = FastAPI()

    @fast.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)  # type: ignore[misc]
    async def _health() -> str:  # noqa: D401
        return "ok"

    gr_app = gr.mount_gradio_app(fast, ui, path="/")
    server = uvicorn.Server(uvicorn.Config(gr_app, host="0.0.0.0", port=7864, loop="asyncio"))
    await server.serve()


# ─────────────────────────── Main ───────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(launch_ui())
    finally:
        # tidy aiohttp session if running outside Docker
        from .data_feeds import aiohttp, _SESSION

        if (s := _SESSION) and isinstance(s, aiohttp.ClientSession):
            with contextlib.suppress(Exception):
                asyncio.run(s.close())
