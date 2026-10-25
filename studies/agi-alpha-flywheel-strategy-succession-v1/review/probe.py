#!/usr/bin/env python3
"""Frozen development diagnostic of retained regression assets.

Fixture solutions are analytical and fault variants are deliberately seeded.
This is not the main confirmation study or a test of general solver discovery.
"""
from __future__ import annotations
import argparse
import copy
import datetime
import hashlib
import json
import math
import time
from pathlib import Path
from check import check, operation_reserve

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = ["PROBE_PROTOCOL.json", "probe.py", "check.py", "challenge.py", "adjudicate.py",
                "development_cases.py", "run_regressions.py", "regression_assets.json"]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(family, p):
    if family == "routine":
        a, b, c = 2 + p % 3, 1 + p % 3, 1 + p % 2
        jobs = [dict(id="J1",duration=a,crew=2,deps=[]),dict(id="J2",duration=b,crew=1,deps=[]),dict(id="J3",duration=c,crew=2,deps=["J1","J2"])]
        cap, starts = [3]*20, {"J1":0,"J2":0,"J3":max(a,b)}
        t = dict(kind="plan",jobs=jobs,capacity=cap)
        critical, locked = max(a,b)+c, 0
    elif family == "calendar_dip":
        a, gap = 2+p%2, 1+p%2
        jobs = [dict(id="J1",duration=a,crew=2,deps=[]),dict(id="J2",duration=a,crew=2,deps=["J1"])]
        cap, starts = [2]*a+[0]*gap+[2]*(a+2), {"J1":0,"J2":a+gap}
        t = dict(kind="plan",jobs=jobs,capacity=cap)
        critical, locked = 2*a, 0
    elif family == "fixed_prefix":
        a, gap = 2+p%2, 2+p%2
        jobs = [dict(id="J1",duration=a,crew=1,deps=[]),dict(id="J2",duration=2,crew=1,deps=["J1"])]
        starts = {"J1":0,"J2":a+gap}
        t = dict(kind="repair",jobs=jobs,capacity=[1]*20,release={"J2":a+gap},
                 locked={"J1":0},baseline={"J1":0,"J2":a},movement_limit=gap)
        critical, locked = a+gap+2, a
    elif family == "late_lock":
        a, gap = 1+p%3, 2+p%3
        jobs = [dict(id="J1",duration=a,crew=1,deps=[]),dict(id="J2",duration=2,crew=1,deps=["J1"])]
        starts = {"J1":gap,"J2":gap+a}
        t = dict(kind="repair",jobs=jobs,capacity=[1]*20,locked={"J1":gap},baseline=starts.copy(),movement_limit=0)
        critical, locked = gap+a+2, gap+a
    elif family == "released_root":
        gap = 3+p%3
        jobs = [dict(id="J1",duration=2,crew=1,deps=[]),dict(id="J2",duration=2,crew=1,deps=["J1"])]
        starts = {"J1":gap,"J2":gap+2}
        t = dict(kind="plan",jobs=jobs,capacity=[1]*20,release={"J1":gap})
        critical, locked = gap+4, 0
    else:
        raise ValueError(family)
    t.update(schema="release-plan/v1", id=f"prospective-dev-{family}-{p}",
             public_or_synthetic="synthetic", planning_only=True)
    schedule = [dict(id=j["id"],start=starts[j["id"]],end=starts[j["id"]]+j["duration"]) for j in jobs]
    makespan = max(row["end"] for row in schedule)
    required = sum(j["duration"]*j["crew"] for j in jobs)
    accumulated, load = 0, None
    for i,c in enumerate(t["capacity"]):
        accumulated += c
        if load is None and accumulated >= required:
            load = i+1
    value = max(critical,load,locked)
    movement = sum(abs(starts[j]-t["baseline"][j]) for j in starts) if t["kind"] == "repair" else 0
    r = dict(schema="release-plan-result/v1",task_id=t["id"],schedule=schedule,makespan=makespan,movement=movement,
             lower_bound=dict(value=value,critical=critical,load=load,locked=locked),optimal_by_lower_bound=makespan==value,
             dispatch_order=[j["id"] for j in jobs if j["id"] not in t.get("locked",{})],lookahead_steps=0,proof=[],authority=[])
    return dict(task=t,result=r)


