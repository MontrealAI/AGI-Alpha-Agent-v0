# Automated offering costs

`automated-costs.mjs` adds a shared, non-transactional operating-cost record to the
existing mission ledger. It models software replacing routine manual handling;
it does not convert a historical staffed estimate or a token subtotal into an
established cost of AGI ALPHA. Neither $31.74 nor approximately $0.17 is a default.
Frozen studies and existing ledger records remain unchanged.

## API and units

```js
import {inspectAutomatedCosts,evaluateAutomatedCosts} from './automated-costs.mjs';
const input = inspectAutomatedCosts(record);
const report = evaluateAutomatedCosts(input);
```

Every material numeric input is a fact:

```json
{"value":120000,"basis":"estimated","reference":"Offering-specific measured component or explicit scenario assumption"}
```

Allowed bases are `measured`, `sourced`, `estimated` and `unknown`. An unknown
value must be `null`; it never becomes zero. Every fact needs a nonempty provenance
reference. Money is an integer number of **micros**, with 1,000,000 micros per USD,
CAD or EUR. There is one currency per record and no token or exchange-rate conversion.
Whole minutes, basis points and parts per million represent duration, percentages
and expected repeated work. Subcent costs remain exact internally. BigInt rational
arithmetic rounds upward only at final monetary output; individually rounded
component displays may differ by a few micros from the once-rounded aggregate.

The top level has exactly `schema:'alpha-automated-costs/v1'`, `offeringId`,
`currency` and `scenarios`. Supply exactly one `base`, one `conservative` and one
`stress` scenario. These are caller-defined scenarios, not confidence intervals or
an optimization search. Their outcomes may win, tie or lose.

## Scenario fields

| Field | Meaning |
| --- | --- |
| `capacityRequestsPerMonth` | Fully utilized request capacity of the provisioned configuration |
| `utilizationBps` | Expected utilized share of that capacity; 10,000 means 100% |
| `acceptanceBps` | Expected accepted fraction of complete requests, retaining unsuccessful request costs |
| `attemptsPerRequestPpm` | Total execution attempts, including initial attempt and retries; 1,000,000 means one attempt |
| `operations` | Complete eight-stage automated operation inventory |
| `residual` | Expected genuinely residual human exceptions |
| `monthly` | Shared recurring capacity, maintenance or business costs |
| `investments` | One-time setup and development allocations with finite amortization |
| `humanBaseline` | Equivalent accepted traditional non-AI work: `minutesPerAccepted`, `hourlyCostMicros` |

All four scalar scenario fields and both human-baseline fields use the fact shape.
The four inventories are required, including when explicitly empty. An empty
residual/monthly/investment array is a supplied assertion that no such cost is
allocated; omission is refused. If a category is unmeasured, include an unknown
fact rather than removing it. All record IDs are bounded and duplicate cost IDs
within a scenario are refused across inventories.

An operation has exactly:

```json
{"id":"verify-output","stage":"verification","frequency":"attempt","unitsPerOccurrencePpm":{"value":1000000,"basis":"estimated","reference":"One verifier invocation per execution attempt"},"unitCostMicros":{"value":30000,"basis":"estimated","reference":"Explicit invocation-price estimate; not observed"},"implementation":"modeled"}
```

The eight required stages are preparation, planning, execution, verification,
correction, packaging, reporting and recovery. More than one operation can belong
to a stage, for example model invocation plus compute. A genuinely unnecessary
stage requires an explicit zero quantity or rate with its reason. `implementation`
is `implemented` or `modeled`; implemented code alone does not establish a measured
operating cost. Frequency is `request`, `attempt` or `accepted`. Use `attempt` for
costs that recur after failures; `accepted` prevents charging final packaging as
though every failed attempt delivered a usable package. Fractional or conditional
correction/recovery work uses `unitsPerOccurrencePpm`. Expected counts can model
missing live components, but do not establish that an authenticated connection works.

A residual exception has `id`, `stage`, `exceptionsPerRequestPpm`,
`minutesPerException` and `hourlyCostMicros`, with facts for its three quantities.
A zero-routine-human scenario must replace the work with charged software
operations or explain why the offering does not require it. Removing a cost row
does not implement an automation. Required input-rights, objective, scope and
execution approvals remain user decisions; no cost record changes authority.

