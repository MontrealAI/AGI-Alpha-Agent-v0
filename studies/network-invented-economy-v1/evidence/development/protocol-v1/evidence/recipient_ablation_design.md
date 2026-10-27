# Frozen-recipient cost comparison and lifecycle thresholds

## Implemented experiment and evidence status

`src/recipient_ablation.py` executes deterministic **modeled cost comparisons**.
It does not execute frontier models, sell a service, spend cash or translate the
mechanism witness's operation counts into dollars. Every workload comes from the
simulator's explicitly assumed `Work` catalogs and is priced by its current
`Work.cost`. The source/configuration freeze must bind this module, its tests,
the simulator and `alpha_assessment.py` together.

The module has three public entry points:

```python
probe_recipient(scenario, recipient, mission, bundle,
                validation_overhead=1.0, frontier_factor=1.0)
assess_lifecycle(scenario, recipients, mission, bundle, plan,
                 weights=None, validation_overhead=1.0,
                 frontier_improvement=None)
run_recipient_ablation(scenario=None)
```

The final function returns the declared deterministic panel for integration into
the confirmation harness. It uses no random seed, external service or trial
outcome. Its arithmetic smoke run and invariant tests occurred during development;
replaying the same panel after freeze verifies reproducibility, not an unseen
statistical confirmation. The enterprise's independent confirmation worlds remain
a separate experiment.

Standalone reproduction from the study directory:

```sh
python3 -m unittest tests.test_recipient_ablation -v
python3 -m src.recipient_ablation --out results/recipient_ablation.json
```

## What is frozen and what is removed

A `RecipientSnapshot` holds a described, versioned competent Beta baseline,
ordinary experience factors and already held equivalent methods. Beta knows the
underlying theory, has appropriate frontier models and tools, and can reconstruct
all required methods. Ordinary familiarity changes required reconstruction work;
it does not multiply intelligence, quality or acceptance probability.

A `FrozenMission` fixes purpose/domain, required components, common production,
intake, validation and packaging work, cash available for that mission, total
input/output allowances and deadline. These allowances are identical in both
branches. Work latency is serial and local; this comparison does not simulate
enterprise queue dynamics. A `CandidateBundle` specifies the only removable
artifact, its residual execution work, exact assessed Beta, scope, status,
expiry and revalidation due date. The candidate record is an analysis input,
not an authenticated graph execution permit.

The counterfactual removes only that candidate. It preserves all ordinary
experience, model/tool configuration and existing equivalents. For each component,
Beta uses the less expensive eligible ordinary reconstruction or already held
equivalent route. Candidate selection cannot erase an inconvenient equivalent.
The complete inputs and comparator state have deterministic SHA-256 bindings.

The panel contains five recipient states: a competent frontier reconstructor,
an ordinarily experienced recipient, a specialist, a recipient with one existing
equivalent, and a recipient with complete equivalents. Their workload factors
are stated assumptions. They are not observations that real agents differ by
the corresponding amount.

## Explicit transfer branches and optional use

For each eligible subset of the three candidate components, the model calculates
three complete routes:

1. Successful adaptation pays the candidate's residual work, per-component
   integration and receiver checking, plus unaffected ordinary components and
   common delivery work.
2. Failed adaptation pays the full attempted work, the original competent Beta
   reconstruction route and correction/recovery.
3. Harmful adaptation pays the failed route plus a complete additional delivery
   validation workload.

The assumed probability masses are `transfer_success * (1 - harmful_transfer)`,
`1 - transfer_success`, and `transfer_success * harmful_transfer`. They sum to
one. These are scenario probabilities, not measured frequencies. Optional use
selects the least expected-cost route before learning which branch occurs.
If none improves on Beta, the candidate is not used; duplication does not force
an integration penalty on the mission. Availability and lifecycle infrastructure
can still cost money.

Failure routes are assumed to recover the same functional scope if their resource
requirements can be met. This isolates cost rather than inventing a quality
improvement. Unresolved specification errors, false passes and commercial
acceptance remain in the enterprise simulator; this panel cannot estimate them.
Every conditional route records cash, input, output and serial-latency constraints.
Positive expected cost savings alone cannot recommend investment when a
positive-probability route cannot finish within those limits.

“Newly feasible” has only an operational meaning here: the fixed required route
crosses the same mission cash/quota/deadline threshold with the candidate. It is
not a claim that the method was previously unknown to frontier intelligence.
Required costs for an infeasible route are disclosed counterfactual requirements,
not expenses that were actually paid.

## Complete lifecycle accounting

