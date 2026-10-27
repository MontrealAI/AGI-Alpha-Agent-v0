"""Independent exact rational audit of the polynomial witness's 1D bounds.

This verifies only analytic tail and finite-n objective conditions. It does NOT
certify the 2D class inequalities; those are deliberately a separate obligation.
Only Python's standard library is used. Decimals in the input are exact rationals.
"""
import json
import math
import sys
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def add(p, q):
    return [(p[i] if i < len(p) else Q(0)) +
            (q[i] if i < len(q) else Q(0)) for i in range(max(len(p), len(q)))]


def mul_linear(p, a, b):
    out = [Q(0)] * (len(p) + 1)
    for i, v in enumerate(p):
        out[i] += a * v
        out[i+1] += b * v
    return out


def polynomial(c):
    t0, t1 = [Q(1)], [Q(-1), Q(2)]
    p = [c[0]]
    for k in range(2, 2 * len(c) - 1):
        t2 = add(mul_linear(t1, Q(-2), Q(4)), [-a for a in t0])
        if k % 2 == 0:
            p = add(p, [c[k//2] * a for a in t2])
        t0, t1 = t1, t2
    return p


def value(p, x):
    out = Q(0)
    for a in p[::-1]:
        out = out*x + a
    return out


def derivative(p):
    return [i*p[i] for i in range(1, len(p))]


def bernstein(p, lo, hi):
    """Exact Bernstein coefficients of p(lo+(hi-lo)t), t in [0,1]."""
    n = len(p)-1
    powers = [(hi-lo)**i for i in range(n+1)]
    transformed = [powers[i] * sum((p[j] * math.comb(j, i) * lo**(j-i)
                   for j in range(i, n+1)), Q(0)) for i in range(n+1)]
    return [sum((transformed[j]*Q(math.comb(i,j), math.comb(n,j))
                 for j in range(i+1)), Q(0)) for i in range(n+1)]


def record(q):
    return {'exact': str(q), 'decimal_approximation': float(q)}


def power_sums(n, degree):
    sums = [n]
    for j in range(1, degree+1):
        numerator = (n+1)**(j+1)-1-sum(math.comb(j+1,k)*sums[k] for k in range(j))
        assert numerator % (j+1) == 0
        sums.append(numerator//(j+1))
    return sums


def midpoint_objective(p, n):
    a, b = power_sums(2*n,len(p)-1), power_sums(n,len(p)-1)
    return sum((co*Q(a[j]-2**j*b[j],(2*n)**j*n) for j,co in enumerate(p)),Q(0))


def run():
    input_path = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'scout/polynomial_probe.json'
    output_path = Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'lineage/myerson_independent_bounds.json'
    witness = json.loads(input_path.read_text(), parse_float=Q)
    c = [Q(a) for a in witness.get('coefficients',witness.get('cheb_even_coefficients'))]
    p = polynomial(c)
    d1 = derivative(p)
    d2 = derivative(d1)
    integral = sum((a/Q(i+1) for i,a in enumerate(p)), Q(0))
    # Independent identity check against the Chebyshev integral formula.
    assert integral == sum((co/Q(1-(2*j)**2) for j,co in enumerate(c)), Q(0))
    assert value(p,Q(0)) == value(p,Q(1))
    for x in [Q(1,7),Q(2,9),Q(5,12)]:
        assert value(p,x) == value(p,1-x)
    segments = 64
    integral_abs_d2_bound = Q(0)
    sup_abs_d2_bound = Q(0)
    for i in range(segments):
        bs = bernstein(d2, Q(i,segments), Q(i+1,segments))
        integral_abs_d2_bound += sum(map(abs,bs),Q(0))/Q(segments*len(bs))
        sup_abs_d2_bound = max(sup_abs_d2_bound, max(map(abs,bs)))
    # g=f-f(0), zero outside [0,1], is continuous. Its derivative has jumps
    # f'(0) at 0 and -f'(1) at 1; add both absolute jumps to integral |f''|.
    variation = abs(value(d1,Q(0))) + integral_abs_d2_bound + abs(value(d1,Q(1)))
    tail = integral + abs(value(p,Q(0)))/40 + variation/Q(8*40*40)
    n0 = 2
    while integral-sup_abs_d2_bound/Q(24*n0*n0)<=Q(49,50):
        n0 += 1
        if n0>2000: raise ValueError('No bounded finite-n completion with this witness')
    mids = []
    for n in range(2,max(n0,241)):
        objective = midpoint_objective(p,n)
        if n<12:
            assert objective == sum((value(p,Q(2*i-1,2*n)) for i in range(1,n+1)),Q(0))/n
        mids.append((objective,n))
    out = {
      'status':'EXACT_PARTIAL_CERTIFICATE; bivariate inequalities not covered',
      'input':str(input_path),
      'input_coefficients_are_exact_decimal_rationals':True,
      'power_coefficients':[str(a) for a in p],
      'integral':record(integral),
      'endpoint_value':record(value(p,Q(0))),
      'endpoint_slope':record(value(d1,Q(0))),
      'second_derivative_sup_bound':record(sup_abs_d2_bound),
      'integral_abs_second_derivative_bound':record(integral_abs_d2_bound),
      'zero_extended_g_prime_variation_bound':record(variation),
      'tail_upper_bound_for_k_at_least_41':record(tail),
      'tail_passes_unscaled':tail <= 1,
      'n_at_least_midpoint_remainder_certifies_above_098':n0,
      'finite_n_objective_failures':[n for v,n in mids if v<=Q(49,50)],
      'smallest_midpoint_objectives':[
        {'n':n,'objective':record(v)} for v,n in sorted(mids)[:8]],
      'smallest_midpoint_objective_n_at_least_11':record(min(v for v,n in mids if n>=11)),
      'scales':{}
    }
    for scale in [Q(999,1000),Q(998,1000),Q(997,1000),Q(996,1000),Q(995,1000)]:
        gap = scale*integral-Q(49,50)
        if gap<=0:
            out['scales'][str(scale)] = {'status':'Integral itself is below target'}
            continue
        n0 = 2
        while scale*sup_abs_d2_bound/(24*n0*n0) >= gap:
            n0 += 1
        fails = [n for v,n in mids if scale*v <= Q(49,50)]
        out['scales'][str(scale)] = {
          'integral':record(scale*integral),
          'n_at_least_midpoint_remainder_certifies_above_098':n0,
          'finite_n_objective_failures_2_to_240':fails,
          'tail_passes':scale*tail<=1
        }
    output_path.write_text(json.dumps(out,indent=2)+'\n')
    for k in ['integral','second_derivative_sup_bound','zero_extended_g_prime_variation_bound',
              'tail_upper_bound_for_k_at_least_41','smallest_midpoint_objective_n_at_least_11',
              'n_at_least_midpoint_remainder_certifies_above_098','finite_n_objective_failures','scales']:
        print(k, out[k])


if __name__ == '__main__':
    run()
