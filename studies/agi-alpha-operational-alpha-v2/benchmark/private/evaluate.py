# SPDX-License-Identifier: Apache-2.0
"""Independent finite contract checks; never import a reference implementation."""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import time


def equal(left, right):
    if left != right:
        raise AssertionError(f"{left!r} != {right!r}")


def reject(call, snapshot=None):
    before = deepcopy(snapshot()) if snapshot else None
    try:
        call()
    except ValueError:
        if snapshot:
            equal(snapshot(), before)
        return
    raise AssertionError("required ValueError was not raised")


def development(module, check, seed):
    def replay():
        ledger = module.Ledger({"a": 100, "b": 50})
        ledger.reserve("a", "j", 40)
        before = ledger.snapshot()
        ledger.reserve("a", "j", 40)
        equal(ledger.snapshot(), before)
        reject(lambda: ledger.reserve("a", "j", 41), ledger.snapshot)
        reject(lambda: ledger.reserve("b", "j", 40), ledger.snapshot)
    check("request-binding", replay)

    def ownership():
        ledger = module.Ledger({"a": 100, "b": 50})
        ledger.reserve("a", "j", 40)
        reject(lambda: ledger.settle("b", "j", 10), ledger.snapshot)
        reject(lambda: ledger.cancel("b", "j"), ledger.snapshot)
    check("owner-isolation", ownership)

    def terminal():
        ledger = module.Ledger({"a": 100})
        ledger.reserve("a", "j", 40)
        ledger.settle("a", "j", 10)
        before = ledger.snapshot()
        ledger.settle("a", "j", 10)
        equal(ledger.snapshot(), before)
        reject(lambda: ledger.settle("a", "j", 11), ledger.snapshot)
        reject(lambda: ledger.cancel("a", "j"), ledger.snapshot)
        ledger.reserve("a", "k", 40)
        ledger.cancel("a", "k")
        before = ledger.snapshot()
        ledger.cancel("a", "k")
        equal(ledger.snapshot(), before)
        reject(lambda: ledger.settle("a", "k", 0), ledger.snapshot)
    check("terminal-retry-conflict", terminal)

    def isolation():
        ledger = module.Ledger({"a": 100})
        record = ledger.reserve("a", "j", 40)
        record["cap"] = 999
        before = deepcopy(ledger.snapshot())
        snap = ledger.snapshot()
        snap["wallets"]["a"]["available"] = -10
        snap["requests"]["j"]["owner"] = "evil"
        equal(ledger.snapshot(), before)
    check("copy-isolation", isolation)

    def invalid():
        for value in [True, -1, 0, 1.2, "1", None]:
            ledger = module.Ledger({"a": 100})
            reject(lambda v=value: ledger.reserve("a", "j", v), ledger.snapshot)
        ledger = module.Ledger({"a": 100})
        ledger.reserve("a", "j", 40)
        for actual in [True, -1, 41, None]:
            reject(lambda a=actual: ledger.settle("a", "j", a), ledger.snapshot)
    check("invalid-input-atomicity", invalid)

    for offset in range(4):
        def sequence(offset=offset):
            rng = random.Random(seed + offset)
            ledger = module.Ledger({"a": 1000, "b": 800})
            expected = {"a": {"available": 1000, "reserved": 0, "spent": 0},
                        "b": {"available": 800, "reserved": 0, "spent": 0}}
            for i in range(24):
                owner = rng.choice(["a", "b"])
                cap = rng.randrange(1, 20)
                request = f"job-{offset}-{i}"
                ledger.reserve(owner, request, cap)
                ledger.reserve(owner, request, cap)
                if rng.random() < .3:
                    ledger.cancel(owner, request)
                    ledger.cancel(owner, request)
                else:
                    actual = rng.randrange(cap + 1)
                    ledger.settle(owner, request, actual)
                    ledger.settle(owner, request, actual)
                    expected[owner]["available"] -= actual
                    expected[owner]["spent"] += actual
                equal(ledger.snapshot()["wallets"], expected)
        check(f"fresh-sequence-{offset}", sequence)


