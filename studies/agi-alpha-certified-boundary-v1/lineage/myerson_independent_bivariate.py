"""Independent exact checker for every short-class polynomial inequality.

Rebuilds each summand by generic sparse bivariate Horner multiplication (no
moment shortcut), uses factorial Bernstein conversion, and uses explicit
binomial midpoint subdivision formulas. No imports from scout's checker.
"""
import json
import math
import hashlib
import time
from fractions import Fraction as Q
from pathlib import Path
from myerson_independent_bounds import polynomial

ROOT = Path(__file__).resolve().parents[1]
NS, NV = 21, 20


def multiply_sparse(a, b):
    c = {}
    for (i,j), x in a.items():
        for (r,s), y in b.items():
            key = i+r,j+s
            c[key] = c.get(key,0)+x*y
    return {key:value for key,value in c.items() if value}


def direct_polynomial(k, upper, coeffs, denominator):
    b = k-1 if upper else k+1
    rr = k*b
    constant = b if upper else k
    total = {}
    for j in range(k):
        t = 2*j-k+1
        z = {(0,0):t*constant,(1,0):t,(1,1):-b if upper else b}
        if upper:
            z[0,1] = b
        z = {key:value for key,value in z.items() if value}
        term = {(0,0):coeffs[20]}
        for power in range(19,-1,-1):
            term = multiply_sparse(term,z)
            term[0,0] = term.get((0,0),0)+coeffs[power]*rr**(20-power)
        for key,value in term.items():
            total[key] = total.get(key,0)+value
    total = multiply_sparse(total,{(0,0):constant,(1,0):1})
    result = {key:-value for key,value in total.items()}
    result[0,0] = result.get((0,0),0)+denominator*rr**21
    assert all(i<=NS and j<=NV for i,j in result)
    return result,denominator*rr**21


def factorial_weights(n):
    # n!*binom(i,j)/binom(n,j) = i!*(n-j)!/(i-j)!
    return [[math.factorial(i)*math.factorial(n-j)//math.factorial(i-j)
             if j<=i else 0 for j in range(n+1)] for i in range(n+1)]


WS, WV = factorial_weights(NS),factorial_weights(NV)


def to_bernstein(poly):
    first = [[sum(WS[i][p]*poly.get((p,q),0) for p in range(i+1))
              for q in range(NV+1)] for i in range(NS+1)]
    return [[sum(WV[j][q]*first[i][q] for q in range(j+1))
             for j in range(NV+1)] for i in range(NS+1)]


def split_curve(curve):
    n = len(curve)-1
    left = [(sum(math.comb(i,j)*curve[j] for j in range(i+1)) << (n-i))
            for i in range(n+1)]
    right = [(sum(math.comb(n-i,j-i)*curve[j] for j in range(i,n+1)) << i)
             for i in range(n+1)]
    return left,right


def subdivide(grid, axis):
    if axis==0:
        columns = list(zip(*grid))
        pairs = [split_curve(column) for column in columns]
        return [list(row) for row in zip(*(p[0] for p in pairs))], \
               [list(row) for row in zip(*(p[1] for p in pairs))]
    pairs = [split_curve(row) for row in grid]
    return [p[0] for p in pairs],[p[1] for p in pairs]


def certify(grid, denominator):
    stack = [(grid,denominator,0,Q(0),Q(1),Q(0),Q(1))]
    nodes = 0
    leaves = []
    while stack:
        g,den,depth,s0,s1,v0,v1 = stack.pop()
        nodes += 1
        low,high = min(map(min,g)),max(map(max,g))
        if low>=0:
            leaves.append({'s':[str(s0),str(s1)],'v':[str(v0),str(v1)],
                           'lower_bound':str(Q(low,den)),'depth':depth})
            continue
        assert high>=0, 'Entire box violates constraint'
        assert depth<18 and nodes<20000, 'Certificate resource limit exceeded'
        # Deliberately reverse the other checker's initial split axis.
        axis = 1-depth%2
        left,right = subdivide(g,axis)
        next_den = den * 2**(NS if axis==0 else NV)
        if axis==0:
            mid=(s0+s1)/2
            stack.extend([(left,next_den,depth+1,s0,mid,v0,v1),
                          (right,next_den,depth+1,mid,s1,v0,v1)])
        else:
            mid=(v0+v1)/2
            stack.extend([(left,next_den,depth+1,s0,s1,v0,mid),
                          (right,next_den,depth+1,s0,s1,mid,v1)])
    assert sum((Q(leaf['s'][1])-Q(leaf['s'][0]))*
               (Q(leaf['v'][1])-Q(leaf['v'][0])) for leaf in leaves) == 1
    return {'nodes':nodes,'leaves':leaves,'max_depth':max(x['depth'] for x in leaves)}


def run():
    path = ROOT/'scout/revised_polynomial.json'
    raw = path.read_bytes()
    obj = json.loads(raw)
    p = polynomial(list(map(Q,obj['coefficients'])))
    # Reconstruct F(z)=f((z+1)/2), independently of the other checker's
    # direct T_j(z) recurrence and its symmetric moment expansion.
    zco = [sum((p[i]*Q(math.comb(i,j),2**i) for i in range(j,len(p))),Q(0))
           for j in range(len(p))]
    assert all(zco[i]==0 for i in range(1,21,2))
    den = math.lcm(*(x.denominator for x in zco))
    integers = [int(x*den) for x in zco]
    results = []
    start = time.monotonic()
    for k in range(2,41):
        for upper in [False,True]:
            poly,d = direct_polynomial(k,upper,integers,den)
            grid = to_bernstein(poly)
            answer = certify(grid,d*math.factorial(NS)*math.factorial(NV))
            answer.update(k=k,patch='upper' if upper else 'lower',passed=True)
            results.append(answer)
    report = {'status':'PASS: all 78 bivariate patches independently certified',
              'witness_sha256':hashlib.sha256(raw).hexdigest(),
              'method':'exact rational/integer sparse Horner, factorial Bernstein, binomial subdivision',
              'elapsed_seconds':time.monotonic()-start,
              'patches':results}
    (ROOT/'lineage/myerson_independent_bivariate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'])
    print('Seconds',report['elapsed_seconds'])
    print('Total leaves',sum(len(r['leaves']) for r in results),'maximum depth',max(r['max_depth'] for r in results))


if __name__=='__main__':
    run()
