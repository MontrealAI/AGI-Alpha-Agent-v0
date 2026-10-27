# Final conditional economics results — v2.1

The frozen exploratory quote is **$800.00 per useful accepted original-query package**. It is a scenario-selected quote, not an observed service-market price. The exploratory launch gate is **False**. Final fresh confirmation gives baseline mean 90-day operating profit **$-809.68**, with modeled operating-loss frequency **69.0%**. The robust profitable region contains **0 of 12 declared cells**. No live launch is justified by these unvalidated assumptions.

**Actual collections and actual revenue: USD 0. Actual authoring/hosted-model costs: unknown.** All amounts below are modeled USD. These simulations do not calibrate real mission success, willingness to pay, or scientific source coverage. E, U, and the identical-content ordinary library have identical operating economics by the primary attribution-null assumption.

## Fresh confirmation: 90-day campaigns

| Scenario | Origins | Willing | Contracts | Useful accepted by day 90 | Earned revenue | Operating profit | Loss frequency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low | 60.00 | 1.29 | 1.29 | 0.23 | $176.00 | $-2,377.23 | 100.0% |
| baseline | 150.00 | 23.59 | 23.59 | 9.16 | $7,115.56 | $-809.68 | 69.0% |
| high | 300.00 | 68.36 | 48.69 | 21.86 | $17,146.75 | $6,282.96 | 0.5% |

Each row averages 600 campaigns under a fresh seed. Finite horizon and open work matter: accepted deliveries by day 90 are not the assumed eventual technical-success probability. High-case capacity rejections average 19.67; open contracts at day 90 average 14.03.

The baseline mean-profit Monte Carlo interval is $-951.27 to $-668.10; its 10th–90th percentile campaign outcome is $-3,029.87 to $1,431.67. These describe simulation noise/outcomes under fixed assumptions, not empirical confidence in a business.

## Contribution reconciles to operating profit

| Scenario | Net earned revenue | Bad debt | Direct variable A cost | Contribution | Fixed cost incl. overhead | Finance | Operating profit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low | $176.00 | $4.35 | $975.94 | $-804.28 | $1,572.95 | $0.00 | $-2,377.23 |
| baseline | $7,115.56 | $106.34 | $6,245.45 | $763.78 | $1,572.95 | $0.52 | $-809.68 |
| high | $17,146.75 | $201.20 | $9,088.69 | $7,856.85 | $1,572.95 | $0.94 | $6,282.96 |

Direct variable A costs include channel acquisition, all-origin intake, failed work, domain construction/validation, bounded rework, compute, delivery/refusal, support, fees, and variable overhead. Fixed compensation and its overhead are deducted once. Refunds are revenue reversals or returned deposit liabilities, not duplicate costs. Sunk development C and optional retention B remain separate.

## Expected amount per originating opportunity

| Scenario | Contract probability | Accepted by day 90/origin | Gross cash collected | Earned revenue | All A expense | Bad debt + finance | Operating profit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low | 2.1% | 0.4% | $8.56 | $2.93 | $42.48 | $0.07 | $-39.62 |
| baseline | 15.7% | 6.1% | $77.77 | $47.44 | $52.12 | $0.71 | $-5.40 |
| high | 16.2% | 7.3% | $84.82 | $57.16 | $35.54 | $0.67 | $20.94 |

The primary cash channel assumption is $5 per origin. Non-buyers and unsupported sources still incur it, plus intake labor. Origination volumes are explicit opportunity-pool assumptions, not guaranteed demand.

## Cash, obligations, reserves and free funds at day 90

| Item | Low | Baseline | High |
| --- | --- | --- | --- |
| Gross customer cash collected | $513.87 | $11,664.80 | $25,447.20 |
| Cash refunded | $291.47 | $3,667.20 | $4,328.80 |
| Net customer cash collected | $222.40 | $7,997.60 | $21,118.40 |
| Earned modeled revenue | $176.00 | $7,115.56 | $17,146.75 |
| Cash on hand, including owner funding | $2,829.39 | $5,746.50 | $16,081.85 |
| Unaccepted/refundable deposits | $53.33 | $1,120.00 | $4,532.27 |
| Full fee reserve during refund windows | $26.93 | $1,157.60 | $2,658.93 |
| Accrued unpaid costs | $155.87 | $493.12 | $625.34 |
| Pending payment fees, subset of payables | $0.16 | $5.30 | $12.94 |
| Remaining maximum completion budget | $48.74 | $634.37 | $2,406.00 |
| Additional conditional fee buffer | $0.03 | $0.66 | $1.43 |
| Outstanding borrowing | $0.00 | $74.69 | $0.68 |
| Free funds after all listed restrictions and debt | $2,544.48 | $2,266.06 | $5,857.19 |

