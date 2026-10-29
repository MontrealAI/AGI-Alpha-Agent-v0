# Structural transfer runtime

The additive `transfer` workflow extracts a typed relation from executed source work,
retrieves it by its structural signature, validates an explicit variable mapping,
constructs a whitelisted target adaptation, and checks its output independently.
It does not execute supplied code, call a model, fetch a URL, or send a payment.

The ordinary mission lifecycle remains available. A mission with
`work.kind = "structural-transfer"` uses the same pipeline and stops at operator
review before a native mission export.

## Operator commands

Run the installed entry point with an existing environment:

```sh
alpha-agent transfer extract source.json --output extracted
alpha-agent transfer inspect extracted/capture.json
alpha-agent transfer run request.json --output delivery
alpha-agent transfer check delivery
```

Use a new output directory for each extraction or run. Existing files and source
inputs are not overwritten. Keep failed runs: their records show which stage
failed and prevent an unsuccessful adaptation from disappearing from the record.

`extract` verifies the supplied source execution evidence before it emits a
principle. `inspect` reports the principle's typed variables, relation graph,
assumptions, applicability boundaries and provenance. `run` executes the pipeline;
`check` reconstructs acceptance from the captured inputs and artifact.

An extraction creates `source.json`, `capture.json` and `extraction-check.json`.
A successful run creates `request.json`, numbered stage records, `result.json`,
`constructed.json`, `artifact.json`, `acceptance.json`, `delivery.json` and
`verification.json`. Once a run starts, a failure leaves its input, completed
stages and `failure.json` in place.

## Source records

Primary transfer requires `kind = "adapter-work"`: an actual operation through
the installed adapter registry, a nonempty evidence manifest and source cost
identities. Its `task` contains `adapter_id`, `target` and `constructed`; the
runtime executes the source operation and independently checks its artifact.
Each evidence manifest item declares `path`, raw-file `sha256` and `role`.
An optional provenance `url` is a citation and is never fetched. Source context
must be explicit in `context`.

The small built-in operations `capacity-ledger`, `interval-audit` and
`precedence-schedule` exercise extraction locally. For example:

```json
{
  "schema": "agialpha/structural-source/v1",
  "id": "capacity-development",
  "kind": "capacity-ledger",
  "task": {
    "dimension": "currency",
    "unit": "microUSD",
    "capacity": "100",
    "demands": [{"id": "first", "amount": "40"}]
  },
  "context": "Development arithmetic; no customer or cash attestation."
}
```

This executes a reservation and extracts its checked capacity identity. Its
capture is marked `developmental_only = true` and cannot qualify as the primary
source for `transfer run`. Changing that flag and refreshing its hash does not
bypass source replay.

## What transfers

A principle records variables with units and dimensions, relations, constraints,
assumptions, an extraction method and its applicability boundaries. Retrieval
uses a typed graph signature, rather than a prose match. A target request must
declare its need and map source variables to the target variables explicitly.
Missing variables, undeclared units or dimensions, inconsistent dimensional
equalities, reversed causal roles and unsupported extrapolation are rejected
before adaptation. A dimensional binding has mode `structural-instantiation`:
it instantiates a relation in a new domain and performs no numerical conversion
between the source and target quantities.

An observed ledger identity supports a bounded accounting or capacity structure.
It does not establish a physical law in a new domain or attest that simulated
ledger balances are actual cash. The current extraction status is
`supported-axiom-instantiated-by-checked-execution`; it does not claim to have
discovered an empirical invariant. Unsupported manually supplied validation
flags cannot substitute for source verification.

The adapter registry is fixed in repository code. It builds a concrete target
operation from the validated mapping and target inputs. The checker recomputes
the relevant target conditions without accepting the adapter's own success flag.
Acceptance must be a literal JSON boolean and must bind the exact target and
artifact identities.

## Evidence and costs

Each run retains bounded input captures and hashes for the source evidence,
source task and result, principle, target request, constructed adaptation,
artifact and executing code. Those bindings make later substitution detectable.
Each JSON input is limited to 1 MiB; duplicate keys, nonfinite numbers and unknown
contract fields are rejected. Quantities use bounded exact rational strings,
such as `"3/2"`, rather than floating-point JSON numbers. Captured evidence bytes
remain bound to their raw-file hashes even after the original file changes.

Costs are explicit quantities multiplied by rates. Source work, retention,
adaptation and research remain separate, and cost IDs must be unique. These
records contain declared quantity and price estimates, with `currency = "USD"`
and `basis = "estimate"`. They do not establish measured resource use, customer
demand, a cash collection, or a profitable successor. The source capture's
`cost_ids` must appear exactly once in the request's source cost stage.

Delivery links an accepted artifact to its target need and recorded economic
terms. Payment or settlement requires the separately authorized existing flow.
An already implemented adapter cannot be represented as a newly learned
successor merely because it was selected through retrieval.

## Local validation

The focused regression suite is additive:

```sh
../env/bin/python -m pytest contrib/structural_transfer/test_runtime.py -q
```

The suite covers source binding and replay, mapping rejection, strict acceptance
booleans and identities, cost identity, file collisions, retained failures and
the ordinary mission review/export lifecycle. Its full-pipeline adapter is a
test-only arithmetic fixture. These authored regressions do not freeze an
evaluation set or provide evidence of general transfer ability.
