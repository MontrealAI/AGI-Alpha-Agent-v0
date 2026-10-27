# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use an empty output directory; original experiment receipts are never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    freeze = json.loads((ROOT / "technical/instrument_freeze_1_1.json").read_text())
    for name, expected in freeze["files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Frozen instrument mismatch: {name}")
    for item in json.loads((ROOT / "sources/public_data_sources.json").read_text()):
        if sha(ROOT / item["file"]) != item["sha256"]:
            raise ValueError(f"Source dataset mismatch: {item['id']}")
    mirror = output / "study"
    for directory in ("src", "tests", "sources", "technical/independent_audit"):
        (mirror / directory).mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "data", mirror / "data")
    for name in ("geodelivery.py", "wkt_adapter.py", "confirm_formats.py"):
        shutil.copy2(ROOT / "src" / name, mirror / "src" / name)
    shutil.copy2(ROOT / "tests/test_geodelivery.py", mirror / "tests/test_geodelivery.py")
    shutil.copy2(ROOT / "sources/public_data_sources.json", mirror / "sources/public_data_sources.json")
    shutil.copy2(ROOT / "technical/partition_freeze.json", mirror / "technical/partition_freeze.json")
    for name in ("audit.py", "fresh_confirmation.py", "public_control.py"):
        shutil.copy2(ROOT / "technical/independent_audit" / name, mirror / "technical/independent_audit" / name)
    commands = [
        ["tests/test_geodelivery.py"],
        [
            "src/geodelivery.py",
            "--parks",
            "data/parks.geojson",
            "--facilities",
            "data/facilities.geojson",
            "--sources",
            "sources/public_data_sources.json",
            "--out",
            "technical/delivery",
        ],
        [
            "technical/independent_audit/audit.py",
            "--label",
            "reproduction",
            "--expected-hash",
            freeze["files"]["src/geodelivery.py"],
        ],
        [
            "technical/independent_audit/fresh_confirmation.py",
            "--label",
            "reproduction",
            "--expected-hash",
            freeze["files"]["src/geodelivery.py"],
            "--seed",
            "2026102751",
        ],
        ["technical/independent_audit/public_control.py"],
        ["src/confirm_formats.py", "--out", "technical/gym/fresh_format_missions"],
    ]
    receipts = []
    environment = dict(os.environ, MPLCONFIGDIR=str(output / "mpl-cache"))
    for index, command in enumerate(commands):
        completed = subprocess.run(
            [sys.executable, *command], cwd=mirror, env=environment, text=True, capture_output=True
        )
        (output / f"step_{index + 1}.log").write_text(completed.stdout + completed.stderr)
        receipts.append({"command": command, "returncode": completed.returncode})
        if completed.returncode:
            raise RuntimeError(f"Reproduction step {index + 1} failed; see its preserved log")
    delivery = json.loads((mirror / "technical/delivery/summary.json").read_text())
    baseline = json.loads((ROOT / "technical/delivery/summary.json").read_text())
    control = json.loads((mirror / "technical/independent_audit/public_control_results.json").read_text())
    fresh = json.loads((mirror / "technical/independent_audit/fresh_reproduction.json").read_text())
    formats = json.loads((mirror / "technical/gym/fresh_format_missions/summary.json").read_text())
    expected_formats = json.loads((ROOT / "technical/gym/fresh_format_missions/summary.json").read_text())
    checks = {
        "public_summary_reproduced": delivery == baseline,
        "public_reconciliation_bytes_reproduced": sha(mirror / "technical/delivery/reconciliation.csv")
        == sha(ROOT / "technical/delivery/reconciliation.csv"),
        "independent_public_control_passed": control["passed"],
        "independent_structural_replay_passed": fresh["passed"],
        "format_results_including_failures_reproduced": formats == expected_formats,
    }
    receipt = {
        "reproduced": all(checks.values()),
        "checks": checks,
        "commands": receipts,
        "public_summary": delivery,
        "independent_public_decisions": [control["matched_decisions"], control["sample_count"]],
        "independent_structural_cases": [fresh["accepted_cases"], fresh["case_count"]],
        "format_semantic_parity": [formats["semantic_parity_missions"], formats["missions"]],
        "scope": "Replay of saved policies, sources and seeds. Reproduction does not turn the three format divergences into passes.",
    }
    (output / "reproduction_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    if not receipt["reproduced"]:
        raise RuntimeError("Reproduction mismatch; inspect reproduction_receipt.json")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.out.resolve()), ensure_ascii=False, indent=2))
