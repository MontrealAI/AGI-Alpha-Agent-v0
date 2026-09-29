# SPDX-License-Identifier: Apache-2.0
"""Loopback-only local interface with explicit progress and reviewable measurements."""
from __future__ import annotations

import inspect
import json
import os
from typing import Any, Iterator

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

from .lab import run


def build(args: Any) -> Any:
    import gradio as gr

    with gr.Blocks(title="MuZero × MCTS × LLM", analytics_enabled=False, delete_cache=(3600, 3600)) as demo:
        gr.Markdown(
            "# MuZero × MCTS × LLM\n### An idea is a proposal. A rollout is evidence.\n"
            "Explore a two-step decision: take **0.3 now**, or learn the route to **1.0 later**. "
            "Retrieve task evidence, optionally consult a local language model, then inspect trained search. "
            "Everything executes in a small simulator; rewards are not money."
        )
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 1 · Set up\nNo model or API key is needed for the default run.")
                question = gr.Textbox(value=args.question, label="Question about MiniChoice", max_lines=4)
                episodes = gr.Slider(0, 100, value=args.episodes, step=1, label="Training episodes")
                simulations = gr.Slider(2, 128, value=args.simulations, step=1, label="Simulations per search")
                seed = gr.Number(value=args.seed, precision=0, label="Seed")
                model = gr.Textbox(
                    value=args.model, label="Optional installed Ollama model", placeholder="Blank = no language model"
                )
                gr.Markdown(
                    "Model requests go only to `127.0.0.1:11434`. The question and evidence are sent there. "
                    "Errors stop the run; no synthetic model response is substituted."
                )
                start = gr.Button("Retrieve, train & compare", variant="primary")
                stop = gr.Button("Stop")
            with gr.Column(scale=2):
                gr.Markdown("## 2 · Follow the experiment")
                status = gr.Markdown("Ready. A fresh model is trained for each run.")
                curve = gr.LinePlot(x="episode", y="reward", title="Observed training rewards", height=260)
                evidence = gr.Dataframe(headers=["Source", "Evidence", "Lexical overlap"], interactive=False, wrap=True)
        gr.Markdown(
            "## 3 · Review the decision\nThe language model is an adviser. Search selects the action. "
            "A valid quotation does not prove the model's reasoning. Compare predictions with observed returns. "
            "Reward/value fields are blank for unvisited branches: no estimate was evaluated."
        )
        advice = gr.JSON(label="Model proposal and validated quotations")
        search = gr.Dataframe(
            headers=["Action", "Prior", "Visits", "Predicted reward", "Value", "Q"], interactive=False
        )
        outcomes = gr.Dataframe(
            headers=["First action", "Observed total reward", "Actual action/reward trace"], interactive=False
        )
        baselines = gr.Dataframe(headers=["Policy", "Mean held-out reward"], interactive=False)
        gr.Markdown(
            "Both first actions use the same reset seed and trained continuation. "
            "These are simulator measurements, not live execution. MiniChoice repeats a deterministic task; "
            "held-out reset seeds do not establish generalization."
        )
        with gr.Accordion("Complete report · copy JSON for reproducibility", open=False):
            record = gr.Code(
                label="Report, source hashes, versions and portable model weights", language="json", interactive=False
            )
        gr.Markdown(
            "**Review required.** This interface has no financial, shell or deployment tools and no wallet access gate. "
            "[Research, setup and preserved presentation](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/muzeromctsllmagent_v0)"
        )

        def execute(
            query: str, count: float, budget: float, random_seed: float, local_model: str
        ) -> Iterator[tuple[Any, ...]]:
            import pandas as pd

            # Clear every prior result, including after an invalid new request.
            yield "Preparing evidence…", pd.DataFrame(columns=["episode", "reward"]), [], None, [], [], [], ""
            try:
                values = (count, budget, random_seed)
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v != int(v) for v in values):
                    raise ValueError("Budgets and seed must be whole numbers")
                for event in run(
                    query, episodes=int(count), simulations=int(budget), seed=int(random_seed), model=local_model
                ):
                    if event["status"] == "training":
                        frame = pd.DataFrame(event["history"])
                        yield f"Training **{event['completed']} / {event['total']}**", frame, [], None, [], [], [], ""
                    else:
                        experiment = event["experiment"]
                        yield (
                            f"**Complete · review required.** Search chose action **{event['search_action']}**. Model agreement: **{'not requested' if event['agreement'] is None else 'yes' if event['agreement'] else 'no'}**.",
                            pd.DataFrame(experiment["history"], columns=["episode", "reward"]),
                            [[r["id"], r["text"], r["overlap"]] for r in event["evidence"]],
                            event["advice"],
                            [list(r.values()) for r in experiment["search_after"]],
                            [
                                [r["first_action"], r["observed_return"], json.dumps(r["trace"])]
                                for r in event["counterfactuals"]
                            ],
                            [[key, sum(scores) / len(scores)] for key, scores in experiment["evaluation"].items()],
                            json.dumps(event, indent=2, allow_nan=False),
                        )
            except (ValueError, RuntimeError, OSError) as exc:
                raise gr.Error(str(exc)) from exc

        event = start.click(
            execute,
            [question, episodes, simulations, seed, model],
            [status, curve, evidence, advice, search, outcomes, baselines, record],
            concurrency_limit=1,
            concurrency_id="planning-lab",
        )
        stop.click(
            lambda: "Stop requested. Training stops between episodes; an active model request may take up to 60 seconds.",
            outputs=status,
            cancels=[event],
            queue=False,
        )
    return demo.queue(max_size=4, default_concurrency_limit=1)


def launch(args: Any) -> None:
    import gradio as gr
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()
    app.add_api_route("/__live", lambda: {"status": "ok", "mode": "local-planning-lab"}, methods=["GET"])
    options: dict[str, Any] = {}
    if "theme" in inspect.signature(gr.mount_gradio_app).parameters:
        options["theme"] = gr.themes.Base(primary_hue="indigo", font=["system-ui"], font_mono=["monospace"])
    if "run_history" in inspect.signature(gr.mount_gradio_app).parameters:
        options.update(run_history=False, footer_links=[])
    app = gr.mount_gradio_app(app, build(args), path="/", **options)
    uvicorn.run(app, host="127.0.0.1", port=args.port)
