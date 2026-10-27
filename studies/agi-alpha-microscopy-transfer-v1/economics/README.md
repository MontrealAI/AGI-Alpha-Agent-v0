# Conditional economics: microscopy transfer

This standalone research simulator supplements the executed microscopy instrument.
It does not create production receipts, customer contracts, authenticated identities,
or a replacement enterprise accounting system. All entries are explicitly simulated.

## What is sourced

The CHUM cellular-imaging rate card, opened 2026-10-27, lists formatted image-analysis
delivery at $129.75/hour for external university/hospital customers and $143.50/hour
for businesses. The service description includes extracting quantitative information,
staff analysis, ImageJ/FIJI, CellProfiler and Imaris. These are relevant existing expert
alternatives, not obsolete methods. The rate block uses dollar signs; CAD is an
explicit inference from the Montreal provider. No quotation for this particular
study was obtained. Hours, customer preferences, staff costs and effort are assumptions.

- https://www.chumontreal.qc.ca/en/crchum/core-facilities-and-services/cellular-imaging/rates
- https://www.chumontreal.qc.ca/en/crchum/core-facilities-and-services/cellular-imaging/services

The model rate anchor is the opened official Standard GPT-6 Astra API price page:
$10 input and $50 output per million tokens, at input length at most 272,000 tokens.
The assumed workload and CAD/USD ratio are scenario parameters. They do not price
the hosted research session. No API transaction or real commercial collection occurs.

- https://developers.openai.com/api/docs/models/gpt-6-astra
- https://developers.openai.com/api/docs/pricing

## Scope and initial conditions

One fictional accepted originating job pays CAD550 against CAD310 of A cash cost
(CAD180 necessary instrument construction and CAD130 delivery) plus CAD20 owner
opportunity cost. This is an explicit conditional starting case, not an observed
sale or an estimate of the actual research effort. Its contribution is separated
from subsequent work in `origin_economic_surplus` and `fresh_economic_surplus`.
No origin is executed if initial liquid funds cannot cover its costs and reserve.

Eight prospective buyers may each buy one later quantitative transfer report.
Their human-service reference uses the sourced business rate and assumed hours
(1.5, 2.5 or 4). Buyers compare expected delivered value, quote, their own effort,
deposit burden, a human alternative and declining. Values and probabilities remain
assumptions. Full technical acceptance is not inferred from simulated purchase.

The buyer rule is a **conservative maximum-price screen**, not an exact risk-neutral
expected-utility calculation. It subtracts the entire quote from expected delivered
value even though settlement can refund failed or unperformed work and can bill a
smaller accepted partial milestone. The rule deliberately uses that maximum-price
burden, plus customer effort and a supplied deposit penalty, to decide participation.
This is a behavioral assumption; the variable named `expected_utility` in frozen
code must not be interpreted as a derived optimal decision under conditional billing.
A different expected-payment choice rule would require a prospective new edition.

Four supplied operating routes test the mechanism: established expert tools; a
self-funded new common adapter; contingent coordination using established tools;
and the adapter with contingent coordination. A new common adapter has CAD240
assumed incremental construction cost, allocated once to A when undertaken for
the orders. Coordination adds CAD35. Without contingent construction, the adapter
is built before binding demand is known. With coordination, construction follows
the declared participant threshold. This is a supplied commercial ablation, not
autonomous invention. E can select any route with the same evidence/resources.
The primary assumption gives the new adapter no labor or quality advantage.

E is a competent workflow. E+ may retain the originating artifact. Its screening
cost is CAD5; extra packaging and upkeep total CAD70. If expected reusable savings
cannot exceed those incremental costs, retention stops. The primary retained gain
is zero, so E+ rejects after the cheap screen. An identical ordinary library has
the same artifact, permissions, admission and costs; its trajectories must match.
Optional extra Gym is considered separately as C and is rejected when unprofitable.
Originating construction is never charged again as B or C.

## Complete modeled accounting

Cash uses integer cents. Seed capital is financing. Refundable deposits increase
cash and liability together and create no immediately available funds. Delayed
receivables cannot finance current work. Each job reserves a worst-case correction
and support budget before execution, then charges the realized scenario expenditure
once. Each accepted milestone releases its earned part of a deposit; only the
unearned excess is refunded. Default loses the outstanding accepted balance; it
is not also charged as a refund. Withdrawals and common failures retain incurred
costs and refund unearned deposits. A failed full report may generate only a
pre-agreed partial diagnostic fee, counted separately from full delivery.

A covers originating and subsequent delivery, required construction, coordination,
failed attempts, correction, support, modeled tool/hosting and operating overhead.
B covers extra assessment, retention and upkeep. C is optional practice. Owner
opportunity cost and customer effort are separately represented. Assumed staff
cash cost is not the sourced human-service charge-out rate. Complete actual
research cost and actual operating profit remain unknown (`null`).

The 24-hour production-capacity limit covers **fresh paid-job delivery labor only**,
including modeled correction and support. Origin construction, new adapter
construction, coordination, retention and practice are represented as fixed cash
charges outside that capacity account. The results therefore require an outsourced
or separately provisioned interpretation of those charges, with adequate provider
capacity and lead time. That availability was not measured. The simulator omits
their internal staffing and scheduling requirements; its capacity conclusions do not
apply if those activities consume the same constrained staff. This qualification
does not change the frozen results or assert that the omitted requirements are zero.

