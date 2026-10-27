"""Value-based price sensitivity with no inferred demand or measured buyer value."""
from fractions import Fraction as F
from pathlib import Path
import csv
import json
import model

ROOT=Path(__file__).resolve().parent
rows=[];checks=[]
for value in [3000,6000,12000,24000]:
    for capture in [F(1,4),F(1,2),F(3,4)]:
        for n in [1,2,4,6,8]:
            fee=value*capture
            result=model.outcome(model.SCENARIOS['central'],n,fee)
            # Separate closed-form accounting replay; assumptions unchanged.
            expected_profit=n*(fee*F(97,100)-1426)-15168
            assert result['full_project_profit']==expected_profit
            break_even_value=(F(15168,n)+1426)/(F(97,100)*capture)
            assert n*(break_even_value*capture*F(97,100)-1426)-15168==0
            condition=fee<=value
            rows.append(dict(cost_scenario='central unchanged',
                prospective_compatible_beneficiaries=n,
                hypothetical_net_incremental_value_each=value,
                fee_fraction_of_value=str(capture),conditional_fee_each=float(fee),
                conditional_accepted_revenue=float(result['conditional_accepted_revenue']),
                complete_project_cost=float(result['complete_project_cost']),
                full_project_profit=float(expected_profit),
                fee_not_above_value_condition=condition,
                hypothetical_buyer_surplus_each=float(value-fee),
                break_even_hypothetical_value_each=float(break_even_value),
                actual_demand_inferred=False))
            checks.append(dict(value=value,capture=str(capture),n=n,
                exact_fee=str(fee),exact_profit=str(expected_profit),
                exact_break_even_value=str(break_even_value),passed=True))
assert len(rows)==60
half_four=(F(15168,4)+1426)/(F(97,100)*F(1,2))
assert half_four==F(1043600,97)
assert model.outcome(model.SCENARIOS['central'],4,6000)['full_project_profit']==2408
assert model.outcome(model.SCENARIOS['central'],4,3000)['full_project_profit']==-9232
with (ROOT/'value_pricing_grid.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
audit={'status':'PASS: 60 conditional value-price combinations exactly reconciled',
    'grid':{'net_incremental_value':[3000,6000,12000,24000],
            'capture_fractions':['1/4','1/2','3/4'],'compatible_participants':[1,2,4,6,8]},
    'definition':'V is hypothetical incremental accepted value of paid review/integration relative to the public-artifact outside option, already net of buyer internal costs.',
    'condition':'p<=V is only a necessary affordability/participation inequality under these assumptions, not observed willingness to pay or demand.',
    'fixed_cost':15168,'variable_cost':1426,'processing_fraction':'3/100',
    'break_even_value_N4_capture_half':{'exact':str(half_four),'approx':float(half_four)},
    'named_cases':[{'V':12000,'capture':'1/2','N':4,'fee':6000,'profit':2408},
                   {'V':6000,'capture':'1/2','N':4,'fee':3000,'profit':-9232}],
    'checks':checks,
    'limitations':['No buyer value or willingness to pay was measured.',
                  'Participation is held fixed as a compatible cohort assumption; no demand curve is inferred.',
                  'Public certificate and self-service options remain available.',
                  'Capture fractions are sensitivity inputs, not optimal mechanisms or a game-theoretic result.',
                  'Amounts are pre-tax, before hypothetical financing costs, and include discovery only once.']}
(ROOT/'value_pricing_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(audit['status'])
print('N4,50% capture break-even value:',float(half_four))
