# SPDX-License-Identifier: Apache-2.0
"""Compiler and actual job boundary tests, including revoked evidence and replay."""

import pytest
from test_successor_state import ENVIRONMENT, FUTURE, add_release, build_store

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.jobs import JobDispatcher, JobResult, compile_jobs
from alpha_factory_v1.core.runtime.successor.protocol import (
    ExecutionAuthorization,
    JobContract,
    JobDependency,
    JobGraph,
    digest,
)
from alpha_factory_v1.core.runtime.successor.trust import sign_record

FAMILIES = ["constitution", "evidence", "formation", "challenge", "verification", "admission", "renewal"]


def graph(release_digest):
    jobs = []
    for index, family in enumerate(FAMILIES):
        worker = (
            "local-verifier"
            if family in {"challenge", "verification"}
            else "local-controller" if family == "admission" else "local-producer"
        )
        owner = "local-verifier" if worker == "local-controller" else "local-controller"
        jobs.append(
            JobContract(
                job_id=family,
                family=family,
                worker=worker,
                acceptance_owner=owner,
                release_digest=release_digest,
                environment_digest=ENVIRONMENT,
                inputs={"record": "record-v1"} if index else {},
                outputs={"record": "record-v1"},
                critical_functions=[family],
                resources={"calls": 1},
                valid_until=FUTURE,
                max_attempts=2,
                allowed_tools=["fixed"],
                effects=[],
            )
        )
    edges = [
        JobDependency(source=FAMILIES[index - 1], target=family, kind="evidence")
        for index, family in enumerate(FAMILIES)
        if index
    ]
    return JobGraph(jobs=jobs, edges=edges, required_families=FAMILIES, required_functions=FAMILIES)


def authorization(terms, attempt=1):
    return ExecutionAuthorization(
        authorization_id=terms.job_id + "-" + str(attempt),
        acting_identity=terms.worker,
        job_terms_digest=digest("job-terms", terms),
        release_digest=terms.release_digest,
        environment_digest=terms.environment_digest,
        capabilities=["fixed"],
        reservation_id=terms.job_id + "-reservation-" + str(attempt),
        expires_at=FUTURE,
    )


def accept(keys, terms, auth, **changes):
    result = JobResult(
        **{
            "job_id": terms.job_id,
            "authorization_id": auth.authorization_id,
            "terms_digest": digest("job-terms", terms),
            "output_digest": digest("result", {"candidate_verdict": "fail"}),
            "outputs": terms.outputs,
            "accepted": True,
            "accepted_by": terms.acceptance_owner,
            "valid_until": FUTURE,
            "permitted_uses": ["dependency"],
            "candidate_verdict": "fail",
            "actual_resources": {"calls": 1},
            **changes,
        }
    )
    return sign_record(keys[terms.acceptance_owner], terms.acceptance_owner, "job-acceptance", result)


def setup(tmp_path):
    store, keys = build_store(tmp_path, budget=20)
    _, release_digest, _, _ = add_release(store, keys)
    dispatcher = JobDispatcher(store, "institution")
    frozen = graph(release_digest)
    dispatcher.seal(frozen)
    return store, keys, dispatcher, frozen


def test_all_seven_families_execute_actual_tools_and_accept_negative_reports(tmp_path):
    store, keys, dispatcher, frozen = setup(tmp_path)
    executions = []
    for terms in frozen.jobs:
        auth = authorization(terms)
        assignment = sign_record(keys["local-controller"], "local-controller", "execution", auth)
        dispatched = dispatcher.dispatch(terms.job_id, assignment)
        assert dispatcher.dispatch(terms.job_id, assignment)["revision"] == dispatched["revision"]
        result = dispatcher.execute_tool(
            terms.job_id,
            tool="fixed",
            actor=terms.worker,
            invocation_id=terms.job_id,
            handler=lambda current_job=terms.job_id: executions.append(current_job) or {"candidate_verdict": "fail"},
        )
        assert result["candidate_verdict"] == "fail"
        accepted = dispatcher.complete(accept(keys, terms, auth))
        assert accepted["runs"][terms.job_id][-1]["result"]["accepted"]
    assert executions == FAMILIES
    institution = store.read("institution")
    assert institution["resources"]["spent"] == {"calls": 7}
    assert institution["resources"]["reserved"] == {"calls": 0}
    assert institution["serving_release"] is None
    assert store.journal.verify()["valid"]


