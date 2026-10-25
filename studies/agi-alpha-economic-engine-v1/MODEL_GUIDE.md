# Reproducing the separate financial amendment

This directory contains a finite forward simulation, not observed commercial
collections, company invoices, new work-performance trials or executed token
transactions. It preserves the separately frozen capability and operating-cost
studies. The public preregistration and recorded GO are in `FREEZE.json` and
`AUTHORIZATION.json`.

## Cash model

The standard-library implementation is `src/financial_model.py`. From the
workspace root, use a new output directory:

```sh
python reinvestment_amendment_v1/src/financial_model.py \
  --out reinvestment_amendment_v1/outputs/reproduction-cash
```

The program verifies the public freeze identity, explicit GO, and every frozen
file before evaluating any case. It refuses to overwrite an earlier output
directory. A copy of the exact attempted model is retained in each run. If a
run fails, `FAILURE.json` preserves the traceback and input boundary. No network
request, provider invocation, credential or financial transaction is performed.

The complete declared matrix has 144 primary cases and 32 demand sensitivities,
each with twelve operating months after setup. Setup remains in both the cash
and resource accounts. The ordinary-USD collection route is a proposed company
arrangement; it is not an implemented token treasury or on-chain appropriation.
The prospective input file supplies demand, prices, reliability, collection,
refunds, reserves, resources, candidate methods and simulated outcomes.

`outputs/run-002/results.json` contains:

- `primary_cases` and `demand_sensitivity_cases`, with complete selector identities;
- `profile_accounts`, preserving imported provider/customer components and resource assumptions;
- `summary`, with requested/accepted/unresolved work, invoice face value, cash collections, all incurred and paid costs, reserves, unpaid obligations, allocations, spending, cash and conditional break-even diagnostics;
- `monthly`, with the exact twelve-step history, cash constraints, resource ceilings, backlog, forecasts, decisions and events;
- `candidates`, with constructed costs, failed and promoted simulated outcomes, subsequent uses, upkeep, forecast and realized modeled payback;
- `customer_comparison`, for both served-request cohorts and full annual-demand fallback; and
- `capacity_purchases` and `events`, retaining any bounded additions and stops.

The companion files are `results_summary.csv`, `monthly_cash_ledger.csv`,
`customer_comparisons.csv`, `event_ledger.csv` and `cost_ledger.csv`. The cost
ledger distinguishes provider, customer, current expenses, collection deductions
and payments of already incurred obligations. Reserves are cash restrictions,
not duplicate expenses. Source-zero component entries are preserved in the
frozen anchor even where a zero ledger line is omitted.

The original `run-001` and its exact model remain inspectable. The adjudicated
`REPORTING_REVISION.json` changes only report semantics: stopped operational
forecasts are zero with any restart counterfactual separately labeled; an empty
served cohort has `NO_SERVED_COHORT` and null comparison results; and complete
provider expense explicitly includes payment-processing charges. Refunds remain
contra-revenue. `outputs/run-002/REPORTING_PATH_COMPARISON.json` verifies that
all actual paths, costs, actions and annual-demand comparisons are unchanged.
Use `complete_provider_expense_including_payment_processing_usd` for complete
provider expense, or its per-expected-accepted field. The older before-collection
cost fields remain separately labeled for transparency.

Reproduce that read-only comparison with:

```sh
python reinvestment_amendment_v1/src/check_reporting_revision.py
```

All imported field reliability and full-service costs remain assumptions.
The native four-passage evidence-pack observation has zero task-time model
calls and a measured subcomponent duration; neither is used as a complete
service price or latency. The USD0.50 hypothesis is a different, unvalidated
variable-cost offering with USD200 assumed all-in traditional replacement
cost. Its USD200 cost already includes any traditional fixed readiness
allocation; no additional fixed human amount is added to that hypothetical
all-in figure. Its human duration and fallback staffing capacity remain unknown.

For the actual brief anchor, productive human durations are hypothetical
sensitivities and never become newly measured timings. Traditional fixed
enablement and twelve months of upkeep are recomputed over the specified
cohort. Failed Agent requests require complete human fallback and handoff;
unserved annual demand also requires fallback in the annual-demand comparison.
Customer attention, fallback worker minutes and provider minutes remain separate.

Provider token quotas, rate limits, network tails, daily staffing and live
executor concurrency are not established. Resource-only investment forecasts
are upper planning bounds; actual monthly service is additionally cash-limited.
A failed candidate keeps its cost. Promotion uses a frozen simulation outcome,
not independent experimental discovery. Nothing in this model establishes
self-acceleration.

