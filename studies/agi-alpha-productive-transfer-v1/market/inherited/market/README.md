# Game-theoretic economics companion

`MODEL.md` specifies the repeated procurement game, explicit information, price responses, cash restrictions and interpretation. `protocol/parameter-manifest.json` distinguishes measured narrow production quantities, external price/wage anchors, design choices and unidentified assumptions. Source and scenario hashes are frozen before primary market outcomes.

Requires Node.js 24.22.1 (used locally), with no external package install, API key, account or financial transaction. The browser-compatible market core and unchanged canonical accounting modules also power the bilingual demonstration. This is a local research simulation, not an operational runtime or live protocol ledger.

```sh
node tests/test_market.mjs
node src/run.mjs --output results/reproduction-01
```

Run from this directory. Output directories must be new. The runner verifies every frozen input before executing the complete predeclared scenario set with the fixed 24 seeds. `complete-runs.jsonl.gz` contains concatenated standard gzip members, one complete matched A/B/C world per JSON line after decompression. Standard Python `gzip.open` reads all members; no failed world is omitted. `outcomes.jsonl`, `summary.json`, `configurations.json` and `completion.json` provide compact review paths. Monetary amounts are integer USD cents; probabilities, time parameters and value assumptions are explicit. All observed customer-collection fields stay zero.

The primary full-history grid pays the declared original research cost at opening, then considers cash-funded adoption after useful work. The prospective adoption-only grid excludes sunk research and cannot demonstrate historical repayment. A separate retrospective-allocation sensitivity is not evidence that original R&D could have been funded when incurred. Adoption requires finite engineering time and pauses delivery. There is no tested second capability in this study; the next-investment policy therefore retains reserves.

The same actual retained and conventional producers receive equal economic treatment. B/C parity is deliberate and required by the source evidence. Internally verified component tests do not estimate real customer acceptance or market reliability. Confidence intervals are conditional simulation intervals, not empirical evidence of a profitable market.

The final canonical projection uses the existing shadow-ledger API with simulated receipts in its **assumed** scenario field. Its observed collected category remains zero. Dynamic invoice, expense, cash and buyer events are inspectable market state, without payment authority. Original invoices and refunds remain distinct; unpaid obligations are deducted once in the liquidity view and never charged twice in the accrual view.

For an exploratory one-world run, import `pairedSimulation` from `src/market.mjs`; changing assumptions yields an exploratory scenario, never a replacement primary result. Unknown costs must not be passed as null: the simulator refuses them instead of interpreting them as zero. Supply explicitly assumed finite values and preserve the actual unknown in the evidence record.

## Three preserved campaigns

The study has one primary campaign and two explicitly subsequent diagnostic stages. They use the same frozen core (`52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27`). The later stages do not replace the primary result. There are no further campaigns in this study.

| Stage | Configurations | Seeds per configuration | Paired worlds | Enterprise histories | Complete output |
|---|---:|---:|---:|---:|---|
| Primary | 87 | 24 | 2,088 | 6,264 | `results/primary-01/` |
| Postprimary exploration | 206 | 12 | 2,472 | 7,416 | `exploratory/results-01/` |
| Post-exploratory pricing diagnostic | 160 | 12 reused exploratory seeds | 1,920 | 5,760 | `policy-diagnostic/results-01/` |

All 19,440 enterprise histories are preserved, including failures, refusals and null cases. Reproduce the two later stages in fresh output directories:

```sh
node exploratory/run.mjs --output exploratory/reproduction-01
node policy-diagnostic/run.mjs --output policy-diagnostic/reproduction-01
```

The final diagnostic compares all five already-declared **target prices with a cost floor**, USD5/10/20/40/80. Actual quotes equal the larger of the target and current unit cost plus USD1. This distinction matters: before adoption the USD5 and USD10 targets both quote USD14.33 under the stated ten-minute effort assumption. Computed weekly quotes, quotes actually offered to simulated buyers, and accepted simulated invoice prices have separate fields.

The primary campaign produced no adoption and no profitable enterprises. Exploration found six B adoptions, all seed-funded, and no positive-mean enterprise configuration. Its recorded histories exposed a finite-horizon pricing weakness: the optimistic margin-weighted heuristic repeatedly selected USD80 despite no conversions and lower-price sales. The final diagnostic addresses that specific policy risk using reused seeds. It is not independent confirmation, an equilibrium calculation or an achieved optimal policy.

In the final diagnostic, B adopted in 398 of 1,920 worlds, all seed-funded; 199 used full-history accounting and 199 adoption-only accounting. There were no operating-surplus-funded adoptions. Four of 160 configurations had positive mean B enterprise profit, all with adoption-only accounting, seed funding, zero integration cost, arrival probability 0.5, and targets USD10 or USD20. No full-history configuration had positive mean profit or positive mean B-minus-A. B and C were exact numeric ties throughout all three campaigns. These scenario-grid counts are not population adoption probabilities.

`policy-diagnostic/results-01/summary.csv` contains all 160 configuration results. `predeclared-price-slice.csv` contains all prices for the pre-outcome-selected publication slice, including its USD10-integration counterpart. `predeclared-representative-histories.json` contains all four funding/accounting regimes at the preselected target USD20 and seed2001. `investment-events.csv` lists all B/C adoption events. `analyze.py` produces these arithmetic-only derivatives from the preserved outcomes; it does not run a simulation.

The preselected logit, zero-integration, arrival-0.5, USD20 prospective seed-funded condition yielded mean B profit USD183.28 and mean B-minus-A USD184.967. Its fixed-path one-off capital ceiling is USD217.657 after accounting for noncapital effects, compared with the scenario's total historical-plus-adoption charge of USD394.21. This is an arithmetic ceiling holding the realized policy path fixed, not a nonlinear capital-cost experiment or cash available to invest. The corresponding full-history mean B profit is negative USD178.24. The same condition under earned-surplus funding does not adopt. No second tested capability is available to finance.

Public freezes precede each stage's outcomes in issue4850: primary comment6421724738, exploratory comment6421879271, and final policy-diagnostic comment6422222209. Resource receipts report executable child CPU and wall time while retaining total monetary, authoring/inference and active human costs as unknown. Independent audits in the sibling `review/` directory cover every complete history, investment funding event and canonical reconciliation.
