# Appendix A. A universal piecewise-linear weight certificate

## A.1 Statement and exact coefficients

Let finitely many complete residue classes, restricted to the integers $1,\ldots,n$, partition that interval. Suppose each restriction contains at least two integers. If their moduli are $m_1,\ldots,m_r$, then

$$
\boxed{\displaystyle h=\sum_{i=1}^r\frac1{m_i}
\ge J:=\frac{17902560}{18258529}
=0.9805039606421744\ldots>\frac{49}{50}.}
$$

The proof permits repeated moduli and therefore answers the original distinct-modulus question. It retains complete restrictions, exact partitioning and the minimum of two interval elements per class. No optimality assertion accompanies the constant $J$.

Define $W$ as the continuous linear interpolant at the knots $j/20$, for $0\le j\le20$, with $W(1-x)=W(x)$ and the following integer coefficients. Extend $W$ by zero outside $[0,1]$.

| $j$ | $W(j/20)$ |
|--:|--:|
| 0 | 0 |
| 1 | 159 |
| 2 | 316 |
| 3 | 493 |
| 4 | 721 |
| 5 | 981 |
| 6 | 1240 |
| 7 | 1500 |
| 8 | 1658 |
| 9 | 1818 |
| 10 | 1858 |

Reflection supplies the remaining ten coefficients. Exact trapezoid integration and summation of derivative jumps give

