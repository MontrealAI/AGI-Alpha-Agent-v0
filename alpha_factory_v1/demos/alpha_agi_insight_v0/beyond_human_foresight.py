#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# References to "AGI" and "superintelligence" describe aspirational goals
# and do not indicate the presence of a real general intelligence.
# Use at your own risk. Nothing herein constitutes financial advice.
# MontrealAI and the maintainers accept no liability for losses incurred.
"""Preserved Insight launcher; local execution is default and provider/runtime use is explicit."""
from __future__ import annotations

from typing import List

if __package__ is None:  # pragma: no cover - allow direct execution
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

from .official_demo_final import main as _main
from .openai_agents_bridge import print_banner


def main(argv: List[str] | None = None) -> None:
    """Entry point for the Beyond Human Foresight demo."""
    _main(argv)


if __name__ == "__main__":  # pragma: no cover
    main()
