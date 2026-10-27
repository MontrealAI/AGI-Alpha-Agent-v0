# Technical experiment: reusable empirical interaction structure

This is an executed synthetic scientific-software experiment. The responses are
researcher-constructed nonlinear polynomial functions, not physically calibrated
engineering simulators. Ordinary numerical methods perform the learning. No
frontier API, proprietary model weights, customer data or live authentication is used.

## What is delivered

The originating job produces a coefficient model from 128 simulator observations
and verifies it on 384 separate observations. The model is an executable artifact:
`predict.py --model artifacts/origin-deliverable.json --inputs inputs.json` evaluates
it, where `inputs.json` contains a list of ten-dimensional input vectors in [-1, 1].

`v1.json` retains the empirically fitted support of that originating response. Ten
additional 128-observation Gym jobs produce `v2.json` by taking the union and count
of empirically nonzero features. This update is actual automatic computation. It
does not receive the hidden generator supports. The algorithm, synthetic family,
feature representation and update rule were constructed by the research team.

An inverse-design recipient must select a plan from a 512-plan menu with normalized
response at least 2.0 and a known plan cost at most 1.2. A final actual simulator
query is charged inside the declared budget and determines operational acceptance.
This outcome changes the task from reproducing response values to proposing and
verifying an actionable operating plan. The numerical thresholds are externally
unvalidated benchmark assumptions, not established customer willingness to pay.

The model's fresh prediction error and regret against the fully evaluated menu are
research audits. The primary action service does not promise unobserved global
optimality. A separately marketed verified-model service must pay for all 384
validation observations; it cannot use the audit as a free commercial validator.

`recipient.py` consumes actual capability bytes plus recipient observations. It
returns a newly fitted model and a proposed plan, which still needs its final
simulator query. The integration adapter separately retrieves capability bytes
through the repository's fixture access controls and invokes this callable.

## Ordinary methods and causal controls

All model-fitting configurations may use validation-selected orthogonal matching
pursuit, automatic relevance determination, and ridge polynomial regression.
Ordinary design alternatives include Latin-hypercube sampling, full-library
pivoted-QR volume design, and pilot support discovery followed by support-adaptive
volume design. Pivoted QR is a practical greedy determinant heuristic, not exact
global D-optimal design. Model fitting is repeated after visible validation using
all paid observations. Validation occupies 8, 12 or 16 calls within each budget.

A direct-search baseline queries the cheapest allowed plans until it finds a
measured qualifying result or exhausts the budget. It can succeed without a useful
surrogate and can stop early. Its cost is the actual number of oracle queries.
It is not forced to learn an unnecessary model.

The inherited-prior configurations use the same generic numerical algorithms with
their empirical support. A visibly poor prior invokes and compares the ordinary
full-library fit. The experiment retains failures after this fallback.

- `v1`: support from the originating paid characterization.
- `v2`: support after ten additional Gym characterization jobs.
- `library_v2`: identical bytes and operations supplied through an ordinary library.
- `wrong_prior`: an unrelated support artifact, with the same validation guard.
- `oracle_support`: hidden correct support supplied as an explicitly unattainable bound.

No graph advantage can be inferred if `v2` and `library_v2` perform identically.
The supported scientific mechanism would be amortized empirical structure, not a
novel regression or experimental-design algorithm. Executed ordinary baselines are
not measurements of the full capabilities of a current frontier model.

## New-offering prototype and strong alternative

The fault-diagnosis prototype identifies one changed interaction coefficient from
12 faulty-response measurements and checks its explanation on four held-out
measurements. This is a simulated fault benchmark, not demonstrated repair of
deployed software. True coefficient identity is available only to the audit.

The original simulator remains available. Therefore a strong ordinary baseline
queries both original and faulty simulators at the same 16 points, requiring 32
calls, and identifies the changed term by direct differencing. This alternative
does not need the originating model or Gym. Its success can make the proposed
specialist investment unattractive, and that outcome is retained.

## Information and freeze boundaries

Learning uses seeds beginning at 210000. Development uses 12 tasks beginning at
310000. Confirmation uses 48 separate tasks beginning at 910000. Half the tasks
reuse recurring motifs, one quarter replace two of eight active motifs, and one
quarter use a different support family. These labels are hidden from operational
policies. No infeasible menu is removed after evaluation.

`results/FREEZE.json` records source, protocol and artifact SHA-256 hashes before
confirmation. The earlier pre-policy freeze is retained separately. The final
runner checks both source and artifact bytes. `CONFIRMATION_COMPLETE.json` binds
the final fresh rows. This is procedural separation within one research team,
not cryptographic isolation or organizationally independent evaluation.

The only post-development technical changes before final freeze recorded the
already executed final verification response, asserted agreement with the audit,
and enforced the saved artifact hashes. Fitting methods, thresholds, targets,
budgets and confirmation seeds were not changed after development.

## Reproduction

