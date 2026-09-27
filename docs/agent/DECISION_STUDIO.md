[Project notice](../DISCLAIMER_SNIPPET.md)

# Decision Studio

[Open the studio](../studio/index.html). Eleven editable cases turn the project’s ideas into
bounded decisions with useful work products. Calculations run locally, without a provider, account,
wallet or external side effect. The defaults are constructed operational cases, not real deployment
measurements. Replace them with your records and review the assumptions before acting.

## Start with a decision

| Workspace | Inputs you control | Work product |
|---|---|---|
| Ω-Lattice capital committee | Capital, staffing, discounted cash flows, prerequisites | Fund/defer slate, modeled NPV, benefit shocks and verification backlog |
| Invention to operating value | Development costs, recurring benefits, dependencies | Development portfolio and prerequisite-aware economics |
| Supplier resilience desk | Quotes, fixed fees, capacities, lead times, concentration | Exact discrete supplier split, invoice totals and single-supplier outage tests |
| Factory delivery control | Ordered operations, resources, durations and due times | Resource schedule, job-priority order, makespan and lateness |
| Product launch room | Shared design, engineering and QA operations | Delivery sequence and resource calendar |
| Demand & replenishment desk | Chronological demand, stock, open orders and lead time | Holdout comparison, order-up-to target and replenishment quantity |
| Service capacity forecast | Demand history, available capacity and reserve | Future capacity gap with separate historical error |
| Microgrid dispatch console | Hourly load, solar, tariffs, import limits and storage | Feasible 24-hour dispatch with reconciled energy and costs |
| Proof Debt → AGI Jobs | Numeric criteria, exact source quotations, age and owners | Evidence docket, unresolved claims and scoped proof-job plans |
| Nova-Seeds pilot gate | Pilot thresholds, evidence and missing observations | Explicit promotion holds and proof backlog |
| Second-order agency trial | Calibration/test labels, pipeline predictions and costs | Calibration-only selection, held-out confusion matrices and complete stated costs |

All 26 original demo entries link to these practical workspaces. Their source implementations and
historical limitations remain accessible under **Original research implementations**. This is a new
practical application layer; it does not relabel the old synthetic fitness or replay backends as real AI.

## A five-minute supplier decision

1. Open **Supplier resilience desk**. The constructed case needs 60 batches, at least three suppliers,
   no supplier above 45%, delivery within 21 days and quoted on-time performance of at least 92%.
2. Select **Calculate plan**. The default solution costs **75,970 USD**, including fixed order fees.
   The row-level table is the proposed allocation. The outage tests remove each selected supplier and
   re-solve under the same constraints; read both feasibility and replacement cost.
3. Change demand, qualification thresholds or capacity. Every edit immediately invalidates the old
   result. Try a one-day lead-time limit to see a genuine infeasibility result.
4. Download the editable suppliers CSV, replace its records, and import it. CSV headers are the exact
   field names from the template. Quotes, embedded commas and multiline text are supported.
5. Export the **Decision brief**, **Row-level plan**, **Replayable dossier** and **Proof job plans**.
   The jobs describe acceptance work; no purchase order or marketplace job is submitted.

## What each engine actually computes

- **Portfolio:** enumerates every subset of at most 18 indivisible projects; enforces budget, staff
  days and acyclic prerequisite closure. Annual net benefit is discounted over the supplied horizon.
  Per-project NPV is rounded to cents before summation. Zero investment is permitted. Ties prefer lower
  cost. The input-order baseline includes prerequisite closure. Benefit shocks are scenarios, not probabilities.
- **Procurement:** dynamic programming over discrete batch counts and supplier count, including fixed
  order fees. At most eight suppliers and 80 batches. Lead-time and quoted reliability thresholds exclude
  suppliers. The share cap is rounded down to whole batches. An infeasible allocation stays on HOLD.
  Outage reallocation assumes other quoted capacities remain available.
