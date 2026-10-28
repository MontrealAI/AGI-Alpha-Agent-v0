# AGI ALPHA FLYWHEEL
## The Enterprise That Invents Its Next Advantage

**Transformational Intelligence, Specialist Learning and the Creation of New Profitable Work**

**Paper by Vincent Boucher, President of MONTREAL.AI**

FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.

This package executes a bounded manufacturing-planning experiment and a matched enterprise simulation. It asks whether productive experience creates a transferable capability, whether optional additional training improves it, and whether the resulting advantage supports a worthwhile next offering. The numerical schedules, policy updates, fresh transfer and native accounting/control fixtures execute. Frontier-model behavior, customers, collections and enterprise economics are conditional models.

Start with the [paper](paper/enterprise-next-advantage.pdf), its [LaTeX source](paper/enterprise-next-advantage.tex), the [English/French browser edition](web/index.html), the [proposed pilot operating blueprint](OPERATOR_BLUEPRINT.md), or the [reproduction guide](REPRODUCE.md). The browser edition embeds its report data and can be opened offline. Local artifact links work when the complete directory structure is preserved.

## What the executed study supports

The primary numerical comparison uses **80 fresh synthetic missions** across four strata, with 32–64 jobs and 3–4 machines. It retains a competent, bounded generic dispatch/search portfolio as the algorithmic Beta comparator. It does not measure the capability ceiling of a current frontier model.

| Finding | Executed result | Scope |
| --- | --- | --- |
| Productive learning | v1 reduces nominal objective by 7.71% on average relative to Beta | Eight simulated productive-development jobs; actual numerical parameter search |
| Additional Gym | v2 reduces nominal objective by 9.04% relative to Beta; the incremental reduction over v1 is 1.42% | Same 48-candidate serving budget; no proprietary model-weight update |
| Fresh transfer | Serialized v2 policy is reloaded for fresh recipient missions | Local execution with synthetic agent labels; no live ENS admission |
| Robust planning | v2 with scenario ranking reduces the robust objective by 7.81% relative to matched Beta | Both receive the same scenario-ranking component and selection budget |
| Composition alone | Additional scenario ranking yields an estimated 0.59% increment with an interval spanning zero | Extra computation; no established independent composition gain |
| Generic catch-up | On a secondary twelve-case fresh sample, Beta144 beats learned48 on mean objective by the reciprocal comparison | Three times the candidate count; very small measured extra solver time |

Primary technical acceptance is unchanged throughout: feasibility plus at least 3% nominal improvement or 5% robust improvement over a synthetic EDD incumbent. Beta accepts 76/80 nominal and 78/80 robust cases; learned variants accept 80/80. These outcomes do not establish customer acceptance. The 24 development cases all passed the primary criterion, so confirmation differences cannot be used retrospectively as decision priors.

The stronger-Beta addendum uses twelve further fresh cases, seeds 61000–61011, with all three methods on identical problems. Beta144 improves on Beta48 by 4.49% nominal and 6.27% robust. Learned48 has a mean advantage of **−1.42% nominal and −2.10% robust relative to Beta144**, with substantial small-sample uncertainty. All methods pass the primary criterion on all twelve cases. The threefold generic search is an economically important alternative to learning and retention.

The original CP-SAT challenge and its higher-budget extension returned feasible schedules but did not improve their warm starts. Bounds remained wide. This does not demonstrate superiority over an extensively optimized industrial solver. The expanded classical-parameter-grid challenge also failed to improve the baseline consistently; it is not labeled a stronger successor.

## What is sold in the bounded operating blueprint

The initial offering is a **schedule-design and comparison package** for a buyer who supplies an approved finite batch of jobs, eligible machines, processing estimates, release times, due dates, priorities and setup families. The deliverable is a reproducible feasible schedule, machine/job assignments, an independent constraint check, objective comparison and documented operating limits. It is planning support, not direct production-machine control.

The adjacent offering evaluates the schedule under declared processing-duration uncertainty and common shocks. It is a risk-aware planning package within that model. Machine-breakdown calendars, multistage job-shop precedence, worker qualifications and arbitrary factory constraints are not implemented by this numerical kernel. A real contract must add and validate any such required constraints before promising acceptance.

An operator should:

1. Validate the customer's data and agree on the objective, required constraints, deliverable, turnaround and acceptance rule before execution.
2. Offer the bounded initial planning service only after a real buyer demonstrates willingness to pay. The study's human-service reference and price search are estimates/scenarios, not observed sales.
3. Compare ordinary additional search, retained v1 and optional Gym at complete cost. An unneeded training campaign is not an operating requirement.
4. Evaluate the robust service against an actual buyer's need. Beta can also offer it; unique product creation caused by specialist composition is not established here.
5. Retain or share a capability only when fresh quality, rights, serving cost, upkeep and expected demand justify it. A summary of a policy is not equivalent to its executable artifact.
6. Keep cash, suspend an unproductive offering, or stop optional development when the evidence favors that choice.

The enterprise simulator permits those choices and reports collections, receivables, complete expenses, profit, reserves and available funds separately. A/B/C activity records are disjoint. Numerical-learning formation during the originating productive campaign is not charged a second development bill. Additional Gym, assessment, sharing and upkeep retain their own costs. No modeled collection in this package is actual earned revenue.

The supported economic boundary is mainly **incremental investment value**, not a located universal business break-even point. All primary scenario-policy mean accrued profits are positive (minimum about USD 4,313), as are the displayed demand–cost grid means (minimum about USD 2,546). The separate stricter-quality supplement does contain absolute losses: under thin demand, initial-offer Beta averages about USD 2,646 at a 20% improvement contract, −USD 1,455 at 30%, and −USD 3,502 at 40%. These conditional outputs bracket a sign change between tested contracts for one policy and assumed market; they do not locate the boundary for the best feasible enterprise. Optional learning is skipped throughout that thin-demand supplement.

