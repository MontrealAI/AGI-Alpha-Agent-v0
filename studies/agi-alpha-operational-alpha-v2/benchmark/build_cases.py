# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMON = '''
## Deliverable and acceptance

Repair `engine.py` while preserving the documented public API, add meaningful regression tests, and write
`REPAIR.md` explaining the corrected behavior and remaining limits. Python 3.11+ and the standard library suffice.
No network or external services are required. You may restructure internals. Do not weaken requirements or modify
the supplied public smoke tests. Acceptance requires the public smoke test and every protected contract category
to pass. Protected tests exercise only this contract with fresh values and command sequences, including boundary
values and interactions. They are not production certification or proof of arbitrary inputs outside this scope.

All identifiers are nonempty strings and numbers called integers must have `type(x) is int` (booleans are not
integers for this API). Invalid inputs, unknown identifiers, authorization failures and conflicting operations
raise `ValueError`. Any rejected operation must leave all externally observable state unchanged. Returned
snapshots, logs and receipts are independent copies; mutating them must not mutate internal state.

Run `python test_public.py` for the public smoke test. Production concurrency, OS process crashes, filesystem
durability, arbitrary Python object adversaries and cryptographic authorization are outside this finite contract.
The caller supplies the authenticated owner; this exercise tests enforcement of that asserted identity, not
whether it was authenticated. No currency or real customer funds are involved.
'''

SPECS = {
"development": '''# Development mission: bounded reservation ledger

A workflow service reserves a tenant's credits before execution and settles only the actual accepted consumption.
Fix its in-memory transaction behavior so caller retries cannot lose credits or spend another tenant's balance.

`Ledger(initial: dict[str, int])` accepts nonnegative integer balances. Public methods:

- `reserve(owner, request, cap)`: positive cap, known owner, globally unique request. It moves cap from available
  to reserved. An exact repeated request is idempotent and returns the current request record; a changed owner
  or cap conflicts even if the original request has already settled/canceled. Insufficient funds reject atomically.
- `settle(owner, request, actual)`: active matching-owner request, integer 0 <= actual <= cap. It moves actual
  to spent and refunds cap-actual; repeated identical settlement is idempotent, changed actual conflicts.
- `cancel(owner, request)`: releases the whole active cap; repeated cancel is idempotent; settling a canceled
  request or canceling a settled request rejects.
- `snapshot()`: returns `{"wallets": {owner: {"available", "reserved", "spent"}}, "requests": {...}}`.
  Request records have `owner`, `cap`, `state` (`reserved`, `settled`, `canceled`) and `actual` (None until settled).
  Every owner's available + reserved + spent equals its initial balance, and all amounts remain nonnegative.
''',
"c1": '''# Confirmation mission C1: replayable reservation journal

A batch runner stores accepted reservation events so a restarted worker can reconstruct the same credit state.
Repair the event journal without changing its complete event stream or ownership contract.

`Journal(initial: dict[str, int])` accepts nonnegative integer balances. `append(event)` accepts dictionaries with
exactly `id`, `job`, `owner`, `kind`, `amount`. IDs/job/owner are nonempty strings. Kinds:

- `reserve`: amount is positive, job is new, known owner can afford it; creates an active reservation.
- `settle`: existing active job owned by owner, integer 0 <= amount <= reserved cap; spends amount and releases
  remaining reserve.
- `cancel`: existing active owned job, amount exactly 0; releases reserve. A second terminal event with a NEW
  event ID rejects, even if it repeats a terminal transition. Only exact event-ID retries are idempotent.

An exact event-ID retry returns its original receipt and changes nothing. Reusing its ID with different content
rejects. Receipt is `{"id": event_id, "sequence": one_based_accepted_event_count, "job": job, "kind": kind}`.
Only first successful events enter the log. Failed events cannot poison their IDs or become part of replay.
`snapshot()` returns wallets `{available,reserved,spent}` and jobs `{owner,cap,state}`. States are active/settled/canceled.
`export_log()` returns accepted events in order. `Journal.replay(initial, events)` applies them in the supplied
order, accepting exact duplicates idempotently, and returns an equivalent journal; malformed logs reject.
All state, receipts and log exports must remain isolated from caller mutation.
''',
"c2": '''# Confirmation mission C2: dependency scheduler with scoped leases

