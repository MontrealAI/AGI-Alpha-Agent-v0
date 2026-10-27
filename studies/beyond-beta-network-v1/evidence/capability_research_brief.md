# Autonomous optimization foundry: capability evidence and falsifiable design

Evidence checked 2026-10-26. This is a new research design, separate from the preserved human-market-surplus study. No frontier API experiment, customer job, or autonomous invention was performed for this brief.

## Recommendation

Use an autonomous foundry for **formally specified, non-safety-critical scheduling and allocation algorithms**. A campaign accepts structured constraints and an authorized objective; produces an executable solver or policy, an independently implemented outcome checker, a reproducible benchmark manifest, and a bounded adapter; and abstains if it cannot establish the promised result. Recurring triggers are changed instance distributions, new permitted constraints, solver/runtime changes, and a buyer's recurring performance problem. Do not claim that arbitrary natural-language business requirements are already a formally correct specification.

The commercial outcome is an accepted useful artifact, not a guaranteed mathematical breakthrough. Sometimes a competent use of an existing solver is the best outcome. The foundry may stop searching, deliver that supported outcome if the contract allows it, or decline an improvement contract that it cannot fulfill. No routine provider human review or manual onboarding belongs in the primary model. Automated intake, clarification, specification testing, failed search, correction, packaging, recovery, revalidation, and obsolescence all consume resources.

## Evidence and its limits

The source register accompanies this note. All external results below are **reported by external sources**, not observed in our work.