`LifecyclePlan` supplies explicit upfront costs, a failed-construction subset,
historical research allocation, weekly upkeep/distribution, periodic revalidation,
moving-Beta reassessment, useful life, expected uses per week, an available
investment-cash amount and an optional uncertainty allowance per use.

The standard plan charges simulator construction work for one successful attempt
and one failed attempt, plus a separate evaluation/revalidation allowance and
creator compensation. Failed construction is a disclosed subset of construction,
not a second addition. The weekly allocation charges the bundle's maintenance and
the full declared network distribution/access overhead; alternative allocations
must be passed explicitly. Those workload and allocation choices are assumptions.

Receiver integration, full checking, failed transfer and recovery are already
deducted in each paired delivery saving. They are not charged again in the
`AlphaCosts` wrapper. Upfront construction, failure, confirmation, distribution,
upkeep and subsequent revalidation/reassessment are additional lifecycle costs.
The total project view retains historical costs. The prospective continuation
view excludes that historical amount from the decision to spend again.

`AlphaAssessment` receives actual deterministic paired-cost calculations across
the declared weeks, with `source_kind="simulation"`. There are no random gain
multipliers or manufactured empirical pairs. Weeks are not independent samples;
the reported lower/upper arithmetic bounds are not confidence intervals. A
one-week projection is reported without fabricating a second pair to satisfy the
assessment schema. The assessment binds a declared baseline **path**, not a single
production graph baseline, and is not directly an admission authorization.

The module reports strict required reuse, the first lifetime with positive lower
net benefit, and the first lifetime that remains positive through the end of the
tested range. This last distinction matters when later upkeep or Beta improvement
erodes an early payback. A missing crossing is reported as `null` rather than
extrapolated into a favorable lifetime. Required reuse at a fixed declared lifetime
holds its allocation and mean savings fixed; it is a conditional threshold, not
an observed demand forecast.

Upfront affordability is checked against currently supplied investment cash.
Projected later savings cannot fund today's construction. The module does not
replace the enterprise's finite-cash event ledger: it contains no customer
collection timing, financing schedule or enforceable payment obligation.

## Moving Beta and predeclared sensitivity panel

Ordinary reconstruction cost improves along the declared annual rate, with the
simulator's 0.15 residual-work floor. The candidate's own residual work remains
fixed, so a moving Beta can eliminate its advantage. Beta epochs are versioned.
Reassessment can either be paid or omitted; omitting it blocks candidate use after
the baseline version changes. Periodic revalidation and reassessment are assumed
to succeed in this cost surface and are charged. Failure, revocation hazards,
copying dynamics and policy-driven early retirement are modeled separately in
the enterprise simulation. Increased overlap is a direct durability stress here.

The one-factor grid contains exactly 25 rows:

| Variable | Values |
| --- | --- |
| Population with an already equivalent capability | 0, .25, .5, .75, 1 |
| Planned uses per week | 0, 1, 2, 4, 8 |
| Receiver integration/checking workload factor | .5, 1, 2, 4, 8 |
| Annual ordinary reconstruction improvement | 0, .18, .5, 1 |
| Useful lifetime in weeks | 4, 12, 26, 40, 64, 104 |

The reference population is weighted .75 competent reconstructor and .25 already
equivalent recipient. Those weights are exact scenario mixture weights, not
rounded counts or empirical adoption estimates. The other factors use the
supplied scenario and standard lifecycle. This panel is descriptive sensitivity;
it does not tune the enterprise policy or establish a globally optimal design.

## Tests and limitations

Seventeen invariant tests cover preservation of complete and partial equivalents,
stronger ordinary experience, failed/harmful transfer charges, optional nonuse,
scope/status/freshness/baseline rejection, fixed-resource threshold crossings,
full-cost reconciliation, joint bundles with shared fixed costs, strict break-even
arithmetic, zero reuse, no fabricated one-week pairs, finite upfront funds,
historical-cost separation, moving-Beta reassessment, failed-construction
allocation, deterministic bindings and malformed inputs.

Joint profitability can arise because the same confirmation cost supports a
complete bundle while each component alone does not repay it. The tests do not
assign a free numerical synergy bonus or require all components to be profitable.
The independent exact witness supplies the separate demonstration of real
mathematical dependencies; this cost panel does not claim to discover them.

The source-linked economic register and protocol govern interpretation. In
particular, [AMD-LLM](https://arxiv.org/html/2502.12203v1) motivates a strong
mechanism-design baseline, while the known-method witness's operation counts
remain distinct from the assumed frontier workload costs used here. Positive
results are conditional modeled opportunities; negative results, duplication,
optional nonuse and unaffordable investments remain in the output.
