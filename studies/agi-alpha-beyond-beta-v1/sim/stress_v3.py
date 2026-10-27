# SPDX-License-Identifier: Apache-2.0
"""Prespecified sensitivity runs. Keep all scalar worlds; avoid duplicate full ledgers."""
import argparse, copy, json, pathlib
from economy_v3 import (load_inputs, initial_primitives, simulate, paired, summarize,
    Result, POLICIES, sha, dumps, write_csv)
HERE=pathlib.Path(__file__).resolve().parent

def recompute(register):
    from economy_v3 import cost_table
    table=cost_table(register)
    for collection in ['investment_campaigns','incremental_retention_options']:
        for budget in register[collection].values():
            budget['derived_budget_usd']=sum(table[k]['usd']*n for k,n in budget['counts'].items())
            for field in ['astra_input','astra_output','terra_input','terra_output','container_sessions_16gb','resource_minutes']:
                units={s['id']:s for s in register['stages']};units.update({k:v for k,v in register.items() if isinstance(v,dict) and 'astra_input' in v});budget[field]=sum(units[k][field]*n for k,n in budget['counts'].items())

def design(c,r):
    out=[]
    def add(name,change,scenario='favorable',compound=False):
        cc=copy.deepcopy(c);rr=copy.deepcopy(r);change(cc,rr);recompute(rr);out.append((name,scenario,cc,rr,compound))
    add('lower_reference_4900',lambda c,r:c['scenarios']['central'].update(human_reference=4900),'central')
    add('demand_downturn_one_arrival',lambda c,r:c['scenarios']['favorable'].update(arrivals_month=1,arrival_growth=0))
    add('zero_job_candidate_emergence',lambda c,r:c['paid_job_learning'].update(candidate_probability_given_scan=0))
    add('optional_research_disabled',lambda c,r:c['paid_job_learning'].update(optional_research_enabled=False))
    add('zero_alpha_mapping',lambda c,r:c['network'].update(alpha_activity_effect_fraction=0,alpha_quality_effect_fraction=0))
    add('cost_only_alpha',lambda c,r:c['network'].update(alpha_quality_effect_fraction=0))
    add('all_recipients_already_equivalent',lambda c,r:c['scope'].update(existing_equivalent_R=1,existing_equivalent_V=1,partial_equivalent_probability=0))
    add('free_ordinary_reuse_across_agents',lambda c,r:c['paid_job_learning'].update(free_ordinary_reuse_across_agents=True))
    add('static_beta',lambda c,r:c['network'].update(beta_epochs=c['network']['beta_epochs'][:1]))
    def rapid(c,r):
        c['network']['beta_epochs']=[{'month':m,'version':f'beta-fast-{i+1}','reconstruction_quantity_factor':.75**i,'public_equivalent_probability_per_month':.08} for i,m in enumerate([1,5,9,13,17,21])]
    add('rapid_beta_erosion',rapid)
    add('fortyeight_recipients_same_compute',lambda c,r:c['scope'].update(recipient_agents=48))
    add('specialized_routing_same_compute',lambda c,r:c['scope'].update(specialist_routing_fraction=1))
    add('concentrated_compatible_scope',lambda c,r:c['scope'].update(domain_weights=[.8,.05,.05,.05,.05]))
    def validation(c,r):
        names=['independent_semantic_validation','certificate_checker_reconstruction','adversarial_harness_reconstruction','fresh_stress_and_holdout_execution'];units=[s for s in r['stages'] if s['id'] in names]+[r[n] for n in ['revalidation','asset_evaluation_unit','beta_version_reevaluation']]
        for unit in units:
            for key in ['astra_input','astra_output','terra_input','terra_output','container_sessions_16gb','tools_usd','other_usd','resource_minutes']:unit[key]*=2
    add('validation_activity_double',validation)
    def retention(c,r):
        for budget in r['incremental_retention_options'].values():budget['counts']={k:n*2 for k,n in budget['counts'].items()}
    add('retention_activity_double',retention)
    add('strong_shared_errors',lambda c,r:c['scenarios']['central'].update(shared_fault_probability=.20,shared_fault_miss=.60),'central')
    add('authorization80_lag2',lambda c,r:c['scenarios']['central'].update(collection_probability=.80,collection_lag=2),'central',True)
    def loose(c,r):c['operations']['monthly_workbench_minutes']*=20;c['operations']['monthly_token_quota']*=20
    add('loose_capacity_cost_only',loose)
    def joint(c,r):
        c['network']['beta_epochs']=c['network']['beta_epochs'][:1];c['scope']['recipient_agents']=48;c['scenarios']['favorable'].update(arrivals_month=32,arrival_growth=0);c['operations']['monthly_workbench_minutes']*=4;c['operations']['monthly_token_quota']*=4;c['operations']['monthly_control_cost']*=4
    add('compound_static_beta_large_pool_recurrence',joint,compound=True)
    return out

