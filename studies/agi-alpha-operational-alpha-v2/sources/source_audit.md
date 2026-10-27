# Source audit for Operational Alpha additive edition

Retrieved 2026-10-27. Research notes; not a quotation, customer commitment, API invoice, or legal determination.

## First offering: durable-service repair and regression evidence

A bounded Python/backend maintenance package is commercially interpretable: reproduce a reported retry, idempotency, reservation, rollback, authority or recovery defect; deliver a patch, adversarial regression tests, runnable evidence and a concise deployment/remaining-risk note. Scope must name the source version, supported environment, invariants, acceptance suite, deadline and customer effort before comparison. A research fixture is not a production service or a general assurance certificate.

**Human reference:** Arc's own backend freelance rate explorer reports an average and median rate band of USD 61–80/hour. It is a market rate reference, not a task-matched quote. Source: https://arc.dev/freelance-developer-rates/back-end (fetched full page; `turn11view2`, lines 166–178). A reasonable *explicit researcher estimate* for the small bounded service is 4–12 human hours, giving USD 244–960 at that rate band; these hours must be called assumed and sensitivity-tested, not sourced. It is also acceptable to model 8 hours × USD 70 = USD 560, provided the report distinguishes the assumed hours and chosen within-band rate from the sourced band. No buyer has accepted these estimates.

**Lower-price alternative:** Upwork's first-party search entries report Python developers at USD 20–40/hour (median 30), and backend developers at USD 20–40/hour (median 25): https://www.upwork.com/hire/python-developers/cost/ (`turn10search0`) and https://www.upwork.com/hire/back-end-developers/cost/ (`turn10search1`). Direct page fetches returned 403; label these search-index observations, not fully fetched quotes. At the same assumed 4–12 hours, the lower-price reference is USD 80–480. Do not suppress this alternative when choosing a selling-price hypothesis.

**Why the job matters:** AWS's own engineering account explains why a retry after a missing response can duplicate an external effect, and why request identifiers, response semantics and atomic durable recording matter: https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/ (`turn12view0`). Temporal's own workflow documentation explains replay from event history and the need for deterministic decisions and separately managed external effects: https://docs.temporal.io/workflows (`turn12view1`). These establish real engineering requirements and available alternatives. They do not establish willingness to buy this study's service. U should retain access to this ordinarily available knowledge and tools.

**Demand strength:** Plausible service category, observable technical need and published labor-market references; no measured demand, customer quote, sale, or willingness-to-pay observation. A buyer can repair internally, use existing durable-execution platforms, hire a human, defer, or decline. Do not price as if all alternatives were absent.

## Frontier model audit

Current official API identifiers are `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6.1-terra`. All have 1,050,000-token context and 128,000-token output ceilings. Astra/Sol accept reasoning effort low, medium, high, xhigh, max; Terra also supports none. Tool calling on these models requires Responses. Their documented tools include shell, code interpreter, apply_patch, web/file search, computer use, MCP and skills. Fine-tuning is marked unsupported. Public pages show aliases, not dated immutable snapshots; record requested and returned model identity in any future paid run.

Standard short-context input/cached-input/output USD per million tokens: Astra 10/1/50; Sol 2/0.10/10; Terra 1/0.05/5. Above 272K input tokens in a request, input/cache rates double and output rate multiplies by 1.5 for the entire request. Cache writes, speed mode, regional processing and tool/host charges can add cost. See `official_model_manifest.json` for rates, references and evidence labels.

