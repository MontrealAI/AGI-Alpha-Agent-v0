# Independent audit of the preserved market results

**PASS: no arithmetic, census, source-identity or qualification discrepancy found.** The audit reads the original completed simulation artifacts. It does not execute the market model, resample demand, run a solver or produce a replacement cohort.

## Frozen source and outcome census

All **17 frozen economic source/input files** match before and after the audit. The market freeze is `e7ab97589a8bc99671888d599c3fc4d44ae916d5809c56e6fc967b29e42446ee`; its calibration, protocol and completion-receipt bindings match. Every one of the 144 calibration execution receipts matches the preserved numerical primary outcome, including its complete timing and acceptance.

The complete compressed output contains exactly **2,304 paired simulated worlds**, **9,216 primary simulated enterprise histories**, and **46 additional same-world finance-control histories**. Every predeclared condition, cost schedule and seed is present exactly once. Complete worlds match the compact output; all paired CSV values and all 144 cell summaries reconcile, including distributions, loss/zero counts and financing counts. The preselected representative also exactly matches its original complete world.

Completion is within the prospective 900-second envelope: **68.412901 CPU seconds** and **61.995436 elapsed seconds**. The numerical primary job envelope remains the separate 60-second limit.

## Cash, obligations and complete costs

The audit reconciles every cash event against its invoice or paid bill, every weekly cash/obligation/receivable balance, and both the canonical accrual and cash projections. No uncollected invoice creates cash. All accepted simulated work has exactly one invoice; rejected work creates none. All cash stays nonnegative, and there are no unpaid obligations at the inspected balance points.

At each capability-construction decision, available resources are recomputed from **already collected cash, all accrued costs, obligations and one reserve**, using the specified seed-paid opening-history adjustment. Construction preserves both current obligations and the reserve. The code never turns original seed capital alone into operating-generated resources.

**The reserve is an investment-eligibility reserve, not an inviolable cash floor.** Subsequent ordinary operating overhead can consume it. The lowest preserved cash balance is **6,298 cents ($62.98)**, below the 20,000-cent ($200) investment reserve. This is consistent with the frozen implementation; a statement that every ending balance stays above $200 would be false.

All three completed prototype costs remain in each primary history's full project accounting, whether or not the enterprise adopts them. Shared construction is charged once per asset. An independent recipient pays a complete reconstruction charge at most once per retained method and family. Per-job acquisition, execution, verification and declared residual-attention costs match their bills. Fractional compute is carried before rounding, and unrounded project comparisons reconcile.

Asset payback includes every modeled shared use, failed acquisition, stale failure and upkeep charge. Both recorded failed shared deliveries debit their full incurred cost. Internal contributor reward allocations add zero consolidated enterprise value.

## Exact later-investment qualification

The registered control qualifies only the complete **G2+G3 later-investment bundle**. It requires every completed later prototype cost to be funded from operating-generated resources, positive actual use, nonnegative aggregate direct value after complete costs and upkeep, no failed construction, and favorable incremental full project profit against the same-world control in both rounded and unrounded accounting.

| Preserved outcome | Registry B | Graph C |
|---|---:|---:|
| Worlds with a later capability investment | 23 | 23 |
| Complete qualifying later-investment bundles | **0/2,304** | **0/2,304** |
| Full finance-control histories retained | 23 | 23 |

All 46 later-investment histories construct **G2 only**. Every one fails full bundle financing, has negative bundle direct value, and has nonpositive incremental full project value. No individual generation qualification is established by this bundle control. No positive Level 5 claim is supported by these results.

## Downside outcomes remain visible

| Full project outcome count, out of 2,304 worlds | A | B | C | D |
|---|---:|---:|---:|---:|
| Loss worlds | 2,102 | 2,105 | 2,105 | 2,121 |
| Worlds with no accepted jobs | 1,319 | 1,319 | 1,319 | 1,319 |
| Insolvent worlds | 0 | 0 | 0 | 0 |

The 2,304 primary histories from zero-demand cells are retained, with zero invoices, zero collections and full project losses. The archived representative is fixed prospectively, not selected for a favorable result. These counts describe the specified sensitivity panel and must not be presented as empirical market probabilities.

## Claims boundary and reproduction

Actual customer collections remain **zero**, actual complete historical cost remains **unknown**, and the canonical observed ledgers do not acquire simulated revenue. Larger populations, demand, prices, resource tariffs, residual attention and competitor behavior remain scenario assumptions. The completed research prototypes predate their modeled financing; the simulation does not rewrite their actual funding history. It does not establish unsupported mathematical capability, global skill uniqueness, field reliability or actual commercial succession.

`market-reconciliation.json` contains 13,072,953 elementary reconciliation checks, an empty discrepancy list, all later-bundle diagnostics and the precise artifact hashes. This count measures accounting checks, not independent experiments or new empirical observations. The audit took 48.610717 elapsed seconds. `market-representative-check.json` records the separate exact representative comparison. Reproduce the read-only reconciliation with:

```sh
python audit-final/reconcile_market.py
```

All audit artifacts are outside the frozen implementation. The original source, complete worlds, ledger records and outcome files remain unchanged.
