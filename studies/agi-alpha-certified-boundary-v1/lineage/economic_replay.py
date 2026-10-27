"""Independent exact algebra/cash replay; does not import the economic model."""
from fractions import Fraction as Q
from pathlib import Path
import csv
import json
import math

ROOT=Path(__file__).resolve().parents[1]


def close_to_report(exact, reported):
    assert abs(exact-Q(str(reported)))<=Q(1,20000),(exact,reported)


def run():
    source=json.loads((ROOT/'economics/results.json').read_text())
    ledger=list(csv.DictReader((ROOT/'economics/cash_ledger.csv').open()))
    definitions=[('favorable',Q(13,20),Q(9,10),5),('central',Q(1),Q(1),4),
                 ('adverse',Q(8,5),Q(11,10),2)]
    # Independently sum the stated activity assumptions; these are NOT invoices.
    base_fixed_labor=sum(Q(h)*r for h,r in [(24,110),(18,110),(20,140),(12,90),
                                           (12,110),(6,120),(10,100),(8,100)])
    base_variable_labor=sum(Q(h)*r for h,r in [(4,110),(2,140),(1,90),(2,90),(Q(3,2),110)])
    assert base_fixed_labor==12340 and base_variable_labor==1155
    results=[]
    for name,hours,rates,n in definitions:
        f=Q(6,5)*base_fixed_labor*hours*rates+300*hours+60
        v=Q(6,5)*base_variable_labor*hours*rates+40*hours
        r=Q(n*6000)
        cost=f+n*v+Q(3,100)*r
        profit=r-cost
        development=Q(6,5)*42*110*hours*rates+300*hours
        stages=[f/4,Q(3,100)*Q(2,5)*r,Q(2,5)*f+n*v/4,
                Q(3,100)*Q(3,10)*r,Q(7,20)*f+Q(3,4)*n*v,Q(3,100)*Q(3,10)*r]
        receipts=[Q(0),Q(2,5)*r,Q(2,5)*r,Q(7,10)*r,Q(7,10)*r,r]
        liabilities=[Q(0),Q(2,5)*r,Q(2,5)*r,Q(0),Q(0),Q(0)]
        reserves=[Q(0),Q(0),Q(0),Q(7,200)*r,Q(7,200)*r,Q(1,20)*r]
        running=Q(0);gap=Q(0);cash_rows=[]
        for j,c in enumerate(stages):
            running+=c
            bank=5000+receipts[j]-running
            spendable=bank-liabilities[j]-reserves[j]
            gap=max(gap,-spendable)
            cash_rows.append({'stage_index':j+1,'gross_cash':str(bank),
                              'refundable_liability':str(liabilities[j]),
                              'warranty_reserve':str(reserves[j]),
                              'unrestricted_after_reserve':str(spendable),
                              'cumulative_financing_need':str(gap)})
        assert running==cost and Q(cash_rows[-1]['gross_cash'])==5000+profit
        target=source['scenarios'][name]
        exact={'fixed_cost':f,'per_beneficiary_cost':v,'complete_project_cost':cost,
               'full_project_profit':profit,'development_cost_counted_once':development,
               'delivery_operating_surplus_before_development':profit+development,
               'break_even_fee':(f/n+v)/Q(97,100),
               'peak_additional_financing_required':gap,
               'illustrative_bridge_principal':gap/Q(98,100)}
        exact['illustrative_bridge_cost']=exact['illustrative_bridge_principal']/20
        exact['profit_after_illustrative_bridge']=profit-exact['illustrative_bridge_cost']
        for key,value in exact.items():
            close_to_report(value,target[key])
        assert target['break_even_beneficiaries_at_fee']==math.ceil(f/(6000*Q(97,100)-v))
        reported_rows=[row for row in ledger if row['scenario']==name]
        assert len(reported_rows)==6
        for exact_row,reported_row in zip(cash_rows,reported_rows):
            for ek,rk in [('gross_cash','gross_cash_before_new_finance'),
                          ('refundable_liability','restricted_refundable_deposits'),
                          ('warranty_reserve','additional_unrestricted_warranty_reserve'),
                          ('unrestricted_after_reserve','spendable_cash_before_new_finance'),
                          ('cumulative_financing_need','cumulative_new_finance_required')]:
                close_to_report(Q(exact_row[ek]),reported_row[rk])
        canceled=f*Q(13,20)+n*v/4+r*Q(2,5)*Q(3,100)
        close_to_report(canceled,target['pre_acceptance_cancellation']['unrecovered_cost'])
        close_to_report(5000-canceled,target['pre_acceptance_cancellation']['cash_before_new_finance'])
        final_after_repayment=5000+exact['profit_after_illustrative_bridge']
        results.append({'scenario':name,'exact_replayed_results':{k:str(v) for k,v in exact.items()},
                        'cash_rows':cash_rows,'post_bridge_repayment_cash':str(final_after_repayment),
                        'repayment_shortfall_without_further_capital':str(max(Q(0),-final_after_repayment)),
                        'matches_published_planning_outputs':True})
    assert source['actual_revenue']==source['actual_receipts']==source['actual_customers']==0
    assert source['actual_complete_study_cost'] is None and source['actual_profit'] is None
    out={'status':'PASS independent exact arithmetic and six-stage cash replay',
         'method':'Separate Fraction algebra; economic model module is not imported',
         'scope':'Consistency of stated assumptions only, not validation of prices, demand, resource hours or financing availability',
         'scenarios':results,'actual_profit_not_asserted':True,
         'material_qualifications':[
          'Ninety-day finance costs assume final receipts and repayment occur within the modeled term.',
          'The adverse case remains loss-making and cannot repay the illustrative bridge from the modeled project cash and original capital.',
          'Deposits stay liabilities until acceptance; fees and refundable principal are treated separately.',
          'Warranty reserves constrain liquidity without being charged a second time as expense.'
         ]}
    (ROOT/'lineage/ECONOMIC_REPLAY.json').write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'])
    for item in results:
        print(item['scenario'],item['exact_replayed_results']['full_project_profit'],
              item['exact_replayed_results']['peak_additional_financing_required'])


if __name__=='__main__':
    run()
