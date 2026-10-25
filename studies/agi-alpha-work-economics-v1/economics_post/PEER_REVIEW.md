# Independent economics review and measured-resource extension

Review date: 25 October 2026. This directory is a **postfreeze economic presentation**, created after the primary campaign. It changes no protocol, acceptance decision, source, worker, task or frozen analysis. All 69 files listed in `../protocol/FREEZE.json` match their committed hashes. The separate model therefore supplements the preregistered evidence rather than retroactively changing its claims.

## Review conclusion

The model is suitable for a conditional employer decision analysis. It combines an actual operating quantity from the AGI ALPHA workflow with externally observed labor-price estimates. It does **not** estimate a measured full-service cost advantage, provider margin, customer cash savings or human speedup. Those quantities remain unknown. The six main cases deliberately include two losses, a modest advantage and strong conditional advantages. The full unweighted grid is summarized without presenting favorable-grid frequency as a probability of commercial success.

## What is measured

The primary campaign contains 36 attempts and 36 acceptances under the frozen deterministic machine criteria. Every receipt has a CPU quantity. Across all attempts, CPU time is 0.357956 seconds at the median, 0.174306–1.634259 seconds across the observed range, 0.582980 seconds at the mean and 20.987286 seconds in total. CPU scope includes the worker from startup and completed child processes through packaging. The final receipt-serialization tail, host idle time and pre-campaign construction are outside that scope.

Operational model calls are zero in these receipts. This is a measured property of the reused local workflow, not evidence that its construction, supervision, maintenance or complete delivery was free. Actual attention, construction allocation, maintenance allocation and host invoice are unknown. Zero unplanned orchestration interventions would not establish zero human effort.

At an assumed price of one applicable currency unit per CPU-hour, median CPU is priced at 0.0000994322 units per attempt. The complete campaign's CPU component is 0.0058298017 units, or 0.0001619389 per accepted output. These are tariff scenarios, not an invoice or a full delivery cost. Even the observed maximum CPU at the highest assumed tariff of five units per CPU-hour costs only 0.0022698042 units. The measured CPU component is therefore small **within this explicit tariff range**; attention and construction assumptions dominate these scenarios.

Use median CPU only for a typical-job illustration. A portfolio or accepted-output resource ledger must use the sum of resource expenditure on **all** attempts divided by accepted outputs. The model reports both. The observed min/max is a resource range, not an uncertainty interval, and reflects this fixed portfolio rather than market task variability.

## Algebra and interpretation

For a loaded hourly rate `w`, traditional human effort `t`, residual system-side human effort `h`, measured CPU seconds `u`, assumed CPU price `p`, traditional nonlabor cost `v`, and system allocation `k`:

`C_H = (w*t/60 + v)/qH`

`C_A = (w*h/60 + p*u/3600 + k)/qA`

Here `qH` and `qA` are accepted outputs per attempted job in the modeled operating regime. Costs and effort in each numerator are **per attempt**. Division by acceptance rate describes a steady stream of comparable attempts or homogeneous retries; it is not a claim that every failed job will eventually be deliverable. Rates may depend on difficulty, cost and operator intervention in practice. Such dependence requires stratified empirical totals rather than an independent-parameter grid.

The cost ratio is `C_H/C_A`. Potential capacity value is `C_H-C_A`. The break-even traditional effort is `60*(qH*C_A-v)/w`. The effort-capacity ratio is `(t/qH)/(h/qA)`, interpreted as accepted jobs per employer-attention hour under the assumed workflows. It is not observed wall-clock capacity or throughput. If different worker and reviewer rates apply, replace the single-rate attention terms with separate rate-times-effort sums.

The main table uses U.S. private-industry office/admin **total compensation USD35.96/hour**, from BLS ECEC December 2025; it adds no second benefits allowance. It assumes `qH=qA=1`, `v=0`, and CPU price USD1 per CPU-hour. The assumed zero `v` makes this a direct labor-cost reference; actual ordinary-software or other human-side costs remain unknown. Allocations of USD1 or USD5 are assumptions for maintenance, construction amortization and otherwise unpriced non-attention overhead, not measured investments.

