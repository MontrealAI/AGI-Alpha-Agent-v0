# Commercial assessment extension

This extension reads the existing AGI ALPHA cost-stage vocabulary and reuses the
unchanged `planMission`, `replayLedger` and `calculateInvestment` APIs. It creates
no ledger implementation, worker, scheduler, account, credential, payment or
deployment action. Root-level `canonical/` contains byte-preserved existing
modules; their source identities belong in the companion evidence manifest.

## Run

```sh
node src/commercial.mjs --template > assumptions.json
node src/commercial.mjs assumptions.json > assessment.json
node tests/commercial.test.mjs
```

Run those commands from the companion root. No package installation is needed.
The assessed input must be plain JSON no larger than 2 MB. All monetary inputs
are integer USD cents; input minutes and counts are whole numbers. A missing
measurement is `null`. The code refuses unknown fields, duplicate charge IDs,
non-finite quantities, fractional cents and changed asset association.

The scenario constructor supports up to 32 explicit hypotheses. Each scenario
records accepted jobs, failed attempts, price, collection basis points, complete
service cost items, construction items, upkeep, reserves and opening obligations.
The labels and all original assumptions are retained in the output. Test fixture
numbers are arbitrary engineering controls and are not estimates for this service.

## Input contract

The exact schema is produced by `--template`:

| Field | Meaning |
|---|---|
| `asset.id`, `asset.source_sha256` | Exact retained capability and source identity; null identity cannot establish repayment. |
| `evidence` | Explicit claims about fresh equivalent work, complete monetary evidence and actual repayment, with a source reference. The module cannot authenticate these claims. |
| `actual_ledger` | Existing `alpha-shadow-ledger/v1` supplied-evidence account, or null. It is replayed unchanged. No modeled item is added to it. |
| `scenarios[].asset_id` | Must equal the tested asset. A different future idea cannot inherit its economic result. |
| `price_cents`, `accepted_jobs`, `failed_attempts`, `collection_bps` | Explicit modeled price, accepted workload, unsuccessful attempts and collection fraction. Assertions, repeated probes and reexports never supply demand. |
| `cost_items` | All eight canonical delivery stages plus business, setup and general service maintenance. Each row has one distinct bill ID, category, amount, settlement state, reference and `attempt` or `period` units. |
| `investment_items` | Discovery, construction, unsuccessful candidates, verification and integration of the same asset. Each required category must exist, including a referenced explicit zero where justified. |
| `maintenance_per_reuse_cents` | Incremental upkeep for the retained asset, distinct from general service maintenance. It is charged on accepted invocations. |
| `opening_obligations` | Separate prior-period bills that remain unpaid and are excluded from current-period costs. IDs may not duplicate any service or investment item. |
| `opening_obligations_complete` | False means the opening obligation total is unknown. An empty list means zero only when this flag is explicitly true. |
| `reserves_cents` | A modeled stock of required reserves after the period, not a reinvestment percentage or operating expense. |
| `expected_saving_per_reuse_cents`, `remaining_reuses` | Hypothesized gross incremental saving before asset upkeep against equivalent accepted work and a finite remaining useful lifetime. Unknown comparator advantage remains null. |
| `buyer` | Sourced hourly rate, separately supplied human duration and remaining buyer effort. The model computes a break-even duration without inventing one. |
| `next_investment` | Separately identified cost and independently justified case. Modeled affordability is reported separately from actual available resources and economic eligibility. No action is authorized. |

Every cost amount must include all relevant model calls, tools, compute, labor
and recovery within its declared scope. The input contract does not make a
partial estimate complete. Each bill is assigned to exactly one row and one
settlement state. A physical cost must not be duplicated using two new IDs;
identity checks catch repeated IDs but cannot discover dishonest billing labels.

The entire incremental construction account is charged once in the modeled
period. There is no implicit amortization or zero setup assumption. Per-accepted
cost includes failed delivery attempts. Zero accepted jobs yields no finite
per-accepted cost or economic break-even price.

## Two accounting projections

**Economic margin:** modeled collections minus all attributable current paid and
accrued expenses, including the complete asset investment. Unpaid current bills
already included in those expenses are not deducted a second time. The model
uses collection-adjusted revenue conservatively; it does not implement formal
accrual revenue recognition, taxation or financing accounting.

**Cash availability:** modeled collections minus paid expenses, current unpaid
expense obligations, distinct opening unpaid obligations and required reserves.
The canonical `fullCost` field in this cash projection is expressly a paid-cash
subtotal, not the economic cost of delivery. The extension exposes the complete
incurred amount separately. A settlement change from paid to unpaid leaves the
ultimate amount available after reserving obligations unchanged.

Both projections place hypothetical collections in the native assumed-price
field. Their observed collection fields remain null. Supplied actual collections
remain exclusively in the unchanged actual ledger. Customer savings, model
savings, token issuance and valuation are not incoming cash events.

## Claim boundaries

A profitable modeled period does not establish that the retained asset repaid
its cost. Repayment uses the separate canonical finite-reuse calculation,
including failed construction and incremental upkeep. A conventional tie is
compatible with a useful service and leaves the retained-method repayment claim
unproved. A positive modeled next-investment budget is not actual funding.

The model never promotes a capability or authorizes spending. It can mark a next
investment eligible for review only when the supplied exact-asset evidence
asserts complete actual repayment, the unchanged actual ledger reports sufficient
observed surplus, and a separately referenced next-investment justification is
present. Authentication, acceptance and authorization remain with their existing
owners. Unverified boolean claims do not become independently verified evidence
by being entered in this file.

## Verification

`tests/commercial.test.mjs` contains 23 focused economic and input-integrity
cases. They cover unknowns, missing stage or construction coverage, failed
delivery costs, missing settlements, duplicate bills, double counting, low/zero
demand, collection losses, maintenance, parity with the conventional alternative,
buyer savings versus receipts, exact asset association and unjustified future
investment. They do not represent customer jobs or fresh scientific confirmation.

Initial local execution passed all 23 cases under Node v24.22.1. The existing
Node 22.17.1 binary in another owner's workspace was not executable from this
worker (exit 126); no pinned-version qualification is implied by that failed
attempt. The publication owner can run the same dependency-free command under
its available authorized Node 22.17.1 runtime.
