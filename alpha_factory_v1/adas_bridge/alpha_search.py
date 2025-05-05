import asyncio, pathlib, os, sys

from .registry import make_forward_fn
from .tasks import SAMPLE_TASKS
from alpha_factory_v1.third_party.ADAS.core import search  # adjusted import path

# ──────────────────────────────────────────────────────────────
#  Early-exit guard: if NO LLM key is present, disable ADAS only
# ──────────────────────────────────────────────────────────────
if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
    print("⚠️  ADAS disabled – no LLM API key detected. Skipping meta-search.")
    sys.exit(0)


def evaluate_forward_fn(fn):
    score = 0
    for t in SAMPLE_TASKS:
        result = asyncio.run(fn({"prompt": t["prompt"]}))
        score += t["judge"](result)
    return score / len(SAMPLE_TASKS)


def run_search(max_iters: int = 2):
    seed = [make_forward_fn(n) for n in ["finance"]]
    search.run(
        seed_agents=seed,
        evaluate_forward_fn=evaluate_forward_fn,
        max_iters=max_iters,
        docker_runner=None,  # reuse Alpha-Factory’s own sandbox
    )


if __name__ == "__main__":
    run_search()
