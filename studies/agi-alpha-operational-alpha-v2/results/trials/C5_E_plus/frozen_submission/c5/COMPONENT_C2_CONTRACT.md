# Confirmation mission C2: dependency scheduler with scoped leases

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