Pending payment fees are already in payables and are not subtracted twice. Free funds include remaining initial owner capital of $5,000; they are not profit. Full refundable deposits and fee reserves cannot finance unrestricted spending. The model accrues accepted-but-unsettled collection fees and imminent refusal-refund fees, and reserves potential additional fees.

Baseline 95th-percentile temporary borrowing requirement is $1,184.13; modeled credit-limit breach frequency is 0.0%. Borrowing is costed at an assumed 12% APR. The first confirmation campaign's unselected full cash ledger is preserved; all campaign cash identities are checked.

## Outside-option and acquisition stress cases

| Case | Cash acquisition/origin | Contracts | Earned revenue | Operating profit | Loss frequency |
| --- | --- | --- | --- | --- | --- |
| warm_inbound_acquisition_zero | $0.00 | 23.59 | $7,115.56 | $-59.35 | 53.2% |
| baseline | $5.00 | 23.59 | $7,115.56 | $-809.68 | 69.0% |
| acquisition_15_per_origin | $15.00 | 23.59 | $7,115.56 | $-2,311.91 | 90.5% |
| acquisition_50_per_origin | $50.00 | 23.59 | $7,115.56 | $-7,604.05 | 100.0% |
| competent_human_fast | $5.00 | 0.00 | $0.00 | $-2,839.44 | 100.0% |
| no_buyer_advantage | $5.00 | 0.00 | $0.00 | $-2,838.40 | 100.0% |

The competent-human-fast case uses 10 median additional analysis minutes and preserves the source burden. The no-buyer-advantage case supplies the buyer with an equivalent free answer. These are distinct from E=U: a zero E-versus-U gain does not itself imply zero outsourcing demand.

## Preserved price exploration

| Success fee | Expected contracts | Expected accepted deliveries | Mean operating profit | Modeled loss frequency |
| --- | --- | --- | --- | --- |
| $150.00 | 61.52 | 20.47 | $-8,931.19 | 100.0% |
| $250.00 | 61.27 | 20.43 | $-7,065.12 | 100.0% |
| $350.00 | 60.48 | 20.07 | $-5,271.12 | 100.0% |
| $450.00 | 58.17 | 19.32 | $-3,627.49 | 99.0% |
| $600.00 | 49.47 | 17.15 | $-1,577.93 | 83.0% |
| $800.00 | 23.41 | 9.18 | $-852.22 | 67.0% |
| $1,000.00 | 9.45 | 3.71 | $-1,513.64 | 85.0% |

The seven quotes were compared on 200 baseline campaigns with a common exploration seed. The best quote was frozen before the untouched confirmation seed was used. The launch gate rejects a negative best mean; the quote remains available solely for the conditional comparison. No confirmation outcome changed the price.

## Robust profitable region

| Source construction + validation hours | Outside extra minutes | Worst-corner mean profit | Worst lower MC mean bound | Robust in declared grid? |
| --- | --- | --- | --- | --- |
| 0.50 | 30.00 | $-2,849.52 | $-2,869.73 | False |
| 0.50 | 90.00 | $-2,167.06 | $-2,394.97 | False |
| 0.50 | 180.00 | $-1,614.79 | $-1,927.29 | False |
| 1.00 | 30.00 | $-3,113.77 | $-3,348.86 | False |
| 1.00 | 90.00 | $-2,785.11 | $-3,044.53 | False |
| 1.00 | 180.00 | $-2,627.17 | $-2,942.86 | False |
| 2.00 | 30.00 | $-6,225.37 | $-6,626.17 | False |
| 2.00 | 90.00 | $-6,243.29 | $-6,721.01 | False |
| 2.00 | 180.00 | $-6,145.71 | $-6,609.91 | False |
| 4.00 | 30.00 | $-10,256.36 | $-10,671.73 | False |
| 4.00 | 90.00 | $-10,256.11 | $-10,671.51 | False |
| 4.00 | 180.00 | $-10,256.11 | $-10,671.51 | False |

Every cell includes baseline, lower source admissibility/decisiveness, higher refunds/defaults, lower outcome value, and a combined adverse corner at the frozen quote. Every corner is retained. An empty region means the stated grid supplies no robust-profit claim; widening or repricing it after confirmation would be a new exploratory study.

## Buyer break-even avoided minutes

The buyer comparison retains q_H for the human alternative and separately reduces q_offer for the provider's budget-exhaustion risk. At median complexity, the required extra human minutes depend on source burden and outcome value through `(q_H − q_offer) × value`. These are participation thresholds, not measured savings, and supplier profit must independently pass.

