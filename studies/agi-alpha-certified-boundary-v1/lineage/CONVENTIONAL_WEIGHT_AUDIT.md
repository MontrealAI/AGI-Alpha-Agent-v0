# Independent audit of the stronger conventional construction

## Accepted mathematical result

The conventional workstream's piecewise-linear weight, after normalization by
its exact verified maximum, proves

    h >= 17902560/18258529 = approximately 0.9805039606421744 > 49/50.

This is stronger than the earlier degree-20 polynomial result
1891871140656049/1929687500000000, approximately 0.9804028583156853. The earlier
proof remains valid. Its constant must not be described as superior after this
comparison, and neither construction establishes an exclusive AI capability,
controlled discovery advantage, operational Alpha, or commercial demand.

The original conventional checker used the convenient safe scale 2003/2,
which yields 1963/2003, approximately 0.9800299551. Its own exact calculation
already established the smaller maximum 18258529/18240. Dividing by this
verified maximum instead is a straightforward exact normalization; no search,
new knot values, or relaxed customer requirement is needed. Reporting only
the looser scale would understate the strongest conventional challenge.

## Frozen mathematical object

Let W be the continuous linear interpolant at knots j/20, j=0,...,20, with
heights

    0,159,316,493,721,981,1240,1500,1658,1818,1858,
    1818,1658,1500,1240,981,721,493,316,159,0.

Its integral is 1963/2. The total variation of the derivative of its zero
extension, including the jumps at 0 and 1, is 21200. All values and bounds
are exact rationals or integers.

## Why the finite maximum enumeration is complete

For a class of length k, write its normalized sample points as a+j*d,
j=0,...,k-1. The domain is the quadrilateral with vertices (a,d)

    (1/(k+1),1/(k+1)), (1/k,1/k),
    (0,1/(k-1)), (0,1/k).

Equivalently, 0<=a<=d and a+(k-1)*d<=1<=a+k*d. Knot-crossing lines
a+j*d=r/20 partition this quadrilateral into convex polygonal cells.
Within each cell, each W(a+j*d) is affine, so

    S(a,d)=d*sum_j W(a+j*d)=A*a*d+B*d^2+C*d.

If A is nonzero, the Hessian determinant is -A^2<0, so no interior local
maximum exists. If A is zero, S is independent of a; a maximizing horizontal
section meets the boundary with the same value. Thus a global maximum always
occurs on a cell boundary. This argument covers stationary ridges as well as
ordinary critical points; interior stationary cases are not omitted.

Every cell boundary is either a sample-knot line or a boundary of the original
domain. The sample lines j=0,r=0 and j=k-1,r=20 cover a=0 and the last-point
boundary. The additional lines j=-1,r=0 and j=k,r=20 cover a=d and the
next-point boundary. All four outer boundaries are therefore included.

On each boundary segment between consecutive knot intersections, S is a
quadratic in d. Its maximum is at an endpoint or, if it is concave, at its
interior stationary point. All these candidates are checked with exact rational
arithmetic. Degenerate point segments are also evaluated.

## Independent implementation and result

The original checker `fresh_conventional/verify_weight.py` was executed in a
disposable directory, preserving its original files and outputs. A separate
implementation, `lineage/audit_conventional_weight.py`, reconstructs the
geometry through polygon-edge intersections instead of the original
inequality-clipping formulas. It evaluates W directly at segment endpoints,
fits each quadratic from those exact values, checks the midpoint identity,
and evaluates interior stationary points directly.

For every k=2,...,20, both computations give a maximum no greater than

    M=18258529/18240 = approximately 1001.0158442982456.

This maximum occurs for k=2, a=7/20, d=4273/9120. The independent computation
took approximately 0.916 seconds in the recorded run. Timing does not establish
a model performance advantage.

For k>=21, d<=1/20. The centered-cell quadrature bound for the zero-extended W
gives

    d*sum W(a+j*d) <= integral(W)+d^2*TV(W')/8
                      <= 1963/2+21200/(8*20^2)
                       =7905/8 < M.

Thus M bounds every class length, with no numerical cutoff in the theorem.

## Exact passage to every finite interval length

For any interval of length n, define cell-average weights

    w_i=integral from (i-1)/n to i/n of W(x) dx.

For a complete residue class C modulo m, containing k>=2 interval points,
put d=m/n and sample x_i(t)=(i-1+t)/n, t in [0,1]. For every t these k
sample points lie in the class domain, so

    (m/n)*sum_{i in C}W(x_i(t)) <= M.

Integrating over t gives m*sum_{i in C}w_i<=M. Summing over the exact partition
therefore yields

    h=sum_C 1/m >= (sum_i w_i)/M = integral(W)/M
                                =17902560/18258529.

This proof works for every n>=2 directly; it does not use an asymptotic midpoint
approximation. Distinct moduli are unnecessary for the proof. The original
one-dimensional exact-partition and at-least-two-hits requirements are retained.

## Evidence and limits

Run `python lineage/audit_conventional_weight.py` from the package root, choosing
a fresh output destination in the script if its preserved audit directory
already exists. Evidence is in
`confirmation/conventional_independent/INDEPENDENT_WEIGHT_AUDIT.json`, alongside
the original checker's independent rerun output. This is a same-session exact
computer-assisted audit, not external peer review or a proof-assistant proof.
The conventional workstream's discovery conditions and budget are recorded by
the parent; this audit does not infer a controlled initial-information comparison.