A constrained worker pool must execute tenant DAGs without oversubscribing capacity or unlocking dependent work
after failure. Repair its lease lifecycle; callers may retry any response after a timeout.

`Scheduler(capacity)` takes a positive integer. `add(owner, job, cost, dependencies)` adds a pending job with
positive integer cost <= capacity and a LIST of unique existing job IDs. Dependencies must belong to the same
owner; self-dependencies reject. Since dependencies already exist, additions cannot introduce cycles. Same job
and identical owner/cost/ordered dependency list is idempotent; any conflicting reuse rejects.

`claim(owner, job, lease)` requires a pending owned job, all dependencies succeeded and enough free capacity.
The nonempty lease ID is unique across all jobs and across all attempts, including finished/failed/canceled ones.
Repeating the exact active (owner,job,lease) claim is idempotent. A new lease cannot replace an active lease.
`finish(owner, job, lease, success)` takes a bool and requires the matching active lease. It frees capacity.
Success makes the job succeeded; failure makes it pending for a later NEW lease. A repeated finish for the SAME
lease and SAME success flag is idempotent even after another attempt has begun; a changed flag conflicts.
`cancel(owner, job)` frees active capacity, makes pending/running jobs canceled, is idempotent for canceled jobs,
and rejects for succeeded jobs. Canceling invalidates any active lease; a later finish for it rejects.

`snapshot()` returns `{"capacity": ..., "used": ..., "jobs": {...}}`; each job has owner,cost,deps,state,lease.
States are pending/running/succeeded/canceled; lease is None except while running. Snapshots are deep copies.
Free capacity equals capacity minus the costs of running jobs, never goes negative, and a terminal or rejected
operation cannot release the same reservation twice. Case-sensitive identifiers have no special namespace.
''',
"c3": '''# Confirmation mission C3: tenant-scoped resumable artifact assembly

A workflow runner uploads small result artifacts in chunks, retries writes and restores in-memory checkpoints.
Repair the assembler so artifacts remain isolated, complete and digest-verified.

`ArtifactStore()` supports `begin(owner, upload, size, digest)`, where size is an integer 0..65536 and digest is
64 lowercase hex characters (SHA-256). Upload IDs are scoped by owner, so two owners may use the same ID.
An exact begin retry is idempotent in any state; different size/digest conflicts. `put(owner, upload, offset, data)`
takes bytes, integer offset >= 0 and offset+len(data) <= size. Arbitrary overlap is allowed iff every overlapping
byte agrees. Conflicting overlap rejects the entire write, including previously empty positions. Owner/id must
identify a begun upload. Writes to aborted uploads reject; after commit only writes consistent with stored bytes
are allowed, and do not change its state.

`commit(owner, upload)` requires every position present and matching SHA-256, returns the exact bytes, and is
idempotent once committed. Missing data or wrong digest rejects without changing state. `abort(owner, upload)`
clears data and marks an active upload aborted, is idempotent for aborted uploads, and rejects committed uploads.
`snapshot()` returns a JSON-compatible LIST of records, sorted by (owner,upload), with owner,upload,size,digest,
state (`active`,`committed`,`aborted`), and `cells` (a list of byte integers or None, one entry per position).
`ArtifactStore.restore(snapshot)` restores any valid emitted checkpoint with independent state. It must reject
malformed/duplicate records, invalid cell lengths/values, committed records with holes/wrong digest, and aborted
records containing data. Restored operations obey the same contract. Caller mutations of input/returned snapshots
must not affect a store. An empty artifact is valid only with SHA-256 of empty bytes.
''',
"c4": '''# Confirmation mission C4: atomic optimistic account batches

A workflow service moves internal credits among project accounts using revision guards and idempotent batch IDs.
Repair atomic commit and retry behavior. These are synthetic allocation credits, not financial settlement.

