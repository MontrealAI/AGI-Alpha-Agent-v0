# Confirmation mission C4: atomic optimistic account batches

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
