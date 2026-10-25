# Human-work comparison: source and interpretation notes

Research lane frozen on 25 October 2026. Sixteen primary or primary-publication sources are registered in `evidence/source_ledger_human.json`; citation keys match `sources_human.bib`. The numerical occupation anchors below were freshly verified on official BLS pages. They use May 2025 data, which supersede the familiar May 2024 figures. These sources provide a market-data-grounded comparison without pretending that occupational salaries establish task durations.

## Rate anchors

| Deliverable family | U.S. occupation | May 2025 median annual wage | Wage/2,080 hours | Benefit-loaded scenario |
|---|---|---:|---:|---:|
| Tested software repair/release | Software developers | $135,980 | $65.38/h | $93.40/h |
| Source-backed document production | Technical writers | $90,390 | $43.46/h | $62.09/h |
| Operational dataset reconciliation | Bookkeeping/accounting/auditing clerks | $50,670 | $24.36/h | $34.80/h |
| Dependency-aware planning | Operations research analysts | $88,940 | $42.76/h | $61.09/h |

Sources: `bls_software_2025`, `bls_writer_2025`, `bls_bookkeeping_2025`, `bls_operations_2025`. Rates are nominal USD, U.S. national employee medians. They are neither contractor quotes nor collected customer prices. Population AI use is not identified. The intended comparator is a competent human using ordinary non-AI tools; the wage sources do not verify that their sampled workers avoided AI.

BLS uses 2,080 hours for its full-time year-round annual-wage convention (`bls_oews_method`). June 2026 private-industry ECEC reports $32.82 wages and salaries plus $14.07 benefits, totaling $46.89 per hour worked (`bls_ecec_2026q2`). The ratio is **1.4287020109689215**. Applying it to occupation medians is a transparent cross-population scenario, not a measured occupation-specific compensation rate. Wage-only is a conservative lower anchor; 1.25, 1.4287 and 1.60 multipliers can be sensitivity cases. The 1.25 and 1.60 factors are assumptions. Ordinary software, office and management costs are separate lines; do not silently treat the benefit factor as every employer overhead.

Paid leave is already part of ECEC benefits. Do not add another paid-leave adjustment without reconciling its denominator. Actual productive hours, self-employed service prices and task-specific overhead remain unknown here. Mixing a median wage and mean compensation ratio is an estimate and must stay labeled accordingly.

## Two different break-even questions

Let `W_h` be a stated human hourly-cost scenario and `C_A` complete Agent cost per accepted deliverable, including the allocation of failed attempts. The production-cost break-even is:

`human_minutes_required = 60 * C_A / W_h`.

For the customer, the relevant alternative is the price actually payable plus the customer's remaining work and switching costs:

`customer_break_even_minutes = 60 * (price + customer_review_hours * customer_rate + switching_cost) / W_h`.

Customer savings are the human alternative cost less this all-in purchase cost. Enterprise revenue is collected customer proceeds. Neither equation lets the enterprise retain the entire savings unless a price and actual collection support it. A low internal cost can coexist with an unattractive customer offer, and a low price can coexist with enterprise losses.

A sensitivity grid of 5, 15, 30, 60, 120 and 240 human minutes is useful. Every point is an assumption, not a sourced completion time. If the task has multiple revisions or failure, use expected human effort per accepted deliverable. Do not compare the Agent's first successful kernel execution with the entire human occupation, or infer human quality from wages. A win is conditional on matched acceptance and a credible human time above the displayed threshold. A failure or unsupported scope remains a loss or unmeasured category, even if a simulated cost looks low.

The ordinary-tool baseline includes existing spreadsheets, scripts, solvers, document templates and test frameworks. A competent human need not manually enumerate a scheduling problem or retype a dataset when a conventional specialist already handles it. Reuse of these specialists inside AGI ALPHA is sensible, but does not by itself establish a uniquely valuable capability or customer willingness to pay.

## Scope and geography

O*NET maps the four families to recognized activities: software modification/testing; recording and checking numerical records; technical material and revision production; and optimization for time/cost/logistics decisions (`onet_software_2026`, `onet_bookkeeping_2026`, `onet_writer_2026`, `onet_operations_2026`). This supports relevance of task selection. It establishes neither universal occupational coverage nor task duration.

ILOSTAT distinguishes earnings from employer labour costs and explains cross-country harmonization (`ilostat_wages_method`). The study should preserve country, year, currency and population before combining any estimates. Its definitions do not supply an estimate of global keyboard-and-screen work.

Eurostat estimates 2025 hourly labour costs of EUR34.9 for the EU and EUR38.2 for the euro area, with specified activity exclusions (`eurostat_labour_2025`). These averages include wage and non-wage costs. They provide international context only and are not substituted for U.S. occupational rates.

Job Bank's technical-writer figures provide a Canadian crosscheck: CAD39.85/h median in Montreal (2024 Small Area Estimation), CAD41.54 in Quebec and CAD36.06 nationally (2023–2024 Labour Force Survey); wages were updated 19 November 2025 (`jobbank_writer_2024`). They are wages, not total employer costs. Keep them in CAD; no currency conversion is performed in this lane. The canonical URL intermittently failed, but the official returned indexed URL opened and supplied the period and methodology.

The user's U.S. **$5–10 trillion/year** digital-labour interval is an explicit compensation/computer-use scenario. This study does not independently estimate that interval. It must not become obtainable revenue, existing demand, universal service coverage or a global total. No supported U.S. $40 trillion claim is made. Scale analysis should grow from accepted orders, prices, collections and binding capacity limits.

## Relevant empirical literature and limits

Noy and Zhang's final 2023 journal abstract reports a randomized professional-writing experiment with 453 participants, 40% lower completion time and 18% higher assessed quality with ChatGPT (`noyzhang2023`). This is historical assistive writing evidence. The accessible earlier MIT manuscript uses 444 participants; do not blend its version with the final abstract. The journal full-text fetch was blocked, while its primary search abstract and academic abstract page agreed. None of its effect sizes calibrates this study's workflow durations.

Becker and colleagues' pinned arXiv v2 reports 16 experienced open-source developers completing 246 tasks with randomized AI availability; AI use increased completion time by 19% (`becker2025`). It concerns familiar mature codebases and early-2025 tools. Preserve this losing comparison as evidence that review and integration can outweigh code-generation benefits, without treating it as a verdict on every digital service or on current tools.

Brynjolfsson, Li and Raymond's arXiv v2 reports 5,172 support workers and a 15% average productivity gain from an assistive deployment, with heterogeneous effects (`brynjolfsson2024`). It motivates studying retained methods and differences across workers; it does not establish autonomous operation. Customer support involving private personal data remains outside the present permitted scope. Version 1 used different figures; the v2 citation is deliberate.

These studies establish that measured effects vary with task and deployment. They neither prove AGI ALPHA's present advantage nor substitute for this study's observed deliverables. Use them to motivate full workflow accounting and scope discipline, while keeping the human-work commercial comparison primary.

## Claim discipline for the publication

- Classify observed execution, externally sourced wage inputs, estimated operating costs and assumed price/demand separately.
- Report benchmark thresholds alongside measured deliverable quality and unresolved human timing.
- Describe the $0.50 Agent / $200 human example as a hypothesis. Salary tables and a fast deterministic kernel establish neither number.
- Preserve real costs of adaptation, supervision, corrections, failed construction and maintenance.
- Mark business revenue, surplus and financing coverage as modeled until genuine external collection records exist.
- The independent source lane is a separate agent in the same session, sharing tooling and model lineage. It is not external peer review or organizational independence.
