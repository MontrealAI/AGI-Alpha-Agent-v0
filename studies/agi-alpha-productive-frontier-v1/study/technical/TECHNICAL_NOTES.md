# Numerical evidence: the useful advantage that did not create a new service

## Scope and status

This is an executed numerical study on synthetic, nondimensional coupled-mode systems. It is not a physical plant experiment, a live frontier-model evaluation, a safety certificate, or evidence of buyer demand. The learned artifact is a numerical subspace, not a fine-tuned foundation model. The operating box, error criteria, methods, splits, rank limit and query deadlines were serialized before the original protected numerical confirmation. The numerical proposal is a bounded, enumerative engineering prototype; it is not evidence that an agent independently discovered a new market.

The mission is to calculate stationary disturbance energy accurately, with a numerical error certificate, across parameter variations of the same dynamical family. A second service selects added damping on a frozen grid using that capability. Ordinary adaptive Krylov tools are competent alternatives. Their success is a valid result.

## Equations and independently checkable certificates

For each parameter vector, the code constructs a real matrix `A = -D + K`, where `D` is positive diagonal and `K` is skew symmetric, and two localized disturbance channels `B`. The steady covariance solves

\[
A X + X A^T + B B^T = 0.
\]

If `alpha > 0` and `(A+A.T)/2 <= -alpha I`, the semigroup norm satisfies `||exp(At)||_2 <= exp(-alpha t)`. For any approximation `Xhat`, define `R = A Xhat + Xhat A.T + B B.T`. Integrating the error equation gives

\[
\|X-X_{\rm approx}\|_F \leq F\equiv\frac{\|R\|_F}{2\alpha},\qquad
|\operatorname{tr}(X-X_{\rm approx})|\leq\delta\equiv\sqrt{n}F.
\]

When the denominator is positive, `delta / (trace(Xhat)-delta)` is a bound on relative trace error with the true trace in the denominator. Otherwise the implementation explicitly refuses a finite relative certificate. Similarly, `F/(||Xhat||F-F)` bounds relative Frobenius error. Since `|trace(Xhat)| <= sqrt(n)||Xhat||F`, a one-percent trace certificate implies a Frobenius certificate no worse than one percent, which is stricter than the declared two-percent audit requirement. The hidden Schur reference is used only for ex-post numerical auditing; no policy receives it to select an answer or decide whether to invoke fallback.

The current implementation validates shapes, finite values, covariance symmetry, basis orthogonality, artifact hashes and the supplied dissipativity bound. It first uses a Gershgorin sufficient bound and, when necessary, verifies the maximum eigenvalue of the symmetric part. This is a numerical certificate under the stated matrix assumptions; it does not establish robustness of a physical controller or safety under unmodeled dynamics.

## Learning and ordinary alternatives

Six origin-work instances produce exact covariance solutions. The retained work basis comprises the leading eigenvectors of their aggregate covariance, at rank24 and rank48. The optional Gym evaluates the rank48 work basis on20 development instances, selects the four worst residual certificates, pays for four additional full solutions, and refits a rank48 basis. This is an actual data-dependent update of an executable numerical artifact. It is not more prompting presented as learning, and no proprietary weights are assumed.

The direct comparator uses SciPy's Bartels-Stewart solver. An adaptive block Krylov comparator constructs its own query-specific basis with reorthogonalization and checks a residual certificate every eight dimensions, up to rank96. A fixed rank48 central-instance Krylov basis is a nonlearned library reuse control. Work rank48 versus Gym rank48 isolates the update from a rank increase; rank24 is reported separately. The adaptive comparator is sufficient to invalidate the claim that access to the learned basis uniquely enables the tested service. The study does not claim superiority to specialized packages such as M.E.S.S. or optimally configured rational/extended Krylov solvers.

## Original protected results

There are64 confirmation instances,32 shifted instances with lower damping and greater coupling, and32 early prototype instances. Every raw row, parameter vector, artifact and source hash is retained.

| Method | Confirmation accepted | Shift accepted |
|---|---:|---:|
| Schur |64/64|32/32|
| Adaptive Krylov, before fallback |64/64|22/32|
| Fixed central Krylov48 |2/64|0/32|
| Work POD24 |17/64|0/32|
| Work POD48 |62/64|0/32|
| Gym POD48 |62/64|0/32|

The original32-case timings were1.10–1.15s for Schur,0.177–0.224s for adaptive Krylov and0.078–0.081s for Gym48. Ordinary adaptive Krylov already met the frozen0.25s interactive contract on those two batches. Optional Gym improved some residual magnitudes but did not improve the64-case acceptance count. All retained bases failed certification on the shifted family. A certificate failure is a refusal, not permission to deliver a numerically plausible answer.

