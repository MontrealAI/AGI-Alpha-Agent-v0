# Dependency scheduler repair

Applied the supplied expert workflow to global job/lease identity, owner authorization, dependency gates and retry transitions. Regression probes first reproduced cross-owner dependencies, premature claims, reused lease IDs and failure-finish retry rejection.

Add now requires every dependency to belong to the asserted owner. Claim requires every dependency to have succeeded, enforces permanent global lease uniqueness after recognizing an exact active retry, and consumes a lease only on success. Finish distinguishes an unfinished `None` result from the completed `False` result, so failed finishes replay without changing any later attempt. Cancellation invalidates the currently active lease while preserving completed attempt history. Existing positive integer validation, staged checks, copied response values and derived capacity accounting are retained.

Invariants: used capacity is exactly the sum of running job costs and remains within capacity; only running jobs carry a lease; a lease identifies one successfully claimed attempt forever; canceled active leases cannot finish; completed result replays do not touch later capacity; dependent jobs require succeeded same-owner predecessors. All rejected operations preserve snapshots and failed claims leave their proposed lease available.

Verification: `python -m unittest test_public test_regression` passes 8 tests: the unchanged public smoke and 7 regression methods. Coverage includes pending/running/failed/canceled dependency states, owner and ordered-definition conflicts, lease reuse across tenants and terminal states, old failure replays during later attempts, cancellation, capacity exhaustion and recovery, changed finish results, boolean validation, caller mutation, and literal case-sensitive identifiers with no reserved namespace.

Limits: finite sequential in-memory scheduling, not production concurrency, authentication, process recovery or durability. No protected evaluator or supplementary tasks were used, and finite regression success is not a general correctness proof.
