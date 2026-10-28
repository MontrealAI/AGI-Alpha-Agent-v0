# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
O = ["protected-data-local", "original-purpose"]

def step(name, requires, produces, cost=10, seconds=10, permission="documented", preserves=None):
    return dict(step_id=name, purpose=name, requires=requires, produces=produces,
                preserves=O if preserves is None else preserves, permission=permission,
                permission_basis="Authored synthetic declaration; no external approval exists",
                estimated_cost_micro_usd=cost, duration_seconds=seconds)

def problem(family, v, steps, goals=None, cost=200, seconds=200, nodes=20000):
    return dict(mission_id=f"fresh-{family}-{v}", useful_purpose="Produce a checked conditional feasibility packet",
                starting_facts=["start"], required_outputs=goals or ["output"], obligations=O,
                steps=steps, cost_cap_micro_usd=cost, seconds_cap=seconds, search_node_cap=nodes,
                mode="synthetic", limitations="Authored finite monotone facts; approvals, capacity, wait times and policy interpretation are unverified")

cases = []
for v in range(4):
    cases.append(problem("shared-fork", v, [step("shared",["start"],["ready"],10+v),
        step("left",["ready"],["left-output"],11), step("right",["ready"],["right-output"],12),
        step("bypass-left",["start"],["left-output"],0,preserves=[O[1]]),
        step("bypass-right",["start"],["right-output"],0,permission="denied")], ["left-output","right-output"]))
    cases.append(problem("approval-cost", v, [step("cheap-pending",["start"],["output"],1,1,"required"),
        step("approved-a",["start"],["mid"],30+v), step("approved-b",["mid"],["output"],30),
        step("bad-zero",["start"],["output"],0,1,preserves=[O[0]])]))
    cases.append(problem("cycle-entry", v, [step("cycle-a",["b"],["a"],5),
        step("cycle-b",["a"],["b"],5), step("entry",["start"],["a"],5+v,
        permission="denied" if v%2 else "documented"), step("finish",["b"],["output"],5)]))
    cases.append(problem("two-output-choice", v, [step("shared",["start"],["a","b"],20+v),
        step("left",["a"],["x"],5), step("right",["b"],["y"],5),
        step("separate-x",["start"],["x"],20), step("separate-y",["start"],["y"],20),
        step("joint-pending",["start"],["x","y"],1,1,"required")], ["x","y"]))
    cases.append(problem("binding-cost", v, [step("first",["start"],["mid"],10,8),
        step("last",["mid"],["output"],10,8),step("expensive",["start"],["output"],30,1)],cost=[19,20,29,30][v]))
    cases.append(problem("binding-time", v, [step("slow-a",["start"],["mid"],1,10),
        step("slow-b",["mid"],["output"],1,10),step("fast",["start"],["output"],25,19)],cost=20,seconds=[19,20,21,1][v]))
    cases.append(problem("denied-obligation", v, [step("raw-transfer",["start"],["output"],0,1,preserves=[O[1]]),
        step("denied",["start"],["output"],0,1,"denied"),
        step("pending-safe",["start"],["ready"],5,5,"required"),
        step("safe-finish",["ready"],["output"],5,5,"denied" if v%2 else "documented")]))
    cases.append(problem("search-budget", v, [step("branch-a",["start"],["a"],1),
        step("branch-b",["start"],["b"],1),step("finish",["a","b"],["output"],1)],nodes=1+v))

encoded = json.dumps(cases, sort_keys=True, separators=(",", ":")).encode()
freeze = dict(schema="fresh-conventional-challenge-freeze/v1", created_at=datetime.now(timezone.utc).isoformat(),
    target_commit="095c11fe33522be6c0e2d7a00043d7bbb5bcb457", target_git_blob="058fea1672a06b6b0a1253aa7d78f56f8a86e7c1",
    cases_sha256=hashlib.sha256(encoded).hexdigest(), case_count=len(cases),
    requirements=["Same original purpose, declared facts, action set, goals, obligations, cost/time/node caps",
        "Independent exact conventional construction may use every established primitive and a subset/topological solver",
        "Minimize pending approvals, then cost, time and lexicographic step sequence",
        "No authority, customer acceptance or actual scientific experiment follows from a plan",
        "Incomplete search never establishes infeasibility or optimality"],
    acceptance=dict(validated_contract=True, exact_rank_and_sequence_on_complete_pairs=True,
        independent_witness_check=True, illegal_shortcuts_refused=True, counters_and_incomplete_preserved=True),
    resource_ceiling=dict(wall_minutes=35,campaign_cpu_seconds=90,output_bytes=10000000,paid_external_calls=0),
    stop_rules=["Stop novelty claim on competent ordinary parity", "Stop on resource ceiling without replacing cases",
        "Preserve every failure; no outcome-based substitution or rerun"],
    attribution="Execution comparison only; not a discovery-search, real-buyer or frontier-model experiment",
    logical_budget_caveat="A conventional subset examination and a target recursive state visit are algorithm-specific units, not matched CPU or monetary costs",
    cases=cases)
path=ROOT/"FROZEN_CASES.json"
if path.exists(): raise SystemExit("freeze already exists")
path.write_text(json.dumps(freeze,indent=2,sort_keys=True)+"\n")
print(json.dumps(dict(freeze_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cases_sha256=freeze["cases_sha256"],cases=len(cases))))
