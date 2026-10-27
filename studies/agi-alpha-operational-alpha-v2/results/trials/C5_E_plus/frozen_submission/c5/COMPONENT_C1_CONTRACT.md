# Confirmation mission C1: replayable reservation journal

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
