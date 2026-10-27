# Independent mathematical audit: finite residue partition lower bound

Status: **the independent computer-assisted certificate passes**. The revised
witness passes the tail, every finite-n objective obligation, and all 78 exact
bivariate class inequalities for lengths 2 through 40. A separately derived
uniform midpoint certificate strengthens this to
h>1891871140656049/1929687500000000, approximately 0.9804028583156853, under
the stated definitions. Literature priority remains subject to
review. The original sampled witness is rejected by an exact counterexample.

## Original problem and source

Gerry Myerson's author-posted question defines a length-n cover as congruence
classes modulo distinct positive integers, partitioning the integers 1 through n,
with at least two members of the interval in each class. Its heft is the sum of
the reciprocals of the moduli. The question asks whether any such cover has heft
below 0.98. The August 2026 updates address other directions; no resolution of
this lower-heft question appears in the inspected source.

Primary source:
https://mathoverflow.net/questions/462981/open-problems-which-might-benefit-from-computational-experiments/499017

Original paper: Gerry Myerson, Jacky Poon, and Jamie Simpson, *Incongruent
restricted disjoint covering systems*, Discrete Mathematics 309 (2009),
4428–4434, DOI 10.1016/j.disc.2009.02.002. The retrieved primary search extract
states Theorem 4.2 as (n-t)/(n-1) <= h <= (n+t)/(n+1), where t is the number
of classes. Full PDF access to the public CORE copy returned HTTP 403; do not
describe its entire contents as inspected.

## Valid dual reduction

Let f be a real polynomial symmetric about 1/2. For every integer k>=2,
let D_k be all (a,d) satisfying

    1/(k+1) <= d <= 1/(k-1),
    max(0,1-k*d) <= a <= min(d,1-(k-1)*d).

Suppose d*sum_{j=0}^{k-1} f(a+j*d) <= 1 throughout every D_k.
For any actual congruence class modulo m, write its first member r in [1,n],
put d=m/n and a=(r-1/2)/n, and let k be its number of members. Since the previous
member is <1 and the next member is >n, this (a,d) lies in D_k. Consequently

    (1/n)*sum_{i in this class} f((i-1/2)/n) <= 1/m.

Summing over the partition proves h >= S_n(f), where
S_n(f)=(1/n)*sum_{i=1}^n f((i-1/2)/n). Negative polynomial values are permitted:
the constraints are an exact partition, not an arbitrary overlapping cover.
The distinct-modulus condition is unused, so any completed result would apply
to the larger family allowing repeated moduli, provided classes still partition
the interval and each has at least two members. n=1 admits no such cover.

## Domain coverage for the proposed bivariate certificate

Set F(z)=f((z+1)/2), and u=2a+(k-1)*d-1. By the symmetry of F, reversing the
k summands lets one restrict to u>=0 without losing any configurations.
The exact domain is

    0 <= u <= min((k+1)*d-1, 1-(k-1)*d).

It is covered by two unit-square parameterizations, with s,v in [0,1]:

    lower: d=1/(k+1)+s/[k(k+1)], u=v*s/k;
    upper: d=1/k+s/[k(k-1)], u=v*(1-s)/k.

The polynomial to be certified is

    1-d*sum_{j=0}^{k-1} F(u+(2j-k+1)*d).

An exact nonnegative Bernstein certificate on both squares for each k=2,...,40,
combined with the tail below, proves every needed inequality.

The discovery stream's moment-expansion checker passed all 78 patches. An
independent implementation in `myerson_independent_bivariate.py` also passes
all 78. It derives F(z) by substituting (z+1)/2 in independently constructed
f(x); expands each of the k summands using generic sparse polynomial Horner
multiplication; uses factorial Bernstein conversion weights; and uses explicit
binomial subdivision formulas starting on the opposite axis. Its certificate
has 95 leaves and maximum depth 6, covers every square exactly, and reports
exact rational lower bounds in `myerson_independent_bivariate.json`.

The frozen witness SHA-256 at verification was
`c92bc1977bbb6804af862d52c82507793ff57e2355c501477f609e7a1dd22633`.

## Exact rejection of the original witness

The original coarse grid appeared feasible with integral 0.9855824689586415.
It is not feasible. With n=26, modulus m=15, and first member r=11, the class is
{11,26}. Exact evaluation gives

    d*sum f =
    2585311195333525853352450417160683219223491 /
    2470645290734503927044130000000000000000000
    = approximately 1.0464113181398584 > 1.

This is a real finite-class counterexample, not only a continuous relaxation
objection. More counterexamples are preserved in
`myerson_original_counterexample.json`. The original integral is not a lower
bound on heft and must not appear as an established result.

## Revised witness and independently checked analytic obligations

