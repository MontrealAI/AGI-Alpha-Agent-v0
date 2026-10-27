# Independent economics audit

**Scope:** read-only review of `economics/runner.py`, `config.json`, and `README.md`, with arithmetic recomputation from an existing saved ledger. The auditor did not run stochastic campaigns, change economic inputs, select prices, or edit the economic implementation. This audit concerns a hypothetical archival-query service; it does not establish live demand, revenue, source admissibility, or novel capability.

**Verdict:** the audited v2.1 source addresses the material defects found in this review. Its five frozen-input hashes match the actual files. The retained exploration selects USD 800 as the least-loss quote among seven tested prices, with mean modeled operating profit **−USD 852.22** and the **launch gate false**. Every tested exploratory price loses money under the baseline assumptions. This audit does not substitute for the author's fresh confirmation, and it does not certify commercial readiness.

## Findings and their preserved corrections

1. **Partial-confirmation reporting failure.** V1 never created the `contracts` counter in a zero-demand campaign. The `no_buyer_advantage` row consequently omitted it, and `confirm()` raised `KeyError` while producing per-origin results, after some files had been written. V2.1 initializes the structural counters explicitly. Original source, policy, partial results, failure record, and a separate reporting completion are retained under `economics/versions/v1_before_acquisition/`.

2. **Unpriced acquisition channel.** V1 had intake labor but no separately priced acquisition channel. Its baseline mean of USD 466.82 over 150 origins could absorb only another USD 3.11 per origin, before demand feedback. That incomplete positive result is superseded. V2.1 charges USD 5 per origin once in A, without a labor-overhead multiplier; USD 0, 15, and 50 are explicit sensitivities. Channel cost and exposure volume remain assumptions.

3. **Buyer deposit timing.** V1 charged liquidity only for nominal production duration although bookings could wait up to 21 days. V2.1 uses the currently offered queue plus promised turnaround in participation, before outcome draws are consulted. Dated receipts/refunds remain in the cash ledger. This is a quoted-duration financing assumption, not an exact estimate of every buyer's realized capital cost.

4. **Small outstanding payment obligations.** V1 released the completion reserve before pending balance/refund fees were accrued. V2.1 accrues expected balance fees at acceptance, adjusts them at settlement, and accrues definite refusal-refund fees at refusal. Pending expected fees are a disclosed subset of payables, not a second deduction. A separate conditional cash buffer covers the excess up to the maximum balance collection fee and a possible accepted-refund transfer fee.

5. **Bounded correction and recovery.** V2.1 reserves at most one extra labor/tool round, charges it on an assumed 20% of jobs, and models an assumed 5% budget-exhaustion event as refusal/refund with no fee. Incurred failed work stays in A. This closes the unspecified unlimited-retry interpretation. These probabilities and effort allowances still require empirical calibration; the exact-solver pass rate supplies none.

6. **Provider-specific failure transferred to the human comparator.** The initial v2 change multiplied both offer and human success probabilities by provider budget survival. The outside human estimate had no matching hard cap. This would silently weaken the comparator. The intermediate exploration is preserved under `economics/versions/v2_before_outside_option_correction/`. V2.1 correctly uses `q_offer = 0.95 × q_H`, retains the shared source/decisiveness/acceptance factors, and includes `(q_H − q_offer) × outcome value` in buyer break-even conditions. Its confirmation seed was not consumed by either earlier exploratory revision.

## Accounting and controls that passed the read-only review

- Deposits are liabilities until acceptance/refund; owner cash and borrowing are financing. Failure refunds return liabilities rather than creating a second operating expense. Accepted refunds are contra-revenue. Pending balances are receivables, and bad-debt/refund adjustments avoid charging the same refunded balance twice.
- Role labor receives the compensation factor and assumed shared overhead once. Failed source cases still incur source construction, independent validation, tools, and refusal costs. Promised support is accrued at acceptance even when paid after the horizon.
- For unfinished signed jobs, remaining completion budget equals maximum assigned budget less already incurred job expenses. Accrued unpaid costs are reserved separately, avoiding duplication of the incurred part. New-job reserves start only after the order date.
- The scheduling correction reserves each job's full promised slot. It no longer releases a slot using a source-refusal outcome not yet observed. This is a conservative finite-capacity model, not a detailed employee calendar.
- The retained **v1** first confirmation ledger independently reconciles expense, payment, gross receipt, and refund totals to its saved summary. It has 90 daily records and no pre-arrival starts. Its cash-identity residual is approximately USD 3.64 × 10^-12. This is a check of an existing record, not a new campaign or validation of v2.1 numerical outputs.
- E, U, and an identical-content ordinary library use explicitly identical economic assumptions. Their zero differences are a declared attribution null, not a measured causal estimate. Conditional service profit would not establish Operational Alpha or retained Alpha.
- The price is selected from a finite exploratory grid, with inputs and exploratory output bound by a frozen-policy hash. Fresh confirmation cannot select a different quote. Losing worlds and price candidates are retained. The temporary-credit-limit breach is reported rather than hidden.

## Reporting and evidence boundaries

V2.1 reports contribution as net earned revenue less bad debt and direct variable A costs. Fixed campaign compensation and its separately identified overhead, then financing cost, reconcile contribution to operating profit. Collected cash, restricted deposits, refund reserves, payables, completion obligations, borrowing, and free funds are separate. Free funds include unspent owner financing and are not earned profit.

Sunk development and exploratory failures remain separately labeled C, with actual authoring expenditure unknown. The existing human-development ranges are scoped planning estimates, not market quotes or evidence of customer willingness to pay. Demand, source effort, and mission success remain unmeasured scenario inputs. Monte Carlo intervals measure sampling noise conditional on those inputs.

## Reproduction layout

The agreed repository layout is `studies/agi-alpha-archive-claims-v1/study/...`, retaining the literal `study/` folder in the ZIP as well. Under that layout, the runner's script-relative `HERE.parents[1]` plus configured `study/...` input paths resolve correctly from any working directory. Flattening the study contents into the outer directory would break those paths. Frozen outputs intentionally cannot be overwritten; reproduction must preserve the original records and use a fresh output copy.

## Final reviewed source identity

- Revision: `archival-claim-rescue-economics-v2.1`.
- `runner.py`: `7b8c84b50f8a84da6cabe49d9e3adfce19f6c3ec54eab29b716b28fdc7d8a5a0`.
- `config.json`: `14b985e852308e12b15cdb6ac6694b3ff77fe21c9672e7e3a6342a887af0ced2`.
- Exploratory output: `870b8a569a592f8870ec59c639bf465476c577520454fa953380b59ccac33aba`.
- The source/configuration, technical protocol, model manifest, and exploration hashes all match `policy_frozen.json`.
- Frozen quote: USD 800; launch recommendation: false; fresh confirmation seed: 271029987.

No additional stochastic confirmation, optional formatting gate, or economic-file mutation was performed by the auditor. A changed source/configuration requires renewed freeze checks and a clearly versioned evidence record.
