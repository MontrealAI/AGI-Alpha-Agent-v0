# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
#!/usr/bin/env python
# alpha_factory_v1/demos/era_of_experience/agent_experience_entrypoint.py
# © 2025 MONTREAL.AI – Apache-2.0 License
"""
Era-of-Experience Agent 👁️✨
────────────────────────────
A minimal yet *comprehensive* reference implementation of an **autonomous,
reward-grounded, life-long agent** as envisioned in “Welcome to the Era of Experience”
(Sutton & Silver 2024)

✓ Streams of experience (continuous event generator)
✓ Sensor-motor tools (search, meal planning, workout scheduling)
✓ Grounded reward (fitness & knowledge signals, *no* human grading)
✓ Non-human reasoning (MCTS planning + vector memory)

The script runs **online** (OPENAI_API_KEY) *or* **offline** (Ollama Mixtral) and
spawns a Gradio dashboard on `http://localhost:7860`.

Run locally:

    pip install -U openai_agents gradio rich pretty_errors
    python agent_experience_entrypoint.py

Environment vars (optional):

    OPENAI_API_KEY      – use OpenAI cloud LLM
    MODEL_NAME          – default gpt-4o-mini
    TEMPERATURE         – default 0.2
    LIVE_FEED           – 1 to mix in real wearable/web data
    LOGLEVEL           – default INFO
"""
from __future__ import annotations
import os
import asyncio
import random
import datetime as dt
import json
import logging
import math
import re
from typing import Dict, Any, AsyncIterator, Callable, TypeVar

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn

try:  # gradio may be absent in minimal environments
    import gradio as gr
except ImportError:  # pragma: no cover - optional dependency
    gr = None
try:  # optional for tests
    from openai_agents import Agent, OpenAIAgent, Tool, memory
except ImportError:  # pragma: no cover - allow import without package
    Agent = OpenAIAgent = Tool = memory = None
    _NO_OPENAI_AGENTS = True
else:
    _NO_OPENAI_AGENTS = False

if Tool is None:
    F = TypeVar("F", bound=Callable[..., Any])

    def Tool(*_args: Any, **_kwargs: Any) -> Callable[[F], F]:  # noqa: D401 - simple passthrough decorator
        """Fallback no-op decorator when openai_agents is unavailable."""

        def _wrap(func: F) -> F:
            return func

        return _wrap


from .alpha_detection import (
    detect_yield_curve_alpha,
    detect_supply_chain_alpha,
)

# ───────────────────────────── configuration ────────────────────────────────
MODEL = os.getenv("MODEL_NAME", "gpt-4o-mini")
TEMP = float(os.getenv("TEMPERATURE", "0.2"))
LIVE_FEED = bool(int(os.getenv("LIVE_FEED", "0")))
PORT = int(os.getenv("PORT", "7860"))
LOG_LVL = os.getenv("LOGLEVEL", "INFO").upper()
STREAM_RATE = float(os.getenv("STREAM_RATE_HZ", "1"))

logging.basicConfig(
    level=LOG_LVL,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)


# ───────────────────────────── experience stream ────────────────────────────
async def experience_stream() -> AsyncIterator[Dict[str, Any]]:
    """
    Asynchronous generator producing perpetual experience events.
    If LIVE_FEED = 1 it *could* be wired to real APIs/wearables; here we
    synthesise plausible telemetry for demo purposes.
    Event schema
    ------------
    {
        id:         int,
        t:          ISO-8601,
        user:       str,
        kind:       {"health","learn","general"},
        payload:    dict            # free-form details
    }
    """
    uid = 0
    users = ["alice", "bob"]
    learn = ["Duolingo Spanish 10 min", "Khan Academy Calculus 15 min", "Read 'Nature' abstract"]
    health = ["Run 5 km", "Sleep 7 h 45 m", "Cycle 12 km", "Yoga 30 min"]

    rate = float(os.getenv("STREAM_RATE_HZ", str(STREAM_RATE)))
    if not math.isfinite(rate) or not 0 < rate <= 1000:
        raise ValueError("STREAM_RATE_HZ must be finite and greater than 0, at most 1000")
    period = 1.0 / rate
    while True:
        uid += 1
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        if random.random() < 0.6:
            kind, payload = "health", {"activity": random.choice(health)}
        else:
            kind, payload = "learn", {"session": random.choice(learn)}
        evt = {"id": uid, "t": now, "user": random.choice(users), "kind": kind, "payload": payload}
        yield evt
        await asyncio.sleep(period)


# ────────────────────────────── sensor-motor tools ──────────────────────────
@Tool("web_search", "Search the public web and return the top URL.")
async def web_search(q: str) -> Dict[str, str]:
    return {"top_result": f"https://duckduckgo.com/?q={q.replace(' ','+')}"}


@Tool("plan_meal", "Craft a low-carb meal plan for a target kcal.")
async def plan_meal(target_kcal: int = 600) -> Dict[str, str]:
    menu = f"Grilled salmon + spinach salad ({target_kcal} kcal)"
    return {"menu": menu}


@Tool("schedule_workout", "Generate a personalised workout block.")
async def schedule_workout(duration_min: int = 30, focus: str = "cardio") -> Dict[str, str]:
    return {"workout": f"{duration_min} min {focus} – warm-up · interval · cool-down"}


