# Sparse conductance engineering: frozen candidate acceptance contract

## Scope and useful outcome

The service produces a numerical engineering report for a supplied linear grounded conductance network. A complete connected outcome solves baseline scenarios, identifies grouped conductances from partial observations, and allocates a finite conductance-improvement resource budget against the worst supplied load scenario. The output enables a modeled design decision; the input cases are research-generated and neither observed commercial demand nor physical-system validation is claimed.

This scope differs from the existing polynomial quadrature, scheduling MILP and thermal-fluid calibration work. It is a preplanned connected workflow, not autonomous discovery of which job or capability to invent.

## Inputs and methods

All methods receive the full mathematical specification, ordinary NumPy/SciPy tools, the same task inputs and declared scope. A connected graph has positive edge conductances and nonnegative ground conductances with positive grounding in every connected component. For oriented incidence matrix B, K = B diag(c) B^T + diag(g). The arbitrary orientation does not change K. States obey K u = q.

The public JSON schema is `agi-alpha-conductance-job/v1`. `network` contains node_count, edges `[left, right, base_conductance]`, and ground. `loads` contains one complete vector per scenario. Family `forward` returns finite states. Family `inverse` multiplies disjoint edge groups by bounded parameters, fits supplied partial-state observations, and predicts three additional load scenarios. Family `design` adds nonnegative conductance to unique candidate edges with box bounds and a linear resource budget, minimizing maximum scenario compliance q^T K^-1 q.

The candidate API is `solve(task) -> result`. Successful outputs use `status: complete`, and arrays have the dimensions specified by the task. Forward returns states; inverse returns parameters, states and prediction_states; design returns allocation and states. Solver success labels alone are never acceptance evidence.

## Prospective scale

- Development: one independent task per family on 49 nodes, for three development jobs.
- Discovery: two connected three-stage chains on 225 and 400 nodes, for six discovery stages. These are construction data and never confirmation outcomes.
- Primary: 12 independently seeded chains, each with three staged jobs; 36 stages and at most 144 arm-stage evaluations. The independent sampling unit is the chain, not the stage, process or method replay.
- Four fixed primary profile strata have three seeds each: grid 100 nodes, 4 loads, 4 inverse parameters and 8 design variables; anisotropic grid 625/8/12/24; irregular connected 1600/12/20/48; long-range grid 2500/16/32/80.
- The seed-plan SHA-256 is in `seed-commitment.json`. Source and protocol must freeze before primary generation. No primary case has been generated during protocol authoring.
- Nine adverse input controls are predeclared in `controls/manifest.json`, separate from useful jobs. Graph authority/freshness/dependency tests are additional software controls, also separate.

These sizes exercise batch sparse solves, calibration sensitivities and increasingly complementary optimization work. They do not make ordinary methods unavailable and do not establish an asymptotic law of network value. All arms receive the same allowed tools and equal native execution envelope: 60 seconds inclusive of source checking, solver, independent verification and pack generation; solver subprocess at most 50 seconds and bounded by remaining allowance; outer 70 seconds only for cleanup. An outcome completed after the 60-second acceptance limit fails. Separate real model-agent reconstruction has its own prospective authoring allowance and is recorded as construction, not hidden free work.

## Connected execution and custody

Each chain uses the same baseline topology and load scenarios. The forward method is an actual reusable dependency of inverse calibration. After inverse outputs are sealed, a design template is released and materialized using each arm's actual independently accepted fitted parameters. The helper `materialize_design(template, inverse_task, inverse_result, inverse_acceptance)` binds template, parent task, parent result and parent acceptance hashes. It changes baseline conductances using those actual fitted parameters; it does not substitute hidden true parameters.

A failed or unaccepted inverse blocks that arm's design stage. The block and incurred cost remain in the denominator and complete-chain result. No truth substitution or replacement case is permitted. The frozen design template is identical across arms; numerical conductances may differ because the accepted upstream estimates differ. The independent design oracle uses the same true calibrated network for every arm, and acceptance checks both fitted and true-model outcomes.

Primary seeds and answers are held by a separate same-session acceptance role until the agreed release stages. The filesystem is shared; this is process separation, not a cryptographically secure blind or organizational independence. Hidden true parameters, prediction arrays and future design truth are excluded from skill records and retrieval indices. Final reproducibility releases the full corpus after outcomes are frozen.

## Numerical acceptance

1. Input and output arrays must have exact required shapes and finite values. Conductance, grounding, index, disjoint-group, candidate-edge and budget scope must hold.
2. Independently reassemble K and solve the full scenarios. Returned-state relative error must be at most 1e-7, and normalized backward balance error at most 1e-10.
3. Inverse parameter bounds must hold to feasibility allowance 1e-8. Relative fit error on supplied observations must be at most 1e-7. Relative prediction error against the independently generated true network on three additional loads must be at most 1e-5. The local observation-Jacobian smallest/largest singular-value ratio must be at least 1e-8 at initial and returned values. Local rank does not prove global identifiability; useful held-out prediction is therefore required independently, and exact hidden parameter equality is not the acceptance target.
4. Design bounds and the linear resource budget must hold to 1e-8 times max(1, budget). Recompute every scenario's compliance. For each convex compliance function f_s(x), construct its affine supporting plane at the returned x. A separate LP minimizes the maximum of these planes over the full feasible resource polytope. Its optimum is a global lower bound for the finite-scenario convex design model. Require relative upper-minus-lower gap at most 5e-5. Perform this check on both the fitted network and the independent true network; true-model returned-state error must be at most 2e-5.
5. The design bound is a floating-point numerical certificate for the specified finite model. It is not an interval-arithmetic proof, a physical safety guarantee or evidence that unmodeled real-world loads are covered.

All thresholds are fixed before primary outcomes. Failed jobs, timeouts, invalid outputs and blocked successors are retained. No efficacy rerun, source repair, job replacement or tolerance change is allowed inside the frozen primary campaign. A repaired implementation requires a separately labeled fresh follow-up.

## Comparison interpretation

A may retain every independently constructed capability and all ordinary caches after construction; lack of the shared file is not lack of capability. B and C receive identical validated sources, evidence and dependency metadata, and B has competent search, dependency closure and planning. C may additionally use typed graph adjacency. D is an independently authored conventional sparse/SciPy composition. A/B/C/D share complete acceptance and native budgets.

Sharing value, validation value, graph overhead and construction-method value are reported separately. Initial independent conventional development already solves all three small tasks, so this protocol does not presume a missing underlying mathematical capability. Reconstruction time, fresh success, integration failure and end-to-end cost must decide any added-value claim.

Twelve complete chains, not 36 staged jobs, are the natural unit for a buyer purchasing the whole engineering report. Internal stage reuse and inter-agent transfer fees cannot be counted as additional enterprise revenue. All economic monetization, demand, receipt timing and complete unknown authoring/attention costs require separate explicit model inputs.
