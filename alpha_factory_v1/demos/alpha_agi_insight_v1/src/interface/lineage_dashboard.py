# SPDX-License-Identifier: Apache-2.0
"""Re-export the lineage dashboard for the Insight demo package."""

from alpha_factory_v1.core.interface.lineage_dashboard import build_tree, load_df, main

__all__ = ["build_tree", "load_df", "main"]
"""Expose the lineage dashboard for the Insight demo."""
from __future__ import annotations

from alpha_factory_v1.core.interface import lineage_dashboard as _core

load_df = _core.load_df
build_tree = _core.build_tree


def main(argv: list[str] | None = None) -> None:
    """Launch the lineage dashboard CLI."""
    _core.main(argv)


__all__ = ["build_tree", "load_df", "main"]


if __name__ == "__main__":  # pragma: no cover
    main()
