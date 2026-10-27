"""Fresh direct exact cell-integral confirmation for the final weight certificate."""
from fractions import Fraction as Q
from pathlib import Path
import hashlib
import json
import random
import time

ROOT=Path(__file__).resolve().parents[1]


def interpolation_and_integral(heights, denominator):
    prefix=[Q(0)]
    for left,right in zip(heights,heights[1:]):
        prefix.append(prefix[-1]+Q(left+right,2*denominator))

    def value(x):
        assert 0<=x<=1
        index=min((x*denominator).numerator//(x*denominator).denominator,denominator-1)
        offset=x-Q(index,denominator)
        slope=denominator*(heights[index+1]-heights[index])
        return heights[index]+slope*offset

    def primitive(x):
        assert 0<=x<=1
        index=min((x*denominator).numerator//(x*denominator).denominator,denominator-1)
        offset=x-Q(index,denominator)
        slope=denominator*(heights[index+1]-heights[index])
        return prefix[index]+heights[index]*offset+slope*offset*offset/2

    return value,primitive,prefix[-1]


def run():
    plan_path=ROOT/'lineage/FINAL_WEIGHT_CONFIRMATION_PLAN_V2.json'
    plan=json.loads(plan_path.read_text())
    raw=(ROOT/plan['witness_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==plan['witness_sha256']
    data=json.loads(raw)
    value,primitive,integral=interpolation_and_integral(data['heights'],data['knots_denominator'])
    maximum=Q(data['maximum'])
    assert integral==Q(data['integral']) and integral/maximum==Q(data['bound'])
    rng=random.Random(plan['seed'])
    start=time.monotonic()
    cases=[]
    for index in range(512):
        k=rng.randint(2,20) if index<256 else rng.randint(21,250)
        m=rng.randint(1,10000);r=rng.randint(1,m);pad=rng.randint(0,m-1)
        n=r+(k-1)*m+pad
        points=[r+j*m for j in range(k)]
        assert r-m<1 and points[-1]<=n<points[-1]+m
        phase=Q(rng.randrange(998),997)
        sample_lhs=Q(m,n)*sum((value(Q(i-1,n)+phase/n) for i in points),Q(0))
        cell_lhs=m*sum((primitive(Q(i,n))-primitive(Q(i-1,n)) for i in points),Q(0))
        assert sample_lhs<=maximum and cell_lhs<=maximum
        cases.append({'case':index,'n':n,'modulus':m,'first_member':r,'length':k,
                      'phase':str(phase),'sample_constraint':str(sample_lhs),
                      'cell_integral_constraint':str(cell_lhs),'passed':True})
    telescope=[]
    for n in [2,3,7,19,20,21,47,123,257]:
        summed=sum((primitive(Q(i,n))-primitive(Q(i-1,n)) for i in range(1,n+1)),Q(0))
        assert summed==integral
        telescope.append({'n':n,'sum_of_cell_integrals':str(summed),'equals_integral':True})
    # A known exact maximizing class phase rejects any smaller normalization.
    extremal=Q(4273,9120)*(value(Q(7,20))+value(Q(7,20)+Q(4273,9120)))
    assert extremal==maximum
    wrong_maximum=maximum-Q(1,1000000)
    assert extremal>wrong_maximum
    corrupt_heights=data['heights'].copy();corrupt_heights[10]+=100
    wrong_value,_,_=interpolation_and_integral(corrupt_heights,20)
    changed_height_lhs=sum((wrong_value(Q(2*i-1,6)) for i in [1,2,3]),Q(0))/3
    assert changed_height_lhs>maximum
    report={
      'status':'PASS: 512 fresh exact cell-average and phase cases; altered normalization and height rejected',
      'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),
      'witness_sha256':hashlib.sha256(raw).hexdigest(),'seed':plan['seed'],
      'elapsed_seconds':time.monotonic()-start,'short_class_cases':256,'tail_class_cases':256,
      'maximum_fresh_phase_ratio':float(max(Q(c['sample_constraint']) for c in cases)/maximum),
      'maximum_fresh_cell_ratio':float(max(Q(c['cell_integral_constraint']) for c in cases)/maximum),
      'telescoping_cell_checks':telescope,
      'normalization_adverse_control':{'n':9120,'m':4273,'first_member':3193,'phase':'0',
         'actual_constraint':str(extremal),'rejected_normalization':str(wrong_maximum),'refused_exactly':True},
      'height_adverse_control':{'change':'add100 to middle knot height','n':3,'m':1,'first_member':1,'phase':'1/2',
         'actual_constraint':str(changed_height_lhs),'allowed_maximum':str(maximum),'refused_exactly':True},
      'cases':cases,
      'scope':'Fresh implementation confirmation, not a replacement for the universal proof. No model A/B or market inference.'
    }
    destination=ROOT/'confirmation/final_weight_exact_cases.json'
    assert not destination.exists()
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print({key:report[key] for key in ['status','elapsed_seconds','maximum_fresh_phase_ratio','maximum_fresh_cell_ratio']})


if __name__=='__main__':
    run()
