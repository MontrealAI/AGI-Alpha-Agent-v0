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
| Service staffing & backlog desk | Case history, handling time, shift coverage, staff caps and costs | Per-shift additional staff, uncovered workload, backlog and incremental cost |
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

## A staffing decision you can inspect

1. Open **Service staffing & backlog desk**. Each historical observation is one shift's incoming cases;
   each Coverage row is one future shift. Replace both tables using their CSV templates.
2. The constructed example uses 12 minutes per case, an eight-hour shift, 25% unavailable time and
   85% handling occupancy: **306 productive minutes, or 25.5 case-equivalents per person per shift**.
   A 10% arrival reserve and 120 existing cases are included; the backlog target is three shifts.
3. Calculate the plan. It proposes **31 additional staff shifts costing 7,920 USD**, with at most five
   additional people in any shift. The row table reconciles incoming work, staff, capacity and backlog.
4. Set the first shift's additional staff cap to zero. Recalculate: the uncovered workload stays on
   **HOLD** and the backlog flows forward. Spare time on another day cannot retroactively cover it.
5. Inspect the +20% demand shock. It exceeds the stated staffing caps, so its cost is labeled with a
   shortfall rather than presented as an adequate plan. The forecast validation table remains separate
   from the proposed roster. Review handling time, skills, calendars and response-time requirements.

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
  minimizes total job lateness plus delivery-window overrun, then makespan. All deadline-feasible orders
  outrank all violating orders. The commitment table includes due times, completions and slack. This is
  not a global optimum over all job-shop schedules, and HOLD does not establish global infeasibility.
  Any late job or exceeded overall window keeps the plan on HOLD. Calendars,
  setup and breaks must be included in the supplied durations.
- **Inventory:** selects last/mean/drift/seasonal forecasts on expanding training windows only. A final
  temporal holdout measures error; it does not select the model. Future estimates refit the frozen policy
  to all observations. Replenishment is `max(0, ceil(lead demand + reserve) - on hand - on order)`.
  Negative forecast demand is clamped to zero only for stock calculation. A worse-than-baseline holdout
  result stays on HOLD. The reserve is operator supplied, not a calibrated service-level guarantee.
- **Service staffing:** uses the same training-only forecast selection, then plans each future shift
  independently. Productive minutes per person are `shift hours × 60 × (1 − shrinkage) × occupancy`.
  Buffered arrivals round up; completed case capacity rounds down. The work target includes current
  arrivals and an equal-share clearance of the remaining backlog before its target shift. It adds the
  minimum whole staff needed for that target, capped by that shift's available extras. Actual remaining
  backlog carries to the next shift; excess capacity does not. Any uncovered target or worse-than-baseline
  forecast holdout keeps the plan on HOLD. This is an aggregate workload rule, not a queueing/SLA guarantee
  or a multi-period cost optimizer. Staffing costs cover additional shifts only.
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

The input schema is `agialpha.decision.v1`; new reports use `agialpha.decision.report.v2` and bind
`calculation_version: "1.10.0"`. Original `agialpha.decision.report.v1` dossiers replay through the archived
1.9.0 calculation policy and show that version beside the method. Recalculating those inputs uses the
current policy and produces a new report. Unsupported versions fail explicitly. Reports include all
input records, results, checks, limits and scoped jobs. Importing a report recomputes it and rejects
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
