#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserved Insight launcher; local execution is default and provider/runtime use is explicit."""
from __future__ import annotations

import pathlib
import sys

if __package__ is None:  # pragma: no cover - allow execution via `python run_demo.py`
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

import importlib

main = importlib.import_module("alpha_factory_v1.demos.alpha_agi_insight_v0.__main__").main

if __name__ == "__main__":  # pragma: no cover
    main()
