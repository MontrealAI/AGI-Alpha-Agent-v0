# SPDX-License-Identifier: Apache-2.0
import argparse, datetime, hashlib, json, os, resource, subprocess, time
from pathlib import Path

p=argparse.ArgumentParser(); p.add_argument('--out',required=True); p.add_argument('cmd',nargs=argparse.REMAINDER); a=p.parse_args()
out=Path(a.out); out.mkdir(parents=True,exist_ok=False)
cmd=a.cmd[1:] if a.cmd and a.cmd[0]=='--' else a.cmd
start=datetime.datetime.now(datetime.timezone.utc).isoformat(); w=time.perf_counter(); self0=time.process_time(); c0=resource.getrusage(resource.RUSAGE_CHILDREN)
with (out/'stdout.txt').open('w') as so,(out/'stderr.txt').open('w') as se:
    proc=subprocess.run(cmd,stdout=so,stderr=se,check=False)
c1=resource.getrusage(resource.RUSAGE_CHILDREN)
r={'schema':'second-investment-resource-receipt/v1','started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'cwd':os.getcwd(),'exit_code':proc.returncode,'wall_seconds':time.perf_counter()-w,'self_cpu_seconds':time.process_time()-self0,'child_cpu_seconds':(c1.ru_utime+c1.ru_stime)-(c0.ru_utime+c0.ru_stime),'peak_child_rss_kib':c1.ru_maxrss,'scope':'inclusive command resources; do not add nested receipts','active_human_minutes':None,'model_authoring_invoice_usd':None,'new_paid_commitment_usd':0,'outputs':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['stdout.txt','stderr.txt']}}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(proc.returncode)
