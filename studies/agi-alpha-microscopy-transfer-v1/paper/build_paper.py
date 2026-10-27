# SPDX-License-Identifier: Apache-2.0
"""Bind display values to archived evidence and compile the publication edition."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, cast

PAPER = Path(__file__).resolve().parent
STUDY = PAPER.parent


def read_json(relative: str) -> dict[str, Any]:
    """Read one archived JSON evidence file."""
    return cast(dict[str, Any], json.loads((STUDY / relative).read_text()))


def main() -> None:
    """Verify frozen evidence, emit display macros, and run the LaTeX build."""
    confirmation = read_json("confirmation/results/frozen-v1/summary.json")
    economics = read_json("economics/results/results.json")
    integration = read_json("integration/results/frozen-v1/summary.json")
    hosted = read_json("hosted_trials/scoring.json")
    freeze = read_json("protocols/source-freeze.json")
    for relative, expected in freeze["files"].items():
        observed = hashlib.sha256((STUDY / relative).read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(f"Frozen evidence changed: {relative}")
    primary = economics["scenarios"]["primary_zero_gain"]["established/E"]
    threshold = next(item for item in economics["thresholds"] if item["realized_reuses"] == 4)
    values = {
        "FreshPass": confirmation["recovered_passed"],
        "FreshTotal": confirmation["n_compatible_missions"],
        "RefusalPass": confirmation["semantic_passed"],
        "RefusalTotal": confirmation["n_semantic_cases"],
        "InterfacePass": integration["passed"],
        "InterfaceTotal": integration["total"],
        "HostedU": hosted["arms"]["U"]["passed"],
        "HostedE": hosted["arms"]["E"]["passed"],
        "HostedEplus": hosted["arms"]["Eplus"]["passed"],
        "ConditionalSurplus": f"{primary['mean_economic_surplus']:.2f}",
        "FreshSurplus": f"{primary['mean_fresh_economic_surplus']:.2f}",
        "RetentionMinutes": f"{60 * threshold['minimum_cash_labor_hours_saved_per_use']:.2f}",
        "WorldHistories": economics["world_rows"],
    }
    source_files = [
        "confirmation/results/frozen-v1/summary.json",
        "economics/results/results.json",
        "integration/results/frozen-v1/summary.json",
        "hosted_trials/scoring.json",
        "protocols/source-freeze.json",
    ]
    record = {
        "purpose": "display values read from archived results, not new experimental evidence",
        "values": values,
        "sources": {name: hashlib.sha256((STUDY / name).read_bytes()).hexdigest() for name in source_files},
    }
    (PAPER / "source-results.json").write_text(json.dumps(record, indent=2) + "\n")
    (PAPER / "results.tex").write_text(
        "% Generated from archived evidence by build_paper.py.\n"
        + "".join(f"\\newcommand{{\\{name}}}{{{value}}}\n" for name, value in values.items())
    )
    manuscript = (PAPER / "manuscript.md").read_text()
    (PAPER / "body.md").write_text(manuscript[manuscript.index("# A measurement worth carrying forward") :])
    subprocess.run(
        [
            "pandoc",
            "body.md",
            "--from",
            "markdown",
            "--to",
            "latex",
            "--standalone",
            "--template",
            "template.tex",
            "--lua-filter",
            "pagebreaks.lua",
            "--output",
            "paper.tex",
        ],
        cwd=PAPER,
        check=True,
    )
    for _ in range(2):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
            cwd=PAPER,
            capture_output=True,
            text=True,
            check=True,
        )
    (PAPER / "build.log").write_text(result.stdout)
    forbidden = ("Overfull", "Missing character", "LaTeX Error", "Font shape")
    failures = [item for item in forbidden if item in result.stdout]
    if failures:
        raise ValueError(f"Publication rendering diagnostics require inspection: {failures}")
    print(json.dumps({"compiled": "paper.pdf", "source_bound_values": values}, indent=2))


if __name__ == "__main__":
    main()
