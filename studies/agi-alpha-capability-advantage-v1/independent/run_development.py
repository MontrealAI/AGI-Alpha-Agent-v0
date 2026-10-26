"""Record all outcomes for allowed development/discovery and independent stress."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent.parent
OWN = ROOT/'independent'
sys.path.insert(0, str(ROOT/'workloads'))
sys.path.insert(0, str(OWN))
from workload_generator import build_chain, materialize_design, canonical, PROFILES
from verifier import verify
from solver import solve

def utc():
    return datetime.now(timezone.utc).isoformat()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--stress', action='store_true')
    args = parser.parse_args()
    path = OWN/'attempts'/args.attempt
    path.mkdir(parents=True, exist_ok=False)
    source = (OWN/'solver.py').read_bytes()
    (path/'solver.py').write_bytes(source)
    record = {'attempt':args.attempt,'start_utc':utc(),'solver_sha256':hashlib.sha256(source).hexdigest(),
              'scope':'independently selected development; no primary cases or sealed seeds',
              'time_interpretation':'elapsed wall clock; not human attention, inference bill, or monetary cost',
              'results':[]}
    (path/'record.json').write_bytes(canonical(record)+b'\n')
    cases=[]
    for split in ['development','discovery']:
        for task_path in sorted((ROOT/'workloads'/split/'tasks').glob('*-FORWARD.json')):
            prefix=task_path.name[:-len('FORWARD.json')]
            chain=[]
            for family in ['FORWARD','INVERSE','DESIGN']:
                t=json.loads((task_path.parent/(prefix+family+'.json')).read_text())
                o=json.loads((ROOT/'workloads'/split/'oracles'/(prefix+family+'.json')).read_text())
                chain.append((t,o))
            cases.append(chain)
    if args.stress:
        for i, profile in enumerate(PROFILES):
            # Deliberately chosen public integers; never derived from primary seeds.
            cases.append(build_chain(2400260+i, profile, 'independent-stress', f'IND-STRESS-{i+1:02d}'))
    for chain in cases:
        parent_task=parent_result=parent_acceptance=None
        for task,oracle in chain:
            casepath=path/task['id']
            casepath.mkdir()
            (casepath/'template.json').write_bytes(canonical(task)+b'\n')
            (casepath/'oracle.json').write_bytes(canonical(oracle)+b'\n')
            entry={'task_id':task['id'],'family':task['family'],'nodes':task['network']['node_count'],
                   'start_utc':utc()}
            begin=time.perf_counter()
            try:
                if task['family']=='design' and 'lineage' in task:
                    task=materialize_design(task,parent_task,parent_result,parent_acceptance)
                (casepath/'task.json').write_bytes(canonical(task)+b'\n')
                started=time.perf_counter()
                result=solve(task)
                entry['solver_wall_seconds']=time.perf_counter()-started
                (casepath/'result.json').write_bytes(canonical(result)+b'\n')
                started=time.perf_counter()
                acceptance=verify(task,result,oracle,parent_task=parent_task,parent_result=parent_result)
                entry['verification_wall_seconds']=time.perf_counter()-started
                (casepath/'acceptance.json').write_bytes(canonical(acceptance)+b'\n')
                entry.update(accepted=acceptance['accepted'],status=result.get('status'),
                             diagnostics=result.get('diagnostics',{}),acceptance=acceptance)
                if task['family']=='inverse':
                    parent_task,parent_result,parent_acceptance=task,result,acceptance
            except Exception as error:
                entry.update(accepted=False,status='exception',error=str(error),traceback=traceback.format_exc())
            entry.update(end_utc=utc(),task_wall_seconds=time.perf_counter()-begin)
            record['results'].append(entry)
            (path/'record.json').write_bytes(canonical(record)+b'\n')
            print(json.dumps({k:entry.get(k) for k in ['task_id','nodes','status','accepted','solver_wall_seconds','verification_wall_seconds','diagnostics','error']}),flush=True)
    record.update(end_utc=utc(),accepted=sum(r['accepted'] for r in record['results']),total=len(record['results']))
    (path/'record.json').write_bytes(canonical(record)+b'\n')
    print(json.dumps({k:record[k] for k in ['attempt','accepted','total','start_utc','end_utc','solver_sha256']}),flush=True)

if __name__=='__main__':
    main()
