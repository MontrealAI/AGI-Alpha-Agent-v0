# Delivery-extracted observable-contract probes

## Origin and observed motivation

This is a researcher-directed, development-origin extraction of ordinary
contract-testing logic from this repair. It applies the supplied
`durable-service-contract-workflow` expert method; it is not a claim of novelty,
autonomous scientific discovery, model change, or weight update.

The observed development failures were concrete: a changed retry payload was
accepted, a wrong-owner action mutated another balance, and a returned snapshot
aliased internal state. The alias was particularly relevant to testing: simply
retaining a live pre-operation snapshot can let subsequent mutation also change
the expected baseline, concealing a failed atomicity check.

## General method actually extracted

`contract_probes.py` implements three reusable assertions:

- `assert_rejected_unchanged(case, observe, action, exception=ValueError)` freezes
  an independent pre-action observation, requires the documented rejection,
  and compares the resulting observable state with that frozen baseline.
- `assert_idempotent(case, observe, action)` performs an action and its immediate
  retry, requiring equal results and unchanged state after the retry.
- `assert_independent_result(case, observe, action, mutate)` executes an action,
  freezes the resulting service observation, deliberately mutates its returned
  object, and checks that the service observation remains unchanged.

Each helper accepts actions and observers instead of importing a particular
service. Baselines use `deepcopy`; expected results are frozen before retries.
The helper contains no ledger implementation, business-rule oracle, task
fixtures, protected answers, or customer information. Service-specific rules
and the accounting oracle stay in `test_regression.py`.

## Use and possible transfer

The delivery uses these helpers for rejection atomicity, retry identity, and
copy isolation across the ledger's public operations. They can transfer to
other bounded stateful APIs when those APIs promise the same properties, such
as sequential inventory reservations or in-memory job registries. A new caller
must supply its own operations, invalid cases, mutation functions, and complete
observer; the helper does not infer what an operation is allowed to do.

The useful separation is between domain decisions and repeated observation
checks. A frozen baseline protects a check from a defective aliased observer,
while shared assertions make it easier to apply the same promise at multiple
operation states and boundaries.

## Evidence and limits

The repaired delivery passed the unchanged public smoke test and 15 regression
tests, including 3,200 seeded operations. The helper is used by those tests;
three additional generic checks within the 15 demonstrate detection of
intentional mutation-before-rejection, repeat side effects, and live returned
objects. These are local development observations, not an independent transfer
evaluation, controlled effectiveness comparison, or quantified productivity gain.

Assumptions: synchronous sequential calls; a side-effect-free observer covering
all contract-relevant state; values with meaningful equality and safe
`deepcopy`; and deterministic immediately repeated results when idempotence is
promised. Calls interleaved with other actions require their own expectations.
A timestamped or otherwise intentionally changing receipt would require an
adapted comparator, which this small helper does not provide.

An observer cannot reveal omitted external effects. These probes do not check
thread races, external services, durable writes, process crashes, authentication,
or malicious custom Python object behavior. Finite cases do not prove the
contract universally. No fresh confirmation task or private acceptance result
was inspected when producing this artifact.
