# SPDX-License-Identifier: Apache-2.0
"""MiniMu demo package for MuZero Planning."""


def launch_dashboard() -> None:
    """Load optional UI dependencies only when launching the dashboard."""
    from .agent_muzero_entrypoint import launch_dashboard as launch

    launch()


__all__ = ["launch_dashboard"]
__version__ = "2.0.0"
