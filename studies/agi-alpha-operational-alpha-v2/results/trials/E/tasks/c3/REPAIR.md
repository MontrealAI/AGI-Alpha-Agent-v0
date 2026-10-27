# Artifact assembly repair

Applied the supplied durable-service-contract workflow: map identities and transitions, state invariants, reproduce failures, validate before mutation, and verify retry and rejection paths.

The identity key is now `(owner, upload)`. Begin retries preserve the current state and require the same declaration. Writes validate every overlapping byte before filling cells, so conflicts cannot leave a partially applied chunk. Every commit validates completeness and SHA-256 before changing state. Empty declarations require the empty-byte digest. Restore copies each record and its cells, validates schema, byte ranges and state consistency, and verifies committed content. Snapshots remain sorted independent copies.

Invariants: tenant keys never alias; rejected operations leave snapshots unchanged; committed data is complete and digest-valid; aborted data is empty; retries cannot resurrect an aborted upload; external snapshots cannot modify internal storage.

Verification: `python -m unittest test_public test_regression` passes all 6 tests (the unchanged public smoke plus 5 regression methods). Before repair the regression run reproduced tenant collisions, partial conflicting writes, restored-state aliasing, and invalid empty declarations. Regressions additionally check initial digest mismatch, retry states, malformed checkpoints, boolean rejection, unknown owners, zero/maximum sizes, and caller mutation.

Limits: finite sequential in-memory behavior only. No protected tests or production durability/concurrency testing were available; passing these examples is not a proof for arbitrary Python adversaries.
