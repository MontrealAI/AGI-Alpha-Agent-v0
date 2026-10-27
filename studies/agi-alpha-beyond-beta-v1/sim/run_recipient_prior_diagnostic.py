# SPDX-License-Identifier: Apache-2.0
"""One fixed, post-confirmation prior sensitivity; frozen v3 remains unchanged."""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import economy_v3 as frozen
import economy_v3_posterior as extension
from stress_v3 import design

ROOT=frozen.HERE.parent
ARMS=('frozen_beta','frozen_network','posterior_coherent_network')
CASE='compound_static_beta_large_pool_recurrence'
WORLDS=100
SEED=951557


def inputs():
    c,r=frozen.load_inputs(frozen.HERE/'config_v3.json')
    name,scenario,cc,rr,_=next(x for x in design(c,r) if x[0]==CASE)
    source=json.loads((ROOT/'results/paid_work_sensitivity/design_freeze.json').read_text())
    expected=next(x for x in source['cases'] if x['name']==name)
    assert frozen.sha(cc)==expected['configuration_sha256']
    assert frozen.sha(rr)==expected['workflow_costs_sha256']
    return scenario,cc,rr


def verify(out):
    f=json.loads((out/'freeze.json').read_text())
    for path,h in f['closure_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
    scenario,c,r=inputs()
    assert frozen.sha(c)==f['configuration_sha256']
    assert frozen.sha(r)==f['workflow_costs_sha256']
    assert json.loads((out/'diagnostic_design.json').read_text())['worlds']==WORLDS
    return f,scenario,c,r


def freeze(out):
    scenario,c,r=inputs();out.mkdir(parents=True,exist_ok=True)
    prior=json.loads((ROOT/'results/paid_work_final/freeze.json').read_text())
    for path,h in prior['closure_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
    (out/'frozen_config.json').write_text(frozen.dumps(c,indent=2))
    (out/'frozen_workflow_costs.json').write_text(frozen.dumps(r,indent=2))
    design_record={'status':'POST-CONFIRMATION EXPLORATORY DECISION-PRIOR DIAGNOSTIC','case':CASE,'scenario':scenario,'worlds':WORLDS,'seed':SEED,'arms':list(ARMS),'matched_worlds':True,'prior_equivalent_cases':4,'paid_job_good_probability_basis':'declared reconstruction_correctness * declared retention_generalization_success','research_good_probability_basis':'declared asset_build_success','prior_correctness_mean':'pi * retained_component_correctness + (1-pi) * 0.65','actual_capability_cost_demand_tests_and_beta_unchanged':True,'quality_effect_multiplier_in_condition':c['network']['alpha_quality_effect_fraction'],'no_further_tuning':True,'historical_primary_config_sha256':prior['configuration_sha256']}
    (out/'diagnostic_design.json').write_text(frozen.dumps(design_record,indent=2))
    paths=list(prior['closure_sha256'])+['sim/economy_v3_posterior.py','sim/run_recipient_prior_diagnostic.py','sim/test_recipient_prior_diagnostic.py','sim/PRIOR_DIAGNOSTIC_PROTOCOL.md','results/paid_work_final/freeze.json','results/paid_work_sensitivity/design_freeze.json']+[str((out/name).relative_to(ROOT)) for name in ['frozen_config.json','frozen_workflow_costs.json','diagnostic_design.json']]
    manifest={'status':design_record['status'],'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'configuration_sha256':frozen.sha(c),'workflow_costs_sha256':frozen.sha(r),'worlds':WORLDS,'seed':SEED,'closure_sha256':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in dict.fromkeys(paths)}}
    (out/'freeze.json').write_text(frozen.dumps(manifest,indent=2));print(frozen.dumps(manifest,indent=2))


def worker(args):
    arm,scenario,c,r,out=args;module=extension if arm=='posterior_coherent_network' else frozen
    policy='optimized_beta' if arm=='frozen_beta' else 'optimized_network';rows=[]
    with gzip.open(out/f'{arm}_complete_records.jsonl.gz','wt',compresslevel=9) as stream:
        for world in range(WORLDS):
            common=frozen.initial_primitives(c,c['scenarios'][scenario],SEED,world)
            result=module.simulate(c,r,scenario,world,policy,SEED,common)
            record=asdict(result);record['diagnostic_arm']=arm
            stream.write(frozen.dumps(record)+'\n')
            rows.append({'world':world,'scenario':scenario,'diagnostic_arm':arm,'policy':policy,**result.metrics})
    frozen.write_csv(out/f'{arm}_worlds.csv',rows)
    return arm,rows


def arm_summary(rows):
    result={}
    for key in rows[0]:
        values=[x[key] for x in rows if isinstance(x.get(key),(int,float,np.generic)) and not isinstance(x.get(key),(bool,np.bool_))]
        if values and key!='world':result[key]=frozen.stats(values)
    total=lambda k:sum(x[k] for x in rows)
    accepted=total('true_accepted_projects');passed=total('validated_deliveries')
    result.update(worlds=len(rows),pooled_fully_allocated_cost_per_true_project=total('fully_allocated_cost_total')/accepted if accepted else None,pooled_material_error_fraction=total('false_passes')/passed if passed else None,probability_profit=sum(x['net_profit']>0 for x in rows)/len(rows),probability_retention=sum(x['retention_cost']>0 for x in rows)/len(rows),probability_retention_admission=sum(x['retention_admissions']>0 for x in rows)/len(rows),probability_retention_use=sum(x['retention_uses']>0 for x in rows)/len(rows),probability_useful_recipient_use=sum(x['retention_useful_fresh_projects']>0 for x in rows)/len(rows),probability_insolvency=sum(x['insolvent'] for x in rows)/len(rows))
    return result


def comparisons(arms):
    rows=[]
    for world in range(WORLDS):
        b=arms['frozen_beta'][world];n=arms['frozen_network'][world];p=arms['posterior_coherent_network'][world]
        r={'world':world}
        for label,target,base in [('frozen_network_vs_beta',n,b),('posterior_network_vs_beta',p,b),('posterior_vs_frozen_network',p,n)]:
            for key in ['net_profit','quality_adjusted_profit','true_accepted_projects','false_passes','fully_allocated_cost_total','retention_cost','delivery_tokens','research_tokens','delivery_workbench_minutes','research_workbench_minutes','delivery_container_minutes','research_container_minutes']:
                r[f'{label}_{key}']=target[key]-base[key]
        r['posterior_operating_funded_paid_job_feedback']=bool(p['retention_cost']>0 and p['investment_cost']==0 and p['operating_funded_true_paid_source_useful_projects']>0 and p['net_profit']>b['net_profit'] and p['quality_adjusted_profit']>b['quality_adjusted_profit'])
        rows.append(r)
    summary={key:frozen.stats([r[key] for r in rows]) for key in rows[0] if key not in ('world','posterior_operating_funded_paid_job_feedback')}
    for label in ['frozen_network_vs_beta','posterior_network_vs_beta','posterior_vs_frozen_network']:
        values=[r[label+'_net_profit'] for r in rows]
        summary[label+'_probability_positive']=sum(v>0 for v in values)/WORLDS
        summary[label+'_probability_negative']=sum(v<0 for v in values)/WORLDS
        summary[label+'_profit_mean_mc_standard_error']=float(np.std(values,ddof=1)/math.sqrt(WORLDS))
        summary[label+'_probability_quality_adjusted_positive']=sum(r[label+'_quality_adjusted_profit']>0 for r in rows)/WORLDS
    summary['probability_operating_funded_paid_job_feedback']=sum(r['posterior_operating_funded_paid_job_feedback'] for r in rows)/WORLDS
    return rows,summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(ROOT/'results/paid_work_prior_diagnostic'));p.add_argument('--freeze',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--workers',type=int,default=3);a=p.parse_args();out=Path(a.output).resolve()
    if a.freeze:freeze(out)
    if not a.run:return
    f,scenario,c,r=verify(out);started=datetime.now(timezone.utc).isoformat();arms={}
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(worker,(arm,scenario,c,r,out)) for arm in ARMS]
        for future in concurrent.futures.as_completed(futures):
            arm,rows=future.result();arms[arm]=rows;print(frozen.dumps({'completed_arm':arm,'worlds':len(rows)}),flush=True)
    verify(out);world_rows=[row for arm in ARMS for row in arms[arm]];frozen.write_csv(out/'worlds.csv',world_rows);paired_rows,paired_summary=comparisons(arms);frozen.write_csv(out/'paired_worlds.csv',paired_rows)
    summary={'status':'ONE POST-CONFIRMATION EXPLORATORY PRIOR DIAGNOSTIC; NOT PRIMARY CONFIRMATION OR EMPIRICAL CAPABILITY EVIDENCE','case':CASE,'scenario':scenario,'worlds':WORLDS,'seed':SEED,'arms':{arm:arm_summary(arms[arm]) for arm in ARMS},'paired':paired_summary,'configuration_sha256':frozen.sha(c),'workflow_costs_sha256':frozen.sha(r),'freeze_timestamp':f['frozen_at_utc'],'limitations':['Decision priors are uncalibrated assumptions; actual frontier capability and economic conditions were unchanged.','Useful-retention counts are capability-project pairs, not necessarily unique projects.','Profit differences are total-policy effects; they do not isolate the causal repayment of each individual asset.','The compound condition jointly assumes larger recipient pool, stronger recurrence, static Beta versions, larger capacity and scaled control cost.']}
    (out/'summary.json').write_text(frozen.dumps(summary,indent=2));(out/'run_manifest.json').write_text(frozen.dumps({'started_at_utc':started,'completed_at_utc':datetime.now(timezone.utc).isoformat(),'worlds':WORLDS,'seed':SEED,'history_count':WORLDS*len(ARMS),'freeze_timestamp':f['frozen_at_utc'],'configuration_sha256':frozen.sha(c),'workflow_costs_sha256':frozen.sha(r),'no_further_tuning':True},indent=2));print(frozen.dumps({'complete':True,'paired':paired_summary},indent=2))


if __name__=='__main__':main()
