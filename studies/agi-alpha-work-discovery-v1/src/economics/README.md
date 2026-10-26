# Calibrated finite-cash economic model

This directory contains the source for a **conditional economic simulation**, not a paid service or a market-demand
measurement. The primary production experiment supplies public local execution records. Human effort, demand,
business costs, prices, willingness to pay, useful life and CPU tariffs remain explicitly modeled.

The offering is a selected structural GET 2xx JSON response-contract dossier. A dossier identifies structural
changes and preserves their schema provenance. Documentation review is still required for runtime/API compatibility.
Every customer, human-only, public-DIY and AI-assisted comparison uses this same limited outcome.

## Order of work and commands

The economic source and calibrated inputs must be frozen before the first market outcome campaign. Run from the
study directory, with new output filenames and an absent output directory:

```sh
node tests/economics.test.mjs
node src/economics/run_campaign.mjs calibrate protocol/economics-calibration.json
node src/economics/run_campaign.mjs freeze protocol/economics-calibration.json protocol/economics-freeze.json
node src/economics/run_campaign.mjs run protocol/economics-freeze.json protocol/economics-calibration.json outputs/economics-primary
```

`calibrate` only normalizes already executed primary records. It reads the complete primary campaign, production
protocol, acquisition manifest, acceptance verifier and production source freeze; it executes no market simulation.
`freeze` records their calibration digest, the exact economic source closure, inherited accounting source, tests,
protocol and Node version. It is a local byte binding with a self-declared ordering, not an authenticated timestamp.
`run` verifies those bytes, executes exactly 384 paired worlds, and verifies source, calibration and underlying
evidence again. Existing evidence/output files are never overwritten.

The module exports are inert on import. The synthetic unit tests never call the full campaign generator or runner.
Test fixtures are explicitly synthetic and must never be used as observed calibration. Truncated model controls
are labeled `SYNTHETIC_CONTROL_OR_TRUNCATED_TEST`.

## Preserved foundations

The model imports the exact inherited `calculateInvestment` and `planMission` implementations from:

`heritage/graph-foundations/market/inherited/upstream/canonical/shadow-ledger.mjs`

Its SHA-256 is `cdc7c5a73593050a9af79b54589462e27f61b868e88ca6985d5cb639f3066d21`.
It also imports the original deterministic `randomDraw` function from the inherited `src/market.mjs`.
No inherited demand, price, quality or attention defaults are adopted. The inherited files remain verbatim.

`calculateInvestment` uses integer micro-USD here, explicitly identified in every result, to preserve signed CPU
differences below a cent. The actual finite-cash model uses integer cents. `planMission` is used for diagnostic
human-workflow comparisons. Its observed-revenue field stays zero; simulated receipts are not passed as observed
collections. Its unknown business/capability costs remain unknown in that limited diagnostic.

## Calibration and the intended-case denominator

`normalize.mjs` requires every predeclared primary version pair in every arm. Missing, duplicate or substituted
questions fail normalization. It separates:

- Intended questions, including missing frozen inputs.
- Source availability and source-acquisition failure.
- Technical acceptance conditional on available inputs.
- Per-planned, per-available and per-blocked execution CPU/wall means.
- Common acquisition, acquisition-session overhead and production-driver overhead.

The fraction of frozen questions with available inputs supplies a **scenario condition**, not an estimate of
the availability of future customer inputs. A common paired draw fixes source availability once for each intended
job. An unavailable input cannot become available through a technical retry, cannot be invoiced and does not
incur downstream onboarding/support. It does incur its observed acquisition and handling cost plus assumed
early triage. Available inputs receive the declared 0.98 conditional execution stress, up to two attempts, with
rejected-attempt correction and verification charged.

The experimental acquisition book divides shared version acquisition over eight registered questions and four
arms. Each independent counterfactual service restores the four-arm factor. Inter-question sharing remains visible.
Positive acquisition-session CPU/wall outside the individual acquisition entries is allocated over the eight
registered questions. Driver overhead is allocated over all intended primary records. The normalized record retains
both the original experimental allocation and the standalone service allocation; these are never added together.

