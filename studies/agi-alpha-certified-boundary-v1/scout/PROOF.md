# A universal lower bound for the heft of finite exact congruence partitions

**Research-review status.** The numerical discovery has been converted into exact rational obligations. A second workstream independently reimplemented and verified all 78 bivariate patches, the univariate tail bounds and the finite-length objective. A separately derived uniform midpoint identity proves the stronger bound stated below. The theorem has not been externally peer-reviewed or formalized in a proof assistant. A bounded prior-art search found the question explicitly open in the author's 2026 problem list; this is not a universal priority claim.

## Original question and exact scope

Gerry Myerson asks whether, for any positive integer n, there is a partition of the integers 1,...,n by congruence classes with distinct positive integer moduli, each class hitting the interval at least twice, whose **heft** h=sum_i 1/m_i is below 0.98.

Primary question: https://mathoverflow.net/questions/462981/open-problems-which-might-benefit-from-computational-experiments/499017 . Its 2026 updates settle other requested constructions but continue to state the h<0.98 question. Foundational definition: Myerson, Poon and Simpson, Discrete Mathematics 309(13):4428-4434 (2009), DOI 10.1016/j.disc.2009.02.002. Emanuel's 2012 paper gives the same definition and discusses known heft values: https://math.colgate.edu/~integers/a8self/a8self.pdf .

**Theorem (certificate-backed, subject to independent review).** Let n be a positive integer. Suppose finitely many complete congruence classes, restricted to [1,n], partition every integer in that interval exactly once and each class contains at least two interval integers. Then

\[
\sum_i\frac1{m_i}>
\frac{1891871140656049}{1929687500000000}
=0.9804028583156853\ldots>\frac{49}{50}=0.98.
\]

The proof does not require distinct moduli. Thus it applies to the original incongruent restricted disjoint covering systems and to the larger class allowing repeated moduli. The complete-congruence-class requirement is retained: the result does not apply to arbitrary truncated arithmetic progressions or classes from which inconvenient points have been removed. A class may not be a singleton. The assertion for n=1 is vacuous because no class can hit twice.

## Explicit witness

Write T_r for the Chebyshev polynomial of the first kind. Define the following exact degree-20 polynomial on [0,1]:

\[
f(x)=\frac{2499}{2500\cdot10^{10}}\sum_{j=0}^{10}b_jT_{2j}(2x-1),
\]

where

\[
(b_0,\ldots,b_{10})=(7061527976,-8616261687,2079655784,
-480883959,30533879,8370806,32646497,-16295510,
3707761,-15109523,30943868).
\]

It is symmetric: f(1-x)=f(x). Its integral is exactly

\[
I=\int_0^1f(x)\,dx
=\frac{1891871140656049}{1929687500000000}
=0.9804028583156853\ldots.
\]

The exact coefficient file is `revised_polynomial.json`; no floating-point coefficient is used by the certificate checkers.

## 1. From a finite partition to a universal class inequality

Assign weight w_i=f((i-1/2)/n)/n to each interval integer i. Consider a complete congruence class with modulus m and first interval hit r. Its hits are r,r+m,...,r+(k-1)m, with k>=2. Set

\[
d=m/n,\qquad a=(r-1/2)/n.
\]

Because the previous and next class members lie outside [1,n],

\[
\max(0,1-kd)\le a\le\min(d,1-(k-1)d),\qquad
\frac1{k+1}\le d\le\frac1{k-1}.
\]

The actual integer data satisfy strict versions of the exterior inequalities, but the certificate covers their closed relaxation. It suffices to prove, for every such (k,a,d),

\[
d\sum_{j=0}^{k-1}f(a+jd)\le1.\tag{C}
\]

Then that class has total assigned weight at most 1/m. Since the classes partition every integer exactly once, summing their inequalities gives

\[
h=\sum_i\frac1{m_i}\ \ge\ \frac1n\sum_{r=1}^{n}f((r-1/2)/n)=:M_n.\tag{D}
\]

Weights need not be assumed nonnegative for this exact-partition argument.

## 2. Exact finite verification for class sizes 2 through 40

Let F(t)=f((t+1)/2). Set u=2a+(k-1)d-1. Symmetry allows u>=0, with

\[
0\le u\le\min((k+1)d-1,1-(k-1)d).
\]

The domain splits into two triangular patches, each parameterized by (s,v) in [0,1]^2:

