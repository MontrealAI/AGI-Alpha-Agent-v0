# SPDX-License-Identifier: Apache-2.0
import argparse, concurrent.futures, hashlib, json, pathlib, sys
from datetime import datetime,timezone
import numpy as np
from economy_v3 import HERE, load_inputs, run_scenario, sha, dumps

def worker(args):
    c,r,name,worlds,seed,out=args
    return name,run_scenario(c,r,name,worlds,seed,out)

def verify(out,c,r):
    freeze=json.loads((out/'freeze.json').read_text());assert freeze['configuration_sha256']==sha(c);assert freeze['workflow_costs_sha256']==sha(r)
    for path,h in freeze['closure_sha256'].items():assert hashlib.sha256((HERE.parent/path).read_bytes()).hexdigest()==h,path
    return freeze

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(HERE.parent/'results/paid_work_final'));p.add_argument('--worlds',type=int,default=500);p.add_argument('--workers',type=int,default=3);a=p.parse_args();out=pathlib.Path(a.output);c,r=load_inputs(HERE/'config_v3.json');freeze=verify(out,c,r);started=datetime.now(timezone.utc).isoformat();summaries={}
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(worker,(c,r,name,a.worlds,c['test_seed'],str(out))) for name in c['scenarios']]
        for future in concurrent.futures.as_completed(futures):
            name,s= future.result();summaries[name]=s;print(dumps({'completed_scenario':name,'worlds':a.worlds,'network_incremental_profit':s['paired']['network_incremental_profit'],'retention_probability':s['policies']['optimized_network']['probability_retention']}),flush=True)
    verify(out,c,r);result={'status':'Frozen independent confirmation','config_sha256':sha(c),'workflow_costs_sha256':sha(r),'seed':c['test_seed'],'worlds_per_scenario':a.worlds,'scenarios':{n:summaries[n] for n in c['scenarios']},'sampling_unit':c['scope']['sampling_unit']};(out/'summary.json').write_text(dumps(result,indent=2));(out/'run_manifest.json').write_text(dumps({'started_at_utc':started,'completed_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'numpy':np.__version__,'seed':c['test_seed'],'worlds_per_scenario':a.worlds,'policy_count':4,'phase':'confirm','configuration_sha256':sha(c),'freeze_timestamp':freeze['frozen_at_utc']},indent=2))
if __name__=='__main__':main()