`AccountBook(initial: dict[str,int])` takes nonnegative balances and initializes each account revision to zero.
`transact(request, operations, expected)` takes a nonempty request ID, a nonempty LIST of dictionaries each with
exactly `from`, `to`, `amount`, and expected revision map. Accounts must exist, amount must be a positive integer,
and self-transfers are permitted. The expected map must contain EXACTLY every account touched by any operation;
its values must be nonnegative integers matching current revisions. Evaluate operations in order: each source
must have enough balance at that moment, including for self-transfer. No temporary overdraft is allowed, even if
a later operation would replenish it.

On success, balances commit atomically; each touched account revision increments ONCE for the whole batch.
Receipt is `{"request": request, "balances": final balances of touched accounts,
"revisions": final revisions of touched accounts}`. An exact request retry returns the ORIGINAL receipt without
rechecking now-stale revisions or executing again; even after other batches it remains idempotent. Exactness uses
mapping equality and ordered operations. Different content under a used request ID rejects. Failed requests
consume neither IDs nor balances/revisions. Every failure is atomic. `snapshot()` returns `{"balances": {...},
"revisions": {...}}`. Caller mutations of operations, expected, snapshots or returned receipts cannot change
stored state or later idempotent receipts. Total credits are conserved. Unknown or malformed inputs reject.
'''
}


def save_case(name: str, code: str, public: str, changes: list[tuple[str, str]]) -> None:
    ref = ROOT / "private" / "references" / name
    ref.mkdir(parents=True, exist_ok=True)
    ref.joinpath("engine.py").write_text(code)
    starter = code
    for before, after in changes:
        if before not in starter:
            raise RuntimeError(f"missing mutation in {name}: {before}")
        starter = starter.replace(before, after, 1)
    case = ROOT / "cases" / name
    case.mkdir(parents=True, exist_ok=True)
    case.joinpath("engine.py").write_text(starter)
    case.joinpath("CONTRACT.md").write_text(SPECS[name] + COMMON)
    case.joinpath("test_public.py").write_text(public)
    ref.joinpath("test_public.py").write_text(public)
    ROOT.joinpath("private", name + "_mutations.json").write_text(json.dumps(changes, indent=2))


PREAMBLE = '''# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy


def identifier(value):
    if not isinstance(value, str) or not value:
        raise ValueError("invalid identifier")
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid integer")
    return value

'''

development = PREAMBLE + '''
class Ledger:
    def __init__(self, initial):
        if not isinstance(initial, dict):
            raise ValueError("invalid initial balances")
        self.wallets = {identifier(k): {"available": integer(v), "reserved": 0, "spent": 0}
                        for k, v in initial.items()}
        self.requests = {}

    def _owned(self, owner, request):
        identifier(owner)
        identifier(request)
        if request not in self.requests or self.requests[request]["owner"] != owner:
            raise ValueError("unknown or unauthorized request")
        return self.requests[request]

    def reserve(self, owner, request, cap):
        identifier(owner)
        identifier(request)
        integer(cap, 1)
        if owner not in self.wallets:
            raise ValueError("unknown owner")
        if request in self.requests:
            old = self._owned(owner, request)
            if old["cap"] != cap:
                raise ValueError("request conflict")
            return deepcopy(old)
        wallet = self.wallets[owner]
        if wallet["available"] < cap:
            raise ValueError("insufficient balance")
        wallet["available"] -= cap
        wallet["reserved"] += cap
        record = {"owner": owner, "cap": cap, "state": "reserved", "actual": None}
        self.requests[request] = record
        return deepcopy(record)

    def settle(self, owner, request, actual):
        integer(actual)
        record = self._owned(owner, request)
        if record["state"] == "settled" and record["actual"] == actual:
            return deepcopy(record)
        if record["state"] != "reserved" or actual > record["cap"]:
            raise ValueError("invalid settlement")
        wallet = self.wallets[owner]
        wallet["reserved"] -= record["cap"]
        wallet["available"] += record["cap"] - actual
        wallet["spent"] += actual
        record.update(state="settled", actual=actual)
        return deepcopy(record)

    def cancel(self, owner, request):
        record = self._owned(owner, request)
        if record["state"] == "canceled":
            return deepcopy(record)
        if record["state"] != "reserved":
            raise ValueError("invalid cancellation")
        wallet = self.wallets[owner]
        wallet["reserved"] -= record["cap"]
        wallet["available"] += record["cap"]
        record["state"] = "canceled"
        return deepcopy(record)

    def snapshot(self):
        return deepcopy({"wallets": self.wallets, "requests": self.requests})