The revised witness is frozen in `scout/revised_polynomial.json`, with 11 exact
rational coefficients of T_(2j)(2x-1). It was produced by cutting-plane search,
rounding to ten decimal places, and multiplying by 2499/2500. This independent
audit uses those final rational coefficients, not floating point values.

The exact integral is

    I=1891871140656049/1929687500000000
     = approximately 0.9804028583156853.

`myerson_independent_bounds.py` constructs the polynomial from the Chebyshev
recurrence using rational arithmetic, differentiates it, and represents f'' in
the Bernstein basis on 64 equal rational intervals. A polynomial in Bernstein
form lies within the range of its coefficients. The triangle inequality and
the fact that each degree-D Bernstein basis function integrates to 1/(D+1)
also give an exact integral bound for |f''|. No floating point comparison is
used to accept any inequality.

The resulting bounds are:

- sup |f''| <= 485.76248165583934 (decimal approximation to an exact rational);
- TV(g') <= 23.055448568925648, where g=f-f(0) on [0,1] and 0 outside;
- for every k>=41, the class-constraint left side is at most 0.9825010361292407.

For the last statement, g is continuous because f(0)=f(1). Its distributional
second derivative has total mass variation at most integral |f''| plus the
absolute endpoint slopes. A lattice with spacing d can be partitioned into
cells centered at its sample points. Taylor's integral remainder, subtracting
the linear term whose integral over a centered cell is zero, bounds the error
on a cell by d^2/8 times the variation of g' within that cell. Summing gives

    |d*sum_{j in Z} g(a+j*d)-integral g| <= d^2*TV(g')/8.

All nonzero lattice samples of g are among the k listed points. At the closed
domain boundary, an extra sample at 0 or 1 has g=0 and changes no sum. The class
domain implies |k*d-1|<=d. Therefore

    d*sum_{j=0}^{k-1}f(a+j*d)
      <= I + |f(0)|*d + d^2*TV(g')/8.

For k>=41, d<=1/(k-1)<=1/40. Substituting the exact rational bounds proves the
reported tail upper bound, strictly below 1.

Finally, the ordinary composite midpoint remainder gives

    S_n(f) >= I - sup|f''|/(24*n^2).

The exact right side exceeds 49/50 for every n>=225. Independently calculated
exact power sums prove S_n(f)>49/50 for n=2,...,240, overlapping the analytic
range. The implementation cross-checks the power-sum formula against direct
rational evaluation for n<12. Thus the finite-n objective is above 0.98 for
every n>=2. Combined with all 78 short-class inequalities and the tail bound,
this completes the computer-assisted lower-bound argument.

## Stronger uniform lower bound, independently verified

The root stream strengthened the finite-n objective to S_n(f)>I for every
integer n>=2 using an exact Euler–Maclaurin polynomial. To avoid relying on
the same formula or polynomial-conversion implementation, the independent
checker `myerson_independent_uniform.py` uses a separate argument.

Let z_i=(2i-1-n)/n and t=1/n^2, and write

    M_(2r)(t)=(1/n)*sum_{i=1}^n z_i^(2r).

The binomial difference sum

    sum_i [(z_i+1/n)^(2r+1) - (z_i-1/n)^(2r+1)] = 2

telescopes exactly. Therefore M_0=1 and

    M_(2r)(t) = [1 - sum_{ell=1}^r binom(2r+1,2ell+1)
                      *t^ell*M_(2r-2ell)(t)]/(2r+1).

This determines each centered moment as a rational polynomial in t for every
positive integer n, without an asymptotic remainder. An explicit factorial
formula for Chebyshev coefficients independently reconstructs F(z), avoiding
the earlier recurrence used to build f(x). Combining the centered moments
gives S_n(f)-I = t*P(t), with degree-9 P.

The independently derived coefficients of P agree identically with the root
stream's Euler–Maclaurin coefficients. Exact Bernstein conversion proves
P(t)>0 on all 16 equal subintervals of [0,1/16]. This covers every integer n>=4.
Direct rational evaluation gives S_2(f)>I and S_3(f)>I. Direct identity checks
also pass at n=4,5,11,47,123,241,997, but the polynomial identity and interval
coverage, rather than these finite checks, establish the universal conclusion.

Consequently every allowed cover has

    h >= S_n(f) > I = 1891871140656049/1929687500000000 > 49/50.

This stronger statement does not require the modulus-distinctness condition.
All other original requirements, especially exact partition and at least two
members per class, remain essential.

## Reproduction

    python lineage/myerson_independent_bounds.py \
      scout/revised_polynomial.json \
      lineage/myerson_revised_independent_bounds.json

    python lineage/myerson_independent_bivariate.py

    python lineage/myerson_independent_uniform.py

The decimal fields are presentation only; the exact rational fields are the
certificate. This is a computer-assisted rational calculation with independently
reviewed analytic reductions, not a Lean or other proof-assistant formalization.
