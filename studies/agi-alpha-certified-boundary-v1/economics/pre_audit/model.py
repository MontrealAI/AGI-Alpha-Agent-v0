"""Deterministic planning model for one fixed, existing proof artifact.

No market, receipts, wages paid, token charges, or future discoveries are inferred.
All money USD; pre-tax; fractions eliminate floating-point accounting noise.
"""
from fractions import Fraction as Q
from pathlib import Path
import csv
import json
import math

ROOT = Path(__file__).resolve().parent

# Analyst assumptions, not observed labor or sourced market offers.
# (activity, baseline hours, loaded-before-overhead hourly rate, phase)
FIXED = [
    ('Discovery research, including failed search',24,110,'development'),
    ('Certificate construction and repair',18,110,'development'),
    ('Independent mathematical review and reproduction',20,140,'delivery'),
    ('Publication and reproducibility packaging',12,90,'delivery'),
    ('Correction and failed-review allowance',12,110,'delivery'),
    ('Human oversight, rights and commitments',6,120,'delivery'),
    ('Acquisition and sponsor coordination',10,100,'delivery'),
    ('One-year shared maintenance and response',8,100,'delivery'),
]
VARIABLE = [
    ('Beneficiary integration',4,110,'delivery'),
    ('Acceptance and independent reproduction',2,140,'delivery'),
    ('Onboarding',1,90,'delivery'),
    ('Support',2,90,'delivery'),
    ('Correction and failure allowance',Q(3,2),110,'delivery'),
]
SCENARIOS = {
    'favorable':dict(hours=Q(13,20),rates=Q(9,10),n=5,fee=6000,capital=5000),
    'central':dict(hours=Q(1),rates=Q(1),n=4,fee=6000,capital=5000),
    'adverse':dict(hours=Q(8,5),rates=Q(11,10),n=2,fee=6000,capital=5000),
}
OVERHEAD=Q(1,5)
PAYMENT_FEE=Q(3,100)
RESERVE_RATE=Q(1,20)

def as_number(x):
    return round(float(x),4) if isinstance(x,Q) else x

def cost_model(s):
    rows=[]
    for shared,items in [('fixed',FIXED),('per_beneficiary',VARIABLE)]:
        for name,hours,rate,phase in items:
            h=Q(hours)*s['hours']; r=Q(rate)*s['rates']; cost=h*r
            rows.append(dict(activity=name,scope=shared,phase=phase,hours=h,
                             hourly_rate=r,labor=cost,overhead=cost*OVERHEAD,
                             complete_cost=cost*(1+OVERHEAD)))
    # Compute/storage budgets are allowances, not measured API invoices.
    rows += [dict(activity='Research and verification compute allowance',scope='fixed',
                  phase='development',hours=Q(0),hourly_rate=Q(0),labor=Q(0),
                  overhead=Q(0),complete_cost=Q(300)*s['hours']),
             dict(activity='One-year shared storage and distribution',scope='fixed',
                  phase='delivery',hours=Q(0),hourly_rate=Q(0),labor=Q(0),
                  overhead=Q(0),complete_cost=Q(60)),
             dict(activity='Per-beneficiary compute and distribution',scope='per_beneficiary',
                  phase='delivery',hours=Q(0),hourly_rate=Q(0),labor=Q(0),
                  overhead=Q(0),complete_cost=Q(40)*s['hours'])]
    fixed=sum(r['complete_cost'] for r in rows if r['scope']=='fixed')
    variable=sum(r['complete_cost'] for r in rows if r['scope']=='per_beneficiary')
    development=sum(r['complete_cost'] for r in rows if r['phase']=='development')
    return rows,fixed,variable,development

def outcome(s,n=None,fee=None):
    rows,fixed,variable,development=cost_model(s)
    n=s['n'] if n is None else n; fee=Q(s['fee'] if fee is None else fee)
    revenue=n*fee; payment=PAYMENT_FEE*revenue
    costs=fixed+n*variable+payment
    contribution=fee*(1-PAYMENT_FEE)-variable
    return dict(prospective_beneficiaries=n,conditional_fee=fee,
                conditional_accepted_revenue=revenue,fixed_cost=fixed,
                per_beneficiary_cost=variable,development_cost_counted_once=development,
                payment_processing_cost=payment,complete_project_cost=costs,
                delivery_operating_surplus_before_development=revenue-costs+development,
                full_project_profit=revenue-costs,
                break_even_fee=(fixed/n+variable)/(1-PAYMENT_FEE),
                break_even_beneficiaries_at_fee=(math.ceil(fixed/contribution)
                                               if contribution>0 else None),
                required_warranty_cash_reserve=RESERVE_RATE*revenue,
                original_capital=s['capital'])