def c1(module, check, seed):
    def event(i, job="j", owner="a", kind="reserve", amount=40):
        return dict(id=i, job=job, owner=owner, kind=kind, amount=amount)

    def binding():
        journal = module.Journal({"a": 100})
        row = event("e")
        equal(journal.append(row), dict(id="e", sequence=1, job="j", kind="reserve"))
        before = journal.snapshot()
        equal(journal.append(deepcopy(row)), dict(id="e", sequence=1, job="j", kind="reserve"))
        equal(journal.snapshot(), before)
        reject(lambda: journal.append(event("e", amount=41)), journal.snapshot)
        equal(len(journal.export_log()), 1)
    check("event-id-binding", binding)

    def ownership():
        journal = module.Journal({"a": 100, "b": 100})
        journal.append(event("e"))
        reject(lambda: journal.append(event("bad", owner="b", kind="settle", amount=5)), journal.snapshot)
        reject(lambda: journal.append(event("bad", owner="b", kind="cancel", amount=0)), journal.snapshot)
        equal(len(journal.export_log()), 1)
    check("cross-tenant-terminal-denial", ownership)

    def log_isolation():
        journal = module.Journal({"a": 100})
        row = event("e")
        receipt = journal.append(row)
        saved = deepcopy(journal.export_log())
        row["amount"] = 999
        receipt["sequence"] = 999
        journal.export_log()[0]["owner"] = "evil"
        equal(journal.export_log(), saved)
        equal(journal.append(saved[0])["sequence"], 1)
    check("input-log-receipt-isolation", log_isolation)

    def atomic():
        journal = module.Journal({"a": 100})
        journal.append(event("e"))
        before_log = journal.export_log()
        reject(lambda: journal.append(event("terminal", kind="settle", amount=41)), journal.snapshot)
        equal(journal.export_log(), before_log)
        journal.append(event("terminal", kind="settle", amount=25))
        equal(journal.snapshot()["wallets"]["a"], dict(available=75, reserved=0, spent=25))
        reject(lambda: journal.append(event("another", kind="settle", amount=25)), journal.snapshot)
        journal.append(event("terminal", kind="settle", amount=25))
        equal(len(journal.export_log()), 2)
    check("failed-id-recovery-terminal-rules", atomic)

    def invalid():
        journal = module.Journal({"a": 100})
        bads = [None, {}, event("e", amount=True), event("e", amount=-2),
                event("e", kind=[]), event("", amount=1), dict(event("e"), extra=1)]
        for row in bads:
            reject(lambda r=row: journal.append(r), journal.snapshot)
        equal(journal.export_log(), [])
    check("input-domain", invalid)

    for offset in range(4):
        def sequence(offset=offset):
            rng = random.Random(seed + offset)
            initial = {"a": 2000, "b": 2000}
            journal = module.Journal(initial)
            spent = dict(a=0, b=0)
            accepted_events = []
            replay_events = []
            for i in range(20):
                owner = rng.choice(["a", "b"])
                cap = rng.randrange(1, 50)
                reserve = event(f"r{i}", f"j{i}", owner, "reserve", cap)
                actual = rng.randrange(cap + 1)
                kind = "settle" if rng.random() < .7 else "cancel"
                if kind == "cancel":
                    actual = 0
                terminal = event(f"t{i}", f"j{i}", owner, kind, actual)
                for row in [reserve, terminal]:
                    journal.append(row)
                    journal.append(row)
                    accepted_events.append(row)
                    replay_events.extend([row, deepcopy(row)])
                spent[owner] += actual
            equal(journal.export_log(), accepted_events)
            equal(module.Journal.replay(initial, replay_events).snapshot(), journal.snapshot())
            equal(journal.snapshot()["wallets"],
                  {o: dict(available=initial[o] - spent[o], reserved=0, spent=spent[o]) for o in initial})
        check(f"fresh-replay-sequence-{offset}", sequence)