def test_compiler_rejects_cycles_missing_coverage_role_overlap_and_partial_ports(tmp_path):
    _, _, _, frozen = setup(tmp_path)
    invalid = frozen.model_copy(
        update={
            "edges": frozen.edges
            + [JobDependency(source="renewal", target="constitution", kind="control", principal="local-controller")]
        }
    )
    with pytest.raises(ValueError, match="cyclic"):
        compile_jobs(invalid)
    with pytest.raises(ValueError, match="seven"):
        compile_jobs(frozen.model_copy(update={"jobs": frozen.jobs[:-1]}))
    first = frozen.jobs[0].model_copy(update={"acceptance_owner": frozen.jobs[0].worker})
    with pytest.raises(ValueError, match="separate"):
        compile_jobs(frozen.model_copy(update={"jobs": [first] + frozen.jobs[1:]}))
    second = frozen.jobs[1].model_copy(update={"inputs": {"record": "record-v1", "missing": "missing-v1"}})
    with pytest.raises(ValueError, match="coverage"):
        compile_jobs(frozen.model_copy(update={"jobs": [frozen.jobs[0], second] + frozen.jobs[2:]}))


def test_changed_terms_wrong_actor_and_missing_dependency_block_dispatch(tmp_path):
    store, keys, dispatcher, frozen = setup(tmp_path)
    first, second = frozen.jobs[:2]
    with pytest.raises(ValueError, match="dependency"):
        dispatcher.dispatch(
            second.job_id, sign_record(keys["local-controller"], "local-controller", "execution", authorization(second))
        )
    bad = authorization(first).model_copy(update={"acting_identity": "local-verifier"})
    with pytest.raises(ValueError, match="terms"):
        dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", bad))
    changed = first.model_copy(update={"goal": "changed richer work while legacy spec remains fixed"})
    with pytest.raises(ValueError, match="terms"):
        dispatcher.dispatch(
            first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", authorization(changed))
        )
    assert store.read("institution")["resources"]["reserved"] == {}


def test_revoked_dependency_after_dispatch_blocks_actual_action(tmp_path):
    store, keys, dispatcher, frozen = setup(tmp_path)
    first, second = frozen.jobs[:2]
    auth = authorization(first)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", auth))
    dispatcher.complete(accept(keys, first, auth))
    dispatcher.dispatch(
        second.job_id, sign_record(keys["local-controller"], "local-controller", "execution", authorization(second))
    )
    dispatcher.revoke_dependency(
        sign_record(
            keys["local-controller"],
            "local-controller",
            "job-revocation",
            {"job_id": first.job_id, "reason": "rights revoked"},
        )
    )
    calls = []
    with pytest.raises(ValueError, match="revoked"):
        dispatcher.execute_tool(
            second.job_id,
            tool="fixed",
            actor=second.worker,
            invocation_id="after-revocation",
            handler=lambda: calls.append(True),
        )
    assert not calls
    assert store.read("institution")["denials"][-1]["action_id"] == second.job_id


def test_acceptance_cannot_be_replayed_into_a_retry(tmp_path):
    _, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    one, two = authorization(first), authorization(first, 2)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", one))
    accepted = accept(keys, first, one, accepted=False)
    dispatcher.complete(accepted)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", two))
    with pytest.raises(ValueError, match="different execution"):
        dispatcher.complete(accepted)
    dispatcher.complete(accept(keys, first, two))
    with pytest.raises(Conflict, match="bound"):
        dispatcher.dispatch(
            first.job_id,
            sign_record(keys["local-controller"], "local-controller", "execution", authorization(first, 3)),
        )


