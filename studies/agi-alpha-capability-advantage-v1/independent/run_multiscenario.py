"""Exercise genuine multi-scenario design using an accepted actual calibration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

ROOT=Path(__file__).resolve().parent.parent
OWN=ROOT/'independent'
sys.path.insert(0,str(ROOT/'workloads'))
sys.path.insert(0,str(OWN))
from workload_generator import canonical, materialize_design
from verifier import verify
from solver import Network, _factor, solve

path=OWN/'attempts'/'v001_multiscenario'
path.mkdir(exist_ok=False)
source=(OWN/'solver.py').read_bytes()
(path/'solver.py').write_bytes(source)
record={'start_utc':datetime.now(timezone.utc).isoformat(),
        'solver_sha256':hashlib.sha256(source).hexdigest(),
        'scope':'independently constructed multi-scenario branch exercise from accepted own calibration',
        'time_interpretation':'wall clock elapsed; not human attention or monetary cost',
        'results':[]}
for suffix in ['DISC-02','IND-STRESS-04']:
    origin=OWN/'attempts'/'v001_full'
    inverse=json.loads((origin/(suffix+'-INVERSE')/'task.json').read_text())
    result=json.loads((origin/(suffix+'-INVERSE')/'result.json').read_text())
    acceptance=json.loads((origin/(suffix+'-INVERSE')/'acceptance.json').read_text())
    template=json.loads((origin/(suffix+'-DESIGN')/'template.json').read_text())
    oracle=json.loads((origin/(suffix+'-DESIGN')/'oracle.json').read_text())
    calibrated=materialize_design(template,inverse,result,acceptance)
    net=Network(calibrated)
    states=_factor(net.matrix()).solve(net.loads)
    objectives=np.sum(net.loads*states,axis=0)
    # All loads begin at the same compliance. This scaling uses only the
    # accepted calibration, not oracle parameters or oracle states.
    scaled=net.loads*np.sqrt(np.max(objectives)/objectives)[None,:]
    template['loads']=scaled.T.tolist()
    template['id']=suffix+'-BALANCED-DESIGN'
    template['split']='independent-multiscenario-exercise'
    oracle['task_id']=template['id']
    oracle['task_sha256']=hashlib.sha256(canonical(template)).hexdigest()
    task=materialize_design(template,inverse,result,acceptance)
    casepath=path/task['id']
    casepath.mkdir()
    for name,value in [('template',template),('task',task),('oracle',oracle),
                       ('parent_task',inverse),('parent_result',result),('parent_acceptance',acceptance)]:
        (casepath/(name+'.json')).write_bytes(canonical(value)+b'\n')
    entry={'task_id':task['id'],'nodes':task['network']['node_count'],
           'start_utc':datetime.now(timezone.utc).isoformat()}
    try:
        start=time.perf_counter()
        outcome=solve(task)
        entry['solver_wall_seconds']=time.perf_counter()-start
        checked=verify(task,outcome,oracle,parent_task=inverse,parent_result=result)
        entry.update(accepted=checked['accepted'],diagnostics=outcome.get('diagnostics'),acceptance=checked)
        (casepath/'result.json').write_bytes(canonical(outcome)+b'\n')
        (casepath/'acceptance.json').write_bytes(canonical(checked)+b'\n')
    except Exception as error:
        entry.update(accepted=False,error=str(error),traceback=traceback.format_exc())
    entry['end_utc']=datetime.now(timezone.utc).isoformat()
    record['results'].append(entry)
    (path/'record.json').write_bytes(canonical(record)+b'\n')
    print(json.dumps({k:v for k,v in entry.items() if k!='acceptance'}),flush=True)
record['end_utc']=datetime.now(timezone.utc).isoformat()
record['accepted']=sum(entry['accepted'] for entry in record['results'])
record['total']=len(record['results'])
(path/'record.json').write_bytes(canonical(record)+b'\n')
