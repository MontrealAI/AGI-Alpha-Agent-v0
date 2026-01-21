# SPDX-License-Identifier: Apache-2.0
"""Prompt generation helpers."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

__all__ = ["load_templates", "construct_prompt"]

_TOKEN_QUEUES: dict[tuple[str, ...], list[str]] = {}


def _next_token(tokens: Sequence[str]) -> str:
    if not tokens:
        return ""
    key = tuple(tokens)
    queue = _TOKEN_QUEUES.get(key, [])
    if not queue:
        queue = random.sample(list(tokens), k=len(tokens))
    token = queue.pop(0)
    _TOKEN_QUEUES[key] = queue
    return token


def load_templates(path: str | Path) -> dict[str, Mapping[str, Any]]:
    """Return prompt templates loaded from ``path``."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("template file must map names to templates")
    return {str(k): dict(v) for k, v in raw.items()}


def construct_prompt(parent_diff: str, exemplars: Sequence[str], template: Mapping[str, Any]) -> str:
    """Return a prompt populated with ``parent_diff`` and ``exemplars``.

    ``template`` must provide a ``user`` string and may include ``system`` and
    ``tokens``. The ``{diff}`` and ``{exemplars}`` placeholders are replaced with
    the given parameters. A random entry from ``tokens`` (when present) fills the
    ``{token}`` placeholder.
    """
    tokens = list(template.get("tokens", []))
    token = _next_token(tokens)
    user = str(template.get("user", "")).format(
        diff=parent_diff,
        exemplars="\n".join(exemplars),
        token=token,
    )
    system = template.get("system")
    if system:
        return f"{system}\n{user}"
    return user
