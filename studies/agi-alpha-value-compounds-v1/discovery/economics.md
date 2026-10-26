# Human comparison and finite economic ledger

Research date: 26 October 2026. Scope: a complementary AGI ALPHA lane producing accepted release-readiness, change-assessment, or artifact-maintenance evidence. These notes do not assert that the eventual selected task replaces an entire occupation. They supply external labor benchmarks and accounting rules; task duration, customer demand, complete automated cost, and willingness to pay remain to be established.

## Current primary evidence

| Source and reference period | Observation | Appropriate use |
| --- | --- | --- |
| U.S. BLS, May 2025 OEWS, software quality assurance analysts and testers, SOC 15-1253 | Median hourly wage USD 50.14; mean hourly wage USD 53.60; employment 186,740 | Wage-only benchmark for matched QA work; neither a customer price nor a measured duration |
| U.S. BLS, Occupational Outlook Handbook, updated 27 August 2026, May 2025 wages | Median annual QA/tester wage USD 104,300; median software developer wage USD 135,980 | Corroboration and occupation-scope description; use QA rate when evidence assessment is the relevant work |
| U.S. BLS, June 2026 ECEC, released 9 September 2026 | Private-industry professional and related occupations: total compensation USD 73.69/hour worked, wages USD 50.98, benefits USD 22.71 | Optional, explicitly modeled benefits adjustment; this occupational-group ratio is not measured QA-specific compensation |
| Government of Canada Job Bank, NOC 21222, Montréal region | Low/median/high hourly wages CAD 30.40/46.26/65.10; wage update 19 November 2025, reference 2024, Statistics Canada small-area model | Local wage-only comparison; occupational group broader than this deliverable |
| Same Job Bank page, Québec and Canada | Québec CAD 30.00/46.15/63.19; Canada CAD 28.85/46.15/68.68; reference 2023–2024 Labour Force Survey | Geographic sensitivity without mixing currencies |

Primary URLs:

