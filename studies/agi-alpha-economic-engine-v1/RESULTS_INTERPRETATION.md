# Results interpretation: cash, reinvestment and source-specific settlement

**Status: audited simulation, not observed business operation.** The [frozen protocol](PROTOCOL.md) was publicly fixed at [commit 76ba784](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/76ba78492da893b235b071cb0a61cf3608f9db37) before execution. The 144 primary cash paths, 32 predeclared demand sensitivities, 27 token-realization rows and nine failure examples now have [independent arithmetic review](evaluation/INDEPENDENT_AUDIT.json): 1,288,965 comparisons, zero remaining discrepancies. Those checks are repeated equation, field and ledger comparisons, not independent experiments or acceptance trials. This report only describes existing audited rows; it adds no scenario, parameter or new performance result.

The [cash results](outputs/run-002/results.json), [token results](outputs/token-run-002/token_waterfalls.json), [scorecard](SCORECARD.json) and [CSV ledgers](outputs/run-002/results_summary.csv) expose every case. The preserved first run and [reporting revision](REPORTING_REVISION.json) show that the revision changed reporting boundaries without changing financial paths.

## 1. Provider viability is separate from customer savings

Each row below quotes USD20 per expected accepted output with zero reinvestment. Revenue is modeled collections after refunds but **before** payment processing; complete expense includes processing, setup, delivery, support, maintenance and any incurred construction. Income then subtracts the model's retained tax reserve; it is not audited company profit. Showing revenue before processing avoids subtracting processing twice. Expected accepted counts may be fractional.

| Profile / scenario | Status | Requests served / expected accepted | Revenue after refunds (USD) | Complete expense (USD) | Income after tax reserve (USD) |
|---|---|---:|---:|---:|---:|
| Evidence pack / base | 12 operating months | 1,000 / 950 | 16,903.79 | 19,533.80 | -2,630.00 |
| Evidence pack / conservative | stopped month 6 | 125 / 106.25 | 1,816.88 | 26,069.85 | -24,252.97 |
| Evidence pack / stress | startup refused | 0 / 0 | 0.00 | 0.00 | 0.00 |
| USD0.50 hypothesis / base | 12 operating months | 12,000 / 11,400 | 202,771.80 | 29,742.60 | 121,120.44 |
| USD0.50 hypothesis / conservative | 12 operating months | 1,200 / 1,020 | 15,988.50 | 38,411.65 | -22,423.15 |
| USD0.50 hypothesis / stress | startup refused | 0 / 0 | 0.00 | 0.00 | 0.00 |

These six rows have distinct assumptions and are not six observed services. The evidence pack remains a bounded brief assembled from four preselected exact passages; its measured native execution component does not establish end-to-end source discovery, synthesis, cost or field reliability. The USD0.50 variable-cost / USD200 traditional-replacement profile is a separate, unvalidated offering hypothesis. Its positive base result follows from those strong assumptions; the conservative and stress results remain visible.

The model begins with **USD25,000 of provider cash**. Customer wages, review and fallback costs sit in a separate customer account. This is not the earlier operating amendment's USD25,000 combined resource budget: it permits collections to finance later service and does not charge customer labor against provider cash. The horizons also differ. Here twelve operating months follow setup of 48, 164 or 520 modeled workdays in the base, conservative and stress arrangements. Stress startup requires USD32,323.08, exceeds cash, and is refused; the zero incurred expense in that row records refusal, not a free deployable service. Setup scheduling, demand, field quality and prices are unvalidated.

## 2. Complete-demand customer comparison and duration sensitivity

For the base evidence pack at USD20, all 1,000 requests are admitted but only 950 are expected to meet the assumed standard; the complete-demand comparison therefore buys 50 full traditional fallbacks plus handoff and readiness. A pure Agent cost per accepted output does not establish completion of every requested job. The following durations change the traditional assumption while holding the Agent scenario fixed; they do not demonstrate increasingly difficult work at unchanged Agent cost.

| Assumed productive human minutes | Traditional total (USD) | Agent plus complete fallback (USD) | Customer savings (USD) | Maximum beneficial Agent face price (USD) |
|---:|---:|---:|---:|---:|
| 5 | 13,434.27 | 31,517.29 | -18,083.02 | 0.97 |
| 15 | 19,427.60 | 31,816.95 | -12,389.35 | 6.96 |
| 30 | 28,417.60 | 32,266.45 | -3,848.85 | 15.95 |
| 60 | 46,397.60 | 33,165.45 | 13,232.15 | 33.93 |
| 120 | 82,357.60 | 34,963.45 | 47,394.15 | 69.89 |

The base evidence-pack zero-reinvestment provider break-even is USD23.21 per accepted-output invoice, with collection loss and lag included, under the fixed-cohort algebra. At a 30-minute human assumption the customer's maximum beneficial face price is USD15.95, so those conditional bounds do not overlap. At 60 minutes they do overlap, USD23.21–33.93, but neither the 60-minute duration nor demand at the changed price was measured. Longer assumptions cannot convert the four-passage fixture into empirical evidence of a USD200 human job. The separate USD0.50 hypothesis assumes that USD200 all-in comparator and leaves human duration and fallback staffing unknown.

