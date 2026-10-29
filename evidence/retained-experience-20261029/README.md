# Retained experience: executed comparison, 29 October 2026

The native `experience` implementation constructs fresh fixed-route scheduling
certificates from verified historical constraint sets and infeasibility witnesses.
It compares that treatment with six complete HiGHS configurations, template caching,
ordinary result caching and a conventional HiGHS warm start.

**The requested complete-cost advantage is NOT DEMONSTRATED.** The treatment
reduces measured deployment CPU, but learning and verification overhead reverse
that advantage over this 64-task horizon. Complete monetary cost remains UNKNOWN.
The conventional production defaults and all prior negative evidence are preserved.

| Actual endpoint | Retained experience | Strongest whole-panel control |
| --- | ---: | ---: |
| Control identity | Frozen historical bases/rays | `highs-ds-1` (dual simplex, presolve on) |
| Fresh tasks | 64 | Same 64 |
| Independently accepted observations | 192/192 | 192/192 |
| Median-per-task deployment CPU, summed | 1.439854 s | 1.869313 s |
| Training/selection/construction/preparation CPU | 1.808256 s | 0 s: pre-existing fixed method |
| Lifecycle CPU, including additional independent verification | 5.086064 s | 2.592862 s |
| Observations requiring no new LP solve | 183/192 | 0/192 |
| Complete modeled monetary cost | UNKNOWN | UNKNOWN |

Deployment CPU is 22.974% lower; lifecycle CPU is 96.156% higher. No result is
promoted on the favorable partial comparison. Sixty-one of the 64 treatment tasks
use retained methods without a fresh LP solve, consistently across three timings.
The task set has 16 feasible schedules and 48 infeasibility diagnoses. A correct
diagnosis is not a transported passenger or a newly feasible business activity.

The full planned denominator is **64 tasks × 10 arms × 3 timing repeats = 1,920**.
All 1,920 outputs pass the unchanged Decimal feasibility checker and, for feasible
outputs, an independently reconstructed dual optimality bound. Accepted objective
gap is at most `1e-5`. There are 480 feasible-schedule observations and 1,440
infeasibility-certificate observations, with no conflicting accepted outcomes.
Repeated timings are not independent tasks or customer deliveries.

`prospective-v1/` retains the protocol, source/dependency freeze and source
snapshots, all 54 development comparator outputs, nine chronological source tasks,
retained and ordinary memories, frozen fallback, fresh-seed record, all 64 inputs,
every result, unique delivered-work cost records, independent verification and
summary. The candidate, fallback and lifecycle setup costs were frozen before
sampling the evaluation seed. The evaluation cannot update historical memory.

The sealed result is
`a1eee42f8701ebceaa53b88d1f59fd15744121317ce1fcb0df1213529295736c`.
From the matching source checkout:

```sh
alpha-agent experience check evidence/retained-experience-20261029/prospective-v1 \
  --seal-sha256 a1eee42f8701ebceaa53b88d1f59fd15744121317ce1fcb0df1213529295736c
```

The separate verifier demonstrates denied file writes and new sockets, imports no
candidate solver, reconstructs historical basis provenance and checks the whole
denominator. It shares authorship, host, libraries and the pre-existing checker;
this is procedural separation, not external certification. The actual whole
experiment uses 67.814 s parent CPU, 22.800 s verifier CPU and 90.597 s wall time.
Those research resources are reported separately from mutually exclusive
counterfactual one-pass deployment costs. Later validation/replay incurs additional
resources and cannot reclassify the original exposed cases as fresh.

The initial `development-smoke-v1/` remains intact with its original source
snapshots and adverse result: one of 40 outputs was refused because a tiny dual
multiplier exceeded the checker’s supported decimal precision. The producer now
omits numerical-noise multipliers and recomputes the rigorous residual bound. The
checker and acceptance tolerances remain unchanged. The new producer passes an
explicit regression on that exposed old case. This is engineering repair, not
fresh scientific evidence. The smoke and final panel are separately identified.

This is exploratory generated work within one public raw instance and fixed-route
family. There is no statistical confirmation claim or reset of earlier campaigns'
error budget. All monetary rates are explicit modeled assumptions, retention size
is a disclosed proxy, and authoring, human, energy, hosting and opportunity-cost
inputs remain null unless supplied. No paid API call, customer sale, profit,
earned-funded successor or broad invention advantage is established.

See [the operator and accounting guide](../../docs/agent/RETAINED_EXPERIENCE.md).

## Failure feedback increment

The additive `experience plan-retention` command uses this sealed historical
result to construct a future reuse constraint. It reconstructs the cost ledger,
retains the cost failure with provenance and compares every declared control.
The numerical solver, controls, experiment runner and verifier remain byte-identical
to the original `f2637be7` source. The CLI registration changes, so the original
strict source qualification remains attached to that historical commit.

Actual native CLI records are in `feedback-v1/`:

- `plan-64.json` keeps the incumbent. Deployment savings still do not repay the
  measured overhead, and the additional planning CPU is included in the projection.
- `plan-100000.json` is a projection over 100,000 possible tasks, **not 100,000
  executed tasks**. It returns `MEASURE_VERIFICATION_SCALING_FIRST`: treating all
  unallocated checking overhead as fixed produces a different conclusion from
  treating it as recurring. The original experiment did not measure that split.
- Both retain UNKNOWN complete monetary cost, no established future benefit,
  no production authority and no fresh confirmation claim. No old evidence changes.

The next fresh test must resolve the fixed/recurring verification cost split and
then compare useful outcomes and complete costs. A longer assumed horizon cannot
turn this negative result into a successful demonstration. Projection assumptions
and exposed source cases are explicit. Thirteen added regression cases cover exact
cost intervals, changing strongest controls, zero-cost ties, false summaries,
trusted seals, bounds and overwrite refusal. The combined suite passes **154 tests**.
See `feedback-v1/VALIDATION.json` and the actual `tests.txt` record.
