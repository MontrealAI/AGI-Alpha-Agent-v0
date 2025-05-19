#!/usr/bin/env python
"""Generate a simple alpha opportunity report using offline samples.

This helper aggregates built-in alpha detectors and selects the most
salient opportunity based on heuristic thresholds. It works fully
offline so users can see an end-to-end flow without providing an
API key.
"""
from __future__ import annotations

from typing import Dict

try:
    from alpha_factory_v1.demos.era_of_experience.alpha_detection import (
        detect_yield_curve_alpha,
        detect_supply_chain_alpha,
    )
except ModuleNotFoundError:  # pragma: no cover - running as stand-alone script
    import pathlib
    import sys

    sys.path.append(str(pathlib.Path(__file__).resolve().parents[3]))
    from alpha_factory_v1.demos.era_of_experience.alpha_detection import (
        detect_yield_curve_alpha,
        detect_supply_chain_alpha,
    )


def gather_signals() -> Dict[str, str]:
    """Return raw detector messages for all built-in signals."""
    return {
        "yield_curve": detect_yield_curve_alpha(),
        "supply_chain": detect_supply_chain_alpha(),
    }


def best_alpha(signals: Dict[str, str]) -> str:
    """Select the most actionable alpha message."""
    yc = signals.get("yield_curve", "")
    sc = signals.get("supply_chain", "")

    # simple heuristics
    if "bottleneck" in sc.lower():
        return sc
    if "long bonds" in yc.lower():
        return yc
    return yc if yc else sc


def main() -> None:
    signals = gather_signals()
    choice = best_alpha(signals)
    print("\nAlpha signals:")
    for k, v in signals.items():
        print(f"- {k}: {v}")
    print("\nBest current alpha →", choice)


if __name__ == "__main__":  # pragma: no cover
    main()