$$
I_W:=\int_0^1W(x)\,dx=\frac{1963}{2},
\qquad V:=\operatorname{TV}(W')=21200.
$$

Here $W'$ denotes the derivative of the zero extension. Its variation includes the jumps from zero derivative at both support endpoints. The normalization used below is

$$M=\frac{18258529}{18240},\qquad J=\frac{I_W}{M}.$$

## A.2 The complete progression domain

For $k\ge2$, consider the sum

$$S_k(a,d)=d\sum_{\ell=0}^{k-1}W(a+\ell d),\qquad d>0.$$

The closed domain

$$
D_k=\{(a,d):0\le a\le d,\quad a+(k-1)d\le1\le a+kd\}
$$

contains every complete $k$-point progression in the open unit interval. The inequalities allow its predecessor or successor to lie at an endpoint; this enlargement is harmless because $W(0)=W(1)=0$. In particular,

$$\frac1{k+1}\le d\le\frac1{k-1}.$$

The domain is the compact quadrilateral with consecutive vertices

$$
\left(\frac1{k+1},\frac1{k+1}\right),\quad
\left(\frac1k,\frac1k\right),\quad
\left(0,\frac1{k-1}\right),\quad
\left(0,\frac1k\right).
$$

We prove $S_k\le M$ throughout $D_k$ for every $k\ge2$.

## A.3 Exact maximization for short progressions

For each $2\le k\le20$, subdivide $D_k$ by all knot-crossing lines

$$a+jd=\frac r{20},\qquad 0\le j<k,\quad 0\le r\le20.$$

On each resulting polygonal cell, the arguments of $W$ stay in fixed linear pieces. Consequently

$$S_k(a,d)=Aad+Bd^2+Cd$$

for constant rational coefficients. If $A\ne0$, its Hessian has determinant $-A^2<0$, excluding an interior local maximum. Equivalently, its derivative in $a$ is the nonzero quantity $Ad$. If $A=0$, the objective is independent of $a$: a maximizing section at fixed $d$ reaches the cell boundary with the same value. Degenerate cells already belong to boundaries. Thus a global maximum occurs on an enumerated boundary, including possible stationary ridges.

Every boundary is a knot-crossing line or one of the four edges of $D_k$. The lines with $(j,r)=(0,0)$ and $(k-1,20)$ cover $a=0$ and $a+(k-1)d=1$. The remaining edges are included explicitly as $(j,r)=(-1,0)$ and $(k,20)$, representing $a=d$ and $a+kd=1$.

On a fixed line $a+jd=r/20$, every crossing with another knot line occurs at

$$d=\frac{s-r}{20(\ell-j)},\qquad \ell\ne j.$$

The domain endpoints and these crossings divide the line into finitely many rational segments. On each, $S_k=\alpha d^2+\beta d$. Its maximum occurs at an endpoint or, when $\alpha<0$, at the stationary point $-\beta/(2\alpha)$ if that point belongs to the segment. Degenerate point segments are also evaluated.

The standard-library checker `fresh_conventional/verify_weight.py` implements this enumeration using exact integers and fractions. All nineteen cardinalities pass, and their largest value is precisely

$$M=\frac{18258529}{18240},$$

attained at $k=2$, $a=7/20$ and $d=4273/9120$. The original enumeration checks 1,967 segments, including point cases and repeated descriptions.

The independent checker `lineage/audit_conventional_weight.py` reconstructs line segments by intersecting polygon edges, rather than by the first checker's inequality-clipping formulas. It interpolates $W$ directly, reconstructs each quadratic from exact endpoint values, checks its midpoint identity and evaluates stationary points directly. It reproduces every per-cardinality maximum. Its different bookkeeping gives 1,863 positive-length segments and 360 interior stationary evaluations, with degenerate points checked separately. The audit receipt is `confirmation/conventional_independent/INDEPENDENT_WEIGHT_AUDIT.json`. These are separate implementations within one study, not external peer review or proof-assistant verification.

## A.4 An analytic bound for all remaining cardinalities

For a continuous compactly supported piecewise-linear function, the composite trapezoid estimate on a lattice of spacing $d$ is

$$
\left|d\sum_{z\in\mathbb Z}W(a+zd)-\int_{\mathbb R}W(x)\,dx\right|
\le\frac{d^2}{8}\operatorname{TV}(W').
$$

Indeed, on a lattice cell $[u,u+d]$, the trapezoid error is the integral of $(x-u)(u+d-x)/2$ against the signed measure of derivative jumps. This kernel has magnitude at most $d^2/8$. Summing over cells and using the measure's total variation proves the estimate. Endpoint jumps of the zero extension are included, so cells crossing the support boundary require no exception.

For $(a,d)\in D_k$, the listed progression contains every nonzero contribution of the lattice. When $k\ge21$, the bound $d\le1/20$ therefore gives

$$
S_k(a,d)\le\frac{1963}{2}+\frac{21200}{8\cdot20^2}
=\frac{7905}{8}<M.
$$

Together with the finite exact computation, this proves $S_k\le M$ for every admissible progression, without a cardinality cutoff.

## A.5 Exact transfer to every integer interval

For an arbitrary partition of $\{1,\ldots,n\}$, define cell-integral weights

$$w_j=\int_{(j-1)/n}^{j/n}W(x)\,dx.$$

Consider a complete restricted residue class $C$ modulo $m$. For each $0<t<1$, its points

$$x_j(t)=\frac{j-1+t}{n},\qquad j\in C,$$

form a progression of spacing $d=m/n$ with at least two members. Its predecessor integer is at most zero, so its normalized predecessor is at most $(-1+t)/n<0$. Its successor integer is at least $n+1$, so its normalized successor is at least $1+t/n>1$. The progression thus belongs to $D_{|C|}$.

Integrating its certified inequality in $t$ yields

$$
\frac mn\sum_{j\in C}\int_0^1W\!\left(\frac{j-1+t}{n}\right)dt
=m\sum_{j\in C}w_j\le M.
$$

Sum over the partition. Every integer cell occurs once, giving $I_W\le Mh$ and hence $h\ge J$. This applies directly to every admissible $n$; no limiting argument, midpoint correction or unverified small-length case remains. For $n=1$ the hypotheses are impossible.

## A.6 Normalization and contribution

The discovery report used the convenient safe scale $T=2003/2$, obtaining $h\ge1963/2003>0.98$. Its computation already established the smaller exact maximum $M$. Normalizing by $M$ gives the stronger bound $J$ without changing the knots, domain or proof obligations. The theorem states $h\ge J$; it does not assert strictness at $J$.

Discovery used standard linear and mixed-integer optimization, followed by exact rational geometry and a classical quadrature estimate. The contribution is the explicit certificate and resulting universal bound. It establishes neither a new general solver nor an exclusive AI capability or controlled discovery advantage.
