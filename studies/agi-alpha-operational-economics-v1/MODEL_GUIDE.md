# Reproducing the operational economics amendment

## What this model establishes

This is a separately frozen, market-data-grounded **scenario comparison**, not a new human trial or a measurement of a deployed service. The employer's bounded job is a publication-readiness evidence pack made from two approved source packets and four specified passages. The actual native artifact and acceptance record are preserved in `observed/`. They establish exact-passage coverage and provenance for that component, not open-ended research, the quality of model-generated interpretation, or the reliability of the hypothetical service surrounding it.

The complete operating scenarios compare traditional work using ordinary non-AI software with an employer-owned or attributed-cost Agent service. They charge the resources used by the service directly. A separate provider invoice is not added to those same costs. The provider engineering team is assumed to be U.S.-based and priced at sourced U.S. professional compensation in every reporting currency. Employer review and traditional production use the selected local labor-price basis. No provider price, customer contract, cash saving, revenue or profit was observed.

The original research authoring bill and actual employer attention remain unknown. Prospective construction, deployment, integration, review and maintenance allowances are not substitutes for that missing historical invoice. Material downstream losses also remain unknown: the low-consequence draft scenario does not establish expected liability for high-consequence use.

## Authorization and immutability

The sixteen-file specification was published before these scenario calculations at commit `4d1d2af3e77a5346e3dc1a574f509d5c67c0aef7`. Its freeze manifest SHA-256 is:

`54bc70fec9bb635b473193d966d36ed5bf445460a58255f025cbed4a30854d8b`

`AUTHORIZATION.json` records authorization for local calculation at 13:30:40 UTC on 25 October 2026. The public notice is <https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6398263719>.

The executable checks the manifest's identity, every frozen file's size and hash, and the matching authorization both before calculation and before completing the output manifest. It makes no network call, requests no model inference and deploys nothing. It refuses to reuse an existing output directory. This preserves unsuccessful implementations and previous checkpoints.

## Run locally

Python 3.10 or later and its standard library are sufficient. From the directory containing `economics_amendment_v1`, choose a fresh result directory:

```sh
python economics_amendment_v1/src/model.py \
  --output economics_amendment_v1/outputs/reproduction-001
```

The first producer execution is preserved at `outputs/run-001/`; its source snapshot, invocation, return code, standard output and standard error are under `development/attempt-001/`. The independent evaluator computes its own probability-path expansion and prices without importing this model. Audit artifacts are in `evaluation/`; an independent calculation checkpoint alone is not the final reconciliation report.

The final independent reconciliation is `evaluation/INDEPENDENT_AUDIT.json`: 157,435 checks passed with no producer discrepancy. `evaluation/DERIVATIVE_AUDIT.json` separately passes 24,125 checks of the CSV exports and post-result reuse diagnostic. `evaluation/FIGURE_DATA_AUDIT.json` independently verifies all 55 plotted values and identity fields. These accounting checks are not new accepted jobs, human observations or field-reliability evidence.

The evaluator commands write timestamped reports to their own `evaluation/` directory. Run them in a **separate copy** to preserve the published audit originals. From the directory containing the original amendment, choose a destination that does not already exist:

```sh
python -c 'import shutil; shutil.copytree("economics_amendment_v1", "economics_amendment_v1_audit_copy")'
python economics_amendment_v1_audit_copy/evaluation/oracle.py --run
python economics_amendment_v1_audit_copy/evaluation/audit_figures.py
python economics_amendment_v1_audit_copy/evaluation/audit_results.py \
  --results outputs/run-001/results.json
python economics_amendment_v1_audit_copy/evaluation/audit_derivatives.py
```

