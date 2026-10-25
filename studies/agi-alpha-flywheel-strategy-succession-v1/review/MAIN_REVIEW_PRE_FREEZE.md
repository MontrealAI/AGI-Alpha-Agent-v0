# Main experiment orchestration review — pre-freeze hold

This review concerns `companion/stream.mjs`, `adapter.mjs`, `learning.mjs` and `run.mjs` as first inspected after the independent Python checker was implemented and its separate development probe frozen. The producer's `core.mjs` solver/interpreter was neither read nor imported. This is a review of accounting and orchestration, not a terminal assessment of subsequent edits.

## Verdict at first inspection

**HOLD main confirmation freeze pending the following corrections.** The engine owner was notified directly; fixes are in progress. No main confirmation task or result was accessed.

### 1. Qualification controls can receive an unequal residual allocation

`qualify()` evaluates the candidate then the reference under a shrinking shared acquisition cap. Its correctness field checks only candidate rows. If a later reference gets `CHECK_RESERVE` or truncation because the stage allocation has been consumed, its reduced qualification frequency enters the admission forecast as though it were a fair specialist failure.

Reserve equivalent per-output allocations for a pair before either evaluation, or defer admission when either arm lacks its registered allocation. A specialist's genuine inability under the same fully funded output cap can remain an observed failure. A stage-starved comparator cannot. Preserve each row's allocated budget for auditing.

### 2. Cursor-only recovery guards do not protect cumulative expenditure

The inspected external guard stores source hash, mission cursor and rejected digests. An older valid snapshot at the same cursor can precede expensive discovery or acknowledgement work and restore a lower spent-work value. The guard's rejection check only refuses a rejected digest that is already active in the supplied snapshot. Subsequent persistence overwrites the guard with the restored snapshot's possibly shorter rejection history.

Use monotone spent/reserved-work and relevant completion identities in addition to cursor, or conservatively reject same-cursor stale snapshots. Merge rejection history monotonically; an older snapshot must not erase a newer refusal. A local hash establishes internal consistency, not freshness relative to later external evidence.

### 3. Restore and terminal persistence need reservations too

The inspected `restore()` uses a fixed 18,000-unit threshold before independent rechecks rather than `checkerReserve(task,result)`, and does not bound the returned checker count against that dynamic reservation. Every current recheck needs its own reservation, with control/transport cost accounted for.

`persist()` sets a stop reason when the remaining budget cannot pay its calculated checkpoint cost, but still performs `storage.save`. Reserve a terminal-checkpoint allowance or describe and account for an explicit separate control budget. The final write cannot silently become free under an all-charged-work claim.

The adapter also has a fixed envelope allowance. Ignored metadata has no semantic force, but its byte length can still cost storage/transport work. Input/metadata byte limits or an actual envelope reservation should make this bound explicit.

## Positive mechanisms observed

- Exact source/configuration binding of a restored stream.
- Explicit empty current proof and authority, including inherited assets.
- Candidate identity frozen before qualification inputs are sent to its executor.
- Separate current checker invocation for restored accepted schedules.
- Pending execution intent persisted before execution; its ceiling charged when completion is unacknowledged.
- A durable ready result can prevent rerunning an already measured mission before receipt commitment.
- Scope and expiry checked at mission checkpoints.
- Full raw failed proposals and candidate/reference rows retained.

These mechanisms are useful, but do not remove the blocking paths above. Their corrected behavior needs targeted operating tests and exact-source evidence before the main freeze.

## Method and comparators

The proposed conventional strategy-learning control should receive the same methods, input access, acquisition allocation and final checker. If it is behaviorally identical to the flywheel, report that tie. The saved-workflow/specialist controls need comparable output validation and a declared policy for early stopping under the shared mission target. A no-retention/no-discovery ablation is not a substitute for an equally enabled conventional learner.

Changing the proposed acquisition allowance from the preserved 250,000-unit development pilot to 500,000 before confirmation is a development choice, not a confirmatory result. Preserve the pilot and explain the resource tradeoff. A 500,000-unit stage allowance under a 1,000,000-unit cumulative stream budget is a ceiling, not a promise that all three stage searches can be afforded. Later deferred stages and qualified coverage lost to discovery must remain visible.

The separately frozen seven-variant regression-screening probe in this directory remains **development diagnostic evidence**. Its first-batch cost loss and exact conventional-assets tie must not be presented as main confirmation outcomes.
