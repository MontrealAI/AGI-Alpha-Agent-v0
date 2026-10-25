# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import datetime,hashlib,json,os,platform,resource,subprocess,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'extracted/SUCCESSOR_Omega_Strategy_Lab_v0.1.0'
PY=Path('/tmp/strategy-replay-python/cpython-3.13.5-linux-x86_64-gnu/bin/python3.13')
COMMAND=[str(PY),'-m','omega','verify','--workspace','evidence/example','--replay']
record={'schema':'historical-exact-replay/v1','original_zip_sha256':'c0df2ac39ddcb32de672db93d05df77b8d8f683966cb92469ab00bf2060284a1','start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':COMMAND,'runtime':subprocess.check_output([str(PY),'--version'],text=True).strip(),'runtime_executable_sha256':hashlib.sha256(PY.read_bytes()).hexdigest(),'source_modified':False,'runtime_guard_bypassed':False,'timeout_seconds':900,'status':'RUNNING','independence':'Fresh execution of original implementation on current host, not independent institutional replication.'}
(HERE/'EXECUTION.json').write_text(json.dumps(record,indent=2)+'\n')
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
start=time.perf_counter();before=resource.getrusage(resource.RUSAGE_CHILDREN)
with (HERE/'replay.log').open('w') as log:
 try: run=subprocess.run(COMMAND,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900);record['exit_code']=run.returncode
 except subprocess.TimeoutExpired:record['exit_code']=None;record['timeout']=True
after=resource.getrusage(resource.RUSAGE_CHILDREN)
record.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.perf_counter()-start,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
log=(HERE/'replay.log').read_text();record['log_sha256']=hashlib.sha256(log.encode()).hexdigest();offset=log.find('{\n')
if offset>=0:
 try:record['verdict']=json.loads(log[offset:])
 except json.JSONDecodeError:record['verdict']=None
record['status']='PASS' if record.get('exit_code')==0 and record.get('verdict',{}).get('replay')=='PASS' else 'FAILED'
(HERE/'EXECUTION.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