Reported profit-like quantities are pretax modeled contribution/surplus over the
specified scope, not statutory accounts or an assertion that unknown real-world
obligations are free. The scenarios include zero and negative gains, demand loss,
common failure, insufficient capital, higher labor cost, greater customer effort,
zero owner obligation and greater owner obligation.

## Prospective protocol and reproduction

From this directory:

```sh
python -m unittest -v test_accounting
python simulate.py develop
python simulate.py confirm
```

Development considers absolute prices CAD200, CAD300 and CAD425; deposits 0 or
50%; and participant thresholds 1 or 3 for coordinated routes. Stopping is an
available policy. No fixed human-reference discount or reinvestment rate is imposed.
Twenty-four development seeds select the price/contract policy for each route and
the competent baseline route. The source/config hashes and all scores are written
to `results/policy_freeze.json` before confirmation. The confirmation phase refuses
a source/config mismatch and uses 96 disjoint fresh seeds per arm/route/scenario.
Frozen policies remain fixed under stresses; only explicitly declared environment
and benefit assumptions change. This is prospective within this execution, not
an external preregistration. Any rerun is deterministic under the same code/config.

`results/confirmation.csv` retains every simulated history, including failures.
`results/example_ledger.json` contains a complete time-ordered event ledger.
`results/results.json` reports summary intervals and all conservation/parity checks.
Intervals quantify Monte Carlo variation under supplied assumptions, not uncertainty
about whether those assumptions hold. Actual U/E/E+ model-task measurements remain
in the study's technical evidence; no deterministic simulator arm is a frontier-model
performance measurement.

## H/U/E/E+ comparison configurations

| Configuration | Competent resources and role | Evidence in this economic edition |
|---|---|---|
| H | Equivalent expert image-analysis service, including established ImageJ/FIJI, CellProfiler or Imaris where suitable | Sourced CHUM hourly references; project hours and comparability remain assumptions |
| U | Representative ordinary use of the same frontier model with the full task requirements, tools and data | No U execution or U performance estimate is produced by this simulator |
| E | The same model plus a small frozen expert workflow: check mission meaning, coordinates and units; choose an established method; verify and correct the output | Competent economic baseline; performance and effort in the simulator are explicit assumptions |
| E+ | E with the actual frozen retained instrument or authorized service, including additional qualification and reuse costs | Zero retained gain in the primary model; positive and negative benefits are conditional sensitivities |

Same-model hosted task trials are a separate evidence stream. At preparation of
this economics edition their outcomes are not used as measurements here. The
ordinary-library control receives identical content, permissions, admission and
serving costs to E+, and its exact parity is preserved. E versus U and E+ versus E
must be reported separately; an assumed expert operating margin cannot also count
the same expertise as additional retained Alpha.

## Low-cost Operational Alpha protocol

Freeze one concise reusable expert workflow before fresh U/E comparisons. Give
both configurations the same model, effort setting, requirements, tools, data and
authorized resource envelope. Count unsuccessful attempts, corrections, verification,
customer effort, latency and preparation. If full token or billing records are
unavailable, report that gap; equal wall-clock/tool limits do not prove equal spend.
Do not regard an expert-looking prompt as an outcome improvement.

Under a simple full-acceptance invoice model, let S be additional method setup
cost, N the realized uses, delta_c its additional complete cost per offered job,
P the price, and d the default probability for an accepted unpaid invoice. With
unchanged collection terms, an acceptance-rate gain must exceed
`(delta_c + S/N) / (P * (1-d))`. At the scenario price CAD425 and assumed default
0.04, each additional CAD1 per job requires approximately 0.245 percentage points
of extra acceptance. Partial invoices, effort changes and correlated defaults require
the event model instead of this simplification. At matched accepted quality, compare
complete cost savings against setup and serving costs. Always include zero gain;
if quality and cost both tie, strictly positive extra method cost is not justified.
This threshold is a protocol calculation, not a completed U/E result.

## Decision threshold

The complete incremental B investment is CAD75. At an assumed avoidable staff
cash cost of CAD65/hour, N actual reuses require more than 75/(65 N) saved hours
per use for cash break-even, absent other changes. At four reuses the threshold is
0.28846 hours (17.31 minutes) per use. This is a condition to test, not measured
saved human effort. If savings are only in owner time or idle salaried capacity,
cash savings do not follow. Additional failure, customer burden or maintenance
raises the required benefit; zero reuse cannot recover the investment.

The 17.31-minute condition requires **four realized, eligible reuses**, not four
forecast opportunities, four inquiries or four unaccepted outputs. Realized reuse
in the confirmation often falls below the supplied four-use forecast. The resulting
false admissions and lost costs remain in the half-hour and negative-transfer
scenarios. An operating policy should update eligibility and credible demand before
committing further retention expense, while preserving each prior admission outcome.
No realized effort gain is established by this economic model.

The next real experiment should obtain a scope-matched human quotation, measure
total delivery/adaptation/correction effort on fresh datasets using competent
existing tools, and elicit willingness to pay before a commercial pilot. The
study can demonstrate a working quantitative instrument while declining any
unsupported retained-Alpha or newly feasible-market claim.

## Source and licensing preservation

The frozen economic Python source has no per-file SPDX header. It is intentionally
left byte-identical to the pre-confirmation source rather than adding a header after
results. Consult the study LICENSE for applicable artifact licensing. Documentation
clarifications after review do not alter source, configuration, policy or raw results.