def creator(envelope, faults):
    """Known fault injection into a fixture solution; not arbitrary planning."""
    e = copy.deepcopy(envelope)
    t,r = e["task"],e["result"]
    jobs = {j["id"]:j for j in t["jobs"]}
    rows = {row["id"]:row for row in r["schedule"]}
    if "calendar" in faults and 0 in t["capacity"]:
        for row in r["schedule"]:
            deps = jobs[row["id"]]["deps"]
            if deps:
                row["start"] = max(rows[d]["end"] for d in deps)
                row["end"] = row["start"]+jobs[row["id"]]["duration"]
    if "prefix" in faults and t.get("locked"):
        jid = next(iter(t["locked"]))
        rows[jid]["start"] += 1
        rows[jid]["end"] += 1
    if "bound" in faults and t.get("locked"):
        finishes = {}
        pending = t["jobs"][:]
        while pending:
            for j in pending[:]:
                if all(d in finishes for d in j["deps"]):
                    finishes[j["id"]] = max([t.get("release",{}).get(j["id"],0)]+[finishes[d] for d in j["deps"]])+j["duration"]
                    pending.remove(j)
        r["lower_bound"]["critical"] = max(finishes.values())
        r["lower_bound"]["value"] = max(r["lower_bound"][k] for k in ("critical","load","locked"))
    if "release" in faults:
        roots = [j["id"] for j in t["jobs"] if not j["deps"] and t.get("release",{}).get(j["id"],0)>0]
        if roots:
            # Deliberately shift the complete release-constrained chain early.
            for row in r["schedule"]:
                row["start"] -= 1
                row["end"] -= 1
    r["makespan"] = max(row["end"] for row in r["schedule"])
    r["movement"] = sum(abs(row["start"]-t["baseline"][row["id"]]) for row in r["schedule"]) if t["kind"] == "repair" else 0
    r["optimal_by_lower_bound"] = r["makespan"] == r["lower_bound"]["value"]
    return e, len(canonical(r))


def freeze():
    dest = ROOT / "PROBE_FREEZE.json"
    if dest.exists():
        raise SystemExit("Existing development-probe freeze is immutable; use a new named edition for changes.")
    protocol = json.loads((ROOT/"PROBE_PROTOCOL.json").read_text())
    inputs = [fixture(x["family"],x["parameter"]) for x in protocol["fresh_case_order"]]
    data = dict(scope="development diagnostic only; not main confirmatory freeze",
                frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                files={name:sha(ROOT/name) for name in SOURCE_FILES},
                public_diagnostic_input_sha256=hashlib.sha256(canonical(inputs)).hexdigest(),
                outcomes_evaluated_before_freeze=False)
    dest.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(dict(status="FROZEN_DEVELOPMENT_PROBE",freeze_sha256=sha(dest)),indent=2))


