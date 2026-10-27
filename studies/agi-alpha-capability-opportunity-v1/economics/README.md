# Conditional enterprise economics

This directory executes a hypothetical economy using outcomes and oracle-call counts measured by the technical
experiment. It contains no customer sales, API billing records, live ENS identities, or measured frontier-model
success rates. The enterprise's simulated collections are not earned real-world revenue.

## Reproduction and decision information

The original development-only policy freeze is `policy_freeze.json`. `scenario.json` and `offerings.json` contain
the assumptions and finite, researcher-authored offering menu. Development data, prices, routes and admission
decisions were frozen before confirmation results were read. Do not silently overwrite the freeze.

```bash
python economics/run_economics.py run
python economics/verify_economics.py
```

Run these commands from the study directory. The standard run reads `technical/results/raw_rows.json`.
`freeze` can create the original policy artifact only when it is absent; reproduction should normally retain
the supplied frozen decision artifact rather than regenerate and relabel it as a prospective decision.

The source used to create the policy freeze is preserved in `history/`. An independent audit found that the
initial execution code used a direct-search job's eventual early-stop count when deciding whether the job could
fit available cash and capacity. No confirmation economy had been run. The corrected executor reserves the known
declared query upper bound and complete promised verification before reading a protected outcome, then settles
actual calls and releases unused capacity. It also uses observed invoices for operating reserves, charges a
failed invocation, reserves known obligations before expansion and includes the missing unique diagnostic labels.
`RESERVATION_CORRECTION.json` binds the correction to the unchanged policy and retained original code.

`CONTRACT_CLARIFICATION.md` preserves a separate prose error: the original design-service description named a
fitted model even though the frozen primary contract and direct-search comparator require a measured feasible
plan. The fitted-model service is separately priced and pays for 384 independent acceptance labels. Nothing in
the corrected result counts a direct-search plan as an unproduced response model.

## Matched policies

- **Beta:** ordinary space-filling, D-optimal, adaptive sparse-regression and direct-search methods. Diagnosis
  also permits the measured 32-query paired original/faulty method, which needs no retained approximation.
- **Private:** assesses v1; retains it only if forecast value covers assessment, retention and upkeep. Only
  the originating agent can use retained capabilities. Other agents keep competent Beta.
- **Shared:** the same assessment and learning rules, with sharing only when forecast peer gain exceeds
  additional distribution cost. Every simulated member has the same entitlement; no live authentication claim.
- **Shared without Gym:** the same policy with optional additional practice disabled.
- **Shared through an ordinary library:** identical callable content, permissions and costs. No graph benefit
  is assigned. Equality with shared outcomes is a parity control, not evidence of an effective graph.
- **Controlled Gym pilot:** deliberately pays for the real 1,280-query exploratory campaign, then assesses v2
  and may reject it. This is a controlled research comparison, not a compulsory production stage.

Primary configurations can select 24, 40, 64 or 96 calls; separate sensitivity cases limit the operating envelope.
The true regime of a confirmation task is not available to the dispatch policy. Matched enterprises receive the
same sampled task, arrival, customer valuation, recipient, transfer shock and shared validator-error event.
Repeated economic seeds replay a finite observed technical sample; they are not additional technical trials.

## Price and investment selection

For each method/budget/offering, development success counts estimate quality with a Beta(1,1) smoothing prior.
The price rule checks six declared price points and chooses the one with the greatest modeled expected net
contribution, permitting rejection. Its buyer rule compares an AI offer with human delivery, deferral or decline.
These demand and trust assumptions have not been fitted to customer evidence.

Human-service anchors are estimated 16 hours for verified design and 12 hours for a validated response-model
package, multiplied by the sourced SDSU external service rate of USD 80/hour. The hours are assumptions, not
measured task duration or scope-matched quotations. The token counts in the cost bundle are assumptions; model
unit prices are sourced. No arbitrary recurring human-review minutes are imposed.

The ordinary policy considers the same finite next-offering menu. A diagnostic prototype may justify its
explicit development budget under a buyer-value hypothesis, but primary operating revenue excludes diagnostic
sales because its live acceptance and willingness to pay have not been established. Only the explicitly named
`diagnostic_market_hypothesis` scenario simulates sales under that additional hypothesis.

The optional Gym decision uses the v1 development forecast to decide whether a practice budget is affordable
and defensible; it does not read v2 outcomes before choosing practice. The controlled pilot provides a separate
comparison even if this cautious policy declines. Candidate assessments and unsuccessful practice remain costs.

## Disjoint accounting

| Bucket | Included expenditure |
|---|---|
| A | One originating accepted model delivery: 128 fitting/visible-validation calls plus 384 paid acceptance labels. Later jobs: actual fitting/search, promised independent verification, assumed frontier/tool/packaging costs, serving costs and payment fees. Failed jobs retain their delivery costs. |
| B | Additional development assessments, cached independent assessment labels, rejected-candidate assessments, retention, distribution and upkeep. The common assessment uses 896 prediction/plan labels plus 32 diagnostic labels per task, charged once per task. |
| C | Optional 1,280-query Gym development, explicitly assumed additional offering-development work, and optional capacity expansion. Full protected confirmation and repeated study-development work are reported separately as edition research expenditure. |

The same deterministic truth labels may be reused across candidate/budget assessments; they are not charged once
per row. Separate candidate construction/fitting calls remain actual resource use. The technical research ledger
preserves duplicate developmental runs and unsuccessful probes instead of deleting them.

Costs paid on execution reduce cash immediately. Payment fees are accrued when an invoice is issued and paid on
collection. Customer collections arrive after the declared delay. A correlated validator-error day may produce
false accepted invoices; subsequent refunds affect cash, while truth-reconciled research revenue never includes
those failed outcomes. The operating decision uses invoices and revealed transactions, not hidden truth.

The reconciliation is:

`cash = seed capital + gross collections - refunds paid - complete costs + unpaid payment fees`.

The equity check is:

`cash + receivables - refund obligations - unpaid fees - seed capital = profit`.

Available funds subtract obligations and declared reserves. Seed capital is never reported as revenue. Estimated
lost contribution from declined work is a separate opportunity-cost column and is not also subtracted as cash
expense. No token issuance, customer savings, speculative opportunity valuation or reinvestment fraction becomes
earned revenue.

## Outputs and limits

- `results/summary.json`: primary and sensitivity means, paired differences and conditional seed intervals.
- `results/enterprise_runs.csv`: every scenario, policy and seed; full revenue/cost/cash/obligation/reserve fields.
- `results/ledger_*_seed0.json`: complete representative event ledgers and cumulative daily balances.
- `results/matched_events_seed0.json`: the common event stream for the representative replay.
- `results/verification.json`: artificial adversarial information-boundary and accounting checks.
- `lifecycle_inputs.json`: actual development comparisons for the existing research lifecycle. These twelve
  tasks also influenced selection; the gate's interval is exploratory rather than independent confirmation.

The primary replay uses 64 customer-event seeds, 30 days, three agents, the same resource limits and source
versions. Thirty predeclared scenarios stress demand, prices, trust, query cost, transfer, reuse, congestion,
collection delays, maintenance, obsolescence, correlated errors, a stronger equal-content Beta and validation
burden. A small demand/price/trust factorial exposes joint effects. Optional expansion is considered separately
and is financed only from observed available surplus above seed capital, obligations and reserves.

The confidence intervals quantify variation under those assumptions. They do not validate prices, demand,
frontier-model ability, real-world simulator fidelity or customer acceptance. Positive simulated profit is a
conditional economic result. It is not a customer sale, proven business, autonomous invention or compounding.
