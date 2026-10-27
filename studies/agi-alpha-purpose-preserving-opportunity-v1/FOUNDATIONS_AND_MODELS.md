# Foundation and model verification memo

Prepared 27 October 2026 for the independent opportunity-first edition. Read-only source inspection; no provider calls, purchases, production credentials, authority or repository files changed.

## Source freeze

The locally inspected repository is `MontrealAI/AGI-Alpha-Agent-v0` at `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`.

| Source | Bytes | SHA-256 |
|---|---:|---|
| `docs/Transformational_Intelligence.tex` | 89,775 | `9d4a664d951d6b97f5136bf0b44f1ca458e90d585434a6a27a542694bb2ece5f` |
| `docs/Transformational_Intelligence.pdf` | 305,040 | `d7170e8217e3bf6aa1b84868c1c76c5994c6995c5297ed092d7e72a6430c664f` |
| `docs/Invent_the_Economy.tex` | 82,693 | `51605532c48edc5465b562e8699f473c42f437c4a288795a610fb61dc2a70a47` |
| `docs/Invent_the_Economy.pdf` | 285,994 | `61e92a47b32cbca12b705094b982dddaca03b3dfe2b7f657bbf30eb8d56bba79` |
| `docs/papers/transformational-autonomous-enterprises-v1.tex` | 115,056 | `4b7b02547832079988d5032231bd69e7d9e86d11a2142b7ca5e4f4c3b6fc5d8a` |
| `docs/papers/transformational-autonomous-enterprises-v1.pdf` | 511,027 | `640cba6e0371407577f708856efa4e4d3b685ed7349cecf48491f1660563fda0` |

Immutable source prefix: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4/

The three papers were read through local LaTeX source rather than relying on search snippets. The supplied Pages PDF URL was inaccessible to the web retrieval tool; the exact repository counterpart was available locally. The hashes above bind the inspected versions, not a claim that a currently served URL was downloaded and matched.

## 1. Transformational Intelligence: mechanism to carry forward

The paper separates the intent charter, problem formulation and evaluation instrument. A formulation may change representations, information procedures, dependencies or production rules while retaining the authorized purpose. A candidate must supply an executable realization and a purpose bridge. A weak procedure is not evidence of an old-frame ceiling; diagnostic evidence can instead show observational equivalence, a serial dependency, or a representation that discards a material distinction.

The paper's exact causal illustration has passive accuracy bounded by one half and an active policy with accuracy `1 - 2^(-(m+1))`. At twelve interventions this is `8191/8192`; an unrestricted optimal planner matches the policy. This is a supplied finite structural demonstration, not a new causal algorithm or measured LLM invention.

**Use in the new study:** name the concrete lost distinction or avoidable dependency before implementation. Keep the original recipient outcome and evaluator frozen for confirmation. Record original purpose, suspected restriction, evidence it is removable, replacement, executable realization and falsifier. Give the resulting formulation to a competent conventional method to separate formulation value from execution value and discovery-policy superiority.

Its lifecycle cost expression is search + build + confirmation + migration + all execution, verification and maintenance. Its elementary break-even condition is `R[(e0+v0)-(e1+v1)] > K`; this is conditional accounting, not evidence of savings. It explicitly permits bounded complementary exploratory edits, unchanged-frame controls and stopping. Cryptographic identity is not semantic truth, and many agreeing evaluators cannot validate the wrong target.

## 2. Invent the Economy: construction and arrangement

The useful object is a package `(technical capability, actual prospective counterparties, transfers/responsibilities, financing/delivery schedule, rights/authority, evidence)`. Its evidence ladder distinguishes technical possibility, modeled viability, accepted arrangement, realized exchange and repeatable market. A well-formed plan cannot advance itself through those states.

For a shared qualification event with probability `p`, the supplied model uses:

`venture contribution = p * sum(q_i - d_i - f_i) - (K + A)`

`buyer surplus_i = p * (v_i - q_i) - a_i`

Positive expected contribution, participation and financing are separate conditions. With delivery before payment, no borrowing and route charges deducted after receipts, prefunding is `K + A + sum(d_i)` under the paper's explicit conditions. Every cash prefix must cover required reserves. Refundable or restricted customer money does not become unrestricted working capital because a spreadsheet is profitable.

Its four-buyer example supplies a shared core, compatible buyers, `p=0.8`, costs, prices and later reuse reductions. The checker validates internal model consistency; it does not discover the invention, demand, enforceability or acceptance. Unrestricted ordinary enumeration ties. The exact factorial comparison motivates technology-only, arrangement-only and combined arms, but the single-buyer commitment restriction is not a theorem about ordinary entrepreneurship.

