# Source dossier: model configuration and opportunity anchors

Checked 2026-10-27. These are source observations, not evidence that an account can invoke a model or that any study customer bought a service. Sources were searched and opened; model statements below come from the opened official pages. The parent must open the cited URLs in its own web session before using their search reference IDs in final chat.

## 1. Current frontier configurations

| Model ID | Intended role in a competent study | Supported reasoning effort | Standard USD / million tokens: input, cached input, output | Limits |
|---|---|---|---|---|
| `gpt-6-astra` | Most demanding reasoning, invention, coding, independent review | low, medium, high, xhigh, max | 10, 1, 50 | 1,050,000 context; 128,000 maximum output |
| `gpt-6.1-sol` | Repeated complex coding and professional work | low, medium (default), high, xhigh, max | 2, 0.10, 10 | 1,050,000 context; 128,000 maximum output |
| `gpt-6.1-terra` | Visual interpretation and precise computer use | none, low, medium (default), high, xhigh, max | 1, 0.05, 5 | 1,050,000 context; 128,000 maximum output |

Sources (each an official model reference, retrieved 2026-10-27):

- https://developers.openai.com/api/docs/models/gpt-6-astra (web refs `turn1view0`, `turn2view2`, `turn2view3`, `turn2view5`). Astra supports Responses function calling, structured outputs, web search, file search, image generation, code interpreter, hosted shell, apply patch, skills, computer use, MCP, and tool search. Its fine-tuning feature is explicitly unsupported. The page lists `gpt-6-astra` as the snapshot identifier; it does not establish a dated immutable model snapshot.
- https://developers.openai.com/api/docs/models/gpt-6.1-sol (refs `turn1view2`, `turn3view1`). Tool calling requires Responses. Cache writes cost 1.25 times normal input. Prompts above 272,000 input tokens incur twice the input/cache and 1.5 times the output rates for the full request. Fast is twice Standard; Batch/Flex halve Standard; Ultrafast is six times Standard; eligible regional processing adds 10%.
- https://developers.openai.com/api/docs/models/gpt-6.1-terra (refs `turn1view1`, `turn3view0`, `turn2view6`). Tool calling requires Responses. Model page describes technical drawings, application-screen interaction, and photo comparison as suitable uses; these are provider capability descriptions, not measured superiority on our tasks.

All three model pages list free-tier access unsupported and published rate tiers: Build 5,000 requests/minute and 1 million tokens/minute; Launch 10,000 and 4 million; Grow 15,000 and 40 million. These published tiers do not prove the user's entitlement, current organization limits, permitted regions, or actual sustained throughput.

### Billing and tool-cost details

https://developers.openai.com/api/docs/pricing (refs `turn1view3`, `turn3view2`, `turn6view5`, `turn6view6`): current Standard rates above; 30-minute cache-write rates for Astra/Sol/Terra are $12.50/$2.50/$1.25, and 12-hour writes $25/$5/$2.50 per million tokens. Web search costs $10/1,000 calls plus search-content tokens; file search $2.50/1,000 calls and storage $0.10/GB-day after 1 GB free. Hosted shell/code interpreter container list prices are $0.03/$0.12/$0.48/$1.92 per 20-minute session for 1/4/16/64 GB. Eligible minute billing has a five-minute minimum. Fine-tuning is being wound down and is inaccessible to new users. No exact computer-use per-action fee was separately established by this retrieved pricing table; include environment and token costs rather than inventing one.

https://developers.openai.com/api/docs/guides/reasoning (refs `turn6view0`, `turn7view0`): `reasoning.mode` supports `standard` and `pro` for GPT-6 and is independent of effort. Pro performs additional model work and bills the aggregated tokens at the model's token rates. Reasoning tokens are output-billed and consume context/output limits. A call can terminate incomplete before producing usable text, so include unsuccessful calls and correction. Fair baseline comparison should evaluate model, effort, and mode rather than grant Alpha more inference resources.

https://developers.openai.com/api/docs/guides/tools-computer-use (refs `turn2view0`, `turn6view4`): a working system must connect the model loop to an execution environment, execute actions, return screenshots and verify the resulting application state. A model identifier alone is not an executable computer-use capability. The guide requires bounded runs and actual outcome checks. Use the same tool access and correction opportunities for baseline and specialist arms.

### Subscription versus API access

https://learn.chatgpt.com/docs/auth (refs `turn6view1`, `turn7view1`): subscription sign-in and API-key sign-in are separate access/billing paths. API-key usage is billed through the Platform account. This confirms that ChatGPT Pro is not a model ID or evidence of API-key entitlement.

https://developers.openai.com/siwc/quickstart (refs `turn6view2`, `turn7view2`): eligible open-source applications can request separately authorized Responses API scopes to use ChatGPT plans; commercial sign-in remains limited to selected partners. Identity-only scopes grant neither general API resources nor conversation access. Therefore do not claim there is categorically no subscription-backed programmatic route. Eligibility, scopes, limits and user authorization must be established for the actual application.

## 2. Primary human-service price anchors