def c2(module, check, seed):
    def ready():
        queue = module.Scheduler(5)
        queue.add("a", "parent", 3, [])
        queue.add("a", "child", 2, ["parent"])
        reject(lambda: queue.claim("a", "child", "early"), queue.snapshot)
        queue.claim("a", "parent", "p1")
        reject(lambda: queue.claim("a", "child", "early"), queue.snapshot)
        queue.finish("a", "parent", "p1", False)
        reject(lambda: queue.claim("a", "child", "early"), queue.snapshot)
        queue.claim("a", "parent", "p2")
        queue.finish("a", "parent", "p2", True)
        queue.claim("a", "child", "c1")
        equal(queue.snapshot()["used"], 2)
    check("dependency-success-required", ready)

    def scope():
        queue = module.Scheduler(5)
        queue.add("a", "parent", 3, [])
        reject(lambda: queue.add("b", "child", 2, ["parent"]), queue.snapshot)
        reject(lambda: queue.claim("b", "parent", "x"), queue.snapshot)
        reject(lambda: queue.cancel("b", "parent"), queue.snapshot)
    check("tenant-scoped-dependencies", scope)

    def lease():
        queue = module.Scheduler(5)
        queue.add("a", "a", 3, [])
        queue.add("a", "b", 2, [])
        queue.claim("a", "a", "l1")
        queue.finish("a", "a", "l1", False)
        before = queue.snapshot()
        queue.finish("a", "a", "l1", False)
        equal(queue.snapshot(), before)
        reject(lambda: queue.claim("a", "b", "l1"), queue.snapshot)
        reject(lambda: queue.claim("a", "a", "l1"), queue.snapshot)
        queue.claim("a", "a", "l2")
        before = queue.snapshot()
        queue.finish("a", "a", "l1", False)
        equal(queue.snapshot(), before)
        reject(lambda: queue.finish("a", "a", "l1", True), queue.snapshot)
    check("old-lease-retries-and-global-uniqueness", lease)

    def capacity():
        queue = module.Scheduler(5)
        queue.add("a", "a", 3, [])
        queue.add("a", "b", 3, [])
        queue.claim("a", "a", "a1")
        queue.claim("a", "a", "a1")
        equal(queue.snapshot()["used"], 3)
        reject(lambda: queue.claim("a", "b", "b1"), queue.snapshot)
        queue.cancel("a", "a")
        queue.cancel("a", "a")
        equal(queue.snapshot()["used"], 0)
        reject(lambda: queue.finish("a", "a", "a1", True), queue.snapshot)
        queue.claim("a", "b", "b1")
        queue.finish("a", "b", "b1", True)
        reject(lambda: queue.cancel("a", "b"), queue.snapshot)
    check("capacity-release-and-cancel", capacity)

    def input_copy():
        queue = module.Scheduler(5)
        deps = []
        queue.add("a", "a", 3, deps)
        deps.append("evil")
        before = queue.snapshot()
        snap = queue.snapshot()
        snap["jobs"]["a"]["deps"].append("evil")
        equal(queue.snapshot(), before)
        for cost in [True, 0, -1, 6, 2.5]:
            reject(lambda c=cost: queue.add("a", "b", c, []), queue.snapshot)
        reject(lambda: queue.add("a", "b", 1, ["a", "a"]), queue.snapshot)
        reject(lambda: queue.add("a", "b", 1, ["missing"]), queue.snapshot)
    check("validation-and-copy-isolation", input_copy)

    for offset in range(4):
        def sequence(offset=offset):
            rng = random.Random(seed + offset)
            queue = module.Scheduler(9)
            for i in range(18):
                deps = [] if i == 0 else [f"j{i-1}"]
                queue.add("a", f"j{i}", rng.randrange(1, 9), deps)
            for i in range(18):
                job = f"j{i}"
                lease = f"first-{i}"
                queue.claim("a", job, lease)
                used = queue.snapshot()["jobs"][job]["cost"]
                equal(queue.snapshot()["used"], used)
                if rng.random() < .6:
                    queue.finish("a", job, lease, False)
                    queue.finish("a", job, lease, False)
                    lease = f"second-{i}"
                    queue.claim("a", job, lease)
                queue.finish("a", job, lease, True)
                queue.finish("a", job, lease, True)
                equal(queue.snapshot()["used"], 0)
            equal({r["state"] for r in queue.snapshot()["jobs"].values()}, {"succeeded"})
        check(f"fresh-dag-sequence-{offset}", sequence)


