# External-method source register
Inspected 2026-10-26. Scope: read-only primary-source review; no framework installation, paid model calls, source mutation, or reproduction of published results.

## Verified identities

| Method | Primary version inspected | License | Implementation checkpoint |
|---|---|---|---|
| Virtual Agent Economies — Tomašev et al. | arXiv:2509.10147v1, submitted 2025-09-12 | CC BY 4.0 | Conceptual paper; no associated implementation was identified in the paper |
| DUPLEX — Hua, Wang, Gu, Ma | arXiv:2603.23909v1, submitted 2026-03-25 | CC BY 4.0 | No author-linked code repository was located in the paper or the focused title/author/code search; this is not proof that none exists |
| OpenEvolve | main `66856ac4ba2f51382c26ca210361db4deb69b9d9`, dated 2026-10-26; package declares 0.4.0 | Apache-2.0 | Latest release v0.4.0 was published 2026-09-28 at target `f7b633986c0b3dbd0a171f6eb0cb0f0ba4fdfb0c`; main and release are distinct |
| EnvHarness — Huang et al. | arXiv:2608.19880v1, submitted 2026-08-20 | Paper CC BY 4.0; code Apache-2.0 | `google-research/envharness` main `fab7d57441f06b75c73a900e04561d4d7600f361`, dated 2026-08-21; package 0.0.1 |

