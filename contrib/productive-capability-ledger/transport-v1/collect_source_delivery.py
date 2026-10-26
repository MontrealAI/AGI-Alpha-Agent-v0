# SPDX-License-Identifier: Apache-2.0
"""Bind actual source browser and recovery receipts to the existing CI handoff."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


def collect(root: Path, output: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "planning_collector", root / "contrib/strategy_succession/qa/collect_qualification.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("source-worker.xml", "source-browser.xml"):
        module.verify_junit(output / name)
    source = output / "source-candidate"
    browser = json.loads((source / "source-browser-acceptance.json").read_text())
    recovery = json.loads((source / "unattended-recovery.json").read_text())
    server = json.loads((source / "server-sigkill-recovery.json").read_text())
    cancelled = json.loads((source / "server-cancel-recovery.json").read_text())
    stopped = json.loads((source / "server-stop-recovery.json").read_text())
    assert stopped["passed"] and stopped["permanentStop"] and stopped["orphanSawCancellationMarker"]
    assert stopped["chargedAttempts"] == 1 and stopped["reservationRetained"] == 2
    assert stopped["originalLeaseUnchanged"] and stopped["source_hash"] == server["source_hash"]
    assert cancelled["passed"] and cancelled["cancelledAfterOriginalWriterExit"]
    assert cancelled["chargedAttempts"] == 1 and cancelled["reservationRetained"] == 2
    assert cancelled["nextSeparatelyApprovedMissionAccepted"] and cancelled["originalLeaseUnchanged"]
    assert cancelled["source_hash"] == server["source_hash"]
    assert server["passed"] and server["serverSignal"] == "SIGKILL"
    assert server["originalSourceChildSurvived"] and server["waitingConsumedNoAttempt"]
    assert server["originalLeaseUnchanged"] and server["attemptsCharged"] == 2
    assert server["source_hash"] == recovery["source_hash"]
    planning = json.loads((output / "qualification.json").read_text())
    assert browser["passed"] and browser["checks"]["realFixedWorker"]
    assert browser["checks"]["sameMissionReconnect"] and browser["checks"]["independentAcceptance"]
    assert browser["tabClosedDuringActiveWork"] is True
    assert browser["executedSource"] == planning["commit"]
    assert recovery["passed"] and recovery["actualWorkerSignal"] == "SIGKILL"
    assert recovery["originalLeaseUnchanged"] and recovery["checkpointBytesUnchanged"]
    assert recovery["conservativeServiceCharge"] == len(recovery["attempts"]) == 2
    assert recovery["result"]["independentAcceptance"]["accepted"]
    assert recovery["result"]["accounting"]["schema"] == "alpha-automated-costs/v1"
    assert all(
        s["costs"]["fullyLoadedMicrosPerAccepted"] is None for s in recovery["result"]["costSummary"]["scenarios"]
    )
    inputs = (
        "source-worker.xml",
        "source-browser.xml",
        "qualification.json",
        "source-candidate/unattended-recovery.json",
        "source-candidate/server-sigkill-recovery.json",
        "source-candidate/server-cancel-recovery.json",
        "source-candidate/server-stop-recovery.json",
        "source-candidate/source-browser-acceptance.json",
        "source-candidate/source-customer-result.zip",
        "source-candidate/source-signed-history.json",
    )
    return {
        "schema": "alpha-source-connected-qualification/v1",
        "commit": planning["commit"],
        "passed": True,
        "scope": "Isolated CI candidate installation; real browser and real source worker.",
        "sourceBrowserHash": browser["sourceHash"],
        "sourceRecoveryHash": recovery["source_hash"],
        "differentProfileBindings": "Default one-attempt browser scope versus explicit two-attempt recovery scope; no approval transfer.",
        "approvedOperator": "NOT RUN",
        "operationalAdoption": "NOT APPROVED",
        "newHeldOutDiversity": False,
        "fullMonetaryCost": None,
        "inputs": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in inputs},
    }


if __name__ == "__main__":
    root, output = map(Path, sys.argv[1:])
    result = collect(root, output)
    (output / "source-qualification.json").write_text(json.dumps(result, indent=2) + "\n")
