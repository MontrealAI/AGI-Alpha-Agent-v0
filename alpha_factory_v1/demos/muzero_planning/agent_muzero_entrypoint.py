# SPDX-License-Identifier: Apache-2.0
"""Local, bounded MuZero dashboard. No model downloads, credentials or telemetry."""
from __future__ import annotations

import os
import inspect
from typing import Any, Iterator

# Gradio reads this setting during import. The demo never needs analytics.
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
try:
    import gradio as gr
except ModuleNotFoundError:  # CLI --help never imports this module
    gr = None

from .minimuzero import MiniMu, play_episode, require_dependencies


async def run_episode(max_steps: int = 500) -> dict[str, float]:
    """Retained local tool entry point; fail clearly if the real backend is absent."""
    require_dependencies()
    mu = MiniMu(env_id=os.getenv("MUZERO_ENV_ID", "CartPole-v1"), render_mode=None)
    _, reward = play_episode(mu, render=False, max_steps=max_steps)
    return {"reward": reward}


class MuZeroAgent:
    """Explicit local adapter; optional historical SDK wiring is preserved in archive/."""

    name = "muzero_demo"
    tools = [run_episode]

    async def policy(self, obs: Any, ctx: Any = None) -> object:
        return await run_episode(obs.get("steps", 500) if isinstance(obs, dict) else 500)


async def explain_move(state: str) -> str:
    """An action alone cannot establish an explanation; inspect search evidence instead."""
    return "Inspect the prior, visit count, predicted reward and discounted value in the search table."


