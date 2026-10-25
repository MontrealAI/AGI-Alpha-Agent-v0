"""Postfreeze decision model: measured CPU, public labor prices, explicit assumptions.

No frozen files are changed. This script reads the primary receipts and frozen
labor sources. Its economic presentation was specified after primary execution;
it is not a preregistered empirical human comparison.
"""
import hashlib
import json
from decimal import Decimal, getcontext
from itertools import product
from pathlib import Path
from statistics import median

getcontext().prec = 32
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
D = lambda x: Decimal(str(x))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value, places=8):
    return None if value is None else float(value.quantize(D(10) ** -places))


def economic_outcomes(w, t, h, u, cpu_price, allocation, q_h, q_a, v):
    """All costs/effort are per attempt; q converts to modeled accepted output.

    None remains unknown. A zero acceptance probability has no finite expected
    accepted-output cost; it is never silently deleted or represented as zero.
    """
    if any(value is None for value in [w, t, h, u, cpu_price, allocation, q_h, q_a, v]):
        return {'status': 'UNKNOWN_INPUT', 'human_cost': None, 'alpha_cost': None,
                'cost_ratio': None, 'effort_capacity_ratio': None,
                'capacity_value': None, 'break_even_human_minutes': None}
    w, t, h, u, cpu_price, allocation, q_h, q_a, v = map(D, [w,t,h,u,cpu_price,allocation,q_h,q_a,v])
    if not (0 <= q_h <= 1 and 0 <= q_a <= 1):
        raise ValueError('Acceptance probabilities must be in [0,1].')
    if any(value < 0 for value in [t,h,u,cpu_price,allocation,v]) or w <= 0:
        raise ValueError('Nonnegative costs/effort and a positive hourly rate are required.')
    if q_h == 0 or q_a == 0:
        return {'status': 'NO_FINITE_ACCEPTED_COST', 'human_cost': None,
                'alpha_cost': None, 'cost_ratio': None, 'effort_capacity_ratio': None,
                'capacity_value': None, 'break_even_human_minutes': None}
    human = (w*t/60 + v)/q_h
    alpha = (w*h/60 + cpu_price*u/3600 + allocation)/q_a
    return {'status':'MODELED_FROM_MEASURED_CPU_AND_ASSUMPTIONS',
            'human_cost':human, 'alpha_cost':alpha,
            'cost_ratio':human/alpha if alpha > 0 else None,
            'effort_capacity_ratio':t*q_a/(h*q_h) if h > 0 else None,
            'capacity_value':human-alpha,
            'break_even_human_minutes':60*(q_h*alpha-v)/w}


def display(outcomes):
    return {key:(number(value) if isinstance(value, Decimal) else value)
            for key,value in outcomes.items()}