'''

save_case("development", development, '''import unittest
from engine import Ledger

class Smoke(unittest.TestCase):
    def test_delivery(self):
        ledger = Ledger({"alpha": 100})
        ledger.reserve("alpha", "job-1", 40)
        ledger.settle("alpha", "job-1", 25)
        self.assertEqual(ledger.snapshot()["wallets"]["alpha"],
                         {"available": 75, "reserved": 0, "spent": 25})

if __name__ == "__main__":
    unittest.main()
''', [
(' or self.requests[request]["owner"] != owner', ''),
('if old["cap"] != cap:', 'if old["owner"] != owner:'),
('if record["state"] == "settled" and record["actual"] == actual:',
 'if record["state"] == "settled":'),
('return deepcopy({"wallets": self.wallets, "requests": self.requests})',
 'return {"wallets": self.wallets, "requests": self.requests}'),
])

c1 = PREAMBLE + '''
class Journal:
    def __init__(self, initial):
        if not isinstance(initial, dict):
            raise ValueError("invalid initial balances")
        self.wallets = {identifier(k): {"available": integer(v), "reserved": 0, "spent": 0}
                        for k, v in initial.items()}
        self.jobs = {}
        self.events = []
        self.receipts = {}

    def append(self, event):
        if not isinstance(event, dict) or set(event) != {"id", "job", "owner", "kind", "amount"}:
            raise ValueError("invalid event")
        identifier(event["id"])
        identifier(event["job"])
        identifier(event["owner"])
        identifier(event["kind"])
        integer(event["amount"])
        if event["id"] in self.receipts:
            old, receipt = self.receipts[event["id"]]
            if old != event:
                raise ValueError("conflicting event ID")
            return deepcopy(receipt)
        owner, job, kind, amount = (event[k] for k in ("owner", "job", "kind", "amount"))
        if owner not in self.wallets:
            raise ValueError("unknown owner")
        wallets = deepcopy(self.wallets)
        jobs = deepcopy(self.jobs)
        wallet = wallets[owner]
        if kind == "reserve":
            if amount <= 0 or job in jobs or wallet["available"] < amount:
                raise ValueError("invalid reservation")
            wallet["available"] -= amount
            wallet["reserved"] += amount
            jobs[job] = {"owner": owner, "cap": amount, "state": "active"}
        elif kind in {"settle", "cancel"}:
            if job not in jobs or jobs[job]["owner"] != owner or jobs[job]["state"] != "active":
                raise ValueError("invalid owned active job")
            record = jobs[job]
            if amount > record["cap"] or (kind == "cancel" and amount != 0):
                raise ValueError("invalid terminal amount")
            wallet["reserved"] -= record["cap"]
            wallet["available"] += record["cap"] - amount
            wallet["spent"] += amount
            record["state"] = "settled" if kind == "settle" else "canceled"
        else:
            raise ValueError("unknown kind")
        receipt = {"id": event["id"], "sequence": len(self.events) + 1, "job": job, "kind": kind}
        self.wallets, self.jobs = wallets, jobs
        self.events.append(deepcopy(event))
        self.receipts[event["id"]] = (deepcopy(event), deepcopy(receipt))
        return deepcopy(receipt)

    def snapshot(self):
        return deepcopy({"wallets": self.wallets, "jobs": self.jobs})

    def export_log(self):
        return deepcopy(self.events)

    @classmethod
    def replay(cls, initial, events):
        journal = cls(initial)
        if not isinstance(events, list):
            raise ValueError("invalid log")
        for event in events:
            journal.append(event)
        return journal
'''

save_case("c1", c1, '''import unittest
from engine import Journal

