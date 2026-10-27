#!/usr/bin/env python3
"""Extract an illustrative trace from the prespecified first favorable world.
Reads retained outputs only. This postconfirmation exposition is not a new test.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists(): raise FileExistsError('Refusing to overwrite retained trace')
    path=args.results/'samples/favorable-network.json'
    r=json.loads(path.read_text())
    assert r['seed']==770001 and r['scenario']=='favorable' and r['arm']=='network'
    outcomes={x['job']:x for x in r['outcomes']}
    orders={x['job']:x for x in r['events'] if x['kind']=='order'}
    collections={int(x['key']):x for x in r['ledger'] if x['kind']=='collection'}
    candidates=sorted(r['retention_records'],key=lambda x:(x['week'],x['id']))
    campaign=next(x for x in candidates if any(outcomes.get(j,{}).get('useful') and j in collections for j in x['source_jobs']))
    skills=[s for s in r['skills'] if s['bundle_id']==campaign['id']]
    keys=[s['key'] for s in skills]
    creators={s['owner'] for s in skills}
    receiving=[x for x in orders.values() if x['owner'] not in creators and any(k in x['skills'] for k in keys)
               and outcomes.get(x['job'],{}).get('useful')]
    receiving.sort(key=lambda x:(outcomes[x['job']]['week'],x['week'],x['job']))
    first=receiving[0]
    admission=next(x for x in r['events'] if x['kind']=='alpha_assessment' and x['campaign']==campaign['id'])
    admitted=[x for x in r['events'] if x['kind']=='admit' and x['source_job'] in campaign['source_jobs'] and x['key'] in keys]
    first_admit=min(x['week'] for x in admitted)
    retirements=[x for x in r['events'] if x['kind'] in ('retire','revoke') and x.get('source_job') in campaign['source_jobs'] and x['key'] in keys]
    assert not any(x['week']<=first['week'] for x in retirements)
    packets=[x for x in r['ledger'] if x.get('key')==campaign['id']]
    initial=Counter()
    for x in packets:
        if x['kind']=='expense': initial[x['category']]+=x['amount_cents']
    upkeep=('skill_maintenance','skill_distribution','skill_revalidation','moving_beta_alpha_reassessment')
    b_categories={k:v for k,v in r['costs'].items() if k.startswith('retention_') or k in upkeep or k=='network_access_overhead'}
    later=next((x for x in candidates if x['week']>campaign['week'] and x['funding_basis']=='operating-surplus'),None)
    beta=json.loads((args.results/'samples/favorable-beta.json').read_text())
    result={
      'schema':'beyond-beta.illustrative-paid-job-trace/1','source_kind':'simulation-trace-extraction',
      'world':{'scenario':r['scenario'],'arm':r['arm'],'seed':r['seed']},
      'selection_rule':'Prespecified first favorable confirmation world; postconfirmation reporting selects its earliest retention with at least one source job useful and eventually collected, then earliest useful noncreator receiving completion.',
      'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'extractor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'A_sources':[{'order':orders[j],'outcome':outcomes[j],'collection':collections.get(j),
                    'collected_before_retention_decision':bool(j in collections and collections[j]['week']<=campaign['week'])}
                   for j in sorted(set(campaign['source_jobs']))],
      'B_retention':{'decision':campaign,'transactions':packets,'initial_expenses_USD':{k:v/100 for k,v in initial.items()},
                     'initial_total_paid_USD':sum(x.get('paid_cents',0) for x in packets)/100,
                     'A_cost_charged_again_USD':0},
      'C_optional_new_rd_USD':r['cost_books']['investment'],
      'validation_and_admission':{'event':admission,'admission_events':admitted,
        'status':'Simulated task validity and forecast-based Alpha admission; no frontier job execution or independent production validation.'},
      'earliest_useful_receiving_work':{'order':first,'outcome':outcomes[first['job']],
        'collection':collections.get(first['job']),
        'status_at_selection':{'admitted_week':first_admit,'selection_week':first['week'],
          'beta_id':admission['alpha']['decision']['beta_id'],'initial_revalidation_due_week':first_admit+12,
          'expiry_week':min(s['expiry'] for s in skills),'retirement_before_selection':False,
          'bundle_components':keys,'additional_components_reconstructed':first['missing'],
          'availability':'all authenticated direct agent members in the simulated network'},
        'feasibility_claim':'Useful modeled receiving work occurred. No frozen-state comparison of this exact job establishes that it was previously impossible.'},
      'ongoing_lifecycle':{'selected_skill_terminal_records':[{k:v for k,v in s.items() if k!='alpha_assessment'} for s in skills],
        'retirement_events':retirements,
        'beta_reassessments':[{'week':x['week'],'keys':x['keys'],'decision':x['alpha']['decision']} for x in r['events'] if x['kind']=='beta_reassessment' and any(k in x['keys'] for k in keys)],
        'whole_world_B_categories_USD':b_categories,'whole_world_B_total_USD':r['cost_books']['retention'],
        'whole_world_upkeep_revalidation_distribution_USD':sum(r['costs'].get(k,0) for k in upkeep),
        'allocation_limit':'Ongoing maintenance/distribution/revalidation ledger entries lack capsule identifiers. Their exact whole-world charges are shown; they are not falsely attributed solely to this capsule.'},
      'first_later_earned_cash_funded_retention':later,
      'world_context':{'network_profit_USD':r['profit'],'beta_profit_USD':beta['profit'],
        'network_minus_beta_profit_USD':round(r['profit']-beta['profit'],2),
        'whole_world_cost_books_USD':r['cost_books'],'same_job_in_beta_outcomes':any(x['job']==first['job'] for x in beta['outcomes'])},
      'limitations':['All jobs, receipts, validity labels, transfers and prices are simulated.',
        'The trace is illustrative, not an independent successful campaign or a new confirmation sample.',
        'Direct source-job cost excludes allocated common overhead and is not full historical job profit.',
        'A source invoice collected later did not finance the earlier retention decision; the recorded first campaign used seed or mixed funds.',
        'Forecast Alpha qualification is distinct from the realized within-model enterprise increment; the sampled network underperformed its Beta arm.',
        'The research exact mechanism witness and fixture graph are separate evidence objects; this simulated job did not execute that witness as a frontier-model invention.']}
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'trace':str(args.out),'campaign':campaign['id'],'source_jobs':campaign['source_jobs'],
                      'receiver_job':first['job'],'network_minus_beta_profit_USD':result['world_context']['network_minus_beta_profit_USD']}))


if __name__=='__main__': main()
