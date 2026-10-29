# Primary complete-economics result: overhead through wind-down

This is a **post-confirmation accounting correction replay**, not a new untouched confirmation. The original frozen source, configuration, selected price, 768 histories, ledgers and summaries remain intact one directory above. The primary complete-cost figures below supersede the original financial headline; they do not replace or conceal it.

## Identified omission and mechanical correction

Independent review found that the original campaign loop ran 33 weeks (26 selling weeks plus seven weeks of runoff) but charged business overhead for only the 26 selling weeks. The corrected source reserves and charges all **33 weeks × USD120 = USD3,960** from the start. The seven-week closure window is deliberately conservative; the modeled last service obligations ordinarily settle before its end. This is an added USD840 committed cost per campaign.

It would be incorrect merely to subtract USD840 from old profit. Reserving this obligation reduces cash available for acquisition and intake before receipts arrive. Therefore all cash-prefix checks, admission decisions, settlements and optional investment decisions were rerun. Selected price **USD3,500**, opening seed **USD10,000**, operating buffer **USD1,000**, all commercial assumptions and original confirmation seeds remain unchanged. There is no new price selection or parameter tuning.

The replay uses the same seeds with the corrected policy. Conditional event generation can consume random draws differently when liquidity alters accepted bookings, so it is not a matched exogenous-event causal experiment. It is an explicitly disclosed known-seed accounting replay.

## Corrected primary results

All monetary values below are **USD conditional simulation results**. Actual collections remain zero; actual complete cost and profit remain unknown.

| 26 selling weeks plus 7 closure weeks | Conservative | Central | Favorable |
|---|---:|---:|---:|
| Histories | 256 | 256 | 256 |
| Mean bookings | 0 | 7.48828 | 35.64063 |
| Mean accepted reports | 0 | 6.89063 | 34.54688 |
| Mean full-balance collections | 0 | 6.67188 | 34.01172 |
| Mean contribution before fixed/startup | −2,640.00 | 9,322.08 | 83,639.14 |
| Mean operating profit before startup | −6,600.00 | 5,362.08 | 79,679.14 |
| **Mean full-project profit** | **−9,000.00** | **2,962.08** | **77,279.14** |
| Median full-project profit | −9,000.00 | 3,545.00 | 80,997.00 |
| Fifth percentile profit | −9,000.00 | −9,000.00 | 33,610.50 |
| 95th percentile profit | −9,000.00 | 19,530.00 | 96,775.00 |
| Minimum profit | −9,000.00 | −9,000.00 | −8,971.50 |
| Maximum profit | −9,000.00 | 28,410.00 | 104,900.00 |
| Fraction profitable | 0% | **59.375%** | **98.828125%** |
| Mean terminal cash | 1,000.00 | 12,962.08 | 87,279.14 |
| Mean available funds after operating reserve | 0 | 11,962.08 | 86,279.14 |
| Mean positive surplus above protected seed and reserves | 0 | 5,512.31 | 76,395.99 |

Central mean profit falls from USD6,477.28 to **USD2,962.08**, exceeding the direct USD840 correction because tighter cash admission also reduces booked work. Its profitable share falls from75% to59.375%. Favorable mean falls fromUSD78,884.91 toUSD77,279.14, with three losing histories now retained. Conservative scenarios still earn no fees and reach theUSD9,000 modeled capital-risk limit; more overhead is offset by earlier acquisition stops.

These results support only a **conditional mean-positive service scenario with material loss risk**. They do not support a robust launch across the assumed demand range, actual profits, commercial Alpha or inevitable self-financing expansion.

## Corrected financing and stage decisions

The complete reserve policy's sufficient opening-cash thresholds for commercial setup, all33weeks of overhead, one qualified lead, a complete first job and the operating buffer are:

| First-job admission threshold | No common shock | Common shock |
|---|---:|---:|
| Conservative | USD9,845 | USD10,410 |
| Central | USD8,945 | USD9,295 |
| Favorable | USD8,445 | USD8,675 |

The conservative shock requirement exceeds the unchangedUSD10,000 seed. The actual policy can refuse a job it cannot finance; it does not manufacture the additionalUSD410. The conservative scenario's reservation ceiling also produces zero bookings at the inherited selected price. These are policy-specific thresholds, not globally minimal funding for every smaller possible offering.

