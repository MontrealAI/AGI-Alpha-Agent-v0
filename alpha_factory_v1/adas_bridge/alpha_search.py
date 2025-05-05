import asyncio, pathlib
from .registry import make_forward_fn
from .tasks import SAMPLE_TASKS

# updated import path — note the leading alpha_factory_v1.
from alpha_factory_v1.third_party.ADAS.core import search

def evaluate_forward_fn(fn):
    score = 0
    for t in SAMPLE_TASKS:
        result = asyncio.run(fn({"prompt": t["prompt"]}))
        score += t["judge"](result)
    return score / len(SAMPLE_TASKS)

def run_search(max_iters=2):
    seed = [make_forward_fn(n) for n in ["finance"]]
    search.run(
        seed_agents=seed,
        evaluate_forward_fn=evaluate_forward_fn,
        max_iters=max_iters,
        docker_runner=None      # uses Alpha-Factory’s own sandbox
    )

if __name__ == "__main__":
    run_search()
