# SPDX-License-Identifier: Apache-2.0
"""Rebuild exact-byte four-kind cross-language fixtures; no credentials or chain."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.fleet_work import execute
from alpha_factory_v1.core.runtime.work_spec import validation

ROOT = Path(__file__).resolve().parents[1]


def vectors() -> dict[str, Any]:
    missions = [
        {
            "goal": "Inspect café evidence 🧪 with exact supplied quotations",
            "work": {
                "kind": "research",
                "sources": [
                    {
                        "id": "public-test",
                        "title": "Created test data",
                        "text": "The café test records three useful observations. No financial outcome was observed.",
                    }
                ],
            },
        },
        {
            "goal": "Allocate bounded test units",
            "work": {
                "kind": "allocation",
                "budget": 5,
                "max_risk": 3,
                "items": [{"id": "A", "cost": 3, "value": 7, "risk": 2}, {"id": "B", "cost": 2, "value": 4, "risk": 1}],
            },
            "population": 4,
            "generations": 1,
        },
        {
            "goal": "Schedule bounded test tasks",
            "work": {
                "kind": "schedule",
                "jobs": [
                    {"id": "A", "operations": [{"machine": "M1", "duration": 2}], "due": 5},
                    {"id": "B", "operations": [{"machine": "M1", "duration": 1}], "due": 4},
                ],
            },
            "population": 4,
            "generations": 1,
        },
        {
            "goal": "Forecast a synthetic measured series with Unicode unités",
            "work": {
                "kind": "forecast",
                "observations": [0.0, -0.0, 1.0, 1.5, -2.5, 1e-7, 1e7, 2.0, 3.0, 4.0, 5.0, 6.0],
            },
        },
    ]
    output = []
    for mission in missions:
        spec = {
            "schema": "agialpha.bounded-work-spec.v1",
            "market": "agijobsv0-jobregistry-v2",
            "executor": "fleet-linux-v1",
            "mission": mission,
        }
        raw = json.dumps(spec, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        output.append(
            {
                "kind": mission["work"]["kind"],
                "spec_base64": base64.b64encode(raw).decode(),
                "validation": validation(raw),
                "result": execute(raw),
            }
        )
    return {
        "schema": "agialpha.fleet-work-vectors.v1",
        "scope": "synthetic supplied-input computation; no Fleet IPC qualification",
        "vectors": output,
    }


def main() -> None:
    (ROOT / "examples/ecosystem/fleet-work-vectors.json").write_text(
        json.dumps(vectors(), ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
