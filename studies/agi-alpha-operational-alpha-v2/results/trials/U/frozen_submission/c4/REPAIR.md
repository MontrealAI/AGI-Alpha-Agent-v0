# C4 repair: atomic optimistic account batches

## Changes

- Revision guards must contain exactly the touched accounts, with strict nonnegative integer revisions. Missing and extra guards reject.
- Every operation and revision value is structurally validated before retry comparison. This prevents Python's boolean/integer or float/integer equality from bypassing strict API types.
- Used request IDs compare the complete ordered operation list and expected-revision mapping. Mapping insertion order is irrelevant, while operation order is significant. Exact retries return an independent copy of the original receipt before checking current revisions.
- Transfers execute against a local balance dictionary. Each ordered source balance is checked, including self-transfers; any later failure discards the entire staged batch.
- Each touched account revision increments once on successful commit. Inputs and stored receipts remain isolated from caller mutation, and failed requests never consume IDs.

## Checks

- `python test_public.py`: 1 test passed; supplied public test unchanged.
- `python test_regression.py`: 9 tests passed. Directed cases cover late overdrafts, valid replenishment ordering, self-transfer solvency, exact guards, stale guards, corrected retries, original receipts after later batches, mapping/operation equality, mutation isolation, strict types, malformed inputs, and arbitrary-size integers.
- An exhaustive bounded check covers all 2,304 two-operation batches over two accounts with initial balances 0..3 and positive amounts 1..3. A prefix-sum oracle checks solvency; accepted batches verify final balances, conservation, one revision increment per touched account, and exact retry behavior. Rejected batches verify unchanged snapshots.

## Limits

The repair implements sequential in-memory optimistic batches. No protected evaluator was available, and bounded enumeration is not proof over all input sizes or sequences. Production concurrency, process crashes, durable storage, arbitrary Python object adversaries, and authentication remain outside the contract.
