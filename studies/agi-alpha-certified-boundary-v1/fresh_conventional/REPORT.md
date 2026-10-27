# Fresh conventional challenge: exact negative answer

Started 2026-10-27 22:19:09 UTC; final exact certificate completed at 22:23:45 UTC.

## Result

The certificate in `verify_weight.py` and the argument below prove that every partition of `[1,n]` into complete restricted residue classes, each containing at least two interval elements, satisfies

    h >= 1963/2003 = 0.980029955067... > 49/50.

The gap is exactly 3/100150. Distinct moduli are not needed. Thus the requested cover with h<0.98 cannot exist. This is a proposed computer-assisted proof; independent mathematical and code review should precede any public priority claim.

## Exact proof

Let W be continuous, piecewise linear, zero outside [0,1], with knots r/20 and the following values for r=0,...,10:

    0,159,316,493,721,981,1240,1500,1658,1818,1858.

Reflect about 1/2 to obtain the remaining ten values. Its integral is I=1963/2. The total variation V of the derivative of the zero extension, including the two endpoint jumps, is 21200.

Claim: for every complete progression a,a+d,...,a+(k-1)d in [0,1] with k>=2,

    d * sum_l W(a+l*d) <= T = 2003/2.

Completeness is expressed by 0<=a<=d and a+(k-1)d<=1<=a+kd. Allowing equality enlarges the domain and is harmless. In particular 1/(k+1)<=d<=1/(k-1).

For fixed 2<=k<=20, these inequalities define a compact polygon in (a,d). Subdivide it by every line a+j*d=r/20, for 0<=j<k and 0<=r<=20. Within each cell the sum W has the form A*a+B*d+C, so its product with d is affine in a for fixed d>0. A maximum can therefore be moved to the boundary of its cell without decreasing the objective. It suffices to maximize on every subdivision line and every original polygon edge. The edges a=0 and a+(k-1)d=1 already are subdivision lines. The verifier explicitly includes the other two edges a=d and a+kd=1.

On a line a+j*d=r/20, all other crossings occur at d=(s-r)/(20*(l-j)). Between consecutive crossings the objective is A*d^2+B*d with integer coefficients. Its maximum occurs at an endpoint or at -B/(2*A) when A<0 and that point is in the segment. `verify_weight.py` enumerates all these possibilities with exact Fraction arithmetic. It checks 1,967 segments and obtains global maximum 18258529/18240 = 1001.015844... < 2003/2. The maximizing cardinality is k=2. All per-k exact values are in `verify_weight.log` and `weight_certificate.json`.

For k>=21, use the composite trapezoid estimate on any lattice of spacing d:

    | d*sum_{z in Z} W(a+z*d) - integral W | <= V*d^2/8.

Proof of the estimate: on a lattice cell [u,u+d], the trapezoid error is the integral of (x-u)*(u+d-x)/2 against the derivative-jump measure of W. The kernel is bounded in absolute value by d^2/8. Sum over cells and use the total variation V of the jump measure. Compact support makes the sum finite. Since the progression is complete, it includes every nonzero lattice contribution. Since d<=1/20, its objective is at most

    1963/2 + 21200/(8*20^2) = 7905/8 = 988.125 < T.

This proves the progression inequality for every k>=2.

### Exact transfer to every integer interval length

For an arbitrary integer cover, assign to each j=1,...,n the cell weight

    w_j = integral from (j-1)/n to j/n of W(x) dx.

For a complete restricted class C of modulus m and any 0<t<1, its points x_j(t)=(j-1+t)/n form a complete progression in (0,1) with spacing d=m/n and at least two members. The predecessor integer is at most zero, hence its coordinate is at most (-1+t)/n<0. The successor integer is at least n+1, hence its coordinate is at least 1+t/n>1. Therefore the progression inequality applies. Integrating it over t from 0 to 1 gives

    (m/n) * sum_{j in C} integral_0^1 W((j-1+t)/n)dt
       = m * sum_{j in C} w_j <= T.

Sum over classes. Since they partition the integers, the cells partition [0,1], so

    I = sum_j w_j <= T * sum_C 1/m_C.

