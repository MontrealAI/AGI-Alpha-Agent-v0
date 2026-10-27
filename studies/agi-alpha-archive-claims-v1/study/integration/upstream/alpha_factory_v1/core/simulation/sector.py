# SPDX-License-Identifier: Apache-2.0
"""Simple container describing a market sector.

Each ``Sector`` tracks energy, entropy and growth parameters alongside a
``disrupted`` flag used during the forecast simulation.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os


@dataclass(slots=True)
class Sector:
    """Simple sector state used by the simulation."""

    name: str
    energy: float = 1.0
    entropy: float = 1.0
    growth: float = 0.05
    disrupted: bool = False


def load_sectors(path: str | os.PathLike[str], *, energy: float = 1.0, entropy: float = 1.0) -> list[Sector]:
    """Load sector definitions from a JSON file.

    The file may contain a list of strings representing sector names or a list
    of objects with ``name`` and optional ``energy``, ``entropy`` and ``growth``
    fields. The ``energy`` and ``entropy`` arguments provide defaults when these
    values are omitted.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sectors: list[Sector] = []
    for entry in data:
        if isinstance(entry, str):
            sectors.append(Sector(entry, energy, entropy))
        elif isinstance(entry, dict):
            sectors.append(
                Sector(
                    entry.get("name", ""),
                    float(entry.get("energy", energy)),
                    float(entry.get("entropy", entropy)),
                    float(entry.get("growth", 0.05)),
                    bool(entry.get("disrupted", False)),
                )
            )
        else:
            raise ValueError(f"Invalid sector entry: {entry!r}")
    return sectors