def test_job_tool_crash_does_not_repeat_effect(tmp_path):
    _, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    dispatcher.dispatch(
        first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", authorization(first))
    )
    count = []

    def crash():
        count.append(True)
        raise SystemExit("process loss after effect")

    with pytest.raises(SystemExit):
        dispatcher.execute_tool(first.job_id, tool="fixed", actor=first.worker, invocation_id="effect", handler=crash)
    with pytest.raises(Conflict, match="already started"):
        dispatcher.execute_tool(first.job_id, tool="fixed", actor=first.worker, invocation_id="effect", handler=crash)
    with pytest.raises(Conflict, match="uncertain"):
        dispatcher.complete(accept(keys, first, authorization(first)))
    assert count == [True]


def test_interrupted_job_recovery_consumes_bound_once_and_allows_new_attempt(tmp_path):
    store, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    one, two = authorization(first), authorization(first, 2)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", one))
    recovery = sign_record(
        keys["local-controller"],
        "local-controller",
        "job-recovery",
        {
            "institution_id": "institution",
            "job_id": first.job_id,
            "authorization_id": one.authorization_id,
            "reason": "explicit operator resume",
        },
    )
    recovered = dispatcher.recover_job(recovery)
    assert dispatcher.recover_job(recovery)["revision"] == recovered["revision"]
    assert store.read("institution")["resources"]["spent"] == {"calls": 1}
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", two))
    dispatcher.complete(accept(keys, first, two))
    final = store.read("institution")["resources"]
    assert final["spent"] == {"calls": 2} and final["reserved"] == {"calls": 0}
    assert final["unknown"] == [one.authorization_id]


def test_pause_commits_during_pure_work_and_suppresses_invalidated_result(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    store, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    dispatcher.dispatch(
        first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", authorization(first))
    )
    started, release = Event(), Event()

    def bounded():
        started.set()
        assert release.wait(timeout=5)
        return {"must_not_publish": "stale result"}

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            dispatcher.execute_tool,
            first.job_id,
            tool="fixed",
            actor=first.worker,
            invocation_id="pausable",
            handler=bounded,
            retain_result=True,
        )
        assert started.wait(timeout=5)
        store.journal.control(True)
        release.set()
        with pytest.raises(ValueError, match="failed"):
            future.result(timeout=5)
    graph_state = store.journal.latest(dispatcher.key)
    invocation = graph_state["runs"][first.job_id][-1]["tools"]["pausable"]
    assert invocation["state"] == "failed" and invocation["result_digest"] is None
    assert invocation["result_json"] is None


def test_recovery_decision_cannot_close_a_newer_attempt(tmp_path):
    store, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    one, two = authorization(first), authorization(first, 2)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", one))
    recovery = sign_record(
        keys["local-controller"],
        "local-controller",
        "job-recovery",
        {
            "institution_id": "institution",
            "job_id": first.job_id,
            "authorization_id": one.authorization_id,
            "reason": "recover only the interrupted first attempt",
        },
    )
    dispatcher.recover_job(recovery)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", two))
    before = store.journal.verify()
    with pytest.raises(Conflict, match="different execution attempt"):
        dispatcher.recover_job(recovery)
    assert store.journal.verify() == before
    assert store.journal.latest(dispatcher.key)["runs"][first.job_id][-1]["state"] == "running"
    resources = store.read("institution")["resources"]
    assert resources["spent"] == {"calls": 1}
    assert resources["reserved"] == {"calls": 1}
    assert resources["unknown"] == [one.authorization_id]


@pytest.mark.parametrize("binding", ["missing", "other-institution", "other-authorization"])
def test_job_recovery_requires_exact_institution_and_attempt(tmp_path, binding):
    store, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    auth = authorization(first)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", auth))
    payload = {
        "institution_id": "institution",
        "job_id": first.job_id,
        "authorization_id": auth.authorization_id,
        "reason": "operator recovery",
    }
    if binding == "missing":
        del payload["authorization_id"]
    elif binding == "other-institution":
        payload["institution_id"] = "different-institution"
    else:
        payload["authorization_id"] = "different-authorization"
    before = store.journal.verify()
    with pytest.raises((ValueError, Conflict)):
        dispatcher.recover_job(sign_record(keys["local-controller"], "local-controller", "job-recovery", payload))
    assert store.journal.verify() == before
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}


