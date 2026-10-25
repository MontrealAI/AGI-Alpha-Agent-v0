# Mission economic planning

`shadow-ledger.mjs` is a pure, non-transactional extension for the existing mission
workspace. It never reads wallets, creates payment instructions, grants authority,
reserves real funds or changes the workspace's original evidence. References and
`observed` labels are supplied assertions, not authenticated receipt verification.

This follows the existing separation in
`alpha_factory_v1/core/runtime/successor/protocol.py`: `ForecastRecord`,
`ExperimentalMeasurement` (unknown is null), `AcceptedOutcome`,
`ResourceReservation` and `AllocationDecision` (obligations and reserves reduce
available resources). It does not replace those models, the operational Journal,
`runtime/chain.py` receipt verification, or `docs/assets/nova-studio/ledger.mjs`.

## Interface

```js
import {planMission, replayLedger, appendEvent} from './shadow-ledger.mjs';
const plan = planMission({
  missionId: 'fresh-public-csv-2', currency: 'USD', acceptance: 'accepted',
  reference: 'Explicit hypothetical acceptance and user-supplied accounting',
  totalCollectedCents: null, priceAssumptionCents: 10000,
  totalOperatingCostCents: 2500, operatingCostsComplete: true,
  capabilityCostCents: 1000, reserveCents: 500, obligationCents: 200,
  reinvestmentBps: 5000, humanMinutes: 5, humanHourlyCents: 6000,
  traditionalMinutes: 120
});
const replay = replayLedger(plan.ledger, {reinvestmentBps: 0});
```

All money uses safe, nonnegative integer minor units, with at most 1,000,000,000,000
per event and 4,096 events. Supported currencies are USD, CAD and EUR. No exchange
rate or token conversion is inferred. Time inputs use whole minutes. Defaults
are unknown (`null`); commercial acceptance defaults to `unknown`. A mechanically
checked local result alone does not establish commercial acceptance. An accepted
scenario must be explicitly labeled as assumed when no customer has accepted it.

`operatingCostsComplete` is an explicit assertion that the supplied aggregate
includes tools, model use, supervision, verification, all attempts/retries/failures,
recovery, applicable setup, support, business overhead and maintenance. Business
and maintenance rows are then zero *additional* cost, explicitly referenced as
included in the aggregate. Without that assertion they remain unknown. Capability
construction is separate, including unsuccessful construction. No missing cost
becomes zero. Avoid counting the same component in two aggregates.

`costBasis` defaults to `assumed`. `observed` is available for supplied measured
costs, but does not authenticate them. Reserves and unpaid obligations are separate
deductions after operating margin. They are not operating expenses, wallet
balances or commitments. Record zero explicitly when none apply.

`summary.observed` uses only observed collected proceeds and complete observed
costs. `summary.scenario` uses an assumed customer price when supplied, otherwise
collected proceeds. The two revenue columns are alternatives and are never added.
Failed attempts, rejected construction, maintenance and negative-margin missions
remain in enterprise totals. Unknown complete costs, reserves or obligations
prevent calculation of investable surplus. Positive proceeds from an unaccepted
mission cannot qualify for investment. Reinvestment from zero through 10,000 bps
only models a fraction of nonnegative available surplus; it executes nothing.

`comparison` keeps traditional labor cost, customer price plus customer attention,
and provider full cost separate. Customer attention is already included in the
attested aggregate operating cost and is not added a second time. These are conditional
equal-acceptance calculations using supplied durations and hourly cost, not
measured savings or a market-size estimate. Customer savings are never revenue.

## Event replay

The exact ledger shape is `{schema:'alpha-shadow-ledger/v1',currency,events}`.
Every event has `id`, `type`, `missionId`, `reference`. There must be one mission
event per mission with `acceptance:'accepted'|'rejected'|'unknown'`.

Accounting events also have `category`, `amountMinor` and
`basis:'observed'|'assumed'|'unknown'`. Unknown amounts must be null. Categories:

| Type | Categories |
| --- | --- |
| `revenue` | `collected` (observed), `price` (assumed) |
| `cost` | `delivery`, `business`, `capability`, `maintenance` |
| `reserve` | `reliability` |
| `obligation` | `unpaid` |

Optional `capability` events instead have `capabilityId` and
`action:'invoked'|'admitted'|'rejected'|'retired'`. They record evidence references;
they confer no permission and imply no improvement. Additional cost rows can
retain a failed attempt or later maintenance. Append identical event IDs once;
conflicting duplicate IDs are refused. Replay is deterministic regardless of event
order. Unknown fields, currencies, unsafe numbers and orphan missions are refused.
Every API first owns one descriptor-based JSON frame, before validation or any
coercion. Accessors are refused without invoking them; custom serializers,
prototypes, nonfinite values, cycles, sparse arrays and oversized/deep frames are
also refused. A changing getter cannot supply one amount for validation and a
different amount for accounting. An unknown acceptance leaves per-mission surplus
unknown, as well as preventing enterprise investment qualification.

`calculateInvestment({constructionCostMinor,failedConstructionCostMinor,
maintenancePerReuseMinor,expectedSavingPerReuseMinor,remainingReuses})` provides a
separate conditional finite-reuse calculation. All five inputs default to null.
It retains failed construction, recurring maintenance, zero/negative savings and
an exhausted reuse horizon. Savings may be signed integer minor units; the
finite horizon is a whole count from zero through 1,000,000. It reports total
cost, gross saving, net benefit, required break-even reuse and whether the
supplied finite horizon pays back. A nonpositive net saving per reuse cannot
recover a positive fixed cost. An unknown input prevents dependent conclusions.
This does not demonstrate future improvement, authorize investment, prove
capability payback or modify AGIALPHA/USDC mechanisms. Independent performance
and lifecycle-cost evidence still belong to the existing owners.

Run `node --test examples/successor-alpha/shadow-ledger.test.mjs`.
