# SPDX-License-Identifier: Apache-2.0
"""
MuZero Planning demo – Cross‑industry Alpha‑Factory illustration.
Runs a lightweight MuZero agent (MiniMu) on Gymnasium’s CartPole‑v1
(or ``$MUZERO_ENV_ID``) and streams a live Gradio dashboard
on ``$HOST_PORT`` (default 7861).

Core algorithm follows the public pseudocode from Schrittwieser et al. (2020)
but trimmed to <300 LoC for pedagogy.
"""

import os
import sys
from typing import Any

# Optional Google ADK gateway for Agent-to-Agent federation
try:
    from alpha_factory_v1.backend import adk_bridge

    if not getattr(adk_bridge, "_ADK_OK", True):
        print(
            "Google ADK not installed. Install with: pip install google-adk \n"
            "and set ALPHA_FACTORY_ENABLE_ADK=true to enable the gateway.",
            file=sys.stderr,
        )
except Exception:  # pragma: no cover - optional dependency
    adk_bridge = None
    print(
        "Google ADK integration unavailable. Install with: pip install google-adk "
        "and set ALPHA_FACTORY_ENABLE_ADK=true to enable the gateway.",
        file=sys.stderr,
    )


try:  # OpenAI Agents SDK is optional
    from agents import Agent, AgentRuntime, Tool, OpenAIAgent
except Exception:  # pragma: no cover - provide graceful degrade
    print(
        "OpenAI Agents SDK not installed. Install with: pip install openai-agents",
        file=sys.stderr,
    )

    class OpenAIAgent:
        def __init__(self, *_, **__):
            pass

        def __call__(self, *_: str) -> str:
            return "LLM commentary unavailable."

    class Agent:  # type: ignore[misc]
        name: str | None = None

        async def policy(self, *_: object) -> object:
            return None

    def Tool(*_, **__):  # type: ignore[misc]
        def wrapper(func):
            return func

        return wrapper

    class AgentRuntime:  # type: ignore[misc]
        def __init__(self, *_, **__):
            pass

        def register(self, *_: object) -> None:
            pass

        def run(self) -> None:
            pass


try:
    import gradio as gr

    _HAVE_GRADIO = True
except ModuleNotFoundError:  # pragma: no cover - allow CLI help without gradio
    print("Gradio not installed. Install with: pip install gradio", file=sys.stderr)

    class _MissingGradio:
        def __getattr__(self, name: str):  # noqa: D401
            raise ModuleNotFoundError("gradio is required for this feature. Install with: pip install gradio")

    gr = _MissingGradio()  # type: ignore[misc]
    _HAVE_GRADIO = False

# ── Minimal MuZero utilities --------------------------------------------------
# (full implementation lives in demo/minimuzero.py, imported here)
from . import minimuzero
from .minimuzero import MiniMu

ENV_ID = os.getenv("MUZERO_ENV_ID", "CartPole-v1")  # default environment
EPISODES = int(os.getenv("MUZERO_EPISODES", 3))
PORT = int(os.getenv("HOST_PORT", 7861))

# ── Optional commentary agent -------------------------------------------------
llm = OpenAIAgent(
    model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
    api_key=os.getenv("OPENAI_API_KEY", None),
    base_url=("http://ollama:11434/v1" if not os.getenv("OPENAI_API_KEY") else None),
)


@Tool(name="explain_move", description="explain MuZero's next action")
async def explain_move(state: str):
    prompt = f"You are New‑Yorker‑style columnist. Explain why MuZero picks {state}."
    return llm(prompt)


@Tool(name="run_episode", description="Run a single MuZero episode and return the reward")
async def run_episode(max_steps: int = 500) -> dict:
    mu = MiniMu(env_id=ENV_ID)
    frames, reward = minimuzero.play_episode(mu, render=False, max_steps=max_steps)
    return {"reward": reward}


class MuZeroAgent(Agent):
    """Expose the MuZero demo as an OpenAI Agent."""

    name = "muzero_demo"
    tools = [run_episode]

    async def policy(self, obs: dict[str, Any] | Any, ctx: Any) -> object:  # type: ignore[override]
        steps = int(obs.get("steps", 500)) if isinstance(obs, dict) else 500
        return await run_episode(steps)


_runtime = AgentRuntime(api_key=None)
_agent = MuZeroAgent()
_runtime.register(_agent)

if adk_bridge and adk_bridge.adk_enabled():  # pragma: no cover - optional
    adk_bridge.auto_register([_agent])
    adk_bridge.maybe_launch()


# ── Gradio UI -----------------------------------------------------------------
def launch_dashboard() -> None:
    if not _HAVE_GRADIO:
        raise RuntimeError("gradio is required for this feature. Install with: pip install gradio")

    with gr.Blocks(title="MuZero Planning Demo") as demo:
        vid = gr.Video(label="Live environment")
        log = gr.Markdown()

        async def run() -> tuple[list[bytes], str]:
            mu = MiniMu(env_id=ENV_ID)
            frames = []
            commentary = []
            for _ in range(EPISODES):
                obs = mu.reset()
                done = truncated = False
                total_reward = 0.0
                while not done and not truncated:
                    frames.append(mu.env.render())
                    action = mu.act(obs)
                    try:
                        note = await explain_move(f"obs={obs}, action={action}")
                    except Exception:
                        note = "LLM commentary unavailable."
                    commentary.append(note)
                    obs, reward, done, truncated, _ = mu.env.step(action)
                    total_reward += float(reward)
                frames.append(mu.env.render())
                commentary.append(f"**Episode reward:** {total_reward}")
            return frames[::2], "<br>".join(commentary)

        start = gr.Button("▶ Run MuZero")
        start.click(run, outputs=[vid, log])
    import threading

    def _serve_runtime() -> None:
        _runtime.run()

    threading.Thread(target=_serve_runtime, daemon=True).start()
    demo.launch(server_name="0.0.0.0", server_port=PORT)


if __name__ == "__main__":
    launch_dashboard()