def main():
    source_file = BASE/'raw/primary/results.json'
    rates_file = BASE/'economics/human_market_benchmarks.json'
    freeze_file = BASE/'protocol/FREEZE.json'
    raw = json.loads(source_file.read_text(), parse_float=Decimal)
    rates = json.loads(rates_file.read_text(), parse_float=Decimal)['rates']
    freeze = json.loads(freeze_file.read_text())
    mismatches = [row['path'] for row in freeze['files']
                  if digest(BASE/row['path']) != row['sha256']]
    if mismatches:
        raise ValueError('Frozen inputs changed: '+repr(mismatches))
    receipts = raw['records']
    accepted = sum(r.get('accepted') is True for r in receipts)
    cpu = [D(r['total_cpu_seconds']) for r in receipts if r.get('total_cpu_seconds') is not None]
    if not cpu or len(cpu) != len(receipts):
        raise ValueError('Missing CPU receipts: do not silently price a successful subset.')
    u_min, u_med, u_max = min(cpu), median(cpu), max(cpu)
    cpu_sum = sum(cpu,D(0))
    observed = {
        'primary_attempts':len(receipts), 'machine_accepted':accepted,
        'machine_rejected_or_not_accepted':len(receipts)-accepted,
        'observed_acceptance_fraction':accepted/len(receipts) if receipts else None,
        'acceptance_scope':sorted(set(r['acceptance_scope'] for r in receipts)),
        'cpu_scope':sorted(set(r['cpu_scope'] for r in receipts)),
        'cpu_seconds_min':number(u_min), 'cpu_seconds_median':number(u_med),
        'cpu_seconds_mean':number(cpu_sum/len(cpu)), 'cpu_seconds_max':number(u_max),
        'cpu_seconds_total_all_attempts':number(cpu_sum),
        'cpu_seconds_total_per_accepted':number(cpu_sum/accepted) if accepted else None,
        'operational_model_calls':sum(r.get('model_calls',0) for r in receipts),
        'human_timing_status':'NOT_RUN',
        'actual_host_invoice':None, 'actual_human_attention_minutes':None,
        'actual_investment_allocation':None, 'actual_maintenance_allocation':None,
        'actual_fully_allocated_cost':None,
        'scope_note':'Primary local reused workflow only. Machine acceptance is not customer or independent human acceptance. Receipt CPU excludes final serialization tail, host idle time and development/construction. Operational zero model calls do not make construction free.'
    }
    assumptions = {
        'publication_status':'POSTFREEZE_ECONOMIC_PRESENTATION',
        'traditional_minutes_per_attempt':[5,15,30,60],
        'residual_human_minutes_per_attempt':[1,5,15],
        'allocation_per_attempt_own_currency':[0.10,1,5,20],
        'cpu_price_per_cpu_hour_own_currency':[0.1,1,5],
        'human_acceptance_probability':[0.8,0.95,1],
        'alpha_acceptance_probability':[0.8,0.95,1],
        'wage_only_employer_load_multiplier':[1,1.25,1.5],
        'total_compensation_or_employer_cost_load_multiplier':[1],
        'traditional_nonlabor_cost_v_per_attempt':0,
        'v_status':'ASSUMED_ZERO_FOR_LABOR_COST_REFERENCE; actual nonlabor cost is unknown, not measured zero',
        'allocation_scope':'Assumed maintenance, amortized construction and all otherwise unpriced non-attention overhead per attempt. F/N_attempts is a possible investment allocation. Do not insert F/N_accepted here and divide by q again.',
        'time_scope':'Assumed per-attempt effort includes its ordinary preparation, review and within-attempt correction. Separate rejected attempts are represented by q; do not count the same rework in t and q twice.',
        'cpu_statistic_for_scenarios':'Observed primary median; observed min/max are a resource-range sensitivity, not confidence bounds. Aggregate campaign resource cost uses sum/accepted, not median.',
        'currency_policy':'Each source currency is calculated independently. Equal numeric CAD, USD and EUR assumptions do not assert exchange equivalence; no additional FX conversion.',
        'acceptance_policy':'Scenario q values are sensitivity assumptions, not confidence limits or matched observed human reliability. Observed 36/36 applies only to frozen machine checks.',
        'capacity_policy':'Effort capacity ratio compares accepted outputs per employer-attention hour under assumptions. It is not measured throughput, headcount reduction, cash savings or profit.'
    }
    provenance = {'primary_results_sha256':digest(source_file),
                  'source_rates_sha256':digest(rates_file),
                  'freeze_manifest_sha256':digest(freeze_file),
                  'frozen_files_checked':len(freeze['files']),
                  'frozen_file_hash_mismatches':mismatches}
    scenarios = [("equal_effort_loss",5,5,1),("moderate_workflow",15,5,1),
                 ("longer_workflow",30,5,1),("low_attention_long_workflow",60,1,1),
                 ("heavy_review_weak_advantage",30,15,5),("short_workflow_heavy_review_loss",5,15,5)]
    main_rows=[]
    w=D('35.96')
    for name,t,h,allocation in scenarios:
        result=economic_outcomes(w,t,h,u_med,1,allocation,1,1,0)
        row={'id':name,'rate_id':'us_office_admin_compensation','currency':'USD',
             'published_total_compensation_per_hour':35.96,'employer_load':1,
             'human_minutes_assumed':t,'alpha_attention_minutes_assumed':h,
             'allocation_per_attempt_assumed':allocation,'cpu_price_assumed':1,
             'human_q_assumed':1,'alpha_q_assumed':1,'v_assumed':0,
             **display(result)}
        row['alpha_cost_cpu_min']=number(economic_outcomes(w,t,h,u_min,1,allocation,1,1,0)['alpha_cost'])
        row['alpha_cost_cpu_mean']=number(economic_outcomes(w,t,h,cpu_sum/len(cpu),1,allocation,1,1,0)['alpha_cost'])
        row['alpha_cost_cpu_max']=number(economic_outcomes(w,t,h,u_max,1,allocation,1,1,0)['alpha_cost'])
        main_rows.append(row)
    rate_rows=[]
    grid_summary=[]
    sensitivity_slices=[]
    for rate in rates:
        loads=[1,D('1.25'),D('1.5')] if rate['cost_basis']=='wage_only' else [1]
        for load in loads:
            wage=D(rate['rate_per_hour'])*D(load)
            reference=economic_outcomes(wage,30,5,u_med,1,1,1,1,0)
            rate_rows.append({'rate_id':rate['id'],'geography':rate['geography'],
                              'occupation':rate['occupation'],'reference_period':rate['reference_period'],
                              'currency':rate['currency'],'source_cost_basis':rate['cost_basis'],
                              'source_rate_per_hour':float(rate['rate_per_hour']),
                              'employer_load_assumed':float(load),'valuation_rate':number(wage),
                              'source_url':rate['source_url'],'source_key':rate['source_key'],
                              'source_refs':rate['source_refs'],
                              'scenario':'t=30,h=5,allocation=1,cpu_price=1,qH=qA=1,v=0; all assumed except measured CPU',
                              **display(reference)})
            positive=negative=equal=count=0
            min_value=max_value=min_ratio=max_ratio=None
            for t,h,allocation,price,q_h,q_a in product([5,15,30,60],[1,5,15],
                                                      [D('.10'),1,5,20],[D('.1'),1,5],
                                                      [D('.8'),D('.95'),1],[D('.8'),D('.95'),1]):
                r=economic_outcomes(wage,t,h,u_med,price,allocation,q_h,q_a,0)
                value,ratio=r['capacity_value'],r['cost_ratio']; count+=1
                positive+=value>0; negative+=value<0; equal+=value==0
                min_value=value if min_value is None else min(min_value,value)
                max_value=value if max_value is None else max(max_value,value)
                min_ratio=ratio if min_ratio is None else min(min_ratio,ratio)
                max_ratio=ratio if max_ratio is None else max(max_ratio,ratio)
            grid_summary.append({'rate_id':rate['id'],'employer_load':float(load),
                                 'currency':rate['currency'],'combinations':count,
                                 'modeled_advantage_cases':positive,'modeled_disadvantage_cases':negative,
                                 'equal_cost_cases':equal,'capacity_value_min':number(min_value),
                                 'capacity_value_max':number(max_value),'cost_ratio_min':number(min_ratio),
                                 'cost_ratio_max':number(max_ratio),
                                 'interpretation':'Unweighted sensitivity grid, not probability, expected market performance or estimated success frequency.'})
    for q_h,q_a in product([D('.8'),D('.95'),1],repeat=2):
        sensitivity_slices.append({'slice':'reliability','qH_assumed':float(q_h),'qA_assumed':float(q_a),
                                  **display(economic_outcomes(w,30,5,u_med,1,1,q_h,q_a,0))})
    for price,u_label in product([D('.1'),1,5],['min','median','max']):
        u={'min':u_min,'median':u_med,'max':u_max}[u_label]
        sensitivity_slices.append({'slice':'cpu_resource_and_price','cpu_statistic':u_label,
                                  'cpu_seconds_measured':number(u),'cpu_price_assumed':float(price),
                                  **display(economic_outcomes(w,30,5,u,price,1,1,1,0))})
    # The zero-q and unknown-input edges must never produce a fictional zero cost.
    edges={'zero_alpha_acceptance':display(economic_outcomes(w,30,5,u_med,1,1,1,0,0)),
           'zero_human_acceptance':display(economic_outcomes(w,30,5,u_med,1,1,0,1,0)),
           'unknown_allocation':display(economic_outcomes(w,30,5,u_med,1,None,1,1,0))}
    resource_prices=[{'assumed_price_per_cpu_hour_own_currency':float(price),
                      'modeled_cpu_cost_at_measured_min':number(price*u_min/3600,10),
                      'modeled_cpu_cost_at_measured_median':number(price*u_med/3600,10),
                      'modeled_cpu_cost_at_measured_max':number(price*u_max/3600,10),
                      'modeled_campaign_cpu_cost_all_attempts':number(price*cpu_sum/3600,10),
                      'modeled_campaign_cpu_cost_per_accepted':number(price*cpu_sum/(3600*accepted),10) if accepted else None,
                      'label':'ASSUMED_TARIFF_TIMES_OBSERVED_CPU; NOT_AN_INVOICE_OR_COMPLETE_COST'}
                     for price in [D('.1'),D(1),D(5)]]
    output={'status':'MODELED_ECONOMICS_WITH_MEASURED_RESOURCE_COMPONENT',
            'formulas':{'human':'C_H=(w*t/60+v)/qH',
                        'alpha':'C_A=(w*h/60+p_cpu*u/3600+k)/qA',
                        'break_even_human_minutes':'60*(qH*C_A-v)/w',
                        'effort_capacity_ratio':'(t/qH)/(h/qA)',
                        'cost_ratio':'C_H/C_A','potential_capacity_value':'C_H-C_A'},
            'provenance':provenance,'observed_primary_resources':observed,'assumptions':assumptions,
            'resource_pricing_sensitivity':resource_prices,
            'main_us_office_scenarios':main_rows,'geographic_reference_scenarios':rate_rows,
            'grid_summary':grid_summary,'grid_combination_count':sum(r['combinations'] for r in grid_summary),
            'sensitivity_slices_us_reference':sensitivity_slices,'edge_handling':edges,
            'actual_complete_cost_ratio':None,'actual_cash_savings':None,'provider_margin':None}
    (HERE/'measured_resource_economics.json').write_text(json.dumps(output,indent=2)+'\n')
    table=['# Postfreeze economic scenarios using measured CPU', '',
           'All workflow times, acceptance probabilities and prices below are assumptions. CPU is measured from the frozen 36-job primary campaign. U.S. office/admin total compensation: USD35.96/hour; qH=qA=1; CPU price USD1/CPU-hour; traditional nonlabor cost v=0 assumed.', '',
           '| Scenario | Human min | Alpha attention min | Allocation USD | Human cost/accepted | Alpha cost/accepted | Break-even human min | Effort capacity ratio | Cost ratio | Potential capacity value USD |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in main_rows:
        table.append(f"| {r['id']} | {r['human_minutes_assumed']} | {r['alpha_attention_minutes_assumed']} | {r['allocation_per_attempt_assumed']:.2f} | {r['human_cost']:.2f} | {r['alpha_cost']:.2f} | {r['break_even_human_minutes']:.2f} | {r['effort_capacity_ratio']:.2f} | {r['cost_ratio']:.2f} | {r['capacity_value']:.2f} |")
    table += ['',f"Observed CPU median {number(u_med,6):.6f}s; range {number(u_min,6):.6f}–{number(u_max,6):.6f}s; mean {number(cpu_sum/len(cpu),6):.6f}s. Median-priced CPU component at USD1/CPU-hour: USD{number(u_med/3600,10):.10f} per attempt. Complete actual cost remains unknown.", '',
              'Effort capacity is a conditional attention-budget ratio, not observed throughput. Potential capacity value is not realized cash saving. Source: frozen BLS ECEC December 2025 rate and primary CPU receipts; assumptions are the postfreeze presentation model.']
    (HERE/'SCENARIO_TABLE.md').write_text('\n'.join(table)+'\n')
    validation={'status':'PASS','frozen_file_hashes_verified':len(freeze['files']),
                'primary_receipts_included':len(receipts),'primary_receipts_with_missing_cpu':len(receipts)-len(cpu),
                'observed_failed_attempts':len(receipts)-accepted,
                'main_scenario_rows':len(main_rows),'geographic_loaded_cases':len(rate_rows),
                'grid_combinations':output['grid_combination_count'],
                'grid_advantage_cases':sum(r['modeled_advantage_cases'] for r in grid_summary),
                'grid_disadvantage_cases':sum(r['modeled_disadvantage_cases'] for r in grid_summary),
                'unknown_and_zero_acceptance_preserved':all(e['alpha_cost'] is None for e in edges.values()),
                'actual_complete_cost_ratio_is_null':output['actual_complete_cost_ratio'] is None,
                'postfreeze_status_explicit':True}
    (HERE/'MODEL_VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation,indent=2))
    print('\n'.join(table))


if __name__=='__main__':
    main()
