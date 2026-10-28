# Publication economic review

Review observation: 28 October 2026, approximately 01:55–01:58 UTC.  
Reviewer role: repository/economic reviewer, separate from the publication author but within the same AI-assisted session and shared workspace. This is not external peer review or independent validation of assumptions.

## Verdict

**The publication's numerical economic claims reconcile with the frozen scenario results. Three precision corrections are requested before final rendering.** None changes the central decision: retain the supporting engineering artifact, reject this formulation as the transformational flagship, and hold commercial admission. Buyer demand, complete actual study cost, actual profit and an incremental AI advantage remain unestablished.

The reviewer independently read the frozen inputs, result ledger, financing record and arithmetic audit; reconstructed the stated unit-cost, break-even and cash identities; and checked scenario rows, shared-provider equivalence and scale/retention outputs directly. No frozen file was changed. The four frozen source hashes still match their pre-execution manifest.

### Exact publication versions reviewed

| File | SHA-256 at review start |
|---|---|
| `publication/PAPER.md` | `87b908aee42a1c8cef74aa993c4a17076126471882b8db356af37844ed3942ee` |
| `publication/EXECUTIVE_BRIEF.md` | `f52f0a8e52c7bee85ba8683983cc5f3abbae352ff481337140f95d1151c85732` |

Any subsequent correction creates a new publication version. This review does not silently transfer to changed prose or regenerated figures.

## Requested precision corrections

### R1 — State the scope of the recurring-order break-even

**Location:** PAPER §8.1, sentence giving USD729.59 as the later clean-delivery break-even.

The value is arithmetically correct for one clean, fully collected order after shared preparation, with one USD75 acquisition charge, USD540 execution cost and USD100 support. It excludes the separately charged **USD120 cohort-continuation coordination cost**. That charge is present in the finite policy model, but omitting the qualification beside this standalone threshold can make the threshold look sufficient for an expansion decision.

Suggested replacement:

> After shared preparation, a later clean, fully collected order has a USD729.59 break-even before allocation of the separate USD120 cohort-continuation charge. The continuation decision uses the complete cohort ledger.

The clean first-order USD139 loss and corrected first-order USD294 loss are also conditional on **both payments being collected and one prospect acquisition**. Add that qualification to the PAPER paragraph and BRIEF cash paragraph. These are single-path arithmetic examples; the scenario results separately include refusal, failure and balance default.

### R2 — Distinguish exact break-even from positive return

**Location:** PAPER §12, retention paragraph.

The phrase “break-even requires more than 0.9375 incremental hours” is imprecise. The frozen retention arithmetic is:

`750 / (10 × 0.8 × 100) = 0.9375 hours per usable fresh reuse.`

Exactly 0.9375 breaks even; more gives positive modeled net benefit. Suggested replacement:

> Break-even requires 0.9375 incremental hours saved per usable fresh reuse; a positive modeled return requires more.

No observed reuse saving supports either threshold being reached. The rejection decision remains correct.

### R3 — Do not let “no expenditure” imply zero actual model cost

**Locations:** PAPER abstract/decision paragraph and BRIEF final decision paragraph.

The frozen actual account explicitly sets complete study cost, human cost, model cost and profit to unknown. The paper also correctly says hosted model billing was not surfaced. “No expenditure was performed” is broader than the evidence and may be read as a zero-cost statement.

Suggested replacement, if it matches the execution record:

> No customer outreach, new spending commitment, payment transaction, machine operation or live authentication was performed. Actual model and full study costs remain unknown.

This is a wording correction, not a claim that a charge was observed.

## Additional clarity improvements

1. **BRIEF proposed terms:** “USD1,200 upon final acceptance” plus “payment thirty days after acceptance” is best stated as “USD1,200 earned on final acceptance; 50% restricted refundable deposit beforehand, with the remaining balance due thirty days after acceptance.” This separates revenue recognition from payment timing.
2. **PAPER payment-processing row:** “2% applied to modeled collections” should explicitly include gross payment receipts that may later be refunded. The model retains the deposit processor fee on failure; refunds do not erase that cost.
3. **Evidence scope:** Retain the existing statements that common-state probabilities and demand distributions are uncalibrated, that the conventional/proposed shared tie is imposed by matched assumptions, and that the arithmetic audit is a same-session reconstruction. No economic result here is an observed commercial outcome.
4. **Conditional completeness:** The publication appropriately makes insurance/licensing/responsibility and customer-specific obligations unresolved commercial-admission blockers. Do not shorten “complete only within stated finite obligations” to an unconditional full-cost or profitable-business claim.

