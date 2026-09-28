#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# References to "AGI" and "superintelligence" describe aspirational goals
# and do not indicate the presence of a real general intelligence.
# Use at your own risk. Nothing herein constitutes financial advice.
# MontrealAI and the maintainers accept no liability for losses incurred.
"""Preserved Insight launcher; local execution is default and provider/runtime use is explicit."""
from __future__ import annotations
import pathlib
import sys

if __package__ is None:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

from .official_demo_final import main, _agents_available, _run_offline

if __name__ == "__main__":
    main()
