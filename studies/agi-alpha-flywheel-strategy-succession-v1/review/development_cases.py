"""Hand-authored, public synthetic DEVELOPMENT fixtures, never confirmation."""
from copy import deepcopy


def plan():
    task = dict(schema="release-plan/v1", id="review-dev-plan", kind="plan",
                jobs=[dict(id="J1", duration=4, crew=2, deps=[]),
                      dict(id="J2", duration=3, crew=1, deps=[]),
                      dict(id="J3", duration=2, crew=2, deps=["J1", "J2"])],
                capacity=[3] * 16, release={}, locked={}, deadline=7,
                public_or_synthetic="synthetic", planning_only=True)
    result = dict(schema="release-plan-result/v1", task_id=task["id"],
                  schedule=[dict(id="J1", start=0, end=4), dict(id="J2", start=0, end=3),
                            dict(id="J3", start=4, end=6)], makespan=6, movement=0,
                  lower_bound=dict(value=6, critical=6, load=5, locked=0),
                  optimal_by_lower_bound=True, dispatch_order=["J1", "J2", "J3"],
                  lookahead_steps=0, proof=[], authority=[])
    return dict(task=task, result=result)


def repair():
    e = plan()
    t, r = e["task"], e["result"]
    t.update(id="review-dev-repair", kind="repair", baseline={"J1": 0, "J2": 0, "J3": 4},
             locked={"J1": 0, "J2": 0}, release={"J3": 4}, deadline=8, movement_limit=2)
    t["capacity"][4:6] = [1, 1]
    r.update(task_id=t["id"], makespan=8, movement=2,
             lower_bound=dict(value=7, critical=6, load=7, locked=4),
             optimal_by_lower_bound=False, dispatch_order=["J3"])
    r["schedule"][2].update(start=6, end=8)
    return e


def calendar_dip():
    task = dict(schema="release-plan/v1", id="review-dev-calendar-dip", kind="plan",
                jobs=[dict(id="J1", duration=2, crew=2, deps=[]),
                      dict(id="J2", duration=2, crew=2, deps=["J1"])],
                capacity=[2, 2, 0, 0, 2, 2], deadline=6)
    result = dict(schema="release-plan-result/v1", task_id=task["id"],
                  schedule=[dict(id="J1", start=0, end=2), dict(id="J2", start=4, end=6)],
                  makespan=6, movement=0, lower_bound=dict(value=6, critical=4, load=6, locked=0),
                  optimal_by_lower_bound=True, dispatch_order=["J1", "J2"],
                  lookahead_steps=0, proof=[], authority=[])
    return dict(task=task, result=result)


def late_lock():
    task = dict(schema="release-plan/v1", id="review-dev-late-lock", kind="repair",
                jobs=[dict(id="J1", duration=2, crew=1, deps=[]),
                      dict(id="J2", duration=3, crew=1, deps=["J1"])],
                capacity=[1] * 12, locked={"J1": 5}, baseline={"J1": 5, "J2": 7},
                deadline=10, movement_limit=0)
    result = dict(schema="release-plan-result/v1", task_id=task["id"],
                  schedule=[dict(id="J1", start=5, end=7), dict(id="J2", start=7, end=10)],
                  makespan=10, movement=0, lower_bound=dict(value=10, critical=10, load=5, locked=7),
                  optimal_by_lower_bound=True, dispatch_order=["J2"],
                  lookahead_steps=0, proof=[], authority=[])
    return dict(task=task, result=result)


