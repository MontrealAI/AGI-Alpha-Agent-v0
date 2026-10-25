# Independent evaluation plan for the economic cost amendment

## Status and boundary

This plan belongs to the separately versioned economic amendment. The sealed
capability-construction study, its prospective experiment, its observed results,
and all previously delivered release files remain unchanged. This amendment is
a forward operational-cost scenario analysis, not a new human trial or a new
measurement of provider billing, employer attention, or field reliability.

The evaluator will review the amendment protocol, input records, equations, and
source scope before confirmation. Scenario calculations and result auditing will
start only after the coordinator publishes the new prospective hash freeze and
signals execution. This plan does not authorize network transactions, paid model
calls, credentials, or modifications to the sealed study.

## Primary economic identity

The proposed model uses mutually exclusive terminal request paths, rather than
assuming that repeated failures are independent. Let `p_b` be a path probability,
`a_b` its qualified-delivery indicator, and `c_b` its complete variable cost. A
path includes every reached production attempt, verification event, paid tool
operation, retry, review, manual repair, refusal, rejection, and closure action.
Acceptance means that the stated deliverable standard is assumed to have been
met; a returned response or nominal system approval alone is insufficient.

The independent oracle will expand all path events before aggregation:

```
Q = sum_b p_b * a_b
Expected_variable_cost_per_request = sum_b p_b * c_b
Expected_accepted_deliveries = V * Q
Total_cost = V * Expected_variable_cost_per_request + K
Cost_per_accepted_deliverable = Total_cost / (V * Q)
```

Here `V` is the explicitly declared number of requests within a finite horizon.
`K` contains all modeled fixed costs attributable to that horizon. It must not
silently assume a perpetual customer base, all future reuse, or amortization over
unserved demand. The evaluator will independently verify the variable and fixed
subtotals and this numerator/denominator identity for every reported row.

Rejected and refused paths have `a_b = 0` but retain their entire cost and resource
use. No additional generic failure surcharge is permitted for work already
included in those paths. Retry caps must be verifiable from the event sequence.
If `Q` or `V` is zero, cost per accepted deliverable is unavailable; zero accepted
output is never silently converted into a favorable zero cost or finite ratio.

## Required accounting coverage

The review will map every cost component to exactly one owner and charging rule:

- Production and verification model calls, with uncached input, cached input,
  output, and any separately billed reasoning or retrieval usage distinguished.
- Paid search, retrieval, execution tools, executor occupancy and its billing
  granularity, storage and other declared infrastructure charges.
- Employer source preparation, briefing, approval, review, correction, exception
  handling and closure. Hours and role-specific labor prices remain separate.
- Successful and unsuccessful capability construction, testing, qualification,
  integration and deployment. Failed construction remains paid work.
- Fixed and variable support, monitoring, maintenance and storage across the
  stated operating horizon, including any declared idle-capacity charge.

Each nonzero amount must trace to an observed quantity or explicitly assumed
quantity and a documented price. A zero must mean a justified zero or an
inapplicable charge, not missing data. An unavailable material cost must remain
unknown and prevent a claim of observed complete cost. A fully specified modeled
scenario is still a modeled scenario.

The modeled operating account does not establish expected downstream losses,
professional liability, or a monetized guarantee against material errors. Such
unmeasured exposure must not appear as an assumed zero. High-consequence
clinical, legal, financial-execution and safety-critical work is outside this
bounded publication-readiness brief and remains unsupported. Any proposed use
that changes that boundary needs a separate protocol and validation standard.

Measured native execution is a separate evidence layer. Its process or CPU
measurement is not a complete employer cost, a provider invoice, or a measurement
of model-assisted authoring. Pricing that measurement creates a scenario and
must preserve the difference between CPU time, occupied executor time and billed
time. Native task-time model calls of zero do not imply zero model cost for
development, authoring or a different proposed service configuration.

## Human comparator and parity

The primary comparator is competent traditional work using ordinary non-AI
software. Sourced labor prices establish compensation, not the duration or
quality of this particular task. The model must identify occupation, geography,
reference period, currency, benefit coverage, source methodology and known or
unknown AI-use status. Already benefit-inclusive prices receive no additional
benefit multiplier.

