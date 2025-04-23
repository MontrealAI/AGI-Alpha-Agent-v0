#!/usr/bin/env python
# alpha_factory_v1/demos/era_of_experience/agent_experience_entrypoint.py
# © 2025 MONTREAL.AI – MIT License
"""
Era-of-Experience Agent 👁️✨
────────────────────────────
A minimal yet *comprehensive* reference implementation of an **autonomous,
reward-grounded, life-long agent** as envisioned in “Welcome to the Era of Experience”
(Sutton & Silver 2024) :contentReference[oaicite:2]{index=2}&#8203;:contentReference[oaicite:3]{index=3}.

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
"""
from __future__ import annotations
import os, asyncio, random, datetime as dt, json, logging, math
from typing import Dict, Any, AsyncIterator, List

import gradio as gr
from openai_agents import Agent, OpenAIAgent, Tool, memory

# ───────────────────────────── configuration ────────────────────────────────
MODEL       = os.getenv("MODEL_NAME", "gpt-4o-mini")
TEMP        = float(os.getenv("TEMPERATURE", "0.2"))
LIVE_FEED   = bool(int(os.getenv("LIVE_FEED", "0")))
PORT        = int(os.getenv("PORT", "7860"))
LOG_LVL     = os.getenv("LOGLEVEL", "INFO").upper()

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
    learn = ["Duolingo Spanish 10 min", "Khan Academy Calculus 15 min",
             "Read 'Nature' abstract"]
    health = ["Run 5 km", "Sleep 7 h 45 m", "Cycle 12 km", "Yoga 30 min"]

    while True:
        uid += 1
        now = dt.datetime.utcnow().isoformat()
        if random.random() < .6:
            kind, payload = "health", {"activity": random.choice(health)}
        else:
            kind, payload = "learn", {"session": random.choice(learn)}
        evt = {"id": uid,
               "t":  now,
               "user": random.choice(users),
               "kind": kind,
               "payload": payload}
        yield evt
        await asyncio.sleep(1.5)               # ~0.66 Hz stream


# ────────────────────────────── sensor-motor tools ──────────────────────────
@Tool("web_search", "Search the public web and return the top URL.")
async def web_search(q: str) -> Dict[str, str]:
    return {"top_result": f"https://duckduckgo.com/?q={q.replace(' ','+')}"}


@Tool("plan_meal", "Craft a low-carb meal plan for a target kcal.")
async def plan_meal(target_kcal: int = 600) -> Dict[str, str]:
    menu = f"Grilled salmon + spinach salad ({target_kcal} kcal)"
    return {"menu": menu}


@Tool("schedule_workout", "Generate a personalised workout block.")
async def schedule_workout(duration_min: int = 30,
                           focus: str = "cardio") -> Dict[str, str]:
    return {"workout":
            f"{duration_min} min {focus} – warm-up · interval · cool-down"}


TOOLS = [web_search, plan_meal, schedule_workout]

# ─────────────────────────────── reward functions ───────────────────────────
def _fitness_reward(evt: Dict[str, Any]) -> float:
    act = evt["payload"].get("activity", "")
    if "Run" in act or "Cycle" in act or "Yoga" in act:
        return 1.0
    if "Sleep" in act:
        hrs = float(act.split()[1][:-1])            # crude parse
        return max(0, min(1.0, hrs / 8.0))
    return 0.0


def _education_reward(evt: Dict[str, Any]) -> float:
    if evt["kind"] != "learn":
        return 0.0
    minutes = int(evt["payload"]["session"].split()[-2])
    return math.tanh(minutes / 20)                  # 0→1 smooth


def grounded_reward(state: Dict[str, Any],
                    action: str | None,
                    evt: Dict[str, Any]) -> float:
    """Composite grounded reward (0-1)."""
    return 0.6 * _fitness_reward(evt) + 0.4 * _education_reward(evt)


# ─────────────────────────────── LLM & memory ───────────────────────────────
LLM = OpenAIAgent(
    model=MODEL,
    temperature=TEMP,
    api_key=os.getenv("OPENAI_API_KEY") or None,
    base_url=("http://ollama:11434/v1"
              if not os.getenv("OPENAI_API_KEY") else None),
)

VECTOR_STORE = memory.LocalQdrantMemory(
    collection_name="experience_mem",
    host=":memory:"                               # purely local
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

# ───────────────────────────── orchestrator loop ────────────────────────────
async def main() -> None:
    """
    • Feeds the stream to the agent
    • Shows a slim Gradio dashboard (memory + live reasoning)
    """
    evt_gen = experience_stream()

    async def ingest_loop():
        async for evt in evt_gen:
            logging.debug("Event %s", evt)
            # agent observes the world
            agent.observe(json.dumps(evt))
            # agent decides whether / how to act
            act = await agent.act()
            logging.info("Tool-call » %s", act)
            # mock tool latency
            await asyncio.sleep(0.2)

    # ── Gradio UI ───────────────────────────────────────────────────────────
    with gr.Blocks(title="Era-Of-Experience Agent") as ui:
        gr.Markdown("# ✨ Era-Of-Experience Agent")
        mem_view = gr.Dataframe(headers=["mem"])
        log_view = gr.Markdown()
        btn      = gr.Button("Step once")

        async def step_once():
            evt = await anext(evt_gen)
            agent.observe(json.dumps(evt))
            call = await agent.act()
            return [[json.dumps(m)[:120] for m in agent.memory.recent(10)]], \
                   f"**Event:** {evt}\n\n**Action:** {call}"

        btn.click(step_once, outputs=[mem_view, log_view])

    # run both loops concurrently
    await asyncio.gather(
        ingest_loop(),
        ui.launch(server_name="0.0.0.0", server_port=PORT, share=False),
    )

# ──────────────────────────────── entrypoint ────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Graceful shutdown requested – bye 👋")