The same unavailable source applies to human and competitor offers. The model records unavailable opportunities
for all offerings; competitor choices are choices, not assertions of accepted competitor delivery.

## Declared primary design

The protocol has 24 cells: three arrival conditions, two integration burdens, two competitor conditions and two
full-cost bundles. Each cell has 16 shared random seeds and a 52-week horizon: 384 worlds, each with four separate
counterfactual enterprises. Their seed capital is not pooled or summed into one firm's profit.

| Dimension | Declared conditions |
| --- | --- |
| Buyer pool | 24, with recurring arrival probabilities 0.025, 0.125 or 0.25 per buyer/week |
| Integration | 0 or 15 customer minutes on first use of a paid service |
| Competition | Equal complete-cost offering, or explicit 0.60 labor-cost efficiency |
| Operating cost | Low and reference bundles, with 2 or 5 residual provider minutes/attempt |
| Human workflow | 5, 15 or 45 minutes with competent conventional public tools |
| Residual-attention diagnostics | 2, 5 and 10 minutes; no measured reduction is asserted |
| Capital | USD 1,000 seed; USD 200 reserve |
| Collection | Accepted output only; two-week delay; 0.98 collection probability |
| Expenses | Accrue when incurred; due one week later |
| Lifetime | At most 26 weeks per candidate asset and no longer than a prerequisite's remaining life |

The USD 65.375 hourly wage anchor is 135,980/2,080. The annual figure is the inherited BLS May 2025 software-developer
median; 2,080 hours is an assumption. The result is an employee wage anchor, not a contractor quote, willingness to
pay or a full employer compensation estimate. The CPU valuation of USD 1 per core-hour is also an assumption.

All remaining numeric assumptions are declared in `protocol.mjs`, with their provenance and limitations.

## Pricing and practical alternatives

The tariff is fixed mechanically before economic outcomes. Both our ordinary service and the equal AI-assisted
competitor use the same complete prospective cost function:

1. Charge expected acquisition/driver CPU and early triage for unavailable sources.
2. For available sources, charge expected execution/verification attempts, corrections, support and onboarding.
3. Allocate weekly business, maintenance, tooling and ordinary setup at three **intended** jobs/week and the
   declared onboarding reuse assumption.
4. Divide by the expected collected-job probability: source availability × eventual conditional acceptance × 0.98.
5. Choose the smallest price in the predeclared labor-equivalent grid that covers that cost. If even the highest
   grid price does not cover it, retain the uncovered status; there is no outcome-selected replacement price.

This is a fixed, cost-derived scenario tariff, not observed willingness to pay. Historical research and later
capability construction remain fully charged in the ledger but are not put into the prospective tariff allocation.

Public DIY uses exactly the same competent human/public-tool duration as the human-only benchmark. It has no
extra assumed 0.15× or 0.30× effort discount. AI-assisted alternatives are separate, explicitly modeled offerings.
The equal competitor bears the same business, support, verification, maintenance and setup allocation. The strong
competitor has an explicit labor-efficiency assumption. At week 20, copying reduces its labor cost and permits a
price cut, bounded below by its full prospective cost. Both retain conventional tools; neither reconstructs them
for each job.

Buyers choose the least expensive generalized eligible offer, including their attention and first-use integration,
subject to modeled willingness to pay. They may decline. Public DIY wins an exact tie; other minimum-cost ties
are split by a common seeded draw. No arm receives an unmeasured quality, preference, graph or demand premium.

## Finite cash and the two investment gates

Opening historical discovery, failed discovery, research inference and ordinary setup are charged once. Those
historical budgets exclude the candidate construction budgets that are charged once when an investment is admitted.
These are separate **modeled budgets**, not substitute measurements for the actual study's unmetered research cost.

