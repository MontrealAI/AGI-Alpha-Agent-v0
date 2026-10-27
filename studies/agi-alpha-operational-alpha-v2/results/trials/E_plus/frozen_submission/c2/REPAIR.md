# Scheduler repair

Dependencies now require the same asserted owner and every prerequisite must be succeeded before a claim. Lease identifiers are reserved across all jobs and attempts forever; only an exact active claim can retry. Completed leases distinguish false from unfinished, retain independent finish receipts, and allow exact finish retries even after a newer attempt starts. Cancel invalidates only the active lease. Used capacity remains derived from running jobs, so terminal retries cannot release a reservation again.

All checks that can reject precede mutation. Existing strict integer, identifier and bool validation and copy isolation are retained. Public API and the supplied public test are unchanged.

Validation: the original engine failed the new suite with 2 failures and 4 errors, covering dependency ownership, lease reuse and failed-finish retries. After repair, `python -m unittest -v test_public test_regression` passed 12 tests: 1 public smoke test and 11 regression tests. Coverage includes ordered job identity, pending/failed/canceled prerequisites, authority, capacity boundaries, all lease terminal states, delayed retries, malformed inputs, and caller mutation. A 30-round exercise claims and fails seven jobs each round and checks capacity accounting and immediate retries.

The supplied `contract_probes.py` is used for rejected-operation atomicity, immediate idempotence and independent return values. Observations include the snapshot and lease history so hidden reservation/history changes do not escape the regression assertions. Delayed retries are checked separately with explicit saved receipts, in line with the helper's immediate-retry scope.

Limitations: finite sequential in-memory validation, not concurrency, process-crash, persistence or authentication certification. Owners are asserted by the caller as the contract specifies. No private tests or external services were accessed.