class Smoke(unittest.TestCase):
    def test_delivery(self):
        journal = Journal({"alpha": 100})
        journal.append(dict(id="e1", job="j1", owner="alpha", kind="reserve", amount=40))
        journal.append(dict(id="e2", job="j1", owner="alpha", kind="settle", amount=25))
        self.assertEqual(journal.snapshot()["wallets"]["alpha"]["available"], 75)
        self.assertEqual(Journal.replay({"alpha": 100}, journal.export_log()).snapshot(), journal.snapshot())

if __name__ == "__main__":
    unittest.main()
''', [
('if old != event:', 'if old["kind"] != event["kind"]:'),
(' or jobs[job]["owner"] != owner', ''),
('self.events.append(deepcopy(event))', 'self.events.append(event)'),
('return deepcopy(self.events)', 'return list(self.events)'),
])

c2 = PREAMBLE + '''
class Scheduler:
    def __init__(self, capacity):
        self.capacity = integer(capacity, 1)
        self.jobs = {}
        self.leases = {}

    def _owned(self, owner, job):
        identifier(owner)
        identifier(job)
        if job not in self.jobs or self.jobs[job]["owner"] != owner:
            raise ValueError("unknown or unauthorized job")
        return self.jobs[job]

    def add(self, owner, job, cost, dependencies):
        identifier(owner)
        identifier(job)
        integer(cost, 1)
        if cost > self.capacity or not isinstance(dependencies, list):
            raise ValueError("invalid job")
        for dep in dependencies:
            identifier(dep)
        if len(set(dependencies)) != len(dependencies) or job in dependencies:
            raise ValueError("invalid dependencies")
        if job in self.jobs:
            old = self._owned(owner, job)
            if old["cost"] != cost or old["deps"] != dependencies:
                raise ValueError("job conflict")
            return deepcopy(old)
        for dep in dependencies:
            self._owned(owner, dep)
        record = dict(owner=owner, cost=cost, deps=list(dependencies), state="pending", lease=None)
        self.jobs[job] = record
        return deepcopy(record)

    def _used(self):
        return sum(row["cost"] for row in self.jobs.values() if row["state"] == "running")

    def claim(self, owner, job, lease):
        identifier(lease)
        row = self._owned(owner, job)
        if row["state"] == "running" and row["lease"] == lease:
            return deepcopy(row)
        if lease in self.leases or row["state"] != "pending":
            raise ValueError("lease conflict")
        if any(self.jobs[dep]["state"] != "succeeded" for dep in row["deps"]):
            raise ValueError("dependencies not succeeded")
        if self._used() + row["cost"] > self.capacity:
            raise ValueError("capacity exceeded")
        row.update(state="running", lease=lease)
        self.leases[lease] = dict(owner=owner, job=job, result=None, canceled=False)
        return deepcopy(row)

    def finish(self, owner, job, lease, success):
        identifier(lease)
        if type(success) is not bool:
            raise ValueError("success must be bool")
        row = self._owned(owner, job)
        record = self.leases.get(lease)
        if not record or record["owner"] != owner or record["job"] != job or record["canceled"]:
            raise ValueError("invalid lease")
        if record["result"] is not None:
            if record["result"] != success:
                raise ValueError("finish conflict")
            return deepcopy(row)
        if row["state"] != "running" or row["lease"] != lease:
            raise ValueError("not active")
        record["result"] = success
        row.update(state="succeeded" if success else "pending", lease=None)
        return deepcopy(row)

    def cancel(self, owner, job):
        row = self._owned(owner, job)
        if row["state"] == "succeeded":
            raise ValueError("already succeeded")
        if row["state"] == "running":
            self.leases[row["lease"]]["canceled"] = True
        row.update(state="canceled", lease=None)
        return deepcopy(row)

    def snapshot(self):
        return deepcopy(dict(capacity=self.capacity, used=self._used(), jobs=self.jobs))
'''

save_case("c2", c2, '''import unittest
from engine import Scheduler

class Smoke(unittest.TestCase):
    def test_delivery(self):
        queue = Scheduler(5)
        queue.add("alpha", "a", 3, [])
        queue.add("alpha", "b", 2, ["a"])
        queue.claim("alpha", "a", "l1")
        queue.finish("alpha", "a", "l1", True)
        queue.claim("alpha", "b", "l2")
        self.assertEqual(queue.snapshot()["used"], 2)

