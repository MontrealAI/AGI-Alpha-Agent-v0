# Matrix-function production compiler: reject as the next flagship

## Decision

The tested proposal does produce numerical vectors approximating `exp(A) @ v`, but it does not establish a new productive capability from OpenAI family 325. Its polynomial and its strongest applicable constant-2 bound were already available. The numerical campaign also finds only small gains when the constant is compared with the weaker general 2017 bound. This is a bounded negative investigation of this proposed construction, not a claim that complete Crouzeix 2 has no useful computational consequences.

All investigation files are confined to `alternative_probe`; frozen flagship study source was not edited. The protocol and source hash were written before the measurements. A subsequent primary-source check identified an even stronger classical comparator; the separate `matrix_probe_assessment.json` records that correction without changing the raw experiment.

## Exact mathematical scope and chronology

OpenAI's family-325 scope description reports the sharp complete inequality for arbitrary positive matrix dimensions and coefficient dimensions, not merely positive semidefinite matrices. For a matrix-valued polynomial or suitable analytic matrix-valued function, the norm after evaluation at an arbitrary matrix or bounded Hilbert-space operator is at most twice the supremum on its numerical range. A linked structural result concerns an attained similarity and a common positive boundary representation on regular analytic convex domains. This investigation read the stated formalization scope; it did not independently rebuild Lean or audit the complete proof. [Source: OpenAI family 325](https://github.com/openai/math/blob/main/lean/docs/325.md).