def cash_ledger(s):
    _,fixed,variable,_=cost_model(s); n=s['n']; gross=Q(n*s['fee'])
    cash=Q(s['capital']); restricted=Q(0); recognized=Q(0); cumulative_cost=Q(0)
    reserve=Q(0); rows=[]; peak_gap=Q(0)
    # All dates are relative stages; refundable deposits are never used for costs.
    events=[
        ('Pre-contract research allocation',Q(0),Q(0),Q(0),fixed/4,Q(0)),
        ('Signed contingent sponsorship; refundable deposit',gross*Q(2,5),gross*Q(2,5),Q(0),gross*Q(2,5)*PAYMENT_FEE,Q(0)),
        ('Independent review before first acceptance',Q(0),Q(0),Q(0),fixed*Q(2,5)+n*variable/4,Q(0)),
        ('Core dossier accepted; deposit earned; second payment',gross*Q(3,10),-gross*Q(2,5),gross*Q(7,10),gross*Q(3,10)*PAYMENT_FEE,gross*Q(7,10)*RESERVE_RATE),
        ('Integration, correction and prepaid maintenance obligations',Q(0),Q(0),Q(0),fixed*Q(7,20)+n*variable*Q(3,4),Q(0)),
        ('Final acceptance and final payment',gross*Q(3,10),Q(0),gross*Q(3,10),gross*Q(3,10)*PAYMENT_FEE,gross*Q(3,10)*RESERVE_RATE),
    ]
    for event,receipt,restricted_change,earned,cost,reserve_change in events:
        cash+=receipt-cost; restricted+=restricted_change; recognized+=earned
        cumulative_cost+=cost; reserve+=reserve_change
        available=cash-restricted-reserve
        gap=max(Q(0),-available); peak_gap=max(peak_gap,gap)
        rows.append(dict(stage=event,gross_cash_before_new_finance=cash,
                         restricted_refundable_deposits=restricted,
                         earned_revenue_to_date=recognized,paid_or_reserved_cost_to_date=cumulative_cost,
                         additional_unrestricted_warranty_reserve=reserve,
                         spendable_cash_before_new_finance=available,
                         cumulative_new_finance_required=peak_gap,
                         funding_feasible_with_original_capital=(available>=0)))
    assert recognized==gross and restricted==0
    expected=outcome(s)
    assert cumulative_cost==expected['complete_project_cost']
    assert cash==s['capital']+expected['full_project_profit']
    # Cancellation just before first acceptance: deposits returned in full;
    # refund is removal of a liability, not negative operating revenue.
    canceled_sunk=fixed*Q(13,20)+n*variable/4+gross*Q(2,5)*PAYMENT_FEE
    cancellation=dict(earned_revenue=Q(0),deposit_refunded=gross*Q(2,5),
                      restricted_balance_after_refund=Q(0),
                      unrecovered_cost=canceled_sunk,
                      cash_before_new_finance=s['capital']-canceled_sunk)
    return rows,peak_gap,cancellation

def write_csv(name,rows):
    with (ROOT/name).open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k:as_number(v) for k,v in row.items()} for row in rows)