All768 admitted campaign paths preserve nonnegative available funds. Zero-seed runs refuse before spending. Every deposit, receivable, payable, completion obligation and support reserve clears by closure. Capital loss remains bounded byUSD9,000 within the declared expense model becauseUSD1,000 remains reserved. This is a provider financial-model bound, not a bound on physical plant risk or unmodeled legal liabilities.

Every optional digital module remains **STOP**. Central histories evaluate7,762 option decisions:1,542 are affordable and none has positive expected incremental benefit. Favorable histories evaluate11,498:9,167 are affordable and six have positive expected benefit, but none has both properties. No module cost or hypothesized saving is charged to the final paths because no investment is selected. The ordinary-library comparator remains identical for the same asset.

The customer's future field-experiment EVSI remains unchanged: illustrative grossEUR30,620.96 and netEUR22,348.23. It is still separate from the desk pack's delivered evidence and provider receipts. Provider surplus does not finance theEUR180,000 plant.

## Switching-cost ambiguity: an analytical sensitivity

The original booking rule compares price with the assumed reservation amount and separately checks price plusUSD300 switching cost against theUSD5,200 human-service alternative. It is coherent if the reservation amount is a **net acceptable fee after switching effort**. If it instead denotes **gross total value before switching**,USD300 should also reduce the fee that buyer will accept.

`economics_switching_sensitivity.py` independently recomputes both interpretations using Decimal, without changing the selected price or corrected main replay. Results are analytical expected-load figures, not another stochastic validation.

| Selected USD3,500 offer | Net-fee-cap interpretation | Gross-value interpretation |
|---|---:|---:|
| Central no-shock booking probability | 15.2174% | 10.6522% |
| Central no-shock full33-week planning profit | USD10,795.01 | USD3,776.51 |
| Central common-shock booking probability | 9.8913% | 6.9239% |
| Central common-shock full33-week planning profit | USD−3,312.59 | USD−6,098.81 |
| Favorable no-shock booking probability | 41.6667% | 36.6667% |
| Favorable no-shock full33-week planning profit | USD98,441.97 | USD85,116.93 |

Both conservative interpretations produce zero booking probability. Actual buyer reservation values and switching burden have not been elicited, so neither interpretation is empirically established.

The corrected central no-shock analytical break-even booking rate is **8.19573%** of qualified leads. Under the common shock it is **13.41929%**, above the assumed9.89130% net-fee-cap uptake. These thresholds include the fullUSD6,240 planned acquisition spend,USD2,400 startup andUSD3,960 overhead. They do not eliminate stochastic timing, capacity or financing risk, which the actual replay retains.

## Verification, unchanged boundaries and reproduction

Corrected source: `src/economics_complete.py`.
Corrected input: `inputs/economics_complete.json`.
Primary outputs: this `results/complete/` directory.

- Eight development accounting/zero-seed checks pass under the corrected cost boundary.
- Ruff format and lint pass before the correction freeze.
- Corrected source SHA-256: `836861cacca9954379a8cf6437530f37966373da62b9842f7d22fc93d4aed8a5`.
- Corrected configuration SHA-256: `beddaabb1128fbede98db1fc4c8187227b1f3bb1319b72fac7778512cd1dbffa`.
- Inherited selected-policy SHA-256 remains `857da37114749837e4c086939e14885ad8f90034a27faae561a0dfde135b7c1e`.
- Correction freeze:2026-10-27T23:39:03.314647+00:00. Its stage explicitly states post-confirmation correction and known-population replay.
- Separate Decimal audit imports no producer code and independently checks185,135cash-ledger rows plus768final reconciliations. All1,113,882scalar checks pass. This is implementation separation under one controller, not institutional review or that many independent efficacy trials.
- Original frozen source/config/policy hashes still match; preservation receipt is `economics_original_freeze_preservation.json`.
- The six static typing findings of the original source are not claimed fixed; no extra type-test campaign was run.

From the study root:

    python src/economics_complete.py selfcheck
    python src/economics_complete.py confirm
    python results/complete/economics_audit.py
    python results/complete/economics_switching_sensitivity.py

Do not invoke development or regenerate the original price-policy/freeze records. Confirmation is the command's inherited name; the corrected run is a known-population replay, not a fresh holdout. The source and input digests are checked before it executes.
