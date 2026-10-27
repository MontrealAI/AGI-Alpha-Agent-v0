# Feasible-policy addendum: input contract

This separate prospective policy corrects the original control's ranking-before-liquidity
limitation. It does not change the original accounting program, inputs, results or interpretation.
The source and this contract are frozen before the parent constructs or supplies fresh numeric
diagnostic alternatives. The policy author already reviewed the original known accounting study;
any later replay of those alternatives is post-review analysis.

## Required input

The top-level object has:

- `schema`: exactly `agialpha.feasible-policy-input.v1`.
- `information_set_id`: nonempty string identifying the same evidence available to every plan.
- `world_weights_evidence`: nonempty provenance/status string, such as an explicit assumption
  label. This code does not validate probabilities empirically.
- `opening_cash_usd`: finite nonnegative JSON number shared by all alternatives.
- `worlds`: nonempty list of `{id, probability}` records. IDs are unique nonempty strings.
  Probabilities are finite JSON numbers in the unit interval and sum exactly to one under decimal
  interpretation. No normalization or missing-probability imputation occurs.
- `alternatives`: nonempty list of complete enumerated plans, with unique nonempty `id` values.

Each alternative has nonempty string fields `id`, `proposer`, `configuration`, `production_plan`,
`retention_choice` and `development_choice`; finite nonnegative `price_usd`; `deposit_fraction`
in the unit interval; `independent_evidence`; and `scenarios`.

`independent_evidence` contains exactly the two required gate records named `readiness` and
`acceptance`. Each record must supply:

- `passed: true` and `independent: true` for eligibility; false or null is ineligible.
- Nonempty `attestor`, `reference` and `scope` strings.
- An attestor identity different from the plan's proposer identity.

Readiness is the independently assessed technical and commercial readiness of that complete
plan, including rights, participation, purpose, demand assumptions and genuine residual delivery
obligations. Acceptance covers unchanged useful scope, quality, deadline, customer effort and
the relevant buyer's acceptance criteria. Supplied attestations can be hypothetical diagnostics,
but must be labeled as such outside the selector. The code checks declared fields and identity
inequality; it does not authenticate a person, fetch the reference or establish independence,
truth, actual demand or actual customer acceptance. Those remain upstream evidence obligations.

Each scenario has:

- `world_id`, with exactly one scenario per shared world and no additional scenarios.
- `costs_complete: true` and `cash_path_complete: true` for eligibility.
- `earned_revenue_usd`: finite nonnegative JSON number. It excludes capital, refundable deposits,
  savings and speculative future benefits. Revenue and collections are different quantities.
- `costs`: all three A/B/C objects, each with finite nonnegative `monetary_expense_usd` and
  `opportunity_cost_usd`. No amount is inferred or defaulted. Monetary expense means the full
  accrued monetary cost, including unpaid incurred expenses and writeoffs where applicable;
  cash payment timing appears separately below. Opportunity costs exclude amounts already
  recorded as monetary expenses. Required job learning belongs in A once; additional retention
  belongs in B; genuinely optional additional development belongs in C.
- `cash_path`: a nonempty, chronological list of `{label, cash_balance_usd,
  restricted_for_obligations_usd, operating_reserve_usd}`. Labels are nonempty strings, cash
  balances are finite JSON numbers, restrictions and reserves are finite nonnegative numbers.
  The first balance must equal the shared opening cash. The path must include every cash prefix
  needed for the declared decision horizon, including upfront and deferred payments, collections,
  refunds and support. Restricted obligations include refundable deposits where applicable;
  operating reserves exclude amounts already restricted, so each encumbrance is counted once.

Input numbers must be JSON numbers, not booleans, nulls or numeric strings. Missing, unknown or
malformed alternative-specific evidence or financial inputs make that alternative ineligible.
Malformed shared evidence/world sets or duplicate alternative identities reject the input.
No absent monetary amount is converted to zero.

## Decision rule and output

For each complete plan, calculate contribution in each world as earned revenue minus disjoint
monetary expenses and opportunity costs. Weight those contributions with the common world
probabilities. At every cash prefix calculate available funds as cash balance minus restricted
obligations and operating reserve. All declared worlds, including any zero-weight stress world,
must have nonnegative available funds at every prefix.

Only plans that pass both independent-evidence gates, have complete known inputs, have strictly
positive expected complete contribution, and satisfy the entire cash path are ranked. The rank
is decreasing expected complete contribution, then lower price, then lexical plan ID. If no
plan is eligible, stop. Retention and development are plan choices with their full costs, not
fixed shares of surplus, mandatory investments, guaranteed benefits or fixed discounts.

The output identifies every exclusion reason, the eligible ranking and the selected plan ID.
Exact decimal results are JSON strings. Selection is conditional on supplied evidence and worlds.
`external_evidence_verified_by_this_code`, `actual_profit_established` and `production_authorized`
are always false. The rule does not establish completeness of the proposed opportunity set,
exhaustiveness of worlds, continuous price optimality, acceptance of future delivery, or cash
conservation in an upstream ledger. It consumes those declared calculations and filters complete
choices consistently. Shared starting cash and probabilities hold initial financial resources
and declared uncertainty fixed across plans.

Run with `python3 economics/feasible_policy.py --inputs PATH --output NEW_PATH`.