## Lineage, methods and evidence

The researcher authored the problem generator, dispatch family, feedback and cross-entropy update procedure. The computer then learned seven dispatch parameters through **512 v1 and 2,880 v2 schedule evaluations**. All 184 parameter candidates, including unsuccessful candidates, remain in the evidence. Eight source jobs have saved Beta/v1 schedules and independent acceptance results. The policy transfers as serialized parameters plus the executable scheduler; there is no claim of autonomous algorithm discovery or proprietary-model fine-tuning.

| Item | Location |
| --- | --- |
| Primary protocol and source/policy freeze | `config/numerical_protocol.json`, `evidence/numerical/policy_freeze.json` |
| Productive jobs and delivered schedules | `evidence/numerical/productive_experience_cases.json`, `productive_deliveries.json` |
| Learned policies and all search candidates | `evidence/numerical/policy_v1.json`, `policy_v2.json`, `all_learning_candidates.json` |
| Fresh full schedules and acceptance | `evidence/numerical/confirmation/` |
| Economic calibration with development-only priors | `evidence/numerical/economic_calibration.json` |
| Every prespecified secondary quality tier | `evidence/numerical/quality_frontier.json` |
| Final stronger-Beta fresh calibration | `evidence/numerical/beta144_confirmation/calibration.json` |
| Matched enterprise outputs | `evidence/economics/` |
| Supplemental quality/economic frontier | `evidence/expansion_frontier.json` |
| Native source identities and validation record | `provenance/runtime_source_manifest.json`, `provenance/native_validation.json` |
| Source classifications and primary references | `provenance/source_map.json`, `provenance/primary_sources.json` |
| Package integrity | `evidence_manifest.json`, `verify_evidence.py` |

The original interrupted source is retained in `evidence/numerical_interrupted_source/`. It completed 24 development cases and six confirmation cases before a provenance/input-isolation repair. Those confirmation outcomes were not used to tune the policy. The final primary source uses fresh seeds 51000–51079. `research_execution_overhead.json` reports the known executed workload, including the interrupted attempt, and explicitly identifies unmeasured overhead.

## Integration and authority boundaries

The study freezes the upstream AGI ALPHA source at commit `80b345828f34fd8a6e592977dd17ef37141305f4`. The eighteen-file closure in `vendor/runtime/` is checked against `provenance/runtime_source_manifest.json` before native execution. It reuses the actual Journal, trust/signature, cost-ledger, protected-access and public lifecycle code.

Native fixtures execute real cryptographic checks against synthetic identities and RPC responses. They test revoked authority, replay and unauthorized access; duplicate A/B/C charging; unknown costs; and invoice-versus-collection distinctions. The current protected capsule schema **correctly refuses arbitrary scheduling capability admission**. This study does not change Jobs validator roles, governance, settlement or execution authority, and does not claim live authenticated scheduling access.

The ordinary-library comparison uses identical content and permissions. No graph-specific premium is claimed. The paper and browser edition remain research artifacts until the existing repository review and publication process qualifies them; a local file or a GitHub source branch is not evidence of a deployed public release.

## Timing, economic assumptions and practical limits

`solve_seconds` is measured with `time.perf_counter()`. It includes schedule construction, candidate ranking and the per-candidate checks inside the solver. It excludes the final independent 64-scenario acceptance calculation, artifact serialization, process startup and engineering effort. It is elapsed solver time, not a metered cloud invoice or exact CPU usage.

The conversion at USD 3 per solver-hour is an explicit cost proxy. On the secondary fresh sample, additional generic search costs about USD 0.00026–0.00028 per job under that proxy. The numerical v2 campaign itself took 6.42 measured seconds in the final primary run; a modeled USD 420 Gym campaign includes additional assumed orchestration/validation/engineering work and must not be described as measured GPU/API expenditure.

The enterprise scenarios include unsupported demand, buyer choice, campaign-success and transfer assumptions. Bootstrap intervals describe numerical task sampling; Monte Carlo intervals describe simulation variation conditional on its inputs. Neither captures the full uncertainty of real markets, model behavior or the synthetic task generator. A viable Beta business, a transferable specialist, worthwhile sharing and sustained commercial compounding are distinct findings.

## Validation and provenance

Nine directed numerical integrity tests pass, covering invalid schedules, serialization, uncertainty replay, hidden-truth isolation and the CP-SAT interface. Other native, economic and frontier checks are recorded separately; consult the final validation record for their exact scope and counts. A hash verifies artifact identity, not scientific or commercial validity. Full repository release qualification and live customer/identity/provider trials are separate gates.

The final standalone suite passes **44 tests**, Ruff lint passes, and the bilingual browser passes all **154 primary selections**. The [final validation record](provenance/final_validation.json) also preserves the strict mypy result: **12 errors in seven research files**, not a passing type-check. See [review and publication status](PUBLICATION.md) for the required hosted and release gates. The source that produced frozen evidence is not silently rewritten to conceal a diagnostic.

The work was developed with AI assistance, including researcher-authored code and manuscript support, numerical implementation, checks and interpretation. The named author line does not convert synthetic identities, modeled sales, proposed mechanisms or same-team verification into independently observed deployment evidence.

The upstream [Apache 2.0 license](vendor/runtime/LICENSE) is preserved. This repository is a conceptual research prototype; references to AGI and superintelligence describe ambitions rather than demonstrated general or superhuman intelligence.
