# Final run design v2 — specified before training and confirmation

The dated `results/protocol_freeze.json` is the controlling manifest. Its source
hash check binds this design, the longer research protocol, adopted calibration,
source/test modules, and deterministic recipient design. Antecedent mechanism
evidence and graph fixtures retain separate identities and evidence status.
Version 1's source, manifest and 909-row partial training stream are preserved in
`evidence/development/protocol-v1`. No v1 economic confirmation was run. The
accounting clarification, revised policies and all v2 seeds are declared before
the new experiment; the earlier stream is development history.

## Replications and policy decisions

- Training: 24 independent worlds, seeds 760001–760024, for each of 32 policies
  in conservative, central and favorable scenarios.
- Confirmation: 64 fresh worlds, seeds 770001–770064, for each of four arms in
  each scenario: `beta` (B), `isolated` (I), `network` (S), and
  `network_no_invest` (S0). The same selected scenario policy applies to every arm.
- Price family: fixed human-reference ratios .35/.55/.75/1/1.15, or state-aware
  one-period responses over .25/.35/.45/.55/.65/.75/.85/1/1.15/1.30 with offsets
  −.10/0/.10, clipped to .15–1.40. Each combines with delivery only; retention
  hurdle 1 without separate R&D; retention hurdle 1.5 without separate R&D; or
  retention hurdle 1 plus optional separate R&D at hurdle 1.35. These 32 policies
  are a bounded family, not an exhaustive dynamic policy space. Main selection
  may choose no retention.
- Objective: maximize mean collected operating surplus after accrued costs and
  closing commitments/refunds. Require observed training shortfall frequency
  at most .05. Within USD1, prefer no separate R&D, then no retention, then the
  lexical policy name. This sample screen is not a certified real-world risk
  bound. No terminal graph-node value is added.
- The seller observes scope/urgency, queue, trust and order history. It uses
  declared population priors rather than buyers' private realized values. These
  priors are assumptions, not an estimated market. Pricing is a bounded best
  response to fixed outside alternatives, not a solved market equilibrium.
- Retention and separate R&D appraisal include their respective incremental
  lifecycle costs, technical admission probability and estimated displaced
  delivery margin. Waiting is unpenalized. Paid-job learning is not charged again.
- Fifty-seven sensitivity cases are declared in `sensitivity_cases()`, each with
  16 fresh worlds, seeds 780001–780016. Use central selected pricing for Beta and
  network; force retention on, then compare network optional separate R&D off/on.
  Beta remains without experimental capsules. This tests conditional retention
  even if main training selected delivery only. Joint assumption stresses remain
  explicitly named and are not interpreted as one-factor causal effects.
- Component removal, duplicates and deliberate forgetting use the first 16
  confirmation worlds per scenario. These are adaptive policy effects, distinct
  from frozen-recipient comparisons. Forgetting is not competent Beta.
- World is the replication unit. Means and paired differences use normal 95%
  Monte Carlo intervals; binary rates use Wilson intervals. These quantify seed
  sampling conditional on assumptions, not empirical acceptance or demand.
- Preserve complete transaction ledgers for all 768 primary confirmation runs.
  Full event traces are also retained for the first prespecified seed per
  scenario/arm; every other trace regenerates from source, parameters and seed.

The four primary arms mean competent Beta, isolated paid-job retention, network
retention with the selected optional-C decision, and the same network with C
disabled. All competent arms retain ordinary experience and established methods.
`network_no_invest` does not disable useful paid-job retention B. There are 2,304
training runs, 768 primary confirmation runs, 2,736 stress-response runs and 240
additional ablation runs: 6,048 executions, not 6,048 independent worlds.

## Capacity choice and its fresh test

The initial menu is central capacity, validators 1, validators 4, quota-quarter,
compute-double, agents-double and scale-complete-double. For Beta and network
separately, use the first eight stress worlds (780001–780008) to choose maximum
mean surplus under the central selected price and the retention response with C
off. Exact ties use the lexically larger case name, as the implementation's tuple
maximum specifies. Test the chosen setting on the last eight worlds
(780009–780016), paired against central capacity in those same worlds.

The menu reuses declared stress simulations; it supplies no extra independent
sample. Weekly infrastructure costs USD105 plus USD30 per validator, USD40 per
producer and the declared storage/access amount. Each producer or validator
added above the baseline incurs USD500 initial setup. This is a one-time initial
capacity choice, not a global dynamic-expansion optimum or free scaling.

