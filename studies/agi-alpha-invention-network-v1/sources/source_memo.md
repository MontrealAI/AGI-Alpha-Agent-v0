# Source and calibration memo

Research edition: 27 October 2026. All web pages were retrieved on this date. The accompanying `primary_sources.json` provides exact URLs, titles, source status and citation handles. The sources supply model specifications, methodological precedents and service-rate anchors. They do not establish customer sales, model access, autonomous discovery, physical validation or the results of the new relay.

## Frontier Beta

Current official IDs are `gpt-6-astra`, `gpt-6.1-sol` and `gpt-6.1-terra`. Standard input/output prices per million tokens are respectively $10/$50, $2/$10 and $1/$5. Cached input is $1, $0.10 and $0.05. Use explicit token assumptions in enterprise scenarios; do not present simulated token counts as recorded usage. The verified context/output limits are 1,050,000/128,000 tokens for each. Astra and Sol expose reasoning effort `low`, `medium`, `high`, `xhigh`, `max`; Terra also supports `none`. The API documentation does not establish an `ultra` reasoning setting even if an internal orchestration environment uses that word.

Astra is a sensible high-capability research/code role and Terra a sensible visual execution role, but these are workload choices rather than permanent restrictions. Sol provides another competent cost/performance alternative. All three official pages list image input and Responses tool support including computer use, hosted shell, functions and code interpreter. Terra tool calling requires Responses. All three list fine-tuning as unsupported, so this edition should learn portable numerical components rather than imply proprietary-weight training.

The published tiers are Build 5,000 requests/minute and 1,000,000 tokens/minute, Launch 10,000/4,000,000, and Grow 15,000/40,000,000 for these models. Limits remain project-, organization- and model-dependent. No account API access or funded entitlement has been tested. A ChatGPT Pro subscription does not identify an API model or prove entitlement. The public model pages expose aliases without a separately dated immutable snapshot; a future live experiment should capture returned model IDs, usage, request settings and available response fingerprints.

Keep modeled prompts below the documented 272K long-context threshold unless a live pricing check resolves a documentation ambiguity: the individual model pages give 2x input/cache and 1.5x output for the entire long request; a selectable table in the rendered pricing page exposes 2x output. Short-context Standard tables agree. Web search is separately priced at $10/1,000 calls plus retrieved-content tokens. Screenshots incur image-input cost and environments can incur additional charges. These are disjoint from research, validation, retention and serving labor.

## Primary literature and novelty boundary

Silver and Sutton's *Welcome to the Era of Experience* motivates continual environmental interaction and learning from outcome feedback. The official Ineffable Intelligence site states a reinforcement-learning research ambition; Silver's dated founder note explicitly acknowledges failure risk. Cite these as motivation without implying affiliation, equivalence or reproduced superintelligence.

FunSearch (Romera-Paredes et al., 2024) and AlphaEvolve (Novikov et al., 2025) provide primary precedents for evaluator-guided improvement of executable algorithms. They do not make a researcher-constructed scientific surrogate an autonomous discovery. The official AlphaEvolve companion contains result verification code, expressly not the discovery system.

Reduced-basis and POD numerical learning are established methods. Rozza, Huynh and Patera (2008) combine low-dimensional projection, greedy sampling, error estimation and offline-online decomposition for parameterized coercive PDEs, including heat conduction. Gräßle, Hinze and Volkwein (2020) cover POD/SVD, adaptive basis updates and certification. Hinze and Kunkel (2010) specifically study residual-based POD sampling in a different drift-diffusion setting. The new contribution can be an inspectable transfer/composition/economics experiment around these methods. It should not claim to invent POD, Galerkin projection, greedy sampling, reusable factorizations or sensor optimization.

Manohar et al. (2018) use SVD and pivoted QR for training-dependent sparse sensor placement. Alexanderian and Saibaba (2018) exploit low-rank structure for D-optimal PDE inverse design. Attia, Alexanderian and Saibaba (2018) target a downstream quantity of interest. These support a meaningful specialist-composition task: a reusable response representation can reduce repeated forward-solve work, while a sensor-design procedure chooses informative measurements. The design remains conditional on the statistical model, noise law, admissible sensors and target quantity.

## Numerical certification and fair baselines

