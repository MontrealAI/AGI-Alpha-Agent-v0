# SPDX-License-Identifier: Apache-2.0
"""Reproduce scoped development checks and observed local runtime evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy
import scipy

HERE = Path(__file__).resolve().parent
OPPORTUNITY = HERE.parent
REPOSITORY = OPPORTUNITY.parents[2]
sys.path.insert(0, str(OPPORTUNITY / "instrument"))
import model_reuse as instrument

SOURCE = OPPORTUNITY / "discovery/science/source_checkout/petab_select/test_cases/0009/petab"


def main() -> None:
    started = datetime.now(timezone.utc).isoformat()
    code = OPPORTUNITY / "instrument/model_reuse.py"
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_model_reuse.py", "-v"],
        [sys.executable, "-m", "ruff", "check", str(code), str(HERE / "test_model_reuse.py")],
        [sys.executable, "-m", "mypy", "--strict", "--ignore-missing-imports", str(code)],
    ]
    validation = []
    for index, command in enumerate(commands):
        before = time.perf_counter()
        result = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, check=False)
        elapsed = time.perf_counter() - before
        log = HERE / f"validation_{index + 1}.log"
        log.write_text(result.stdout + result.stderr)
        validation.append({"argv": command, "returncode": result.returncode, "wall_seconds": elapsed, "log": log.name})
    info = instrument.inventory(SOURCE)
    calibration = {
        "model_fingerprint": info["source_fingerprint"],
        "scope_id": "development-only",
        "scale_per_physical_unit": [0.7, 1.9],
        "physical_unit": "minute",
        "evidence_kind": "assumed",
        "evidence_id": "development-hypothesis-not-a-physical-measurement",
    }
    missions = [
        {"mission_id": "development-inventory", "type": "inventory"},
        {"mission_id": "development-stationary", "type": "stationary"},
        {"mission_id": "development-clock", "type": "clock_witness", "scales": [0.37, 2.31], "time": 1.27},
        {"mission_id": "development-selected-bound", "type": "dimension_bound"},
        {"mission_id": "development-full-bound", "type": "dimension_bound", "kinetic_parameters": 33},
        {
            "mission_id": "development-calibration",
            "scope_id": "development-only",
            "type": "response",
            "quantity": "spectral_relaxation_time",
            "time_basis": "physical",
            "calibration": calibration,
        },
    ]
    observations = []
    for mission in missions:
        before = time.perf_counter()
        result = instrument.qualify(mission, SOURCE)
        observations.append({"request": mission, "wall_seconds": time.perf_counter() - before, "receipt": result})
    report = {
        "evidence_kind": "observed_local_execution_of_researcher_authored_instrument",
        "stage": "development_before_fresh_confirmation",
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "code_sha256": hashlib.sha256(code.read_bytes()).hexdigest(),
        "validation": validation,
        "all_validation_passed": all(item["returncode"] == 0 for item in validation),
        "development_missions_executed": len(observations),
        "observations": observations,
        "accounting": {
            "classification": "C: unpaid additional research and development; not paid-job learning",
            "provider_charge_usd": None,
            "model_tokens": None,
            "human_attention_minutes": None,
            "customer_collections_usd": 0,
            "reason_unknown": "Hosted agent token billing and researcher-attention telemetry are not exposed.",
            "runtime_caveat": "Single-run local timings include parsing and numerical work; no provider inference, queueing or complete customer delivery is measured.",
        },
        "confirmation_claimed": False,
        "biological_validation_claimed": False,
        "authority": [],
    }
    (HERE / "development_results.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        json.dumps({"passed": report["all_validation_passed"], "validation": validation, "missions": len(observations)})
    )
    if not report["all_validation_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
