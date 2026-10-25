# Independent numerical and reporting audit

**Final status: PASS for arithmetic and frozen-definition consistency.** This is
an audit of a forward financial simulation. It is not evidence that the
simulated demand, prices, acceptance probabilities, capability gains, payments
or profits occurred.

The canonical, machine-readable release gate is `INDEPENDENT_AUDIT.json`.
It binds the final cash results, token results, both producer implementations,
the public freeze, the authorization, both independent engines and the four
numerical audit reports. The 68 prospectively frozen files remain unchanged.
The cash and token calculations began only after the separately recorded public
freeze and GO.

## Coverage and independence

The evaluator implemented `oracle.py` from the frozen protocol and inputs,
using Decimal arithmetic, without importing the producer's financial
functions. `token_oracle.py` independently implements atomic-unit waterfalls
and Decimal conversion scenarios. Producer schemas were subsequently read to
map field names. The original independent result arrays remain preserved.

| Audit | Coverage | Comparisons | Final report |
|---|---|---:|---|
| Cash core | 144 primary paths, 32 demand sensitivities, 2,112 monthly records, customer comparisons | 100,754 | `audit_attempts/attempt-002.json` |
| Components and exports | All 82,191 cost-ledger rows, 11,616 forecast-month rows, 528 candidate records, resource constraints, and every CSV cell | 878,355 | `DETAIL_AUDIT.json` |
| Reporting revision | All old actual financial paths and token quantities, allowing only the explicitly adjudicated report changes | 308,779 | `REPORTING_REVISION_AUDIT.json` |
| Token arithmetic | Nine success waterfalls, 27 realization scenarios, nine specified failure examples | 1,077 | `TOKEN_AUDIT.json` |

These counts include repeated field, identity, ledger and export-consistency
checks. They are **not** independent experiments, human observations, task
acceptance trials or a statistical sample size. Continuous comparisons use the
reported small arithmetic tolerances; atomic contract quantities are compared
exactly. There are no unresolved numerical differences in these scopes.

The figure-data check in `FIGURE_DATA_AUDIT.json` separately verifies all 91
registered plotted values against the audited result files, including source
pointers and the stated example selection. Visual PDF review is a separate
gate.

## Preserved disagreements and corrections

The initial core report, `audit_attempts/attempt-001.json`, contains 424
disagreements. Of these, 184 concerned stopped enterprises' next-month
resource-only counterfactual forecasts being displayed in an operational
field. The other 240 concerned the treatment of traditional readiness and
savings for an empty served cohort. Cash, service admissions, collections,
costs, reserves, construction, actual investment and full annual-demand
comparisons already agreed.

The root reviewer explicitly adjudicated a **post-result reporting revision**:

1. A stopped enterprise has zero operational next-month service. A resource-only
   restart counterfactual may remain in a separately labeled field.
2. An empty served cohort supports no meaningful unit-cost or savings
   comparison. Such comparison fields are unavailable; the traditional unit
   assumption and full readiness commitment remain separately visible. The
   annual-demand fallback comparison does not change.
3. Complete provider expense includes payment processing. Refunds are
   contra-revenue. Previously reported before-collection-charge cost remains
   separately labeled.

`REPORTING_REVISION.json` and both producer runs are preserved. The independent
invariance audit establishes that the actual financial paths did not change.
The final reporting rules are not represented as part of the original
prospective endpoint specification.

The auditor also preserved its own adapter corrections. The first reporting
invariance checker flagged 48 empty-cohort status-label changes; the checker
was extended to admit only the adjudicated unavailable-comparison label while
the numerical fields stayed null. Detailed audit attempt 001 stopped at a
producer customer-component name that differed from the anticipated name.
Attempt 002 stopped at the recurring candidate-upkeep label. The subsequent
adapter maps those labels and represents delivery export multiplicity as the
request count with the independently calculated method factor in the unit
amount. These changes alter no economic equations or frozen inputs.
Source snapshots, invocation records and errors remain in `audit_attempts/`.

## What the results can establish

The model can identify conditions under which a supplier and customer could
both benefit, and conditions where low variable cost, high cash balances or a
large earmark fail to produce a viable investment. It consistently charges
failed delivery paths, paid construction, failed candidates, inherited setup
and maintenance, and required upkeep. Zero new reinvestment does not remove
pre-existing construction or ongoing support from the service account.

Customer savings and provider profitability are different calculations. A low
accepted-job price can benefit a customer while failing to recover the
supplier's complete expense. Supplier invoices are not collected cash; the
last month's invoices remain receivables and cannot finance investment.
Returned collateral, initial capital and restricted tax, warranty and
working-capital amounts are also distinct from earned investable surplus.

The evidence-pack profile retains the limited native task receipt as an
observed component of an otherwise modeled service. The alternative
USD 0.50 variable-cost / USD 200 human-replacement profile is an unvalidated
offering hypothesis. Its favorable outcomes are not observations of a new
product. Promoted capabilities in the assumed-gain world are assumed
financial effects, not newly constructed or empirically accepted tools.

Capacity and forecasts use aggregate expected resource consumption. They are
not validated daily schedules, provider quota commitments, hard stochastic
budget guarantees or proof that future work will be cash-feasible. The
reinvestment simulation does not exercise paid-call budget enforcement.
Historical authoring, unquantified consequential losses and high-consequence
jobs remain outside validated scope; their missing evidence is not a zero
cost estimate.

Token results are source-based settlement arithmetic under chosen
configurations. They establish no current on-chain state, execution, market
price, liquidity, legal entitlement or enterprise profit. Only identified
worker receipts enter the worker realization examples. Other fee wallets,
validator receipts and returned collateral are separate. Jobs-v0 failed-route
economics and failure-route gas remain explicitly unmodeled.

## Reproduce without modifying released evidence

From the directory containing this amendment, choose a destination that does
not already exist:

```sh
python reinvestment_amendment_v1/evaluation/reproduce_independent.py --destination /tmp/agi-alpha-independent-audit-copy
```

The wrapper copies the required frozen inputs, sources, outputs and evaluation
files into the new directory. It runs both independent engines, the core
comparison, the reporting-invariance proof, the token audit and the component
and CSV audit. It appends a fresh core audit in that copy, compares all
independent scenario arrays exactly with the release, and verifies that all
68 frozen files in both locations remain unchanged. It preserves stdout,
stderr and the result in the new destination.

The supplied run in `reproduction-001/REPRODUCTION.json` passed with exact
cash-path and token-quantity reproduction. Timestamps and corresponding
report hashes change on a new run; numerical arrays do not. Direct audit
scripts write their designated reports, so run them only in a reproduction
copy when preserving a released artifact's bytes matters. No network,
credentials, API calls, financial transactions or additional dependencies
beyond standard Python are needed for this audit reproduction.