Across the **72 primary parameter rows per profile**, results below use full annual-demand fallback. Startup-refused rows remain in the case count but have no Agent service and zero modeled customer saving; empty served-only cohorts are separately null. Both outcome worlds and allocation settings can produce identical paths, so these counts are neither frequencies of independent outcomes nor probabilities of commercial success.

| Profile / human assumption | Customer saving positive | Negative | Zero | No Agent service | Positive customer saving and positive provider income |
|---|---:|---:|---:|---:|---:|
| Evidence pack / 5 min | 0 | 48 | 24 | 24 | 0 |
| Evidence pack / 15 min | 0 | 48 | 24 | 24 | 0 |
| Evidence pack / 30 min | 8 | 40 | 24 | 24 | 0 |
| Evidence pack / 60 min | 32 | 16 | 24 | 24 | 0 |
| Evidence pack / 120 min | 48 | 0 | 24 | 24 | 8 |
| USD0.50 / USD200 all-in, duration unknown | 48 | 0 | 24 | 24 | 24 |

Provider income after the modeled tax reserve is positive in 8 of 72 evidence-pack rows and 24 of 72 hypothesis rows. Each profile has 24 startup-refused rows, excluded from positive/negative operating-income counts. The scorecard separately reports primary and sensitivity distributions, ranges, medians, scope, resource infeasibility and unknown staffing. No duration assumptions or task profiles are pooled into an overall customer-win percentage.

## 3. Allocation authority does not imply useful expenditure

**All 144 primary paths make zero candidate constructions and zero executor purchases.** At base hypothesis demand, the first candidate has a positive remaining-horizon forecast of USD48.02 in month 1 but no earned earmark. By month 2 the 50% policy has USD3,297.77 earmarked, yet the shortened-horizon forecast is negative USD1.80. The frozen policy stops rather than treating accumulated funds as proof of a good investment. The next eligible candidate never satisfies funding and the remaining-horizon payback test at the same decision time; stopping that candidate ends the frozen construction sequence.

The table shows the USD20 hypothesis profile. Allocation is the cumulative amount earmarked from recovered after-tax operating surplus; spending is actual modeled construction outlay. Idle earmarks remain cash restrictions. All amounts are simulated, and 50% is one tested policy, not a contract requirement or privileged result.

| Demand / outcome world | Allocation policy | Lifetime earmark (USD) | Construction/capacity spent (USD) | Idle earmark (USD) | Income after tax reserve (USD) |
|---|---:|---:|---:|---:|---:|
| 1× / no gain | 0% | 0.00 | 0.00 | 0.00 | 121,120.44 |
| 1× / no gain | 25% | 30,280.11 | 0.00 | 30,280.11 | 121,120.44 |
| 1× / no gain | 50% | 60,560.22 | 0.00 | 60,560.22 | 121,120.44 |
| 1× / no gain | 75% | 90,840.33 | 0.00 | 90,840.33 | 121,120.44 |
| 4× / no gain | 0% | 0.00 | 0.00 | 0.00 | 478,796.17 |
| 4× / no gain | 25% | 119,699.04 | 1,250.00 | 118,449.04 | 477,546.17 |
| 4× / no gain | 50% | 239,398.08 | 1,250.00 | 238,148.08 | 477,546.17 |
| 4× / no gain | 75% | 359,097.13 | 1,250.00 | 357,847.13 | 477,546.17 |
| 4× / assumed gain | 0% | 0.00 | 0.00 | 0.00 | 478,796.17 |
| 4× / assumed gain | 25% | 120,257.33 | 1,250.00 | 119,007.33 | 479,779.31 |
| 4× / assumed gain | 50% | 240,514.65 | 1,250.00 | 239,264.65 | 479,779.31 |
| 4× / assumed gain | 75% | 360,771.98 | 1,250.00 | 359,521.98 | 479,779.31 |

The 1× assumed-gain world has the same path because nothing is constructed. At 4× demand, every positive allocation policy funds the same USD1,250 of construction; larger percentages mostly immobilize more cash in idle earmarks. No case buys an executor. All 4× hypothesis policies serve 44,640 requests with 42,408 expected acceptances, leaving 3,360 unserved and 2,232 unresolved admitted requests. The annual-demand comparison charges 5,592 full fallbacks; their worker duration is unknown. Increasing retained-method efficiency does not increase accepted output in these cases because the unchanged customer-attention pool binds at 3,720 requests per month.

## 4. The positive transfer is conditional, and failed search is charged

The 4×, 50% policy provides the representative event history. Month 2 spends USD500 on candidate 1; month 3 rejects it in both simulated worlds and spends USD750 on candidate 2. Month 4 either rejects candidate 2 (no-gain world) or promotes its frozen assumed gain. In that gain world the promoted method is subsequently applied 33,480 times, saves USD3,325.20 gross, incurs USD135 of upkeep and returns USD2,440.20 after its own construction and upkeep. Charging the earlier failed candidate reduces the combined before-tax gain to USD1,940.20 relative to zero investment. The no-gain world loses the full USD1,250 construction cost. These are model arithmetic, not observed inventions.

