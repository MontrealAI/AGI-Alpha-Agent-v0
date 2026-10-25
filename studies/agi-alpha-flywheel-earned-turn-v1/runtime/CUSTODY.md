# Custody and separate CPU accounts

`custody.py` is a bounded local journal and resource-accounting component. It performs no task selection,
scheduling, provider call, deployment, key creation or financial action. The existing Alpha workbench still
dispatches actual mission computation through `workbench_client.py`.

```python
from runtime.custody import Custody, digest

with Custody(run_directory, source_hash, service_ms=10000, improvement_ms=1000,
             earned_cap_ms=250, dependencies={"scipy": "1.17.0"}) as custody:
    request = {"mission": "fresh-loads", "input_digest": input_digest}
    reservation = custody.reserve("mission-b", "service", 200, digest(request))
    if reservation["execute"]:
        report, cpu_ms = execute_fixed_work(request)
        receipt = custody.commit("mission-b", cpu_ms, report)
    else:
        receipt = reservation
```

`report` must contain boolean `valid` and `qualified`. Qualified implies valid. The journal preserves these
checker observations but is **not itself a numerical checker**. A source-bound valid result may still fail
product admission or investment recovery. `accepted` on a custody receipt only means a valid/qualified result
arrived inside the local account, expiry and STOP limits. It is not production authority.

## Accounts and complete measurement

`service` and `improvement` start with separate externally endowed CPU allowances. `earned` starts with zero.
Reservation and settlement use integer microseconds, rounding reported nonnegative CPU milliseconds upward.
An operation can reserve only its named account. Failed improvement work cannot borrow the service balance.
`commit` charges measured CPU, including failures. A charge above its reservation records the actual overrun,
refuses acceptance and puts the run on terminal accounting HOLD; it does not silently charge another account.

This is **reservation and observed-cost enforcement**, not OS-level preemption of native BLAS/SuperLU calls.
One indivisible native call can exceed its reservation. The overrun remains visible; the component cannot claim
that an actual CPU ceiling was physically guaranteed. The numerical worker must use declared input-size and
call bounds, and the enclosing process must separately measure end-to-end CPU, wall time, startup, checking,
integration, storage and recovery overhead. Do not add CPU and elapsed time or convert microseconds into cash.

For an accepted completed service request:

```python
custody.release_capacity("mission-b", conservative_released_ms,
                         evidence_digest=paired_measurement_digest)
custody.reserve("construct-child", "earned", child_ceiling_ms, child_request_digest)
```

This **moves existing allowance** from service to earned. It cannot exceed that completed request's unused
reserved ceiling, the remaining service balance, or the declared cumulative release cap. The total external
endowment is conserved. Released quota is distinguished from external improvement funding in every transfer.
The caller must demonstrate, using the registered comparator and actual measured execution, whether the release
is attributable to a useful retained capability. A loose service reservation alone does not establish saved
computation, improved throughput, profit or causal feedback. A `release-capacity` record explicitly says the
custody layer has not proved incremental saving and created no cash.

## Durable identity and recovery

Each event has a contiguous sequence, previous hash and SHA-256 over its exact finite JSON. `journal.jsonl`
and the separately appended `anchor.jsonl` are flushed to disk. A process-level exclusive file lock prevents
simultaneous writers. The files are ordinary local research data; they contain no credential or signing key.

On reopening:

- All events and receipt digests are rechecked before state restoration.
- Source identity, dependencies and original endowments must equal the original configuration.
- Original absolute expiry and deadline remain fixed.
- A completed duplicate returns its original exact receipt, without a new execute instruction or charge.
- An incomplete reservation is quarantined and conservatively charged its full ceiling. Its true unclean-exit
  CPU remains explicitly unknown. That request ID cannot silently execute again.
- One fully written journal event whose matching anchor acknowledgement was lost can reconcile the anchor.
  A truncated event, inconsistent chain, missing anchor, larger mismatch or stale journal is refused.

`checkpoint()` returns the current sequence/head/source/dependency tuple. `verify_checkpoint()` requires exact
equality. Retain this tuple independently when detecting rollback matters. **The unsigned journal and anchor
share one host**: someone able to replace both with an older matching pair can rewind them. This component does
not claim cryptographic authentication or protection against the controlling OS administrator.

## STOP, expiry and assets

`stop()` appends a persistent intervention and increases the stop generation. New work remains refused after
restart. `resume()` is an explicit intervention under the same unexpired source/scope/deadline; it retains all
STOP events and does not extend authorization. CPU spent before a STOP/expiry is still charged. A result arriving
after STOP, authority expiry or the absolute deadline is retained but not accepted.

`retain_asset(id,digest,receipt_id,scope=...,parent_digest=...)` retains scoped research evidence with empty
institutional proof/authority. `select_asset(digest)` and `rollback(digest)` require a retained applicable asset.
`reject_asset(digest,reason)` is durable. A rejected descendant cannot return through another receipt or retry;
rejecting a parent invalidates selection of descendants depending on it. Rollback selects a still-applicable
earlier asset; it does not roll journal history or revive an expired authority.

The numerical implementation must recheck applicability to each actual mission (matrix identity, units,
dependency version, rank-update conditions and residual checks). The journal does not infer these mathematical
conditions merely from an asset label.

## Source-bound development checks

```sh
python3 runtime/test_custody.py
```

`development_custody_tests.json` records sixteen targeted development checks. They cover lost acknowledgement,
duplicates, unclean pending restart, invalid receipts, source/dependency changes, exhausted research allowance,
service protection, STOP/resume, stale checkpoints, expiry before/during work, deadline exhaustion, rollback,
rejected descendants, funded child construction, overruns, writer exclusion and journal rollback.
These use temporary local files, declared synthetic clock injection for one expiry case and small explicit
account amounts. They do not constitute a fresh scientific confirmation run or independent institutional audit.