@pytest.mark.parametrize("retain_result", [False, True])
def test_tool_output_retention_is_explicit_and_bound_to_completion(tmp_path, retain_result):
    from alpha_factory_v1.core.runtime.successor.protocol import safe_json_loads

    store, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    dispatcher.dispatch(
        first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", authorization(first))
    )
    expected = {"measurement": [1, 2, 3], "accepted": False}
    assert (
        dispatcher.execute_tool(
            first.job_id,
            tool="fixed",
            actor=first.worker,
            invocation_id="retained",
            handler=lambda: expected,
            retain_result=retain_result,
        )
        == expected
    )
    invocation = store.journal.latest(dispatcher.key)["runs"][first.job_id][-1]["tools"]["retained"]
    assert invocation["state"] == "completed"
    assert invocation["result_digest"] == digest("job-tool-output", expected)
    if retain_result:
        assert safe_json_loads(invocation["result_json"]) == expected
    else:
        assert invocation["result_json"] is None


def test_recovered_attempt_cannot_borrow_a_newer_tool_claim(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import contextmanager
    from threading import Event

    store, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    one, two = authorization(first), authorization(first, 2)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", one))
    original_transaction = store.journal.transaction
    recovered = False
    started, release = Event(), Event()
    old_calls = []
    new_calls = []
    newer = []

    def new_handler():
        new_calls.append(True)
        started.set()
        assert release.wait(timeout=5)
        return {"attempt": 2}

    with ThreadPoolExecutor(max_workers=1) as pool:

        @contextmanager
        def recover_after_claim():
            nonlocal recovered
            with original_transaction() as cx:
                yield cx
            if not recovered:
                recovered = True
                dispatcher.recover_job(
                    sign_record(
                        keys["local-controller"],
                        "local-controller",
                        "job-recovery",
                        {
                            "institution_id": "institution",
                            "job_id": first.job_id,
                            "authorization_id": one.authorization_id,
                            "reason": "interrupt before the handler starts",
                        },
                    )
                )
                dispatcher.dispatch(
                    first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", two)
                )
                newer.append(
                    pool.submit(
                        dispatcher.execute_tool,
                        first.job_id,
                        tool="fixed",
                        actor=first.worker,
                        invocation_id="same-name",
                        handler=new_handler,
                    )
                )
                assert started.wait(timeout=5)

        monkeypatch.setattr(store.journal, "transaction", recover_after_claim)
        try:
            with pytest.raises(Conflict, match="attempt changed before"):
                dispatcher.execute_tool(
                    first.job_id,
                    tool="fixed",
                    actor=first.worker,
                    invocation_id="same-name",
                    handler=lambda: old_calls.append(True) or {"attempt": 1},
                )
        finally:
            release.set()
        assert newer[0].result(timeout=5) == {"attempt": 2}
    assert old_calls == [] and new_calls == [True]
    runs = store.journal.latest(dispatcher.key)["runs"][first.job_id]
    assert runs[0]["tools"]["same-name"]["state"] == "uncertain"
    assert runs[1]["tools"]["same-name"]["state"] == "completed"


@pytest.mark.parametrize("prior_output", [False, True])
def test_oversized_retained_graph_fails_without_stranding_reservation(tmp_path, prior_output):
    from alpha_factory_v1.core.runtime.store import Journal
    from alpha_factory_v1.core.runtime.successor.jobs import GraphState
    from alpha_factory_v1.core.runtime.successor.protocol import canonical

    store, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    one, two = authorization(first), authorization(first, 2)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", one))
    output = {"text": '"' * (250_000 if prior_output else 500_000)}
    assert len(canonical(output)) < 2_000_000
    if prior_output:
        dispatcher.execute_tool(
            first.job_id,
            tool="fixed",
            actor=first.worker,
            invocation_id="earlier-output",
            handler=lambda: output,
            retain_result=True,
        )
    with pytest.raises(ValueError, match="bounded job tool failed") as rejected:
        dispatcher.execute_tool(
            first.job_id,
            tool="fixed",
            actor=first.worker,
            invocation_id="oversized-output",
            handler=lambda: output,
            retain_result=True,
        )
    assert "byte limit" in str(rejected.value.__cause__)
    graph_state = GraphState.model_validate(Journal.document(store.journal.latest(dispatcher.key)))
    invocation = graph_state.runs[first.job_id][-1].tools["oversized-output"]
    assert invocation.state == "failed"
    assert invocation.result_json is invocation.result_digest is None
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}
    dispatcher.recover_job(
        sign_record(
            keys["local-controller"],
            "local-controller",
            "job-recovery",
            {
                "institution_id": "institution",
                "job_id": first.job_id,
                "authorization_id": one.authorization_id,
                "reason": "close oversized output failure",
            },
        )
    )
    assert store.read("institution")["resources"]["reserved"] == {"calls": 0}
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", two))
    dispatcher.complete(accept(keys, first, two))
    assert store.read("institution")["resources"]["spent"] == {"calls": 2}
    assert store.journal.verify()["valid"]