def build_dashboard(config: Any = None) -> Any:
    """Build an accessible interface; generator cancellation stops between episodes."""
    if gr is None:
        raise RuntimeError("gradio is required; install the demo requirements.txt")
    require_dependencies()
    from .training import Config, ENVIRONMENTS, experiment, preview_episode

    config = config or Config()
    with gr.Blocks(title="MuZero · Planning Lab", analytics_enabled=False) as demo:
        gr.Markdown(
            "# MuZero · Planning Lab\n### Learn a model. Inspect a decision. Measure the difference.\n"
            "Train a small neural model locally, then compare it with random actions and its untrained self. "
            "**No API key or downloaded model needed.**"
        )
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown(
                    "### 1 · Choose your experiment\nStart with **MiniChoice**: take 0.3 now, or learn a two-step "
                    "route to 1.0. CartPole is a harder research experiment; short training may not improve it."
                )
                env = gr.Dropdown(choices=list(ENVIRONMENTS), value=config.env_id, label="Environment")
                episodes = gr.Slider(
                    0, 100, value=config.episodes, step=1, label="Training episodes (0 = untrained baseline)"
                )
                sims = gr.Slider(2, 128, value=config.simulations, step=1, label="Search simulations per action")
                seed = gr.Number(value=config.seed, precision=0, label="Seed")
                steps = gr.Slider(2, 500, value=config.max_steps, step=1, label="Maximum steps per episode")
                with gr.Row():
                    start = gr.Button("Train & compare", variant="primary")
                    stop = gr.Button("Stop")
            with gr.Column(scale=2):
                gr.Markdown("### 2 · Follow the learning")
                status = gr.Markdown("Ready. Choose **Train & compare** to run a real local experiment.")
                curve = gr.LinePlot(x="episode", y="reward", title="Observed training reward", height=260)
                losses = gr.Dataframe(
                    headers=["Episode", "Reward loss", "Value loss", "Policy loss"], interactive=False
                )
        gr.Markdown(
            "### 3 · Compare on held-out episodes\nEach policy sees the same reset seeds, separate from training. "
            "MiniChoice repeats one deterministic task; this checks behavior, not generalization. "
            "A higher score in one small experiment does not establish general capability."
        )
        comparison = gr.Dataframe(headers=["Policy", "Mean reward", "Episode rewards"], interactive=False)
        with gr.Accordion("Watch the trained agent · bounded episode snapshots", open=False):
            gr.Markdown(
                "Up to 60 steps and 12 snapshots from the first evaluation seed. "
                "The complete held-out scores remain in the table above."
            )
            frames = gr.Gallery(label="Environment snapshots", columns=3, height=240)
        with gr.Accordion("Why this action? Inspect the root search", open=True):
            gr.Markdown(
                "**Prior** is the network's initial preference. **Visits** show where search allocated effort. "
                "**Q = predicted reward + 0.997 × value** ranks expected discounted returns. "
                "Predictions can be wrong; compare them with observed rewards."
            )
            tree = gr.Dataframe(
                headers=["Action", "Prior", "Visits", "Predicted reward", "Value", "Q"], interactive=False
            )
        with gr.Accordion("Reproducible experiment record", open=False):
            record = gr.JSON(label="Configuration, versions, measurements and portable weights")
        gr.Markdown(
            "### How it works\nObservation → representation → latent state. Search unrolls learned dynamics "
            "and backs up reward + discounted value. Real environment transitions enter replay; gradient descent "
            "trains reward, value and search-policy targets.\n\n"
            "This is a bounded educational MuZero-style implementation, not a reproduction of DeepMind's "
            "Atari results, autonomous enterprise system or achieved AGI. "
            "[Research and preserved flowchart](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/"
            "alpha_factory_v1/demos/muzero_planning)"
        )

        def run(env_id: str, count: int, budget: int, random_seed: int, limit: int) -> Iterator[tuple[Any, ...]]:
            import pandas as pd

            try:
                values = (random_seed, count, budget, limit)
                if any(isinstance(value, bool) or value != int(value) for value in values):
                    raise ValueError("Seed and budgets must be whole numbers")
                cfg = Config(env_id, int(random_seed), int(count), int(budget), int(limit))
            except ValueError as exc:
                raise gr.Error(str(exc)) from exc
            yield "Preparing held-out baselines…", gr.skip(), [], [], [], None, []
            for event in experiment(cfg):
                history = event["history"]
                frame = pd.DataFrame(
                    [{"episode": h["episode"], "reward": h["reward"]} for h in history], columns=["episode", "reward"]
                )
                loss_rows = [
                    [h["episode"], round(h["loss_reward"], 6), round(h["loss_value"], 6), round(h["loss_policy"], 6)]
                    for h in history[-10:]
                ]
                if event["status"] == "training":
                    yield (
                        f"Training episode **{event['completed']} / {event['total']}**",
                        frame,
                        loss_rows,
                        [],
                        [],
                        None,
                        [],
                    )
                else:
                    rows = [
                        [key, round(sum(values) / len(values), 3), str(values)]
                        for key, values in event["evaluation"].items()
                    ]
                    search_rows = [list(row.values()) for row in event["search_after"]]
                    yield (
                        "**Complete.** Compare measured returns below; every run starts with fresh weights.",
                        frame,
                        loss_rows,
                        rows,
                        search_rows,
                        event,
                        preview_episode(event),
                    )

        event = start.click(
            run,
            [env, episodes, sims, seed, steps],
            [status, curve, losses, comparison, tree, record, frames],
            concurrency_limit=1,
            concurrency_id="muzero-training",
        )
        stop.click(
            fn=lambda: "Stopped. Completed measurements remain visible.", outputs=status, cancels=[event], queue=False
        )
    return demo.queue(max_size=4, default_concurrency_limit=1)


def launch_dashboard(*, config: Any = None, host: str = "127.0.0.1", port: int | None = None) -> None:
    """Serve loopback by default with an explicit health endpoint and no public tunnel."""
    demo = build_dashboard(config)
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()

    def live() -> dict[str, str]:
        return {"status": "ok", "mode": "local-research"}

    app.add_api_route("/__live", live, methods=["GET"])
    options: dict[str, Any] = {}
    if "theme" in inspect.signature(gr.mount_gradio_app).parameters:
        options["theme"] = gr.themes.Base(primary_hue="emerald", font=["system-ui"], font_mono=["monospace"]).set(
            button_primary_background_fill="#065f46",
            button_primary_text_color="#ffffff",
            button_primary_background_fill_hover="#064e3b",
            block_label_text_color="#183f35",
            block_label_text_color_dark="#d1fae5",
        )
    if "run_history" in inspect.signature(gr.mount_gradio_app).parameters:
        options["run_history"] = False
        options["footer_links"] = []
    app = gr.mount_gradio_app(app, demo, path="/", **options)
    uvicorn.run(app, host=host, port=port or int(os.getenv("HOST_PORT", "7861")))


if __name__ == "__main__":
    launch_dashboard()