def c3(module, check, seed):
    def begin(store, owner="a", upload="u", data=b"abcdef"):
        store.begin(owner, upload, len(data), hashlib.sha256(data).hexdigest())

    def scoped():
        store = module.ArtifactStore()
        begin(store)
        begin(store, "b", data=b"different")
        store.put("a", "u", 0, b"abcdef")
        store.put("b", "u", 0, b"different")
        equal(store.commit("a", "u"), b"abcdef")
        equal(store.commit("b", "u"), b"different")
        reject(lambda: store.commit("c", "u"), store.snapshot)
    check("tenant-upload-namespace", scoped)

    def overlap():
        store = module.ArtifactStore()
        begin(store)
        store.put("a", "u", 3, b"def")
        reject(lambda: store.put("a", "u", 0, b"abcXef"), store.snapshot)
        equal(store.snapshot()[0]["cells"], [None, None, None, 100, 101, 102])
        store.put("a", "u", 0, b"abcd")
        equal(store.commit("a", "u"), b"abcdef")
        store.put("a", "u", 1, b"bc")
        reject(lambda: store.put("a", "u", 1, b"BX"), store.snapshot)
    check("overlap-atomicity-and-committed-retry", overlap)

    def digest():
        store = module.ArtifactStore()
        begin(store)
        reject(lambda: store.commit("a", "u"), store.snapshot)
        store.put("a", "u", 0, b"abcdeg")
        reject(lambda: store.commit("a", "u"), store.snapshot)
        equal(store.snapshot()[0]["state"], "active")
        store.abort("a", "u")
        store.abort("a", "u")
        reject(lambda: store.put("a", "u", 0, b"abcdef"), store.snapshot)
        reject(lambda: store.commit("a", "u"), store.snapshot)
    check("completeness-digest-abort", digest)

    def recovery():
        store = module.ArtifactStore()
        begin(store)
        store.put("a", "u", 0, b"abc")
        source = store.snapshot()
        recovered = module.ArtifactStore.restore(source)
        source[0]["cells"][0] = 90
        store.snapshot()[0]["cells"][0] = 90
        equal(recovered.snapshot()[0]["cells"][0], 97)
        recovered.put("a", "u", 3, b"def")
        equal(recovered.commit("a", "u"), b"abcdef")
        equal(store.snapshot()[0]["cells"], [97, 98, 99, None, None, None])
        reject(lambda: recovered.abort("a", "u"), recovered.snapshot)
    check("checkpoint-input-output-isolation", recovery)

    def validation():
        store = module.ArtifactStore()
        begin(store)
        snapshot = store.snapshot()
        malformed = []
        for key, value in [("state", []), ("size", True), ("cells", [None]),
                           ("cells", [True] * 6), ("state", "committed")]:
            copy = deepcopy(snapshot)
            copy[0][key] = value
            malformed.append(copy)
        malformed.append(snapshot + deepcopy(snapshot))
        aborted = deepcopy(snapshot)
        aborted[0].update(state="aborted", cells=[1] * 6)
        malformed.append(aborted)
        for candidate in malformed:
            reject(lambda c=candidate: module.ArtifactStore.restore(c))
        reject(lambda: store.put("a", "u", True, b"a"), store.snapshot)
        reject(lambda: store.put("a", "u", 0, bytearray(b"a")), store.snapshot)
        empty = module.ArtifactStore()
        begin(empty, data=b"")
        equal(empty.commit("a", "u"), b"")
    check("restore-validation-and-empty-boundary", validation)

    for offset in range(4):
        def sequence(offset=offset):
            rng = random.Random(seed + offset)
            store = module.ArtifactStore()
            for i in range(10):
                data = bytes(rng.randrange(256) for _ in range(rng.randrange(1, 100)))
                upload = f"u{i}"
                begin(store, upload=upload, data=data)
                chunks = [(k, data[k:k+7]) for k in range(0, len(data), 7)]
                rng.shuffle(chunks)
                for k, chunk in chunks:
                    store.put("a", upload, k, chunk)
                    store.put("a", upload, k, chunk)
                    if rng.random() < .25:
                        store = module.ArtifactStore.restore(store.snapshot())
                equal(store.commit("a", upload), data)
                equal(store.commit("a", upload), data)
            equal(len(store.snapshot()), 10)
        check(f"fresh-chunk-recovery-{offset}", sequence)


