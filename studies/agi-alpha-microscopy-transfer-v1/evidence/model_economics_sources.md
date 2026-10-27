# Official model and economic reference dossier

Prepared 2026-10-27 for the additive AGI Alpha Flywheel research edition. This is research support, not a claim of measured API cost, customer demand, contracted service price or realized profit.

## 1. Verified model identifiers and capabilities

The official pages were searched and opened on 2026-10-27. Current documented models fit the intended roles: `gpt-6-astra` for demanding reasoning, and `gpt-6.1-terra` for visual interpretation and computer use. Astra also supports computer use, so this allocation is a design choice, not a model restriction. Both document 1,050,000-token context and 128,000 maximum output. Astra reasoning efforts are `low`, `medium`, `high`, `xhigh`, `max`; Terra additionally supports `none`, with `medium` its documented default. Terra tool calling requires the Responses API. Astra fine-tuning is not supported. The pages show aliases, not an immutable dated snapshot that we can independently verify.

Primary URLs (opened, not merely search snippets):

- https://developers.openai.com/api/docs/models/gpt-6-astra — model, capability and Astra price source; refs turn2view0 / turn3view1.
- https://developers.openai.com/api/docs/models/gpt-6.1-terra — Terra model, tool interface and rates; refs turn2view1 / turn3view2.
- https://developers.openai.com/api/docs/guides/tools-computer-use — browser/desktop integration and driver responsibilities; refs turn2view3 / turn7view4.
- https://developers.openai.com/api/docs/guides/latest-model — current model selection/effort guidance; search ref turn1search4; root should open if citing.

Do not infer that the study exercised every documented capability. A native session's exposed model label is evidence of configured identity; it does not provide API billing, an immutable backend weight version, or a guarantee of repeatability. Explicitly separate hosted same-model trials from independently billed API experiments.

## 2. Current price anchors

USD per million text tokens, Standard mode and input length at most 272,000 tokens:

| Identifier | Input | Cached input | Output | 30-minute cache write | 12-hour cache write |
|---|---:|---:|---:|---:|---:|
| gpt-6-astra | 10.00 | 1.00 | 50.00 | 12.50 | 25.00 |
| gpt-6.1-sol | 2.00 | 0.10 | 10.00 | 2.50 | 5.00 |
| gpt-6.1-terra | 1.00 | 0.05 | 5.00 | 1.25 | 2.50 |
| gpt-6-luna | 0.10 | 0.01 | 0.50 | 0.125 | 0.25 |

Primary pricing page: https://developers.openai.com/api/docs/pricing (refs turn2view2 / turn3view3 / turn7view3). For Astra/Terra, prompts above 272k are priced at 2x input/cache and 1.5x output over the full request. Batch/Flex are 50% of Standard; Fast is 2x. Do not select a discounted mode in the simulator without respecting its latency/availability. Regional processing can add 10%. Web search is $10/1,000 calls plus model-priced search content. Container example: 1 GiB is $0.03 per 20-minute session; larger containers and session details differ. These anchors are source facts; their use as this study's cost is a modeled assumption unless usage is actually metered on the same billable service.

For a simple no-cache, short-context scenario, 100k Astra input and 20k output cost $2.00 in token charges; the same Terra workload costs $0.20. This arithmetic excludes tools, retries, failed attempts, model-invisible preparation, hosting and human obligations. It is not an invoice for this research session. A complete estimate uses the provider's actual mutually exclusive billable categories and avoids counting cache-write tokens twice.

ChatGPT Work/Codex billing is separately documented at https://learn.chatgpt.com/docs/pricing (opened through https://developers.openai.com/codex/pricing; refs turn2view4 / turn3view4). The page distinguishes subscription/credit usage from API-key access; API availability follows the key and usage follows API pricing. This session's subscription does not authorize an external API purchase. Work credits are not converted into money without the actual plan's credit purchase price and usage record.

## 3. Human-service market reference H

Rates are a starting point for a scope-matched reference. No source below establishes how many hours the selected new deliverable takes, buyer willingness to pay for this study's artifact, or its equivalence to licensed engineering services.

### Canadian engineering services

