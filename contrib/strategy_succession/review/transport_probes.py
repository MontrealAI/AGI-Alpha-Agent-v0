import hashlib, json, multiprocessing, sys, tempfile
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "transport"))
from alpha_factory_v1.core.runtime.store import Conflict, Journal
from strategy_executor import ExecutorPolicy, Limits, SourceFile, StrategyExecutor, create_strategy_app
from fastapi.testclient import TestClient


class Worker:
    def __init__(self, hook=None, verified=True):
        self.calls = 0
        self.hook = hook
        self.verified = verified

    def execute(self, method, payload, limits, checkpoint):
        self.calls += 1
        checkpoint()
        if self.hook:
            self.hook(checkpoint)
        service = 0 if method == "construct" else 1
        improvement = 1 if method == "construct" else 0
        checkpoint(service_work=service, improvement_work=improvement)
        return {
            "result": {"echo": payload},
            "costs": {
                "service_work": service,
                "improvement_work": improvement,
                "native_calls": 0,
                "native_solve_seconds": 0,
                "unknown_costs": ["human effort"],
            },
            "source_hash": limits["source_hash"],
            "verified": self.verified,
        }


def expect(exception, call):
    try:
        call()
    except exception:
        return True
    raise AssertionError("expected refusal")


def setup(root, worker=None, clock=None, limits=None):
    root.mkdir()
    source = root / "fixed.py"
    source.write_text("fixed reviewed worker marker\n")
    worker = worker or Worker()
    policy = ExecutorPolicy(
        "review-fixed",
        (SourceFile("fixed.py", source, hashlib.sha256(source.read_bytes()).hexdigest()),),
        {"run-mission": Limits(4, 0, 0, 0), "construct": Limits(0, 4, 0, 0)},
        limits or Limits(24, 24, 0, 0),
        grant_seconds=60,
        request_seconds=30,
    )
    journal = Journal.initialize(root / "journal")
    return journal, worker, policy, StrategyExecutor(journal, worker, policy, **({"clock": clock} if clock else {}))


def approve(executor, ident="one", method="run-mission"):
    p = executor.prepare({"method": method, "input": {"public": "independent fixture"}, "request_id": ident})
    ref = {k: p[k] for k in ["plan_id", "plan_digest"]}
    executor.approve(ref)
    return ref


def child_run(home, policy, ref, entered, release, queue):
    def hold(checkpoint):
        entered.set()
        release.wait(5)
        checkpoint()

    try:
        queue.put({"state": StrategyExecutor(Journal(home), Worker(hold), policy).run(ref)["state"]})
    except Exception as e:
        queue.put({"error": type(e).__name__})