The zero-reinvestment break-even diagnostic is reported only for that policy.
Investing paths additionally report a cohort-conditional combined-cost price
including all incurred construction, failed candidates and upkeep. These
algebraic prices hold the actually served cohort fixed and do not rerun demand,
collection or capacity at the changed price. Combined-cost repricing is before
the model's retained tax reserve; it is not a promise of spendable after-tax cash.

## Separate contract arithmetic and realization scenarios

```sh
python reinvestment_amendment_v1/src/token_waterfalls.py \
  --out reinvestment_amendment_v1/outputs/reproduction-tokens
```

The model reads `token_scenarios.json` and the source-inspection evidence under
`contracts/`. It produces 27 success/realization rows and nine specified failure
examples in `token_waterfalls.json`, with CSV derivatives. Manager USDC,
Ascension AGIALPHA and Jobs-v0 AGIALPHA retain their distinct amounts,
denominators, recipients, collateral and burn rules. Jobs-v0 failed/no-quorum
numerical economics remain NOT MODELED.

The current token result is `outputs/token-run-002/token_waterfalls.json`.
Its numerical contents are identical to the retained first token run; the
second run binds the shared authorization/IO module's reporting-revision hash.

Contract arithmetic uses exact integer atomic units. These values are serialized
as decimal strings, avoiding JavaScript's large-integer precision limit. The
separate hypothetical realization calculation follows the frozen continuous
`min(conversion value, liquidity)` rule. Its fractional converted/unconverted
asset-unit estimates are valuation quantities, not executable atomic transfer
instructions. Only realized hypothetical cash is available to the calculation;
unconverted assets remain inventory. Gas allowances still apply when the
liquidity limit is zero. Capital cost is imputed, not a cash loan or transaction.

Source settlement proceeds are shown before enterprise delivery, setup, review,
support, overhead, tax and reserves. They are not profit and are not bridged
into the dynamic USD cash simulation. Returned collateral and unused MARK
capital are not revenue. Burns do not establish price appreciation, tokenholder
yield or money for further model calls.

## Verification status and preserved boundaries

The producer asserts monthly cash conservation, invoice conservation, cumulative
allocation conservation and exact source token conservation. A further local
sanity check covered 5,658 cash/resource/ledger identities with no discrepancy.
Those checks do not substitute for independent arithmetic review.

Independent evaluation is maintained under `evaluation/`. The canonical
`evaluation/INDEPENDENT_AUDIT.json` is PASS with 1,288,965 equation, field,
ledger, source-identity and export comparisons and zero remaining discrepancies.
These repeated checks are not independent experiments or a reliability sample.
Its SHA256 is
`07afc7155b7d07fcd63b1ce37b9553df49b79704716fe1bef7686199c73598d7`.
It binds cash run002, token run002 and both exact producer identities. Earlier
audit attempts and reporting-adapter corrections remain inspectable.

Reproduce the independent oracles and audits in a new copy, preserving the
canonical release files:

```sh
python reinvestment_amendment_v1/evaluation/reproduce_independent.py \
  --destination /tmp/agi-alpha-audit-new-copy
```

The destination must not exist. This wrapper copies the required frozen inputs,
sources, outputs and evaluation files, runs the two independent Decimal
oracles and all audits inside that copy, appends a new core-audit attempt there,
and preserves invocation logs. It checks all 68 frozen files and exact
reproduction of the 176 cash paths, 27 token realization cases and nine failure
examples. The verified reference run is
`evaluation/reproduction-001/REPRODUCTION.json`, SHA256
`1cbc7d1b1ebb951793fae242933537ae95e3004bb3e7f89ed5228b64c325e44b`.
Running the lower-level audit programs directly in the canonical directory
would change timestamped reports, so use the wrapper for reproducibility.

The derivative `SCORECARD.json` and `RESULTS_INTERPRETATION.md` summarize only
existing audited cases. Regenerate them with:

```sh
python reinvestment_amendment_v1/src/summarize_results.py
```

That extraction verifies the canonical audit and result identities and does
not execute a scenario. Descriptive case counts retain duplicated policy/world
paths; they are not empirical success rates or market weights.

The source register can be verified without executing a contract:

```sh
python reinvestment_amendment_v1/contracts/verify_sources.py
```

That verifier authenticates retained source bytes and reference ranges only.
Historical deployment reports remain historical attestations; this amendment
does not query or establish current chain state or authorize funded operation.
