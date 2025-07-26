# SPDX-License-Identifier: Apache-2.0
"""Project disclaimer helper."""

from pathlib import Path

_DOCS_PATH = Path(__file__).resolve().parents[2] / "docs" / "DISCLAIMER_SNIPPET.md"
DISCLAIMER: str = _DOCS_PATH.read_text(encoding="utf-8").strip()


import os
import sys


def _enabled() -> bool:
    """Return True when the disclaimer should be printed."""
    if os.environ.get("NO_DISCLAIMER"):
        return False
    return sys.stdout.isatty()


def print_disclaimer() -> None:
    """Print the project disclaimer when enabled."""
    if _enabled():
        print(DISCLAIMER)


__all__ = ["DISCLAIMER", "print_disclaimer"]
