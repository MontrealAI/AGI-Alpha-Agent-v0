# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from alpha_factory_v1.core.agents.prompt_sampler import construct_prompt

TEMPLATE = {
    "system": "sys",
    "user": "{diff}|{exemplars}|{token}",
    "tokens": ["t1", "t2", "t3"],
}


def test_prompt_variants() -> None:
    parent = "diff-123"
    exemplars = ["ex1", "ex2", "ex3"]
    seen = {construct_prompt(parent, exemplars, TEMPLATE) for _ in range(10)}
    assert len(seen) >= 3


def test_placeholders_stable() -> None:
    parent = "pdiff"
    exemplars = ["a", "b"]
    join = "\n".join(exemplars)
    prefix = f"sys\n{parent}|{join}|"
    for _ in range(5):
        prompt = construct_prompt(parent, exemplars, TEMPLATE)
        assert prompt.startswith(prefix)
        assert prompt[len(prefix) :] in TEMPLATE["tokens"]  # noqa: E203
