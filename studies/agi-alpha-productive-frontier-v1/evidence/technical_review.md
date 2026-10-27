# Technical review: covariance specialist and opportunity prototype

**Reviewer role:** A separate assistant work role reviewed the implementation, frozen protocols, raw tables and source documentation. This is an independent work assignment within the same AI-assisted study, not external institutional review, a human validation panel, or a certified engineering audit. The reviewer did not edit the numerical engine or run new experiments.

**Reviewed material:** `technical_work/lyapunov_study.py`, `prototype_study.py`, both protocol JSON files, their archived initial sources, initial raw CSV/JSON outputs, exposed-case `results_validated` outputs, and artifact hashes. Review completed 27 October 2026.

## Overall finding

The generated matrix family satisfies the assumptions of the stated residual error bound. The technical comparison supports a bounded conclusion: a reusable covariance-weighted reduced basis changes actual numerical behavior, transfers as an executable artifact, and sometimes reduces solver time; optional Gym refitting does not establish a useful new offering or reliable frontier expansion. Competent adaptive ordinary tools already solve the standard workload and the secondary gain-selection task. Learned bases can fail the residual contract after the declared parameter shift, and Gym refitting increases refinement work in the secondary prototype.

No numerical correctness blocker was found for the generated cases. Publication must preserve the distinction between numerical solution certification, observed benchmark timing, simulated commercial qualification, and validation of a real customer model. Broad claims of reliable interactive service, new-market discovery, live frontier-model superiority, or sustained compounding would exceed the evidence.

## 1. Certificate: valid assumptions and limits

The generator constructs `A=-D+K`, where `D` is positive diagonal and `K` is skew symmetric. Therefore `(A+A.T)/2=-D <= -alpha I` for `alpha=min(diag(D))>0`. The system has two localized input channels and 192 states. For the continuous-time covariance equation

`A X + X A.T + B B.T = 0`,

and residual `R=A Xhat+Xhat A.T+B B.T`, the error satisfies

`X-Xhat = integral_0^infinity exp(A t) R exp(A.T t) dt`.

Dissipative contraction bounds its Frobenius norm by `||R||F/(2 alpha)`. The trace error bound `delta=sqrt(n)||R||F/(2 alpha)` follows by Cauchy–Schwarz. When `trace(Xhat)>delta`, `delta/(trace(Xhat)-delta)` bounds relative trace error. Refusing a finite relative certificate when this denominator is nonpositive is appropriate.

The hardened source validates dimensions, finiteness, basis orthogonality and the claimed dissipativity lower bound. It explicitly records a relative Frobenius bound. These are useful corrections, and the initial sources and observations were retained rather than rewritten as fresh evidence.

### Hidden-oracle concern resolved within the mathematical scope

The initial experiment's `accepted` flag combines the trace certificate with exact-reference trace/Frobenius checks. Reference errors are calculated after the timed solver and are not supplied to the policy. Reading every raw row shows **zero disagreements** between the final acceptance flag and the trace-certificate decision in confirmation, shift or the first prototype split.

There is also a mathematical explanation. If `delta/(trace(Xhat)-delta)<=0.01`, then, using `abs(trace(Xhat))<=sqrt(n)||Xhat||F`, the corresponding Frobenius bound `b/(||Xhat||F-b)` is at most 0.01. Thus the protocol's 2% Frobenius reference-error gate is redundant under a valid trace certificate. The Schur results can remain independent ex-post research audits without being a required serving oracle. The paper should explain this rather than suggest that full reference validation was included in each specialist's measured serving time.

### Limits requiring explicit wording

- The bound controls numerical error relative to the specified finite-dimensional model. It does not validate the physical model, disturbance law, units, omitted dynamics, controller hardware or a real plant.
- Stability alone does not imply the stated `alpha` bound. The strict dissipativity restriction is material. Systems outside it require a different validated bound or refusal.
- Residuals and eigenvalue checks use ordinary floating-point arithmetic. There is no outward-rounded interval arithmetic or verified roundoff enclosure. Use “residual-derived numerical error certificate under stated assumptions”; avoid claiming a machine-checked rigorous proof covering floating-point error.
- The generic validation tolerance is adequate relative to the generated family's damping scale; it should not be presented as validated for arbitrarily tiny dissipativity margins.
- The code's alpha/shape guards do not authenticate a model, establish rights to customer inputs, or perform ENS identity verification.

## 2. H2, covariance and candidate objective

For the study's zero-feedthrough, stable state-space system driven by the specified unit-intensity white-noise channels, `trace(X)` is squared H2 when the output is the full state (`C=I`). It is output covariance power or squared disturbance-energy norm, not a worst-case H-infinity gain and not a general robustness guarantee. MathWorks' own H2 documentation states the squared-norm/white-noise relation and the instability/nonzero-feedthrough limitations:

https://www.mathworks.com/help/control/ref/dynamicsystem.norm.html

The secondary objective `J(g)=trace(X_g)+0.15*g^2` is a declared synthetic tradeoff between modeled state variance and a quadratic damping penalty. The coefficient has no independently elicited buyer-value interpretation. With `A_g=A-gI`, the same certificate applies using `alpha+g`.

The eight-point grid from 0 to 0.7 verifies a discrete candidate choice. It does not establish a continuous optimum, a practical actuator design, feasibility of implementing added damping, or superiority across arbitrary feedback controllers. In the original eight fresh cases, the Schur oracle selected 0.7 in five cases, and 0.4, 0.5 and 0.6 once each. Boundary choices should not be represented as proof that the allowed gain range contains the unconstrained optimum.

## 3. What was learned

`pod()` takes the leading eigenvectors of the sum of work-instance covariance matrices. It is properly described as a **covariance-weighted state subspace**, related to POD/controllability-energy compression. It is not necessarily the basis minimizing Frobenius reconstruction error of vectorized covariance snapshots; that would be a different objective.

The artifact changes as a result of work and Gym data, is persisted as an array, and affects fresh solutions. This establishes learning in the modest executable sense of a data-dependent fitted numerical representation. It does not establish model-weight training, a learned general reasoning policy, reinforcement learning, algorithm invention or specialist ASI.

Gym adds four development examples selected by the largest pre-Gym residual certificates and refits at the same rank 48. This rotates/reweights the basis rather than monotonically enlarging it. Negative transfer is therefore plausible and observed: the secondary gain-selection workload needs seven Schur refinements after Gym versus none for the work-only basis. Improved representation of selected development cases does not guarantee a better future portfolio.

The method is familiar numerical analysis. Prior art includes M.E.S.S., low-rank ADI and parametric model reduction:

- https://arxiv.org/abs/2003.02088
- https://www.mpi-magdeburg.mpg.de/projects/mess
- https://link.springer.com/article/10.1007/s11075-022-01409-5

The new study contribution should be its inspectable lifecycle, matched alternatives, negative transfer and investment decision, not a claim to have invented the underlying mathematics.

## 4. Comparator fairness

Including adaptive block Krylov is essential. A comparison only against repeated dense Bartels–Stewart solves would overstate specialist advantage. The adaptive ordinary method uses fresh matrices, builds an instance-specific basis, evaluates the same residual contract and can use fallback in the secondary prototype. It is not deprived of tools simply to make retained learning win.

The fixed center-instance Krylov48 basis is a useful reuse ablation but a weak representative of all ordinary libraries. Its poor transfer does not imply that “libraries fail” or that authenticated graph sharing has superior mathematics. No graph-specific claim is supported.

Further ordinary alternatives exist: LR-ADI with adaptive shifts, extended/rational Krylov, optimized low-rank residual evaluation, sparse operators, vendor packages, and parameter-recycling methods. They are documented but were not all benchmarked. Since a conventional baseline already wins the relevant feasibility comparison, their absence cannot establish a hidden specialist advantage. Conversely, do not claim the implemented adaptive method is the strongest solver available.

All methods share the same 192-state matrix family and input-channel locations. The shifted split changes damping/coupling ranges, not system dimension, forcing locations, topology, physics, nonnormality class or model-validity conditions. Transfer claims should remain within this family. Failed shifted certificates are not evidence that all specialized covariance methods necessarily fail outside this box.

The scripted solver controller is a competent tool-backed **Beta surrogate**. No frontier-model inference traces or task-success comparisons were collected. Its performance cannot be attributed to an empirically measured Astra or Terra model.

## 5. Timings and reliability: observations, not an SLA

The initial implementation times each fresh instance once, in a fixed method order, with one BLAS thread and a warm-up. It adds common assembly time and includes explicit full residual construction. This is useful descriptive benchmarking. It is not independent repeated performance measurement, randomized method-order benchmarking, CPU-isolated production testing, queue/cold-start testing or a latency SLA.

The field `batch32_seconds_p95_proxy` is **32 times a per-instance p95**, not a measured p95 of 32-case batches. Use the separately recorded actual batch sums for observed batch comparisons, and label them as a small number of observations.

The hardened exposed-case rerun is especially informative about the 0.25-second contract:

| Method | Initial confirmation batch sums, seconds | Guarded revalidation batch sums, seconds |
|---|---:|---:|
| Adaptive Krylov | 0.177, 0.224 | 0.213, 0.259 |
| Work POD48 | 0.078, 0.089 | 0.089, 0.104 |
| Gym POD48 | 0.078, 0.081 | 0.087, 0.100 |

Adaptive performance straddles the proposed threshold when guards and runtime variation are included. The 32-case first-prototype adaptive total also moved from about 0.195 to 0.265 seconds. A stable, reliable new interactive offering has not been established. The standard five-second contract has ample observed margin for ordinary methods.