The oracle's `--run` is required. The producer-results argument is relative to the copied amendment root. The figure-data audit runs before the primary audit report is regenerated because it checks the published report's exact hash. Recreated audit reports have fresh timestamps and therefore different hashes; the economic comparisons must still pass. The original figure builder also deliberately binds to the **published** primary-audit hash, so reproduce those canonical figure bytes from the original unchanged extraction, not from the copy whose audit reports have just been regenerated. No provider invocation or deployment occurs in these commands.

## Files and interfaces

| File | Contents |
| --- | --- |
| `inputs.json` | Frozen assumptions, six path definitions, usage budgets, labor-price choices and prespecified sensitivities. |
| `sources/pricing_register.json` | Dated official provider, executor, storage and FX sources; routing and billing conventions. |
| `sources/labor_rates.json` | Labor-price observations, years, occupations, geography, benefits coverage, methodology and limitations. |
| `observed/ANCHOR.json` | Native component measurements and explicit unknowns; points to the actual artifact and acceptance record. |
| `src/model.py` | Deterministic producer implementation with Apache-2.0 SPDX identifier. |
| `outputs/run-001/results.json` | Complete branch, event, component, resource, fixed-cost, latency and capacity decomposition. |
| `outputs/run-001/results_summary.csv` | Sixty core scenario/price-basis/productive-duration comparisons. |
| `outputs/run-001/sensitivities.csv` | Twenty-three prespecified one-way sensitivity rows. |
| `outputs/run-001/component_ledger.csv` | Component cost, account ownership and period for every core Agent case. |
| `outputs/run-001/OUTPUT_MANIFEST.json` | Result file hashes and row counts. |

There are twelve primary scenario/price-basis cases: three joint operating scenarios and four labor-price bases across three geographies. Each contains five productive human durations, 5/15/30/60/120 minutes. These durations are assumptions. They are not inferred from salaries or presented as matched human observations.

The detailed JSON uses `core_scenarios`. Each case contains `agent_variable`, `fixed_agent`, `annual_at_demand`, `first_commission`, `capacity`, and `traditional_comparisons`. Each comparison has `productive_minutes`, `traditional` and `hybrid`, with equivalent first-commission, annual and capacity accounts. Flat aliases meet the separately frozen `output_schema.json` interface. Top-level `human_duration_comparison` and `hybrid_complete_demand` provide compact cross-case tables.

Money is in each row's `currency`. Human resources are minutes, executor occupancy is seconds, and tokens include assumed charged reasoning output. `cost_per_expected_accepted` is currency per expected accepted output, not cost per request and not a probability-free promise of delivery. `None`/JSON `null` represents undefined denominators or unknown observations; it must not be displayed as zero.

## Acceptance and failure accounting

The six terminal paths are disjoint: direct acceptance, model repair followed by acceptance, infrastructure retry followed by acceptance, combined specialist rescue followed by acceptance, final rejection, and early refusal. Each lists actual event occurrences in the scenario. This allows failures, re-reviews, retries, specialist rescue, exhausted attempts and closure effort to be charged without an independent-retry assumption or a duplicate generic failure surcharge. No path exceeds three production attempts. A model call is not a production attempt.

For path probability `p_b`, acceptance indicator `a_b`, variable cost `c_b` and resource vector `r_b`:

```
Q = sum(p_b * a_b)
E[C_variable] = sum(p_b * c_b)
E[resource] = sum(p_b * r_b)
C_total(N, M) = initial_fixed + M * monthly_fixed + N * E[C_variable]
C_per_expected_accepted = C_total(N, M) / (N * Q)
```

All failed and refused requests stay in the numerator. The denominator is the expected number accepted in the finite cohort. A one-request first commission charges the entire initial investment plus one operating month; dividing by `Q` is a ratio of expectations. It does not model infinite repetition until a particular commission succeeds.

The Agent-only service leaves some requests unresolved. The separate complete-demand hybrid charges the full unsuccessful Agent path, an additional handoff, and a fresh traditional completion. It also pays for both arms' readiness and support. Traditional final acceptance is assumed to be one, a favorable assumption for competent traditional work rather than an observed success rate. Human correction and rereview costs are nevertheless included.

