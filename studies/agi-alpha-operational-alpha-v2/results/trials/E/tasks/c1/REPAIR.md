# Reservation journal repair

Followed the supplied expert workflow: identify event-ID intent, global job identity, owner authorization and legal state transitions; assert rejection and conservation invariants; reproduce the defects; repair and rerun executable probes.

Event-ID retries now compare the complete validated event mapping, preserving the original sequence and receipt only for exact retries. Terminal transitions require the reservation's owner as well as an active job. Accepted events and exported logs are deep copies, so caller mutation cannot corrupt replay or alter accepted intent. The existing staged wallet/job update is retained, and only successful events acquire IDs and enter the log. Replay uses the same validation and transition rules and accepts exact duplicates without appending them again.

Invariants: each owner's available + reserved + spent remains its initial balance; reserved equals the sum of its active job caps; failed operations preserve both snapshot and log; each accepted first event gets the next contiguous sequence; terminal jobs cannot transition again under a new ID; external values cannot mutate journal state.

Verification: `python -m unittest test_public test_regression` passes 7 tests: the unchanged public smoke and 6 regression methods. The pre-repair run reproduced changed-payload acceptance, unauthorized terminal transitions, and event/log aliasing. Tests also cover failed-ID reuse, zero/full settlements, cancel retries, duplicate replay, malformed logs and inputs, multiple simultaneous reservations, conservation, and mutation isolation of snapshots, receipts, events and replay sources.

Limits: finite sequential in-memory behavior, without production authentication, concurrency or persistence. No protected evaluator was consulted; finite regression success is not certification for arbitrary external inputs or process failures.
