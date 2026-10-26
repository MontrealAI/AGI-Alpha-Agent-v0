# SPDX-License-Identifier: Apache-2.0
import argparse, datetime, hashlib, json, resource, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze_ok():
    freeze=json.loads((ROOT/'protocol/production-freeze.json').read_text())
    for item in freeze['files']:
        if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('FROZEN_SOURCE_CHANGED:'+item['path'])
    return digest(ROOT/'protocol/production-freeze.json')
def invoke(cmd,out):
    with (out/'driver.stdout.txt').open('a') as so,(out/'driver.stderr.txt').open('a') as se:
        try:return subprocess.run(cmd,cwd=ROOT,stdout=so,stderr=se,timeout=120,check=False).returncode
        except subprocess.TimeoutExpired:
            se.write('FROZEN_INVOCATION_TIMEOUT; no retry\n');return 124
def read_result(path):
    if not path.is_file():return {}
    try:return json.loads(path.read_text())
    except (ValueError,OSError) as error:return {'read_error':str(error)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--phase',choices=['fresh-confirmation','reproduction'],required=True);a=p.parse_args()
    out=(ROOT/a.out).resolve()
    if not out.is_relative_to(ROOT):raise ValueError('STUDY_OUTPUT_REQUIRED')
    out.mkdir(parents=True,exist_ok=False);freeze_hash=freeze_ok()
    manifest_path=ROOT/'protocol/confirmation-jobs.json';manifest=json.loads(manifest_path.read_text())
    rows=[];orders=[['A','B','C'],['B','C','A'],['C','A','B']]
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def checkpoint(current=None):
        state={'schema':'agi-alpha-second-investment-confirmation/v1','phase':a.phase,'partial':True,'started_at':started,'source_freeze_sha256':freeze_hash,'job_manifest_sha256':digest(manifest_path),'questions':len(manifest['jobs']),'expected_arm_evaluations':3*len(manifest['jobs']),'new_customer_orders':0,'current_or_unfinished_slot':current,'rows':rows}
        (out/'campaign.json').write_text(json.dumps(state,indent=2)+'\n')
    checkpoint()
    for i,job in enumerate(manifest['jobs']):
        if job['status']!='READY':rows.append({'mission':job['id'],'status':job['status'],'accepted':False,'new_customer_orders':0});continue
        job_path=ROOT/job['job']
        if digest(job_path)!=job['job_sha256']:raise ValueError('JOB_IDENTITY')
        for arm in orders[i%3]:
            checkpoint({'mission':job['id'],'arm':arm})
            folder=out/job['family']/arm;folder.mkdir(parents=True)
            before_wall=time.perf_counter();before_cpu=time.process_time();before_children=resource.getrusage(resource.RUSAGE_CHILDREN)
            freeze_ok()
            if arm=='B':
                cmd=['node',str(ROOT/'production/workbench.mjs'),str(job_path),str(folder/'native')]
                exit_code=invoke(cmd,folder);result_path=folder/'native/delivery/result.json';verification_path=folder/'native/verification.json';verification_exit=None
            else:
                module='incumbent.py' if arm=='A' else 'conventional.py'
                cmd=[sys.executable,str(ROOT/'production'/module),'--job',str(job_path),'--out',str(folder/'delivery')]
                exit_code=invoke(cmd,folder);result_path=folder/'delivery/result.json';verification_path=folder/'verification.json';verification_exit=None
                if result_path.is_file():verification_exit=invoke([sys.executable,str(ROOT/'production/verify.py'),'--job',str(job_path),'--result',str(result_path),'--out',str(verification_path)],folder)
            after_children=resource.getrusage(resource.RUSAGE_CHILDREN)
            wall=time.perf_counter()-before_wall;cpu=time.process_time()-before_cpu+after_children.ru_utime+after_children.ru_stime-before_children.ru_utime-before_children.ru_stime
            result=read_result(result_path)
            verification=read_result(verification_path)
            freeze_ok()
            binding=(digest(job_path)==job['job_sha256'] and verification.get('job_sha256')==job['job_sha256'] and result.get('job_sha256')==job['job_sha256'] and result_path.is_file() and verification.get('result_sha256')==digest(result_path))
            row={'mission':job['id'],'family':job['family'],'arm':arm,'phase':a.phase,'order':orders[i%3],'job_sha256':job['job_sha256'],'command':cmd,'exit_code':exit_code,'verification_exit_code':verification_exit,'accepted':exit_code==0 and binding and verification.get('status')=='COMPLETE','registered_job_binding':binding,'decision':verification.get('verdict','INCOMPLETE'),'producer_decision':result.get('decision'),'complete_service_wall_seconds':wall,'inclusive_cpu_seconds':cpu,'producer_wall_seconds':result.get('elapsed_wall_seconds'),'producer_cpu_seconds':result.get('cpu_seconds'),'human_minutes':None,'customer_minutes':None,'new_customer_orders':0,'result_path':str(result_path.relative_to(ROOT)) if result_path.is_file() else None,'result_sha256':digest(result_path) if result_path.is_file() else None,'verification_path':str(verification_path.relative_to(ROOT)) if verification_path.is_file() else None,'verification_sha256':digest(verification_path) if verification_path.is_file() else None}
            rows.append(row);(folder/'service-receipt.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ['family','arm','accepted','decision','complete_service_wall_seconds']}),flush=True)
            checkpoint()
            if digest(job_path)!=job['job_sha256']:raise ValueError('REGISTERED_JOB_CHANGED_AFTER_OPERATION')
    record={'schema':'agi-alpha-second-investment-confirmation/v1','started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':a.phase,'source_freeze_sha256':freeze_hash,'job_manifest_sha256':digest(manifest_path),'questions':len(manifest['jobs']),'new_customer_orders':0,'rows':rows,'notes':['Each full-lock substitution is one research question; three arms are matched evaluations, not new jobs.','Ordinary tools and shared wheel cache retained in every arm.','One run per arm; timing is descriptive, not generalized reliability or human effort.','Independent verification and native orchestration are included in complete service timing.','Initial capability and original evidence preserved unchanged; no application runtime started.']}
    record['partial']=False;(out/'campaign.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