**Use in the new study:** make data acquisition, construction, acceptance and payment stages explicit; test nonparticipation, withdrawal, common failure, partial delivery, nonpayment/refunds and support where they matter. Optimize within stated hypotheses and report a boundary, not an imaginary firm offer. A later opportunity may become expected-profitable but remain unfundable from earned surplus. Keep the A/B/C cost partition disjoint and separate modeled collections from actual receipts. Native token throughput does not establish cash profit or token value.

## 3. SUCCESSOR Omega Harness: stable structure, new meaning, separate authority

The retained harness changes a weighted bill-of-materials graph into Boolean unique-impact propagation. Normalization and graph structure transfer, but multiplication/addition cannot silently be reused as unique reachability. Every descendant begins with empty current proof and authority. The external evaluator can reuse a generic module check only when its complete source, dependency, policy and input identity match; fresh mission input/output checks remain mandatory.

The initial three-repetition finite campaign and disclosed known-bank confirmation use 48 missions (40 valid, 8 invalid). Reuse, full replay and the supplied direct specialist all correctly handle those missions. Reuse reduces generic qualification cases from 1,600 to 64, but the direct specialist has lower pooled CPU and the better final median wall time. The reported source repair concerns self-parent lineage metadata; the known-bank repair is not new blinded confirmation. The paper does not establish external demand, complete monetary costs or commercial profit.

**Use in the new study:** transfer actual immutable capability bytes, dependencies, scope and rights. Recheck a materially different mission and its acceptance criteria. Do not infer authority from a passed checker. Count matching, adaptation, lookup and fresh verification, and compare against the recipient's actual preexisting competent method. A same-content ordinary library should receive identical contents and permissions for any graph-related comparison.

## 4. Reusable current interfaces

Source base for every path below is the commit above; use current exact bytes rather than duplicating a registry.

### Journal

`alpha_factory_v1/core/runtime/store.py`, SHA-256 `12ce595dc0277a68c8aadf2b0a6f25edb7ece892bba6a5d07f0781d8c82820aa`.

`Journal.initialize(root, config=None, allow_empty=False)` creates an isolated signed SQLite journal. `transaction()`, `append(cx, mission, document)`, `latest(mission, cx=None)`, `document(record)` and `verify()` support append-only evidence and source binding. `submit(...)` enqueues native missions; `transition(...)` performs revision/allowed-state compare-and-swap and checks active configuration. A local key proves record integrity, not ENS control or external institutional independence.

### TrustRegistry

`alpha_factory_v1/core/runtime/successor/trust.py`, SHA-256 `d94cfcf49d28869980de084fc7e9cd9d9d59cd2b165c5e113119388629ba12cd`.

`TrustAnchor(public_key, roles, provenance='local', independence_attestation='')`; `TrustRegistry(anchors)`; `anchor(principal, role)`; `verify(envelope, domain, role)`; `revoke(principal)`. The registry is installed out of band. Incoming evidence cannot create its own trust root. `sign_record(key, principal, domain, record)` signs a payload without conferring trust. `JournalCheckpoint.capture(journal)` and `.verify(journal)` detect truncation relative to a separately retained anchor.

Important integration detail: `local_principals()` does not include an `accounting` role. An isolated accounting fixture must explicitly configure an accounting anchor and identify it as fixture/local. It must not alter production trust, identity or wallet state.

### CostLedger

`alpha_factory_v1/core/runtime/successor/flywheel_costs.py`, SHA-256 `4d2e19b937471bdc247a9b0bb66bd4c315da5a9c6498591bc9f24496e07feb13`.

Construct with `CostLedger(journal, trust)`. `apply(signed)` requires a `flywheel-cost-command` envelope from an `accounting` principal. Payload keys are exactly `journal_identity`, `operation_id`, `action`, `record`. Operation identity binds exact terms; duplicate charge/payment/funding evidence is rejected.

`Charge` carries activity/mission identity, bucket A/B/C, category, accrued and paid micro-USD, basis (`measured`, `attested`, `unknown`), evidence digest and note. An unknown cost has `accrued_micro_usd=None`; it cannot be silently zero. Categories are model, tools, compute, storage, network, human, acceptance, correction and overhead.

Actions include charge, resolve, payment, capital, collection, offer, invoice, pending, reserve, seal, seal-reuse/seal-retention and seal-investment. A completeness seal needs all nine categories and no unknown accruals. `report(mission_id=None)` returns disjoint bucket totals, collected revenue, conditional delivery/complete-cost profit, cash, obligations, reserves and available funds. Token movements are excluded. A configured accounting signer is not a bank attestation.

