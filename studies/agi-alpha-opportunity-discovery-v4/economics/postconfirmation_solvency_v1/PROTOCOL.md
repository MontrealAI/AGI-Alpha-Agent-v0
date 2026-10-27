# Post-confirmation development-milestone solvency audit

Version 1, 27 October 2026. This adverse audit was requested during editorial
review after the original economic results were known. Its protocol, calculation
code and input hashes are frozen before this additional calculation. It is not
new market confirmation, a retuned commercial policy, or recovered profit.

## Question and exact population

The original model assumes that the contracted development/failure record is
accepted even if the useful audit fails. It retains the nonrefundable portion of
the advance in that branch. The proposed contract instead requires a full refund
if the development record itself is rejected. That rejection event was absent
from the frozen simulation and was not covered by its partial-refund reserve.

Inspect every one of the 3,520 original arm-horizon rows, without resampling or
selecting illustrative favorable cases. The exposure population is precisely
`plan.action == "produce"`: the original planner's selected financeable
commitments, including plans later cancelled after observed withdrawal. Record
that distinction. No previously rejected plan is admitted and no price, buyer
subset, probability, capacity or payment term is optimized again.

## Adverse condition and reconstruction

For each original selected package, assume the development milestone is rejected
after all committed precollection work and all collected advances must be
refunded. No final invoice collection or borrowing pays for that work. This is
a deterministic adverse contractual condition, not an estimated probability.

Reconstruct the original current needs from the exact frozen random-generation
specification, seed and scenario. The audit is a separate standard-library
implementation; it does not import `evaluate_plan`, `realize`, `job_terms`, or
their reported cash requirement as its calculation oracle. Validate reconstruction
against all retained buyer objects in the original cash examples and against
the original selected buyer IDs/need counts.

Reconstruct precollection A from common commissioned construction (retained
arms only) plus each selected buyer's preparation, conditional delivery treated
as fully committed, and support. Add B retention and C prospect assessment once.
The hour/rate, compatibility, adaptation and cost formulas are the frozen
research assumptions, not observations. Use Decimal representations of the
same generated float inputs; tolerate less than USD0.00000001 of original
float-rounding difference when checking the original partial-refund cash formula.
Bad-debt writeoffs are excluded from this cash calculation: no final invoice is
collected or booked in the adverse branch, so a noncash credit loss is not a
second cash outflow. Seed is financing, never revenue.

With D total advances and C_full full committed precollection cost, terminal
cash before any final payment is B0 + D - C_full - D = B0 - C_full. Therefore
required opening cash is C_full, and shortfall is max(C_full - B0, 0). A package
is exposed if its shortfall exceeds USD0.00000001. This conservative committed-
work envelope does not assume cost reductions after cancellation or technical
failure. It is not a prediction that each exposed plan would actually incur
that entire loss.

## Report and stopping rule

Report original selected-plan counts, exposed counts and maximum shortfall for
each arm and each original scenario, plus aggregate arm counts and exact
per-package reconstruction rows. Label whether the original realization later
produced or cancelled. Preserve all original summaries and receipts. Report no
new expected profit, customer revenue, acceptance probability or feasibility
crossing. Stop after one calculation and integrity/reconciliation checks; any
failure requires a separate documented correction, not silent input changes.

This audit does not model legal enforceability, buyer disputes, partial milestone
acceptance, contractor nonperformance, actual laboratory costs, late collection,
strategic default, insurance, credit facilities, or alternative contract design.
It identifies a cash exposure within the stated proposed full-refund contingency.
Actual customer collections and earned revenue remain zero; complete actual
research cost remains unknown. New live commercial terms need their own
acceptance and solvency evidence.
