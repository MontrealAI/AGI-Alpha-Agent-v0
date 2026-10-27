# C3 repair: tenant-scoped resumable artifact assembly

## Changes

- Uploads are keyed by the `(owner, upload)` pair, preserving independent same-named uploads across tenants and canonical snapshot ordering.
- Chunk writes use a staged cell list. Any disagreeing overlap rejects the whole write without filling previously empty positions.
- Every commit verifies SHA-256 before changing state, including first commits and empty artifacts. Complete bytes with an incorrect declared digest remain active on rejection. An empty upload declaration with a syntactically valid but incorrect digest cannot commit.
- Checkpoint restoration deep copies each record and validates dimensions, strict byte values, states, duplicates, and terminal-state consistency. Committed records pass the same completeness and digest checks as normal commits.
- Exact begin retries, valid overlaps after commit, aborted-state behavior, and strict input bounds retain their documented semantics.

## Checks

- `python test_public.py`: 1 test passed; public test unchanged.
- `python test_regression.py`: 8 tests passed. Cases include tenant separation, sorted JSON round trips, atomic overlap conflicts, holes, digest mismatches, zero-length and maximum-size artifacts, lifecycle retries, malformed checkpoints, and independent original/restored state.
- A deterministic 100-write overlap sequence checks each occupied position against the intended bytes, injects conflicting writes, and restores intermediate checkpoints.

## Limits

The service remains a finite sequential in-memory assembler with the specified 65,536-byte limit. No protected evaluator was available; checks are not exhaustive certification. Concurrency, crash durability, adversarial Python objects, and authentication of the asserted owner remain outside scope. Digest validation establishes byte integrity at commit; declarations can be made before bytes exist.
