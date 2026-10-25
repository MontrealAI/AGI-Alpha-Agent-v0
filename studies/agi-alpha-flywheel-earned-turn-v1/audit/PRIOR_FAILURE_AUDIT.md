# Why the prior flywheel failed to earn a retained capability

**Disposition: read-only reconciliation of the frozen Strategy Succession study, not a new experiment.** The audit reads original checkpoints, ledgers, raw output records and source. It runs no candidate, modifies no prior file, and chooses no new parameter using the old confirmation tasks. All 52 files in the prior top-level freeze still match their recorded SHA-256 values. The new audit script and machine-readable report live in the new `earned_turn` study.

The old study's scientific-source identity is `7e5a1dd2dcf7eb00ec055f1858d5dd722cc950f15f33314bb94c456c753845a7`. `PRIOR_FAILURE_AUDIT.json` contains 166 evidence-file identities and the per-stream reconciliation. Paths below are relative to the preserved `strategy_succession/` package. The public source handoff is PR #4896, not a claim of deployment.

## 1. The four facts reconcile

At the fixed primary cumulative budget of 1,000,000 declared units per stream, the raw checkpoint ledger and mission arrays independently reproduce these totals across 12 streams of 72 offered missions:

| System | Attempted | Valid | Qualified / 864 offered | Retained assets | Total charged units |
|---|---:|---:|---:|---:|---:|
| Fixed conventional portfolio | 769 | 768 | 591 | 0 | 11,719,575 |
| Flywheel | 677 | 675 | 517 | 0 | 11,714,786 |
| Equally enabled learner | 677 | 675 | 517 | 0 | 11,714,786 |
| Conventional saved workflow | 615 | 613 | 465 | 0 | 11,749,635 |

The flywheel's 52-outcome advantage over the saved-workflow arm is not an inheritance effect: neither arm retains an accepted asset. The equally enabled learner executes literally the same discovery mechanism after its experimental label is normalized, and it ties the flywheel. The fixed portfolio delivers 74 more qualified outcomes. The no-discovery ablation also delivers 591, while admission and retention ablations are uninformative about their intended mechanisms because no candidate reaches those gates.

The diagnostic evidence is equally specific:

| Diagnostic treatment | Valid / 48 | Qualified / 48 | Mean cumulative units per stream |
|---|---:|---:|---:|
| Inherited methods | 48 | 36 | 888,009.50 |
| Parent removed; direct fallback on later missions | 48 | 37 | 225,339.33 |
| Exact reconstruction allowed | 48 | 36 | 2,239,765.92 |
| Equivalent recipe replacement | 48 | 36 | 889,359.08 |

Inheritance avoids repeated construction relative to exact reconstruction. That advantage does not survive the cheaper, competent parent-free fallback for the later missions. The diagnostic uses correctness-only retention, and none of these forced admissions is a positive product-admission or investment-recovery result.

Sources: `results/confirmation-v1/trials.jsonl`, every primary `checkpoint.json`, all 48 diagnostic `checkpoint.json` files, and the corresponding 12 inherited diagnostic `raw.jsonl.gz` files. The audit recomputes totals from the checkpoints rather than simply accepting the published summary.

## 2. The primary search stopped before admission, not at admission

The immediate failure was an acquisition-allocation mismatch.

- Each acquisition stage had a ceiling of 500,000 units.
- Four qualification tasks required an equal candidate and reference allocation of 50,000 units each: eight allocations, plus 1,024 control units, reserved **401,024 units (80.20% of the entire stage)** before exploration.
- Exploration therefore had at most 98,976 units before additional control reserves and a further 1,024-unit next-call margin.
- `evaluate()` subtracts its state-dependent control reserve from the call allowance and refuses to launch unless at least 18,000 execution units remain.
- The fixed eight-method race needs up to 17 paid evaluations to progress through its six-task training sequence: 8, then 4, then 2, then 1, 1 and 1.

Every primary flywheel stream stops after only **11–13 paid evaluations**. Across all 12 streams there are 140 paid training evaluations; **all 140 are valid and untruncated**. Twelve further requested calls receive a zero-work `CHECK_RESERVE` refusal. No strategy completes all six training cases. No nominee is selected, no fresh qualification pair is executed, and no economic admission test is reached.

Actual acquisition spending is 74,818–79,327 units per stream, averaging 76,575.83. The 401,024-unit qualification reservation is not spending. Its being unspent does not mean the registered next pipeline call was fundable. The search was constrained simultaneously by a stage ceiling, a protected future allocation and the conservative minimum execution allowance.

Do not count every incomplete menu entry as a budget failure. Of 96 method entries, 58 are ordinary valid successive-halving eliminations, 26 are unfinished valid prefixes, and 12 contain the explicit unfunded-call refusal. No primary paid training output is invalid. At the 2,000,000 total-budget sensitivity the same failure repeats because the acquisition-stage ceiling and qualification reservation remain unchanged. At 250,000 total units no training call is funded.

Source locations: `companion/stream.mjs` (`acquire`, `evaluate`, `controlReserve`); `companion/learning.mjs` (`discover`); `protocol/MAIN_PROTOCOL.json`; `results/confirmation-v1/ACQUISITION_FAILURE_AUDIT.json`; per-stream checkpoint `discoveries`, `events` and `ledger`. The new audit independently matches the primary acquisition classifications.

## 3. Root causes must be separated

