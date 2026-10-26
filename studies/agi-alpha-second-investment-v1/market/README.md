# Second-investment market continuation

This extension carries the existing finite enterprise forward. It is research software,
not a payment system. Every monetary amount remains **simulated**; observed customer
collections remain zero.

## Preserved source

`upstream/src/market.mjs` is the byte-identical frozen strategic market source
`52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27`.
The canonical ledger modules, calibration and protocols retain their original bytes.
`upstream/CUSTODY.json` records their identities.

`build-core.mjs` generates `continuation-core.mjs` through nine exact insertions.
`core-transformation.json` contains every before/after anchor. With no continuation
hooks, the generated core must return the exact same JSON as the original.

```sh
node build-core.mjs
node --test tests/test-continuation.mjs
```

These tests are synthetic software controls. They are not a new market campaign,
customer workload, confirmation cohort or evidence of a worthwhile investment.

## Comparison contract

`pairedContinuation(config, seed, {B: profileB, C: profileC})` uses the existing
**first-asset B enterprise for all three new arms**. New A keeps that strong incumbent.
New B and C may construct their separately identified second improvements.
The code verifies exact shared histories before the earliest second decision and
verifies that new A equals the unmodified original B.

The original 52-week horizon, first-asset costs, buyers, prices, quality, capacity,
competitors, outstanding invoices and obligations remain. Only explicitly supplied,
evidence-bound second-asset effects can change production or customer effort.
Construction causes a declared finite service pause. No added external capital,
future receipts, token issuance or buyer savings enter the financing test.

## Candidate profile

Profiles use schema `agi-alpha-second-investment-continuation/v1` and require:

- Exact asset and acceptance-evidence SHA-256 identities and explicit tested status.
- `researchPrototypeConstructed` discloses whether the research prototype already exists.
- `policy` is either `adaptive` or `completed-research-replay`. The latter requires one
  fixed decision checkpoint (`earliestWeek === lastDecisionWeek`).
- Earliest/latest decision week, construction pause, finite useful life and resource cap.
- Integration-failure probability and conservative forecast discount.
- Every one-off category: `priorDiscovery`, `discovery`, `rejectedCandidates`,
  `construction`, `verification`, `integration`, `researcherContribution`, `modelAndTools`.
- `weeklyMaintenance` as a separate recurring cost.
- For each cost: `amountCents`, `basis`, and `explanation`. Basis is `scenario`,
  `measured-time-assumed-tariff`, or `unknown`. Unknown requires `amountCents: null`.
- Explicit effects and evidence for `providerMinutesSaved`, `computeAndToolCentsSaved`,
  and `customerReviewMinutesSaved`. These are signed net savings: a negative value
  increases the corresponding burden instead of being discarded. Zero effects also
  require an explanation. Positive savings cannot exceed the surviving baseline burden.
- Optional `unroundedComputeSavingsMicrocentsPerJob` preserves a small measured/tariff
  effect below cent-ledger precision. One microcent is $0.00000001. The result shows
  the omitted signed residual and its maximum absolute dollar contribution over modeled
  uses. It does not manufacture a whole-cent saving or hide a small slowdown.

There is no default candidate, saving or price for unknown research/model effort.
An unknown complete-cost category blocks affirmative financing. A separately declared
priced scenario can evaluate that uncertainty without claiming an empirical cost bound.
The prior 321.8-second discovery effort is not silently free and is not measured human
active time.

## Search, construction and repayment

Under `adaptive`, the first three cost categories constitute the candidate search. They are paid once
from already generated resources. Rejected candidates remain costs even if no asset is
admitted. The gate then requires both affordability of all remaining construction
categories and positive expected repayment of the **whole** one-off amount, including
the already charged search. This is a repayment hurdle, not a second cash charge.

Forecast reuse uses only trailing eight-week accepted sales, discounted over the
remaining horizon and declared useful life. Upkeep and expected foregone contribution
during construction are deducted. The gate monetizes supported provider/tool savings;
customer effort alone is not converted into enterprise income. Actual market effects
still emerge through the existing buyer choices and competitors.

Under `completed-research-replay`, the entire completed prototype cost must fit generated
funds at the single declared checkpoint. When affordable, the replay pays every category
once and models construction/usage even if the expected benefit fails. That outcome is
an **unqualified research attempt**, not an admitted worthwhile investment. When it is
unaffordable, no partial debit, fresh capital or eventual-balance borrowing is permitted.