The general *complete* constant was already `1 + sqrt(2)` in Crouzeix–Palencia (2017). Replacing it by 2 lowers that multiplier by approximately 17.16%; any change in executable polynomial degree still depends on the approximation and matrix. [Source: authors' 2017 paper](https://arxiv.org/abs/1702.00668).

The scalar inequality needed for `exp(A) @ v` was public before the October release: Lorist–Schwenninger submitted their proof on August 4, 2026, revised it on August 17, and give the scalar theorem for bounded Hilbert-space operators in Theorem 3. Their Section 3(iv) expressly distinguishes the complete case, which their argument does not directly establish. Consequently the new complete scope is unused by this scalar exponential action. [Source: full August paper](https://arxiv.org/html/2608.03841v2). TU Delft independently records the announcement on September 14, 2026. [Source: official university announcement](https://www.tudelft.nl/en/2026/eemcs/crouzeixs-mathematical-puzzle-has-finally-been-solved).

There is an older and more decisive comparator for the implemented construction: any disk containing the numerical range is already a complete 2-spectral set by classical numerical-radius dilation and the Okubo–Ando result. Davidson–Paulsen–Woerdeman explicitly summarize this fact on printed pages 3–4, including the implication from numerical radius at most one. The probe uses a disk enclosure throughout, so **the entire constant-2 program is also a conventional program with the same degree, vector output, and operation count**. It does not require the new theorem, even for matrix-valued coefficients. [Source: authors' paper, preprint 2016](https://www.math.uwaterloo.ca/~krdavids/Preprints/DPWnum_range.pdf).

## Executed production and conventional comparisons

The callable `production_call` in `matrix_action_probe.py` chooses a Taylor degree and computes the resulting vector using repeated sparse matrix-vector products. It is ordinary shifted Taylor approximation, not a newly invented algorithm. Forty-eight matrices generate 144 matrix/tolerance cases:

- Matrix sizes 16, 32, 64, and 128.
- A Jordan family, a symmetric diffusion control, and two nonnormal tridiagonal convection-diffusion families with upper/lower coefficients 4/1 and 12/1.
- Time factors 0.25, 1, and 4; unit-norm seeded input vectors.
- Absolute 2-norm tolerances `1e-6`, `1e-10`, and `1e-12`.

For `A = c I + B`, a scalar disk radius bound `R` gives the analytical truncation estimate

\[
\|e^A v-e^c\sum_{k=0}^d B^kv/k!\|
\le C e^c \frac{R^{d+1}}{(d+1)!}
\frac{1}{1-R/(d+2)},\qquad d+2>R,\quad\|v\|=1.
\]

The nonnegative tridiagonal coefficients give numerical radius `(upper+lower)*cos(pi/(n+1))`. A rational cosine upper bound encloses it. Separate conventional controls use the triangle-inequality operator-norm bound with constant 1, constant 1 on the symmetric control, and exact nilpotency to truncate Jordan polynomials at degree `n-1`. A further conventional comparator is the identical constant-2 disk program established above.

The comparison also executes SciPy's production `expm_multiply`, and a dense `scipy.linalg.expm` supplies a numerical reference. Al-Mohy–Higham's established exponential-action algorithm already uses shifted/scaled Taylor series and sharper power-norm estimates; it is not a new capability opened by Crouzeix 2. [Source: authors' 2011 paper and code](https://eprints.maths.manchester.ac.uk/1591/). The installed version was SciPy 1.17.0 with NumPy 2.3.5.

## Results

Every computed polynomial output met its declared tolerance against the numerical reference. Outputs for four representative 32-dimensional cases, together with inputs and reference vectors, are saved in `produced_matrix_actions.npz`.

| Comparison | Result across 144 cases |
|---|---:|
| Constant 2 reduces degree relative to general `1+sqrt(2)` | 18 cases |
| Largest reduction relative to general `1+sqrt(2)` | 1 matrix-vector product |
| Total matvecs, general `1+sqrt(2)` → 2 | 4,194 → 4,176 |
| Constant 2 versus norm/special controls: lower / equal / higher degree | 5 / 87 / 52 |
| Constant 2 versus conventional portfolio including classical disk result: lower / equal / higher degree | 0 / 92 / 52 |

Thus even the favorable constant ablation removes only 18 of 4,194 products, about 0.43%. The strongest directly applicable conventional disk comparator is exactly the same program. There is no candidate-only production gain to attribute to the October result.

As a concrete nonnormal example, the 16-dimensional 12/1 convection-diffusion case at time 4 and tolerance `1e-10` uses degrees 103 with the general 2017 constant, 102 with constant 2, and 104 with the simple norm control. The 102-degree method already follows from the classical disk result. For the Jordan case at size 16 and time 4, constant 2 uses 22 products while nilpotency needs only 15, with equal numerical output to observed precision.

The median measured ratio of constant-2 runtime to the general 2017 program was 0.991; versus the norm/special program it was 1.015. On these small cases the simple polynomial loop was much faster than stock SciPy (`0.122` median runtime ratio), but the identical classical disk implementation enjoys precisely that advantage. Generic SciPy overhead and its tighter default accuracy make this unsuitable as a claim of a new algorithmic improvement. The stock public SciPy API does not expose a tolerance parameter; its errors were evaluated against the same acceptance thresholds, not at a matching internal requested precision. Timings use five repeated calls after warmup and include degree selection and polynomial evaluation, but exclude matrix construction, numerical-range enclosure setup, and reference evaluation. They are a small local probe, not production throughput measurements.

## Certification and remaining boundary

The bound controls mathematical truncation. The implementation evaluates it and the vector recurrence with ordinary floating-point arithmetic. Dense `expm` is a numerical reference, not an interval oracle. No total roundoff certificate, formal end-to-end arithmetic proof, rigorous large-scale geometry algorithm, customer evidence, payment, or profitability was created. Calling these outputs a certified production service would overstate what was built.

Reopening this route would require a concrete matrix-valued, non-disk task that actually uses the newly complete scope, and measurable useful production beyond conventional approximants and specialized bounds. A tightened certificate alone, a scalar `exp(A)v` wrapper, or a relabeling of the classical disk compiler is insufficient. The present evidence supports stopping this candidate and preserving the negative result.

## Reproduce

From the workspace root:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python alternative_probe/matrix_action_probe.py
python alternative_probe/assess_probe.py
```

The first command regenerates the declared protocol, raw measurements, and actual output vectors; the second preserves the stronger-prior-art assessment alongside them. `matrix_probe_results.json` is the complete case-level measurement record, and `matrix_probe_assessment.json` records the final rejection and the exact conventional comparator.
