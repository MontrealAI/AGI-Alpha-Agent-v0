# SPDX-License-Identifier: Apache-2.0
"""Require actual CPU training/planning, lineage UIs and optional local GPT-2 inference."""
from __future__ import annotations

import argparse
from functools import partial
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from alpha_factory_v1.demos.catalog import REPO_ROOT, command_for, entries, environment_for


def validate(model: Path | None = None) -> dict[str, object]:
    """No Torch or UI fallback is accepted by this dedicated optional-runtime gate."""
    import torch
    from streamlit.testing.v1 import AppTest
    from alpha_factory_v1.demos.aiga_meta_evolution.meta_evolver import EvoNet, Genome, MetaEvolver
    from alpha_factory_v1.demos.aiga_meta_evolution.curriculum_env import CurriculumEnv, EnvGenome
    from alpha_factory_v1.demos.muzero_planning.minimuzero import MiniMu, play_episode, _TORCH

    assert _TORCH
    torch.set_num_threads(1)
    report: dict[str, object] = {"torch": torch.__version__}
    with tempfile.TemporaryDirectory(prefix="native-demo-") as temporary:
        root = Path(temporary)
        for shape in [(9,), (3, 9)]:
            net = EvoNet(9, 4, Genome(layers=(8, 6), hebbian=True))
            result = net(torch.ones(shape))
            assert tuple(result.shape) == shape[:-1] + (4,) and torch.isfinite(result).all()
        evolver = MetaEvolver(
            partial(CurriculumEnv, genome=EnvGenome(max_steps=5), size=6, seed=42),
            pop_size=3,
            elitism=1,
            parallel=False,
            checkpoint_dir=root / "aiga",
        )
        evolver.population = [Genome(layers=(8,), hebbian=False) for _ in range(3)]
        evolver.run_generations(1)
        assert evolver.gen == 1 and all(math.isfinite(value) for value in evolver._last_scores)
        assert (root / "aiga/gen_0001.json").is_file()
        report["aiga"] = {"generation": evolver.gen, "scores": evolver._last_scores, "hebbian_multilayer": True}
        agent = MiniMu()
        policy = agent.policy(agent.reset())
        assert abs(float(policy.sum()) - 1) < 1e-6
        frames, reward = play_episode(agent, render=False, max_steps=5)
        assert frames == [] and reward <= 5
        report["muzero"] = {"reward": reward, "max_steps": 5, "policy": policy.tolist()}
        previous_db = os.environ.get("METAAGI_DB")
        try:
            for entry in entries():
                if entry["id"] not in {"meta_agentic_agi", "meta_agentic_agi_v2", "meta_agentic_agi_v3"}:
                    continue
                destination = root / entry["id"]
                destination.mkdir()
                subprocess.run(
                    command_for(entry, destination),
                    cwd=destination,
                    env=environment_for(entry, destination),
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                os.environ["METAAGI_DB"] = str(destination / "lineage.sqlite")
                app = AppTest.from_file(
                    str(REPO_ROOT / "alpha_factory_v1/demos" / entry["id"] / "ui/lineage_app.py"), default_timeout=30
                ).run()
                assert not app.exception and len(app.dataframe) > 0
                app.checkbox[0].check().run()
                assert not app.exception and len(app.code) == 1
                report[entry["id"]] = {"actual_streamlit_ui": True, "tables": len(app.dataframe), "code": len(app.code)}
        finally:
            if previous_db is None:
                os.environ.pop("METAAGI_DB", None)
            else:
                os.environ["METAAGI_DB"] = previous_db
        if model:
            from alpha_factory_v1.demos.gpt2_small_cli.gpt2_cli import generate

            output = generate("The future of AI", 16, model, offline=True)
            assert len(output) > len("The future of AI")
            report["gpt2"] = {"actual_offline_generation": True, "output": output}
        else:
            report["gpt2"] = "Not exercised: supply --model with verified local weights"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