These are finite-sample observations. An empirical62/64 rate is not a demonstrated95% population SLA. There are only two observed32-case confirmation batches, so a robust latency SLA is also unestablished. Safety hardening changed adaptive timings to0.213 and0.259s, straddling the same0.25s boundary; the original timings and corrected timings are both retained. This is evidence of latency sensitivity, not permission to move the boundary or select the favorable run.

## Opportunity prototype and final confirmation

The proposal retains the original purpose: choose added damping `g` on `{0,0.1,...,0.7}` to minimize `trace(X_g) + 0.15*g^2`, with `A_g=A-gI`. The coefficient0.15 and the2s deadline for eight cases are explicit research assumptions. All policies see the same grid, objective and numerical evidence. Each candidate produces an objective interval using the covariance certificate. Overlapping potential winners trigger ordinary Schur refinement; unresolved overlap requires abstention. This demonstrates executable composition and checks coordination cost, without claiming a new market.

Initial fresh seed6401 was executed before the formal economic proposal JSON was serialized. Its numerical criteria were frozen in `prototype_protocol.json`; its source and protocol hashes precede execution. The later economic proposal file must not be described as hashed before6401. Seed6401 is retained as an exploratory prototype. Following boundary-validation fixes, one final fresh seed7401 was evaluated under the unchanged8×8 grid, objective, criteria and deadline. Both implementation hashes, the proposal hash, protocol hash, seed and timestamp were recorded before evaluation. No basis, threshold or candidate was retuned.

| Final seed7401 policy | Eight-case service seconds | Accepted optimal selections | Schur ranking refinements |
|---|---:|---:|---:|
| Schur |2.0554|8/8|0|
| Adaptive Krylov with fallback |0.4662|8/8|2|
| Work48 with fallback |0.1728|8/8|0|
| Gym48 with fallback |0.4592|8/8|8|

Every method achieved zero objective regret against the independent direct oracle. Schur narrowly missed the assumed2s service deadline; all other methods met it. Work48 is the strongest measured reusable artifact. Gym48 incurred more ranking refinements, largely erasing its primitive speed advantage. Ordinary adaptive tools already qualified, so the prototype is an improved service, not a demonstrated new offering enabled only by Alpha. The absolute saved CPU time is small; its economic importance must be tested against actual integration, assurance and maintenance costs.

The count64 denotes distinct candidate settings per policy, not total numerical kernel calls. Fallback and ranking refinements add calls and are recorded. Independent audit solves, origin solves, development assessment, failed candidates, optional Gym and repeat validation consume study resources. Revalidation is research cost, not a second charge for a hypothetical originating customer job.

## Provenance and correction history

The original `lyapunov_study.py` is preserved byte-for-byte under `archived_initial/`; SHA-256 is `124da4d93774f5150dee668e6ada3c8c677b1db63532075801063a7ff4b647c2`. The original source trusted caller-provided `alpha` and marked Schur accepted without applying the common certificate gate. Current code adds the missing boundary checks and uses a finite, verified gate. Every original acceptance count and every learned artifact hash remained unchanged in scoped exposed-case revalidation. `results/` contains original protected observations; `results_validated/` contains explicitly labeled exposed-case checks; `results_final_prototype/` contains fresh seed7401.

Six focused tests cover invalid dissipativity claims, malformed/nonfinite inputs, corrupted/nonorthogonal artifacts, independent residual-bound checks, initial-source provenance, and a recipient in a separate Python process. The recipient loads only a digest-checked basis and fresh input parameters; it does not load training snapshots. Byte-identical transfer and matching numerical output are observed. This is local process transfer, not live ENS authentication. Repository-native authorization tests are a separate fixture with their own evidence.

## Reproduction

From this directory, execute `python lyapunov_study.py --out reproduction_a`, then the proposal runner with the documented original or final seed and proposal file. The published result directories should be preserved; use a new output directory. `python test_numerics.py` performs the six boundary/transfer checks. `python fallback_validation.py` replays the hardened composition on exposed original cases and labels the result accordingly. Dependencies are Python3.11–3.13, NumPy, SciPy and threadpoolctl; exact observed versions appear in `technical_results.json`. BLAS is constrained to one thread. Wall times will change by hardware, contention and library build.

## Primary technical sources

- SciPy, `solve_continuous_lyapunov`: <https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_continuous_lyapunov.html>.
- M.E.S.S. primary software report: <https://arxiv.org/abs/2003.02088>; official project <https://www.mpi-magdeburg.mpg.de/projects/mess>.
- Benner, Palitta and Saak, integrated extended Krylov/ADI methods: <https://link.springer.com/article/10.1007/s11075-022-01409-5>.
- MathWorks, system norms and disturbance interpretation: <https://www.mathworks.com/help/control/ref/dynamicsystem.norm.html>.

The residual bound above follows directly from the displayed dissipativity argument; it is a standard analytic device, not a new theorem or evidence of specialist ASI.
