# Market-data-grounded human-work economics

Research date: 25 October 2026. This is an additive extension of `RESEARCH_NOTES.md`; the original global-market model and its hashes are preserved.

## Status and decision value

The public-data economic benchmark is complete. It combines official occupational wages, employer compensation estimates and occupation-task descriptions with explicit system-cost, human-effort and attention scenarios. Reproduction requires no participant recruitment or private employer data. The new same-task human trial is **NOT RUN**: published wage statistics do not measure the time, corrections or acceptance of the AGI ALPHA reconciliation jobs. No external study's duration is silently substituted for those jobs.

The decision model answers a useful employer question now: **At the applicable labor cost, how much traditional work must this accepted deliverable replace to justify its full cost?** Employers can insert their own observed workflow time, review burden and purchased service price. A favorable threshold is conditional evidence of commercial opportunity; it is not an observed speedup or cash saving.

## Occupational task fit

U.S. Department of Labor O*NET lists checking entries and classifications, reconciling records and reporting discrepancies among bookkeeping-clerk tasks (43-3031.00). Data-entry keyers (43-9021.00) validate against source records, correct or escalate errors and maintain work records. Business-intelligence analysts (15-2051.01) prepare business reports, test against requirements and maintain reusable reporting templates. These descriptions establish that the bounded portfolio belongs to recognizable paid work. They do not show that the entire occupation is automated. Sources: `onet_bookkeeping2026`, `onet_dataentry2026`, `onet_bi2026`.

Humans still choose business meaning, authorize source records, resolve ambiguous identities, determine accounting policy and materiality, approve consequential changes and remain accountable. The higher-skilled analyst rate is a sensitivity case; a simple CSV comparison does not automatically justify charging a data analyst's wage. O*NET's displayed wage for the detailed business-intelligence title uses the broader Data Scientists category; this value is deliberately excluded.

## Source table

All amounts are per hour. Canadian and U.S. occupation rows are wages only. U.S. broad-group rows include benefits. European rows are total employer labor costs for a broad covered economy, not matched clerk occupations. All are statistical estimates, not pay observed for participants in this study.

| Geography and occupation | Code | Reference period | Currency | Central rate | Published low–high | Basis and source |
|---|---|---|---|---:|---:|---|
| Quebec: data entry clerks | NOC 14111 | 2023–2024 | CAD | 24.00 | 17.00–28.85 | Median wage; Job Bank/LFS |
| Quebec: accounting technicians/bookkeepers | NOC 12200 | 2023–2024 | CAD | 28.02 | 20.25–43.75 | Median wage; Job Bank/LFS |
| Quebec: database analysts/data administrators | NOC 21223 | 2023–2024 | CAD | 43.96 | 22.00–55.00 | Median wage; Job Bank/LFS |
| U.S.: data entry keyers | SOC 43-9021 | 2025 | USD | 19.88 | — | Median wage; BLS through O*NET |
| U.S.: bookkeeping/accounting/auditing clerks | SOC 43-3031 | 2025 | USD | 24.36 | — | Median wage; BLS through O*NET |
| U.S. private industry: office/admin | Broad group | December 2025 | USD | 35.96 | — | Mean total compensation; BLS ECEC |
| U.S. private industry: professional/related | Broad group | December 2025 | USD | 72.19 | — | Mean total compensation; BLS ECEC |
| EU, covered economy | All occupations | 2025 | EUR | 34.90 | — | Mean employer labor cost; Eurostat |
| Netherlands, covered economy | All occupations | 2025 | EUR | 47.90 | — | Mean employer labor cost; Eurostat |
| Luxembourg, covered economy | All occupations | 2025 | EUR | 56.80 | — | Mean employer labor cost; Eurostat |
| Bulgaria, covered economy | All occupations | 2025 | EUR | 12.00 | — | Mean employer labor cost; Eurostat |
| Romania, covered economy | All occupations | 2025 | EUR | 13.60 | — | Mean employer labor cost; Eurostat |