## Frontier configuration and billing

Modeled substantive producers, validators, correction agents, builders and
investment evaluators use `gpt-6-astra`, Pro mode, max effort. Qualified
visual/computer-use support uses `gpt-6.1-terra`, standard mode, medium/high
effort. These are documented aliases, not immutable snapshots or measured live
task runs. Specifications, source/tool context, decomposition, critique and
correction are represented in the assumed workload. There is no expert or
superhuman quality bonus.

Per-request planning assumes at most 128,000 input and 32,000 output tokens.
Campaign budgets aggregate multiple requests, including all underlying Pro work
and billed reasoning. The simulator meters aggregate tokens and concurrent
producers and validators at five ticks/week. Effective weekly quotas are study
constraints, not account entitlements. Minute-by-minute provider scheduling is
not emulated; a paced broker would be required in operation. Subscription access
is not API credit and supplies no assumed subsidy.

With caching, every fresh input token is conservatively billed as a 30-minute
write: Astra USD12.50/M, Terra USD1.25/M. Separately enumerated reads cost USD1/.05
per million, and output costs USD50/5. Prior context is reused in decomposed call
bursts; latency includes workflow and queue delays. No-cache sensitivity bills
all input at standard uncached rates. No Batch/Flex discount is assumed.

## Complete costs and their boundary

`sources/workload_catalog.json` records assumed token, tool and latency quantities.
Job tool budgets cover search, executable checks, extra compute and computer-use
support. Weekly fixed infrastructure USD105 covers hosting/orchestration,
automated operations and opportunity intake; validator capacity costs USD30 each.
Dedicated producer execution support costs USD40 each. Network distribution/access
costs USD70 plus USD4 for each of 24 members; local/isolated retention costs USD35.
API usage is separate. Storage/access remain charged with no admissions. USD9,500
bootstrap setup is a modeled historical cost paid from USD60,000 seed, not
measured research expenditure. Capacity additions incur the setup cost above.

Three books are distinct. **A** records complete paid-job delivery, including
learning, experimentation, reconstruction and the job's checking/correction.
The source-job memo is direct accrued cost, not collected cash or demonstrated
margin; its value is never charged again to B or prospective Alpha. Receiving-agent
integration performed during a later job also remains an A delivery expense. The
comparative Alpha calculation includes its incremental effect without billing it
twice. A field retaining a historical `paid_cost` name remains an accrued-cost
memo; the transaction ledger determines collections and payments.

**B** records only additional extraction, sanitization, generalization, fresh
reusable validation and packaging through the distinct `RETENTION` packets, plus
admission, incremental maintenance and distribution. Fixed network overhead is
paid once at enterprise level; the marginal skill gate charges only per-skill
distribution. Retention may fail even after a useful job. Its central
generalization success is an explicit .90 assumption (.70 conservative, .97
favorable), with adverse stress cases.

**C** is optional separate R&D using `CONSTRUCTION`: new search, failed attempts,
construction, confirmation and migration not already performed in A. No C is
required to retain a useful capability from paid delivery. Historical costs stay
in enterprise profitability while prospective continuation excludes sunk costs.
Creator bounties are external contributor payments under this operator accounting
boundary; an internal transfer would need a different consolidated boundary.
Maintenance, distribution, revalidation, integration, correction, default, refunds
and active runoff remain charged exactly once.

Available cash excludes unpaid obligations and funded commitments. Authorized
retention/R&D budgets and actual accrued expenditure are separate fields. A
priced source job may default; report useful source jobs with modeled collections
separately from all retained candidates originating during commissioned work.
All competent arms retain ordinary learning. Exogenous copying/method diffusion
uses the same draws across arms. New Beta epochs require fresh Alpha assessment.
The actual assistant research-session bill is unknown, never silently zero, and
is not recouped by simulated receipts. Dollar results are prospective conditional
enterprise economics. AGIALPHA issuance/appreciation contributes zero earnings.

## Reproduction and decision rule

From the study directory run:

```sh
python3 -m src.run_study all --out results/replay --workers 4
```

Phases `freeze`, `train`, `confirm` and `sensitivity` also run separately. The
harness refuses to overwrite the protocol, selected policy or confirmation.
Postfreeze source changes require a distinct protocol and fresh conditions.
The recipient panel is deterministic and was development smoke-tested; its replay
is an arithmetic reproducibility test, not unseen stochastic confirmation.
