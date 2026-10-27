# Human-led R&D costing framework

As-of date: **2026-10-27**. Prepared before candidate selection. This is a labor-cost and uncertainty framework for a small Canadian or U.S. technical team producing a novel computational/scientific instrument. It is not an established service-market price, a vendor quote, or an empirical estimate of project success. The ordinary discovery record was not modified.

## 1. Four primary sources

| ID | Primary source | Reference/publication timing | What it supports |
|---|---|---|---|
| S1 | [U.S. BLS, national occupational employment and wage table](https://www.bls.gov/news.release/ocwage.t01.htm) | May 2025 occupational estimates; retrieved 2026-10-27 | Employee wage anchors for software, research scientists, and candidate-dependent domain occupations |
| S2 | [U.S. BLS, Employer Costs for Employee Compensation](https://www.bls.gov/news.release/ecec.htm) | June 2026 observations; released September 9, 2026 | Employer wages versus benefits; a broad compensation loading cross-check |
| S3 | [Canada Job Bank, software developers and programmers, NOC 21232](https://www.jobbank.gc.ca/wagereport/occupation/22548) | Updated November 19, 2025; national figures reference 2023–2024 Labour Force Survey | Canadian software employee wage anchors |
| S4 | [Canada Job Bank, data scientists, NOC 21211](https://www.jobbank.gc.ca/marketreport/wages-occupation/227147/ca?source=6&wbdisable=false) | Updated November 19, 2025; national figures reference 2023–2024 Labour Force Survey | Canadian data-science wage proxy, subject to role matching |

The dates above are data vintages, not a claim that wages were surveyed on the as-of date. Keep currencies separate. No CAD/USD conversion or automatic wage inflation is assumed. Canadian data scientist is a broad proxy and may understate the compensation necessary for a senior applied-research lead.

## 2. Observed gross employee wage anchors

### United States — USD/hour

| Role mapping | Occupational category | Median hourly wage | Mean hourly wage | Mean annual wage |
|---|---|---:|---:|---:|
| Software implementation | Software developers | 65.38 | 71.20 | 148,100 |
| Applied computational research | Computer and information research scientists | 67.45 | 74.00 | 153,930 |
| Provisional domain specialist | Physical scientists, all other | 58.93 | 62.13 | 129,230 |
| Possible alternate domain match | Materials scientists | 56.63 | 60.67 | 126,180 |
| Possible alternate domain match | Geoscientists, except hydrologists and geographers | 49.00 | 55.84 | 116,150 |

Source S1. These are national occupational observations, not interchangeable specialties or senior-consultant rates. Select the domain row from the actual scientific task; do not choose the cheapest category after seeing the desired result. Mean annual wages and median hourly wages are different statistics. genui{"citation":{"ref":"turn22view1"}}

### Canada — CAD/hour

| Role mapping | NOC | Published low | Published median | Published high |
|---|---|---:|---:|---:|
| Software implementation | 21232 | 30.00 | 48.08 | 76.92 |
| Applied data-science proxy | 21211 | 30.00 | 46.15 | 69.74 |

Sources S3–S4. These are employee wages, with the table's own low/median/high labels, not project-cost quantiles. genui{"citation":{"refs":["turn24search1","turn28search1"]}}

A Canadian domain-specialist category should be selected after the candidate is fixed. The U.S. domain alternatives above supply a sourced U.S. costing route now. Do not synthesize a Canadian specialist wage by currency conversion or silently reuse a data-science median.

## 3. Gross wage, employer cost, delivery cost, and selling price

1. **Gross employee wage:** pay before employee deductions. The occupational tables anchor this layer. It excludes employer benefit and payroll burdens and says nothing about a vendor's quoted rate.
2. **Employer compensation cost:** wages plus employer-paid benefits and payroll obligations. S2 reports June 2026 private-industry averages of USD 32.82 wages and USD 46.89 total compensation per hour worked, a ratio of 1.429. For the professional, scientific, and technical services industry, wages are USD 51.88 and total compensation USD 75.97, a ratio of **1.464**. These are aggregate ratios, not a measured burden for this proposed team. Benefits include paid leave, supplemental pay, insurance, retirement, and legally required benefits. genui{"citation":{"ref":"turn22view2"}}
3. **Internal project delivery cost:** employer compensation attributable to the project, plus shared operating costs and explicit external inputs. Count evaluation, failed experiments, rework, project management, documentation, and handoff—not only implementation time.
4. **Selling price:** a negotiated commercial amount reflecting scope, alternatives, intellectual property, risk allocation, support, and supplier economics. None of the four sources supplies this amount. A cost-plus calculation is a proposed offer or accounting scenario, not evidence of market price or willingness to pay.

For a preliminary U.S. sensitivity analysis, use compensation multipliers of **1.30 / 1.46 / 1.65** and separate shared-overhead allowances of **10% / 20% / 35%** of compensation. These are analyst assumptions around the S2 cross-check, not measured confidence intervals. The corresponding total multipliers are 1.43 / 1.752 / 2.2275 before separately priced experimental inputs. A Canadian burden must be replaced with the selected team's actual employer costs; using the U.S. range there is only a flagged stress test.

Avoid counting a cost twice. The quick compensation factor already reflects leave-related costs on a per-hour-worked basis; do not add another generic vacation factor. If using annual payroll instead, calculate annual salary plus actual employer costs divided by allocable project hours, and do not apply the ECEC multiplier on top. Likewise, if overhead already includes equipment, administration, or licenses, do not add the same item again. The quoted hourly wage and an employer-compensation ratio come from different samples, so their product is an approximation.

## 4. Before assigning effort: freeze the promised deliverable

The provisional scope is **one research instrument with a reproducible build, a stated scientific claim, an independently checked validation set, failure boundaries, documentation, and a partner acceptance decision**. It does not automatically include a production SaaS business, multi-site deployment, regulatory clearance, a custom physical apparatus, or multiple field seasons. If these are necessary for the selected candidate, add them explicitly.

The human counterfactual should use ordinary professional software and established automation available on the as-of date. A manual-from-scratch comparison would inflate apparent agent savings. If frontier coding agents are prohibited in the human comparator, record that design choice; it is not automatically the commercial alternative.

## 5. Low/central/high planning assumptions — not observed estimates

### Effort and elapsed time

| Quantity | Low | Central | High |
|---|---:|---:|---:|
| Software developer hours | 400 | 1,000 | 2,400 |
| Applied scientist hours | 240 | 600 | 1,440 |
| Domain specialist hours | 160 | 400 | 960 |
| Total human project hours | **800** | **2,000** | **4,800** |
| Elapsed duration | **3 months** | **8 months** | **18 months** |

These are deliberately broad placeholders for a small team with two core technical contributors and fractional domain expertise. A person's hours are counted once even if they wear multiple roles. With the software role averaging roughly 30 project hours per week, the selected durations are broadly compatible with the effort ranges; review, access, hardware procurement, or biological/field cycles can extend calendar time without proportionally increasing labor. They are not empirically estimated percentiles.

One provisional phase allocation is 15% problem specification/access, 20% baseline and data audit, 30% implementation, 25% independent validation and rework, and 10% documentation and handoff. This divides the role-hour totals rather than adding another layer of hours. Refine it only after the candidate's required experiments and acceptance criteria are known.

### Success probability

Use **0.20 / 0.50 / 0.80** as low/central/high sensitivity values for the probability that one funded attempt reaches the prespecified technical acceptance criterion. These are elicitation placeholders with no empirical calibration. They are separate sensitivity axes, not probabilities automatically paired with low, central, and high labor estimates. More effort does not mechanically imply either lower or higher success.

Keep technical acceptance separate from buyer adoption, payment, and recurring use. A successful prototype may have no paying market. If there is no evidence about adoption, show adoption as unknown or as a separately labeled scenario rather than folding a guessed rate into technical success.

## 6. Calculation specification for the later candidate model

No economics implementation is included here. The eventual model should retain these distinct quantities:

- **Attempt cost:** sum over roles of hours × gross wage × compensation factor, plus non-overlapping overhead and explicit external costs. Preserve currency, source vintage, and role mapping for every wage input.
- **Stage-gated expected spend:** for stages with costs C0, C1, C2 and conditional pass probabilities p0, p1, expected spend is C0 + p0·C1 + p0·p1·C2. Do not charge later stages after a specified stop decision unless fixed commitments require it.
- **Success probability:** p0·p1·p2 only when the probabilities are conditional on reaching each stage. Unconditional marginals cannot simply be multiplied.
- **Expected cost per successful delivered instrument:** expected spend divided by success probability can describe a repeated comparable portfolio. It is not the cash budget for one project, and does not imply failed scientific hypotheses can be retried independently until success.
- **Price and value:** leave unpopulated until a buyer, acceptance scope, closest substitute, and credible willingness-to-pay evidence exist. Report internal R&D cost separately from a proposed quote, replacement-cost claim, or customer value.

Count human review and opportunity cost in the agent-assisted alternative as well. Compare equal acceptance standards and equivalent retained artifacts. Avoid combining optimistic agent assumptions with a deliberately adverse human case.

## 7. Candidate-dependent inputs still required

Before making any commercial conclusion, fill in the actual scientific specialty and location; customer-owned versus newly acquired data; external validation and hardware needs; project-access delays; existing reusable components; whether the output is a one-off or a maintained product; the relevant alternative; and buyer acceptance/payment evidence. A small number of practitioner estimates can improve the hours assumptions, but should be logged as elicitation, not a representative market survey.

Retrieval note: BLS tables were successfully opened and inspected. Job Bank wage values and timestamps were verified in official indexed results; several direct opens timed out. A Canadian bulk-data fetch was attempted but blocked, so no claim is made that the CSV was downloaded or audited. The four sources above are the adopted source set. No full costing code or candidate-specific sales price has been created.
