# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.util
import json
import random
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('capacity_candidate',ROOT/'run_economics_v1_1.py')
if spec is None or spec.loader is None:
    raise RuntimeError('Missing candidate')
candidate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
plan=json.loads((ROOT/'capacity-correction-plan-v1_1.json').read_text())
protocol=json.loads((ROOT/'confirmation-protocol.json').read_text())
assert hashlib.sha256((ROOT/'run_economics_v1_1.py').read_bytes()).hexdigest()==plan['candidate_source_sha256']
old=json.loads((ROOT/'results-v1'/'paths.json').read_text())
selected=candidate.prices(protocol)
assert selected['selected_price_cents']==32500
rng=random.Random(plan['fresh_capacity_seed'])
base_minutes=60+3*(70+6)
base_A=old['E+success']['required_core_cents']+3*old['E+success']['per_packet_cost']['total_cents']
cases=[]
for shock,duration,step_cost in [('common-failure',15,3125),('support-overrun',30,6250)]:
    for completed in range(4):
        remainder=rng.randrange(duration)
        limit=base_minutes+duration*completed+remainder
        result=candidate.run_path(protocol,selected,'E+',shock,{'capacity_minutes':limit})
        state=result['final']
        expected_accepted=0 if shock=='common-failure' else completed
        expected_refunds=15000 if shock=='common-failure' else (3-completed)*5000
        expected_A=base_A+completed*step_cost
        assert state['used_capacity_units']==base_minutes+duration*completed
        assert state['used_capacity_units']<=limit
        assert result['accepted_packets']==expected_accepted
        assert state['refunds_cents']==expected_refunds
        assert state['costs_cents']['A']==expected_A
        cancelled=[x for x in result['decisions'] if x.get('decision')=='cancel-unaccepted-contract']
        assert len(cancelled)==3-completed
        assert all(x['performed_minutes']==0 and x['additional_fee_paid_cents']==0 for x in cancelled)
        for step in result['events']:
            s=step['state']
            assert s['cash_cents']==s['capital_cents']+s['gross_collections_cents']-s['refunds_cents']-s['paid_costs_cents']
            assert s['cash_cents']>=s['refundable_liability_cents']
        cases.append({'case':f'{shock}-{completed}','capacity_limit_minutes':limit,'random_remainder_minutes':remainder,
            'expected_completed_extra_obligations':completed,'used_minutes':state['used_capacity_units'],
            'accepted_packets':result['accepted_packets'],'refunds_cents':state['refunds_cents'],
            'cost_A_cents':state['costs_cents']['A'],'passed':True,'path':result})
regressions=[]
for key,previous in old.items():
    result=candidate.run_path(protocol,selected,previous['configuration'],previous['shock'])
    before=dict(previous['final'])
    after=dict(result['final'])
    before.pop('used_capacity_units')
    after.pop('used_capacity_units')
    assert before==after
    assert previous['accepted_packets']==result['accepted_packets']
    regressions.append({'case':key,'economic_and_acceptance_fields_unchanged':True,
        'old_capacity_minutes':previous['final']['used_capacity_units'],'corrected_capacity_minutes':result['final']['used_capacity_units']})
price_rows=[]
p_accept=Fraction(protocol['reference']['assumed_acceptance_probability'])
p_collect=Fraction(protocol['reference']['assumed_collection_probability'])
cost=candidate.packet_cost(protocol,'E')['total_cents']
caps=selected['buyer_caps_cents']
for q in protocol['price_grid_cents']:
    n=sum(cap>=q for cap in caps)
    deposit=min(q,protocol['reference']['deposit_cents'])
    prior=n*(p_accept*p_collect*q-cost)
    corrected=n*(p_accept*(deposit+p_collect*(q-deposit))-cost)
    price_rows.append({'price_cents':q,'participants':n,'prior_approximate_expected_contribution_cents':str(prior),
        'corrected_expected_contribution_cents':str(corrected),'difference_cents':str(corrected-prior)})
best=max(price_rows,key=lambda x:(Fraction(x['corrected_expected_contribution_cents']),-x['price_cents']))
assert best['price_cents']==selected['selected_price_cents']==32500
report={'schema':'prospective-capacity-and-price-diagnostics/v1.1','fresh_capacity_cases':len(cases),
    'passed':sum(x['passed'] for x in cases),'regression_paths':len(regressions),'regressions':regressions,
    'corrected_reference_profit_cents':old['E+success']['final']['collected_basis_profit_cents'],
    'frozen_v1_price_unchanged':True,'price_diagnostic':{'formula':'p_accept * (deposit + p_collect * (price - deposit))',
        'grid':price_rows,'corrected_best_price_cents':best['price_cents'],
        'difference_per_reference_order_cents':'95','difference_three_reference_orders_cents':'285',
        'old_price_selection_retained':True,'retrospective_profit_recovery':False},
    'capacity_scope':plan['capacity_scope'],'source_sha256':plan['candidate_source_sha256'],
    'original_source_unchanged':hashlib.sha256((ROOT/'run_economics.py').read_bytes()).hexdigest()==plan['original_source_sha256'],
    'old72_worlds_replaced':False,'actual_customer_revenue_cents':0,'actual_complete_cost_cents':None}
out=ROOT/'results-v1_1'
out.mkdir(exist_ok=False)
(out/'diagnostics.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'fresh-capacity-cases.json').write_text(json.dumps(cases,indent=2)+'\n')
print(json.dumps(report,indent=2))
