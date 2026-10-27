# SPDX-License-Identifier: Apache-2.0
import argparse, concurrent.futures, json, pathlib
from datetime import datetime,timezone
from economy_v3 import HERE,load_inputs,sha,dumps,write_csv
from stress_v3 import design,run_case,compact

def worker(args):
    name,scenario,c,r,compound,worlds,seed,path=args
    summary=run_case(c,r,scenario,worlds,seed,path/f'{name}_worlds.csv');record={'name':name,'scenario':scenario,'compound':compound,**compact(summary)};(path/f'{name}_summary.json').write_text(dumps({'case':record,'summary':summary,'config_sha256':sha(c),'workflow_costs_sha256':sha(r)},indent=2));return name,record

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(HERE.parent/'results/paid_work_sensitivity'));p.add_argument('--worlds',type=int,default=200);p.add_argument('--workers',type=int,default=3);a=p.parse_args();out=pathlib.Path(a.output);c,r=load_inputs(HERE/'config_v3.json');cases=design(c,r);manifest=json.loads((out/'design_freeze.json').read_text());assert manifest['base_config_sha256']==sha(c) and manifest['base_workflow_costs_sha256']==sha(r) and manifest['worlds_per_case']==a.worlds
    for frozen,(name,scenario,cc,rr,compound) in zip(manifest['cases'],cases):assert frozen['name']==name and frozen['configuration_sha256']==sha(cc) and frozen['workflow_costs_sha256']==sha(rr)
    completed={};started=datetime.now(timezone.utc).isoformat()
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(worker,(name,scenario,cc,rr,compound,a.worlds,manifest['seed'],out)) for name,scenario,cc,rr,compound in cases]
        for future in concurrent.futures.as_completed(futures):
            name,record=future.result();completed[name]=record;write_csv(out/'results.csv',[completed[n] for n,_,_,_,_ in cases if n in completed]);print(dumps(record),flush=True)
    (out/'run_manifest.json').write_text(dumps({**manifest,'started_at_utc':started,'completed_at_utc':datetime.now(timezone.utc).isoformat()},indent=2))
if __name__=='__main__':main()
