# SPDX-License-Identifier: Apache-2.0
"""Measure fresh approved-source jobs without replacing predecessor evidence."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HELPER = HERE / "measure-corrected-processes.py"
CLI = HERE / "run-mission.mjs"
REF = "d12e955909cb5b52a5225c39d4f7fab4a5f93d50"


def main() -> None:
    label = sys.argv[1] if len(sys.argv) == 2 else "final-successor"
    if len(sys.argv) > 2 or not re.fullmatch(r"[a-z][a-z0-9-]{0,23}", label):
        raise ValueError("Use one explicit bounded observation label.")
    output_path = HERE / ("report-recovery-" + label + "-measurements.json")
    if output_path.exists():
        raise FileExistsError("Retain previous observations; choose a new measurement identity.")
    spec = importlib.util.spec_from_file_location("alpha_predecessor_measurement", HELPER)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    reports = []
    for manifest, run_id in (
        ("docs/try/sources.json", "report-" + label + "-guide-d12"),
        ("docs/successor/alpha/sources.json", "report-" + label + "-flagship-d12"),
    ):
        planned, planning = helper.measured(
            ["node", str(CLI), "plan", "--manifest", manifest, "--ref", REF, "--run-id", run_id]
        )
        arguments = [
            "node",
            str(CLI),
            "run",
            "--plan",
            planned["planFile"],
            "--approve",
            planned["approvalDigest"],
        ]
        delivery, operation = helper.measured(arguments)
        reconnected, reconnect = helper.measured(arguments)
        assert delivery["accepted"] and reconnected["reconnected"]
        reports.append(
            {
                "runId": run_id,
                "manifestPath": manifest,
                "sourceRef": REF,
                "methodIdentity": delivery["methodIdentity"],
                "dependencySha256": planned["plan"]["dependencySha256"],
                "planning": planning,
                "newDelivery": operation,
                "reconnect": reconnect,
            }
        )
    report = {
        "schema": "alpha-report-recovery-successor-observations/v1",
        "runnerSha256": hashlib.sha256(CLI.read_bytes()).hexdigest(),
        "measurementSourceSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "measurementHelperSha256": hashlib.sha256(HELPER.read_bytes()).hexdigest(),
        "predecessorRunnerSha256": "b41247af80a42213398c82120ef481dc139c793cec457b52fb3e58df94ec7824",
        "predecessorEvidence": "corrected-external-process-measurements.json",
        "distinctSourceScopes": 2,
        "newDeliveries": 2,
        "reconnectRequests": 2,
        "runs": reports,
        "limits": [
            "Fresh source revision of the existing two inventory scope families; not two new offering types.",
            "Foreground local Node only; no authenticated approved-executor or deployment qualification.",
            "Whole-process resource observations include launch and waited Git children; money remains unknown.",
            "New recovery regressions establish the repaired interruption boundary, not economic superiority.",
        ],
    }
    with output_path.open("x") as output:
        output.write(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "newDeliveries": 2,
                "sourceRef": REF,
                "runnerSha256": report["runnerSha256"],
                "methodIdentity": reports[0]["methodIdentity"],
            }
        )
    )


if __name__ == "__main__":
    main()