Sources: [VAE paper](https://arxiv.org/html/2509.10147v1), [DUPLEX paper](https://arxiv.org/html/2603.23909v1), [EnvHarness paper](https://arxiv.org/html/2608.19880v1), [OpenEvolve inspected commit](https://github.com/algorithmicsuperintelligence/openevolve/commit/66856ac4ba2f51382c26ca210361db4deb69b9d9), [OpenEvolve release](https://github.com/algorithmicsuperintelligence/openevolve/releases/tag/v0.4.0), [EnvHarness inspected commit](https://github.com/google-research/envharness/commit/fab7d57441f06b75c73a900e04561d4d7600f361).

## What the methods actually support

### Virtual Agent Economies
This is a conceptual treatment of intentional/emergent and permeable/impermeable agent economies. Auctions, resource allocation, reputation, coordination around missions, and accountable records supply design ideas. The paper does not estimate demand for AGI ALPHA, solve our market game, or validate a price, willingness-to-pay distribution, switching cost, or profitable investment rule. Its discussion acknowledges emergent instability and difficult oversight. Use it to specify institutions, information, resource constraints, and conflicting incentives. Keep payment outside the experiment: this study is an intentionally isolated simulated market.

### DUPLEX
The fast path uses schema-guided Qwen3-8B extraction, deterministic JSON-to-PDDL conversion, and Fast Downward; GPT-4o repairs grounding upon failure. Published tests cover 160 IPC instances plus 12 household instances repeated 50 times. Those 600 household trials are not 600 independent tasks. The paper reports 97.5% IPC and 83.5% household success, with fast-path ablations 83.8% and 50.9%. These are planning results, not customer or cost results. Limitations include manually authored PDDL domains, reflection latency, and text ambiguity. The stated 60-second generation and 500-second planner budgets matter to comparisons. The appropriate transferable hypothesis is that semantic extraction can feed exact consumer constraints without giving the model authority to decide satisfiability. It remains an adaptation unless original models, planner, domains, and protocols are reproduced.

### EnvHarness
EnvRigger diagnoses policy trajectories, writes environment modifications, and validates them through fresh rollouts. The paper's Stage/Contract/Chain correspond to code Setup/Rules/Link. Evaluation uses original, unmodified held-out tasks. Reported gains reach nine percentage points; reported steps fall 9.8%. Weakness-targeted learning may help only after a production failure is demonstrated. Its limits include costly iterative design, resettable textual interfaces, and restricted verifier composition. A benchmark wrapper is not a demand experiment. The core `EnvHarness.evaluate()` delegates to the inner environment by default, but subclasses can override it; preservation is an experimental contract requiring independent checks, not a general impossibility of changing grading. Do not introduce a curriculum into this first intervention unless failures justify its cost.

### OpenEvolve
OpenEvolve searches programs through model proposals, executable evaluation, quality-diversity populations, and islands. Its evaluator defines success; reported optimization examples do not establish improvement on this offering. A trustworthy application needs an independently specified acceptance test, capped proposals/evaluations, preserved failures, and fresh inputs beyond search. README prices are illustrative provider/iteration figures, not this project's cost evidence. v0.4.0 release notes introduce token accounting and opt-in edit-block restrictions. Neither supplies the complete investment ledger. Defer executable search unless profiling reveals a repeated component whose realistic savings could repay search and integration. A good ordinary builder with retained assets must receive comparable information and resources.

## Dependency and implementation records

OpenEvolve's inspected `pyproject.toml` requires Python >=3.10; runtime dependencies: openai>=1.0.0, pyyaml>=6.0, numpy>=1.22.0, tqdm>=4.64.0, flask (unbounded), dacite>=1.9.2, cloudpickle>=2.0.0. These are declared lower bounds, not an environment lock or a tested compatibility guarantee. Git blob: `8411f9e5ca0a079b359300d1fa25b620fedab9df`. Version-file blob: `350f9834a183c4b7592e7ac05a1c692834099bd7`. License blob: `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64`.

EnvHarness's inspected `pyproject.toml` requires Python >=3.10, pydantic>=2.0, pyyaml>=6.0, litellm>=1.50; dev pytest>=7.0. Blob: `9c3da8bb5165667526735baa9697e9ad3fd8dbcb`. Core wrapper blob: `79ff4fb8b5a0085022b2b2138f5a3cbabbf07145`. License blob: `7a4a3ea2424c09fbe48d455aed1eaa94d9124835`. README says published tables used Gemini whereas repository defaults use GPT-4.1-mini; an unchanged default command is not an exact table reproduction. Benchmark-specific setup and provider credentials are additional requirements. No such environment was installed here.

[OpenEvolve metadata](https://github.com/algorithmicsuperintelligence/openevolve/blob/66856ac4ba2f51382c26ca210361db4deb69b9d9/pyproject.toml) · [EnvHarness metadata](https://github.com/google-research/envharness/blob/fab7d57441f06b75c73a900e04561d4d7600f361/pyproject.toml) · [EnvHarness wrapper](https://github.com/google-research/envharness/blob/fab7d57441f06b75c73a900e04561d4d7600f361/envharness/core/envharness.py)

## Recommended single intervention: consumer-grounded semantic records plus exact constraints

This is a proposed test, not a completed or validated treatment. First verify the actual baseline burden. If it already reliably obtains consumer-relevant conclusions using cheap deterministic tools, do not create an artificial model bottleneck.

- **Observed burden to establish:** time or substantive omissions in translating release/source changes into a complete consumer decision, rather than the cost of inventory formatting.
- **Mechanism:** a constrained model extracts source-linked affected symbols, behavioral preconditions, and uncertainty into a typed record; deterministic code matches consumer usage and version constraints, executes bounded compatibility checks, and either issues a scoped decision or refuses.
- **Borrowed element:** DUPLEX's separation of semantic grounding from exact reasoning, with diagnostic-triggered repair.
- **Our adaptation:** consumer schema, source identity checks, caller mapping, task budget, existing AGI ALPHA runtime integration, and an independent decision verifier. No PDDL result or published success rate transfers by assumption.
- **Failure scope:** undocumented dynamic behavior, incomplete caller coverage, omitted transitive dependencies, ambiguous release text, unavailable tests, or uncertain provenance should preserve uncertainty or HOLD. A syntactically valid record is not semantic evidence.
- **Comparators:** actual incumbent retaining its caches; treatment; a competent conventional AST/search/test workflow retaining useful fixtures. Same source, consumer, budgets, and acceptance standard. An optional no-model ablation isolates whether extraction adds anything beyond deterministic code.
- **Prospective protocol:** freeze source/schema/criteria before fresh repository families and transitions are selected; use a separate verifier; preserve every failed extraction/repair and run; count underlying consumer jobs, not repeated arms or assertions.
- **Resources:** separately record discovery, schema construction, prompts/responses, all proposals, failed calls, checks, repair, integration, execution, upkeep, and residual attention. Unknown billing remains unknown.
- **Disproof:** no accepted-quality advantage, no robust whole-workflow savings, or equal/better conventional performance defeats claims of distinctive productive advantage.

If a callable model is unavailable, hand-authored records alone do not evaluate DUPLEX. Current-session model-produced records can support a narrowly described prospective extraction study only if prompt/response/source identities and unknown inference charges are retained. Replaying those records measures the downstream pipeline, not fresh extraction or autonomous delivery.

## Economic consequence
The market model should keep buyer assumptions identical across arms except for empirically supported production changes. Faster CPU execution cannot be relabeled reduced customer switching effort. Compare investment against the conventional alternative: when accepted quality and recurring cost are equal, any additional nonnegative construction/upkeep cost makes the research treatment economically weakly dominated. Demand or reserves may still be the binding problem even if an engineering improvement transfers.

No result in this register constitutes a completed transfer, a profitable enterprise, paid demand, a solved equilibrium, or self-acceleration.