| Original source | Useful evidence | What the study cannot infer |
|---|---|---|
| [AlphaEvolve, Novikov et al., 2025](https://arxiv.org/html/2506.13131v1) | Gemini-based code evolution uses executable evaluators, evaluation cascades, and whole-program changes. Its scheduling example used unseen workloads; the authors report 0.7% fleet compute recovery. Some evaluations may consume about 100 compute-hours per candidate. | An Astra success probability, a universal cost saving, or human-free completion of every reported application. The compiler-IR application explicitly received final human correctness confirmation. |
| [FunSearch, Romera-Paredes et al., 2023/2024](https://www.nature.com/articles/s41586-023-06924-6) | Program search with automated scoring improved online bin-packing heuristics on held-out OR-Library instances and sizes. The learned object is a generator or decision procedure, not a memorized list of outcomes. | A rate for customer acceptance. Cap-set reformulation included researchers examining discoveries and refining the search. |
| [AlphaDev, Mankowitz et al., 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10247365/) | Assembly-level search combined correctness and latency feedback; discovered small-sort routines entered LLVM. Training used substantial specialized resources. | A production LLM's cheap invention rate or a claim that testing arbitrary code proves universal correctness. |
| [Evolution of Heuristics, Liu et al., ICML 2024](https://arxiv.org/html/2401.02051v3) | An independent team evolved verbal ideas and executable heuristics for packing, routing, and flow-shop scheduling. Guided-local-search variants changed intermediate landscapes while final evaluation used the original task objective. | Superiority to all current solvers, or automatic transfer of its reported gains to modern frontier models. |
| [CodeEvolve, Assumpção et al., version 3](https://arxiv.org/html/2510.14150v3) | An independent open framework records execution failures and studies search components. Reported best-run costs and runtimes differ materially by model and benchmark. | A complete commercial cost estimate: best-run token expenditure does not include every failed research attempt, engineering task, or buyer obligation. |
| [Effective Harness Engineering, Ishibashi et al., 2026](https://arxiv.org/html/2605.15221v1) | A small independent circle-packing study reports evaluator exploitation and mixed benefits from extra memory or verification. | A calibrated hack rate or a general causal advantage from deeper reasoning: the experiments are narrow and configurations differ. Its secondary LLM judgment is not an independent mathematical proof. |

These sources support **possibility and workflow structure**. Their benchmark gains do not set the economic simulator's acceptance, demand, transfer, or invention probabilities. Three of the prominent systems are their vendors' own research; the independent studies are useful corroboration with narrower evidence than a production pilot.

## An explicit I/F/E separation

The local *Transformational Intelligence: Learning to Change the Game* manuscript supplies the intent/formulation/evaluation distinction. Its exact illustrative result is not evidence of frontier-model invention. Apply the distinction as follows.

**Intent I:** Return a schedule or policy obeying the supplied constraints and improving the buyer's declared objective within a stated computation and delivery budget. Changing the objective or omitting a constraint is not an improvement. Permission boundaries remain fixed.

**Formulation F:** The representation, permitted observations of the supplied simulator, decomposition, search operators, and intermediate targets used to reach I. A candidate may propose a different constraint encoding, decomposition plus exact repair, informative experiment, or surrogate search objective. It must say what structural restriction changed.

**Evaluation E:** A separate implementation recomputes feasibility and the original objective from the original instance and returned solution. Performance is measured on fresh instances and a pinned runtime. A revised evaluator must pass its own validation and be assessed on an untouched holdout; it cannot retrospectively upgrade an old score.

## Exact executable bridge and falsifier

For a bounded job-shop domain, inputs contain integer durations, job precedence, machine assignments/capacities, release times, a finite horizon, and the selected objective. Every output must enumerate each required operation once. A separate checker, which does not import candidate feasibility or objective code, recomputes operation ends, nonnegative starts, precedence, release constraints, machine occupancy, and the objective from original inputs. It rejects duplicates, omissions, non-finite values, unsanctioned resources, and altered durations. Mutation tests deliberately violate each constraint type and must be rejected.

This establishes feasibility **relative to the supplied formal specification** if the checker is correct. It does not establish that a factory's unstated requirements were captured. A small exactly enumerable domain can supply ground truth for checker tests. On larger instances, do not label a feasible schedule optimal unless a valid lower bound matches it or a trusted complete proof establishes optimality. OR-Tools distinguishes FEASIBLE, OPTIMAL, INFEASIBLE, MODEL_INVALID, and UNKNOWN; a timeout is not a proof of infeasibility. See the [official job-shop formulation](https://developers.google.com/optimization/scheduling/job_shop) and [CP-SAT status documentation](https://developers.google.com/optimization/cp/cp_solver).

The performance falsifier is straightforward: replay the same fresh instance under identical hardware, resource limits, objective, and permissions with the best permitted baseline. Reject the improvement claim if the candidate violates any constraint, the held-out benefit is below the contract threshold, its cost erases the benefit, or a relevant shifted distribution makes it harmful. Report feasible-but-unimproved cases separately from incorrect cases. A scalar score or LLM agreement cannot override a failed executable check.

## Competent baselines and complementary changes

All comparison arms receive the strongest appropriate frontier configuration, current known solver libraries, adequate context, ordinary task decomposition, correction, and access to the same permitted information. OR-Tools CP-SAT and suitable established heuristics remain available. A missing saved file is not evidence that an agent lacks a known method. Baseline capability is measured by what the agent can reconstruct or already use within the same complete budget.

One candidate bundle is **A**, a family-specific representation or decomposition, plus **B**, a repair/constraint adapter and informative counterexample suite. Either component alone may be useless or harmful. Evaluate neither, A only, B only, and A+B on matched fresh campaigns. For a higher-is-better net metric V, the interaction is V(A+B)-V(A)-V(B)+V(neither). Report its sign and uncertainty; do not insert a positive interaction as a guaranteed property. A separate equal-resource search control tests whether the apparent transformation was merely more compute.

A reusable asset may reduce reconstruction tokens, reduce repeated evaluation through a validated cheap screen, provide useful instance features, or reduce the number of candidates required to find a useful method. These are different mechanisms. Each must affect the relevant resource or observable event, not multiply every success rate. A cheap screen must retain an independent final check; false negatives can suppress a real discovery and false positives can increase downstream cost. Shared misunderstandings correlate producer, critic, and evaluator failures.

## Independent invention campaigns and self-acceleration

Use a campaign ID distinct from descendant job IDs. A campaign includes specification work, all unsuccessful candidates, executable evaluations, checker construction, integration, and final confirmation. Replaying a retained solver on more jobs demonstrates reuse, not faster invention.

To test stronger self-acceleration, launch fresh campaigns with disjoint target families or held-out distributions, fresh seeds, and identical budgets and permissions. Compare the complete cost, latency, and probability of obtaining a newly useful validated capability with and without a retained invention asset. Include unsuccessful campaigns in the denominator. Improving later capability construction or validation at matched quality supports this narrower modeled claim; increased revenue or more descendant jobs alone does not.

Heterogeneous recipients may already possess an equivalent strategy. Acquire or share only when expected incremental benefit exceeds adaptation, validation, maintenance, and opportunity costs. Record overlap, successful reconstruction without transfer, failed transfers, copies, and expiry. Identity attestations and Merkle inclusion do not establish capability quality or commercial value.

## Exploration ranges, not calibrated rates

The following are proposed **assumed or explored** ranges, intentionally broad. They are a design menu, not a frozen primary parameter set. The primary protocol must choose and justify its values before final outcomes.

| Quantity | Suggested exploration | Reason for the parameter |
|---|---|---|
| Campaign candidate budget | 50, 200, 500, 2,000, 5,000 | Search can be much more expensive than one delivery; external papers motivate order-of-magnitude exploration only. |
| Total billed Astra output per candidate, including reasoning/internal Pro work | 5k–100k tokens, with per-call limits respected | This must be charged explicitly; no fixed Pro multiplier. |
| Executable-candidate rate | 0.25–0.95 | Syntax/runtime success is distinct from useful innovation. |
| Shared semantic/specification failure | 0–0.15 per campaign | Independent-looking role calls may repeat one wrong interpretation. |
| Productive campaign probability at a fixed complete budget | 0–0.60 | No source calibrates Astra on this offering; zero is an essential case. |
| Fresh-instance net improvement over the strong baseline | Negative, zero, and 1–15% positive cases | Known solvers may already be optimal or close enough that search is wasteful. |
| Evaluation compute per candidate | Seconds to hours; 100 compute-hours as a severe task context | The large AlphaEvolve evaluation figure is not a default for small scheduling instances. |
| Equivalent existing capability among recipients | 0.25–0.90 | Frontier agents must not be treated as empty workers. |
| Transfer/adaptation failure | 0–0.40 | Artifact availability does not guarantee usefulness. |
| Useful lifetime | 3–24 months | Drift and solver/runtime upgrades can erode value. |
| Invention-cost ratio on fresh campaigns after an asset | 0.5–1.5, explicitly including 1 | Faster invention is a hypothesis; integration can make it slower. |
| Search-outcome common dependence across candidates | 0, 0.4, 0.8 latent correlation settings | Many retries need not be independent chances of success. |

Do not make acquisition decisions using a latent true gain. The controller sees only prior observations, declared scope, available cash, and a forecast with uncertainty. Waiting, retaining cash, abandoning a campaign, and buying a complementary bundle are valid actions. A history of repayment may inform risk, but full prior repayment and exactly two investments are not mandatory rules in this new study.

## Resource accounting with current models

Official pages rechecked on 2026-10-26 support Astra for difficult reasoning/coding and Terra for visual execution; see `model_recheck.json`. The requested configuration is Astra `reasoning.mode=pro`, `reasoning.effort=max` for demanding production, critique, and capability evaluation; Terra `max` for justified visual/computer-use work. The strongest appropriate configuration is selected by stage; no quality improvement is assumed merely because the mode is expensive.

Every role must expose ordinary input, cache-read, cache-write, and total output including reasoning. Pro aggregates internal work at the selected model's token rates. Count tools, solver compute, sandbox sessions, storage, automated intake, packaging, monitoring, recovery, and failed/abstained work. Do not charge reasoning a second time after it is included in output. Apply long-context premiums per individual request, not to a campaign's aggregate token sum. Subscription access is separate from API use and conveys no assumed production quota.

Illustrative arithmetic, **not a measurement**: one candidate using Astra 100k ordinary input and 20k total output costs USD2.00; a critic using 40k input and 5k output costs USD0.65; a Terra packaging/execution allocation of 20k input and 3k output costs USD0.035. Five hundred such units total USD1,342.50 before solver compute, intake, final checks, recovery, storage, and fixed operation. The simulator should generate costs from such explicit units instead of choosing a profitable round-number campaign cost.

## Claim discipline

The model may establish autonomous service viability under stated assumptions and conditional investment value. External algorithm-discovery evidence supports serious scope and a plausible mechanism. It does not establish the proposed venture's buyers, realized sales, deployed autonomy, or measured self-improvement. Keep those claims separate, and preserve zero-gain, strong-baseline, correlated-failure, queue, demand, and expensive-validation cases.