def main():
    checks = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        journal, worker, policy, executor = setup(root / "pause")
        ref = approve(executor)
        journal.control(True)
        expect(Conflict, lambda: executor.run(ref))
        assert worker.calls == 0
        checks["global_pause_before_worker"] = True
        journal.control(False)
        worker.hook = lambda checkpoint: journal.control(True)
        expect(Conflict, lambda: executor.run(ref))
        s = executor.status()
        assert s["plans"][ref["plan_id"]]["state"] == "unknown" and s["reserved"]["service_work"] == 4
        checks["global_pause_fences_commit_keeps_reserve"] = True
        journal, worker, policy, executor = setup(root / "restore")
        ref = approve(executor)
        journal.backup(root / "private-backup.zip")
        restored = Journal.restore(root / "private-backup.zip", root / "restored")
        expect(Conflict, lambda: StrategyExecutor(restored, worker, policy))
        assert worker.calls == 0
        checks["private_restore_has_no_old_authority"] = True
        journal, worker, policy, executor = setup(root / "rejected", Worker(verified=False))
        ref = approve(executor)
        r = executor.run(ref)
        assert (
            r["state"] == "rejected"
            and executor.status()["spent"]["service_work"] == 1
            and not any(executor.status()["reserved"].values())
        )
        assert executor.run(ref)["outcome_hash"] == r["outcome_hash"] and worker.calls == 1
        checks["unverified_rejected_costed_idempotent"] = True
        journal, worker, policy, executor = setup(root / "api")
        client = TestClient(create_strategy_app(journal, worker, policy))
        token = (journal.root / "api.token").read_text()
        headers = {"Authorization": "Bearer " + token}
        assert client.get("/api/strategy-executor/status").status_code == 401
        assert (
            client.post(
                "/api/strategy-executor/control",
                headers={**headers, "Origin": "https://bad.invalid"},
                json={"state": "stopped"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/strategy-executor/prepare",
                headers=headers,
                json={"method": "run-mission", "input": {}, "request_id": "x", "caps": {"service_work": 1000}},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/strategy-executor/prepare",
                headers=headers,
                json={"method": "shell", "input": {}, "request_id": "x"},
            ).status_code
            == 422
        )
        assert worker.calls == 0
        checks["auth_origin_fixed_fields_no_execution"] = True
        ref = approve(executor)
        expect(Conflict, lambda: executor.run({"plan_id": ref["plan_id"], "plan_digest": "0" * 64}))
        assert worker.calls == 0
        checks["forged_displayed_approval_refused"] = True
        outcome = executor.run(ref)
        exported = executor.export(ref["plan_id"])
        assert executor.run(ref)["outcome_hash"] == outcome["outcome_hash"] and worker.calls == 1
        blob = json.dumps(exported)
        assert token not in blob and str(root) not in blob
        checks["committed_duplicate_no_reexecution_export_no_token_or_host_path"] = True
        journal, worker, policy, executor = setup(
            root / "native", Worker(lambda checkpoint: checkpoint(native_calls=1))
        )
        ref = approve(executor)
        expect(Conflict, lambda: executor.run(ref))
        assert (
            executor.status()["plans"][ref["plan_id"]]["state"] == "unknown"
            and executor.status()["reserved"]["native_calls"] == 0
        )
        checks["disabled_native_counter_refused"] = True
        journal, worker, policy, executor = setup(root / "accounts", limits=Limits(24, 0, 0, 0))
        ref = approve(executor, method="construct")
        expect(Conflict, lambda: executor.run(ref))
        assert worker.calls == 0 and not any(executor.status()["reserved"].values())
        checks["improvement_cannot_borrow_service_budget"] = True
        now = [1000.0]
        journal, worker, policy, executor = setup(root / "expiry", clock=lambda: now[0])
        worker.hook = lambda checkpoint: now.__setitem__(0, 1031.0)
        ref = approve(executor)
        expect(Conflict, lambda: executor.run(ref))
        status = executor.status()
        expect(
            Conflict,
            lambda: executor.reconcile({"plan_id": ref["plan_id"], "record_digest": "0" * 64, "note": "stale"}),
        )
        r = executor.reconcile(
            {
                "plan_id": ref["plan_id"],
                "record_digest": status["digest"],
                "note": "Independent inspection; work remains unknown.",
            }
        )
        assert r["state"] == "reconciled" and executor.status()["reserved"]["service_work"] == 4
        expect(Conflict, lambda: executor.run(ref))
        assert worker.calls == 1
        checks["expiry_reconciliation_keeps_unknown_cost_no_replay"] = True
        journal, worker, policy, executor = setup(root / "processes")
        ref = approve(executor)
        ctx = multiprocessing.get_context("fork")
        entered = ctx.Event()
        release = ctx.Event()
        queue = ctx.Queue()
        child = ctx.Process(target=child_run, args=(journal.root, policy, ref, entered, release, queue))
        child.start()
        assert entered.wait(4)
        expect(Conflict, lambda: executor.run(ref))
        release.set()
        child.join(6)
        assert child.exitcode == 0 and queue.get(timeout=1) == {"state": "completed"} and worker.calls == 0
        checks["real_second_process_blocked_by_journal_reservation"] = True
        journal, worker, policy, executor = setup(root / "source")
        ref = approve(executor)
        policy.sources[0].path.write_text("changed")
        expect(ValueError, lambda: executor.run(ref))
        assert worker.calls == 0
        checks["changed_installed_source_refused"] = True
    files = {
        name: hashlib.sha256((Path(__file__).resolve().parents[1] / "transport" / name).read_bytes()).hexdigest()
        for name in ["strategy_executor.py", "test_strategy_executor.py"]
    }
    print(
        json.dumps(
            {
                "scope": "Independent tiny engineering probes only; no frozen-study input, remote action or production claim.",
                "checks": checks,
                "passed": sum(checks.values()),
                "source_files_sha256": files,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
