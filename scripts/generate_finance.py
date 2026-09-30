# SPDX-License-Identifier: Apache-2.0
"""Publish recorded finance evidence from the exact same offline Python engine."""
from pathlib import Path

from alpha_factory_v1.demos.finance_alpha.delivery import render
from alpha_factory_v1.demos.finance_alpha.paper import CASES, run
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def build(root: Path) -> None:
    """Keep the original gallery presentation and publish replayable scenario results."""
    target = root / "docs/finance_alpha"
    target.mkdir(parents=True, exist_ok=True)
    original = target / "research.html"
    if not original.exists():
        original.write_bytes((target / "index.html").read_bytes())
    reports = {case: run(case=case) for case in CASES}
    (target / "index.html").write_text(render({"mode": "gallery", "scenarios": reports}), encoding="utf-8")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