if __name__ == "__main__":
    unittest.main()
''', [
('self._owned(owner, dep)', 'identifier(dep)\n            if dep not in self.jobs:\n                raise ValueError("unknown dependency")'),
('if lease in self.leases or row["state"] != "pending":', 'if row["state"] != "pending":'),
('if any(self.jobs[dep]["state"] != "succeeded" for dep in row["deps"]):',
 'if any(self.jobs[dep]["state"] == "running" for dep in row["deps"]):'),
('if record["result"] is not None:', 'if record["result"]:'),
])

c3 = PREAMBLE + '''
import hashlib
import re


class ArtifactStore:
    def __init__(self):
        self.records = {}

    def _key(self, owner, upload):
        return (identifier(owner), identifier(upload))

    def _get(self, owner, upload):
        key = self._key(owner, upload)
        if key not in self.records:
            raise ValueError("unknown upload")
        return self.records[key]

    def begin(self, owner, upload, size, digest):
        key = self._key(owner, upload)
        integer(size)
        if size > 65536 or not isinstance(digest, str) or re.fullmatch("[0-9a-f]{64}", digest) is None:
            raise ValueError("invalid upload declaration")
        if key in self.records:
            row = self.records[key]
            if row["size"] != size or row["digest"] != digest:
                raise ValueError("upload conflict")
            return
        self.records[key] = dict(owner=owner, upload=upload, size=size, digest=digest,
                                 state="active", cells=[None] * size)

    def put(self, owner, upload, offset, data):
        row = self._get(owner, upload)
        integer(offset)
        if type(data) is not bytes or offset + len(data) > row["size"] or row["state"] == "aborted":
            raise ValueError("invalid chunk")
        cells = list(row["cells"])
        for index, value in enumerate(data, offset):
            if cells[index] is not None and cells[index] != value:
                raise ValueError("conflicting overlap")
            cells[index] = value
        row["cells"] = cells

    def commit(self, owner, upload):
        row = self._get(owner, upload)
        if row["state"] == "aborted" or any(v is None for v in row["cells"]):
            raise ValueError("incomplete artifact")
        data = bytes(row["cells"])
        if hashlib.sha256(data).hexdigest() != row["digest"]:
            raise ValueError("digest mismatch")
        row["state"] = "committed"
        return data

    def abort(self, owner, upload):
        row = self._get(owner, upload)
        if row["state"] == "committed":
            raise ValueError("committed artifact")
        row["cells"] = [None] * row["size"]
        row["state"] = "aborted"

    def snapshot(self):
        return deepcopy([self.records[k] for k in sorted(self.records)])

    @classmethod
    def restore(cls, checkpoint):
        if not isinstance(checkpoint, list):
            raise ValueError("invalid checkpoint")
        store = cls()
        required = {"owner", "upload", "size", "digest", "state", "cells"}
        for source in checkpoint:
            if not isinstance(source, dict) or set(source) != required:
                raise ValueError("invalid checkpoint record")
            row = deepcopy(source)
            key = store._key(row["owner"], row["upload"])
            if key in store.records:
                raise ValueError("duplicate record")
            store.begin(row["owner"], row["upload"], row["size"], row["digest"])
            if not isinstance(row["state"], str) or row["state"] not in {"active", "committed", "aborted"}:
                raise ValueError("invalid state")
            cells = row["cells"]
            if not isinstance(cells, list) or len(cells) != row["size"]:
                raise ValueError("invalid cell array")
            if any(v is not None and (type(v) is not int or not 0 <= v <= 255) for v in cells):
                raise ValueError("invalid byte")
            if row["state"] == "aborted" and any(v is not None for v in cells):
                raise ValueError("aborted data")
            store.records[key] = row
            if row["state"] == "committed":
                store.commit(row["owner"], row["upload"])
        return store
'''

save_case("c3", c3, '''import hashlib
import unittest
from engine import ArtifactStore