From the study directory, use Python with NumPy, SciPy and scikit-learn:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/run_study.py train
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/run_study.py development
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/run_study.py freeze
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/run_study.py confirmation
```

Use a separate copy for a reproduction so original evidence remains intact.
Runtime versions are recorded in the freeze. CPU durations are measured; prices,
simulator evaluation time, demand and enterprise decisions belong to the separate
explicitly simulated economics model. The current generator is noiseless and
exactly lies in the public feature library, which materially limits external validity.

## Accounting boundaries

The required originating characterization uses 128 fitting observations plus 384
paid verification observations. Optional Gym fitting uses 1280 observations.
Research audit truth uses 384 prediction points plus 512 operating plans per task
and is cached across alternative policies. Diagnosis adds 16 observed probes per
prototype policy; the direct paired alternative uses 32.

Actual duplicate construction/development executions are retained in
`research_execution_ledger.json`, even when they repeat identical deterministic
data. These one-off study costs must not be silently erased or charged repeatedly
as if every deployable job required the full research campaign. Paid learning is
category A; additional assessment/retention/sharing is category B; optional Gym
and one-off study development are category C. Observed cash revenue is zero.

Local syntax compilation passed. The environment's Black installation could not
start because its pathspec dependency was incomplete; Ruff was not available.
An attempted isolated dependency installation was blocked by network policy and
stopped. These optional checks are not represented as passed.

## Final measured results and stronger opportunity supplement

The original confirmation contains 48 tasks and 1728 method/budget evaluations.
At 24 calls, v2 passes the fresh predictive-model test on 21/48 tasks, versus 1/48
for the hindsight union of the ordinary model methods. Yet its operational
point-design acceptance is 22/48, while direct measured search accepts 27/48.
An improved predictor therefore does not automatically justify the investment
when the buyer needs only one feasible action. At 96 calls, all strong approaches
accept 44/48 point-design tasks; the four remaining menus are infeasible.

This development result motivated exactly one new, separately prespecified
compound-outcome candidate. Its source and evaluator live under `robust/`, with
different development and confirmation seeds and separate frozen hashes. One
five-dimensional control vector must have average response at least 0.4, at least
12 nonnegative responses out of 16 declared environmental contexts, and public
control cost at most 1.2. Accepted plans pay for all 16 actual verification
queries inside the total budget. Direct search may reject a plan early after its
fifth negative response and try another if enough calls remain. Its failures and
unused budget are retained. The test certifies only these 16 contexts.

On 48 fresh compound tasks, the 40-call v2 configuration accepts 22/48, compared
with 14/48 for direct search and 18/48 for an impossible hindsight selector among
all four ordinary methods. The paired difference versus that hindsight selector
is +8.3 percentage points; its conditional task-bootstrap 95% interval is -8.3 to
+25.0 percentage points. This mixed-population result is uncertain.

In the prespecified compatible-family stratum, v2 accepts 17/24 at 40 calls versus
8/24 for the hindsight ordinary selector, with ten wins and one reverse crossing.
The paired advantage is +37.5 points, with a conditional 95% interval of +12.5 to
+58.3 points. The ordinary direct baseline alone accepts 7/24. Shifted families
reduce or reverse the gain. With 96 calls, strong ordinary model methods and v2
all accept the same 36/48 compound tasks. Twelve infeasible menus are retained.
There is no graph-specific effect: `library_v2` is numerically identical to v2.

These intervals describe repeated sampling from the fixed synthetic generator.
They do not validate physical assumptions, buyer demand or prices, and they are
not adjusted for every exploratory comparison. Compatibility is hidden from
operational policies; its favorable stratum cannot be used as free admission
information. The development-only baseline selection in `paired_analysis.json`
is a descriptive rule recorded after confirmation, not a newly preregistered
enterprise policy. The four-method comparisons and raw rows remain available.

`robust/results/crossing_deliverable.json` exposes the full control vector,
16 context inputs, 16 actual verification outputs, source lineage and learned
coefficient model for the first compatible 40-call crossing in sorted task order.
It is an illustrative post-hoc replay. The plan's mean response is 0.403857,
12 responses are nonnegative and its cost is 0.906163. All four ordinary methods
failed on that same task and budget. The original model coefficients replay
exactly, and the fresh method replays all nontiming fields. Both source/artifact
freezes are unchanged, as recorded in `analysis/REPRODUCTION_CHECK.json`.

## Reproduce the separate supplement and final analysis

After the primary commands above, run:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/robust/run_robust.py predeclare
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/robust/run_robust.py development
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/robust/run_robust.py freeze
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/robust/run_robust.py confirmation
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python technical/analysis/derive_results.py
```

The analysis step also corrects the descriptive diagnostic ledger to include all
32 unique original/faulty reference observations, as documented in the study-level
`PROTOCOL_CLARIFICATION.md`. It does not change any numerical source or outcome.

## Conditional complete costs and research burden

`robust/results/economic_sensitivity.json` uses actual observed delivery and
failure calls, including all final verification, at hypothetical query costs of
$0.10, $0.50 and $2.00. It additionally charges the main scenario's assumed
frontier token, tool, packaging, service, payment and invocation costs. Candidate
retention/admission/sharing/upkeep and the 1280-query optional Gym are allocated
across explicitly hypothetical reuse levels. Assumed prices of $100, $300 and
$600 are willingness-to-pay hypotheses for a new offering, not sourced quotes.

Those operating contribution rows exclude the common new-offering research
campaign, which is fully disclosed separately and must be added when assessing
whole-study return. Development, confirmation, independent full-menu audits and
the illustrative replay used 617544 query-equivalent evaluations. Valuing every
one at $0.10 would imply $61754.40 of research expense; the actual synthetic run
made no paid API calls and incurred no observed paid cash expense. This difference
is material: a promising operating contribution does not establish economical
physical research or sustainable enterprise compounding.