Candidate 2's probability-weighted construction forecast required 17,822 subsequent request uses to cover construction and horizon upkeep; once a positive outcome is assumed, its realized-horizon algebra requires 8,911 uses. Those are different questions. Candidate 3 is stopped with negative remaining-horizon forecasts in both worlds (USD−1,087.15 without prior gain; USD−1,170.92 after it). The gain world reduces nonlabor variable cost to 75% and provider-time cost to 92% of baseline, but leaves quality, customer effort, fixed costs and executor occupancy unchanged. A single assumed promotion and diminishing returns do not establish acceleration of capability discovery.

## 5. Source-specific token proceeds stay outside the USD business loop

The following success settlement flows use the frozen chosen configurations and a USD20 quoted job amount. AGIALPHA valuation is an illustrative USD0.00002 per token, not an observed market quote. Exact atomic transfers, integer floors, collateral and failure branches remain in the [source formula register](contracts/ROUTE_FORMULAS.md) and [token results](outputs/token-run-002/token_waterfalls.json).

| Source route | Customer escrow at illustrative quote (USD) | Worker award before conversion and enterprise costs (USD-equivalent) | Base 100-settlement cash after gas (USD) |
|---|---:|---:|---:|
| manager_usdc | 20.00 | 10.400001 | 1,012.92 |
| ascension_agialpha | 20.00 | 18.810000 | 1,827.88 |
| jobs_v0_agialpha_success_only | 21.00 | 17.820000 | 1,730.36 |

Manager's chosen 30% and 10% wallet allocations plus 8% validator pool leave approximately 52% for the worker, with validator division dust returned to it ([settlement source](https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/contracts/utils/JobSettlement.sol#L111-L133)). Ascension deducts a 5% validator pool and burns 1% of each payout, giving a 94.05% worker net at these amounts ([market source](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/contracts/ascension/AscensionJobMarket.sol#L183-L249)). The Jobs-v0 chosen configuration adds a 5% customer fee to a USD20-equivalent reward, then a 10% validator allocation and 1% worker burn; the worker receives USD17.82-equivalent from USD21-equivalent total customer escrow ([registry source](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/JobRegistryBase.sol#L2040-L2136), [stake source](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/StakeManagerBase.sol#L2327-L2484)). The fee-pool burn and eligible Platform stake claims form a separate distribution ([FeePool source](https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/FeePool.sol#L239-L365)). Wallet receipts are not automatically the worker enterprise's income.

At the same USD20 quote, all three conservative realization cases hit the USD1,000 monthly liquidity ceiling and retain USD800 after the assumed USD200 gas cost. In all stress realization cases liquidity is zero, the entire award remains unconverted inventory, and USD1,000 of gas requires outside cash. Collateral locks and imputed capital costs are separately charged; returned bonds are not revenue. Even base cash after gas is before delivery, review, setup, support, overhead, tax and reserves, so it is not reinvestable profit. The model executes no contracts, verifies no current deployment state and creates no bridge from these assets into the ordinary-USD simulation. Jobs-v0 failed-route numerical economics remain NOT MODELED; historical deployment reports remain attestations. No universal tokenholder dividend, automatic buyback, automatic treasury appropriation or 50% reinvestment right is inferred.

## 6. Commercial interpretation and limits

The evidence supports a concrete conditional decision: price, complete delivery cost, customer effort, failed delivery, collections and remaining useful demand must jointly justify investment. Cash generation can be large under an inexpensive high-value offering hypothesis, yet does not guarantee a worthwhile candidate or broader productive capacity. The demonstrated brief's modeled economics are less favorable and remain dependent on hypothetical human duration. The next empirical step is to measure full service cost and field acceptance for a clearly priced useful offering, then test a frozen candidate's transfer on fresh work; these simulations do not replace that evidence.

Historical authoring cost, material downstream liability, real provider contracts, actual customer revenue and observed improvement remain unknown. They are not zero. High-consequence applications, live custody, daily staffing, stochastic budget protection, token quotas and market liquidity are outside this validated arithmetic boundary. The completed operational and capability editions remain independent of this financial amendment.

## Exact evidence identities

- Cash results SHA256: `e194f26361e69549b0e29181f2716e4229c63122eecc9b7c72307b4f48dc44eb`.
- Token results SHA256: `aca12d6d1194f37967fda6fb2e831739b05571df1fd4a095f018c5f16f7f134a`.
- Independent audit SHA256: `07afc7155b7d07fcd63b1ce37b9553df49b79704716fe1bef7686199c73598d7`.
- Scorecard SHA256: `fbad5628fead2283b87d5010ea88bfa884331ace8faafddbbe3b70b9b449d7fb`.
- Reproduce this descriptive extraction with `python reinvestment_amendment_v1/src/summarize_results.py`; it reads the audited outputs and never calls the scenario evaluator.
