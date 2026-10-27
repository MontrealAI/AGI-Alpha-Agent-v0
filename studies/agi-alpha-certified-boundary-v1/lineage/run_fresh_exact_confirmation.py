"""Fresh exact cases against the frozen witness; not a substitute for proof."""
import hashlib
import json
import math
import random
import time
from fractions import Fraction as Q
from pathlib import Path
from myerson_independent_uniform import make_centered_polynomial, evaluate

ROOT=Path(__file__).resolve().parents[1]


def run():
    plan_path=ROOT/'lineage/FRESH_CONFIRMATION_PLAN.json'
    plan=json.loads(plan_path.read_text())
    raw=(ROOT/plan['witness_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==plan['witness_sha256']
    coefficients=list(map(Q,json.loads(raw)['coefficients']))
    centered=make_centered_polynomial(coefficients)
    integral=sum((centered[j]/Q(j+1) for j in range(0,21,2)),Q(0))
    assert integral==Q(plan['exact_bound'])
    rng=random.Random(plan['random_seed'])
    start=time.monotonic()
    cases=[]
    for index in range(plan['fresh_exact_classes']):
        n=rng.randint(2,1000000)
        m=rng.randint(max(1,(n+79)//80),n-1)
        r=rng.randint(1,min(m,n-m))
        points=list(range(r,n+1,m))
        assert len(points)>=2 and r-m<1 and points[-1]+m>n
        lhs=Q(m,n)*sum((evaluate(centered,Q(2*x-1-n,n)) for x in points),Q(0))
        assert lhs<=1,(n,m,r,lhs)
        cases.append({'index':index,'n':n,'m':m,'first_member':r,'length':len(points),
                      'constraint_left_side':str(lhs),'passes':True})
    midpoints=[]
    for n in plan['fresh_midpoint_lengths']:
        average=sum((evaluate(centered,Q(2*i-1-n,n)) for i in range(1,n+1)),Q(0))/n
        assert average>integral
        midpoints.append({'n':n,'average':str(average),'difference_above_bound':str(average-integral),'passes':True})
    original=json.loads((ROOT/'scout/polynomial_probe.json').read_text(),parse_float=Q)
    wrong=make_centered_polynomial(original['cheb_even_coefficients'])
    original_lhs=Q(15,26)*(evaluate(wrong,Q(21-26,26))+evaluate(wrong,Q(51-26,26)))
    assert original_lhs>1
    worst=max(cases,key=lambda c:Q(c['constraint_left_side']))
    out={
      'status':'PASS_FRESH_EXACT_CASES; wrapper refusal controls are recorded separately',
      'scope':'Finite implementation confirmation only; universal validity rests on the independent complete certificates.',
      'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),
      'witness_sha256':hashlib.sha256(raw).hexdigest(),
      'seed':plan['random_seed'],'elapsed_seconds':time.monotonic()-start,
      'valid_class_count':len(cases),'all_valid_class_cases_pass':True,
      'highest_fresh_constraint_value':float(Q(worst['constraint_left_side'])),
      'highest_fresh_constraint_case':worst,
      'midpoint_checks':midpoints,
      'known_original_invalid_witness_rejected':{
       'n':26,'m':15,'first_member':11,'members':[11,26],
       'constraint_value':str(original_lhs),'violates_exactly':True},
      'cases':cases,
    }
    (ROOT/'lineage/FRESH_EXACT_CONFIRMATION.json').write_text(json.dumps(out,indent=2)+'\n')
    print({k:out[k] for k in ['status','valid_class_count','all_valid_class_cases_pass',
                             'highest_fresh_constraint_value','elapsed_seconds']})


if __name__=='__main__':
    run()