- **Schedule:** exhaustively compares up to 7! job-priority permutations using the existing serial
  scheduling policy. Each job preserves its operation order; a resource has unit capacity. The objective
  is makespan, then total lateness. This is not a global optimum over all job-shop schedules. Due dates
  are not silently relaxed: any late job or exceeded overall window keeps the plan on HOLD. Calendars,
  setup and breaks must be included in the supplied durations.
- **Inventory:** selects last/mean/drift/seasonal forecasts on expanding training windows only. A final
  temporal holdout measures error; it does not select the model. Future estimates refit the frozen policy
  to all observations. Replenishment is `max(0, ceil(lead demand + reserve) - on hand - on order)`.
  Negative forecast demand is clamped to zero only for stock calculation. A worse-than-baseline holdout
  result stays on HOLD. The reserve is operator supplied, not a calibrated service-level guarantee.
- **Energy:** dynamic programming on a 1 kWh state grid, up to 100 kWh and 48 one-hour intervals.
  Charging losses round conservatively; discharge is ideal. Power, capacity, import limits, curtailment
  and per-hour energy balance are checked. Terminal storage must be at least its initial level. There
  is no export, load shedding, equipment control or claim of engineering certification. Savings are not
  reported against an infeasible no-battery baseline.
- **Evidence:** reconciles a numeric observation with an exact quotation and numeric token from the
  supplied source, threshold and maximum age. Missing, unbound, stale and failed criteria become jobs.
  Matching text does not establish authenticity or semantic correctness. Even when every criterion
  matches, promotion remains HOLD pending the independent signed review workflow in Proof Bloom.
- **Agency:** chooses between two recorded pipelines using calibration cost, then compares the selected
  pipeline with a baseline on test records. Costs include false negatives, false positives and execution
  on every case. A losing result or inadequate sample remains HOLD. These are supplied predictions,
  not a new model run; independence, label quality and complete operating costs need separate evidence.

## Files, replay and automation

The input schema is `agialpha.decision.v1`; reports use `agialpha.decision.report.v1`. Reports include
all input records, results, checks, limits and scoped jobs. Importing a report recomputes it and rejects
any differing output. This establishes reproducibility, not source authenticity or a cryptographic
signature. A fully rewritten input and correctly recomputed report is a different scenario.

Run the same engines without a browser (Node 22.17.1):

```bash
node scripts/decision_studio.mjs --case supply --output /tmp/supplier-decision
node scripts/decision_studio.mjs --input /tmp/supplier-decision/scenario.json --output /tmp/revised-decision
node scripts/decision_studio.mjs --verify /tmp/supplier-decision/dossier.json
```

Output directories must be empty. They receive `scenario.json`, `dossier.json`, `plan.csv`,
`decision-brief.md` and `proof-jobs.json`. Scenario inputs and CSV imports are limited to 256 KB; report imports allow 1 MiB to include derived outputs. Each engine imposes
its own row and numeric bounds. Unrecognized fields, duplicate identifiers and non-finite values fail.
CSV downloads protect formula-like text cells; a leading apostrophe may be added to text beginning
with `=`, `+`, `-` or `@`. Numeric negative values retain their numeric representation.

**Save inputs** stores only the current scenario in this browser, with explicit restore and clear
controls. Downloaded files are your durable handoff. No local save or export grants approval,
executes a trade, places an order, dispatches equipment or promotes a capability. The workspace works
offline after the full site cache completes; model weights are not required.

## Validation

`tests/browser/studio_engine.test.mjs` checks independent portfolio/procurement cost oracles,
energy accounting, schedule feasibility, train/test isolation, evidence holds, CSV parsing and tampering.
`scripts/validate_decision_studio.py` executes all eleven browser cases and replays their actual downloaded
reports through the CLI. It also verifies editing invalidation, forged-report rejection, CSV imports,
save/restore/clear, all downloads, mobile overflow, automated accessibility checks, catalog navigation
and offline recalculation. The release workflow runs this on both local build profiles and the public site.