Thus h>=I/T=1963/2003. There is no limit, finite-grid approximation, midpoint error, or small-n exception.

## Initial information and independence

Initial mathematical information consisted only of the exact low-heft question at https://mathoverflow.net/a/499017 and the two primary references DOI10.1016/j.disc.2009.02.002 and DOI10.25949/19441907. The budget was ten wall minutes and 300 CPU seconds of deliberate numerical search. I read no other agent's files or shared mathematical hints. All work was confined to this new directory except installed libraries and environment metadata. No people were contacted. The coordinator later asked me to check the continuous-to-discrete passage; I had independently developed the cell-average transfer before that reminder.

## Sources and software actually used

* Myerson's public MathOverflow answer, retrieved 27 October 2026.
* Emanuel's 2011 thesis, public file https://ndownloader.figshare.com/files/34541747, DOIhttps://doi.org/10.25949/19441907. I inspected Chapter2's heft bounds, AppendixC (prior universal lower bound sqrt(8)-2), AppendixA's small-length tables (minimum about0.987289 at length45), and searched relevant terms.
* The 2009 paper's official abstract/metadata and indexed excerpt at https://files01.core.ac.uk/download/195642612.pdf. I did not read its complete text.
* Python3.12, NumPy and SciPy1.17.0/HiGHS. highspy, ortools, pulp and sympy were unavailable. The final checker needs only Python's standard library.

## Search and timings

The initial binary MILP used one variable for each complete restricted residue class containing at least two points, exact-one constraints on interval points, at-most-one constraints for each modulus, and reciprocal-modulus objective. Every returned witness was checked with exact cover counts and rational heft.

| Command | Recorded CPU seconds | Outcome |
|---|---:|---|
| python search.py 50:20 75:40 100:50 | 97.3984 | n50 reported optimum0.9880205312; time-limited n75 incumbent0.9872537710; n100 incumbent0.9899370718 |
| python relax.py | 32.1605 | Distinct-modulus LP minima near0.9863 through n200; n300,n500 each hit12-second limit |
| python dual.py | 3.9698 | Dropping distinct-modulus constraints gives0.9824675325 at n100,n200, suggesting the weight approach |
| python polynomial.py | CPU unrecorded; wall<6 seconds | Aborted inefficient unvectorized setup before an LP result |
| python tent_dual.py | 11.4859 | Sampled continuum LPs with20,40,80 intervals; the20-interval candidate was rounded to the exact integer certificate |
| python verify_weight.py | 0.3231 | Final exact verification passed |

Preliminary exact checks used less than one further CPU second. Recorded deliberate computation is about145.9 CPU seconds, plus the interrupted setup (less than six wall seconds) and small startup costs: comfortably under300 seconds. Exact CPU for the aborted command was not captured, and is not invented here.

## Failed approaches and corrections

* Initial working directory did not exist; created it without inspecting the shared workspace.
* Sandboxed urllib download failed; authorized read-only public download succeeded with escalation.
* /usr/bin/time was unavailable; an invocation returned127 before Python ran. Actual runs use process_time and monotonic.
* polynomial.py was interrupted before results. Its mtime is22:21:48.223834 UTC; interruption completed before22:21:53 UTC.
* Initial scale T=1001 failed because18258529/18240>1001. Scale2003/2 succeeds and retains a ratio above0.98.
* The first checker did not explicitly include a=d and a+kd=1. Both edges were then added and the complete checker passed. `verify_weight_v1.py` preserves that earlier checker (already with successful scale).
* A full-report write was blocked by a sandbox startup 'No space left on device' error. This smaller report was attempted with apply_patch instead. No other work was deleted.

## Reproduction and limitations

Run `python verify_weight.py`. It prints exact per-cardinality maxima and writes `weight_certificate.json`. No solver, network, downloaded thesis, or floating-point decision is needed. Decimal values in output are descriptive only; all checks use exact integers and fractions. The MILP's numerical optimality status is not used in the proof. The conclusion depends on the stated cell-boundary argument, exact checker, trapezoid inequality, and cell-average transfer.

This was an exploratory targeted-discovery comparator, not a preregistered evaluation. It does not establish a general capability ranking.
