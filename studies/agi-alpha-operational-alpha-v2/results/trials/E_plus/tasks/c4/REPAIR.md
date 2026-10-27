# Atomic account batch repair

Transactions now validate the complete operation schema and strict numeric types, require exactly every touched account's revision, and compare the complete ordered-operation/revision-map payload for request retries. Exact retries return independent copies of the original receipt before current-revision or balance checks, including after intervening commits. Invalid bool/float values are rejected before equality can equate them with integers.

Batch transfers execute in order against a private balance copy. A failure at any position discards that copy and does not reserve the request ID. Successful batches commit balances and increment each touched revision once, including self-transfers; self-transfers still require sufficient balance at that point. Payloads, stored receipts and all returned objects are isolated from caller mutation. The documented API and public smoke test are unchanged.

Validation: the original implementation failed seven of the new regression tests, reproducing partial mutation after overdraft, incomplete guards, changed-intent retries and aliased retry receipts. After repair, `python -m unittest -v test_public test_regression` passed 12 tests: 1 public and 11 regression tests. Coverage includes historical receipts, mapping versus list order, malformed retries, strict values, missing/extra/stale guards, late invalid operations, self-transfer affordability, once-per-batch revisions and copies. A seeded 250-batch accounting model checks every final balance/revision and receipt, retries all accepted batches, injects 50 late overdraft failures, and verifies conservation and nonnegative balances.

The supplied helper is used for failure atomicity, immediate idempotence and result independence. Main observations include both balances/revisions and saved request history. Historical retry and input-copy requirements use additional direct assertions.

Limitations: these are finite sequential in-memory checks. Concurrent compare-and-swap, durable transactions and physical crash behavior remain outside the contract and were not tested. No protected evaluator or external service was accessed.
