#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Backward-compatible source launcher for the packaged verified GPT-2 downloader."""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha_factory_v1.demos.gpt2_small_cli.model_download import (
    download_hf_gpt2 as download_hf_gpt2,
    main as main,
)

if __name__ == "__main__":
    main()