The local environment contained OpenAI SDK 1.97.1 and Agents SDK 0.0.17, no model-named environment configuration and no OPENAI_API_KEY environment variable. This read-only observation establishes neither account access nor lack of all possible access. No account quota was checked; no API request or bill was observed. Hosted ChatGPT agent execution can provide empirical output observations but does not become a metered API experiment. ChatGPT subscription usage and API billing are separate (https://learn.chatgpt.com/docs/pricing, `turn4view4`; https://learn.chatgpt.com/docs/auth, `turn4view5`). Do not assign API costs to observed hosted runs as though invoiced.

### Shadow-cost sensitivity when token telemetry is unavailable

Use explicit assumed token-volume bands for every arm rather than manufacturing per-arm token counts. Example aggregate volumes across requests whose individual contexts remain at most 272K:

| Assumed total input/output tokens | Astra | Sol | Terra |
| --- | ---: | ---: | ---: |
| 25,000 / 5,000 | USD 0.50 | USD 0.10 | USD 0.05 |
| 100,000 / 20,000 | USD 2.00 | USD 0.40 | USD 0.20 |
| 400,000 / 80,000 | USD 8.00 | USD 1.60 | USD 0.80 |

These arithmetic scenarios exclude tools/hosting, residual human attention, rejected jobs, refunds, maintenance and capacity costs. They are not complete delivery costs. If telemetry is absent, accepted-output *dollar* advantage cannot be measured; report observed acceptance/resource proxies and conditional economic break-even separately. Calculate spend ceilings that preserve margin and show what a real trace must measure. Aggregate token volume does not determine long-context surcharge without per-request context sizes.

## Original vision and token boundary

agialphaagent.com redirects to its current content-addressed page: https://agialphaagent.mypinata.cloud/ipfs/bafkreidagljdagkbgbw7k75u2syxrdl5wlszsbtph44s3pgxay4rszsmnm (`turn4view0`, `turn8view1`). The page motivates opportunity discovery, orchestration, validator-mediated work and capability access. It advertises a USD 15 quadrillion AGI opportunity and exceptional IP importance, without a quantitative derivation or evidentiary validation on that page. Treat these as attributed motivating claims, excluded from revenue or demand inputs. Its terms describe AGIALPHA as prepaid service access without equity or profit share, while the ecosystem narrative describes job funding and validator-mediated settlement. These are published descriptions, not proof of deployed utility or legal status. Distinguish any implemented token/currency adapter that the source audit actually executes from these descriptions; keep issuance, token market value and earned enterprise cash separate. The page labels itself pre-alpha/under development.

## Optional portfolio references

- APEX CAE publishes part-level analysis at USD 700–1,500 with reported stress/strain/thermal/vibration results and typical 1–2-week turnaround; subsystem analysis USD 1,000–3,000 and 2–3 weeks: https://apexcae.com/pricing/ (`turn3view3`). It is adjacent human-service scope for thermal lineage, not a quote for a small computational benchmark or proof of physical validation.
- Texas A&M statistical consulting publishes USD 150/hour for commercial clients and offers experimental design, sample-size, modeling and analysis support: https://artsci.tamu.edu/statistics/resources/consulting-collaboration-center.html (`turn4view2`). Its public 2025 project log documents consulting activity: https://artsci.tamu.edu/statistics/_files/_documents/scc/statistical-consulting-center-log-2025-sheet1-1.pdf (`turn9view5`). Do not infer demand for our specific output or treat subsidized university support as identical to a commercial service.
- University of Florida publishes external statistics rates of USD 300/hour for PhD-level work and 185/hour for master's-level work, with explicit analysis/design roles: https://phhp.ufl.edu/about/departments/biostatistics/services/biostatistics-consulting-lab/ (`turn4view3`). This supports a sensitivity comparator, not valuation of a prompt.

## Relevant prior methods and evaluation design

- Khattab et al., DSPy (2023), https://arxiv.org/abs/2310.03714 (`turn9view0`): optimizing composed model workflows and demonstrations is established methodology. This motivates versioned operational expertise without requiring novel model weights. Its task-specific results do not calibrate GPT-6 effects.
- Yuksekgonul et al., TextGrad (2024), https://arxiv.org/abs/2406.07496 (`turn9view1`): natural-language feedback can optimize components of compound systems. This is conceptual precedent, not a guaranteed transfer gain.
- OpenAI, Testing Agent Skills Systematically with Evals (2026-01-22), https://developers.openai.com/blog/eval-skills (`turn9view2`): outcome/process/efficiency evidence and small targeted checks support proportionate evaluation. User-independent fresh confirmation and commercial accounting remain our study responsibilities.
- Current OpenAI guidance says hosted Evals is winding down and suggests portable Promptfoo configurations: https://developers.openai.com/cookbook/examples/evaluation/moving-from-openai-evals-to-promptfoo (`turn9view3`). Do not introduce a new required managed-Evals dependency into the research blueprint.

## Citation handling

The parent agent must open the listed URLs itself before citing subagent retrieval references in the user-facing answer. The document can cite canonical URLs or BibTeX keys normally. All notes above are paraphrases; avoid copying source wording or claiming the whole site was independently audited.