\[
\begin{array}{lll}
\text{lower spacing:}&d=(k+s)/(k(k+1)),&u=vs/k,\\
\text{upper spacing:}&d=(k-1+s)/(k(k-1)),&u=v(1-s)/k.
\end{array}
\]

For every k=2,...,40 and both patches, define

\[
P_k(s,v)=1-d\sum_{j=0}^{k-1}F\big(u+(2j-k+1)d\big).
\]

This is a rational polynomial of bidegree at most (21,20). `certify_bernstein.py` expands it with integers after clearing a positive denominator, converts it to tensor-product Bernstein coefficients, and subdivides a patch at exact midpoints until every coefficient is nonnegative. A polynomial is a convex combination of its Bernstein coefficients on the unit square, so their nonnegativity proves P_k>=0 throughout the entire patch.

All **78 patches** pass. The exact calculation visits **106 nodes**, has **92 accepted leaves**, and reaches maximum subdivision depth **6**. This is verification of continuous domains, not evaluation only at sampled points. No numerical optimizer or tolerance occurs in this checker.

The independent implementation expands each summand by sparse Horner arithmetic, reconstructs the centered polynomial from an independently derived polynomial in x, uses factorial Bernstein conversion, and begins subdivision on the opposite coordinate. It also passes all 78 patches, with 95 accepted leaves and maximum depth 6. Different subdivision trees are expected; agreement concerns the continuous inequalities, not the number of leaves.

The coefficient expansion uses

\[
\sum_{j=0}^{k-1}\big(u+(2j-k+1)d\big)^\ell
=\sum_{r=0}^{\ell}{\ell\choose r}u^{\ell-r}d^r
\sum_{j=0}^{k-1}(2j-k+1)^r.
\]

Only even ell and r remain because F is even and the centered integer sequence is symmetric. Each square patch has common positive denominator DEN*[k(k+/-1)]^21, where DEN clears the coefficients of F. This gives (C) for 2<=k<=40.

## 3. All larger class sizes from an analytic bound

Let g=f-f(0) on [0,1] and extend g by zero outside that interval. Symmetry makes the extension continuous at both endpoints. Exact univariate Bernstein bounds establish the convenient outward bounds

