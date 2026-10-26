# Prior market audit and source-intake transfer adapter

## Audit result

The original strategic-market core is retained byte-identically at SHA-256
`52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27`.
The canonical shadow ledger and automated cost modules are unchanged.

A fresh arithmetic auditor inspected every primary, exploratory and fixed-price diagnostic history.
It passed cash conservation, unique billing, outstanding obligations, reserves, finite buyer budgets,
acceptance-before-invoicing, exact financed source identity and preservation of seed/operating distinctions.
The audit is a separate implementation by another agent in the same project and host. It is not independent
institutional replication, additional customer work, or demand validation.

| Preserved campaign | Enterprise histories | B/C adoption events combined | Earned-funded adoption events |
| --- | ---: | ---: | ---: |
| Original primary | 6,264 | 0 | 0 |
| Postprimary exploratory | 7,416 | 12 | 0 |
| Later fixed-price policy diagnostic | 5,760 | 796 | 0 |

The last campaign contains 398 B adoptions and 398 identical C adoptions, all funded from initial capital.
There are 62 B worlds with both positive enterprise profit and positive B-minus-A value, confined to the
adoption-only, seed-funded regime. This excludes historical research costs. It cannot establish that
operating proceeds financed the original construction or another capability. The original primary remains negative.

Nine pre-existing arm worlds were also replayed against the unchanged source; all summary fields matched.
The 14 original simulator tests passed. The transfer extension has 16 additional behavioral tests, including
15 original-vs-adapted history comparisons. These counts are software checks, not empirical trials.

## What actually blocked investment

The reference model posts prices that lose to human, free DIY and competing AI alternatives; it makes no sales.
A incurs USD 154 in modeled setup and overhead; B/C additionally incur USD 361.52 in assumed historical costs.
The empirical pricing heuristic overweights the margin of unbought high prices, so the original null cannot be
attributed only to insufficient customer value. The preserved fixed-price diagnostic substantially changes sales
and permits some capital-funded adoption. It does not produce any earned-funded construction.

Further constraints are genuine within the model: buyer review/integration/trust costs, finite demand,
competitor price response, payment delay, reserves, engineering downtime and the full cost of adoption.
Several inputs are weakly identified, particularly human minutes, task value, integration cost, field reliability,
recurring procurement intensity and complete model/authoring charges. The model is behavioral; no equilibrium,
optimality, convergence, global nonviability or real-market success is established.

## Why a separate adapter is required

The original model hardcodes the earlier component-finalization producer and models a reduction in assumed
provider finalization minutes. A new source-intake compiler is a different asset and workflow stage.
Reusing the old identity or treating improved extraction coverage as human-time savings would misbind the study.

`market-transfer-core.mjs` is a separately named, versioned derivative. `market-transfer-core.patch` exposes every
change; `derive_transfer_core.py` refuses an unexpected original hash. The derivative supports a new exact-source
asset, active-vs-incumbent process resource inputs and a full-cost prospective reconstruction charged at the
investment decision. It retains the original buyer, competition, cash, refund, reserve and canonical ledger logic.
The original source and all original results remain intact.

Prospective reconstruction is a counterfactual exercise: the simulated enterprise can fund a copy of the exact
tested asset from collected funds only if both expected repayment and current affordability permit it. These
collections did not finance the actual research session. No second asset is invented.

## Production interface

`inspectProduction` expects `agi-alpha-intake-transfer-production/v1` with:

- `missions`: distinct registered source-intake mission IDs, never assertion counts or duplicate representations.
- `evidenceSHA256`: immutable production closure identity.
- `arms.A/B/C`: attempted and accepted mission IDs, complete recurring and construction costs (explicit `null` when
  unknown), process CPU/wall per accepted output and scope (`complete-workflow` or `known-process-lower-bound`).
- `arms.B/C.asset`: exact tested source path, asset ID and SHA-256.
- `completeAcceptanceEvidence`: `status: PASS`, `scope: complete-useful-deliverable`,
  `independentlyVerified: true`, exact `receiptSHA256` and `verifierSHA256`. A matching call inventory,
  scoped status vector or incomplete package does not satisfy this gate.

