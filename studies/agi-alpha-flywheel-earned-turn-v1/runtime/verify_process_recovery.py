# SPDX-License-Identifier: Apache-2.0
"""Read-only verification of the actual process probe, without replaying either mission."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from review.checker import check


def identity(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def verify(directory):
    load = lambda name: json.loads((directory / name).read_text())
    report, calls = load("PROCESS_RECOVERY.json"), load("process-calls.json")
    a, b, recovered = load("A-terminal.json"), load("B-terminal.json"), load("duplicate-recovery.json")
    assert report["status"] == "PASS" and all(report["checks"].values())
    assert [r["actual_exit"] for r in calls] == [23, 0]
    assert (directory / "first.stdout").read_bytes() == b""
    assert load("A-worker.json")["pid"] != load("B-worker.json")["pid"]
    assert identity(a["receipt"]) == a["receipt_digest"] == recovered["receipt_digest"]
    assert identity(b["receipt"]) == b["receipt_digest"]
    assert a["accepted"] and b["accepted"] and recovered["execute"] is False
    checks = {}
    for mid, terminal in (("A", a), ("B", b)):
        task, values, pack = load(mid + "-task.json"), load(mid + "-solution.json"), load(mid + "-pack.json")
        result = check(task, values)
        assert result["valid"]
        assert identity(task) == terminal["receipt"]["task_digest"]
        assert identity(values) == terminal["receipt"]["solution_digest"]
        body = {k: v for k, v in pack.items() if k != "integrityDigest"}
        packed = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        pack_digest = hashlib.sha256(("successor-omega/v1:workbench-pack\0" + packed).encode()).hexdigest()
        assert pack_digest == pack["integrityDigest"] == terminal["receipt"]["pack_digest"]
        assert pack["evaluation"]["authority"] == [] and pack["evaluation"]["admission"] == "HOLD"
        checks[mid] = result
    assert a["receipt"]["solution_digest"] != b["receipt"]["solution_digest"]
    factor_receipt = load("parent-receipt.json")
    assert hashlib.sha256((directory / "parent.npz").read_bytes()).hexdigest() == factor_receipt["sha256"]
    head = "0" * 64
    for index, line in enumerate((directory / "custody" / "journal.jsonl").read_text().splitlines()):
        event = json.loads(line)
        body = {k: v for k, v in event.items() if k != "hash"}
        assert event["sequence"] == index and event["previous"] == head and identity(body) == event["hash"]
        head = event["hash"]
    anchors = [json.loads(line) for line in (directory / "custody" / "anchor.jsonl").read_text().splitlines()]
    assert anchors[-1] == {"sequence": index, "head": head}
    executions = [json.loads(line) for line in (directory / "execution-events.jsonl").read_text().splitlines()]
    assert [e["mission"] for e in executions] == ["A", "B"]
    return {"status": "PASS", "scope": "read-only raw evidence and fresh checker reinspection; no mission replay",
        "pids": [e["pid"] for e in executions], "historical_receipt_digest": recovered["receipt_digest"],
        "numerical_checks": checks, "final_journal_head": head, "recorded_children_cpu_ms": report["total_children_cpu_ms"],
        "authority": [], "institutional_independence": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = verify(args.directory)
    (args.directory / "READ_ONLY_VERIFICATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