For a symmetric positive-definite discrete system A u = b, a valid lower bound alpha <= lambda_min(A) gives ||u-u_hat||_2 <= ||b-A u_hat||_2/alpha. A linear quantity of interest c^T u then has error at most ||c||_2 times that bound. This follows directly from e=A^{-1}r and the operator norm; it requires the stated lower bound. pyMOR's official documentation likewise conditions guaranteed upper bounds on an appropriate coercivity estimate. A residual norm without such a bound is an indicator, not a general solution-error certificate.

This certificate concerns the discrete equation. It excludes discretization error, uncertain material coefficients, geometry error, sensor bias and physical-model mismatch. If no physical trials occur, call outcomes numerical design/reconstruction evidence. Verify assembly separately on a manufactured solution, ensure symmetry/positivity, and document boundary conditions and forcing before interpreting learned accuracy.

SciPy CG requires an SPD operator and preconditioner. Generic incomplete LU is not automatically a valid SPD preconditioner for CG; use a mathematically justified construction or a compatible nonsymmetric Krylov method. Keep residual tolerances and accepted outputs comparable across methods. Strong baseline candidates include sparse direct solve, preconditioned iteration and factorization reuse for repeated matrices. A competent baseline should get factor reuse within a mission immediately; treating it solely as a later stronger frontier risks understating Beta. Cross-mission learned bases can still be the retained-capability treatment.

Pay special attention to inverse tasks: give each method identical observations and avoid using hidden target parameters to select the basis, sensor locations, regularizer or stopping rule. Training-derived sensor design should be frozen before the protected cases. Independent noise draws are not independent physical models; report the scope of generalization honestly.

## Human-service calibration

| Primary rate anchor | Published USD/hour | Appropriate scope and limit |
|---|---:|---|
| SDSU Computational Science Research Center | 80 external | Scientific software, algorithm development and HPC; not a quote for this deliverable |
| Vanderbilt ACCRE | From 84 | General research software engineering; complex specialist work can differ |
| UTEP Data Analytics Lab | 190.31 external analyst | Study design and statistical analysis; effective 10 August 2026 |
| UTEP computational equipment | 3.52 external | A listed institutional equipment rate; not an exact cloud CPU tariff |

Do not substitute an employee wage for a service selling price when actual service rates are available. The table supplies only rate anchors. Every mission still needs an explicit researcher-estimated work breakdown: formulation, implementation, experiment design, independent checks, correction, packaging and delivery. Multiply those hours by the justified rates and expose low/base/high ranges. No source here quotes the exact diffusion/sensor artifact or proves demand at the resulting price.

Use a human-equivalent service estimate as a pricing reference, then simulate price sensitivity and willingness to buy separately. An assumed $10,000 human-team project does not prove that a customer will purchase this numerical artifact for $5,000. A generic web or API call is not the complete cost. Maintain acquisition, context preparation, validation, environment, failure/correction, support, refunds and collections timing.

## Economic interpretation cautions

At modest PDE grid sizes, a computational speedup can save milliseconds while developer effort and validation dominate all-in cost. Report this outcome if observed. Do not multiply small CPU savings by an invented GPU tariff, nor assume every reuse avoids an entire human project. A recipient may independently implement a standard method using ordinary tools; retained Alpha is its incremental benefit after this competent baseline.

Disjoint costs should track paid delivery (including learning essential to that delivery), additional assessment/retention/sharing, and optional extra Gym/R&D. Charge failed candidates and training experiments. Report model-derived savings separately from cash expenses and forgone work. At fixed resources, any additional jobs require available demand and a genuine freed bottleneck; freeing CPU while expert validation is saturated need not expand throughput.

A positive technical transfer can coexist with negative program net value. A composition can improve information quality yet fail its cost or reliability threshold. Ordinary library retrieval with identical contents/permissions must remain the comparison for graph-specific claims. An unchanged linear lookup cost is no evidence of a graph benefit.

## Source usage

The memo paraphrases sources, uses no extended quotation, and does not provide a literature-review replacement. The machine-readable bibliography includes precise evidence limitations. Root should open source URLs itself before using the subagent citation handles in the final answer. These source notes are internal intermediates for the requested paper package, not separately published artifacts.
