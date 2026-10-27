# SPDX-License-Identifier: Apache-2.0
"""Build a self-contained bilingual evidence edition from actual study records."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def lower_bound(passed: int, count: int) -> float:
    z = 1.6448536269514722
    p = passed / count
    return (p + z * z / (2 * count) - z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count))) / (
        1 + z * z / count
    )


def policy_times(record: dict[str, Any], split: str) -> dict[str, float]:
    """Measured full compositions: no reconstruction or duplicated assembly."""
    rows = record["summary"][split]
    return {
        label: rows[method]["seconds_total"] * 32 / rows[method]["n"]
        for label, method in (
            ("beta", "adaptive_fallback"),
            ("work", "work48_fallback"),
            ("gym", "gym48_fallback"),
        )
    }


def build(technical: Path, selection: Path | None, output: Path) -> None:
    results = json.loads((technical / "technical_results.json").read_text())
    summaries = results["summary"]
    for rows in summaries.values():
        for row in rows.values():
            row["wilson_lower95"] = lower_bound(row["accepted"], row["n"])
    fallback_path = technical / "fallback_results.json"
    fallback = json.loads(fallback_path.read_text())
    inputs = [technical / "technical_results.json", technical / "confirmation.csv", technical / "shift.csv", fallback_path]
    selected = None
    if selection and selection.is_file():
        selected = json.loads(selection.read_text())
        inputs.append(selection)
    recipient = technical.parent / "results" / "recipient_transfer.json"
    if recipient.is_file():
        inputs.append(recipient)
    economic_protocol = HERE.parent / "protocol" / "economic_protocol.json"
    contract = json.loads(economic_protocol.read_text())
    inputs.append(economic_protocol)
    payload = {
        "technical": results,
        "selection": selected,
        "fallback": fallback,
        "workflow_contracts": [
            {
                "id": offer["id"],
                "kernel_seconds": offer["core_deadline_seconds"],
                "workflow_seconds": offer["model_seconds_assumed"],
                "reserved_seconds": offer["core_deadline_seconds"] + offer["model_seconds_assumed"],
            }
            for offer in contract["offers"]
        ],
        "policy_seconds_per32": {
            "confirmation": policy_times(fallback, "confirmation"),
            "shift": policy_times(fallback, "shift"),
        },
        "source_run": technical.name,
        "source_manifest": [
            {"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
            for p in inputs
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    html = (HERE / "template.html").read_text().replace("__STUDY_DATA__", raw)
    output.write_text(html)
    (HERE / "source_manifest.json").write_text(json.dumps(payload["source_manifest"], indent=2) + "\n")
    print(json.dumps({"html": str(output), "bytes": output.stat().st_size, "source_run": technical.name}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--technical", type=Path, required=True)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--output", type=Path, default=HERE / "index.html")
    options = parser.parse_args()
    build(options.technical, options.selection, options.output)
