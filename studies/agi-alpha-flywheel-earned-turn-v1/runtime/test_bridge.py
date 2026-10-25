# SPDX-License-Identifier: Apache-2.0
"""Source-bound checks of actual callback dispatch, refusal and cancellation."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path

from workbench_client import WorkbenchClient, WorkbenchError


def main() -> None:
    started = time.time()
    root = Path(__file__).parent
    source = hashlib.sha256((root / "workbench_bridge.mjs").read_bytes() + (root / "workbench_client.py").read_bytes()).hexdigest()
    rows = []
    calls = []

    def compute(data):
        calls.append(data)
        return {"valid": True, "qualified": True, "summary": "Two finite values summed by the dispatched callback.",
                "value": sum(data["values"])}

    with WorkbenchClient() as client:
        result = client.run("bridge-development-01", "Check exact dispatch.", {"values": [0.25, 1.75]}, compute, source)
        assert calls == [{"values": [0.25, 1.75]}] and result["callback_calls"] == 1
        assert json.loads(result["pack"]["result"]["artifacts"][0]["content"])["value"] == 2.0
        rows.append({"case": "actual_callback_after_workbench_dispatch", "passed": True})
        assert result["inspection"]["activeProof"] == [] and result["inspection"]["activeAuthority"] == []
        assert result["pack"]["evaluation"]["admission"] == "HOLD"
        rows.append({"case": "proof_authority_not_transferred", "passed": True})
        inspected = client.inspect(result["pack"])
        assert inspected["authentication"] == "UNAUTHENTICATED_HISTORICAL_IMPORT" and len(calls) == 1
        rows.append({"case": "history_inspection_without_reexecution", "passed": True})
        changed = copy.deepcopy(result["pack"])
        changed["result"]["summary"]["description"] = "forged"
        try:
            client.inspect(changed)
            raise AssertionError("forged pack accepted")
        except WorkbenchError as error:
            assert "PACK_INTEGRITY" in str(error)
        rows.append({"case": "invalid_receipt_refused", "passed": True})
        try:
            client.run("bridge-development-01", "Duplicate", {"values": [1]}, compute, source)
            raise AssertionError("duplicate ran")
        except WorkbenchError as error:
            assert "DUPLICATE_OR_INVALID_REQUEST" in str(error) and len(calls) == 1
        rows.append({"case": "duplicate_request_no_callback", "passed": True})
        try:
            client.run("bridge-bad-source", "Invalid source", {"values": [1]}, compute, "not-a-source")
            raise AssertionError("bad source ran")
        except WorkbenchError as error:
            assert "SOURCE_IDENTITY_REQUIRED" in str(error) and len(calls) == 1
        rows.append({"case": "invalid_source_identity_no_callback", "passed": True})
        def fail(_):
            raise ValueError("injected development callback failure")
        refused = client.run("bridge-callback-failure", "Retain failed computation", {}, fail, source)
        assert refused["pack"]["result"]["decision"] == "REFUSED" and refused["callback_calls"] == 1
        assert refused["callback_failure"]["class"] == "ValueError"
        rows.append({"case": "callback_failure_retained_as_refusal", "passed": True})
        try:
            client.run("bridge-stop-before", "STOP before computation", {"values": [1]}, compute, source, cancelled=lambda: True)
            raise AssertionError("stopped run passed")
        except WorkbenchError as error:
            assert str(error) == "CANCELLED" and error.receipt["callback_calls"] == 0 and len(calls) == 1
        rows.append({"case": "stop_before_callback", "passed": True})
        stopped = [False]
        def finish_then_stop(data):
            report = compute(data)
            stopped[0] = True
            return report
        try:
            client.run("bridge-stop-after", "STOP after pure work", {"values": [2]}, finish_then_stop, source, cancelled=lambda: stopped[0])
            raise AssertionError("stopped output admitted")
        except WorkbenchError as error:
            assert str(error) == "CANCELLED" and error.receipt["callback_calls"] == 1
            assert error.receipt["callback_cpu_ms"] >= 0 and len(calls) == 2
        rows.append({"case": "stop_after_work_no_output_admission_cost_retained", "passed": True})
        final = client.run("bridge-after-stop", "New permitted local request", {"values": [3]}, compute, source)
        assert final["pack"]["result"]["decision"] == "QUALIFIED_LOCAL_RESULT"
        rows.append({"case": "explicit_new_request_after_cancel", "passed": True})
        record = {"scope": "development bridge correctness only, not numerical confirmation or native service qualification",
            "source_pair_sha256": source, "started_epoch": started, "elapsed_seconds": time.time() - started,
            "python": sys.version, "node": client.ready["node"], "vendor": client.ready,
            "startup_wall_ms": client.startup_wall_ms, "checks": rows, "passed": len(rows),
            "example_pack": result["pack"], "execution_metrics": {k: v for k, v in result.items() if k not in {"pack", "inspection"}},
            "limitations": ["Serial persistent local process, not a daemon or maintained native CampaignOperation.",
                "The Node source digest alone is not independent numerical proof.",
                "Caller must own durable idempotency, full budgets and process-level recovery; seen IDs are process-local.",
                "Trusted fixed Python callback can run until its own bound; transport does not sandbox arbitrary Python."]}
    destination = root / "development_bridge_tests.json"
    destination.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": len(rows), "source_pair_sha256": source, "record": str(destination)}))


if __name__ == "__main__":
    main()