Quebec estimates use Statistics Canada's 2023–2024 Labour Force Survey and were updated on Job Bank on 19 November 2025. Provincial LFS estimates are kept separate from regional Small Area Estimation entries. Job Bank low/high figures generally represent the 10th/90th percentiles, subject to exceptions; they are **not confidence intervals**. Its methodology excludes non-wage benefits. Statistics Canada's guide explains that LFS hourly wages derive from gross usual pay and usual hours; they are not employer expenditure or task-level effort. Sources: the three `jobbank_qc_*2025` records, `jobbank_methodology2026`, `statcan_wageguide2024`.

BLS ECEC Table 4 gives office/admin compensation as USD24.79 wages plus USD11.17 benefits, totaling USD35.96. The professional/related rate is USD50.10 wages plus USD22.09 benefits, totaling USD72.19. These are December 2025 private-industry group averages, published 20 March 2026; broad compensation is not an occupation-specific quote, service billing rate or all corporate overhead. Source: `bls2025ecec` in the original bibliography.

Eurostat's 31 March 2026 publication covers enterprises with at least ten employees, including apprentices, in NACE B–N and P–S. Agriculture, public administration, household employment and extraterritorial bodies are excluded. Estimates generally extrapolate the 2020 Labour Cost Survey using the Labour Cost Index; documented national exceptions apply. Costs include wage and non-wage expenditure less subsidies. Eurostat itself uses annual exchange rates to publish EUR values; this study applies no additional exchange-rate conversion. Source: `eurostat2025labourcost` and its methodological companion.

ILOSTAT explicitly distinguishes employees' earnings from employers' labor costs. Its earnings definition excludes employers' social-security and pension contributions. This supports the cost-basis labels here; it does not supply an occupation-matched global hourly rate. Source: `ilostat_wagedefinitions`.

## Reproducible break-even calculation

Let `w` be the source hourly rate, `l` an explicitly assumed employer load if the source is wage-only, `h` the human workflow's total effort in minutes, and `C_A` the system's complete cost per accepted deliverable in the same currency. Then:

`C_H = w × l × h / 60`; `h* = 60 × C_A / (w × l)`.

The traditional workflow is more expensive when its observed total effort exceeds `h*`, subject to the same acceptance standard. This simple model treats all human minutes at one valuation rate. Different worker and supervisor rates should be entered separately when known. Rejected outputs, correction, rework and abandoned attempts must enter the respective accepted-delivery cost rather than disappearing from a successful run's denominator.

`C_A` is **not yet measured in this module**. The reproducible grid uses assumptions of 1, 5, 10 and 25 units of the applicable currency, inclusive of model use, compute, execution, setup, verification, retries, maintenance, capability-construction allocation and employer attention. CAD5, USD5 and EUR5 are three independent assumptions, not an FX conversion or equal purchasing-power claim. Unknown actual costs are never set to zero.

### Required traditional effort, minutes

These are computed thresholds at the published central rate without an additional wage load. They are **not measured human times**.

| Rate case | Full system cost 5 | Full system cost 10 | Full system cost 25 |
|---|---:|---:|---:|
| Quebec data entry, CAD24.00/h | 12.50 | 25.00 | 62.50 |
| Quebec bookkeeping, CAD28.02/h | 10.71 | 21.41 | 53.53 |
| Quebec database analyst, CAD43.96/h | 6.82 | 13.65 | 34.12 |
| U.S. data entry, USD19.88/h | 15.09 | 30.18 | 75.45 |
| U.S. bookkeeping, USD24.36/h | 12.32 | 24.63 | 61.58 |
| U.S. office/admin compensation, USD35.96/h | 8.34 | 16.69 | 41.71 |
| U.S. professional compensation, USD72.19/h | 4.16 | 8.31 | 20.78 |
| EU covered economy, EUR34.90/h | 8.60 | 17.19 | 42.98 |
| Netherlands, EUR47.90/h | 6.26 | 12.53 | 31.32 |
| Luxembourg, EUR56.80/h | 5.28 | 10.56 | 26.41 |
| Bulgaria, EUR12.00/h | 25.00 | 50.00 | 125.00 |
| Romania, EUR13.60/h | 22.06 | 44.12 | 110.29 |