Matched human production duration remains a sensitivity variable where it has
not been observed. Its scope must be explicit: production minutes exclude any
separately charged approval, review or correction, and the model must also report
the resulting all-in human effort. Both arms must pay comparable employer
administration and acceptance work when those activities are included in the
brief. Any asymmetric review or correction assumption must be visible.

The human cost denominator must use the human arm's own qualified-delivery
probability. Human correction, rejection and abandonment are treated consistently
with the Agent paths. A human price observed in one geography cannot be combined
with a provider price in another currency without an explicit conversion rule.

The oracle will solve break-even human production time algebraically from the
reported human-cost function and Agent cost, independently of the producer's
reported threshold. It will substitute that threshold back into the original
equations. A negative threshold means the Agent's modeled cost is already below
the human arm's fixed administration component; it does not prove a real task
can be completed in negative time. Negative cost advantages remain visible.

## Attention, latency and capacity

Human attention, request turnaround and resource occupancy are different
quantities. The evaluator will verify both total attention per request and total
attention per accepted deliverable, including unsuccessful paths and attributable
fixed construction/setup work where it consumes the same labor pool.

Accepted-path latency must be calculated as
`sum_b p_b * a_b * latency_b / Q`. Unconditional resource load per accepted
deliverable is a separate quantity and may include failed requests. It must not
be relabeled customer turnaround. Queue delay, human review waiting, model latency
and executor occupancy must have explicit overlap or disjointness assumptions;
the same interval cannot be added twice to elapsed time.

Finite-horizon capacity must jointly respect demand, available budget, residual
human attention, worker time and declared model/tool quotas. Fixed expenses and
fixed resource use are deducted before delivery capacity is calculated when they
draw from those pools. A binding resource limit must be reported. Expected
throughput, which may be fractional, is distinct from a guaranteed integer
service commitment. Multiplying released minutes by a wage produces a capacity
valuation, not realized payroll savings, revenue or cash available to reinvest.

## Source and date audit

Before freeze, the evaluator will inspect the exact pricing and wage records and
their cited source passages. The audit will check publication/effective/retrieval
dates, model or service identity, currency, pricing unit, billing exclusions,
cached-token conditions, and whether a quote applies to the selected service
tier or region. Mixed vintages will be disclosed rather than silently restated
as current observations. An exact provider price must not be used as the observed
cost of the host author's unknown model or token consumption.

Published human workflow evidence must preserve its task, quality definition,
participant population, timing method, selection/censoring and known AI-use
conditions. Adjacent evidence cannot be substituted for a matched task duration.
The previous study's 42 accepted fixtures do not establish field success rates,
the scenario path probabilities, or a population reliability distribution.

## Independent confirmation checks

After the published freeze, the oracle will audit every computed scenario and
all displayed aggregates. Its implementation will use a separate expansion of
path events and high-precision arithmetic where needed. It will verify:

1. Input identities and freeze hashes; probability sums and nonnegative usage.
2. Complete event costs, role-specific labor charges, and fixed-cost ownership.
3. Probability-weighted costs and resource moments, including every failure path.
4. The complete numerator, accepted-output denominator and finite allocation.
5. Human parity, cost differences, ratios and break-even substitutions.
6. Conditional latency, total attention, capacity limits and unused resources.
7. Scenario labels, assumption classifications and preservation of unfavorable
   or infeasible rows, without selection based on outcome.
8. Reconciliation between machine-readable results, figures, tables and prose.

Sensitivity ranges will be labeled as ranges over assumptions, not confidence
intervals or empirical probabilities. Dependencies between path probabilities,
review effort, token growth, retry behavior and demand must remain intact.
Results do not establish self-acceleration, actual revenue or an experimentally
measured full-system dollar advantage.

The audit will produce a machine-readable result with every checked row,
discrepancy, tolerance and input hash. Any failure after freeze remains recorded;
corrections require a separately identified amendment or erratum, rather than
silently rewriting the frozen analysis.