@pytest.mark.parametrize("spare_bytes", [0, 2])
def test_exact_graph_boundary_preserves_and_consumes_recovery_headroom(tmp_path, spare_bytes):
    from alpha_factory_v1.core.runtime.store import Journal
    from alpha_factory_v1.core.runtime.successor.jobs import GraphState, ToolInvocation
    from alpha_factory_v1.core.runtime.successor.protocol import MAX_JSON_BYTES, canonical

    store, keys, dispatcher, frozen = setup(tmp_path)
    first = frozen.jobs[0]
    auth = authorization(first)
    dispatcher.dispatch(first.job_id, sign_record(keys["local-controller"], "local-controller", "execution", auth))
    proposed = Journal.document(store.journal.latest(dispatcher.key))
    invocation = ToolInvocation(
        tool="fixed",
        actor=first.worker,
        state="completed",
        result_digest="0" * 64,
        result_json=canonical({"text": ""}).decode("utf-8"),
    ).model_dump(mode="json")
    proposed["runs"][first.job_id][-1]["tools"]["boundary"] = invocation
    output = {"text": "x" * (MAX_JSON_BYTES - len(canonical(proposed)) - spare_bytes)}
    invocation["result_json"] = canonical(output).decode("utf-8")
    invocation["result_digest"] = digest("job-tool-output", output)
    assert len(canonical(proposed)) == MAX_JSON_BYTES - spare_bytes
    GraphState.model_validate(proposed)

    def execute():
        return dispatcher.execute_tool(
            first.job_id,
            tool="fixed",
            actor=first.worker,
            invocation_id="boundary",
            handler=lambda: output,
            retain_result=True,
        )

    if spare_bytes == 0:
        with pytest.raises(ValueError, match="bounded job tool failed"):
            execute()
    else:
        assert execute() == output
        before = store.journal.verify()
        with pytest.raises(ValueError, match="byte limit"):
            dispatcher.complete(accept(keys, first, auth))
        with pytest.raises(ValueError, match="byte limit"):
            dispatcher.revoke_dependency(
                sign_record(
                    keys["local-controller"],
                    "local-controller",
                    "job-revocation",
                    {"job_id": first.job_id, "reason": "must preserve recovery space"},
                )
            )
        assert store.journal.verify() == before
    recovered = dispatcher.recover_job(
        sign_record(
            keys["local-controller"],
            "local-controller",
            "job-recovery",
            {
                "institution_id": "institution",
                "job_id": first.job_id,
                "authorization_id": auth.authorization_id,
                "reason": "consume the reserved recovery headroom",
            },
        )
    )
    GraphState.model_validate(Journal.document(recovered))
    assert recovered["runs"][first.job_id][-1]["state"] == "uncertain"
    assert store.read("institution")["resources"]["reserved"] == {"calls": 0}
    if spare_bytes == 2:
        assert len(canonical(Journal.document(recovered))) == MAX_JSON_BYTES
