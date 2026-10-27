# Frontier-model calibration and conditional economics

Retrieved 2026-10-27. This is a research-design note, not evidence of customer delivery or API entitlement. Scope: six opened official source pages; no paid API calls. Presence-only environment inspection found the OpenAI SDK installed and no `OPENAI_API_KEY` or `OPENAI_BASE_URL`. No secret value was read or printed. The host's agent execution is available, but its API billing, model request configuration and per-task token receipts are not observable through that check.

## Current verified identifiers and configurations

| Role | Current official identifier | Standard USD / million uncached input / output / cached input | Reasoning effort | Official context / output ceiling |
|---|---|---|---|---|
| Demanding reasoning, invention, verification | `gpt-6-astra` | 10 / 50 / 1 | low, medium, high, xhigh, max | 1,050,000 / 128,000 tokens |
| Visual reasoning and computer use | `gpt-6.1-terra` | 1 / 5 / 0.05 | none, low, medium, high, xhigh, max; medium default | 1,050,000 / 128,000 tokens |
| Cost/quality comparator | `gpt-6.1-sol` | 2 / 10 / 0.10 | low, medium, high, xhigh, max; medium default | 1,050,000 / 128,000 tokens |

Sources: O1/O2 for Astra and Terra, O3/O4 for prices and Sol. The catalog/model pages support text and image inputs, text outputs, structured outputs and tool use; Astra and Terra explicitly list computer use, hosted shell, code interpreter, MCP and tool search. Astra and Terra fine-tuning is not supported. Tool calling for these models requires Responses. Do not equate a tool-support flag with a provisioned browser, credentials or a working application integration.

For Astra and Terra, a request exceeding 272,000 input tokens doubles input/cache prices and multiplies output prices by 1.5. Standard 30-minute cache writes cost 1.25 times ordinary input; the pricing table lists 12-hour writes at 2.5 times input. Batch/Flex prices are half Standard and Fast prices double Standard. A bounded primary simulation should use Standard, <=272K prompts, no cache benefit unless reuse is modeled and its writes counted. Long-context and Fast multipliers are separate stress cases. O1/O2/O3.

Published Astra and Terra tiers are Build: 5,000 RPM and 1,000,000 TPM; Launch: 10,000 RPM and 4,000,000 TPM; Grow: 15,000 RPM and 40,000,000 TPM. Free is unsupported. These are advertised tier limits, not this user's assigned tier. The pages show the unversioned identifiers above, not a dated immutable snapshot. Preserve retrieval date and exact response model when live access exists; do not claim a historical alias guarantees immutable model weights. O1/O2.

API token and tool tariffs are not acceptance probabilities, end-to-end latency measurements, engineering time or total production cost. O5 states that screenshot-based operation incurs image-input tokens and environments may have separate charges. O3 lists web search at USD 10/1,000 calls plus retrieved content tokens, and hosted-shell/code-interpreter container sizes at USD 0.03/0.12/0.48/1.92 per 20-minute session for 1/4/16/64 GB. Use actual usage when available; otherwise expose these as tariff-calibrated modeled workloads. Do not bill this host's connector search as an observed OpenAI API charge.

The official GPT-6 guide describes pro mode as additional model work whose aggregate tokens are billed at the chosen model rates. This is a request execution setting; neither `ChatGPT Pro` nor `Astra Pro` is a substitute API slug. The subscription is not evidence that the project can make API calls. A pro workload multiplier is unknown until measured. O6.

## Recommended bounded primary model

Use a deterministic technical kernel for the actual executable artifact and label that result `executed_computation`. Use a separate parameterized model for semantic interpretation, correction effort and adoption. Freeze the kernel and protocol before fresh tasks. Never take the kernel's success as a measured Astra/Terra success rate.

Use the same documented model tariff and potential tool access in U, E and E+. No U degradation by removing tools or using a weaker model. H is an equivalent human service reference with the same useful acceptance boundary and residual customer duties. If U/E model trials cannot run, put their success, cost and latency parameters on a grid that includes equality, negative transfer and plausible positive gains. A prompt rubric can characterize method design; it cannot set q_E > q_U.

