# Human-market economic adapter

This is an additive, nontransactional study adapter. Its only commercial offer choices are the enterprise,
the equivalent human-delivered service, and deferral. No other AI provider or graph comparator is required.
No primary economic campaign has run merely because these files exist.

## Reuse of existing accounting

`upstream/market/upstream/src/market.mjs` is the unchanged source archived in Second Investment,
commit `daac40ee9e02a1b1bb100d7b9fcfa5caab04c297`. Its existing accounting primitives create firms,
accrue bills, pay bills, collect invoices, calculate unpaid obligations, and enforce finite cash.
`build-core.mjs` appends exports for those existing functions without changing any body. The original
AI-comparator market function remains present as provenance but is never called by this adapter.
The source and derived identities are in `core-transformation.json` and `UPSTREAM.json`.

The unchanged canonical `shadow-ledger.mjs` produces separate accrued-value and cash projections.
Simulated collections populate its scenario price field; observed collections are always zero.
The existing `funding.mjs` supplies a read-only attribution of collected operating resources. Additional
prudential fiscal reserves are applied by this adapter before investment; the original fixed-reserve
attribution stays visible and is not misrepresented as the final available amount.

## Inputs and status

`validateHumanConfig` requires every consequential economic input. Unknown monetary amounts must not be
converted to zero. The actual unmetered research, authoring, review and inference bill stays unknown;
execution requires a separately labeled complete-category cost scenario. `development-fixture.mjs`
is a deliberately synthetic arithmetic control, not pricing or production evidence.

Three production profiles can describe the same enterprise before investment, after its first investment,
and after its second. Each contains explicit support, acceptance probability, complete recurring cost,
marginal execution cost, customer attention, attempts, source identity and evidence references for every
job class. A measured acceptance fraction is not automatically a field-reliability estimate. The caller
must disclose any scenario translation, scarcity mixture and quality stress.

The offer is the matched human reference multiplied by `1-discountBps/10000`, rounded to the nearest cent.
The nominal customer saving is neither enterprise income nor net buyer benefit. Buyer decisions include
perceived quality, price, attention, switching/integration, delay, available budget and deferral.
All buyer behavior and future demand are assumptions unless separately measured.
Buyer quality beliefs remain fixed within each condition, including after rejection or refund; quality
stresses change realized service outcomes and cash, and do not constitute a learned customer-trust model.
No empirical conversion calibration is claimed.

## Investment rule

The investor only uses prior simulated opportunities. It replays each prior opportunity through the same
human/enterprise/defer choice rule with the before and after profiles, retaining the same price and
quality belief. This can value measured scope expansion without automatically converting it into sales:
a buyer may still choose the human service or defer. Projected differences are discounted and limited by
the remaining horizon and the useful lives of all prerequisite capabilities. No future outcomes are read.

Construction, validation, unsuccessful discovery and integration costs are charged once when the modeled
enterprise constructs a capability. Ongoing maintenance is charged while the capability remains usable.
The model does not claim that previously completed research was historically funded by these simulated
collections. Historical research and shared setup schedules must be assigned separately and transparently.
Pre-existing assets, fully reconstructed capabilities and externally funded experiments are different
economic interpretations; the caller must not mix their costs.

An investment requires positive projected value and enough collected operating resources after all accrued
obligations, fixed reserves and a prudential fiscal reserve. Seed capital cannot satisfy the operating-funds
test. The fiscal reserve is an explicit sensitivity assumption applied to positive operating contribution
before capability outlays, not a statutory tax rate, a tax assessment or an exemption claim.

`pairedHumanMarket` runs identical random worlds with zero, at most one, and at most two investments.
It reports own-policy differences in accepted work, final cash and complete modeled project value. A
connected cycle requires both investments, actual accepted reuse in the model, positive first-stage value,
and positive incremental second-stage value relative to the first-only control. Both stages must also earn
positive incremental cash after obligations and protected reserves. Repayment weeks use that protected-cash
basis; accrued-value first crossings are reported separately. Terminal differences must remain positive.

## Accounting boundaries

- `marginalExecutionCostCents` is contained within recurring delivery cost, never added a second time.
- Per-job recurring cost includes failed attempts; all such costs are divided by accepted deliveries.
- Setup allocations describe unit economics; the cash ledger charges shared setup once at opening.
- Payment fees accrue on collected invoices, including invoices later refunded.
- Prospect acquisition and screening are charged for every active-firm opportunity, including human choices,
  deferrals and unsupported work; they are distinct from support/revision and fixed overhead.
- Provider onboarding is separately charged once for each buyer's first enterprise attempt, including
  rejected first deliveries. Buyer attention and integration remain buyer-side costs.
- Unpaid costs and refund obligations block reinvestment; future receivables do not finance it.
- The fixed reserve and prudential fiscal reserve are distinct; neither is counted as expenditure.
- Model project value includes configured historical, setup, operating and purchased-capability costs.
  It is not a statement that actual complete research cost is identified.
- Source code contains no token revenue, wallet interface, real invoice, payment or live settlement action.

## Development verification

Run `node economics/build-core.mjs`, then `node economics/test-human-market.mjs` from the study directory.
Sixteen development controls cover exact source reuse, unknown cost rejection, the offer set, zero demand,
seed/collection timing, buyer refusal, rejection costs, zero-benefit investments, an achievable synthetic
two-stage path, acquisition costs on declined prospects, immediate refund-obligation accrual,
cash/obligation/reserve reconciliation, shared-cost allocation, and obsolescence.
The onboarding control verifies that a rejected first delivery still incurs provider onboarding once.
These tests are finance controls, not confirmatory enterprise histories or evidence of market adoption.

Before primary execution, freeze the code, price methodology, cost schedules, production profiles, scenario
grid, seeds and stopping rules. Retain every condition, outcome and failed run. Publication should show
discount, price-reference, attention, demand, maintenance, lifetime and uncertainty sensitivities rather
than selecting only profitable histories.