The ledger separates seed, simulated collections, invoices, defaults, accrued costs, paid costs, unpaid obligations,
reserves, historical/setup costs and investments. Future invoices are not spendable cash. Bills cannot create a
negative cash balance or hidden credit. An insolvent service stops taking new work, though its existing invoices
and bills continue to settle. Outstanding invoices remain uncollected at week 52 and are excluded from profit.

Available investment is:

```text
max(0, min(cash - reserve - unpaid_obligations,
           max(0, operating_collections - accrued_operating_costs - prior_investments)))
```

All four policies start with retained conventional A:

| Policy | Permitted earned-surplus succession |
| --- | --- |
| A | Retain A |
| B | A → B |
| C | A → B → C |
| D | A → B → D; second-asset costs separately itemize base incremental work and graph work |

There are exactly two possible primary investments. A rejected first gate leaves B/C/D with A. There is no
forced installation, seed-funded upgrade, repeated rebuilding of A or third simulated graph successor.

Investment forecasts use only prior execution volume, discounted by 0.5, inside the remaining useful life.
Construction, failed construction, validation, integration, authoring-inference allowance and incremental
maintenance must be repaid. Only the **signed measured conditional service CPU difference** receives benefit credit.
Common acquisition/driver cost is charged but adds no differential benefit. No source-block handling improvement,
attention reduction, demand premium, avoided reconstruction or graph quality premium is credited.

Cash rounding receives an additional conservative one-cent-per-active-week provision. The inherited calculator's
unrounded result and the conservative net benefit/break-even are both reported. Actual modeled maintenance uses
the increments of rounded cash charges, including prerequisites. Asset expiry invalidates dependent assets.
Repayment is tracked from actual simulated uses and their charged incremental maintenance, with the rounding
provision retained. It is a modeled CPU valuation, not a paid receipt.

Graph-versus-registry and unmeasured onboarding/reconstruction benefits are diagnostic thresholds only. Maintenance
sensitivities of 0×, 1×, 2× and 4× run analytically; none creates an extra favorable market campaign.

## Outputs and accounting interpretation

The runner writes:

- `protocol.json`, `freeze.json`, `calibration.json`: exact input and source bindings.
- `weekly-histories.ndjson`, `weekly-schema.json`: all 52 weekly rows for each counterfactual service, with a
  documented compact column schema.
- `policy-summaries.ndjson`: cost categories, collections, failures, investments, gate decisions and final ledgers.
- `summary.json`: each cell/policy's minimum, mean and maximum over 16 paired seeds, plus paired policy differences.
- `diagnostics.json`: observed mechanical resource means, assumed human comparisons and incremental-cost thresholds.
- `paper-summary.json`: compact 24-cell tables, unit costs, source failures, break-even/payback and null actual costs.
- `completion.json`: final exact-source verification and a clear `COMPLETE_SIMULATION_ONLY` status.

Simulated operating profit means simulated collections minus all accrued recurring costs. Simulated project profit
also subtracts once-only opening historical/setup costs and investments. These collected-basis measures deliberately
exclude outstanding receivables and retain unpaid costs. A positive operating scenario is distinct from recovery
of historical research, useful transfer, graph advantage or repayment of successive investments.

Actual collections are zero. Actual authoring/inference, human research, support, integration, maintenance and full
monetary cost remain `null` when unmetered. No token appreciation or internal transfer counts as operating earnings.
The model does not send messages, execute customer work, authenticate an agent, grant authority or transact funds.

## Preserved pre-freeze review

The first draft priced intended-order cost, used an asymmetric continuous price for the equal competitor, and
applied an additional DIY effort discount. Independent review identified those mismatches before any economic
outcome campaign. The final protocol uses collected-job costs, symmetric tariffs, neutral paid ties and matched
conventional effort. The earlier assumptions/source and review rationale are preserved in
`research-inputs/economics-prefreeze-design` outside the study working tree for the evidence companion.

The first synthetic test run exposed a signed-zero labor charge: 23/24 passed. That source identity and failure
log were preserved before correcting zero handling. Subsequent controls also exercise source-availability
denominators, common-cost allocation and the corrected paired-comparison rules. No actual market campaign was
used to select these corrections.
