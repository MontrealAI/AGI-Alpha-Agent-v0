# AGI ALPHA campaign: frontier and exact-fiber research

Research date: **2026-10-28**. This memo records the frontier search and prior-art assessment that motivated the
executed study. Sources were checked through official vendor pages, original papers, author software and project
documentation. [sources.json](sources.json) preserves URLs, publication dates where known, retrieval dates, source
handles and short source-grounded facts. Per-URL retrieval times were not retained. Downloaded source manuscripts and
comparator archives were intermediate research inputs and are not redistributed here. The completed study and its
experimental chronology are documented in [the README](../README.md).

## Decision relevant finding

A reusable generator of *exactly uniform constrained integer tables* is a legitimate computational production
instrument: it manufactures ensembles of feasible worlds, with explicit margins, cell bounds, structural zeros, and an
auditable output law. It is not a new problem, and exact dynamic-programming sampling is established. The strongest
near-term claim would have to be a measured extension in supported constraints, resource envelope, usability, or
retained conditioning ability. No global algorithmic novelty, new polynomial-time result, autonomous discovery
superiority, or commercial demand is established by this research.

The public [OpenAI family 115](https://github.com/openai/math/blob/main/lean/docs/115.md) is a useful recent search
signal, not a license to replace its algorithm with an unrelated DP and call that theorem implemented. Its
unbounded-cell exact sampler and cell-bounded approximate counter are separate results. The latter explicitly describes
generous polynomial exponents rather than practical runtime estimates. Its exact sampler is also not an exact
polynomial-time counter. Correctly generating a finite set of constrained outputs can be established independently of
the new theorem.

## Subsequent executed disposition

The search identified a useful computational production task, but the completed experiments did not qualify a profitable
transformational flagship. The browser and Python implementations generate exact constrained worlds within explicit
budgets. All 12 larger compiler cases completed; 11 had independent conventional corroboration within confirmation, and
the last was corroborated in a later adaptive row-order probe. The original authors' binary EXACT code succeeded on a
published case for which this implementation refused its budget. Cold successor transfer did not beat the strongest
conventional alternatives in the tested requests. The commercial confirmation selected no launch: the USD 449 instrument
lost a mean simulated USD 26,397.71 in the base scenario; the revised gate lost USD 3,050 while declining to launch. No
actual customers, receipts or willingness-to-pay observations were created.

These findings are linked to [scientific confirmation](../results/confirmation_v2/scientific_summary.json), [successor
results](../results/confirmation_v2/successor.json), [the ordering
challenge](../alternatives/ordering/ordering_review.md), and [the complete economic dossier](../ECONOMICS.md). The
candidate descriptions below preserve the questions posed during search; they are not retrospective claims of success.

## Moving frontier, last 30 days

| Development | Date | What is actually available | Economic implication to test | Exclusion/limit |
|---|---|---|---|---|
| [OpenAI GPT-6.1 Terra](https://openai.com/index/introducing-gpt-6-1-terra/) | Oct 26 | API and Work/Codex rollout; official USD 1/M input, USD 0.05/M cached input, USD 5/M output | Cheaper multimodal production and artifact checking may reduce cost of producing bespoke instruments | Vendor benchmark claims do not establish this workflow's reliability or costs; no model call receipt yet |
| [OpenAI academic science collaboration](https://openai.com/index/building-scientific-understanding-with-academic-communities/) | Oct 26 | Public mathematics/CS manuscripts and some Lean artifacts; ETH natural-language output Oct 16, Lean Oct 17 | New algorithms and formal artifacts can seed implementation search | Authors call outputs raw research data; practical speedups need research; quantum-field artifacts not released |
| [Google Genie 4](https://deepmind.google/blog/genie-4-a-new-generation-of-world-simulation/) | Oct 27 | Trusted-tester research preview; wider access announced for future | Eventually cheaper interactive scenario prototyping | Not currently available to this campaign; no trustworthy engineering physics guarantee; object/physics/spatial drift acknowledged |
| [Anthropic Haiku 5.5](https://www.anthropic.com/claude-haiku-5-5) | Oct 7 | Available small-model API/assistant capability; vendor says lower average costs | Cheap bounded substeps and redundant checking | Not measured here; vendor comparisons are not a cost ledger |
| [Mistral Large 4](https://mistral.ai/news/mistral-large-4/) | Oct 6 | API preview; weights promised end-month | Future local deployment could reduce supplier concentration | Do not assume released weights or practical 1T model hosting in this environment |
| [Google Antigravity scientific workflow](https://deepmind.google/blog/accelerating-antimicrobial-discovery/) | Oct 15 | Agentic integration of public protein/structure data shown | Research workflow assembly becomes faster | Candidate still in wet-lab validation; not evidence of drug efficacy or autonomous science success |
| [SAT-fiber sampling paper revision](https://arxiv.org/html/2511.05709v2) | Oct 9 | Original paper + Apache2 implementation and benchmarks | Practical structural-zero sampling problems remain active | Existing competitor, not an AGI ALPHA invention |

A working hypothesis is that current tools reduce construction friction. This study did not measure that causal effect.
No controlled old-model/new-model
trial establishes that Oct 26 Terra is indispensable to the proposed kernel. A `why now` section must distinguish a
motivating development from an experimentally identified cause.

## Important prior art and correct comparison

1. **[Miller & Harrison (2013)](https://arxiv.org/abs/1301.6635), Annals of Statistics 41(3), 1569–1592, DOI
   10.1214/13-AOS1131.** Their DP uses repeated column-sum symmetry to count and uniformly sample binary/nonnegative
   tables. [EXACT v0.3](https://jwmi.github.io/software.html) is a real C implementation with Python, R, and Matlab
   wrappers, plus pure Python binary code. Author warns about memory and moderate-size/sparse envelopes. This is the
   primary conventional baseline. Generic memoization, column sorting, or count-guided sampling is not novel.
2. **[Scharpfenecker & Windisch (2026)](https://arxiv.org/html/2511.05709v2), Statistics and Computing, DOI
   10.1007/s11222-026-10985-8, arXiv 2511.05709v2 (Oct 9).** Encodes fibers as SAT instances, includes structural zeros
   and bounds, offers hybrid MCMC. The paper explicitly reports near-uniform SAT sampling too expensive even on small
   instances and bias in faster CMSGen. This supports an unsolved practical performance question, not proof that a new
   DP wins. Public code: https://github.com/scharpfenecker/sat_fiber_walks.
3. **[Cryan, Dyer & Randall (2010)](https://epubs.siam.org/doi/10.1137/060650544), SIAM J Computing 39(7), 2683–2703.**
   Cell-bounded approximate counting with fixed number of rows, by DP/volume estimation. Bounds and structural zeros are
   old problem features.
4. **[Arman, Gao & Wormald (2021)](https://arxiv.org/abs/2104.09413), arXiv 2104.09413.** Exactly uniform sparse-table
   algorithm with expected linear time in total M if maximum margin Delta satisfies Delta^4 < M/5. Include specialized
   methods when test cases satisfy their regime.
5. **[SciPy `random_table`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.random_table.html).**
   Boyett/Patefield conditional-independence distribution. For nonnegative tables it is generally weighted by inverse
   cell factorials and is not the uniform distribution over tables. A fast method for a different requested law should
   neither count as success nor be framed as defective software.
6. **[PopulationSim](https://activitysim.github.io/populationsim/) and
   [humanleague/QIWS](https://www.jasss.org/20/4/14.html).** Already produce whole synthetic populations preserving
   controls through balancing/integerization/quasirandom methods. Uniform over aggregate tables does not itself yield
   realistic person/household populations, recover causal truth, or guarantee privacy. It can be an ensemble for a
   specified modeling question.

A search for the exact phrase combination "rank/unrank + residual signature symmetry + future cell bounds" found no
decisive match. Absence in this bounded search is not a novelty result. The combination resembles standard symmetry
reduction and exact-count sampling. Full suffix constraint signatures are necessary to avoid merging non-equivalent
columns; giving the same construction to a conventional system is an essential control.

## Product and economic evidence

**Useful opening:** simulation teams and researchers need samples that obey aggregate controls and known
impossibilities; general approximate samplers can mix slowly or sample the wrong law. A delivered instrument can take a
schema and manufacture a reusable, locally executable exact generator, then condition it on new evidence. Output would
be a generator, sample files, acceptance checks and declared resource limits. These are production outcomes, not a
verification dashboard.

**Scientific demand evidence:** Miller/Harrison already applied exact sampling to ecological co-occurrence, social
affiliation, neurophysiology and psychometrics. Their ecological example shows materially different inference under an
inappropriate heuristic versus the intended fixed-margin law. The Oct 9 SAT paper reports practical bias/performance
tradeoffs. These support importance, not payment likelihood.

**Free alternatives:** EXACT, SAT-fiber walks, PopulationSim, humanleague, generic #SAT/#SMT counting, explicit
enumeration on small cases, and specialists writing a DP. A competitor can copy public algorithms and source, so any
model must allow low-cost entry and price compression.

**Adjacent observed posted prices:** [Mockaroo](https://www.mockaroo.com/pricing): USD 60/year Silver, USD 500/year
Gold, USD 7500/year private-cloud Enterprise. [GraphPad's opened page](https://www.graphpad.com/how-to-buy/) gives
monthly Standard USD 50 and Pro USD 75. These are broad synthetic-data/statistical software prices, not quotes for an
exact-fiber generator. The GraphPad annual page has dynamic academic/corporate selectors and stale search snippets;
monthly figures are less ambiguous.

**No demand proof:** No named prospect, quote, accepted proposal, willingness-to-pay observation, contract, receipt, or
payment for this proposed offering was found or created. Any acquisition, conversion, renewal, support effort, price or
demand distribution is an assumption. Price anchors cannot justify an arbitrary USD 1500/job fee by themselves. Markets
with zero demand must be allowed. No credible billion-dollar reachable market is established.

**Economics implications:** Use measured kernel runtime for marginal compute, but price labor for failed jobs, schema
interpretation, review, support, updates and onboarding. Low compute is unlikely to dominate full cost. Include
competition from free tools, no-sale periods, refund liability, invoice delays and maintenance of persisted generators.
Actual research labor/call costs unknown must stay unknown, not zero. The completed economic model rejected launch under
its declared assumptions; see the separate economic dossier. Positive contribution from a unit does not establish that
its enterprise covers construction and recurring costs.

## Three candidate directions and disposition

| Candidate | Essential construction | First useful output | Successor option | Status |
|---|---|---|---|---|
| Constrained exact-ensemble compiler | Count-guided sampler with correct symmetry under future bounds, portable persisted count graph, explicit resource admission | Reusable generator of exact fixed-margin worlds with structural zeros | Fresh conditioning/network constraints using inherited compiled substructure | Implemented and challenged; bounded correctness established, consequential novelty and profitable launch unqualified |
| Practical family 115 algorithm implementation | Implement the actual new weighted-chain/annealing/correction machinery and benchmark | Scalable exact-uniform or certified approximate sampling beyond DP envelope | General bounded integral network-flow generation | Theoretically consequential; essential practical algorithm too uncertain for immediate flagship. Do not substitute DP and claim theorem implementation |
| Matrix-function production compiler; certification hypothesis | Test whether the sharp complete constant 2 changes executable polynomial programs against established bounds | Executable operator with error/latency contract | Different analytic functions sharing domain instrument | Later numerical probe retained actual outputs; strong conventional comparison gave 0 degree wins, 92 ties and 52 losses. See the [matrix-action dossier](../alternatives/matrix_action/negative_assessment.md) |

## Foundation continuity

The executed study starts from public main commit `12770c22b4a9f90f2013bbfb64242f912ba5071e` of
MontrealAI/AGI-Alpha-Agent-v0. Vincent Boucher's existing foundations make formulation-dependent feasibility,
construction of productive means, mutually acceptable economic arrangements and complete reconstruction costs central to
the program:

- [Transformational Intelligence][foundation-ti].
- [Out-Evolve][foundation-evolve].
- [Invent the Economy][foundation-economy].
- [Autonomous Enterprises][foundation-enterprise].

The current results preserve that distinction between a useful artifact, a new productive advantage and a financeable
enterprise. Known dynamic programming cannot become a new algorithm through relabeling. The failed comparisons and
commercial losses remain part of the study.

## Source handling and scope

The source catalogue contains short research annotations and original URLs; its retrieval handles are provenance
metadata, not standalone citations or assertions of execution. The current-frontier rows report what the retrieved
sources said on the research date. Access to a vendor announcement is different from access to a model, a measured
workflow benefit or a paid usage receipt. The implemented deterministic kernel requires none of those frontier services
at runtime.

This directory includes only this memo and the URL catalogue. Third-party papers and downloaded comparator archives are
excluded. The separately included comparator source in [vendor/](../vendor/) has its own license and provenance. Later
execution details, corrections and numerical results belong to their linked frozen dossiers rather than being silently
substituted for the original research evidence.

[foundation-ti]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/12770c22b4a9f90f2013bbfb64242f912ba5071e/docs/Transformational_Intelligence.tex
[foundation-evolve]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/12770c22b4a9f90f2013bbfb64242f912ba5071e/docs/Out_Evolve.tex
[foundation-economy]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/12770c22b4a9f90f2013bbfb64242f912ba5071e/docs/Invent_the_Economy.tex
[foundation-enterprise]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/12770c22b4a9f90f2013bbfb64242f912ba5071e/docs/Autonomous_Enterprises.tex
