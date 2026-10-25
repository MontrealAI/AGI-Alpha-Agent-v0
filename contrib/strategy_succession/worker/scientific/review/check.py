#!/usr/bin/env python3
"""Independent release-plan/v1 artifact checker; JSONL {task,result} in/out.

No solver, interpreter, strategy, or primary-checker imports. Abstract operation
counts follow README.md; they are not Python bytecode or elapsed-time claims.
"""
from __future__ import annotations
import json
import re
import sys

JOB_ID = re.compile(r"J[1-9][0-9]{0,2}\Z")
MAX_LINE_BYTES = 262144


class Audit:
    def __init__(self, envelope):
        self.errors = []
        self.c = dict(input_bytes=0, input_fields=0, job_scans=0,
                      dependency_edges=0, calendar_slots=0, interval_slots=0,
                      comparisons=0, arithmetic=0, map_operations=0)
        try:
            raw = json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            self.c["input_bytes"] = len(raw)
            self.walk(envelope)
        except (TypeError, ValueError, RecursionError):
            self.fail("INVALID_JSON_VALUE", "$", "Only finite JSON values are permitted.")

    def walk(self, obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                self.c["input_fields"] += 1
                self.walk(value)
        elif isinstance(obj, list):
            for value in obj:
                self.c["input_fields"] += 1
                self.walk(value)

    def fail(self, code, path, message):
        if len(self.errors) < 64:
            self.errors.append(dict(code=code, path=path, message=message))

    def require(self, condition, code, path, message):
        self.c["comparisons"] += 1
        if not condition:
            self.fail(code, path, message)
        return bool(condition)

    def integer(self, value, low, high, path):
        self.c["comparisons"] += 3
        if type(value) is not int or value < low or value > high:
            self.fail("INTEGER_SCOPE", path, f"Expected an integer in [{low}, {high}].")
            return False
        return True

    def finish(self, lower=None, qualified=False, optimal=False):
        counts = {**self.c, "total": sum(self.c.values())}
        return dict(valid=not self.errors, qualified=qualified and not self.errors,
                    lower_bound=lower, counts=counts, errors=self.errors,
                    optimal_if_bound=optimal and not self.errors)


def check(envelope):
    a = Audit(envelope)
    if a.errors:
        return a.finish()
    if not a.require(isinstance(envelope, dict), "ENVELOPE_TYPE", "$", "Expected task/result object."):
        return a.finish()
    task, result = envelope.get("task"), envelope.get("result")
    a.c["map_operations"] += 2
    if not a.require(isinstance(task, dict), "TASK_TYPE", "task", "Task must be an object."):
        return a.finish()
    a.require(task.get("schema") == "release-plan/v1", "TASK_SCHEMA", "task.schema", "Expected release-plan/v1.")
    a.require(isinstance(task.get("id"), str) and 1 <= len(task["id"]) <= 128,
              "TASK_ID", "task.id", "Task id must be a nonempty string of at most 128 characters.")
    a.require(task.get("kind") in ("plan", "repair"), "TASK_KIND", "task.kind", "Expected plan or repair.")
    jobs, capacity = task.get("jobs"), task.get("capacity")
    a.require(isinstance(jobs, list) and 1 <= len(jobs) <= 18,
              "JOB_COUNT", "task.jobs", "Expected 1..18 jobs.")
    a.require(isinstance(capacity, list) and 1 <= len(capacity) <= 128,
              "HORIZON", "task.capacity", "Expected 1..128 calendar slots.")
    if a.errors:
        return a.finish()
    horizon = len(capacity)
    if "horizon" in task:
        a.require(type(task["horizon"]) is int and task["horizon"] == horizon,
                  "HORIZON_MISMATCH", "task.horizon", "Horizon must equal calendar length.")
    for i, value in enumerate(capacity):
        a.c["calendar_slots"] += 1
        a.integer(value, 0, 4, f"task.capacity[{i}]")
    deadline = task.get("deadline", horizon)
    a.integer(deadline, 1, horizon, "task.deadline")
    by_id, order = {}, []
    for i, job in enumerate(jobs):
        a.c["job_scans"] += 1
        path = f"task.jobs[{i}]"
        if not a.require(isinstance(job, dict), "JOB_TYPE", path, "Job must be an object."):
            continue
        jid = job.get("id")
        good_id = a.require(isinstance(jid, str) and JOB_ID.fullmatch(jid) is not None,
                            "JOB_ID", path + ".id", "Expected J followed by 1..999 without leading zero.")
        if good_id:
            a.c["map_operations"] += 1
            if a.require(jid not in by_id, "DUPLICATE_JOB", path + ".id", "Each job must be unique."):
                by_id[jid] = job
                order.append(jid)
                a.c["map_operations"] += 1
        a.integer(job.get("duration"), 1, 12, path + ".duration")
        a.integer(job.get("crew"), 1, 4, path + ".crew")
        deps = job.get("deps")
        if a.require(isinstance(deps, list) and len(deps) <= 17,
                     "DEPENDENCIES_TYPE", path + ".deps", "Dependencies must be a list of at most 17 ids."):
            seen = set()
            for d in deps:
                a.c["dependency_edges"] += 1
                if a.require(isinstance(d, str), "DEPENDENCY_ID", path + ".deps", "Dependency ids must be strings."):
                    a.require(d not in seen, "DUPLICATE_DEPENDENCY", path + ".deps", "A dependency may occur only once.")
                    seen.add(d)
                    a.c["map_operations"] += 2
    if a.errors:
        return a.finish()
    for jid in order:
        for d in by_id[jid]["deps"]:
            a.c["dependency_edges"] += 1
            a.c["map_operations"] += 1
            a.require(d in by_id, "UNKNOWN_DEPENDENCY", "task.jobs." + jid + ".deps", "Dependency must name a declared job.")
            a.require(d != jid, "SELF_DEPENDENCY", "task.jobs." + jid + ".deps", "A job cannot depend on itself.")
    release, locked = task.get("release", {}), task.get("locked", {})
    baseline = task.get("baseline", {})
    repair = task["kind"] == "repair"
    for field, mapping in (("release", release), ("locked", locked), ("baseline", baseline)):
        if not a.require(isinstance(mapping, dict), "MAPPING_TYPE", "task." + field, "Expected id-to-integer mapping."):
            continue
        for jid, value in mapping.items():
            a.c["map_operations"] += 1
            if a.require(jid in by_id, "UNKNOWN_MAPPING_JOB", "task." + field, "Mapping key must name a declared job."):
                upper = horizon - 1 if field == "release" else horizon - by_id[jid]["duration"]
                a.c["arithmetic"] += field != "release"
                a.integer(value, 0, upper, "task." + field + "." + jid)
    movement_limit = task.get("movement_limit", 2304)
    if repair:
        a.require("baseline" in task, "BASELINE_REQUIRED", "task.baseline", "Repair requires the original starts of every job.")
        if isinstance(baseline, dict):
            a.require(set(baseline) == set(by_id), "BASELINE_COMPLETENESS", "task.baseline", "Baseline must contain exactly all jobs.")
            a.c["map_operations"] += len(baseline) + len(by_id)
        a.integer(movement_limit, 0, 2304, "task.movement_limit")
    else:
        a.require(not locked, "PLAN_LOCKS", "task.locked", "Plan accepts no nonempty locks.")
        a.require("baseline" not in task, "PLAN_BASELINE", "task.baseline", "Baseline is a repair-only field.")
        a.require("movement_limit" not in task, "PLAN_MOVEMENT_LIMIT", "task.movement_limit", "Movement limit is repair-only.")
    if a.errors:
        return a.finish()
    for jid, start in locked.items():
        a.c["job_scans"] += 1
        a.require(start == baseline[jid], "LOCK_BASELINE_MISMATCH", "task.locked." + jid, "Locked starts must equal original starts.")
        a.require(start >= release.get(jid, 0), "LOCK_RELEASE_CONFLICT", "task.locked." + jid, "Locked start precedes release.")
        for d in by_id[jid]["deps"]:
            a.c["dependency_edges"] += 1
            a.c["map_operations"] += 1
            a.require(d in locked, "LOCK_PREFIX_NOT_CLOSED", "task.locked." + jid, "Every predecessor of a locked job must be locked.")
    if a.errors:
        return a.finish()

    # Deliberately simple reference topological pass, with explicit visits.
    topo, done = [], set()
    while len(topo) < len(order):
        progressed = False
        for jid in order:
            a.c["job_scans"] += 1
            a.c["map_operations"] += 1
            if jid in done:
                continue
            ready = True
            for d in by_id[jid]["deps"]:
                a.c["dependency_edges"] += 1
                a.c["map_operations"] += 1
                if d not in done:
                    ready = False
            if ready:
                done.add(jid)
                topo.append(jid)
                a.c["map_operations"] += 1
                progressed = True
        if not progressed:
            a.fail("DEPENDENCY_CYCLE", "task.jobs", "Dependency graph must be acyclic.")
            return a.finish()
    earliest_finish, critical, locked_bound, work = {}, 0, 0, 0
    for jid in topo:
        a.c["job_scans"] += 1
        job = by_id[jid]
        start = release.get(jid, 0)
        a.c["map_operations"] += 2
        for d in job["deps"]:
            a.c["dependency_edges"] += 1
            a.c["comparisons"] += 1
            a.c["map_operations"] += 1
            start = max(start, earliest_finish[d])
        if jid in locked:
            a.require(locked[jid] >= start, "LOCK_DEPENDENCY_CONFLICT", "task.locked." + jid, "Locked start precedes a predecessor's earliest finish.")
            start = locked[jid]
        end = start + job["duration"]
        earliest_finish[jid] = end
        critical = max(critical, end)
        work += job["duration"] * job["crew"]
        a.c["arithmetic"] += 3
        a.c["comparisons"] += 1
        a.c["map_operations"] += 2
        if jid in locked:
            locked_bound = max(locked_bound, end)
            a.c["comparisons"] += 1
    cumulative, load = 0, None
    for slot, crew in enumerate(capacity):
        a.c["calendar_slots"] += 1
        cumulative += crew
        a.c["arithmetic"] += 1
        a.c["comparisons"] += 1
        if load is None and cumulative >= work:
            load = slot + 1
            a.c["arithmetic"] += 1
    a.require(load is not None, "INSUFFICIENT_CALENDAR_WORK", "task.capacity", "Calendar capacity is below total required crew-work.")
    a.require(critical <= horizon, "CRITICAL_PATH_OUTSIDE_HORIZON", "task.jobs", "Release/dependency/lock lower bound exceeds the declared horizon.")
    if a.errors:
        return a.finish()
    lower = dict(value=max(critical, load, locked_bound), critical=critical, load=load, locked=locked_bound)
    a.c["comparisons"] += 2

    if not a.require(isinstance(result, dict), "RESULT_TYPE", "result", "Result must be an object."):
        return a.finish(lower)
    a.require(result.get("schema") == "release-plan-result/v1", "RESULT_SCHEMA", "result.schema", "Expected release-plan-result/v1.")
    a.require(result.get("task_id") == task["id"], "TASK_BINDING", "result.task_id", "Result must name the exact task id.")
    for field in ("proof", "authority"):
        value = result.get(field)
        a.require(isinstance(value, list) and len(value) == 0,
                  "NONEMPTY_" + field.upper(), "result." + field, "Current proof and authority must be explicitly empty.")
    reported_lb = result.get("lower_bound")
    if a.require(isinstance(reported_lb, dict) and set(reported_lb) == set(lower),
                 "BOUND_FORMAT", "result.lower_bound", "Expected value, critical, load and locked bounds."):
        for key, value in lower.items():
            a.require(type(reported_lb[key]) is int and reported_lb[key] == value,
                      "BOUND_MISMATCH", "result.lower_bound." + key, "Reported registered bound differs from independently derived bound.")
    makespan_ok = a.integer(result.get("makespan"), 1, horizon, "result.makespan")
    movement_ok = a.integer(result.get("movement"), 0, 2304, "result.movement")
    a.integer(result.get("lookahead_steps"), 0, len(order), "result.lookahead_steps")
    a.require(type(result.get("optimal_by_lower_bound")) is bool,
              "OPTIMAL_FLAG_TYPE", "result.optimal_by_lower_bound", "Expected a Boolean bound-equality flag.")
    schedule = result.get("schedule")
    if not a.require(isinstance(schedule, list) and len(schedule) == len(order),
                     "SCHEDULE_COMPLETENESS", "result.schedule", "Schedule must contain exactly one row per job."):
        return a.finish(lower)
    intervals = {}
    for index, row in enumerate(schedule):
        a.c["job_scans"] += 1
        path = f"result.schedule[{index}]"
        if not a.require(isinstance(row, dict), "SCHEDULE_ROW", path, "Assignment must be an object."):
            continue
        jid = row.get("id")
        if not a.require(isinstance(jid, str) and jid in by_id, "UNKNOWN_SCHEDULE_JOB", path + ".id", "Assignment must name a declared job."):
            continue
        if not a.require(jid not in intervals, "DUPLICATE_ASSIGNMENT", path + ".id", "Job may be assigned only once."):
            continue
        start_ok = a.integer(row.get("start"), 0, horizon - 1, path + ".start")
        end_ok = a.integer(row.get("end"), 1, horizon, path + ".end")
        a.c["map_operations"] += 2
        if start_ok and end_ok:
            intervals[jid] = (row["start"], row["end"])
            a.require(row["end"] - row["start"] == by_id[jid]["duration"],
                      "WRONG_DURATION", path, "End minus start must equal the declared duration.")
            a.c["arithmetic"] += 1
    a.require(set(intervals) == set(by_id), "MISSING_ASSIGNMENT", "result.schedule", "Every declared job needs one valid assignment.")
    if a.errors:
        return a.finish(lower)
    usage, actual_makespan, actual_movement = [0] * horizon, 0, 0
    for jid in order:
        a.c["job_scans"] += 1
        start, end = intervals[jid]
        job = by_id[jid]
        a.require(start >= release.get(jid, 0), "RELEASE_VIOLATION", "result.schedule." + jid, "Job begins before release.")
        if jid in locked:
            a.require(start == locked[jid], "LOCK_VIOLATION", "result.schedule." + jid, "Locked job must retain its exact original start.")
        for d in job["deps"]:
            a.c["dependency_edges"] += 1
            a.require(intervals[d][1] <= start, "DEPENDENCY_VIOLATION", "result.schedule." + jid, "A predecessor has not finished at job start.")
        for slot in range(start, end):
            a.c["interval_slots"] += 1
            usage[slot] += job["crew"]
            a.c["arithmetic"] += 1
        actual_makespan = max(actual_makespan, end)
        a.c["comparisons"] += 1
        if repair:
            actual_movement += abs(start - baseline[jid])
            a.c["arithmetic"] += 3
    for slot, required in enumerate(usage):
        a.c["calendar_slots"] += 1
        a.require(required <= capacity[slot], "CAPACITY_OVERLOAD", f"result.schedule.slot[{slot}]", "Concurrent crew demand exceeds the exact calendar slot.")
    a.require(result["makespan"] == actual_makespan, "MAKESPAN_MISMATCH", "result.makespan", "Makespan must equal the latest actual end.")
    a.require(result["movement"] == actual_movement, "MOVEMENT_MISMATCH", "result.movement", "Movement must equal total absolute deviation from baseline, or zero for plan.")
    a.require(result["optimal_by_lower_bound"] == (actual_makespan == lower["value"]),
              "OPTIMAL_FLAG_MISMATCH", "result.optimal_by_lower_bound", "Flag must exactly report equality with the independently validated bound.")
    dispatch = result.get("dispatch_order")
    expected = [jid for jid in order if jid not in locked]
    if a.require(isinstance(dispatch, list) and len(dispatch) == len(expected),
                 "DISPATCH_COMPLETENESS", "result.dispatch_order", "Dispatch trace must contain exactly the unlocked jobs."):
        dispatched = set(locked)
        for i, jid in enumerate(dispatch):
            a.c["job_scans"] += 1
            if not a.require(isinstance(jid, str) and jid in by_id and jid not in dispatched,
                             "DISPATCH_JOB", f"result.dispatch_order[{i}]", "Dispatch jobs must be known, unlocked and unique."):
                continue
            for d in by_id[jid]["deps"]:
                a.c["dependency_edges"] += 1
                a.require(d in dispatched, "DISPATCH_PRECEDENCE", "result.dispatch_order", "Dispatch order must respect dependency readiness.")
            dispatched.add(jid)
            a.c["map_operations"] += 1
        a.require(dispatched == set(order), "DISPATCH_MISSING", "result.dispatch_order", "Dispatch trace omits a job.")
    qualified = actual_makespan <= deadline and actual_movement <= movement_limit
    a.c["comparisons"] += 2
    # Failing a deadline or movement target is an unqualified feasible plan,
    # not an invalid artifact. These conditions are intentionally separate.
    return a.finish(lower, qualified, actual_makespan == lower["value"])


def _reject_constant(value):
    raise ValueError("Nonfinite JSON number: " + value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def decode_input(raw):
    return json.loads(raw, parse_constant=_reject_constant, object_pairs_hook=_unique_object)


def operation_reserve(envelope):
    """Conservative reference-work reserve; caller charges reservation work.

    B is canonical UTF-8 input bytes. Scope limits make graph passes bounded;
    every nested JSON field occupies at least one input byte. Valid n,H,E give
    a tighter reserve; malformed sizes are capped because validation exits.
    """
    raw = json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    task = envelope.get("task", {}) if isinstance(envelope, dict) else {}
    if not isinstance(task, dict):
        task = {}
    jobs, capacity = task.get("jobs", []), task.get("capacity", [])
    n = min(18, len(jobs)) if isinstance(jobs, list) else 0
    h = min(128, len(capacity)) if isinstance(capacity, list) else 0
    edges = 0
    if isinstance(jobs, list):
        for job in jobs[:18]:
            if isinstance(job, dict) and isinstance(job.get("deps"), list):
                edges += min(17, len(job["deps"]))
    return 2 * len(raw) + 4 * n * n + 220 * n + (2 * n + 50) * edges + 18 * h + 1024


def main():
    for raw in sys.stdin.buffer:
        if len(raw) > MAX_LINE_BYTES:
            out = Audit({})
            out.c["input_bytes"] = len(raw)
            out.fail("INPUT_TOO_LARGE", "$", "JSONL request exceeds 262144 bytes.")
            answer = out.finish()
        else:
            try:
                value = decode_input(raw)
                answer = check(value)
            except (ValueError, UnicodeError, RecursionError) as exc:
                out = Audit({})
                out.c["input_bytes"] = len(raw)
                out.fail("INVALID_JSON", "$", str(exc)[:160])
                answer = out.finish()
        print(json.dumps(answer, separators=(",", ":"), allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
