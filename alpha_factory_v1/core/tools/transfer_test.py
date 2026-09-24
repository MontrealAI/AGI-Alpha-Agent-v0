# SPDX-License-Identifier: Apache-2.0
"""Replay top agents on alternate models and log the scores."""

from __future__ import annotations

import csv
import os
import json
import math
import tempfile
from pathlib import Path
from typing import Iterable

from alpha_factory_v1.core.archive import Archive, Agent


DEFAULT_ARCHIVE = Path(os.getenv("ARCHIVE_PATH", "archive.db"))
DEFAULT_RESULTS = Path("results/transfer_matrix.csv")


def evaluate_agent(agent: Agent, model: str) -> float:
    """Return agent score when evaluated with ``model``.

    The archive must provide ``transfer_cases`` with ``prompt`` and ``expected``
    fields. The operator explicitly selects a compatible endpoint through
    ``ALPHA_TRANSFER_BASE_URL``. No archived score is relabeled as evaluation.
    """

    import httpx
    from alpha_factory_v1.core.runtime.models import RuntimeConfig

    endpoint = os.getenv("ALPHA_TRANSFER_BASE_URL", "")
    config = RuntimeConfig(
        llm_url=endpoint, llm_model=model, allow_remote_llm=os.getenv("ALPHA_TRANSFER_ALLOW_REMOTE") == "1"
    )
    cases = agent.meta.get("transfer_cases")
    if not endpoint or not isinstance(cases, list) or not 1 <= len(cases) <= 100:
        raise ValueError("transfer evaluation requires an explicit provider and 1–100 archived transfer_cases")
    headers = {}
    key = os.getenv("ALPHA_TRANSFER_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    local = httpx.URL(endpoint).host in {"localhost", "127.0.0.1", "::1"}
    passed = 0
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=not local) as client:
        for case in cases:
            if (
                not isinstance(case, dict)
                or set(case) != {"prompt", "expected"}
                or not all(isinstance(v, str) and len(v) <= 10000 for v in case.values())
            ):
                raise ValueError("invalid transfer benchmark case")
            response = client.post(
                endpoint.rstrip("/") + "/chat/completions",
                headers=headers,
                json={
                    "model": config.llm_model,
                    "temperature": 0,
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": case["prompt"]}],
                },
            )
            response.raise_for_status()
            if len(response.content) > 1024**2:
                raise ValueError("transfer response exceeds 1 MiB")
            choice = response.json()["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("transfer response did not complete")
            passed += choice["message"]["content"].strip() == case["expected"].strip()
    return passed / len(cases)


def archived_score_baseline(agent: Agent, model: str) -> float:
    """Return the original demonstration value; this is NOT a transfer test."""
    return agent.score


def run_transfer_test(
    models: Iterable[str],
    top_n: int,
    *,
    archive_path: str | Path = DEFAULT_ARCHIVE,
    out_file: str | Path = DEFAULT_RESULTS,
) -> None:
    """Evaluate the top ``top_n`` agents on each model and store a score matrix."""

    if top_n < 1:
        raise ValueError("top_n must be positive")
    model_list = list(models)
    if not model_list or len(model_list) > 20 or any(not model.strip() for model in model_list):
        raise ValueError("provide 1–20 model names")
    arch = Archive(archive_path)
    agents = sorted(arch.all(), key=lambda a: a.score, reverse=True)[:top_n]

    path = Path(out_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[list[object]] = [["id", *model_list]]
    for agent in agents:
        row: list[object] = [agent.id]
        for model in model_list:
            score = evaluate_agent(agent, model)
            if not math.isfinite(score):
                raise ValueError("non-finite transfer score")
            row.append(f"{score:.3f}")
        rows.append(row)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, newline="", encoding="utf-8", delete=False) as fh:
        csv.writer(fh).writerows(rows)
        temporary = Path(fh.name)
    os.replace(temporary, path)


__all__ = ["run_transfer_test", "evaluate_agent", "archived_score_baseline"]