\[
|f(0)|<3/250,\qquad \|f''\|_\infty<486,\qquad
\operatorname{TV}(g')<24.
\]

The reported tighter rational upper bounds are approximately 485.76248165584 for the second derivative and 23.05544856893 for the total variation of the extended derivative. The latter includes the two endpoint jumps of g', not merely the integral of |f''|.

For any shifted grid of spacing d, the composite trapezoid error bound for a continuous compactly supported function whose derivative has bounded variation is

\[
\left|d\sum_{j\in\mathbb Z}g(a+jd)-\int_{\mathbb R}g\right|
\le \frac{d^2}{8}\operatorname{TV}(g').
\]

One way to see the constant is to integrate the piecewise-linear interpolation error on each grid cell. Its Peano kernel has absolute value at most d^2/8; summing against the distributional second derivative gives the variation bound. The expression d*sum_j g is exactly the composite trapezoid integral because the compactly supported endpoint contributions vanish.

For an admissible complete class, |kd-1|<=d. Adding back the constant f(0) therefore gives

\[
d\sum_{j=0}^{k-1}f(a+jd)
\le I+|f(0)|d+\frac{d^2}{8}\operatorname{TV}(g').
\]

When k>=41, d<=1/40, so the right side is at most

\[
I+\frac{3}{10000}+\frac{3}{1600}
=I+0.002175<1.
\]

Thus (C) also holds for every k>=41. Together with the 78 exact patches, this proves the universal class inequality for every allowed class size.

## 4. The finite-length objective is strictly above 0.98

The composite midpoint error bound gives

\[
M_n\ge I-\frac{\|f''\|_\infty}{24n^2}
> I-\frac{486}{24n^2}.
\]

For every n>=225, the subtracted quantity is at most 1/2500=0.0004, and hence

\[
M_n>I-0.0004=0.9800028583156853\ldots>0.98.
\]

For 2<=n<=224, direct rational evaluation of the finite sum M_n verifies M_n>49/50. The independent checker actually checks the overlapping range 2<=n<=240. Consequently every n admitting a cover satisfies M_n>0.98. Combining this with (D) completes the proof.

## 5. A strengthened uniform bound: the finite average exceeds the integral

An additional exact certificate proves M_n>I for every integer n>=2, which supplies the stronger constant in the theorem. This refinement is independent of the midpoint-remainder estimate in Section 4.

Let t=1/n^2, z_i=(2i-1-n)/n, and write A_r(t) for the average of z_i^(2r). The telescoping identity

\[
\sum_{i=1}^n\big[(z_i+1/n)^{2r+1}-(z_i-1/n)^{2r+1}\big]=2
\]

gives the polynomial recurrence

\[
A_0(t)=1,\qquad
A_r(t)=\frac{1-\sum_{\ell=1}^{r}{2r+1\choose2\ell+1}t^\ell A_{r-\ell}(t)}{2r+1}.
\]

If F(z)=sum_{r=0}^{10}c_r z^(2r), then

\[
M_n=\sum_{r=0}^{10}c_r A_r(t)=I+tQ(t),
\]

where Q is a degree-nine polynomial with exact rational coefficients. This identity follows solely from finite sums and therefore holds for every positive integer n. Its constant term equals I since A_r(0)=1/(2r+1).

The independent checker constructs Q from the recurrence and an explicit formula for Chebyshev coefficients, without using Euler--Maclaurin, Bernoulli numbers, or the earlier polynomial conversion. Its coefficient list agrees identically with a separate Euler--Maclaurin construction. It then certifies Q(t)>0 on the entire interval [0,1/16] using Bernstein coefficients on the 16 exact intervals [j/256,(j+1)/256], j=0,...,15. Every local Bernstein coefficient is strictly positive. The exact coefficient list and all 16 rational lower bounds are stored in `lineage/myerson_independent_uniform.json`.

For n>=4, t lies in that interval and is positive, so M_n>I. Direct rational evaluation gives the two remaining differences:

\[
M_2-I=\frac{184569613348897}{61750000000000000}>0,
\]

\[
M_3-I=\frac{1033236506971259179273363}{53827234190437500000000000}>0.
\]

Thus h>=M_n>I for all n>=2, and the theorem follows. This exact constant is a certified lower bound, not a claim that the best possible heft has been determined.

## What the computation establishes, and what it does not

The certificate and two independent implementations establish a computer-assisted lower-bound argument for the stated low-heft outcome, with external mathematical review still pending. It does not establish a new solver, a universal best heft constant, a commercially sold service, a measured frontier-model advantage, or a general profitable discovery engine. The first useful outcome is a reusable exact proof artifact addressing a documented research question. Other researchers can check it without repeating the floating-point search.

The conventional challenge is substantive: exact-cover enumeration and integer programming already build and reject individual finite instances. The contribution, if novel after fuller review, is the particular universal certificate and its mathematical consequence. An established polynomial-verification pipeline can check or reconstruct the same proof; its availability does not invalidate a newly discovered theorem, but it prevents an exclusive-algorithm claim. No controlled comparison of discovery effort was run.

## Failed evidence retained

The first degree-20 numerical witness looked promising on a coarse phase grid, with integral 0.98558247. Continuous search found a five-percent constraint violation. The independent auditor found an exact integer realization: n=26, modulus 15, residue 11, class {11,26}, for which the attempted class inequality fails. That witness is rejected, not silently replaced in the evidence record.

Dense constraints and eight cutting-plane iterations produced the revised witness. Coefficients were rounded to exact decimal rationals and reduced by 2499/2500 before exact verification. Files preserve the initial probe, its counterexample, every revised numerical iterate, the revised rational witness, the finite-cover MILP attempts, and all exact checker outputs.

## Reproduction and validation roles

From the package root:

```
python3 scout/certify_bernstein.py
python3 lineage/myerson_independent_bounds.py scout/revised_polynomial.json lineage/myerson_revised_independent_bounds.json
python3 lineage/myerson_independent_bivariate.py
python3 study/midpoint_uniform.py
python3 lineage/myerson_independent_uniform.py
```

All certificate checkers use rational/integer arithmetic. The independent uniform checker reads the root checker's result only to assert equality of the separately derived coefficient lists; its positivity proof is calculated independently. The search programs require NumPy and SciPy; search time limits can yield different incumbents and are not mathematical evidence. The frozen rational certificate and its exact verification are the reproducible result.

The witness bytes have SHA-256 `c92bc1977bbb6804af862d52c82507793ff57e2355c501477f609e7a1dd22633`. The retained witness JSON says `UNVERIFIED` because it was frozen before independent checking; the subsequent checker receipts above establish the verified state without changing the frozen candidate's identity.
