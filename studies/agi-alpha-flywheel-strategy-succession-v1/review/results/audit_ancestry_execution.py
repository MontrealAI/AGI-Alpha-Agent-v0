#!/usr/bin/env python3
"""Clarify retained ancestry versus observed parent use in frozen diagnostic data."""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / "results" / "confirmation-v1"
sys.path.insert(0, str(ROOT / "review"))
from check import check  # Independent, frozen artifact checker only.


def read(path):
    return json.loads(path.read_text())


def digest(strategy):
    text = json.dumps(strategy, ensure_ascii=False, separators=(",", ":"))
    text = json.dumps(text, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(("successor-omega/v1:release-strategy\0" + text).encode()).hexdigest()


def case(record, path, line_number):
    row, task = record["row"], record["task"]
    checked = check({"task": task, "result": row["result"]})
    assert checked["valid"] == row["valid"] and checked["qualified"] == row["qualified"]
    result = row["result"]
    return {
        "task_id": task["id"], "raw_path": path, "raw_line": line_number,
        "phase": record["phase"], "strategy": record["strategy"],
        "valid": checked["valid"], "qualified": checked["qualified"],
        "deadline": task.get("deadline", len(task["capacity"])),
        "movement_limit": task.get("movement_limit"),
        "makespan": result["makespan"], "movement": result["movement"],
        "result_lookahead_steps": result["lookahead_steps"],
        "parent_dispatch_rollouts": row["counts"].get("strategy:inherited-dispatch-rollout", 0),
        "parent_lookahead_decisions": row["counts"].get("strategy:inherited-lookahead-decision", 0),
        "repair_policy_entries": row["counts"].get("strategy:repair-policy-entry", 0),
        "charged_work": row["work"],
    }


prior = read(HERE / "MAIN_INDEPENDENT_AUDIT.json")
assert prior["status"] == "PASS" and (RUN / "RUN_COMPLETE.json").exists()
prior_hashes = {r["path"]: r["sha256"] for r in prior["raw_evidence_hashes"]}
trials = [json.loads(line) for line in (RUN / "trials.jsonl").read_text().splitlines()]
diagnostic = { (r["stream"], r["parent_treatment"]): r for r in trials if r["category"] == "diagnostic" }
breakdown = collections.defaultdict(collections.Counter)
streams = []
hashes = {}
checked_records = 0
for number in range(1, 13):
    stream = f"diagnostic-{number:02d}"
    item = {"stream": stream, "treatments": {}}
    for treatment in ["inherited", "removed", "rebuild", "equivalent"]:
        trial = diagnostic[stream, treatment]
        relative = trial["artifact_path"] + "/raw.jsonl.gz"
        actual_hash = hashlib.sha256((RUN / relative).read_bytes()).hexdigest()
        assert actual_hash == prior_hashes[relative]
        hashes[relative] = actual_hash
        with gzip.open(RUN / relative, "rt") as source:
            rows = [(i, json.loads(line)) for i, line in enumerate(source, 1)]
        fresh = [(i, r) for i, r in rows if r["phase"] == "mission"]
        assert len(fresh) == 4
        fresh_cases = [case(r, relative, i) for i, r in fresh]
        checked_records += len(fresh_cases)
        qualification = [(i, r) for i, r in rows if r["phase"] == "qualification" and isinstance(r["strategy"], dict) and r["strategy"].get("kind") == "repair"]
        qualification_cases = [case(r, relative, i) for i, r in qualification]
        checked_records += len(qualification_cases)
        assets = {a["stage"]: a for a in trial["assets"]}
        if treatment != "removed":
            assert len(qualification_cases) == 4
            assert all(digest(c["strategy"]) == assets["repair"]["digest"] for c in qualification_cases)
            assert digest(fresh_cases[3]["strategy"]) == assets["repair"]["digest"]
        item["treatments"][treatment] = {
            "fresh": fresh_cases,
            "selected_repair_qualification": qualification_cases,
            "retained_repair_mode": assets.get("repair", {}).get("strategy", {}).get("mode"),
        }
        if treatment == "inherited":
            retained = {a["digest"] for a in trial["assets"]}
            for _, record in rows:
                selected = isinstance(record["strategy"], dict) and digest(record["strategy"]) in retained
                category = record["phase"] + (":eventually_retained_strategy" if selected else ":other_strategy")
                accumulator = breakdown[category]
                accumulator["evaluations"] += 1
                accumulator["parent_dispatch_rollouts"] += record["row"]["counts"].get("strategy:inherited-dispatch-rollout", 0)
                accumulator["parent_lookahead_decisions"] += record["row"]["counts"].get("strategy:inherited-lookahead-decision", 0)
    streams.append(item)

inherited = [s["treatments"]["inherited"] for s in streams]
lookahead_cases = [r["fresh"][2] for r in inherited]
repair_cases = [r["fresh"][3] for r in inherited]
repair_qualification = [c for r in inherited for c in r["selected_repair_qualification"]]
aggregate = {
    "typed_three_stage_lineages": 12,
    "retained_repair_modes": dict(collections.Counter(r["retained_repair_mode"] for r in inherited)),
    "fresh_lookahead_cases": len(lookahead_cases),
    "fresh_lookahead_cases_calling_dispatch": sum(c["parent_dispatch_rollouts"] > 0 for c in lookahead_cases),
    "fresh_lookahead_dispatch_rollouts": sum(c["parent_dispatch_rollouts"] for c in lookahead_cases),
    "fresh_lookahead_qualified_and_calling_dispatch": sum(c["qualified"] and c["parent_dispatch_rollouts"] > 0 for c in lookahead_cases),
    "fresh_repair_cases": len(repair_cases),
    "fresh_repair_qualified": sum(c["qualified"] for c in repair_cases),
    "fresh_repair_cases_calling_lookahead": sum(c["parent_lookahead_decisions"] > 0 for c in repair_cases),
    "fresh_repair_lookahead_decisions": sum(c["parent_lookahead_decisions"] for c in repair_cases),
    "fresh_repair_qualified_and_calling_lookahead": sum(c["qualified"] and c["parent_lookahead_decisions"] > 0 for c in repair_cases),
    "selected_repair_qualification_cases": len(repair_qualification),
    "selected_repair_qualification_cases_calling_lookahead": sum(c["parent_lookahead_decisions"] > 0 for c in repair_qualification),
    "selected_repair_qualification_lookahead_decisions": sum(c["parent_lookahead_decisions"] for c in repair_qualification),
    "selected_repair_qualification_qualified_and_calling_lookahead": sum(c["qualified"] and c["parent_lookahead_decisions"] > 0 for c in repair_qualification),
    "selected_repair_qualification_qualified_with_result_lookahead_steps": sum(c["qualified"] and c["result_lookahead_steps"] > 0 for c in repair_qualification),
}
assert sum(v["parent_lookahead_decisions"] for v in breakdown.values()) == 86
assert sum(v["parent_dispatch_rollouts"] for v in breakdown.values()) == 2411
result = {
    "schema": "agi-alpha-ancestry-execution-scope-audit/v1", "status": "PASS_WITH_SCOPE_CLARIFICATION",
    "scientific_source_hash": prior["source_hash"], "top_freeze_sha256": prior["top_freeze_sha256"],
    "audit_source_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    "no_new_experiments": True, "independent_artifact_rechecks": checked_records,
    "aggregate": aggregate, "inherited_all_research_call_breakdown": dict(breakdown),
    "streams": streams, "raw_hashes_unchanged_since_main_audit": hashes,
    "interpretation": [
        "Twelve typed ancestry chains do not establish twelve fresh deep uses of a repair predecessor.",
        "All twelve fresh lookahead missions invoke the retained dispatch parent; three qualify.",
        "Four selected-repair qualification outputs qualify and invoke lookahead. They are qualification evidence, not the subsequent fresh repair missions.",
        "Only one fresh repair invokes lookahead, and it fails qualification. Zero fresh repairs both qualify and invoke that parent.",
        "The 86 aggregate repair-parent decisions include 44 calls by other or losing discovery candidates; aggregate research calls do not establish retained productive dependency.",
        "Stream 10 has a descriptive fresh lookahead makespan improvement from 50 to 47 while both treatments qualify; all twelve paired outcomes are retained to avoid selecting only this favorable case.",
    ],
    "independence_limits": "Parent-call counters are producer instrumentation, independently attributed and summed here. Output validity and qualification are checked by the separate frozen checker. This review does not independently trace CPU execution or rerun parent-removal experiments. A recorded call proves neither that the parent was necessary nor that the full investment paid back.",
}
(HERE / "ANCESTRY_EXECUTION_AUDIT.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "aggregate": aggregate, "breakdown": dict(breakdown), "checked_records": checked_records}))
