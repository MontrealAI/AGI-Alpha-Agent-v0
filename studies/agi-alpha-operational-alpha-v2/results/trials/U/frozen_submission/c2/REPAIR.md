# C2 repair: dependency scheduler with scoped leases

## Changes

- Adding a dependency requires both an existing job and the same owner. Ordered dependency-list identity remains part of idempotent add behavior.
- Claims require every dependency to be succeeded. Pending, running, failed-then-pending, and canceled prerequisites all block execution.
- A lease ID is permanently reserved by its first successful claim, across jobs, owners, failed attempts, successes, and cancellation. Only the exact currently active claim can be retried.
- Finish explicitly distinguishes the unfinished `None` result from a completed `False` result. A failed attempt's exact retry therefore remains idempotent while a later lease is active; it cannot release that later attempt's capacity. Changed outcomes reject.
- Capacity continues to be derived from running jobs, and cancellation invalidates only the active lease. Validation precedes mutation and returned job/snapshot data remain copied.

## Checks

- `python test_public.py`: 1 test passed; public test unchanged.
- `python test_regression.py`: 8 tests passed. Subcases cover tenant boundaries, every dependency state, lifetime lease uniqueness, historical finish retries, conflicting results, full-capacity claims, rejected-lease reuse, cancellation, job-definition identity, dependency ordering, mutation isolation, strict input validation, and unrestricted case-sensitive names.
- Capacity assertions check both expected usage and the sum of running costs, including retries and cancellation.

## Limits

This implements the finite sequential in-memory contract. No protected evaluator was available, so these checks do not claim exhaustive acceptance. Concurrency, process failure, durable storage, arbitrary Python object adversaries, and authentication of the asserted owner remain outside scope. Historical finish retries return a copy of the current job record, preserving the supplied API behavior without changing state.