## Numerical reconciliation

All values below come directly from `economics/results-r1/results.json`, not from publication summaries. USD values are rounded for display. Base fee is USD1,200, modeled initial unrestricted owner capital is USD2,000.

| Scenario, proposed shared | First-only expected profit | Selective expected profit | Selective loss probability | Selective after illustrative historical build |
|---|---:|---:|---:|---:|
| Public-source zero-value control | −75.00 | −75.00 | 100.00% | −2,475.00 |
| Adverse | −110.17 | −110.17 | 100.00% | −2,510.17 |
| Central | −275.11 | −252.59 | 86.76% | −2,652.59 |
| Favorable | −235.64 | +146.98 | 37.75% | −2,253.02 |

The public-source control incurs USD75 acquisition cost and no purchase; that is an explicit modeled control, not an observed refusal. Every first-only policy loses under the base scenarios. Stopping has zero incremental cost and profit. The separate USD2,400 historical-build charge is illustrative, counted once, and not measured actual study cost.

Provider account checks:

| Shared selective account | Central | Favorable |
|---|---:|---:|
| Accepted revenue | 763.148445 | 2,374.172520 |
| Collected accepted fees | 744.069734 | 2,362.301658 |
| Cost | 996.661678 | 2,215.317532 |
| Bad-debt expense | 19.078711 | 11.870863 |
| Profit = revenue − cost − bad debt | −252.591944 | +146.984126 |
| Customer net benefit, a separate account | 390.960290 | 3,051.048503 |

The conventional shared and proposed shared providers have exactly equal expected ledgers in all twelve matched scenario/policy cells. This equality follows from giving them the same asset, information, method and events. It does not establish empirical equivalence of model operation. The separate-preparation base-price policy never chooses expansion.

The maximum value in the frozen price/capital sensitivity grid is **USD769.475069**, favorable scenario, USD1,500 fee and USD2,000 capital. It is a finite assumed-grid result, not an optimized or buyer-validated price. Higher supplied capital does not, by itself, establish a higher profit under the frozen policy.

### Unit arithmetic and cash

- Execution cost: `50 + 250 + 150 + 50 + 20 + 20 = 540`.
- Clean first fully collected delivery: `75 + 600 + 540 + 100 + 24 = 1,339`, profit `1,200 − 1,339 = −139`.
- Corrected first fully collected delivery: `1,339 + 155 = 1,494`, profit `−294`.
- Clean first break-even: `(75 + 600 + 540 + 100) / 0.98 = 1,341.83673469`.
- Corrected first break-even: `(75 + 600 + 540 + 100 + 155) / 0.98 = 1,500`.
- Later clean break-even before continuation coordination: `(75 + 540 + 100) / 0.98 = 729.591836735`.
- First-order initial unrestricted capital: `75 + 600 + 540 + 155 + 12 + 10 + 150 = 1,542`.

The last identity protects the maximum scoped failed-order obligation, including the retained deposit fee and refund administration, plus the minimum cash reserve. The restricted refundable deposit does not finance it. No capital availability is established. The frozen financing record gives conditional 90-day interest of USD45.626301 at 12% and USD91.252603 at 24%; neither rate is a financing quote.

### Information, scale and retention

The maximum additional information fee is USD23.750405 in the central scenario and USD52.078303 in the favorable scenario, zero in the adverse/public-source controls. These comparisons hold the ready asset and sufficient capital constant and concern the remaining two prospects. Delivery cost stays in the policy comparison; it is not charged again as fictional research.

The scale arithmetic is also correct:

- Target: USD1 billion cumulative **net customer benefit** over ten years.
- Assumed net benefit per accepted outcome: USD250.
- Required accepted outcomes: 4,000,000.
- Establishment anchor: 17,163; not an eligibility/demand estimate.
- Sum of annual adoption fractions: `229/200 = 1.145`.
- Required accepted jobs per active shop-year: `4,000,000 / (17,163 × 1.145) = 203.545404746`.
- At twenty accepted jobs per active shop-year: `17,163 × 1.145 × 20 × 250 = USD98,258,175`.
- Four million outcomes at USD1,200 would multiply to USD4.8 billion gross fees, conditional only; obtainable revenue, scaled profit and valuation are not estimated.

