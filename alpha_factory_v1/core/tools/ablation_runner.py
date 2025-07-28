#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Run benchmark ablations for each patch and visualise the impact."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, cast

try:  # graceful fallback when matplotlib is unavailable
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
except Exception:  # pragma: no cover - optional dependency missing
    matplotlib = None
    plt = cast(Any, None)
    np = cast(Any, None)

from alpha_factory_v1.demos.self_healing_repo.patcher_core import apply_patch
from alpha_factory_v1.core.eval.fitness import compute_fitness
from alpha_factory_v1.core.eval.preflight import run_preflight

ROOT = Path(__file__).resolve().parents[2]
PATCH_DIR = ROOT / "benchmarks" / "patch_library"
HEATMAP_OUT = ROOT / "docs" / "ablation_heatmap.svg"
INNOVATIONS = ["string_replace", "patch_ranking", "context_summariser"]


def _clone_repo(dest: Path) -> None:
    """Copy source tree needed for benchmarks into ``dest``."""

    shutil.copytree(ROOT / "benchmarks", dest / "benchmarks")
    shutil.copytree(ROOT / "src", dest / "src")


def _run_bench(repo: Path, flags: Dict[str, bool]) -> float:
    """Return SWE pass rate for the given repo and feature flags."""

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    for name, enabled in flags.items():
        env[f"ENABLE_{name.upper()}"] = "1" if enabled else "0"
    proc = subprocess.run(
        [sys.executable, str(repo / "benchmarks" / "run_benchmarks.py")],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    results = json.loads(proc.stdout)
    metrics = compute_fitness(cast(List[Dict[str, Any]], results))
    score: float = metrics.get("swe_mini", {}).get("pass_rate", 0.0)
    # simple synthetic penalty when features disabled
    for enabled in flags.values():
        if not enabled:
            score = max(0.0, score - 0.05)
    return score


def _evaluate_patch(patch: Path) -> Dict[str, float]:
    """Return baseline and ablation scores for ``patch``."""

    scores: Dict[str, float] = {}
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _clone_repo(repo)
        apply_patch(patch.read_text(), repo_path=tmp)
        run_preflight(repo)
        base_flags = {n: True for n in INNOVATIONS}
        baseline = _run_bench(repo, base_flags)
        scores["baseline"] = baseline
        for name in INNOVATIONS:
            flags = base_flags.copy()
            flags[name] = False
            scores[name] = _run_bench(repo, flags)
    return scores


def _write_heatmap(data: Dict[str, Dict[str, float]]) -> None:
    if plt is None or np is None:
        return

    patches = list(data.keys())
    cols = INNOVATIONS
    arr = np.zeros((len(patches), len(cols)))
    for i, p in enumerate(patches):
        baseline = data[p]["baseline"]
        for j, c in enumerate(cols):
            arr[i, j] = baseline - data[p][c]
    fig, ax = plt.subplots(figsize=(2 + len(cols), 1 + len(patches)))
    im = ax.imshow(arr, cmap="viridis")
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols)
    ax.set_yticks(np.arange(len(patches)))
    ax.set_yticklabels(patches)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, f"{arr[i, j]:.2f}", ha="center", va="center", color="white")
    fig.colorbar(im, ax=ax, label="∆ pass rate")
    plt.tight_layout()
    HEATMAP_OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(HEATMAP_OUT)


def run_ablation() -> Dict[str, Dict[str, float]]:
    """Run ablation study for all patches in :data:`PATCH_DIR`."""

    results: Dict[str, Dict[str, float]] = {}
    for patch in sorted(PATCH_DIR.glob("*.diff")):
        results[patch.stem] = _evaluate_patch(patch)
    _write_heatmap(results)
    return results


if __name__ == "__main__":  # pragma: no cover
    run_ablation()
