import json
from decimal import Decimal
from pathlib import Path
p=Path(__file__).resolve().parent
x=json.loads((p/'human_market_benchmarks.json').read_text())
d=lambda v: Decimal(str(v))
r=lambda v: float(v.quantize(Decimal('0.0001')))
thresholds=[]; sensitivity=[]; summaries=[]
for b in x['rates']:
    rate=d(b['rate_per_hour'])
    if 'low_per_hour' in b: assert d(b['low_per_hour'])<=rate<=d(b['high_per_hour'])
    summaries.append({'benchmark_id':b['id'],'geography':b['geography'],'currency':b['currency'],'basis':b['cost_basis'],'hourly_rate':float(rate),'hypothetical_30_minute_job_cost':r(rate/2),'hypothetical_60_minute_job_cost':float(rate),'break_even_minutes_at_cost_5':r(d(300)/rate),'break_even_minutes_at_cost_10':r(d(600)/rate),'break_even_minutes_at_cost_25':r(d(1500)/rate)})
    loads=x['wage_only_employer_load_sensitivity'] if b['cost_basis']=='wage_only' else [1.0]
    for load in loads:
        loaded=rate*d(load)
        for ca in x['system_fully_allocated_cost_scenarios_own_currency']:
            threshold=d(60)*d(ca)/loaded
            thresholds.append({'benchmark_id':b['id'],'currency':b['currency'],'hourly_rate':float(rate),'employer_load_assumption':load,'valuation_rate':r(loaded),'assumed_system_fully_allocated_cost':ca,'break_even_human_minutes':r(threshold),'status':'MODELED_THRESHOLD_NOT_OBSERVED_HUMAN_TIME'})
            for minutes in x['human_minutes_sensitivity']:
                ch=loaded*d(minutes)/d(60)
                sensitivity.append({'benchmark_id':b['id'],'currency':b['currency'],'employer_load_assumption':load,'assumed_human_minutes':minutes,'modeled_human_cost':r(ch),'assumed_system_fully_allocated_cost':ca,'modeled_cost_ratio_human_over_system':r(ch/d(ca)),'modeled_economic_savings':r(ch-d(ca)),'status':'HYPOTHETICAL_SENSITIVITY_NOT_A_MEASURED_ADVANTAGE'})
result={'benchmark_status':x['status'],'currency_policy':x['currency_policy'],'headline_summaries_status':'MARKET_RATES_PLUS_ASSUMED_MINUTES_AND_SYSTEM_COSTS','summaries':summaries,'thresholds':thresholds,'sensitivity':sensitivity,'measured_head_to_head_ratio':None,'empirical_same_task_human_comparison':'NOT_RUN','actual_fully_allocated_system_cost':'UNKNOWN_IN_THIS_MARKET_DATA_MODULE'}
(p/'human_benchmark_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'rate_count':len(summaries),'threshold_count':len(thresholds),'sensitivity_rows':len(sensitivity),'summaries':summaries},indent=2))