def c4(module, check, seed):
    def op(source, target, amount):
        return {"from": source, "to": target, "amount": amount}

    def binding():
        book = module.AccountBook(dict(a=100, b=0, c=0))
        operations = [op("a", "b", 20)]
        receipt = book.transact("t", operations, dict(a=0, b=0))
        book.transact("other", [op("b", "c", 10)], dict(b=1, c=0))
        before = book.snapshot()
        equal(book.transact("t", operations, dict(a=0, b=0)), receipt)
        equal(book.snapshot(), before)
        reject(lambda: book.transact("t", [op("a", "b", 21)], dict(a=0, b=0)), book.snapshot)
    check("durable-request-payload-binding", binding)

    def atomic():
        book = module.AccountBook(dict(a=100, b=0, c=0))
        operations = [op("a", "b", 20), op("c", "a", 1)]
        reject(lambda: book.transact("t", operations, dict(a=0, b=0, c=0)), book.snapshot)
        equal(book.snapshot(), dict(balances=dict(a=100, b=0, c=0), revisions=dict(a=0, b=0, c=0)))
        receipt = book.transact("t", [op("a", "b", 20)], dict(a=0, b=0))
        equal(receipt["balances"], dict(a=80, b=20))
    check("late-failure-atomicity-and-id-reuse", atomic)

    def revisions():
        book = module.AccountBook(dict(a=100, b=0, c=0))
        reject(lambda: book.transact("t", [op("a", "b", 20)], dict(a=0)), book.snapshot)
        reject(lambda: book.transact("t", [op("a", "b", 20)], dict(a=0, b=0, c=0)), book.snapshot)
        receipt = book.transact("t", [op("a", "b", 20), op("b", "c", 10), op("a", "a", 1)],
                                dict(a=0, b=0, c=0))
        equal(receipt["revisions"], dict(a=1, b=1, c=1))
        reject(lambda: book.transact("stale", [op("a", "b", 1)], dict(a=0, b=0)), book.snapshot)
    check("exact-guards-and-once-per-batch-revisions", revisions)

    def isolation():
        book = module.AccountBook(dict(a=100, b=0))
        operations, expected = [op("a", "b", 20)], dict(a=0, b=0)
        receipt = book.transact("t", operations, expected)
        saved = deepcopy(receipt)
        receipt["balances"]["a"] = 999
        receipt["revisions"]["a"] = 999
        operations[0]["amount"] = 999
        expected["a"] = 999
        equal(book.transact("t", [op("a", "b", 20)], dict(a=0, b=0)), saved)
        retry = book.transact("t", [op("a", "b", 20)], dict(a=0, b=0))
        retry["balances"]["a"] = -1
        equal(book.transact("t", [op("a", "b", 20)], dict(a=0, b=0)), saved)
        snap = book.snapshot()
        snap["balances"]["a"] = -1
        equal(book.snapshot()["balances"]["a"], 80)
    check("stored-and-replayed-receipt-isolation", isolation)

    def inputs():
        book = module.AccountBook(dict(a=100, b=0))
        for amount in [True, 0, -1, 2.5, "2"]:
            reject(lambda a=amount: book.transact("t", [op("a", "b", a)], dict(a=0, b=0)), book.snapshot)
        reject(lambda: book.transact("t", [op("b", "b", 1)], dict(b=0)), book.snapshot)
        reject(lambda: book.transact("t", [op("b", "a", 1), op("a", "b", 2)], dict(a=0, b=0)),
               book.snapshot)
        reject(lambda: book.transact("t", [op("a", "b", 1)], dict(a=True, b=0)), book.snapshot)
    check("input-domain-and-sequential-solvency", inputs)

    for offset in range(4):
        def sequence(offset=offset):
            rng = random.Random(seed + offset)
            balances = {a: 100 for a in "abcd"}
            revisions = {a: 0 for a in balances}
            book = module.AccountBook(balances)
            for i in range(25):
                trial = dict(balances)
                operations, touched = [], set()
                for _ in range(rng.randrange(1, 5)):
                    source, target = rng.sample(list(balances), 2)
                    if trial[source] == 0:
                        continue
                    amount = rng.randrange(1, min(20, trial[source]) + 1)
                    trial[source] -= amount
                    trial[target] += amount
                    operations.append(op(source, target, amount))
                    touched.update((source, target))
                if not operations:
                    continue
                guards = {a: revisions[a] for a in touched}
                receipt = book.transact(f"t{i}", operations, guards)
                for a in touched:
                    revisions[a] += 1
                balances = trial
                equal(book.snapshot(), dict(balances=balances, revisions=revisions))
                equal(book.transact(f"t{i}", operations, guards), receipt)
                equal(sum(book.snapshot()["balances"].values()), 400)
        check(f"fresh-atomic-sequence-{offset}", sequence)


