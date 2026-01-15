# SPDX-License-Identifier: Apache-2.0
"""Utility functions for AGIALPHA token unit conversion."""

AGIALPHA_DECIMALS: int = 18
UNIT: int = 10**AGIALPHA_DECIMALS


def to_token_units(amount: float | int) -> int:
    """Convert a token amount to base units."""
    return int(amount * UNIT)


def from_token_units(amount: int) -> float:
    """Convert base units to whole tokens."""
    return float(amount) / float(UNIT)