def run():
    started = time.perf_counter()
    freeze_path = ROOT / "PROBE_FREEZE.json"
    frozen = json.loads(freeze_path.read_text())
    for name,expected in frozen["files"].items():
        if sha(ROOT/name) != expected:
            raise SystemExit("Frozen source mismatch: "+name)
    output, events_path = ROOT/"PROBE_RESULTS.json", ROOT/"PROBE_EVENTS.jsonl"
    if output.exists() or events_path.exists():
        raise SystemExit("Existing probe evidence will not be overwritten.")
    protocol = json.loads((ROOT/"PROBE_PROTOCOL.json").read_text())
    assets = json.loads((ROOT/"regression_assets.json").read_text())
    fresh = [fixture(x["family"],x["parameter"]) for x in protocol["fresh_case_order"]]
    assert hashlib.sha256(canonical(fresh)).hexdigest() == frozen["public_diagnostic_input_sha256"]
    retained = [x["revision"] for x in assets["assets"]]
    totals, calls, work = [], 0, 0
    with events_path.open("x") as journal:
        for arm in protocol["arms"]:
            has_assets = arm != "no_early_assets"
            retrieval = (ROOT/"regression_assets.json").stat().st_size if has_assets else 0
            work += retrieval
            arm_results = []
            for candidate in protocol["candidate_order"]:
                pipeline = ([("retained",x) for x in retained] if has_assets else []) + [("fresh",x) for x in fresh]
                cost, checks, failed = 0, 0, None
                for stage,base in pipeline:
                    envelope, creation = creator(base,candidate["faults"])
                    reserve = creation+operation_reserve(envelope)
                    if calls+1 > protocol["stopping"]["max_checker_calls"] or work+reserve > protocol["stopping"]["max_reference_work"]:
                        raise RuntimeError("Precommitted probe budget exhausted before invocation")
                    if time.perf_counter()-started > protocol["stopping"]["max_elapsed_seconds"]:
                        raise RuntimeError("Precommitted probe deadline exhausted")
                    verdict = check(envelope)
                    actual = creation+verdict["counts"]["total"]
                    assert actual <= reserve
                    cost += actual
                    work += actual
                    calls += 1
                    checks += 1
                    event = dict(arm=arm,candidate=candidate["id"],stage=stage,task_id=envelope["task"]["id"],
                                 evidence=envelope,independent_check=verdict,creator_reference_work=creation,
                                 total_reference_work=actual,reserved_reference_work=reserve)
                    journal.write(json.dumps(event,separators=(",",":"))+"\n")
                    journal.flush()
                    if not verdict["valid"] or not verdict["qualified"]:
                        failed = dict(stage=stage,task_id=envelope["task"]["id"],errors=verdict["errors"])
                        break
                arm_results.append(dict(candidate=candidate["id"],accepted=failed is None,
                                        checker_calls=checks,screening_reference_work=cost,first_failure=failed))
            screening = sum(x["screening_reference_work"] for x in arm_results)
            fixed = assets["acquisition_plus_retention_reference_work"] if has_assets else 0
            totals.append(dict(arm=arm,candidates=arm_results,checker_calls=sum(x["checker_calls"] for x in arm_results),
                               screening_reference_work=screening,retrieval_reference_work=retrieval,
                               acquisition_and_retention_reference_work=fixed,
                               total_reference_work=screening+retrieval+fixed))
    first, inherited, conventional = totals
    assert [x["accepted"] for x in first["candidates"]] == [x["accepted"] for x in inherited["candidates"]] == [x["accepted"] for x in conventional["candidates"]]
    assert inherited["candidates"] == conventional["candidates"]
    assert inherited["total_reference_work"] == conventional["total_reference_work"]
    recurring_saving = first["screening_reference_work"]-inherited["screening_reference_work"]-inherited["retrieval_reference_work"]
    fixed = inherited["acquisition_and_retention_reference_work"]
    break_even = math.ceil(fixed/recurring_saving) if recurring_saving>0 else None
    result = dict(schema="regression-screening-probe-result/v1",scope=protocol["scope"],
                  status="COMPLETED",freeze_sha256=sha(freeze_path),arms=totals,
                  conclusions=dict(admission_decisions_identical=True,conventional_asset_arm_identical=True,
                                   no_final_correctness_improvement_established=True,
                                   screening_work_saved=first["screening_reference_work"]-inherited["screening_reference_work"],
                                   first_batch_net_work_saved=first["total_reference_work"]-inherited["total_reference_work"],
                                   recurring_work_saved_after_retrieval=recurring_saving,
                                   modeled_repeated_identical_batches_to_cover_acquisition_and_retention=break_even),
                  actual_total_checker_calls=calls,execution_reference_work_excluding_prior_asset_acquisition=work,
                  elapsed_seconds=time.perf_counter()-started,
                  limitations=protocol["analysis"],protected_confirmation_used=False,
                  raw_events_sha256=sha(events_path))
    output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(status="COMPLETED",checker_calls=calls,conclusions=result["conclusions"],
                         elapsed_seconds=result["elapsed_seconds"]),indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action",choices=("freeze","run"))
    args = parser.parse_args()
    freeze() if args.action == "freeze" else run()