@Tool("detect_yield_curve_alpha", "Assess yield curve inversion using offline data.")
async def detect_yield_curve_alpha_tool() -> Dict[str, str]:
    msg = detect_yield_curve_alpha()
    return {"alpha": msg}


@Tool(
    "detect_supply_chain_alpha",
    "Check for potential supply-chain disruptions using offline data.",
)
async def detect_supply_chain_alpha_tool(threshold: float = 50.0) -> Dict[str, str]:
    msg = detect_supply_chain_alpha(threshold)
    return {"alpha": msg}


TOOLS = [
    web_search,
    plan_meal,
    schedule_workout,
    detect_yield_curve_alpha_tool,
    detect_supply_chain_alpha_tool,
]


# ─────────────────────────────── reward functions ───────────────────────────
def _fitness_reward(evt: Dict[str, Any]) -> float:
    act = evt["payload"].get("activity", "")
    if "Run" in act or "Cycle" in act or "Yoga" in act:
        return 1.0
    if "Sleep" in act:
        match = re.search(r"(\d+(?:\.\d+)?)\s*h", act)
        minutes = re.search(r"(\d+(?:\.\d+)?)\s*m", act)
        hrs = (float(match.group(1)) if match else 0.0) + (float(minutes.group(1)) / 60 if minutes else 0.0)
        return max(0, min(1.0, hrs / 8.0))
    return 0.0


def _education_reward(evt: Dict[str, Any]) -> float:
    if evt["kind"] != "learn":
        return 0.0
    match = re.search(r"(\d+(?:\.\d+)?)\s*min\b", str(evt.get("payload", {}).get("session", "")))
    minutes = float(match.group(1)) if match else 0.0
    return math.tanh(minutes / 20)  # 0→1 smooth


def grounded_reward(state: Dict[str, Any], action: str | None, evt: Dict[str, Any]) -> float:
    """Composite grounded reward (0-1)."""
    return 0.6 * _fitness_reward(evt) + 0.4 * _education_reward(evt)


# ─────────────────────────────── LLM & memory ───────────────────────────────
if OpenAIAgent is not None and memory is not None:
    LLM = OpenAIAgent(
        model=MODEL,
        temperature=TEMP,
        api_key=os.getenv("OPENAI_API_KEY") or None,
        base_url=os.getenv("LLM_BASE_URL", "http://ollama:11434/v1") if not os.getenv("OPENAI_API_KEY") else None,
    )

    VECTOR_STORE = memory.LocalQdrantMemory(
        collection_name="experience_mem",
        host=os.getenv("VECTOR_DB_URL", ":memory:"),
    )

    # ────────────────────────────── agent definition ────────────────────────────
    agent = Agent(
        llm=LLM,
        tools=TOOLS,
        memory=VECTOR_STORE,
        planning="mcts",
        reward_fn=grounded_reward,
        name="Era-Of-Experience-Agent",
    )
else:  # pragma: no cover - minimal mode for docs/tests
    LLM = VECTOR_STORE = agent = None


# ───────────────────────────── orchestrator loop ────────────────────────────
async def main() -> None:
    """
    • Feeds the stream to the agent
    • Shows a slim Gradio dashboard (memory + live reasoning)
    """
    if _NO_OPENAI_AGENTS:
        raise RuntimeError("OpenAI Agents SDK is required; install via 'pip install openai-agents'")
    if gr is None:
        raise RuntimeError("gradio is required for the demo UI; install via 'pip install gradio'")

    evt_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=128)

    async def ingest_loop() -> None:
        async for evt in experience_stream():
            logging.debug("Event %s", evt)
            # agent observes the world
            agent.observe(json.dumps(evt))
            # agent decides whether / how to act
            act = await agent.act()
            if evt_queue.full():
                evt_queue.get_nowait()
            evt_queue.put_nowait({"event": evt, "action": act})
            logging.info("Tool-call » %s", act)
            # mock tool latency
            await asyncio.sleep(0.2)

    # ── Gradio UI ───────────────────────────────────────────────────────────
    with gr.Blocks(title="Era-Of-Experience Agent") as ui:
        gr.Markdown("# ✨ Era-Of-Experience Agent")
        mem_view = gr.Dataframe(headers=["mem"])
        log_view = gr.Markdown()
        btn = gr.Button("Step once")

        async def step_once() -> tuple[list[list[str]], str]:
            record = await evt_queue.get()
            return [
                [json.dumps(m)[:120]] for m in agent.memory.recent(10)
            ], f"**Event:** {record['event']}\n\n**Action:** {record['action']}"

        btn.click(step_once, outputs=[mem_view, log_view])

    app = FastAPI()

    @app.get("/__live", response_class=PlainTextResponse, include_in_schema=False)
    async def _live() -> str:  # noqa: D401
        return "OK"

    gradio_app = gr.mount_gradio_app(app, ui, path="/")
    server = uvicorn.Server(
        uvicorn.Config(gradio_app, host="0.0.0.0", port=PORT, log_level=LOG_LVL.lower(), loop="asyncio")
    )

    tasks = [asyncio.create_task(ingest_loop()), asyncio.create_task(server.serve())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


# ──────────────────────────────── entrypoint ────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Graceful shutdown requested – bye 👋")