ACEC-BC, 2026 Consulting Engineers Fee Guideline:
https://acec-bc.ca/wp-content/uploads/2025/11/2026_ACEC-BC_Fee-Guideline_FINAL_web_v1.pdf
Opened PDF refs turn6view0 / turn12view0. Page 6 of the PDF specifies Canadian dollars per charge-out hour. Recommended engineering rates E1–E7 are 176, 210, 243, 295, 327, 373, 416; technical T1–T7 are 151, 176, 202, 225, 244, 262, 290. E3 is independently responsible project engineering; E4 includes specialized complex engineering. These are association recommendations, not salaries or accepted quotes. The guideline excludes some specialty/risk premiums and describes separate disbursements. Use a relevant role and explicitly assumed task hours; keep currency CAD unless an actual dated exchange source is added.

### US geospatial engineering/data work

KCI Technologies' Texas DIR service rate card:
https://texassolutions.kci.com/pricing/
Opened refs turn6view1 / turn12view1. Scope covers geospatial analysis/spatial data science, planning and deployment, collection/conversion/integration. Selected posted hourly list rates: Data Analyst $120, Solutions Analyst $135, Solutions Engineer $160, Senior Software Engineer $185, Project Manager $195, Subject Matter Expert $300. Each listed KCI row has 5% DIR discount. This is posted US vendor contract pricing, not proof a general buyer receives that discount. Currency is interpreted as USD from the US procurement context; the displayed cells use dollar signs. Do not substitute salary. Earlier tentative $145 GIS-analyst suggestion was not verified and is withdrawn.

### US analytical consulting

UTEP Data Analytics Laboratory:
https://www.utep.edu/science/data-analytics-lab/services.html
Opened ref turn6view2. Approved rates effective 2026-08-10: external analyst $190.31/hour, external data manager $246.03/hour, external bioinformatics/health informatics $236.66/hour, computational equipment $3.52/hour. The stated service scope spans study design, preparation, analysis, interpretation and report support. The dollar currency is interpreted as USD from the US university context. Select only a comparable service and model residual work explicitly.

### Life-science-specific alternatives

Harvard Chan Bioinformatics Core:
https://hsph.harvard.edu/research/bioinformatics/consulting/
Opened refs turn6view3 / turn7view2. FY26 external academic $193/hour, industry $265/hour. Computing/basic storage and technical expenses are included; person-time billing includes communications/meetings, minimum increments 15 minutes. Work includes high-throughput analysis and custom methods; these rates do not price unrelated engineering services. USD inferred from US context.

Ottawa Bioinformatics Core Facility:
https://ohri.ca/en/who-we-are/core-facilities-and-platforms/bioinformatics
Opened ref turn6view4. Current official page lists internal $95/hour, external academic $130/hour, industry $150/hour; an older marketplace result showed lower amounts, so discard that stale secondary result. Canadian currency is plausible but not expressly stated in the opened rates block; do not use for cross-currency arithmetic without confirmation.

## 4. Complete accounting design

Store each cost once using an immutable cost_id, purpose category, job_id/capability_id, event time, resource units, currency, cash/opportunity status, and evidence type. Evidence types should be individually assigned: observed, sourced, calibrated, assumed, simulated, unknown. Unknown actual amounts remain null; they do not become zero.

- A: all resources necessary for a paid outcome, including intake, original construction/learning, failed attempts, retries, adaptation, verification, correction, customer support and delivery. If the originating artifact is required to deliver the contracted output, its construction is A, even if reusable later.
- B: additional screening, admission, provenance/rights checks, packaging for reuse, sharing, revalidation and upkeep beyond A. Include rejected candidates. Do not re-charge original paid construction.
- C: optional additional Gym or R&D not needed for the original accepted job. Include failed practice and abandoned routes. Unpaid research is C or separately disclosed research expenditure, not customer-funded A.

Separate resources from their opportunity costs. Human charge-out reference H is not the enterprise's internal wage cost. A saved minute creates a cash saving only if avoidable paid expense is reduced; capacity value additionally requires unmet demand and a feasible schedule. Do not add both saved wages and the same saved capacity value. Buyer effort is part of equivalent utility/acceptance and an explicit economic burden, not fictional enterprise revenue.

Revenue and cash need distinct events. A quotation, hypothetical buyer value, token issuance, seed equity and customer savings are not earned revenue. A refundable deposit increases cash and refund liability together. Only earned milestones reduce that liability. A receivable after accepted delivery is not cash until collection. Bad debt reduces collectible value; avoid counting an unpaid amount as a refund also.

At time t:

cash[t] = cash[t-1] + actual_collections[t] + actual_financing[t] - actual_disbursements[t] - actual_refunds[t] - financing_repayments[t].

available[t] = cash[t] - unearned_refundable_deposits[t] - unpaid_committed_obligations[t] - reserve[t].

Report opening capital, gross collections, earned revenue, delivery cash expense, incremental B/C expense, opportunity cost, outstanding receivables, refund/other liabilities, ending cash and available funds. Keep normal accounting profit distinct from the study's settlement-adjusted contribution. A positive expected surplus can coexist with a negative minimum available balance. Do not let expected future earnings fund an earlier commitment.

Model common failure and conditional defaults with shared world variables rather than independent Bernoulli draws when they plausibly correlate. Buyer participation is chosen from a utility comparison that includes outside options, own effort, delay, price and a declining/no-buy option. Test withdrawals before construction, after shared construction but before delivery, partial accepted milestones, deadlines, provider failure, refund obligations, default, support load and demand collapse. Set counterfactuals to the same buyer world, data, tool access, resource capacity and permissible arrangements.

## 5. Analytical break-even conditions

For a simple homogeneous job with price P, acceptance probability q, accepted-invoice default probability d, collection fee fraction f, and expected complete delivery expense a, expected settled contribution is q(1-d)P(1-f)-a. This formula assumes no earned partial delivery; a fuller event model should supersede it when needed.

With an incremental reusable method, unchanged price/default/fee and N realized future uses, incremental expected value is N[(q_plus-q)P(1-d)(1-f) - (a_plus-a)] - B - C - upkeep. Therefore the minimum acceptance gain is [delta_a + (B+C+upkeep)/N] / [P(1-d)(1-f)]. If N is uncertain, integrate over demand and eligibility, including N=0. If this threshold exceeds feasible probability headroom 1-q, the admission rule is structurally unreachable; reject or change costs prospectively rather than repeatedly assessing it.

At matched accepted quality, substitute complete marginal savings per accepted delivery for probability uplift. Report E versus U and E+ versus E separately. If a competent recipient already owns an equivalent method, its transfer advantage is zero unless measured evidence supports another difference. An identical-content ordinary library must receive identical skill bytes and permissions; any graph-specific claim needs an additional causal contrast.

An executable sensitivity grid should include no improvement, negative transfer, higher correction/customer effort, obsolescence, no reuse, weak demand, correlated failures, delayed collections, lower outside-option price and a low-cost skilled-human alternative. Fixed price discounts or reinvestment shares are unnecessary: compare feasible choices under cash/resource constraints.

## 6. Proportionate real U/E/E+ experiment

Freeze ordinary prompt U, a short expert workflow E, retained artifact hash, task acceptance rules and budgets before fresh tasks. U should state the task competently and allow the same tools/docs/data; it should not omit indispensable requirements. E can add a small reusable process: verify semantics/units, select a competent method, construct output, test against requirements, correct failures, return provenance. E+ adds the real retained artifact or authorized service, with acquisition/loading/adaptation costs. A conventional-tool control should receive the discovered formulation explicitly where that isolates formulation from execution.

Use new context agents (fork none) with equal explicitly configured model/effort and the same tool permissions. Randomize or balance arm order. Run at least one unfamiliar mission whose answer was not used to build the artifact. Have another role curate acceptance, but call that role separation, not organizational independence. Shared filesystem access is not a hard secrecy barrier: document protocol isolation and avoid broad reads of protected answers. Do not give E+ special acceptance thresholds or easier tasks.

Record output files, hashes, actual tool calls/retries, elapsed wall time with start/end markers, failures and revisions, and available token/billing telemetry. If full tokens, reasoning tokens or invoices are absent, report them as unobserved. Equal tool-call and wall-clock ceilings are matched authorized envelopes, not proof of matched token spend. Historical inherited context makes all-context subagents unsuitable for a clean prompt comparison. A few repeated paired trials are a pilot; uncertainty and multiple tasks from one template must not be presented as independent population evidence.

## 7. Material reporting boundaries

Actual accepted technical outputs can be a positive accomplishment even if U/E/E+ tie, retention is rejected, or no buyers are observed. Technical conformance is not customer acceptance. Published prices calibrate a scenario, not sale evidence. Simulated revenue is never actual collections. This dossier does not claim real API trials, proprietary weight updates, live ENS authentication, settlement, production deployment, a positive commercial margin, or sustained compounding.