The full sensitivity grid varies human effort over 5, 15, 30, 60 and 120 minutes. Wage-only sources receive separate load assumptions of 1.00, 1.15, 1.30 and 1.50; these multipliers are scenario parameters, not measured benefit rates. No extra load is applied to published compensation or employer-cost series. The script produces 108 thresholds and 540 cost comparisons, including unfavorable combinations. For example, a hypothetical thirty-minute U.S. office/admin workflow costs USD17.98 under this rate: an all-in USD5 system scenario yields modeled USD12.98 capacity value and a 3.596 cost ratio, while USD25 yields a modeled USD7.02 disadvantage. Neither scenario is an empirical claim about this portfolio.

## Attention and retained capability

Attention needs its own operating limit. If `K` is all allocated system cost excluding employer attention, `r` is remaining employer attention in minutes, and `w_r` is its hourly valuation, then `C_A = K + w_r × r / 60`. The maximum attention that preserves a cost advantage is:

`r_max = (w × l × h − 60 × K) / w_r`.

When worker and reviewer rates coincide, `r_max = h − 60K/(w × l)`. A negative result means the non-attention cost already exceeds the modeled human alternative. With an assumed thirty-minute U.S. office/admin task and `K=USD5`, the threshold is 21.66 review minutes. This is a scenario limit, not a recommendation to consume that much attention or evidence that attention was measured. `attention_tradeoffs.json` calculates this threshold with separate, labeled non-attention cost assumptions.

Reusable capability may lower allocated construction cost from `F/N` as accepted jobs `N` accumulate, while maintenance, verification and drift costs continue. Both human templates and system warm-up must be counted. Lower local execution time alone cannot establish lower complete service cost, nor does it establish increasing improvement rate. The paper's measured operational ledger should replace scenario parameters wherever defensible quantities become available.

## External human evidence and limits

The companion review in `../protocol_evaluator/historical_human_evidence.md` documents relevant primary studies. WREX (CHI 2020) includes professional data scientists performing short transformations manually with Jupyter and web access, with a five-minute censoring limit. TASHEEH (EDBT 2024) reports five experts repairing ten malformed CSVs, 67 ±18 minutes and 83 ±17% accuracy, but unrestricted tools and a different acceptance contract. SpreadsheetBench reports four experts' spreadsheet quality without task-level times. These establish useful adjacent practice, not a matched timing denominator for this reconciliation portfolio. Do not divide a batch mean by file count, a one-day evaluation by instructions, or transfer a mixed-desktop median to manufacture a human completion time.

## Commercial interpretation

At a given full delivery cost, higher-value and longer jobs have more room for review and integration. Short, low-wage workflows can lose money even when local code runs quickly. The profitable region must therefore be identified by accepted deliverables, total attention, failure and rework frequency, and recurring demand. The sourced wage gradients make this conclusion inspectable without claiming universal superiority.

The model values released employee capacity. Cash savings require an actual change in overtime, outsourcing, staffing, procurement or another cash outflow. Provider price, provider revenue, operating cost and profit are distinct; a customer's avoided wage expenditure is not automatically any one of them. The global USD40 trillion opportunity remains the illustrative scenario audited in the original notes, independent of these job-level thresholds.

## Reproduction and provenance

Run `python3 compute_human_benchmarks.py` and `python3 compute_attention_tradeoffs.py` in this directory. Both use only the Python standard library. Inputs are frozen in `human_market_benchmarks.json`; outputs and source register are hashed in `BENCHMARK_SHA256SUMS.json`. Decimal arithmetic is used before four-place output rounding. `human_benchmark_sources.bib` extends the original `economics_sources.bib`; do not discard the original BLS and global-market citations.

Job Bank canonical page opens intermittently timed out. Rates were verified in official indexed Job Bank content through both search systems, including full provincial tables; the source register records this extraction path. Other sources were directly opened. No claim is made that a complete raw website snapshot or private participant record was downloaded.