Acceptance proportions must be separated from reliability claims. Work 48 and Gym 48 each pass 62/64 confirmation cases (96.875% observed). This is not enough to establish a 95% population success rate with a conventional lower confidence bound. A batch containing 32 required outputs also has a different reliability definition from an individual-case acceptance fraction. Corrections/fallback or explicit partial rejection are needed before treating such a batch as delivered.

All 64 adaptive cases pass in-range. Under an iid binomial assumption, the one-sided 95% exact lower bound for 64/64 is approximately 95.43%; this only addresses the declared generated-case distribution and excludes timing reliability. Eight successes in the secondary prototype yield a corresponding lower bound of only 68.77%. Present “8/8 observed” directly.

## 6. Secondary prototype and opportunity discovery

The frozen secondary prototype uses eight fresh cases and eight candidate gains each, with no additional training. It selects candidates using numerical intervals and uses Schur refinement for unresolved potential winners. Its separate exact oracle checks regret after policy execution. This is a defensible constrained technical prototype.

Initial observed totals were approximately 2.035 seconds for Schur, 0.289 for adaptive fallback, 0.186 for work48 fallback and 0.406 for Gym 48 fallback. Guarded exposed-case totals were 2.110, 0.383, 0.282 and 0.457 seconds respectively. All methods selected the same grid optimum in all eight cases; all three non-dense policies met the declared two-second deadline in these runs.

The initial Schur miss was just 35 milliseconds above the two-second boundary. It should be called an observed miss, not reliable infeasibility. More importantly, **the competent ordinary adaptive policy already qualifies**. Specialist access therefore did not create this offering's technical feasibility; it changed execution time. Gym was slower than the ordinary adaptive policy on this task after its extra refinements.

The protocol's “64 candidate queries” should be explained as 64 distinct case/gain settings. Fallback and refinement invoke extra numerical kernels, which are correctly recorded and must be charged. Do not imply a 64-total-kernel-call budget.

This prototype does not by itself test open-ended customer opportunity discovery. It tests a declared adjacent offering derived from a familiar engineering mechanism. No matched enterprises independently invented proposals, no external customer panel assessed usefulness, and no willingness-to-pay trial was conducted in these numerical files. If a separate simulated proposal process is included, label its evidence separately. An honest conclusion is “no demonstrated capability-driven new offering or new market.”

## 7. Accounting implications

`stage_costs.json` is a kernel-stage timing log, not a complete economic ledger. It includes paid-work snapshot solves, fitting, Gym assessment/refitting and an ordinary basis build. It does not itself price model orchestration, study authoring, input qualification, independent test/reference solves, prototype selection, packaging, failed sales, support, maintenance, taxes or collection delays.

Complete B/C assessment and prototype costs must be provided in the economic model, with observed kernel timings separated from assumed dollar budgets. Reference-oracle work can be excluded from serving latency because it is ex-post research work, but it must not disappear from research/validation costs. Work-generated snapshots already charged to category A should not receive a second R&D charge; fitting/admission beyond the paid outcome belongs to B, optional extra development to C.

A fraction of a second saved on these small systems has negligible compute value at ordinary unit prices. No additional price premium, customer volume, higher acceptance, or commercially useful capacity should be assigned solely because the solver is faster. Customer validation, integration and expert interpretation may dominate actual delivery economics. All such effects remain scenarios until observed.

## 8. Provenance checks and review disposition

The initial source archived as `archived_initial/lyapunov_study.py` matches the original freeze SHA256:

`124da4d93774f5150dee668e6ada3c8c677b1db63532075801063a7ff4b647c2`.

The initial protocol matches:

`9dba80b867dc00f497d30ab34f342461eb67d8c8788dc0094333f0516ca9fc3c`.

The archived initial prototype source matches:

`f420836a052ee4d2d569049175112247b5c34d6c1c71fbf80add83bc8050bb71`.

Its protocol matches:

`3ebb274ae83faa3e8a526f63b99a934e028c7b01801ac594e707a9ab8589dd9d`.

All four stored basis-array hashes match the initial freeze. Safety revalidation preserves the original basis hashes and acceptance counts. It uses exposed cases, so it must remain labeled as revalidation rather than additional protected confirmation. Local hash freezing records the declared sequence; it is not external preregistration or tamper-proof attestation.

**Disposition:** Suitable for a bounded, reproducible hybrid study after the above wording and accounting requirements are satisfied. Preserve the null and negative results. The defensible result is an operating policy that uses ordinary tools, permits restricted artifact reuse, and declines extra specialization when marginal benefits do not cover costs. A future live engineering service needs customer-scoped input validation, rights-cleared data, independently checked physical applicability, deployment latency measurements, a service contract and observed demand.
