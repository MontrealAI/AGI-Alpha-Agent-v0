# C1 repair: replayable reservation journal

## Changes

- Exact event-ID retries compare every event field. Reusing an ID with a different job, owner, kind, or amount raises ValueError and cannot change the original receipt.
- Both terminal operations verify the asserted owner against the active reservation before modifying a wallet.
- Accepted input events and exported log entries are deep copied. Caller mutation cannot rewrite replay history or accepted-ID identity.
- Existing strict integer validation, copy-before-commit transitions, terminal-state rejection, contiguous receipt sequencing, and ordered replay behavior remain in place. Failed operations do not reserve IDs.

## Checks

- `python test_public.py`: 1 test passed; supplied public test unchanged.
- `python test_regression.py`: 7 tests passed, with subcases for malformed inputs, boolean/float rejection, unknown owners/jobs, complete retry identity, authorization, terminal repeats, failed-ID reuse, zero/full settlement, input/output isolation, malformed replay, and duplicate replay.
- A deterministic 80-job interleaving checks wallet conservation after every job and verifies exported-log replay equivalence.

## Limits

Validation covers the finite sequential in-memory API. No protected evaluator was available; passing these tests is evidence, not a claim of exhaustive acceptance. Thread/process concurrency, persistence, arbitrary object adversaries, and identity authentication remain outside the contract. Replay retains the supplied API's list-based log input.
