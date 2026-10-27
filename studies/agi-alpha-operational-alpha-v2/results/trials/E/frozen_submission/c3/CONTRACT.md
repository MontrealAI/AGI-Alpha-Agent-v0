# Confirmation mission C3: tenant-scoped resumable artifact assembly

A workflow runner uploads small result artifacts in chunks, retries writes and restores in-memory checkpoints.
Repair the assembler so artifacts remain isolated, complete and digest-verified.

`ArtifactStore()` supports `begin(owner, upload, size, digest)`, where size is an integer 0..65536 and digest is
64 lowercase hex characters (SHA-256). Upload IDs are scoped by owner, so two owners may use the same ID.
An exact begin retry is idempotent in any state; different size/digest conflicts. `put(owner, upload, offset, data)`
takes bytes, integer offset >= 0 and offset+len(data) <= size. Arbitrary overlap is allowed iff every overlapping
byte agrees. Conflicting overlap rejects the entire write, including previously empty positions. Owner/id must
identify a begun upload. Writes to aborted uploads reject; after commit only writes consistent with stored bytes
are allowed, and do not change its state.

`commit(owner, upload)` requires every position present and matching SHA-256, returns the exact bytes, and is
idempotent once committed. Missing data or wrong digest rejects without changing state. `abort(owner, upload)`
clears data and marks an active upload aborted, is idempotent for aborted uploads, and rejects committed uploads.
`snapshot()` returns a JSON-compatible LIST of records, sorted by (owner,upload), with owner,upload,size,digest,
state (`active`,`committed`,`aborted`), and `cells` (a list of byte integers or None, one entry per position).
`ArtifactStore.restore(snapshot)` restores any valid emitted checkpoint with independent state. It must reject
malformed/duplicate records, invalid cell lengths/values, committed records with holes/wrong digest, and aborted
records containing data. Restored operations obey the same contract. Caller mutations of input/returned snapshots
must not affect a store. An empty artifact is valid only with SHA-256 of empty bytes.

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