| Candidate explanation | What the evidence supports | What it does not support |
|---|---|---|
| Corrupt implementation or invalid produced plans | No such defect explains primary candidate failure. The frozen code's reserve and stop rules agree with the recorded outcomes; all paid training prefixes are valid. | Passing these checks does not certify the entire implementation defect-free. |
| Poor search allocation | Directly established: a broad race is scheduled with insufficient room for even one fully trained nominee, while 80.20% of the stage is pre-reserved for checks never reached. | The audit does not execute a different allocation or claim that a smaller reserve would yield a useful asset. |
| Expensive construction and evidence handling | Directly established under the declared cost model. Research consumes the same cumulative account as mission delivery, and retained research records are included in every full-state checkpoint rewrite. | Declared units are not CPU instructions, elapsed seconds or money. |
| Representation unsuitable for transfer | Plausible and consistent with the diagnostic. The grammar transfers priority weights and lookahead/repair composition; subsequent missions are unrelated random DAGs. It does not retain a reusable structure-specific index or solver factorization. | There is no proof that all scheduling representations lack useful transfer. Primary gating did not test completed nominees at all. |
| Lack of useful transferable structure | Not established as a universal property. The diagnostic gives narrow evidence against the selected methods under this task distribution: one fewer qualified output and substantially greater cost than direct fallback. | Lack of primary admission is not evidence of economic rejection, because economic admission was never reached. |

The complete-stage marker is recorded before search. A failed dispatch acquisition is therefore terminal for that bounded stage; it is not retried with later spare resources. Subsequent lookahead and repair stages correctly defer with `DEFER_NO_ACCEPTED_PARENT`. This is a finite stopping policy, but it makes the first allocation mismatch fatal to the entire three-stage lineage in every primary stream.

Checkpoint accounting is materially large. The primary flywheel incurs 5,238,180 checkpoint units out of 11,714,786 total units: **44.71%**. Aggregate primary checkpoint spending should not be compared in isolation with a system that completes more missions. The 2M sensitivity is the cleaner cost comparison: every arm serves all 72 offered missions, all qualify 668/864, and the flywheel's mean cost is 1,343,296.58 versus 1,157,022.33 for the fixed portfolio, **16.10% more**. A separate research account and bounded incremental evidence persistence are justified engineering hypotheses, not a discovered performance win.

## 4. Stored ancestry was not productive fresh repair

There are 12 fresh inherited lookahead outputs, all calling the dispatch parent, but only three qualify. Of 12 fresh repair outputs, ten qualify; only one invokes the inherited lookahead parent, and that output misses its deadline. Thus **zero fresh repair outputs both invoke the parent and qualify**.

The selected repair modes explain much of the discrepancy: ten are stable, one selective and one quality. The stable mode's stored parent field does not force an executed call. Aggregate research-wide parent calls mix training of losing candidates, training of eventual winners, qualification, and later delivery. Qualification examples that both call the parent and qualify cannot be relabeled as fresh delivered repair outcomes.

`PRIOR_FAILURE_AUDIT.json` provides all 24 fresh lookahead/repair rows with raw line locations and source hashes. These counts agree with the previously independent ancestry audit. Counter values originate in producer instrumentation; this audit independently attributes and sums them but does not independently trace CPU instructions. The earlier separate checker validates outputs, not necessity of the method.

A second causal weakness precedes the method evaluation. The old `makeTask(...,'repair')` creates a new random job graph, computes a conventional portfolio baseline for that graph, and then adds a disruption. It does **not** derive Mission C from the actual accepted Mission B plan. Therefore the old diagnostic cannot establish a real accepted-project continuation even if its type lineage is valid.

## 5. Admission, adoption and investment need new definitions

The prior `admission()` gate compares the candidate after acquisition spending with an incumbent counterfactual that never spent that acquisition budget. It also subtracts full acquisition from projected savings. This is a full-investment forecast, not the marginal question of whether an already constructed valid asset should now be used. No primary flywheel candidate reaches it, so changing the formula alone cannot explain away the observed failure.

The new study should maintain three separate records:

1. Correctness and applicability: the exact method meets its declared scope and checks.
2. Product adoption: expected future quality/resource benefit against the best current alternative, including incremental use and maintenance costs.
3. Investment recovery: realized or forecast cumulative benefit covers all attributable discovery, failed attempts, construction, evaluation and integration, with unknown human and monetary costs left unknown.

No old result establishes commercial profit, operator-time savings, an earned resource balance or an increasing improvement rate. The old implementation expressly contains no saved-capacity reinvestment mechanism.

## 6. Bounded next hypotheses

The strongest next experiment is not simply a larger version of this race. It should select among a small, declared set of candidate domains and test a family with repeatable structure, changed queries and inexpensive direct methods. A reusable representation must remove real repeated work, and a distinct child capability must be built from the actual accepted preceding state.

Four separable hypotheses are justified by this audit:

- Repeated immutable structure can make a reusable representation pay, if tested against conventional caching, the strongest direct method and the cheapest competent equivalent builder.
- Independently enforced service and improvement accounts can preserve promised useful work when research fails.
- The retained representation can reduce the construction or qualification cost of a distinct capability, against removal-with-reconstruction and a competent parent-free implementation.
- Measured released capacity can fund a bounded next construction only if that capacity is actually reusable and explicitly debited. Abstract operation savings alone do not establish cash or available execution time.

The old confirmation remains historical evidence. Any alternative allocation, new domain, method, task generator or acceptance rule receives a new identity and genuinely new confirmation tasks. The new audit does not authorize an unlimited search for a favorable benchmark.

## Reproduce this reconciliation

With the preserved old package beside `earned_turn`, run:

```bash
python3 earned_turn/audit/audit_prior_failure.py
```

The script verifies the old 52-file freeze, rereads checkpoints and compressed raw output records, checks ledger and summary consistency, and writes only the new audit report. It never runs an old candidate or writes under `strategy_succession/`.
