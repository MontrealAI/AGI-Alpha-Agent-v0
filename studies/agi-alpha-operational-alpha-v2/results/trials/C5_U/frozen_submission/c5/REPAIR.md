# Campaign audit repair

## Delivered scope

`engine.audit(packet)` now builds a release decision only after validating and
reconciling all four supplied component replays. Its public signature and exact
release/hold envelope remain unchanged. The four verified components and the
canonical public test are unchanged. `test_regression.py` is additional test
coverage using only the published contract and standard library.

This is a finite, sequential, in-memory audit of submitted campaign evidence. It
performs no live release, external settlement, network access or remediation.

## Corrected behavior

1. **Complete-input identity.** SHA-256 is computed once from the entire supplied
   packet using the exact canonical JSON options in `CONTRACT.md`, with UTF-8
   encoding. It is retained for both release and hold; it is never replaced by a
   hash of a derived summary. Exact retries can leave the financial result
   unchanged while changing this evidence hash. Mapping order does not change it.
   If encoding is impossible, the hold packet has a null hash.
2. **Declarations and execution.** Job fields, positive integer capacities/costs,
   globally unique job IDs, unique tenant artifact assignments and earlier,
   distinct, same-owner dependencies are checked. All commands are replayed
   through Scheduler. Every declared job must finish succeeded, the final job set
   must match declarations, and used capacity must be zero. Pending, canceled or
   unsuccessfully retried jobs cannot pass merely because they use no capacity.
3. **Reservation evidence.** Journal replays every submitted event under its own
   validation and retry rules. Its job set, owner, reservation cap and settled
   terminal state must match the declarations. Actual consumption comes from the
   accepted settle events, including zero. Exact event retries are excluded from
   its accepted log and cannot increase consumption.
4. **Tenant-bound deliveries.** ArtifactStore restores and validates the submitted
   snapshot. Its exact `(owner, upload)` set must match required artifacts, and
   every record must already be committed. The audit does not promote an active
   upload into acceptable evidence. Idempotent reads of the restored committed
   records yield complete, SHA-256-verified bytes for the byte total. Duplicate
   records, missing artifacts, extra artifacts and cross-tenant substitutions hold.
5. **Per-job credit settlement.** Every positive-consumption job requires exactly
   the logical request `settlement:` plus its literal job ID. Each batch must
   contain one transfer from that job's owner to `__usage__`, for exactly that
   job's actual consumption. Zero-consumption jobs require no batch. Shapes and
   integer types are checked before AccountBook validates revision guards and
   exact request retries. Matching campaign totals cannot excuse swapped job
   amounts or an indirect transfer route.
6. **Independent final reconciliation.** Per-owner settled totals are summed from
   journal consumption. Every final account balance is checked against Journal
   available credits, every Journal reserve must be zero, and Journal spent must
   equal the corresponding settled total. Usage-sink credits must equal their sum.
7. **Isolation and failure envelope.** Audits use a private copy and fresh
   component instances. Returned summaries cannot affect subsequent calls. Domain
   validation errors and ordinary malformed-input errors produce a descriptive,
   nonempty hold reason and an empty summary. Numeric integers exclude booleans.

The implementation delegates each service's local state machine to its supplied
API and separately enforces the relationships between services. It imposes no
additional chronology between otherwise valid scheduler, journal and accounting
streams beyond the published contract.

## Executed validation

Run from this task directory:

```sh
python test_public.py
python -m unittest -v test_public test_regression
```

Observed results through the logged runner:

- Unchanged canonical public smoke: **1 test, passed**, exit status 0.
- Final combined run: **26 tests, all passed**, exit status 0; 0.214 seconds as
  reported by unittest. This comprises the canonical smoke and 25 added tests.
- Added coverage includes 80 deterministic generated campaigns checked against
  independently calculated expected summaries; multi-tenant dependency graphs;
  failed attempts and late exact retries; zero consumption; empty and maximum-size
  artifacts; shared upload names across tenants; malformed nested JSON;
  integer/boolean boundaries; input/output isolation; canonical hashes; mismatched
  per-job amounts; and balanced but forbidden indirect transfers.

One earlier combined run had one failure in a newly written test: it assumed that
1,100 nested lists would always make JSON encoding fail. Encoding succeeded in
this runtime, correctly requiring a non-null hash. That test now checks the
actual canonical-encoding result rather than assuming a fixed recursion limit.
No engine change was needed for that test correction. The final run passes.

Independent protected contract checks are unavailable here and were not inspected
or run. These public results support the bounded prototype; they do not establish
universal correctness for all possible environments or input sizes.

## Remaining limits

- Submitted identities and evidence are asserted, not authenticated. The digest
  identifies complete input content; it is not a signature or proof of origin.
- There is no connection to live services, customer workflow, currency, physical
  delivery, distributed clocks, concurrent workers, crash recovery or filesystem
  durability.
- Agreement among supplied records cannot establish the truth of those records
  outside this finite model. Live export completeness and provenance need a
  separate validation process.
- Malformed JSON-compatible evidence is held. Arbitrary hostile Python objects,
  unbounded resource exhaustion and interpreter/process failure are outside scope.
- Hold reasons identify the first detected failure; this is not an exhaustive
  incident diagnosis or an automatic repair plan.
- Customer demand, avoided incident cost, review-time savings, price and operating
  reliability have not been measured.
