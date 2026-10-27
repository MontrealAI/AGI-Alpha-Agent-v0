# SPDX-License-Identifier: Apache-2.0
"""Post-confirmation input-contract probes; not part of the protected outcome cohort."""

from __future__ import annotations

import copy
import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


def main() -> int:
    """Preserve malformed fixtures and require structured exit-2 rejection."""
    root = Path(__file__).resolve().parents[1]
    output = root / "evaluation/input-probes-v1"
    if output.exists():
        raise ValueError("refusing to overwrite prior input-probe evidence")
    output.mkdir(parents=True)
    origin = json.loads((root / "data/origin.json").read_text())
    probes: list[tuple[str, Callable[[dict[str, Any]], Any]]] = [
        ("prior-not-normalized", lambda m: m["prior"].__setitem__(0, 0.97)),
        ("nonfinite-prior", lambda m: m["prior"].__setitem__(0, float("nan"))),
        ("negative-action-cost", lambda m: m["operators"][0]["actions"][0].__setitem__("cost_usd", -1)),
        ("negative-arrival", lambda m: m["observation"]["outcomes"][0].__setitem__("arrival_hours", -1)),
        ("likelihood-not-normalized", lambda m: m["observation"]["outcomes"][0]["likelihood"].__setitem__(0, 0.99)),
        ("missing-fallback", lambda m: m["operators"][0].__setitem__("fallback_action", "nonexistent")),
        (
            "duplicate-outcome-id",
            lambda m: m["observation"]["outcomes"][1].__setitem__("id", m["observation"]["outcomes"][0]["id"]),
        ),
        ("reserved-outcome-id", lambda m: m["observation"]["outcomes"][0].__setitem__("id", "__timeout__")),
        ("empty-operators", lambda m: m.__setitem__("operators", [])),
        (
            "seven-operators",
            lambda m: m.__setitem__(
                "operators", [{**copy.deepcopy(m["operators"][0]), "id": f"op-{j}"} for j in range(7)]
            ),
        ),
        ("boolean-cost", lambda m: m["operators"][0]["actions"][0].__setitem__("cost_usd", True)),
        ("nonboolean-prerequisite", lambda m: m["observation"].__setitem__("usable", "true")),
    ]
    rows = []
    for name, mutate in probes:
        mission = copy.deepcopy(origin)
        mutate(mission)
        mission_file, result_file = output / f"{name}.input.json", output / f"{name}.output.json"
        mission_file.write_text(json.dumps(mission, indent=2) + "\n")
        command = [
            sys.executable,
            str(root / "capability/compiler.py"),
            "--mission",
            str(mission_file),
            "--output",
            str(result_file),
        ]
        process = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=30, check=False)
        try:
            result = json.loads(result_file.read_text())
        except (OSError, ValueError):
            result = {}
        ok = (
            process.returncode == 2
            and isinstance(result, dict)
            and bool(result.get("error"))
            and "Traceback" not in process.stderr
        )
        rows.append(
            {
                "probe": name,
                "pass": ok,
                "returncode": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "result": result,
            }
        )
    summary = {
        "schema": "shared-observation-input-probes/v1",
        "phase": "post-confirmation diagnostic",
        "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "probe_count": len(rows),
        "pass_count": sum(row["pass"] for row in rows),
        "rows": rows,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "probe_count": len(rows),
                "pass_count": summary["pass_count"],
                "failures": [row for row in rows if not row["pass"]],
            },
            indent=2,
        )
    )
    return 0 if summary["pass_count"] == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
