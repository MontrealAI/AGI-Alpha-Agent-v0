# SPDX-License-Identifier: Apache-2.0
import argparse, concurrent.futures, datetime, hashlib, json, os, random, subprocess, sys, time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]

def run(task,out,parent=None):
    started=time.perf_counter();cmd=[sys.executable,str(BASE/'src/run_job.py'),'--task',str(task),'--out',str(out)]
    if parent:cmd += ['--parent',str(parent)]
    timeout_error=None
    try:
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=35)
    except subprocess.TimeoutExpired as error:
        timeout_error='Outer worker timeout after 35 seconds'
        result=subprocess.CompletedProcess(cmd,124,
            error.stdout.decode(errors='replace') if isinstance(error.stdout,bytes) else error.stdout or '',
            error.stderr.decode(errors='replace') if isinstance(error.stderr,bytes) else error.stderr or '')
    outer=time.perf_counter()-started
    out.mkdir(parents=True,exist_ok=True)
    brief=json.loads((task/'brief.json').read_text())
    if (out/'receipt.json').is_file():receipt=json.loads((out/'receipt.json').read_text())
    else:receipt={'job_id':brief['id'],'context':brief['context'],'complexity':brief['complexity'],
        'accepted':False,'error':timeout_error or result.stderr,'total_cpu_seconds':None,'state':'FAILED',
        'human_active_minutes':None,'fully_allocated_cost':None,'measurement_missing_reason':'worker receipt unavailable'}
    if timeout_error:receipt.update({'accepted':False,'error':timeout_error,'state':'FAILED'})
    receipt.update({'process_turnaround_seconds':outer,'process_exit_code':result.returncode})
    (out/'process.stdout.txt').write_text(result.stdout);(out/'process.stderr.txt').write_text(result.stderr)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['primary','scale'],required=True);p.add_argument('--tasks',required=True);p.add_argument('--out',required=True);p.add_argument('--parent');a=p.parse_args()
    tasks=Path(a.tasks).resolve();dest=Path(a.out).resolve();dest.mkdir(parents=True,exist_ok=False)
    order=json.loads((tasks/'TASKS.json').read_text())['jobs'];records=[];batches=[];parent=Path(a.parent).resolve() if a.parent else None
    if a.mode=='primary':
        for job_id in order:
            r=run(tasks/job_id,dest/job_id,parent);records.append(r)
            if parent is None and r['accepted']:parent=dest/job_id/'output/successor-tool.mjs'
            print(json.dumps({'job_id':job_id,'accepted':r['accepted'],'turnaround_seconds':r['process_turnaround_seconds']}),flush=True)
    else:
        if parent is None:raise ValueError('Scale requires exact previously retained tool')
        chosen=sorted(j for j in order if j.endswith('-01'))
        for rep in range(3):
            for concurrency in ([1,2,4],[4,1,2],[2,4,1])[rep]:
                batch=f'c{concurrency}-r{rep+1}';batch_dir=dest/batch;batch_dir.mkdir()
                start=time.perf_counter();jobs=chosen[:];random.Random(2026102502+rep).shuffle(jobs)
                results=[]
                def call(job):
                    t=time.perf_counter();r=run(tasks/job,batch_dir/job,parent)
                    r.update({'batch':batch,'concurrency':concurrency,'repeat':rep+1,'queue_wait_seconds':t-start,'submission_to_acceptance_seconds':time.perf_counter()-start})
                    (batch_dir/job/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');return r
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                    futures=[pool.submit(call,j) for j in jobs]
                    for f in concurrent.futures.as_completed(futures):results.append(f.result())
                elapsed=time.perf_counter()-start;accepted=sum(r['accepted'] for r in results)
                b={'batch':batch,'concurrency':concurrency,'repeat':rep+1,'jobs':len(jobs),'accepted':accepted,'wall_seconds':elapsed,
                   'accepted_per_minute':60*accepted/elapsed,'initial_queued_backlog':max(0,len(jobs)-concurrency),
                   'cpu_seconds':sum(r['total_cpu_seconds'] for r in results) if all(r['total_cpu_seconds'] is not None for r in results) else None,
                   'known_cpu_seconds_subtotal':sum(r['total_cpu_seconds'] for r in results if r['total_cpu_seconds'] is not None),
                   'cpu_measurement_missing_count':sum(r['total_cpu_seconds'] is None for r in results),
                   'scope':'finite independent local process queue on one shared host; not Fleet or a deployed service'}
                records.extend(sorted(results,key=lambda r:r['job_id']));batches.append(b);print(json.dumps(b),flush=True)
    (dest/'results.json').write_text(json.dumps({'mode':a.mode,'records':records,'batches':batches},indent=2)+'\n')
    return 0 if all(r['accepted'] for r in records) else 1

if __name__=='__main__':sys.exit(main())