## Account ownership

Every priced component has an `ownership` label. Identifiable successful and unsuccessful construction, independent qualification, capability revalidation, refresh and unsuccessful improvement are improvement accounts. Delivery, setup, deployment, executor integration, service support, runtime maintenance, employer onboarding and governance retain their service or employer labels.

Some fixed model, tool and infrastructure allowances jointly support service and improvement. No unsupported split is invented. Accounts expose three totals:

- `identified_improvement`;
- `joint_service_improvement_unallocated`;
- `service_and_employer`.

They sum to the account's full cost. Detailed ownership categories, component amounts and shares remain inspectable. Delivery attempts, failures and review are included in variable service cost. Annual accounting combines the initial and all twelve monthly reserves with the complete variable cohort. Monthly reserves are not refunded or prorated when assumed setup reduces the working calendar.

Human resources remain separate: `employer_minutes`, `provider_minutes` and `traditional_worker_minutes`. `all_human_minutes_per_expected_accepted` includes all three and their finite-volume fixed allocations. A reduction in total labor can coexist with increased employer attention. Neither is automatically a cash saving.

## Native execution, billing and time

The measured native wall time, approximately 0.112 seconds, is an included lower-bound subcomponent of the scenario's occupied executor time. It is not added twice and is not used as a headline full-service turnaround. The observed native delivery made zero task-time model calls. The model and paid search quantities in the main scenarios describe a hypothetical surrounding service and were neither required nor executed by that frozen native task.

Cloud billing uses allocated occupied time rounded to 100 milliseconds, one vCPU and two GiB per independently allocated request slot. Two parallel slots mean two separately allocated instances with maximum one request each. Raw occupancy, rather than rounded billing duration or measured child CPU, is used in the resource bound. Search fees count successful search calls; aggregate model-token budgets already include those retrieved inputs. Token quantities are not multiplied again by the number of calls.

Operational latency adds disjoint serial occupied execution, employer work, provider work and external wait components. Reported statistics include conditional successful latency, all-request and failed-request means, discrete successful median and p95, and the worst declared path. Those are assumed distributions. They are not measured service-level performance. The first commission adds assumed readiness time; hybrid readiness conservatively adds the two setup delays sequentially.

## Capacity and the setup diagnostic

The frozen annual budget is USD 25,000, nominally converted to each reporting currency. Human, executor and assumed aggregate token pools also constrain requests. Fixed work consumes the corresponding capacity pools; human rescue consumes a traditional-worker pool as well as employer attention.

For time resources, the model evaluates both an annual ceiling after initial and recurring usage and a postdeployment calendar ceiling after recurring usage. Initial work is not subtracted twice. The smaller residual constrains delivery. Economic and token residuals are separately evaluated. A fixed-resource shortfall yields zero admission even if variable use of that resource is zero. Otherwise, admission is the floor of the minimum resource request bound and declared demand.

**This is an aggregate-resource feasible upper bound, not a proved daily schedule.** The post-result `setup_scheduling_diagnostic` compares initial resource usage with uniform daily availability over the declared setup window. It does not change any frozen input or primary calculation. For example, base Agent setup contains 72 provider hours; at 120 minutes per workday and 80% utilization, uniform allocation would require 45 working days, exceeding the declared 10-day setup assumption. A frontloaded annual-average allocation could behave differently, but additional setup staffing was not demonstrated. First-commission setup elapsed time is therefore explicitly assumed and unvalidated. The traditional arm receives the same diagnostic.

At every declared demand, display its feasibility flag alongside its amortized cost. An infeasible large denominator must not be used as the headline attainable cost. `capacity.feasible_admitted_cohort` recomputes allocation at the aggregate admitted cohort. If admission is zero, its cost per expected accepted output is null even though initial and recurring obligations remain costly.

## Interpreting the sensitivities

