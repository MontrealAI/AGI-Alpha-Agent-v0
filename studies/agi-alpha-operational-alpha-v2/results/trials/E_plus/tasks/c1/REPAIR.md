# Reservation journal repair

Event-ID retries compare the complete validated event payload and return the original receipt. Terminal transitions require the reservation's asserted owner. Accepted events are copied on entry, log exports are deep copies, and receipt/snapshot isolation is preserved. The existing staged wallet/job transaction remains: rejected events never consume an ID, advance the sequence, alter balances, or enter the replay log. Only exact event-ID retries bypass the active-job requirement; new terminal event IDs still reject after settlement or cancellation.

The supplied public API, event schema, accepted-event order and public smoke test are unchanged.

Validation: the original engine produced four failures in the regression suite (changed intent, wrong owner, input aliasing and malformed replay conflicts). After repair, `python -m unittest -v test_public test_regression` passed 10 tests: 1 public and 9 regression tests. Cases cover strict types and amounts, rejected-ID reuse, receipt sequence, retry after termination, terminal boundaries, independent results, ordered replay with duplicates, malformed logs and case-sensitive names. A seeded accounting exercise processes 200 reservations and 200 terminal events, retries all 400 events, checks nonnegative conservation after each transition and reconstructs the same state and log through replay.

The supplied helper is used for rejected-operation atomicity, immediate retry idempotence and returned-object isolation. The primary observer includes snapshots, exported events and receipt history; input-copy and delayed-retry obligations use direct domain assertions. No helper assumptions were extended to concurrent or external effects.

Limitations: finite sequential in-memory checks only. There is no filesystem persistence, crash recovery process, concurrent execution or authenticated identity system beyond the asserted-owner checks specified by this contract. No private evaluator or external services were accessed.