## Assumption coverage and source matching

The full grid covers traditional effort 5/15/30/60 minutes; residual attention 1/5/15 minutes; allocation 0.10/1/5/20 units per attempt; CPU price 0.1/1/5 units per CPU-hour; and independent human/system acceptance assumptions 0.8/0.95/1. The five wage-only rate series have employer-load scenarios 1/1.25/1.5. Seven already-loaded compensation or employer-cost series have load 1 only. This gives 22 valuation cases and **28,512 combinations**. The output includes every combination in counts and extrema, plus 22 geographic reference cases and selected reliability/resource slices. This is an unweighted parameter grid, not a sample of employers or a forecast distribution.

Quebec values are occupation-specific gross median wages from Job Bank's 2023–2024 Statistics Canada LFS basis; U.S. occupational medians use BLS 2025 wages reproduced by O*NET. U.S. ECEC group compensation includes benefits. Eurostat's 2025 country costs are broad covered-economy employer costs for enterprises with at least ten employees, not occupation-matched clerk rates. Each source's exact title, period, currency, basis and URL is retained in the JSON. A higher-skilled analyst rate is a sensitivity case and does not establish the required skill of every reconciliation.

CAD, USD and EUR cases are separate local-currency scenarios. Identical numeric assumptions across them do not imply equal FX value, purchasing power or provider prices. Eurostat's own published EUR values are used; no additional exchange conversion is introduced.

## Failure, rework and allocation safeguards

Every primary receipt enters the measured CPU distribution; none is removed because of its acceptance result. There happen to be no primary rejections. Control refusals are not paid-job acceptances, and development failures belong to investment accounting rather than being silently omitted from a claimed full cost. Their exact contribution remains unmeasured and must not be replaced by a fabricated zero.

Acceptance sensitivity is separate from the observed 36/36 machine result. It does not supply a reliability guarantee or human quality estimate. If either modeled acceptance rate is zero, the script marks accepted-output economics nonfinite and leaves ratio fields null. Unknown input costs remain unknown; missing CPU receipts stop the calculation instead of silently reducing the numerator. Repeated attempts incur all their costs. Human or system minutes that already include whole-job retry totals must not be divided by another failure factor for those same retries.

For construction amortization, `k` is explicitly **per attempt**: an investment `F` may contribute `F/N_attempts`. Dividing the final expression by `qA` then correctly allocates that investment to accepted outputs. Using `F/N_accepted` inside `k` and dividing by `qA` again would double-count failures. Maintenance, drift, rule changes, evidence review and rescue work still need explicit allocations as the system is reused. Shared setup should be allocated once according to a stated denominator, not charged once per attempt and again as construction.

No CPU tariff in this model establishes an actual cloud billing rate. CPU-seconds can differ from paid vCPU reservations, host wall time, minimum billable units or subscription charges. Such expenditure belongs in a measured invoice or in the separate allocation assumption. This is why the small CPU component cannot be the headline complete cost.

## Human evidence and commercial claims

Published neighboring studies remain external context. Their spreadsheet, transformation or malformed-CSV timing cannot be substituted for the frozen reconciliation contract's human time. The economic model is useful without that substitution because it tells an employer what traditional effort and residual attention would justify adoption at a given cost.

Potential capacity value is a resource valuation. It becomes cash saving only if an actual expense changes, such as outsourcing, overtime or a staffing requirement. Provider prices, customer value, revenue, operating costs and profit require separate accounting. The 60-fold attention-capacity case in the table comes from the stated 60-minute/one-minute assumptions; it is **not a measured 60-fold product claim**. Equally, the modeled 22.48 cost ratio in that case is conditional and must stay beside its assumptions.

## Reproduction

Run `python3 economics_post/model_measured_resources.py` from the study root. It uses the Python standard library, verifies frozen hashes, reads the 36 raw primary receipts and public labor-rate inputs, and writes `measured_resource_economics.json`, `SCENARIO_TABLE.md` and `MODEL_VALIDATION.json` only in this directory. The underlying frozen evidence is not modified. Final postfreeze file hashes are in `SHA256SUMS.json`.