Every registered mission must have a complete useful deliverable independently accepted for all arms before
comparison. A favorable common subset cannot silently replace the full registered set. Scoped outcomes outside
complete acceptance remain recorded; they do not become automatic market-quality or demand premiums. Stage-only process timings
cannot give an arm increased full-workflow capacity. A missing baseline intake is an equivalence/effort gate,
not proof that the incumbent cannot complete the job.

`identificationDecision` returns `IDENTIFICATION_HOLD` if complete money is unknown. It does not convert unknown
model calls, authoring or operator attention into zero. `conditionalPair` separately accepts fully explicit cost
scenarios. Nominal per-attempt cost includes routine verification; the retained failure multiplier separately
charges failed-work corrections, preventing duplicate amortization. No elapsed model time becomes a wage bill.

All customer-quality, trust, effort, integration, supported-frequency and price-related assumptions stay common.
The primary class requires zero asserted labor savings. Exploratory effort assumptions are labeled explicitly
and must be supported by an executed difference before interpreted as a possible mechanism. Customer review
does not fall merely because a capability is retained. Prices and competitors still respond within the original model.

## Run checks

```bash
node market/inherited/market/tests/test_market.mjs
node market/test_transfer_adapter.mjs
```

The original audit and replay scripts refer to the preserved local prior-study tree. Their receipts and source
hashes are portable; a fresh full prior audit requires the original outcome archives identified in the receipts.
The adapter/core and tests themselves are self-contained and need no network, model account or credentials.

## Economic evidence boundary

Official BLS wages provide rate anchors; they do not identify competent task durations or contractor invoices.
The same-day official source recheck confirms May 2025 medians of USD 135,980/year for software developers and
USD 104,300/year for QA analysts/testers. Assuming 2,080 hours gives USD 65.375 and USD 50.144 per hour. This is an
arithmetic wage conversion, not an estimate of AGI ALPHA delivery labor. Break-even human duration should be
reported when actual comparable duration is unknown.

GitHub Dependabot and Mend Renovate demonstrate strong available alternatives. Dependabot raises automated
version-update PRs for all GitHub repositories; Renovate Community Cloud has a free tier for unlimited public
and private repositories, with finite resources. Neither zero license price nor internal software acceptance
means zero operator work or proof of commercial demand for this new offering.

## Prospectively registered market campaign

`transfer-protocol.json` and `transfer-scenarios.json` declare 166 cells before new market outcomes:
24 no-benefit controls (12 stresses with each buyer rule), 120 conditional model-stage/cost cells and 22
prespecified conditional stress cells. Eight new paired seeds, 3001–3008, are specified. The fixed posted-price
target is USD 20; the original current-cost-plus-USD-1 floor remains active. USD 5 and USD 10 targets are stresses,
so the target must not be confused with the actual offered price.

The conditional grid gives A and B the same unknown model/curator-stage charge: USD 0, 0.25, 1, 5 or 15.
All share an assumed USD 5 nonmodel nominal cost. C has no runtime model-stage charge only if executed evidence
shows no runtime model stage and independently verifies equivalent completion of every registered mission.
The full construction envelopes are USD 25, 100 and 500 for B/C; these include discovery, authoring, all failed
candidates, evaluation, correction, integration and uncertain shared-cost allocation. These are counterfactual
scenarios, not measured bills, estimates or established upper bounds. No presumed human-minute saving is used.

The scenario design remains unexecuted until the production bridge and complete source/input freeze exist.
An incomplete C comparison must remain a failed gate. A separately registered stronger conventional C2 may
provide a distinct bridge after full fresh acceptance; it cannot erase primary C's refusals or quietly narrow
the registered task scope. `audit-transfer-histories.py` independently reconciles every admitted output history.

The primary source-intake campaign currently fails this economic-entry gate. The root's independent acceptance
handoff reports complete inventories but no complete useful package: C leaves all 15 caller observations unresolved;
A/B each have six scoped preservation observations, one conflict and eight unresolved observations. These are
caller-level observations, not 15 customer jobs or independent missions. This result remains unqualified and cannot
be converted into market acceptance. A separate prospectively registered C2 and common complete packager may be
tested on fresh tasks; only a distinct complete-acceptance bridge could admit the unchanged 166-cell market design.