Suggested small grid, all explicit assumptions rather than literature-derived performance: baseline first-pass acceptance q_U in {0.60, 0.80, 0.95}; expert change q_E-q_U in {-0.05, 0, 0.05, 0.10}, clipped to [0,1]; retained-capability incremental effect q_E+-q_E in {-0.05, 0, 0.05}. Workload multipliers {0.5,1,2,4} and retry/correction costs supplied independently. If the artifact yields observed exact computation savings, use those measured operations/time only for that component. No selection of the most favorable cell as an empirical result.

Prefer an analytical threshold surface over thousands of stochastic histories when the causal question is scalar. Add only enough Monte Carlo to exercise correlated failures, withdrawal, defaults and liquidity; draw the same world for compared enterprise configurations. Report conditional uncertainty inside one chosen world model separately from the range across unvalidated assumption sets. More simulation worlds do not reduce uncertainty about buyer willingness to pay or model competence.

## Accounting and break-even equations

For each attempted job j under configuration k, retain: delivered artifact/version, technical acceptance, semantic acceptance, deadline, customer effort, all attempts, tools, token workload, paid human work, support, cash collections, refund liabilities, and time of every cash event. `A_jk` is complete job delivery including learning needed to finish that outcome. `B` covers only additional reusable-candidate assessment, rights clearance, admission, distribution and upkeep. `C` covers discretionary extra R&D or Gym. Give every expense one ID and one A/B/C label. Failed candidates and rejected admissions still cost money. Never move A learning into B and charge it twice.

Let q_k be joint useful acceptance probability (quality, deadline and customer effort), p selling price, d noncollection probability conditional on acceptance, and a_k expected complete cost per attempted job including failures and retries. Then, under payment-on-acceptance and no additional liabilities, expected contribution is q_k*p*(1-d)-a_k. If payment is upfront, separately track deposits as liabilities and recognize earned revenue only after the contractual acceptance/refund boundary. Do not subtract both the gross refunded amount from recognized net revenue and from costs.

At identical price/default assumptions, the expert-workflow break-even improvement is:

`q_E - q_U > (a_E - a_U) / (p*(1-d))`.

This is useful even when q is unmeasured: it states the improvement the next trial must show. If a_E <= a_U, better workflow may be worthwhile at equal acceptance; if a_E > a_U and the threshold exceeds 1-q_U, it cannot pay in that envelope. At matched accepted quality, compare `a_k/q_k`, provided q_k > 0 and acceptance definitions coincide. Matched token/time budgets and matched accepted-quality costs answer different questions and should be reported separately.

For retention, let g_t be additional expected recipient contribution versus its competent E baseline, n_t usable opportunities before obsolescence, m_t additional maintenance cost, and B0+C0 new investment. Retain only if evidence available then supports:

`sum_t [n_t*g_t - m_t]/(1+r)^t > B0+C0`,

subject to current scope/identity/rights qualification, cash sufficiency, risk tolerance and attainable validation. Supplied expert tools and all recipient capabilities remain in the E baseline. If the recipient can obtain the same instrument freely and cheaply, g must reflect only actual incremental integration/reuse benefits, not ownership of a common algorithm. Ordinary-library distribution with identical content and permissions should tie unless graph structure actually changes retrieval or composition costs.

A one-period break-even reuse count is `ceil((B0+C0+maintenance)/(g_per_use))` when g_per_use > 0; if g <= 0, refuse retention rather than simulate compulsory investment. Report both the incremental decision and total historical research expenditure. Unknown actual research cost remains unknown, even if a modeled operating enterprise is profitable.

## Arrangement experiment

Test a 2x2 mechanism table: ordinary/constructed capability crossed with individual/coordinated demand. Both baseline organizations may propose the same contingencies, conventional tools and outside options. Shared construction must solve an actual fixed-cost or information bottleneck; mere enrollment cannot be credited with technical success.