`accepted_native_delivery(journal, mission_id, cx=None)` requires an exact completed-and-approved native result, matching request/result hashes and `verify_result`. The protected slice accepts native public-source `Research` delivery only. Arbitrary new scientific computation must remain a separate research artifact/fixture; do not mark it admitted merely by storing it in this ledger.

`flywheel_frontier.py` is an existing bounded model-proposal connector, with exact model/config/task/tools permit binding, expiry, quota/cap, no blind uncertain retry and explicit unavailable-provider state. Its restricted tooling is not evidence that frontier models cannot execute richer workflows. Preserve active runtime owners rather than expanding this connector under a research claim.

## 5. Official model verification, 27 October 2026

The official model pages and current GPT-6 guide were opened, not merely searched. Suggested study configurations are design choices, not tested winners.

| Role | Verified API identifier | Supported reasoning | Standard USD / million text tokens (input / cached / output) |
|---|---|---|---|
| Hard discovery, reasoning and scientific judgment | `gpt-6-astra` | low, medium, high, xhigh, max | 10 / 1 / 50 |
| Visual/computer workflow execution | `gpt-6.1-terra` | none, low, medium (default), high, xhigh, max | 1 / 0.05 / 5 |
| Repeated complex work, lower-cost comparison | `gpt-6.1-sol` | low, medium (default), high, xhigh, max | 2 / 0.10 / 10 |

Astra and Terra pages state a 1,050,000-token context and 128,000 maximum output. They accept text and images and support computer use. They do not expose fine-tuning support. The ordinary model aliases, not invented dated snapshots, are the publicly listed identities; record the actual returned provider model and response IDs in a live trial. Current account API access and account-specific rate limits were not checked.

Both model pages list Free as unsupported and the same public tier ceilings: Build 5,000 RPM / 1,000,000 TPM / 3,000,000 batch-queue tokens; Launch 10,000 / 4,000,000 / 200,000,000; Grow 15,000 / 40,000,000 / 15,000,000,000. These published ceilings are not this account's verified limits (refs `turn22view0`, `turn22view1`).

Tool calling for Astra, 6.1 Sol and 6.1 Terra requires Responses. The guide separates reasoning effort from pro mode; Pro is not a substitute model slug. Remove temperature/top_p/top_logprobs when reasoning is enabled. Standard prices depend on context length, cache writes, mode and regional processing; inputs above 272K receive the documented long-context adjustments. Astra standard 30-minute cache writes are $12.50/M and Terra $1.25/M; cache writes are not the same as reads. Actual model and tool usage must be collected to compute a bill.

The computer-use guide uses a screenshot/action loop with the `computer` tool; the application executes requested actions and returns screenshots. A generated `computer_call` marked complete does not mean the UI action or user task succeeded. A provider route must preserve action receipts, correction and independent acceptance.

ChatGPT plan usage and API-key usage follow distinct entitlements and billing. The official pricing page says API model availability follows the key and API pricing applies. ChatGPT Pro therefore supplies neither an API identifier nor evidence that this research has a funded authorized API route. This session's assistant behavior is not a controlled H/U/E/E+ provider benchmark; its unexposed full token bill stays unknown.

### Official source register

1. Astra model: https://developers.openai.com/api/docs/models/gpt-6-astra (web refs `turn4view0`, `turn16view1`).
2. Terra model: https://developers.openai.com/api/docs/models/gpt-6.1-terra (refs `turn4view1`, `turn8view1`, `turn16view2`).
3. Current GPT-6 guide: https://developers.openai.com/api/docs/guides/latest-model (refs `turn4view2`, `turn6view3`, `turn8view2`).
4. API prices: https://developers.openai.com/api/docs/pricing (refs `turn4view3`, `turn8view3`).
5. Computer use: https://developers.openai.com/api/docs/guides/tools-computer-use (refs `turn15view3`, `turn16view3`).
6. Plan/API separation: https://learn.chatgpt.com/docs/pricing (refs `turn16view0`, `turn17view0`).

Root should open any source itself before citing a delegated ref. Markdown-suffix retrieval failed, but the HTML pages were opened successfully. No credentials were inspected and no model call was sent.

## Recommended synthesis paragraph

The new experiment should test a single opportunity campaign in which a named missing distinction or avoidable dependency is removed without changing the recipient's useful requirement. Technical construction and commercial terms should be assessed together, with conventional methods allowed the same formulation and arrangements. The resulting executable capability may transfer while its new mission earns fresh acceptance and separate authority. The three foundations establish these design obligations and bounded prior examples; they do not supply evidence that this edition has discovered demand, earned revenue or achieved compounding.
