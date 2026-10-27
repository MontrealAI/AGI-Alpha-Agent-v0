# SPDX-License-Identifier: Apache-2.0
"""Named delivery packaging for the existing finite resilient-placement runtime."""

from .schema import PlacementBrief, parse_brief

__all__ = ["PlacementBrief", "parse_brief"]
