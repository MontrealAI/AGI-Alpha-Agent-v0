"""Independent exact proof that every midpoint average exceeds the integral.

No Euler-Maclaurin formula, Bernoulli numbers, or imports of either existing
checker are used. Centered moments follow from a telescoping binomial identity.
"""
import json
import math
import hashlib
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def evaluate(coefficients, x):
    value = Q(0)
    for c in reversed(coefficients):
        value = value*x+c
    return value


def make_centered_polynomial(cs):
    # Explicit T_n coefficient formula, not the recurrence used in other checkers.
    out = [Q(0)]*21
    out[0] = cs[0]
    for j in range(1,len(cs)):
        n=2*j
        for k in range(j+1):
            degree=n-2*k
            coefficient=Q(j*(-1)**k*math.factorial(n-k-1)*2**degree,
                          math.factorial(k)*math.factorial(degree))
            out[degree] += cs[j]*coefficient
    return out


def centered_even_moments(max_r):
    # z_i=(2i-1-n)/n. Summing (z_i+1/n)^(2r+1)-(z_i-1/n)^(2r+1)
    # telescopes to 2; hence 1=sum_l binom(2r+1,2l+1)*t^l*M_{2(r-l)}.
    # This recurrence is a polynomial identity valid for every positive n.
    moments=[[Q(1)]]
    for r in range(1,max_r+1):
        polynomial=[Q(1)]+[Q(0)]*r
        for ell in range(1,r+1):
            factor=math.comb(2*r+1,2*ell+1)
            for j,c in enumerate(moments[r-ell]):
                polynomial[j+ell] -= factor*c
        moments.append([c/(2*r+1) for c in polynomial])
    return moments


def bernstein_interval(poly, left, right):
    degree=len(poly)-1
    # Direct expansion p(left+(right-left)*t), then factorial identity for
    # monomial-to-Bernstein conversion, all exact rationals.
    local=[sum((poly[j]*math.comb(j,i)*left**(j-i)*(right-left)**i
                for j in range(i,degree+1)),Q(0)) for i in range(degree+1)]
    return [sum((local[j]*Q(math.factorial(i)*math.factorial(degree-j),
                            math.factorial(i-j)*math.factorial(degree))
                 for j in range(i+1)),Q(0)) for i in range(degree+1)]


def run():
    witness_path=ROOT/'scout/revised_polynomial.json'
    raw=witness_path.read_bytes()
    cs=list(map(Q,json.loads(raw)['coefficients']))
    centered=make_centered_polynomial(cs)
    moments=centered_even_moments(10)
    average=[Q(0)]*11
    for r in range(11):
        for j,c in enumerate(moments[r]):
            average[j]+=centered[2*r]*c
    integral=sum((centered[2*r]/(2*r+1) for r in range(11)),Q(0))
    assert average[0]==integral
    assert integral==sum((c/Q(1-4*j*j) for j,c in enumerate(cs)),Q(0))
    quotient=average[1:]
    root_result=json.loads((ROOT/'study/midpoint_uniform_result.json').read_text())
    assert quotient==list(map(Q,root_result['coefficients_Qn_minus_I_div_t']))
    # Exact checking on 16 equal intervals covers the entire continuous
    # domain 0<=t<=1/16. There is no floating point acceptance condition.
    leaves=[]
    for j in range(16):
        lo,hi=Q(j,256),Q(j+1,256)
        coefficients=bernstein_interval(quotient,lo,hi)
        lower=min(coefficients)
        assert lower>0
        leaves.append({'lo':str(lo),'hi':str(hi),'strict_lower_bound':str(lower)})
    checks=[]
    for n in [2,3,4,5,11,47,123,241,997]:
        direct=sum((evaluate(centered,Q(2*i-1-n,n)) for i in range(1,n+1)),Q(0))/n
        via_moments=evaluate(average,Q(1,n*n))
        assert direct==via_moments
        assert direct>integral
        checks.append({'n':n,'difference_from_integral':str(direct-integral)})
    out={'status':'PASS: S_n(f)>I for every integer n>=2',
         'independent_method':'telescoping centered-moment recurrence and 16 exact Bernstein intervals',
         'witness_sha256':hashlib.sha256(raw).hexdigest(),
         'integral':str(integral),'integral_approx':float(integral),
         'moment_polynomials':[[str(c) for c in p] for p in moments],
         'quotient_coefficients':[str(c) for c in quotient],
         'agrees_identically_with_root_euler_maclaurin_coefficients':True,
         'positive_intervals':leaves,'direct_identity_checks':checks}
    (ROOT/'lineage/myerson_independent_uniform.json').write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'])
    print('Integral',str(integral),float(integral))
    print('Identity independently derived; all 16 continuous intervals positive; small n=2,3 positive.')


if __name__=='__main__':
    run()
