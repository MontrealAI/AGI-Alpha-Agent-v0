# Productive Capital Engine — executable economics

This companion is an accounting and resource-allocation model over the separately measured local production study. **Every customer price, order, collection, refund, business cost, surplus and investment here is simulated.** Full authenticated live Agent cost remains `null`. No money or token moved.

## Reproduce without replacing recorded results

From the study directory, run:

```bash
python3 economics/run_economics.py --output /tmp/productive-capital-economics-replay
```

Python 3 and its standard library are sufficient. The command checks the frozen economic configuration hash and the measurement bridge's bound source-summary hash. It writes a separate set of 52 scenario-policy runs, 312 cycle rows, 936 family rows and the transaction-event ledger. No API, wallet, paid model call or live executor is required.

The seven primary generated outputs are listed in `outputs/manifest.json`. Supplemental figures/tables do not change the primary freeze. `run_addendum.py` regenerates the post-result sensitivity replay at the recorded output location; `paper_summary.py` regenerates the numeric paper tables, chart CSVs and authorship-allocation sensitivity. These two authoring commands replace their own generated files, so use a copy of the study when preserving the delivered package unchanged.

## What each file means

| File | Purpose |
|---|---|
| `../protocol/economics_config.json` | Frozen numerical assumptions, rates, demand, costs, routes, policies and stress cases |
| `../protocol/economics_protocol.md` | Prospective financial question, conservation rules, comparator and scope |
| `../protocol/economics_freeze.json` | Original configuration hash and timestamp |
| `../protocol/economics_bridge_freeze.json` | Original measured bridge, source summary and first engine hash |
| `../protocol/economics_amendment_1.json` | Known human-time accounting and next-plan feasibility corrections |
| `../protocol/economics_amendment_2.json` | State-aware next-plan capacity/maintenance and output-manifest scope correction |
| `outputs/summary.json` | Compact base result, all scenario-policy outcomes and claim boundaries |
| `outputs/ledger.json` / `.csv` | Per-cycle cash, receivables, collateral, obligations, reserves and resource use |
| `outputs/events.jsonl` | Raw simulated transactions and all five account deltas |
| `outputs/family_results.json` / `.csv` | Counts, full modeled costs and human-time thresholds by deliverable class |
| `outputs/paper_numbers.json` | Paper-ready scorecard, selected results and commensurability limitation |
| `outputs/chart_cycle_cash.csv` | Per-cycle plotting data; cash and class counts remain separate |
| `outputs/chart_policy_outputs.csv` | Policy comparisons by service class |
| `outputs/addendum.json` | Post-result remediation, full-attention-budget and tool-cost replays |
| `outputs/authorship_allocation.json` | Post-result extra authorship/model-bill cost allocations; no demand replay |
| `history/initial_economics_v1.zip` | Preserved original implementation and outputs before corrections |

The shared CPU measurement is divided once among the three outputs of a joint project. This is an allocation convention. The empirical experiment creates three related deliverables on six project instances, while the financial model separately prices services and assumes independent operational failures and repeated demand. It does not establish measured marginal cost for each service or three independently validated customer markets.

## Main modeled findings

The direct-sale base, under $2,000 initial capital and the frozen budgets, accepts 122 release-assurance outputs, 121 rollout plans and 119 bilingual dossiers over six cycles. Allocated modeled costs per accepted output are $28.26, $35.16 and $32.93. These include the stipulated supervision, verification, unsuccessful construction, setup, failed attempts, support and business costs. They are not measured live Agent costs.

At the assumed prices $90, $75 and $55, after remaining customer review, the traditional-work break-even times are 59.78, 78.66 and 57.09 minutes. At an assumed one-hour traditional workflow, release assurance is approximately at break-even, the plan costs the customer $19.00 more, and the dossier saves $3.01. At two hours, all three modeled offers save money. Neither one hour nor two hours is a measured traditional task duration.

Closing base cash is $12,970.11, of which $2,000 began as external capital. Uncollected receivables of $3,202.71 are not spendable. Available modeled operating surplus after loss recovery and the obligation reserve is $8,776.09. The stipulated fresh-child-plus-20-orders-per-class next plan needs $3,564.83, giving 2.46 times cash coverage, but that plan exceeds the unchanged $2,000 service spending ceiling. It is therefore not an executable plan under those resource limits. A smaller target of 12 orders per class needs $2,396.55 including construction and fits the resource ceilings; its cash coverage is 3.66 times. Two attempts per order do not guarantee acceptance.

All four base reinvestment fractions leave the measured child on HOLD. Compared with ordinary conventional caching, its changed-cycle average CPU effect is negative, and both methods support the same bounded scope. The output field `npv_usd` denotes **undiscounted finite-life net benefit at a zero discount rate**. No discounting or speculative token appreciation rescues this result. The discovery pilot also remains on HOLD because productive benefit is unmeasured.

In the separate provider-limited scenario, an assumed execution-capacity purchase increases modeled output. The 50% policy buys one discrete capacity block and produces 101/98/97 class outputs, versus 72/71/68 with 0%. This is an ordinary capacity-scaling scenario based on an assumed vendor offer. It is not observed capability improvement or self-acceleration.

The compelled-research case explicitly spends on the real child despite its negative compute return. At 50%, it ends with lower cash than the base and class outputs 123/119/118; this mixed vector is not evidence of general improvement. The price-compression, high-supervision, Manager-default and adverse-token cases generate no available reinvestment surplus. Currency routes must retain their different beneficiary shares; Manager's worker enterprise cannot count the other 40% wallets as its revenue.

## Unknown-cost sensitivity and timing

The post-result remediation replay charges extra engineering and review before the first modeled customer delivery. With 16 extra engineer hours and four review hours, the unchanged $2,000 seed cannot launch production: all service outputs are zero, cash is exhausted and obligations remain. Actual remediation effort was not measured; the hours are a sensitivity case.

The separate authorship allocation applies additional one-time effort and model/tool bills beyond the frozen estimates over the modeled accepted output count. For example, 40 extra engineering hours, ten review hours and a $250 unmetered bill add $4,606.92. Allocated per-output costs become $40.99/$47.88/$45.66. This is a cost-allocation calculation with unchanged demand. It must not be used to claim that the same business can fund that cost before earning revenue. The early-cash replay and end-period allocation answer different questions.

The unknown values remain unknown, not zero. Zero in a sensitivity grid identifies the frozen reference scenario. Independent arithmetic checks can establish internal consistency of the assumptions and ledgers; they cannot establish external demand, customer acceptance, production permission or the correctness of the assumptions.