CASES = {"development": development, "c1": c1, "c2": c2, "c3": c3, "c4": c4}
SEEDS = {"development": 6102700, "c1": 6102711, "c2": 6102721, "c3": 6102731, "c4": 6102741}


def evaluate(case, submission):
    submission = Path(submission).resolve()
    spec = importlib.util.spec_from_file_location("submission", submission / "engine.py")
    module = importlib.util.module_from_spec(spec)
    results = []
    started = time.perf_counter()

    def check(name, fn):
        try:
            fn()
            results.append(dict(category=name, passed=True))
        except Exception as error:
            results.append(dict(category=name, passed=False, error=type(error).__name__, detail=str(error)))

    try:
        spec.loader.exec_module(module)
        CASES[case](module, check, SEEDS[case])
    except Exception as error:
        results.append(dict(category="import-or-suite", passed=False, error=type(error).__name__, detail=str(error)))
    original_public = Path(__file__).resolve().parents[1] / "cases" / case / "test_public.py"
    # Run canonical smoke source, not a participant-modified public test.
    public = subprocess.run([sys.executable, "-c", original_public.read_text()], cwd=submission,
                            capture_output=True, text=True, timeout=20)
    results.append(dict(category="canonical-public-smoke", passed=public.returncode == 0,
                        output=public.stdout + public.stderr))
    output = dict(case=case, submission=str(submission), seed=SEEDS[case],
                  source_sha256=hashlib.sha256((submission / "engine.py").read_bytes()).hexdigest(),
                  passed=sum(r["passed"] for r in results), total=len(results),
                  accepted=all(r["passed"] for r in results), checks=results,
                  elapsed_seconds=time.perf_counter() - started)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=CASES)
    parser.add_argument("submission")
    parser.add_argument("--out")
    args = parser.parse_args()
    result = evaluate(args.case, args.submission)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(encoded)
    print(encoded)
    raise SystemExit(0 if result["accepted"] else 1)
