# SPDX-License-Identifier: Apache-2.0
import argparse, copy, json, pathlib
from economy import load_inputs, run_scenario, sha, write_csv, unit, resource_sum, scaled
HERE=pathlib.Path(__file__).resolve().parent

def recalculate(r):
    entries={s['id']:s for s in r['stages']}
    for k,v in r.items():
        if isinstance(v,dict) and 'astra_input' in v and 'resource_minutes' in v:entries[k]=v
    for x in entries.values():x['derived_usd']=unit(x,r)['usd']
    for campaign in r['investment_campaigns'].values():
        campaign['derived_budget_usd']=sum(entries[k]['derived_usd']*n for k,n in campaign['counts'].items())
        for key in ['astra_input','astra_output','terra_input','terra_output','container_sessions_16gb','resource_minutes']:campaign[key]=sum(entries[k][key]*n for k,n in campaign['counts'].items())

def design(c,r):
    out=[]
    def add(name,change,scenario='central',structural_off=False):
        cc=copy.deepcopy(c);rr=copy.deepcopy(r);change(cc,rr);recalculate(rr);out.append((name,scenario,cc,rr,structural_off))
    for h in [2800,4900,9604]:add(f'global_reference_{h}',lambda c,r,h=h:c['scenarios']['central'].update(human_reference=h))
    add('sparse_arrivals',lambda c,r:c['scenarios']['central'].update(arrivals_month=1))
    add('oversupply_arrivals_40',lambda c,r:c['scenarios']['central'].update(arrivals_month=40))
    def loose(c,r):c['operations']['monthly_workbench_minutes']*=20;c['operations']['monthly_token_quota']*=20
    add('capacity_loose_cost_only',loose,'favorable')
    add('strong_shared_error',lambda c,r:c['scenarios']['central'].update(shared_fault_probability=.20,shared_fault_miss=.60))
    def equal(c,r):c['scenarios']['favorable']['retained_component_correctness']=c['scenarios']['favorable']['reconstruction_correctness']
    add('retained_reliability_equals_reconstruction',equal,'favorable')
    add('all_recipients_equivalent',lambda c,r:c['scope'].update(existing_equivalent_R=1,existing_equivalent_V=1,partial_equivalent_probability=0),'favorable')
    add('workflow_quantity_x4',lambda c,r:c['scenarios']['central'].update(activity_quantity_multiplier=4))
    def build(c,r):
        for campaign in r['investment_campaigns'].values():campaign['counts']={k:n*2 for k,n in campaign['counts'].items()}
    add('campaign_activity_x2',build,'favorable')
    def validation(c,r):
        names={'independent_semantic_validation','certificate_checker_reconstruction','adversarial_harness_reconstruction','fresh_stress_and_holdout_execution'}
        entries=[s for s in r['stages'] if s['id'] in names]+[r['revalidation'],r['asset_evaluation_unit']]
        for e in entries:
            for key in ['astra_input','astra_output','terra_input','terra_output','container_sessions_16gb','tools_usd','other_usd','resource_minutes']:e[key]*=2
    add('validation_activity_x2',validation)
    add('authorization_80pct',lambda c,r:c['scenarios']['central'].update(collection_probability=.80))
    add('settlement_lag_two_months',lambda c,r:c['scenarios']['central'].update(collection_lag=2))
    add('structure_disabled',lambda c,r:None,'favorable',True)
    add('narrow_supported_scope',lambda c,r:c['scope'].update(supported_domain_fraction=.45))
    return out

def compact(s):
    p=s['policies']['optimized_optional'];b=s['policies']['optimized_no_assets'];paired=s['paired']
    return {'net_profit_mean':p['net_profit']['mean'],'net_profit_p05':p['net_profit']['p05'],'quality_adjusted_profit_mean':p['quality_adjusted_profit']['mean'],'true_projects_mean':p['true_accepted_projects']['mean'],'pooled_cost_per_true_project':p['pooled_fully_allocated_cost_per_true_project'],'pooled_material_error_fraction':p['pooled_material_error_fraction'],'price_fraction_mean':p['mean_price_fraction']['mean'] if p['mean_price_fraction'] else None,'probability_profit':p['probability_profit'],'probability_research':p['probability_research'],'research_repayment_probability':paired['probability_research_repaid'],'incremental_research_profit_mean':paired['optional_incremental_profit']['mean'],'price_policy_total_effect_mean':paired['price_policy_total_effect']['mean'],'no_asset_profit_mean':b['net_profit']['mean']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default=str(HERE/'config.json'));p.add_argument('--output',default=str(HERE.parent/'results/sensitivity'));p.add_argument('--worlds',type=int,default=200);p.add_argument('--freeze-design',action='store_true');p.add_argument('--require-frozen',action='store_true');a=p.parse_args();c,r=load_inputs(a.config);out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True);cases=design(c,r)
    manifest={'base_config_sha256':sha(c),'base_workflow_costs_sha256':sha(r),'worlds_per_case':a.worlds,'seed':c['test_seed']+101,'cases':[{'name':n,'scenario':s,'config_sha256':sha(cc),'workflow_costs_sha256':sha(rr),'structural_off':off} for n,s,cc,rr,off in cases],'status':'Prespecified sensitivity conditions; not retuned after confirmation.'}
    if a.freeze_design:(out/'design_freeze.json').write_text(json.dumps(manifest,indent=2));return
    if a.require_frozen:assert json.loads((out/'design_freeze.json').read_text())==manifest
    records=[];summaries={}
    for name,scenario,cc,rr,off in cases:
        s=run_scenario(cc,rr,scenario,a.worlds,manifest['seed'],structural_off=off);records.append({'name':name,'scenario':scenario,**compact(s)});summaries[name]=s;print(json.dumps(records[-1]),flush=True)
        write_csv(out/'results.csv',records);(out/'summary.json').write_text(json.dumps({'status':manifest['status'],'worlds_per_case':a.worlds,'records':records,'scenarios':summaries},indent=2))
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