The additional retention charge is USD750: USD600 extraction/validation plus three months at USD50. Its modeled incremental benefit over the same ordinary library is zero, so incremental net value is −USD750 and the optional investment is rejected. Gym training and live ENS authentication are not run.

## Evidence identities and boundaries

The economic freeze is `PP-ECO-20261027-R1`, recorded before results at `2026-10-28T01:42:30.002924+00:00`.

| File | SHA-256 |
|---|---|
| `economics/inputs.json` | `f679b8d59dd5848d5ee97dc5cd48965a8d9b7e62e9502894c93bb91a1bd69b53` |
| `economics/PROTOCOL.md` | `8e29a0a7c874900c975cf7613866ccbcfcb74a6668f75cfb0ad265ec28f1afb9` |
| `economics/model.py` | `a16e69353d8dad0e0d6891e0e6d6b7db563039798771b0757c16af602228ac51` |
| `economics/audit.py` | `04b0e2c9a3380219d26889d0040e00b75ed65440be6becfc5449e41868ff97ef` |
| `economics/freeze.json` | `7f4e72e4ea503d7eeba119f1ca507730a0487686da95624bbc722ff05fce6899` |
| `economics/results-r1/results.json` | `2c618a8f660a19837ca705671a0f541b7614dbb1a3e913a2bd90dc4aee13b7fb` |
| `economics/results-r1/financing.json` | `25cdebfaad0f90d4b9b05a973c5640080baca23f32d9af8758cb908bc8d30483` |
| `economics/results-r1/independent_audit.json` | `936cd38f99855df00962ad34764a7acefc7fd2f5cd8716dff19690b63cd6f606` |

The archived arithmetic audit reports PASS on 7,122 finite weighted histories, 143,017 arithmetic/scope assertions and twelve shared comparisons. The reviewer checked 36 main cells and 48 sensitivity cells exist and independently reconciled the publication's selected claims. This review is not a rerun of every history, a fresh demand study, a cost quote or an industrial qualification.

## Repository and publication-owner refresh

Read-only GitHub connector queries were made during this review. No GitHub mutation was performed by this reviewer.

| Metadata | Observed value |
|---|---|
| Main ref | `3947e4ec8fd74ad40e13e8ff825a149fa98a10e9` |
| Main root tree | `1eae5408a1b41d326f04b512de14203825398530` |
| Main parents | `def7cdfcbf927169a78b6c956406023330ade093`; `e6c9265ad1d2c86ebee665166f46ffdd10636ee8` |
| Main commit date | `2026-10-27T22:07:10Z` |
| Main message | Merge pull request #4994, paper-readers 1.46.1 |
| Integration/publication PR | [#4988](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4988), open, unmerged |
| PR head branch | `codex/opportunity-frontier-20261027` |
| PR head | `dae93bd3ed5fc8978e83d8d53f98594e0e9125a0` |
| PR head tree | `094bb98fac5f0000d3549dd754bd24ae4db4f379` |
| PR base | `main` at `3947e4ec8fd74ad40e13e8ff825a149fa98a10e9` |
| GitHub mergeable field | `true`; not an approval or qualification result |
| GitHub test merge SHA | `60d244c2d930d8f94b5d5e70ddce3bc8a99fe6d6`; not a merge/release |
| PR updated at | `2026-10-28T01:28:50Z` |
| Coordination issue | [#4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850), open, 706 comments |
| Issue updated at | `2026-10-28T01:47:36Z` |

**No material publisher-owner change was found.** The [latest owner update](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6458145461) preserves the existing single 1.47 publisher, reports current checks and pending exact-head review, and explicitly claims no 1.47 release/canary success. Its held-test incident remains unqualified. The [study reservation](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6458290271) reserves only this additive study subtree and leaves main/catalog/runtime/publisher and protected pins untouched.

The authorised present route remains an additive draft study and pinned review/download availability. Canonical integration, catalog/homepage changes, production release and serving remain with the existing owner and applicable mixed code/data/HTML qualification gates.

Exact read-only REST sources:

- https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0/git/ref/heads/main
- https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0/git/commits/3947e4ec8fd74ad40e13e8ff825a149fa98a10e9
- https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0/git/commits/dae93bd3ed5fc8978e83d8d53f98594e0e9125a0
- https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0/pulls/4988
- https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0/issues/4850
- https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0/issues/4850/comments?per_page=100&page=8

