# SPDX-License-Identifier: Apache-2.0
"""Fresh-process reproducibility probe; fixture mode does not qualify training."""
from __future__ import annotations

import argparse
from functools import partial
import hashlib
import json
from pathlib import Path
import random

import numpy as np

from alpha_factory_v1.demos.aiga_meta_evolution import meta_evolver as me


class FixtureEvolver(me.MetaEvolver):
    """Synthetic, non-training evaluator for RNG/checkpoint regression tests."""

    def _evaluate_population(self):
        return self._post_eval(
            [
                (
                    sum(g.layers) + g.novelty_weight + random.Random(seed).random(),
                    np.array([i, self.gen, sum(g.layers)], dtype=np.float32),
                )
                for i, (g, seed) in enumerate(zip(self.population, self._evaluation_seeds()))
            ]
        )


def snapshot(evolver):
    return {
        "generation": evolver.gen,
        "population": [g.to_json() for g in evolver.population],
        "history": list(evolver.history),
        "archive": [a.tolist() for a in evolver._archive],
        "last_scores": list(evolver._last_scores),
        "best_fitness": evolver.best_fitness,
        "best_genome": evolver.best_architecture,
        "sha": evolver.population_sha(),
        "rng_state": evolver.rng.getstate(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--global-seed", type=int, default=1)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--training", action="store_true")
    args = parser.parse_args()
    random.seed(args.global_seed)
    np.random.seed(args.global_seed)
    me._A2A = None
    if args.training:
        import torch
        from alpha_factory_v1.demos.aiga_meta_evolution.curriculum_env import CurriculumEnv, EnvGenome

        torch.set_num_threads(1)
        torch.manual_seed(args.global_seed)
        factory = partial(CurriculumEnv, genome=EnvGenome(max_steps=6), size=6)
        cls = me.MetaEvolver
    else:

        def factory():
            return None

        cls = FixtureEvolver
    evolver = cls(
        factory, pop_size=4, elitism=1, parallel=False, checkpoint_dir=args.checkpoint_dir, seed=args.seed, device="cpu"
    )
    evolver.run_generations(3)
    result = snapshot(evolver)
    if args.training:
        net = me.EvoNet(9, 4, me.Genome(layers=(4,)), seed=args.seed)
        weights = b"".join(value.detach().numpy().tobytes() for value in net.parameters())
        result["weights_sha256"] = hashlib.sha256(weights).hexdigest()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