Only the prespecified one-way sensitivities are executed: requested reuse volume; delivery tokens; employer review; unsuccessful initial construction labor; recurring support and upkeep; and the native-delivery route without delivery model/search fees. They are not confidence intervals, probability estimates or a search for favorable combinations. The native-route sensitivity preserves positive fixed investment, review, maintenance, occupancy and the same assumed path acceptance; it establishes no equality of field reliability.

At the U.S. office/administrative base price, the declared 1,000-request scenario yields approximately USD 28.91 per expected Agent-accepted output versus USD 28.42 for a traditional 30-minute productive-work assumption. The complete-demand hybrid is approximately USD 29.73. The declared Agent cohort does not fit the resource budget: its aggregate admitted cohort is 829 requests and 787.55 expected accepted outputs, at approximately USD 31.74 per accepted output. These are conditional modeled results, not an experimental commercial advantage.

The useful conclusion is a set of inspectable adoption thresholds and cost drivers. Model inference is only one cost category. Review, provider work, unsuccessful construction, support, maintenance and attainable reuse can determine whether automation is economical. Continued capability construction is justified only when its complete incremental cost is supported by eligible demand and resource-feasible savings. These calculations establish neither self-acceleration nor cash available for reinvestment.

## Post-result analytical reuse diagnostic

After the primary results, the research owner requested an explicit algebraic reuse threshold using only the existing base cases and the existing 30-minute productive-human assumption. The independent evaluator approved the formulas before the diagnostic ran. This addition is labeled **post-result**, not retrospectively included among the primary frozen analyses. It does not alter the sixteen frozen files or `outputs/run-001/`.

The runnable sidecar is `src/reuse_diagnostic.py`, and its eight derived rows are in `outputs/post_result_reuse_diagnostic.json`. Reproduce it into a new output file:

```sh
python economics_amendment_v1/src/reuse_diagnostic.py \
  --results economics_amendment_v1/outputs/run-001/results.json \
  --output economics_amendment_v1/outputs/reproduction-reuse-001.json
```

Let `F_A` and `F_H` be annual fixed costs, `v_A` and `v_H` be expected variable cost per request, and `Q` be the assumed Agent acceptance probability. At requested volume `N`, pure Agent unit-cost parity satisfies:

```
F_A/(N*Q) + v_A/Q = F_H/N + v_H
DeltaF = F_A/Q - F_H
DeltaV = v_H - v_A/Q
N* = DeltaF / DeltaV
```

When `DeltaF > 0` and `DeltaV > 0`, the smallest integer volume at non-strict cost parity is `ceil(N*)`. When the fixed disadvantage is positive but recurring saving is nonpositive, no finite reuse volume produces payback. The sidecar also handles all-volume equality, all-volume advantage and a possible low-volume-only advantage without misleadingly labeling them permanent payback.

For the hybrid, `F_Y = F_A + F_H` and `v_Y = v_A + (1-Q)*(v_H+handoff)`. Use `DeltaF = F_Y-F_H` and `DeltaV = v_H-v_Y`. The conventional readiness account cancels algebraically in the fixed difference because the hybrid actually pays it; it is not omitted from the cost ledger.

At the primary U.S. office/admin base, the pure threshold is 1,040 requested jobs and the complete-demand hybrid threshold is 1,113. Their existing aggregate resource-admission bounds are 829 and 703 respectively, so those thresholds are outside the permitted workload under the same assumptions. This comparison uses requested volume, not expected accepted count. Pure Agent unit-cost parity still has different completion coverage from the complete-demand human comparator.

All four original price bases retain the same distinction between an algebraic threshold and an operationally attainable workload. The sidecar compares each threshold with both arms' primary aggregate requested-work bounds and with declared demand. It performs no new capacity optimization or parameter sweep. The separate uniform-calendar setup diagnostic remains a limitation even if a threshold were to fit those aggregate bounds.