A transparent assurance arrangement is a conditional order with buyer-specific outcomes and acceptance. Each participant chooses the offered contract, the human outside option, deferral or nonparticipation. Shared R&D proceeds only if enforceable commitments/prefunding meet a declared threshold. Conditional offers are modeled contracts, not collected cash. Buyer i participates only if expected useful benefit minus expected payment, adaptation effort, failure exposure and delay cost exceeds the outside option; values and participation must remain hypotheses without customers.

Stress withdrawal before construction, withdrawal after sunk setup, payment default, partial accepted delivery, common capability failure, heterogeneous incompatibility and support obligations. A shared Bernoulli common shock with probability rho, followed by conditional per-buyer failures, is enough for a minimal correlated-risk model. Do not use independent failures alone to claim diversified safety. Track capacity jointly across paid delivery, development, integration and servicing; preparation can displace revenue and carry into later periods.

Cash is time-ordered: `cash_t = seed + deposits + earned collections - expenses - refunds`. Available unrestricted funds are cash less refundable deposits, committed unpaid obligations and reserves. Deposits may fund construction only if the contract permits it and all associated liability remains visible. Minimum extra financing is the maximum cumulative shortfall over the trajectory. Expected profit can be positive while financing is infeasible. Buyer savings, token issuance and hypothetical surplus are never collections. Applicable AGIALPHA utility is a separate activity.

## Smallest next live trial

Once the domain is selected, recruit one real beneficiary who supplies a complete mission and acceptance conditions; run U/E/E+ on matched unfamiliar tasks under the same model and permissions; collect token/tool/latency/correction and customer-effort receipts; compare against a scoped human quote; ask for a binding order or paid pilot only after the artifact's useful output is reviewable. A pilot need not prove universal competence. If no buyer is available now, deliver the thresholds and simulated contract ledger rather than claiming no result is possible.

## Source register and short evidence excerpts

O1. OpenAI, GPT-6 Astra Model. https://developers.openai.com/api/docs/models/gpt-6-astra ; opened 2026-10-27. Short excerpt: "Prompts with more than 272K input tokens". Retrieval refs: turn2view0, turn6view0, turn5view0. Supports model ID, context, output, effort, tools, tier limits and long-context multiplier. Limit paraphrase to facts needed; parent must open itself before using these refs in final citations.

O2. OpenAI, GPT-6.1 Terra Model. https://developers.openai.com/api/docs/models/gpt-6.1-terra ; opened 2026-10-27. Short excerpt: "Tool calling requires the Responses API." Retrieval refs: turn2view1, turn6view1, turn5view3. Supports Terra ID, visual/computer-use role, effort, pricing, constraints and tier limits.

O3. OpenAI, API Pricing. https://developers.openai.com/api/docs/pricing ; opened 2026-10-27. Short excerpt: "Prices per 1M tokens." Retrieval refs: turn2view2, turn6view3. Supports exact tariffs and tools; prices are not this study's observed charges.

O4. OpenAI, Compare models. https://developers.openai.com/api/docs/models/compare ; opened 2026-10-27. Short excerpt: "Near-Astra performance for complex work at a lower cost." Retrieval ref: turn2view5. Supports Sol model price/specification comparator. Vendor capability description is not independent domain validation.

O5. OpenAI, Computer use. https://developers.openai.com/api/docs/guides/tools-computer-use ; opened 2026-10-27. Short excerpt: "Screenshots count as image input." Retrieval ref: turn2view3. Supports screenshot/environment cost distinction and need to verify project access.

O6. OpenAI, Using GPT-6. https://developers.openai.com/api/docs/guides/latest-model ; opened 2026-10-27. Short excerpt: "Those tokens are billed at the selected model’s standard token rates." Retrieval refs: turn2view4, turn6view2. Supports roles, Responses/tool requirement, context/effort caution and pro-mode distinction. The pro explanation appears in the preserved GPT-5.6 section; the GPT-6 section separately states support for pro mode. No live pro-mode behavior was tested here.

No empirical task-performance calibration is claimed. Current official product specifications calibrate cost and available mechanisms; task competence, latency, customer demand and residual human duties require domain evidence or explicit assumptions.
