"""Separate exact algebraic replay of the planning model.

This is an internal second pass, not an independent accountant's opinion.
"""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import model

BASE=Path(__file__).resolve().parent
claims=[]

def check(name,actual,expected):
    assert actual==expected,(name,actual,expected)
    claims.append(dict(assertion=name,passed=True,exact_value=str(actual)))

check('central fixed cost from independently summed labor and allowances',
      model.cost_model(model.SCENARIOS['central'])[1],F(15168))
check('central marginal cost from10.5hours plus overhead and compute',
      model.cost_model(model.SCENARIOS['central'])[2],F(1426))
check('development counted once, including fixed compute',
      model.cost_model(model.SCENARIOS['central'])[3],F(5844))

scenario_audits={}
for name,s in model.SCENARIOS.items():
    n=s['n']; p=F(s['fee']); gross=n*p
    # Independently collapsed arithmetic, not the activity-table loop.
    fixed=F(12340)*s['hours']*s['rates']*F(6,5)+300*s['hours']+60
    variable=F(1155)*s['hours']*s['rates']*F(6,5)+40*s['hours']
    development=F(4620)*s['hours']*s['rates']*F(6,5)+300*s['hours']
    all_cost=fixed+n*variable+gross*F(3,100)
    r=model.outcome(s)
    for k,v in [('fixed_cost',fixed),('per_beneficiary_cost',variable),
                ('development_cost_counted_once',development),
                ('complete_project_cost',all_cost),('full_project_profit',gross-all_cost),
                ('delivery_operating_surplus_before_development',gross-all_cost+development),
                ('break_even_fee',(fixed/n+variable)/F(97,100))]:
        check(name+': '+k,r[k],v)
    ledger,gap,cancel=model.cash_ledger(s)
    # Replay independent cumulative receipts, liabilities, revenue and cost.
    receipts=[0,gross*F(2,5),gross*F(2,5),gross*F(7,10),gross*F(7,10),gross]
    liabilities=[0,gross*F(2,5),gross*F(2,5),0,0,0]
    recognized=[0,0,0,gross*F(7,10),gross*F(7,10),gross]
    costs=[fixed/4,
           fixed/4+gross*F(2,5)*F(3,100),
           fixed*F(13,20)+n*variable/4+gross*F(2,5)*F(3,100),
           fixed*F(13,20)+n*variable/4+gross*F(7,10)*F(3,100),
           fixed+n*variable+gross*F(7,10)*F(3,100),all_cost]
    reserves=[0,0,0,gross*F(7,10)*F(1,20),gross*F(7,10)*F(1,20),gross*F(1,20)]
    required=F(0)
    for j,row in enumerate(ledger):
        check(f'{name} stage{j}: gross cash conservation',row['gross_cash_before_new_finance'],s['capital']+receipts[j]-costs[j])
        check(f'{name} stage{j}: customer deposit liability',row['restricted_refundable_deposits'],liabilities[j])
        check(f'{name} stage{j}: accepted revenue only',row['earned_revenue_to_date'],recognized[j])
        check(f'{name} stage{j}: remaining full-term cost obligation',row['remaining_modeled_cost_to_complete'],all_cost-costs[j])
        check(f'{name} stage{j}: reserve excluded from expense',row['additional_unrestricted_warranty_reserve'],reserves[j])
        available=s['capital']+receipts[j]-costs[j]-liabilities[j]-reserves[j]
        check(f'{name} stage{j}: spendable cash excludes deposits/reserve',row['spendable_cash_before_new_finance'],available)
        required=max(required,-available)
    check(name+': peak extra unrestricted funding',gap,required)
    check(name+': final cash equals initial capital plus full-project profit',ledger[-1]['gross_cash_before_new_finance'],s['capital']+r['full_project_profit'])
    check(name+': full refund retires liability without revenue recognition',cancel['deposit_refunded'],gross*F(2,5))
    check(name+': cancellation income zero',cancel['earned_revenue'],F(0))
    check(name+': cancellation expenses omit refunded principal',cancel['unrecovered_cost'],costs[2])
    # A funding gap is not silently cured by spending the customer's deposit.
    assert any(not row['funding_feasible_with_original_capital'] for row in ledger)
    principal=gap/F(98,100); finance_cost=principal*F(5,100)
    check(name+': bridge proceeds net of withheld fee cover gap',principal*F(98,100),gap)
    financed_end=s['capital']+r['full_project_profit']-finance_cost-gross*F(1,20)
    scenario_audits[name]=dict(peak_gap=str(gap),bridge_principal=str(principal),
        financing_cost=str(finance_cost),end_cash_after_repayment_and_reserve=str(financed_end),
        bridge_repayment_feasible=financed_end>=0)

check('central exact all-cost total',model.outcome(model.SCENARIOS['central'])['complete_project_cost'],F(21592))
check('central exact full-project profit',model.outcome(model.SCENARIOS['central'])['full_project_profit'],F(2408))
check('central peak extra financing',model.cash_ledger(model.SCENARIOS['central'])[1],F(32866,5))
assert scenario_audits['central']['bridge_repayment_feasible']
assert scenario_audits['favorable']['bridge_repayment_feasible']
assert not scenario_audits['adverse']['bridge_repayment_feasible']
out={'status':'PASS: exact algebraic replay; internal audit, not external accounting review',
     'assertions_passed':len(claims),'claims':claims,'scenario_financing':scenario_audits,
     'corrections':['No headline arithmetic changed. Added explicit remaining cost and prepaid support/maintenance columns.',
                    'Changed paid-or-reserved cash-flow label to paid-or-prepaid: a mere reserve does not reduce gross cash.',
                    'Added bridge repayment feasibility; adverse loss cannot support repayment from modeled end cash.',
                    'Clarified counterfactual cash gaps,90-day repayment assumption and full-term managerial recognition rather than statutory accounting.'],
     'preserved_before_audit':'economics/pre_audit/',
     'model_sha256':hashlib.sha256((BASE/'model.py').read_bytes()).hexdigest(),
     'limitations':['Labor hours and rates are unsourced planning assumptions.','No actual sales, demand, finance offer, model billing or complete actual project cost.',
                    'A one-year support obligation remains even though the timing model prepays its expected cost.','External accounting and contractual review not performed.']}
(BASE/'audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'],len(claims))
