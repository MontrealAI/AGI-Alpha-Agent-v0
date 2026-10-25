import json
from decimal import Decimal
from pathlib import Path
p=Path(__file__).resolve().parent
x=json.loads((p/'market_scenarios.json').read_text())
d=lambda v: Decimal(str(v))
f=lambda v: float(v.quantize(Decimal('0.01')))
rows=[]
for s in x['scenarios']:
    digital=d(s['digital_task_labor_usd']); eligible=digital*d(s['technical_eligible_fraction']); adopted=eligible*d(s['adoption_fraction'])
    retained=adopted*d(s['retained_customer_cost_fraction']); fees=adopted*d(s['service_price_fraction']); provider_cost=adopted*d(s['provider_operating_cost_fraction']); share=d(s['individual_provider_share'])
    savings=adopted-retained-fees
    assert adopted==retained+fees+savings and fees>=provider_cost and savings>=0
    rows.append({'name':s['name'],'digital_share_of_reference':float(digital/d(x['total_labor_expenditure_reference_usd'])),'digital_task_labor_usd':f(digital),'technically_eligible_labor_usd':f(eligible),'adopted_task_baseline_labor_usd':f(adopted),'retained_customer_cost_usd':f(retained),'all_provider_service_revenue_usd':f(fees),'potential_customer_economic_savings_usd':f(savings),'single_provider_revenue_usd':f(fees*share),'single_provider_operating_cost_usd':f(provider_cost*share),'single_provider_gross_contribution_before_fixed_costs_usd':f((fees-provider_cost)*share)})
compensation={'US_private_office_admin_Dec2025':d('35.96'),'US_private_professional_related_Dec2025':d('72.19'),'US_private_management_business_finance_Dec2025':d('86.61')}
thresholds=[{'cost_basis':k,'hourly_total_compensation_usd':float(w),'hypothetical_fully_allocated_system_cost_usd':c,'break_even_human_minutes':f(d(60)*d(c)/w)} for k,w in compensation.items() for c in (1,5,10,25)]
result={'status':x['status'],'rows':rows,'compensation_source':'https://www.bls.gov/news.release/archives/ecec_03202026.htm Table 4','break_even_thresholds_status':'MODELED_THRESHOLDS_NOT_OBSERVED_HUMAN_TIMES; comparable human review or overhead must be added separately if not included','break_even_thresholds':thresholds,'mechanical_GDP_times_labor_share_scale_check_usd':f(d('118.35e12')*d('0.526')),'forty_trillion_fraction_of_scale_check':float(d('40e12')/(d('118.35e12')*d('0.526')))}
(p/'scenario_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
