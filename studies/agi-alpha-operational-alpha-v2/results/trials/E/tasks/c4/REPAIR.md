# Account batch repair

Used the supplied expert workflow to map request identity, revision guards, sequential balance transitions and failure atomicity. Reproduced partial overdraft commits, incomplete guards, changed-intent replays and mutable retry receipts before making the repair.

Transactions now validate all operation and revision types, require exactly the touched account set, and compare the complete ordered operations plus expected map against the saved request payload. Exact retries return an independent copy of the original receipt before checking current revisions. Fresh transactions execute sequentially against a private balance map, then publish balances, one revision increment per touched account and the receipt only after every transfer succeeds. Self-transfers still require sufficient funds at their position in the batch.

Invariants: total credits are conserved; no intermediate overdrafts; each successful batch increments touched revisions once; rejected batches consume no request ID and change no state; saved intent and receipts are independent of caller-owned objects. Mapping insertion order does not affect retry identity; operation order does.

Verification: `python -m unittest test_public test_regression` passes all 6 tests, including the unchanged public smoke. Five regression methods cover late failure and request reuse, stale-revision retries, caller mutation, changed payloads and reordered operations, exact guard membership, malformed/boolean inputs and self-transfers. A seeded 100-batch sequential reference comparison checks state and conservation after both successful and rejected transactions.

Limits: this is the specified sequential in-memory service. No persistence, concurrent commits or protected evaluation is claimed; the finite tests do not prove behavior for arbitrary Python object adversaries.