| Source | Published service and price | Appropriate use | What it does not establish |
|---|---|---|---|
| SDSU Computational Science Research Center | External consulting $80/hour; scientific software/algorithm development, modeling, analytics, machine learning and HPC configuration included in scope | Conservative rate anchor for an explicitly estimated scientific-software engagement | Exact project hours, current capacity, a binding quote, willingness to buy our service |
| Purdue RCAC industry partnerships | Research software engineer consulting $26-$115/hour; external rates include F&A | Broad sensitivity range and evidence that industry-facing RSE/HPC consulting is offered | Comparable seniority across the range or a scope-matched project quote |
| ParaTools | Senior research scientist $249/hour unloaded, $412.97 loaded; individualized scientific-software performance analysis | High-skill sensitivity case for demanding profiling, parallel infrastructure and runtime optimization | Typical market median, recency of a particular quotation, or demand volume |
| Objective Experiments | $500/custom experiment design; $300/hour consultation; $2,800/on-site day | Concrete alternative service for experiment-selection and analysis deliverables | Physical experimental costs, simulator costs, a buyer's value for a new autonomous offering |

Opened URLs and refs:

- https://www.csrc.sdsu.edu/services/ (`turn5view2`, verified by system1 `turn9search0`). Do not substitute subsidized internal $75/hour for the external $80/hour rate.
- https://www.rcac.purdue.edu/industry (`turn5view1`). The page additionally lists HPC use cases including finite-element analysis, fluid dynamics, manufacturing and energy storage, plus GPU and storage charges. This is evidence of offered capacity and relevant application categories; it is not the study enterprise's compute invoice.
- https://www.paratools.com/consulting/ (`turn5view0`, verified by system1 `turn9search1`). Page was accessible on the check date but has no new explicit effective date; do not describe the rate as a newly issued October 2026 quote.
- https://objectiveexperiments.com/consulting/consulting/ (`turn5view3`). Deliverable scope includes experimental constraints, mixed factor types, use/augmentation of existing data, I-optimal or definitive-screening designs, and a written results report. Price is a vendor list offer, not a measured transaction.

Secondary candidate, not a preferred direct comparator: https://ese.ufhealth.org/our-services/ (`turn5view4`) explicitly lists FY26-27 $178.52/hour for custom development and maintenance, but serves UF/UF Health customers; it is an internal institutional price rather than an open commercial market price.

Recommended accounting wording: “The reference human price is estimated team hours times a sourced external service rate. Hours and achievable AI-selling price remain assumptions until scope-matched quotes and buyer trials exist.” Use local currency consistently and do not silently treat USD as CAD.

## 3. Focused portfolio hypotheses

These are study-design inferences, not sourced demand findings.

1. Scientific-software performance and numerical-correctness audit. Beneficiary: an engineering/research team with a costly repeated pipeline. Deliverable: reproducible profile, corrected/optimized code, independent correctness tests, regression envelope and deployment instructions. Specialization could matter when prior workloads teach a robust representation or algorithm selector. Falsifier: strong library or simple analytical reformulation matches gains, correction erases savings, or workload is too small to amortize assessment.
2. Experiment-design / simulator-calibration package. Beneficiary: a team deciding which expensive observations or simulator runs to purchase. Deliverable: frozen design/decision rule, executable optimizer, feasibility certificate, uncertainty diagnostics and results report. Strong baselines must include ordinary design-of-experiments, Bayesian/gradient methods where suitable and the same domain evidence. Falsifier: public conventional design already achieves equivalent decision quality inside the budget; a surrogate's numerical accuracy does not change decisions; distribution shift invalidates recommendations.
3. Constraint-preserving software transformation. Beneficiary: teams repeatedly adapting a scientific program or engineering pipeline. Deliverable: patch plus executable acceptance and counterexamples. Specialized representation or search can be material if it removes a recurring bottleneck while preserving all original semantics. Falsifier: ordinary compiler/search methods or a competent frontier workflow finds the same transformation on first delivery, or verification costs erase gains.

## 4. Research motivation with scope boundaries

https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/ (`turn9view1`), dated 2025-05-14: primary report of evolutionary code proposals coupled to automated evaluators. It reports deployed compute-efficiency and kernel improvements. It motivates executable algorithm search and strong verification, but supplies no measured performance for AGI ALPHA, no guaranteed transfer, and no commercial demand parameter.

https://www.ineffable.ai/ (`turn9view0`): David Silver's note dated 2026-01-15 and the company's mission describe discovering knowledge from environmental experience. Treat these as stated aims and research motivation, not demonstrated technical capability, affiliation, or evidence for our results. https://www.ineffable.ai/blog/nvidia-ineffable-intelligence-team-up-to-build-the-future-of-reinforcement-learning-infrastructure (`turn8search1`, search only; open before citing) describes a May 13, 2026 engineering collaboration for RL infrastructure. The latter is unnecessary for the present study's core claims.

## 5. Mandatory uncertainty labels for the paper

- Sourced: public model IDs, nominal prices, published limits, vendor service rates.
- Observed: only execution, measured resource use, learned artifact updates and independently checked outputs actually produced by the experiment.
- Assumed or simulated: token volumes if no API trace; frontier success/failure behavior; human task hours; buyer arrivals, trust, willingness to pay, collections; service invocation expenses not actually billed; account identities not live resolved.
- Unestablished: live API entitlement, live customer acceptance, earned revenue, autonomous specialist invention, live ENS authentication, graph-specific value, sustained compounding, specialist ASI.

Avoid converting a provider's performance description into measured superiority or using published maximum rates as actual available capacity. Source support and simulator confidence intervals answer different questions.
