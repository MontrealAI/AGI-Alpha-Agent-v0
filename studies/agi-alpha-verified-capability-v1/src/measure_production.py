# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, json, resource, subprocess, sys, time, os, signal
from pathlib import Path
from acceptance import ROOT, in_study

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--job',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--route',choices=['native','direct'],required=True)
    args=parser.parse_args();job=in_study(args.job);out=in_study(args.out,must_exist=False);out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter();command=[sys.executable,str(ROOT/'src/production.py'),'--job',str(job),'--out',str(out/'payload'),'--route',args.route]
    with (out/'driver.stdout.txt').open('x') as stdout,(out/'driver.stderr.txt').open('x') as stderr:
        process=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr,start_new_session=True)
        (out/'process-group.json').write_text(json.dumps({'parent_pid':os.getpid(),'child_group_pid':process.pid})+'\n')
        try: code=process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=10);code=124;stderr.write('MEASURED_PRODUCTION_TIMEOUT; owned descendant group killed; no retry\n')
    child=resource.getrusage(resource.RUSAGE_CHILDREN)
    driver_cpu=time.process_time()
    receipt={'schema':'agi-alpha-complete-production-measurement/v1','command':command,'returncode':code,'wall_seconds':time.perf_counter()-started,
             'child_cpu_seconds':child.ru_utime+child.ru_stime,'measurement_driver_cpu_seconds':driver_cpu,
             'cpu_seconds':child.ru_utime+child.ru_stime+driver_cpu,'max_child_rss_kib':child.ru_maxrss,'descendant_cpu_complete':code!=124,
             'scope':'Producer interpreter startup, all waited subprocess descendants and measurement-driver CPU since process start. Parent campaign/select/serialization CPU measured separately.',
             'unmeasured':'Final receipt serialization after CPU sampling; no human attention or authoring inference estimate.'}
    (out/'measurement.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(code)