| Source hours | Outcome value | q_offer | q_H | Extra human minutes needed | Minimum outcome value vs doing nothing |
| --- | --- | --- | --- | --- | --- |
| 0.50 | $900.00 | 0.4603 | 0.4845 | 153.60 | $854.43 |
| 0.50 | $1,500.00 | 0.4603 | 0.4845 | 160.86 | $854.43 |
| 1.05 | $900.00 | 0.4603 | 0.4845 | 125.20 | $854.43 |
| 1.05 | $1,500.00 | 0.4603 | 0.4845 | 132.47 | $854.43 |
| 2.00 | $900.00 | 0.4603 | 0.4845 | 76.16 | $854.43 |
| 2.00 | $1,500.00 | 0.4603 | 0.4845 | 83.43 | $854.43 |
| 4.00 | $900.00 | 0.4603 | 0.4845 | 0.00 | $854.43 |
| 4.00 | $1,500.00 | 0.4603 | 0.4845 | 0.00 | $854.43 |

The table assumes zero queue wait and a 10-day quoted turnaround; the campaign uses each actual quoted wait plus turnaround. Higher source effort can make outsourcing attractive while simultaneously destroying supplier profitability.

## Optional retention B: unknown gain can reject it

| Assumed fresh uses | Avoidable minutes/use | Modeled net B | Break-even minutes/use | Reject? |
| --- | --- | --- | --- | --- |
| 10 | 0 | $-205.00 | 10.41 | True |
| 10 | 5 | $-106.52 | 10.41 | True |
| 10 | 15 | $90.43 | 10.41 | False |
| 50 | 0 | $-225.00 | 2.28 | True |
| 50 | 5 | $267.38 | 2.28 | False |
| 50 | 15 | $1,252.15 | 2.28 | False |
| 200 | 0 | $-300.00 | 0.76 | True |
| 200 | 5 | $1,669.54 | 0.76 | False |
| 200 | 15 | $5,608.62 | 0.76 | False |

No avoidable minutes were measured. At zero gain every retention option loses money. Identical-content ordinary-library parity is zero incremental gain before special packaging costs; the assumed generic reuse benefit does not establish a special memory mechanism. B is not added to primary campaign profit.

## Human-led development and sunk C

| Scope | Assumed hours | Gross wage cost | Employer compensation | Internal cost incl. assumed overhead |
| --- | --- | --- | --- | --- |
| finite_demonstrator_low | 30 | $1,965.06 | $2,868.99 | $3,442.79 |
| finite_demonstrator_central | 80 | $5,241.38 | $7,652.41 | $9,182.90 |
| finite_demonstrator_high | 180 | $11,742.90 | $17,144.63 | $20,573.56 |
| source_verified_deployment_low | 250 | $15,888.70 | $23,197.50 | $27,837.00 |
| source_verified_deployment_central | 700 | $44,719.60 | $65,290.62 | $78,348.74 |
| source_verified_deployment_high | 1600 | $101,785.00 | $148,606.10 | $178,327.32 |

The 30/80/180-hour finite demonstrator covers small exact code, an independent oracle, tests and documentation. It does not certify historical sources. The 250/700/1,600-hour deployment includes source-family and admissibility work, representative archives and operational validation. These are scoped planning assumptions, not timed human results or vendor quotes. Existing methods may reduce the work. Neither comparator is used as customer value or price.

| Sunk C | Low first-campaign profit | Baseline first-campaign profit | High first-campaign profit |
| --- | --- | --- | --- |
| $0.00 | $-2,377.23 | $-809.68 | $6,282.96 |
| $5,000.00 | $-7,377.23 | $-5,809.68 | $1,282.96 |
| $15,000.00 | $-17,377.23 | $-15,809.68 | $-8,717.04 |
| $50,000.00 | $-52,377.23 | $-50,809.68 | $-43,717.04 |
| $100,000.00 | $-102,377.23 | $-100,809.68 | $-93,717.04 |

## Corrections and evidence boundary

1. The initial scheduling look-ahead defect was corrected before the first confirmation; full old code, policy and outcomes remain in `results_superseded_scheduling_v1/`.
2. V1 confirmation completed, but its zero-event formatter failed. Raw results and the reporting-only completion are preserved in `versions/v1_before_acquisition/`.
3. Independent audit identified missing acquisition cash, quoted queue finance, pending fees and bounded rework. V1's +$466.82 baseline was incomplete and was not relabeled as a full-cost result. V2 used new seeds.
4. Before v2 confirmation, independent audit corrected the provider-specific budget failure being applied to the human comparator. That paired exploratory result is preserved in `versions/v2_before_outside_option_correction/`; final v2.1 confirmation remained untouched until its freeze.

The retained failures and adverse scenarios limit the conclusion. This is a transparent cost-and-participation construction for a conditional service; it establishes neither a market nor a causal expert/agent improvement. A source-verified pilot, measured customer alternative, channel cost, and actual paid acceptance would be required to replace the assumptions.