def mutation_cases():
    """Name, input envelope, expected diagnostic; targeted meaningful defects."""
    cases = []
    def add(name, factory, mutation, code):
        e = factory()
        mutation(e["task"], e["result"])
        cases.append((name, e, code))
    add("wrong_duration", plan, lambda t,r: r["schedule"][0].update(end=3), "WRONG_DURATION")
    add("calendar_overload", calendar_dip, lambda t,r: (r["schedule"][1].update(start=2,end=4), r.update(makespan=4,optimal_by_lower_bound=False)), "CAPACITY_OVERLOAD")
    add("dependency_before_finish", plan, lambda t,r: (r["schedule"][2].update(start=3,end=5),r.update(makespan=5,optimal_by_lower_bound=False)), "DEPENDENCY_VIOLATION")
    add("missing_job", plan, lambda t,r: r["schedule"].pop(), "SCHEDULE_COMPLETENESS")
    add("extra_assignment", plan, lambda t,r: r["schedule"].append(dict(id="J4",start=0,end=1)), "SCHEDULE_COMPLETENESS")
    add("unknown_job", plan, lambda t,r: r["schedule"][1].update(id="J999"), "UNKNOWN_SCHEDULE_JOB")
    add("duplicate_assignment", plan, lambda t,r: r["schedule"][1].update(id="J1"), "DUPLICATE_ASSIGNMENT")
    add("moved_locked_prefix", repair, lambda t,r: (r["schedule"][0].update(start=1,end=5),r.update(movement=3)), "LOCK_VIOLATION")
    add("false_bound", plan, lambda t,r: r["lower_bound"].update(value=7), "BOUND_MISMATCH")
    add("unpropagated_locked_critical_path", late_lock, lambda t,r: (r.update(lower_bound=dict(value=7,critical=5,load=5,locked=7),optimal_by_lower_bound=False)), "BOUND_MISMATCH")
    add("false_optimality", repair, lambda t,r: r.update(optimal_by_lower_bound=True), "OPTIMAL_FLAG_MISMATCH")
    add("missing_bound_component", plan, lambda t,r: r["lower_bound"].pop("locked"), "BOUND_FORMAT")
    add("wrong_makespan", plan, lambda t,r: r.update(makespan=7), "MAKESPAN_MISMATCH")
    add("wrong_movement", repair, lambda t,r: r.update(movement=1), "MOVEMENT_MISMATCH")
    add("inherited_proof", plan, lambda t,r: r.update(proof=["old-pass"]), "NONEMPTY_PROOF")
    add("inherited_authority", plan, lambda t,r: r.update(authority=["production"]), "NONEMPTY_AUTHORITY")
    add("implicit_proof", plan, lambda t,r: r.pop("proof"), "NONEMPTY_PROOF")
    add("task_substitution", plan, lambda t,r: r.update(task_id="different-task"), "TASK_BINDING")
    add("boolean_start", plan, lambda t,r: r["schedule"][0].update(start=False), "INTEGER_SCOPE")
    add("fractional_end", plan, lambda t,r: r["schedule"][0].update(end=4.5), "INTEGER_SCOPE")
    add("outside_horizon", plan, lambda t,r: r["schedule"][2].update(start=15,end=17), "INTEGER_SCOPE")
    add("negative_start", plan, lambda t,r: r["schedule"][0].update(start=-1,end=3), "INTEGER_SCOPE")
    add("duplicate_task_job", plan, lambda t,r: t["jobs"][1].update(id="J1"), "DUPLICATE_JOB")
    add("unknown_dependency", plan, lambda t,r: t["jobs"][2].update(deps=["J999"]), "UNKNOWN_DEPENDENCY")
    add("cyclic_dependencies", plan, lambda t,r: t["jobs"][0].update(deps=["J3"]), "DEPENDENCY_CYCLE")
    add("duplicate_dependency", plan, lambda t,r: t["jobs"][2].update(deps=["J1","J1"]), "DUPLICATE_DEPENDENCY")
    add("bad_job_id", plan, lambda t,r: t["jobs"][0].update(id="J01"), "JOB_ID")
    add("boolean_duration", plan, lambda t,r: t["jobs"][0].update(duration=True), "INTEGER_SCOPE")
    add("duration_outside_scope", plan, lambda t,r: t["jobs"][0].update(duration=13), "INTEGER_SCOPE")
    add("crew_outside_scope", plan, lambda t,r: t["jobs"][0].update(crew=5), "INTEGER_SCOPE")
    add("fractional_calendar", plan, lambda t,r: t["capacity"].__setitem__(0,2.5), "INTEGER_SCOPE")
    add("insufficient_total_calendar", plan, lambda t,r: t.update(capacity=[0]*16), "INSUFFICIENT_CALENDAR_WORK")
    add("horizon_mismatch", plan, lambda t,r: t.update(horizon=15), "HORIZON_MISMATCH")
    add("baseline_missing_job", repair, lambda t,r: t["baseline"].pop("J3"), "BASELINE_COMPLETENESS")
    add("baseline_lock_disagreement", repair, lambda t,r: t["baseline"].update(J1=1), "LOCK_BASELINE_MISMATCH")
    add("nonclosed_locked_prefix", repair, lambda t,r: t.update(locked={"J3":4}), "LOCK_PREFIX_NOT_CLOSED")
    add("plan_with_baseline", plan, lambda t,r: t.update(baseline={"J1":0,"J2":0,"J3":4}), "PLAN_BASELINE")
    add("plan_with_nonempty_locks", plan, lambda t,r: t.update(locked={"J1":0}), "PLAN_LOCKS")
    add("plan_with_movement_limit", plan, lambda t,r: t.update(movement_limit=0), "PLAN_MOVEMENT_LIMIT")
    add("lock_before_release", repair, lambda t,r: t.update(release={"J1":1}), "LOCK_RELEASE_CONFLICT")
    add("locked_predecessor_timing_conflict", late_lock, lambda t,r: (t["locked"].update(J2=6),t["baseline"].update(J2=6)), "LOCK_DEPENDENCY_CONFLICT")
    add("release_beyond_horizon", plan, lambda t,r: t.update(release={"J1":15}), "CRITICAL_PATH_OUTSIDE_HORIZON")
    add("result_dispatch_missing", plan, lambda t,r: r.update(dispatch_order=["J1","J2"]), "DISPATCH_COMPLETENESS")
    add("result_dispatch_dependency", plan, lambda t,r: r.update(dispatch_order=["J3","J1","J2"]), "DISPATCH_PRECEDENCE")
    add("result_dispatch_duplicates", plan, lambda t,r: r.update(dispatch_order=["J1","J1","J3"]), "DISPATCH_JOB")
    add("result_dispatch_locked", repair, lambda t,r: r.update(dispatch_order=["J1","J3"]), "DISPATCH_COMPLETENESS")
    add("too_many_lookahead_placements", plan, lambda t,r: r.update(lookahead_steps=4), "INTEGER_SCOPE")
    return cases
