# SPDX-License-Identifier: Apache-2.0
import argparse, datetime, hashlib, json, os, platform, resource, shutil, subprocess, sys, time, zipfile
from pathlib import Path
from reference_reconciliation import verify_all

BASE=Path(__file__).resolve().parents[1]

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def cpu():
    own=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime+own.ru_stime+children.ru_utime+children.ru_stime
def write(path,value): Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--out',required=True);p.add_argument('--parent');a=p.parse_args()
    started=time.perf_counter();c0=0.0;utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    task=Path(a.task).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    inp=json.loads((task/'input.json').read_text());brief=json.loads((task/'brief.json').read_text())
    stages=[];accepted=False;error=None;output=out/'output';parent=Path(a.parent).resolve() if a.parent else None
    env={k:v for k,v in os.environ.items() if k in {'PATH','SYSTEMROOT','WINDIR','TMPDIR'}}
    for name in ['input.json','left.csv','right.csv','brief.json']:shutil.copyfile(task/name,out/name)
    def command(name,args):
        t=time.perf_counter();c=cpu();left=30-(t-started)
        if left<=0:raise TimeoutError('Study job budget exhausted before '+name)
        r=subprocess.run(args,capture_output=True,text=True,timeout=left,env=env)
        stages.append({'stage':name,'wall_seconds':time.perf_counter()-t,'cpu_seconds':cpu()-c,'exit_code':r.returncode})
        (out/(name+'.stdout.txt')).write_text(r.stdout);(out/(name+'.stderr.txt')).write_text(r.stderr)
        if r.returncode:raise RuntimeError(name+' failed with exit '+str(r.returncode))
    try:
        node=shutil.which('node')
        if parent:
            command('retained_tool',[node,str(parent),str(task/'left.csv'),str(task/'right.csv'),inp['leftKey'],inp['rightKey'],str(output)])
        else:
            command('native_cli',[node,str(BASE/'upstream/examples/successor-alpha/cli.mjs'),'--left',str(task/'left.csv'),'--right',str(task/'right.csv'),'--left-key',inp['leftKey'],'--right-key',inp['rightKey'],'--out',str(output)])
        command('guide_package',[node,str(BASE/'src/supplement.mjs'),str(task/'input.json'),str(output),brief['id'],sha(parent) if parent else ''])
        t=time.perf_counter();c=cpu();audit=verify_all(inp,output)
        stages.append({'stage':'independent_acceptance','wall_seconds':time.perf_counter()-t,'cpu_seconds':cpu()-c,'checks':audit['checks']})
        write(out/'acceptance.json',audit);accepted=audit['accepted']
        t=time.perf_counter();c=cpu()
        manifest=[{'path':str(f.relative_to(output)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(output.rglob('*')) if f.is_file()]
        write(out/'OUTPUT_MANIFEST.json',manifest)
        with zipfile.ZipFile(out/'delivery.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for f in sorted(output.rglob('*')):
                if f.is_file():z.write(f,str(f.relative_to(output)))
            z.write(out/'acceptance.json','acceptance.json');z.write(out/'OUTPUT_MANIFEST.json','OUTPUT_MANIFEST.json')
        stages.append({'stage':'hash_and_package','wall_seconds':time.perf_counter()-t,'cpu_seconds':cpu()-c})
        if time.perf_counter()-started>30:accepted=False;error='Study deadline exceeded after verification'
    except BaseException as e:
        accepted=False;error=type(e).__name__+': '+str(e)
    receipt={'schema':'work-economics-job-receipt/v1','job_id':brief['id'],'context':brief['context'],'complexity':brief['complexity'],
        'started_utc':utc,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accepted':accepted,'error':error,
        'worker_wall_seconds':time.perf_counter()-started,'total_cpu_seconds':cpu()-c0,'stage_observations':stages,
        'cpu_scope':'worker process from startup plus completed child processes, through packaging; final receipt serialization tail excluded',
        'retained_tool_sha256':sha(parent) if parent else None,'retained_tool_created_sha256':sha(output/'successor-tool.mjs') if (output/'successor-tool.mjs').is_file() else None,
        'worker_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'child_maxrss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'model_calls':0,'model_tokens':0,'operational_model_cost':0,'operational_model_cost_currency':'USD',
        'compute_price':None,'human_active_minutes':None,'human_review_minutes':None,'maintenance_allocation':None,'construction_allocation':None,
        'fully_allocated_cost':None,'unplanned_operator_interventions':0,'intervention_count_scope':'batch orchestration; no human stopwatch observation',
        'acceptance_scope':'independent-role deterministic machine acceptance; no customer or human usability certification',
        'new_human_trial':'NOT_RUN','market_comparison':'MODELLED_WITH_SOURCED_BENCHMARKS','python':platform.python_version(),
        'state':'ACCEPTED_BY_FROZEN_MACHINE_CRITERIA' if accepted else 'FAILED','network':False,'settlement':'NOT_CONNECTED'}
    write(out/'receipt.json',receipt);print(json.dumps(receipt));return 0 if accepted else 1

if __name__=='__main__':sys.exit(main())