def compact(summary):
    p=summary['policies']['optimized_network'];b=summary['policies']['optimized_beta'];q=summary['paired']
    return {'net_profit_mean':p['net_profit']['mean'],'net_profit_p05':p['net_profit']['p05'],'quality_adjusted_profit_mean':p['quality_adjusted_profit']['mean'],'true_projects_mean':p['true_accepted_projects']['mean'],'pooled_cost_per_true_project':p['pooled_fully_allocated_cost_per_true_project'],'pooled_material_error_fraction':p['pooled_material_error_fraction'],'probability_profit':p['probability_profit'],'probability_retention':p['probability_retention'],'probability_retention_admission':p['probability_retention_admission'],'probability_retention_use':p['probability_retention_use'],'network_incremental_profit_mean':q['network_incremental_profit']['mean'],'sharing_incremental_profit_mean':q['sharing_incremental_profit']['mean'],'probability_operating_funded_paid_job_feedback':q['probability_operating_funded_paid_job_feedback'],'beta_profit_mean':b['net_profit']['mean'],'mean_price_fraction':p['mean_price_fraction']['mean'] if p['mean_price_fraction'] else None}

FIELDS=['net_profit','quality_adjusted_profit','true_accepted_projects','validated_deliveries','false_passes','fully_allocated_cost_total','ledger_A_delivery_total','ledger_B_retention_total','ledger_C_optional_research_total','retention_cost','retention_attempts','retention_admissions','retention_uses','retention_useful_fresh_projects','retention_seed_funded','retention_operating_funded','operating_funded_true_paid_source_useful_projects','investment_cost','mean_price_fraction','insolvent']

def run_case(c,r,scenario,worlds,seed,path):
    results=[];comparisons=[];rows=[]
    for world in range(worlds):
        common=initial_primitives(c,c['scenarios'][scenario],seed,world);runs=[simulate(c,r,scenario,world,p,seed,common) for p in POLICIES];comparison=paired(*runs);comparisons.append(comparison)
        for run in runs:
            results.append(Result(run.world,run.scenario,run.policy,run.metrics,[],[],{},{}));rows.append({'world':world,'scenario':scenario,'policy':run.policy,**{k:run.metrics[k] for k in FIELDS},**(comparison if run.policy=='optimized_network' else {})})
    write_csv(path,rows);return summarize(results,comparisons)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(HERE.parent/'results/paid_work_sensitivity'));p.add_argument('--worlds',type=int,default=200);p.add_argument('--freeze-design',action='store_true');p.add_argument('--require-frozen',action='store_true');p.add_argument('--case');a=p.parse_args();c,r=load_inputs(HERE/'config_v3.json');out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True);cases=design(c,r);seed=c['test_seed']+101
    manifest={'base_config_sha256':sha(c),'base_workflow_costs_sha256':sha(r),'worlds_per_case':a.worlds,'seed':seed,'cases':[{'name':n,'scenario':s,'configuration_sha256':sha(cc),'workflow_costs_sha256':sha(rr),'compound':compound} for n,s,cc,rr,compound in cases],'status':'Prespecified sensitivity. Compound conditions are exploratory; no selection or primary retuning.'}
    if a.freeze_design:(out/'design_freeze.json').write_text(dumps(manifest,indent=2));return
    if a.require_frozen:assert json.loads((out/'design_freeze.json').read_text())==manifest
    records=[]
    for name,scenario,cc,rr,compound in cases:
        if a.case and a.case!=name:continue
        summary=run_case(cc,rr,scenario,a.worlds,seed,out/f'{name}_worlds.csv');record={'name':name,'scenario':scenario,'compound':compound,**compact(summary)};records.append(record);(out/f'{name}_summary.json').write_text(dumps({'case':record,'summary':summary,'config_sha256':sha(cc),'workflow_costs_sha256':sha(rr)},indent=2));print(dumps(record),flush=True)
        if not a.case:write_csv(out/'results.csv',records)
    if not a.case:(out/'run_manifest.json').write_text(dumps(manifest,indent=2))
if __name__=='__main__':main()