A prototype already constructed in research does not become costless because the model
declines it. In either policy, the unfinanced part of its priced lifecycle remains an
explicit external research contribution. It does not enter enterprise cash. The output
reports both unchanged enterprise accounting and project-inclusive profit after that
outside contribution. The sum of enterprise-funded one-offs and disclosed outside
prototype cost must equal the complete one-off cost exactly once. Unknown tariffs leave
the project-inclusive amount unidentified. These are cost-accounting scenarios, not
claims of actual payment or of operating-funded construction when none occurred.

Generated resources equal the smaller of cash after unpaid obligations and one reserve,
and collected receipts minus all accrued costs plus only explicitly seed-paid opening
historical R&D. Historical R&D remains paid and included in full-history profit.
Search, rejected work, second construction and upkeep never receive that addback.

The source may already have been constructed in the research environment. A modeled
construction schedule is a counterfactual finance test, not a claim that its real
development was paid by customers. The research action log and asset acceptance must
remain separately inspectable.

`secondInvestment` records cost categories, decision-time funds, search, construction,
availability, failure, uses, direct avoided cost and the complete-cost repayment result.
Paired enterprise-profit differences measure causal net outcomes. Original upstream
direct-repayment counters aggregate all capability expenses after extension and must not
be presented as a dedicated second-asset result.
The dedicated direct-repayment flag still measures avoided delivery cost only. The paired
financial gate additionally requires positive **project-inclusive** incremental profit,
actual modeled use, complete priced categories and earned-funded admitted construction.
It remains conditional on the external acceptance and effect evidence.

## Deliberately unsupported claims

The continuation implementation assigns no candidate effects; registered production
inputs are separate. No fresh economic outcomes have been run by this module's author.
A tested source with zero evidenced benefit produces a no-investment decision;
positive cash does not manufacture qualification. Equilibrium, actual receipts,
autonomous invention, unlimited growth and self-acceleration remain unestablished.

## Registered campaign runner

`run-campaign.mjs` reads `campaign-protocol.json`, `cost-profiles.json` and the separate
production-derived `effect-profile.json`. It never chooses costs or effects from market
outcomes. The primary plan contains13conditions, three priced cost profiles, two policies
and24fresh seeds8001-8024:1,872 paired worlds. The actual-unknown cost boundary adds
48reference worlds, for1,920 paired worlds and5,760 reported enterprise branches.

Static validation executes **zero economic outcomes**:

```sh
node run-campaign.mjs --protocol campaign-protocol.json --validate-only
```

Before economic execution, the protocol must have status
`FROZEN_BEFORE_MARKET_OUTCOMES`, a `registeredAtUTC` timestamp and the coordination
`registrationURL`. The exact public comment receipt may be retained separately to avoid
a circular hash. The campaign freeze has this shape:

```json
{
  "schema": "agi-alpha-second-investment-campaign-freeze/v1",
  "marketOutcomesInspected": false,
  "files": [
    {"path": "campaign-protocol.json", "sha256": "ACTUAL_SHA256", "bytes": 123}
  ]
}
```

Every entry must have its actual bytes/hash. Required frozen files are the protocol,
effect profile, cost profiles, runner, continuation implementation, generated core,
transformation manifest, original core and both canonical ledger modules. Paths are
relative to this `market` directory. A missing or mismatched source prevents execution.

```sh
node run-campaign.mjs --protocol campaign-protocol.json \
  --freeze campaign-freeze.json --output results/primary-01
```

The output directory must be new. The runner refuses overwrite/restart, runs only the
frozen design and enforces180seconds wall and180seconds process CPU. It retains partial
outputs and an explicit failure receipt if an invariant, budget or archive operation fails.
No automatic retry or horizon/price/seed substitution is implemented. Compression and
stream finalization are included in the scientific budget; subsequent descriptive
formatting and hashes add no scenarios.

Outputs include compressed complete paired histories, all compact per-world records,
per-world and per-condition CSVs, summaries with conditional quantiles and downside
counts, the preselected seed8001reference histories for every cost/policy combination,
and a source-bound completion receipt. Full histories preserve cash events, invoices,
bills, reserves, construction decisions and the canonical scenario ledger. Compact
records retain decision-time funding and the initial checkpoint. Unknown full costs
remain null; they are never averaged as zero.

The CSV and JSON results contain no automatically generated commercial-success claim.
The condition grid is a bounded sensitivity design, not a distribution of actual markets.