class Smoke(unittest.TestCase):
    def test_delivery(self):
        store = ArtifactStore()
        data = b"useful artifact"
        store.begin("alpha", "report", len(data), hashlib.sha256(data).hexdigest())
        store.put("alpha", "report", 0, data)
        self.assertEqual(store.commit("alpha", "report"), data)
        self.assertEqual(ArtifactStore.restore(store.snapshot()).commit("alpha", "report"), data)

if __name__ == "__main__":
    unittest.main()
''', [
('return (identifier(owner), identifier(upload))', 'identifier(owner)\n        return identifier(upload)'),
('cells = list(row["cells"])', 'cells = row["cells"]'),
('if hashlib.sha256(data).hexdigest() != row["digest"]:',
 'if row["state"] == "committed" and hashlib.sha256(data).hexdigest() != row["digest"]:'),
('row = deepcopy(source)', 'row = dict(source)'),
])

c4 = PREAMBLE + '''
class AccountBook:
    def __init__(self, initial):
        if not isinstance(initial, dict):
            raise ValueError("invalid balances")
        self.balances = {identifier(k): integer(v) for k, v in initial.items()}
        self.revisions = {k: 0 for k in self.balances}
        self.receipts = {}

    def transact(self, request, operations, expected):
        identifier(request)
        if not isinstance(operations, list) or not operations or not isinstance(expected, dict):
            raise ValueError("invalid batch")
        payload = deepcopy((operations, expected))
        if request in self.receipts:
            old, receipt = self.receipts[request]
            if old != payload:
                raise ValueError("request conflict")
            return deepcopy(receipt)
        touched = set()
        for op in operations:
            if not isinstance(op, dict) or set(op) != {"from", "to", "amount"}:
                raise ValueError("invalid operation")
            source, target = identifier(op["from"]), identifier(op["to"])
            integer(op["amount"], 1)
            if source not in self.balances or target not in self.balances:
                raise ValueError("unknown account")
            touched.update((source, target))
        if set(expected) != touched:
            raise ValueError("incomplete revision guard")
        for account, revision in expected.items():
            integer(revision)
            if self.revisions[account] != revision:
                raise ValueError("stale revision")
        balances = dict(self.balances)
        for op in operations:
            source, target, amount = op["from"], op["to"], op["amount"]
            if balances[source] < amount:
                raise ValueError("overdraft")
            balances[source] -= amount
            balances[target] += amount
        revisions = dict(self.revisions)
        for account in touched:
            revisions[account] += 1
        receipt = dict(request=request, balances={a: balances[a] for a in sorted(touched)},
                       revisions={a: revisions[a] for a in sorted(touched)})
        self.balances, self.revisions = balances, revisions
        self.receipts[request] = (payload, deepcopy(receipt))
        return deepcopy(receipt)

    def snapshot(self):
        return deepcopy(dict(balances=self.balances, revisions=self.revisions))
'''

save_case("c4", c4, '''import unittest
from engine import AccountBook

class Smoke(unittest.TestCase):
    def test_delivery(self):
        book = AccountBook({"a": 100, "b": 20})
        receipt = book.transact("batch-1", [{"from": "a", "to": "b", "amount": 30}], {"a": 0, "b": 0})
        self.assertEqual(receipt["balances"], {"a": 70, "b": 50})
        self.assertEqual(book.snapshot()["revisions"], {"a": 1, "b": 1})

if __name__ == "__main__":
    unittest.main()
''', [
('if old != payload:', 'if len(old[0]) != len(operations):'),
('if set(expected) != touched:', 'if not set(expected).issubset(touched):'),
('balances = dict(self.balances)', 'balances = self.balances'),
('return deepcopy(receipt)', 'return receipt'),
('self.receipts[request] = (payload, deepcopy(receipt))', 'self.receipts[request] = (payload, receipt)'),
])

manifest = {"benchmark": "operational-alpha-stateful-software-v1", "constructed_by": "AI-assisted research team",
            "purpose": "bounded hosted-agent maintenance pilot, not frontier capability ceiling", "cases": {}}
for case in sorted((ROOT / "cases").iterdir()):
    manifest["cases"][case.name] = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                          "bytes": p.stat().st_size, "lines": len(p.read_text().splitlines())}
                                  for p in sorted(case.iterdir()) if p.is_file()}
ROOT.joinpath("CASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
