"""Independent polygon-line audit of the conventional piecewise-linear proof.

Uses polygon-edge intersections and direct interpolation at segment endpoints,
not the challenger verifier's inequalities or accumulated slope formulas.
"""
from fractions import Fraction as Q
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
HEIGHTS=[0,159,316,493,721,981,1240,1500,1658,1818,1858,1818,1658,1500,1240,981,721,493,316,159,0]
H=20


def weight(x):
    assert 0<=x<=1
    left=min((x*H).numerator//(x*H).denominator,H-1)
    return HEIGHTS[left]+(x*H-left)*(HEIGHTS[left+1]-HEIGHTS[left])


def in_domain(a,d,k):
    return 0<=a<=d and a+(k-1)*d<=1<=a+k*d and d>0


def polygon(k):
    return [(Q(1,k+1),Q(1,k+1)),(Q(1,k),Q(1,k)),
            (Q(0),Q(1,k-1)),(Q(0),Q(1,k))]


def line_segment_in_polygon(j,c,vertices):
    points=set()
    for p,q in zip(vertices,vertices[1:]+vertices[:1]):
        lp=p[0]+j*p[1];lq=q[0]+j*q[1]
        if lp==lq:
            if lp==c: points.update([p,q])
        else:
            fraction=(c-lp)/(lq-lp)
            if 0<=fraction<=1:
                points.add((p[0]+fraction*(q[0]-p[0]),p[1]+fraction*(q[1]-p[1])))
    return sorted(points,key=lambda p:p[1])


def class_sum(k,j,c,d):
    a=c-j*d
    assert in_domain(a,d,k)
    return d*sum((weight(a+ell*d) for ell in range(k)),Q(0))


def audit_short_class(k):
    vertices=polygon(k)
    lines=[(j,Q(r,H)) for j in range(k) for r in range(H+1)]
    lines.extend([(-1,Q(0)),(k,Q(1))])
    maximum=Q(0);where=None;segments=0;stationary=0
    for j,c in lines:
        endpoints=line_segment_in_polygon(j,c,vertices)
        if not endpoints: continue
        lower,upper=endpoints[0][1],endpoints[-1][1]
        cuts={lower,upper}
        for ell,b in lines:
            if ell==j: continue
            d=(b-c)/(ell-j)
            if lower<d<upper and in_domain(c-j*d,d,k):cuts.add(d)
        cuts=sorted(cuts)
        if len(cuts)==1:
            value=class_sum(k,j,c,cuts[0])
            if value>maximum:maximum=value;where=[j,str(c),str(cuts[0]),'point']
            continue
        for lower,upper in zip(cuts,cuts[1:]):
            low=class_sum(k,j,c,lower)
            high=class_sum(k,j,c,upper)
            # class_sum/d is affine within the line-arrangement segment.
            a=(high/upper-low/lower)/(upper-lower)
            b=low/lower-a*lower
            middle=(lower+upper)/2
            assert class_sum(k,j,c,middle)==a*middle**2+b*middle
            candidates=[(low,lower,'endpoint'),(high,upper,'endpoint')]
            if a<0:
                critical=-b/(2*a)
                if lower<critical<upper:
                    value=class_sum(k,j,c,critical)
                    assert value==a*critical**2+b*critical
                    candidates.append((value,critical,'stationary'))
                    stationary+=1
            for value,d,kind in candidates:
                if value>maximum:maximum=value;where=[j,str(c),str(d),kind]
            segments+=1
    return {'k':k,'maximum':str(maximum),'maximum_approx':float(maximum),
            'maximizer':where,'segments':segments,'stationary_points_checked':stationary}


def run():
    destination=ROOT/'confirmation/conventional_independent'
    if destination.exists():raise ValueError('Preserve previous independent audit output')
    destination.mkdir(parents=True)
    source=ROOT/'fresh_conventional/verify_weight.py'
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='original_checker_',dir=destination) as temporary:
        checked=subprocess.run([sys.executable,str(source)],cwd=temporary,
                               capture_output=True,text=True,timeout=60)
        assert checked.returncode==0,checked.stderr
        original=json.loads((Path(temporary)/'weight_certificate.json').read_text())
        (destination/'original_checker_stdout.jsonl').write_text(checked.stdout)
        (destination/'original_checker_certificate.json').write_text(json.dumps(original,indent=2)+'\n')
    start=time.monotonic()
    classes=[audit_short_class(k) for k in range(2,21)]
    maximum=max(Q(result['maximum']) for result in classes)
    assert maximum==Q(original['maximum'])
    # Integral of each trapezoid and jumps of the derivative of the zero extension.
    integral=sum((Q(a+b,2*H) for a,b in zip(HEIGHTS,HEIGHTS[1:])),Q(0))
    slopes=[H*(b-a) for a,b in zip(HEIGHTS,HEIGHTS[1:])]
    variation=sum(abs(b-a) for a,b in zip([0]+slopes,slopes+[0]))
    tail=integral+Q(variation,8*20**2)
    assert integral==Q(1963,2) and variation==21200
    assert tail==Q(7905,8)<maximum
    bound=integral/maximum
    assert bound==Q(17902560,18258529)>Q(49,50)
    assert bound>Q(1891871140656049,1929687500000000)
    assert before==hashlib.sha256(source.read_bytes()).hexdigest()
    report={
      'status':'PASS independent boundary enumeration and analytic audit',
      'source_checker_sha256':before,'source_checker_reproduced':True,
      'independent_elapsed_seconds':time.monotonic()-start,
      'heights':HEIGHTS,'knots':'j/20 for j=0,...,20',
      'class_results':classes,'maximum':str(maximum),'maximum_approx':float(maximum),
      'integral':str(integral),'variation':variation,'tail_k_ge_21':str(tail),
      'stronger_normalization_bound':str(bound),'stronger_bound_approx':float(bound),
      'claim':'h >= 17902560/18258529 > 49/50 for every finite one-dimensional exact residue partition with at least two points per class.',
      'interior_maximum_argument':'On each arrangement cell S=A*a*d+B*d^2+C*d. If A is nonzero, Hessian determinant is negative; if A is zero, S is independent of a and a maximizing horizontal section meets the boundary. Thus checking every cell boundary is sufficient.',
      'boundary_coverage':'All sample-knot lines a+j*d=r/20 plus all four domain boundary lines are included. Domain edges a=d and a+k*d=1 are represented by j=-1,r=0 and j=k,r=20.',
      'cell_average_argument':'Set w_i=integral over [(i-1)/n,i/n] of W. Integrating (m/n)*sum W((i-1+t)/n)<=M over t in[0,1] gives m*sum w_i<=M. Summing over the exact partition yields h>=integral(W)/M for all n directly.',
      'qualifications':'Exact computer-assisted certificate; same-session independent review; no external peer review or model advantage established. The conventional construction exceeds the earlier polynomial constant after exact normalization.'
    }
    (destination/'INDEPENDENT_WEIGHT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:report[k] for k in ['status','independent_elapsed_seconds','maximum','stronger_normalization_bound','stronger_bound_approx']})


if __name__=='__main__':
    run()