def main():
    results={}; summary=[]; detail=[]; cash=[]
    for name,s in SCENARIOS.items():
        costs,*_=cost_model(s); result=outcome(s)
        ledger,gap,cancellation=cash_ledger(s)
        result['peak_additional_financing_required']=gap
        # Illustrative 90-day bridge: 2% fee withheld at inception and 12%
        # simple annual interest, all assumed, not an available lender offer.
        loan=gap/Q(98,100)
        finance_cost=loan*(Q(2,100)+Q(12,100)*Q(90,360))
        result['illustrative_bridge_principal']=loan
        result['illustrative_bridge_cost']=finance_cost
        result['profit_after_illustrative_bridge']=result['full_project_profit']-finance_cost
        result['pre_acceptance_cancellation']=cancellation
        results[name]=result
        summary.append(dict(scenario=name,**{k:v for k,v in result.items() if not isinstance(v,dict)}))
        detail.extend(dict(scenario=name,**row) for row in costs)
        cash.extend(dict(scenario=name,**row) for row in ledger)
    grid=[]
    for n in range(1,13):
        for fee in [3000,4000,4800,6000,8000,10000,14000,18000]:
            r=outcome(SCENARIOS['central'],n,fee)
            grid.append(dict(prospective_beneficiaries=n,conditional_fee=fee,
                             revenue=r['conditional_accepted_revenue'],
                             full_project_profit=r['full_project_profit'],
                             break_even_fee=r['break_even_fee']))
    schedule=[]
    for n,fee in [(1,18000),(2,10000),(4,6000),(6,4800),(8,4000)]:
        r=outcome(SCENARIOS['central'],n,fee)
        schedule.append(dict(committed_participants=n,conditional_price=fee,
                             full_project_profit=r['full_project_profit'],
                             break_even_price=r['break_even_fee']))
    retention=dict(extraction=330,additional_validation=280,integration=220,
                   one_year_upkeep=200,storage=12,
                   evidence_supported_incremental_benefit_over_same_asset_library=0,
                   total_additional_cost=1042,modeled_net_incremental_value=-1042,
                   decision='HOLD: incremental benefit over ordinary library not established',
                   note='Zero is the benefit admitted to planning, not a measured zero or proof of zero possible future benefit.')
    evidence={'status':'Conditional deterministic planning only',
              'currency':'USD','actual_revenue':0,'actual_receipts':0,
              'actual_customers':0,'actual_complete_study_cost':None,
              'actual_profit':None,'unknown_cost_reason':'No complete authoring, model, labor or infrastructure billing supplied.',
              'price_evidence':'No observed willingness to pay; all fees are sensitivity inputs.',
              'rates_evidence':'Analyst labor-resource assumptions; not sourced quotes or observed wages.',
              'cost_basis':'Human-resource replacement/planning estimate including research once; not an invoice.',
              'reserve_rule':'Warranty reserve is liquidity encumbrance, not an additional expense; expected rework is already in costs.',
              'overhead_rate':OVERHEAD,'payment_processing_rate':PAYMENT_FEE,
              'warranty_reserve_rate':RESERVE_RATE,'scenarios':results,'retention':retention}
    (ROOT/'results.json').write_text(json.dumps(evidence,default=as_number,indent=2)+'\n')
    write_csv('scenarios.csv',summary); write_csv('cost_detail.csv',detail)
    write_csv('cash_ledger.csv',cash); write_csv('fee_participation_grid.csv',grid)
    write_csv('conditional_participation_discounts.csv',schedule)
    central=results['central']
    arms=[
        dict(arm='Existing finite MILP arrangement',universal_certificate_accepted=False,
             finding='Finite cases only; no all-n certificate',conditional_profit='',
             economic_interpretation='Acceptance failed for requested universal outcome; no sale credited'),
        dict(arm='Technical proof alone, one beneficiary',universal_certificate_accepted=True,
             finding='Exact certificate and independent checks',
             conditional_profit=outcome(SCENARIOS['central'],1,6000)['full_project_profit'],
             economic_interpretation='Illustrative one-buyer funding at $6000; no demand established'),
        dict(arm='Commercial coordination alone',universal_certificate_accepted=False,
             finding='Sharing finite MILP results does not certify every n',conditional_profit='',
             economic_interpretation='Acceptance failed for requested universal outcome; no sale credited'),
        dict(arm='Technical proof and shared sponsorship',universal_certificate_accepted=True,
             finding='Same certificate; four prospective sponsors',
             conditional_profit=central['full_project_profit'],
             economic_interpretation='Conditional fixed-cost sharing; no new technical interaction inferred'),
        dict(arm='Conventional shared arrangement, same artifact',universal_certificate_accepted=True,
             finding='Same certificate, reviewers, buyer access, costs and fees',
             conditional_profit=central['full_project_profit'],
             economic_interpretation='Exact economic and technical tie by matched arrangement'),
    ]
    write_csv('arrangements.csv',arms)
    print(json.dumps({k:{j:as_number(v) for j,v in r.items() if j in
          ['complete_project_cost','full_project_profit','break_even_fee',
           'break_even_beneficiaries_at_fee','peak_additional_financing_required']}
          for k,r in results.items()},indent=2))

if __name__=='__main__':
    main()