1. [BLS May 2025 national occupation table](https://www.bls.gov/news.release/ocwage.t01.htm), QA/tester row. Retrieved 2026-10-26. Web evidence `turn2view0` / `turn3view1`.
2. [BLS developer and QA/tester profile](https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm), duties and pay sections. Retrieved 2026-10-26. Web evidence `turn1view1`.
3. [BLS June 2026 ECEC Table 4](https://www.bls.gov/news.release/ecec.t04.htm), overall professional-and-related occupational row, rather than a selected industry row. Retrieved 2026-10-26. Web evidence `turn4view0`.
4. [BLS June 2026 ECEC release](https://www.bls.gov/news.release/ecec.nr0.htm), date and measurement definition. Retrieved 2026-10-26. Web evidence `turn1view2`.
5. [Job Bank Montréal software QA analyst wages](https://on.jobbank.gc.ca/marketreport/wages-occupation/22511/geo25154), wage table and methodology notes. Retrieved 2026-10-26. Web evidence `turn4view1`.

The BLS role includes planning and performing tests, assessing risks, documenting defects and communicating findings. A narrowly scoped automated dossier can therefore be compared with those specific activities, while release approval, security accountability, interpretation of requirements, and organizational responsibility may remain outside its accepted scope. A matched competent human keeps conventional tools, Git, test runners, caches, and ordinary automation; “without AI” does not mean “without software.” The occupational data are population benchmarks, not proof that a particular person would need a particular duration or charge a particular price.

The ECEC benefits factor is 73.69 / 50.98 = 1.4454688113. Applying it to the QA median yields a **modeled** USD 72.4758062/hour compensation sensitivity. It combines different populations and periods. It excludes provider overhead, profit, capacity slack, procurement costs, and any task-specific differences. Do not present USD 72.48/hour as a BLS observation about QA workers. The unadjusted USD 50.14 rate should remain visible.

GSA's [CALC+ ceiling-rate tool](https://buy.gsa.gov/pricing/qr/mas) describes fully burdened not-to-exceed awarded rates. Its [official API documentation](https://open.gsa.gov/api/dx-calc-api/) distinguishes ceiling-rate research from a separate prices-paid tool. This search did not retrieve a matched accepted-dossier procurement transaction with scope and duration. A ceiling must not be substituted for a price actually collected, and a selected vendor rate would not establish demand for AGI ALPHA. Web evidence `turn3search0` and `turn5view0`. No contractor rate is used in the primary model.

## Duration thresholds without fictional time savings

Let `t_H` be the minutes a competent human needs for the entire equivalent accepted deliverable, `w_H` the hourly labor benchmark, `K_H` the human method's attributable tools and other costs, and `E_H` its customer effort valued only if measured or explicitly assumed. Then `H = w_H * t_H / 60 + K_H + E_H`.

For a provider-cost comparison, let `A` be the complete automated cost for that same accepted outcome, including attributable investment, unsuccessful attempts, maintenance, exceptions, and customer effort where the comparison requires it. With comparable responsibility and quality, the cost crossing occurs at:

`t_H > 60 * (A - K_H - E_H) / w_H`.

For the customer's purchase decision, replace provider cost with the amount the customer actually pays, `P`, and include the service's customer effort `E_A`:

`t_H > 60 * (P + E_A - K_H - E_H) / w_H`.

These are different comparisons. A cheap provider can charge an expensive price; customer savings do not become provider revenue. If effort is unmeasured, leave the corresponding variable unknown. Setting the difference in customer effort to zero is a declared equal-effort scenario, not a measurement.

Normalized conversions, calculated directly from the sourced wage benchmarks:

| Comparison | Minutes of matched human labor per currency unit of complete alternative cost |
| --- | ---: |
| U.S. wage-only median | 1.196649382 minutes per USD |
| U.S. modeled benefits adjustment | 0.827862471 minutes per USD |
| Montréal wage-only median | 1.297016861 minutes per CAD |

These coefficients prescribe neither a price nor a duration. Do not exchange USD and CAD without a dated rate if a cross-currency comparison is needed. Neither recruitment nor a human panel is necessary for this explicitly conditional comparison, but a precise savings ratio requires an observed or defensible task-duration model.

## What belongs in the cost denominator

Use accepted useful missions as the delivery denominator. Keep real triggers, no-op checks, repeated measurements and negative controls separate. No-op detection consumes resources but does not become a new delivered customer job. All failed attempts contributing to a mission belong in that mission's cost. A recovered outcome counts once. An earlier completion has turnaround value only; it is not additional eventual production when both methods finish the same job.

Record each charge once, under a stable event and capability identifier:

* Discovery, rejected opportunities, unsuccessful capability candidates, final construction, testing, integration and packaging.
* Model calls, tools, CPU and accelerator time, memory/storage retention, data transfer, source fetching and verification.
* Every failed execution, retry, recovery, independent outcome check and fallback.
* Shared maintenance, source/schema updates, cache invalidation, periodic audits, and retained-asset storage.
* Actual one-time operator actions, customer actions, shared human maintenance and residual exceptions, each with observed duration or an explicit unknown.

Marginal execution cost is the cost attributable to executing and verifying the current mission under the retained capability. Recurring delivery cost at a declared horizon is all delivery-attempt costs plus required shared operating/maintenance costs, divided by accepted missions during that horizon. Fully loaded cost adds all attributable discovery, construction, unsuccessful candidates, integration and validation. Do not count the same validation both as construction and recurring delivery.

The research session does not expose a complete inference bill or token-by-token costs. Therefore `inference_cost_usd=null`, `construction_cost_usd=null` and `fully_loaded_cost_usd=null` are legitimate outcomes until supported bounds exist. Wall-clock assistant duration must not be multiplied by a human wage, treated as paid inference runtime, or silently priced at zero. Measured CPU seconds can support a resource claim even when dollar costs remain unidentified. A lower bound excluding inference is not a complete estimate; if there is no defensible finite upper bound, do not fabricate one.

## One finite investment ledger for the tested asset

Maintain two reconciled views of the **same** capability: cash flow and economic attribution. Cash construction outlays occur when paid; amortization is for cost comparison. Subtracting both capex and its amortization from the same cash balance double-counts it.

Let `B_t` be actual cash on hand, `C_t` actual customer collections, `F_t` external starting or follow-on capital, `D_t` paid delivery/operating costs, and `I_t` paid construction/integration. Then:

`B_t = B_(t-1) + C_t + F_t - D_t - I_t`.

Let `O_t` be unpaid binding obligations and `R_t` required reserves. Unencumbered cash is `U_t = B_t - O_t - R_t`; refuse new commitments exceeding `U_t`. Reserves should follow stated obligations, failure/refund exposure and maintenance requirements. No arbitrary reserve or reinvestment percentage is needed. Starting capital can fund construction but cannot establish that work financed its own improvement.

The self-financing claim requires collected customer revenue, after the attributable costs and obligations of earning it, to cover the investment under investigation. An internal cost saving is not automatically cash available for investment. Customer savings, uncollected invoices, hypothetical service prices, token issuance, and token appreciation never enter actual collections. Keep USDC amounts, USD benchmark values, CAD benchmark values, and AGIALPHA utility entries in separate units. No token transaction is necessary for this study.

For modeled financing, use an explicitly named scenario with every assumed receipt and cost labeled `simulated`; it must not modify actual balances. Preserve failures and negative balances as infeasible states. If unknown costs prevent a numeric finite balance, record the unresolved expression and `feasibility=unknown` instead of a fictitious solvent balance.

Suggested ledger columns: `event_id`, `utc`, `mission_id`, `capability_id`, `phase`, `kind`, `resource_quantity`, `resource_unit`, `amount`, `currency`, `evidence_class`, `source_ref`, `cash_or_attribution`, `obligation_id`, `status`, `unknown_reason`. Allowed evidence classes: observed, sourced, modeled, bounded, unknown. Unknown amounts are null, not zero.

## Investment repayment and sensitivity

For the same accepted scope, let `d_i = C_incumbent_i - C_capability_i` be incremental delivery savings. Let `I` be complete attributable discovery/construction/failed-candidate/integration investment, and `M(N)` incremental maintenance and storage through `N` real fresh missions. Net benefit is:

`G(N) = sum_i(d_i) - I - M(N)`.

If there is supported incremental **collected contribution margin** from genuinely additional useful work, record it separately and include it once. Avoid adding a human-market savings estimate to internal execution savings: they describe different counterfactuals. If equal eventual outcomes exist, earlier delivery cannot be valued as extra output without demonstrated timing-sensitive demand.

For constant saving `d` and fixed maintenance `M`, the arithmetic crossing is `N* = ceil((I + M) / d)` only when `d > 0`. If `d <= 0`, there is no finite repayment from these savings. If `I`, `d` in currency, or justified demand is unknown, the monetary crossing is unknown. A resource-only crossing can be shown in the corresponding measured resource unit, with no conversion into commercial profit.

A useful alternative to assumed demand is the **maximum affordable complete investment** at each disclosed number of substantively triggered missions: `I_max(N) = sum_i(d_i) - M(N)`. This reports what the evidence could support without presuming what the asset cost. If real mission history provides only a few events, show the observed horizon and an explicit extrapolation rather than pretending that repeated replay establishes recurrence.

Required sensitivities are low utilization, maintenance growth, failure/retry rates, demand disappearance, and competitive convergence. Give the strong conventional builder the same information and permission to retain tools, and charge its new construction. Benefit versus the incumbent supports investing in reuse; benefit versus the equally capable builder would support a method claim. An exact tie is consistent with a useful conventional component and cannot substantiate an algorithmic breakthrough.

## Commercial evidence classification

* An actual requirement or backlog in these repositories is observed internal need.
* Source histories collected under a frozen rule can form a representative workload.
* Broader organizations needing comparable reports are an assumed market use case unless directly documented.
* Paid demand requires a real transaction or contract with matching scope; none is established by the sources in this note.

No total market size is required to make the narrow offering useful. Occupation-wide spending cannot be relabeled the realistically serviceable market. Obtainable demand remains unknown without a sales or utilization record. The honest commercial claim can still be useful: an accepted bounded outcome and a transparent human-duration threshold identify where a service *could* be cost competitive, while the actual investment decision remains gated on complete costs and real recurrence.
