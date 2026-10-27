# Development mission: bounded reservation ledger

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
