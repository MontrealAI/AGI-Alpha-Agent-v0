# SPDX-License-Identifier: Apache-2.0
"""Re-export the lineage dashboard for the Insight demo package."""

from alpha_factory_v1.core.interface.lineage_dashboard import build_tree, load_df, main

__all__ = ["build_tree", "load_df", "main"]