A monthly row has `id`, `kind:'capacity'|'maintenance'|'business'`, `amountMicros`
and `allocationBps`. The amount describes the stated provisioned configuration;
an allocation applies an explicitly justified share once. A one-time investment
has `id`, `kind:'setup'|'development'`, `amountMicros`, `allocationBps` and
`amortizationMonths`. Its monetary amount is not charged for every deliverable.
Use an unknown allocation or horizon where unsupported. An investment or shared
cost must not be separately duplicated in per-request operation prices.

## Three costs and accounting identity

Let `R = capacity × utilization`, `A = R × acceptance`, and `T = attempts/request`.
Each request-frequency operation is charged once per request; each attempt-frequency
operation is charged `T` times; each accepted-frequency operation is charged the
acceptance fraction. Add expected residual exceptions to obtain variable cost `V`
per request. Let `M` be the allocated monthly recurring total, and `I` the allocated
monthly amortization of setup and development.

| Output | Formula and interpretation |
| --- | --- |
| `costs.nextRequestMicros` | `V`; expected marginal cost of the next request, including its failed-attempt burden |
| `costs.marginalMicrosPerAccepted` | `V / acceptance`; expected variable cost per accepted output across the request population |
| `costs.recurringMicrosPerAccepted` | `(R × V + M) / A`; complete recurring delivery cost at stated volume/utilization |
| `costs.fullyLoadedMicrosPerAccepted` | `(R × V + M + I) / A`; appropriately amortized setup and development added once |

There is no second utilization divisor after dividing fixed costs by accepted
volume. No/unknown accepted volume gives unknown cost per accepted output rather
than a free job. At zero utilization the recurring/fully loaded outputs are null;
a known variable next-request estimate can still be shown as hypothetical planning.
Expected average failures or recovery repetitions are not a promise that a
particular next request will complete within that average. Operational resource
ceilings and permission checks remain separate.

Results include volume denominators, operation and residual-cost attribution,
allocated amortization, unknown-input paths, and the conditional human comparison.
For each cost tier, `comparison` reports `win`, `tie`, `loss` or `unknown` against
the supplied equal-acceptance traditional workflow. If human duration is unknown,
its total cost remains unknown while a known hourly rate can still yield
`breakEvenHumanMinutes` and an upward-rounded `breakEvenHumanSeconds`. These are
thresholds, not invented human timings. Wages and task-duration evidence should be
replaced by the research owner's offering-specific sourced values; recruitment
is not a requirement of this model.

Customer savings, customer price and revenue remain in the existing shadow ledger.
This model creates neither collected revenue nor spendable cash. If a fully loaded
cost is passed to that ledger, do not charge the same setup/development investment
again as a separate construction amount. A period cash model should instead charge
actual recurring costs and actual period investments separately. Economic
amortization and a profitable price scenario do not establish available treasury cash.

## Fixtures, limits and verification

`fixtures/automated-costs-unknown.json` is the initial template: every material
numeric input remains unknown, including costs, volume and the human comparator.
`fixtures/automated-costs-example.json` is an explicitly estimated sensitivity
example. Its human hourly compensation is the preserved research BLS rate
USD35.96/hour (December 2025, including benefits); the 30-minute duration remains
an illustrative estimate, not a sourced timing. It preserves an unfavorable stress case and makes no claim
about observed Agent cost, customer demand or production readiness.

The module owns a plain-JSON frame before validation and arithmetic. Accessors,
serializers, custom prototypes, cycles, sparse arrays, unsafe numbers, unknown
fields, mixed currencies, duplicate scenarios and duplicate cost IDs are refused.
Records are bounded by node/depth/text/inventory caps. No source text is executed,
no network call is made, and no payment or scheduling interface exists.

```sh
node --test examples/successor-alpha/automated-costs.test.mjs
```

The tests cover independent arithmetic identities, repeated/failed work,
utilization, amortization, human exceptions, unknowns, zero acceptance, loss/tie,
subcent precision, malformed records, replay, mutating accessors and overflow.
They verify the planning implementation, not a live executor or measured full-cost
advantage. Future measurements can replace facts prospectively without rewriting
earlier records or frozen results.

The illustrative human comparator uses the preserved research rate USD35.96/hour
(BLS ECEC Table 4, December 2025; wages and benefits included), not a task price.
The assumed 30-minute duration remains estimated. Separately dated June 2026
sensitivities are in `contrib/productive-capability-ledger/automation-v1/HUMAN_BENCHMARK_SOURCES.json`;
no frozen research rate is replaced.

When a record includes valued customer decision time, its tiers are total resource
costs. That opportunity cost is not automatically an enterprise cash expense.
The UI carries a recurring allocation provisionally and leaves the original
ledger incomplete until actual period costs and investments are reconciled.
