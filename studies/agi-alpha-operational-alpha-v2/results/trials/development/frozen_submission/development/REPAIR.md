# Reservation ledger repair

## Corrected behavior

The repair preserves `Ledger(initial)`, `reserve`, `settle`, `cancel`, and
`snapshot`. The supplied `test_public.py` is unchanged. It fixes four observed
contract violations:

1. A reservation retry previously ignored a changed cap. The original request
   now binds both owner and cap permanently, including after settlement or
   cancellation. An exact retry returns the current record without moving funds.
2. Request lookup previously did not enforce ownership. A settlement asserted
   by a different tenant could debit that tenant's reserved amount, making it
   negative. Lookup now validates the owner, request, and ownership before any
   state-dependent early return or wallet update. Unknown owners consistently
   receive `ValueError`, including on terminal requests.
3. A repeated settlement previously ignored changed actual consumption. Only
   an identical actual amount is now an idempotent retry; changed amounts reject.
4. Snapshots previously returned live dictionaries. They now copy both nested
   wallets and request records, so caller mutation cannot change the ledger.

The initial reproduction reserved 40 from one tenant and then settled 25 while
asserting a different tenant. The second tenant incorrectly reached available
115, reserved -40, spent 25 from an initial 100. Separate probes reproduced
changed-cap acceptance, changed-actual acceptance, and mutable snapshots.

## Transition and rejection rules

| Operation | Identity and authorization | Successful effect | Retry and rejection behavior |
| --- | --- | --- | --- |
| Initialize | Nonempty string owners; exact nonnegative integers | Each owner starts with available equal to its initial balance | Invalid initial mapping, owner, or balance raises `ValueError` |
| Reserve | Known owner; globally unique request binds owner and positive integer cap | Available decreases by cap; reserved increases by cap | Matching owner and cap returns the current record in every state; changed intent or insufficient funds rejects |
| Settle | Matching owner; exact integer actual in the inclusive range zero through cap | Reserved decreases by cap; spent increases by actual; remainder returns to available | Identical settlement retries succeed; changed actual and canceled requests reject |
| Cancel | Matching owner | Full active cap returns to available | Repeated cancellation succeeds; settled requests reject |
| Snapshot | No arguments | Independent complete observation | Observing and mutating returned copies have no ledger side effects |

All validation and conflict checks occur before the first mutation. The
existing arithmetic transitions then operate on ordinary validated integers
and dictionaries; no transaction-copy mechanism is needed for the bounded
sequential contract. Boolean values remain invalid numeric inputs.

After each accepted transition, amounts remain nonnegative and each owner's
available + reserved + spent equals its initial balance. Reserved totals equal
the sum of active caps; spent totals equal accepted settlements. Rejected
operations preserve the entire observed state. Methods that return records
continue to return independent copies.

## Verification

Commands run in the development task directory:

- `python test_public.py`: **PASS**, 1 unchanged smoke test.
- `python -m unittest -v test_regression`: **PASS**, 15 tests.

Regression coverage includes validation, missing identifiers, cross-owner
operations in all request states, exact and conflicting retries, insufficient
funds, zero and full settlement, cancellation conflicts, returned-copy isolation,
multiple concurrent active reservations in sequential use, and large integers.
Forty deterministic sequences of 80 operations each compare the implementation
to an independent accounting model that derives wallet totals from records.
The seed is fixed for reproducibility. Generic probe checks also demonstrate
that the helpers detect deliberately broken rejection, retry, and copy behavior.

Before repair, four selected regression methods produced 24 failing subcases
and 2 errors. Some failures cascade from deliberate snapshot mutation; these
counts are diagnostic output, not a count of distinct implementation defects.

## Deliverables and limits

`engine.py` contains the repair. `test_regression.py` contains service-specific
coverage and probe checks. `contract_probes.py` contains only reusable assertion
logic. `CAPABILITY.md` explains that extraction and its limits.

This is an in-memory, sequential Python 3.11+ repair using the standard library.
It does not add concurrency control, persistent storage, process-crash recovery,
or authentication. The caller supplies the authenticated owner. Arbitrary
Python object adversaries and direct mutation of implementation attributes are
outside the documented method-based contract. No hidden tests were inspected,
and no protected acceptance result was available. Passing these finite tests
is evidence for this bounded contract, not production certification or proof
for all possible inputs and schedules.
