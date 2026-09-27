# SPDX-License-Identifier: Apache-2.0
"""Ship useful, editable mission inputs with both source and wheel installations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Mission
from .store import canonical, private_write, restrict_access

KINDS = ("research", "allocation", "schedule", "forecast", "code")


def examples(output: Path | None = None) -> dict[str, Any]:
    """List or copy validated examples into a new directory without overwriting."""
    files = {}
    for kind in KINDS:
        data = Path(__file__).with_name("examples").joinpath(f"{kind}.json").read_bytes()
        Mission.model_validate_json(data)
        files[f"{kind}.json"] = data
    result: dict[str, Any] = {
        "missions": list(KINDS),
        "scope": "constructed inputs; edit assumptions before use; code requires explicit configuration and Docker",
    }
    if output is not None:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
        restrict_access(output)
        for name, data in files.items():
            private_write(output / name, data)
        specification = {
            "goal": json.loads(files["allocation.json"])["goal"],
            "successMetric": (
                "Independently replay the selected IDs, budget, risk and integer totals against the supplied inputs."
            ),
            "bounty": "100000000000000000000",
            "duration": 86400,
            "priceWeight": 6000,
        }
        private_write(output / "ascension-jobs.json", canonical([specification]))
        result.update(output=str(output.resolve()), files=[*files, "ascension-jobs.json"])
    return result
