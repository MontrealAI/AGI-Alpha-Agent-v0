#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def sha(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
 return json.loads(Path(path).read_text())
def exact_checks():
 checks=[]
 def require(condition,label):
  checks.append({'check':label,'pass':bool(condition)})
 for name in ['experiment-FREEZE.json','experiment-v11-FREEZE.json']:
  manifest=read(ROOT/'protocol'/name)
  for item in manifest['entries']:
   p=ROOT/item['path'];require(p.is_file() and p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],name+': '+item['path'])
 assumption=read(ROOT/'protocol/economics_freeze.json')
 for path,digest in assumption['files'].items():require(sha(ROOT/path)==digest,'economic assumption freeze: '+path)
 bridge=read(ROOT/'protocol/economics_bridge_freeze.json')
 archive=ROOT/'economics/history/initial_economics_v1.zip'
 with zipfile.ZipFile(archive) as original:
  for path,digest in bridge['files'].items():
   current=sha(ROOT/path)
   if path=='economics/run_economics.py' and current!=digest:
    require(hashlib.sha256(original.read(path)).hexdigest()==digest,'preserved original economic engine')
   else:require(current==digest,'economic bridge freeze: '+path)
 final_economics=read(ROOT/'economics/FINAL_ECONOMICS_FREEZE.json')
 for path,digest in final_economics['files'].items():require(sha(ROOT/path)==digest,'final economic source/output freeze: '+path)
 economic_manifest=read(ROOT/'economics/outputs/manifest.json')
 for name,digest in economic_manifest['files'].items():require(sha(ROOT/'economics/outputs'/name)==digest,'economic output: '+name)
 summary=read(ROOT/'economics/outputs/summary.json');provenance=summary['provenance']
 for field,path in [('engine_sha256','economics/run_economics.py'),('config_sha256','protocol/economics_config.json'),('bridge_sha256','outputs/economics_bridge.json')]:require(provenance[field]==sha(ROOT/path),'current economic provenance: '+field)
 correction_paths=provenance.get('correction_records') or [provenance['correction_record']]
 corrections=[read(ROOT/path) for path in correction_paths]
 require(any(provenance['engine_sha256']==entry.get('corrected_engine_sha256') for entry in corrections),'explicit current economic correction record')
 require(read(ROOT/'outputs/economics_bridge.json')['source_summary_sha256']==sha(ROOT/'outputs/summary.json'),'measured bridge identity')
 for p in (ROOT/'data').glob('source_manifest.json'):
  for item in read(p):require(sha(ROOT/'data/sources'/item['local'])==item['sha256'],'upstream snapshot '+item['local'])
 for filename in ['INDEPENDENT_EVIDENCE_AUDIT.json','INDEPENDENT_CORRECTION_AUDIT.json','INDEPENDENT_FINANCIAL_AUDIT.json','INDEPENDENT_SENSITIVITY_AUDIT.json']:
  audit=read(ROOT/'review'/filename);require(audit['status']=='PASS' and not audit['failures'],'saved independent report '+filename)
 require(summary['provenance']['business_outputs']=='SIMULATED' and summary['provenance']['live_paid_transactions']=='NOT RUN','economic evidence labels')
 return {'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','checks':len(checks),'failures':[c['check'] for c in checks if not c['pass']]}

def ignore(directory,names):
 return {name for name in names if name=='__pycache__' or name.endswith(('.pyc','.pyo','.png','.jpg','.jpeg','.gif','.aux','.log','.out','.bbl','.blg','.fdb_latexmk','.fls','.synctex.gz')) or name in ['.DS_Store','reruns']}

def stage(destination):
 destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
 for folder in ['companion','companion_v1_1','data','vendor','protocol','outputs','economics','review','evidence']:
  shutil.copytree(ROOT/folder,destination/folder,ignore=ignore)
 return destination

def invoke(args,cwd):
 environment=dict(os.environ);environment['PYTHONDONTWRITEBYTECODE']='1'
 result=subprocess.run(args,cwd=cwd,env=environment,capture_output=True,text=True,timeout=300)
 if result.returncode:
  raise RuntimeError('Command failed: '+str(args)+'\n'+result.stdout[-4000:]+'\n'+result.stderr[-4000:])
 return result.stdout

def auditor_checks():
 with tempfile.TemporaryDirectory(prefix='productive-capital-check-') as temporary:
  copy=stage(Path(temporary)/'study');results=[]
  for script,name in [('independent_evidence_audit.py','INDEPENDENT_EVIDENCE_AUDIT.json'),('independent_correction_audit.py','INDEPENDENT_CORRECTION_AUDIT.json'),('independent_financial_audit.py','INDEPENDENT_FINANCIAL_AUDIT.json'),('independent_sensitivity_audit.py','INDEPENDENT_SENSITIVITY_AUDIT.json')]:
   invoke([sys.executable,str(copy/'review'/script)],copy);r=read(copy/'review'/name);results.append({'name':name,'status':r['status'],'checks':r['checks'],'failures':r['failures']})
 return results

def replay(mode,output):
 if not output:raise ValueError('--output is required for replay and must name a new directory')
 destination=Path(output).expanduser().resolve()
 if destination.exists():raise ValueError('Replay destination already exists; original records will not be overwritten')
 try:destination.relative_to(ROOT)
 except ValueError:pass
 else:raise ValueError('Replay destination must be outside the immutable study directory')
 copy=stage(destination)
 if mode=='primary-replay':
  if not shutil.which('node'):raise RuntimeError('Node is unavailable; no automatic installation attempted')
  try:import numpy,scipy
  except ImportError as error:raise RuntimeError('NumPy/SciPy unavailable; no automatic installation attempted') from error
  result=invoke([sys.executable,str(copy/'companion/run.py'),'--out',str(copy/'rerun-primary')],copy)
  (copy/'primary-replay.log').write_text(result)
  outcome=read(copy/'rerun-primary/summary.json')
  report={'kind':'known-input timing replay, not fresh confirmation','output':str(copy/'rerun-primary'),'accepted_joint_runs':outcome['accepted_joint_runs'],'joint_runs':outcome['joint_runs'],'current_timing_totals':outcome['totals'],'original_records_preserved':True}
 elif mode=='corrective-replay':
  if not shutil.which('node'):raise RuntimeError('Node is unavailable; no automatic installation attempted')
  shutil.move(copy/'outputs/correction-confirmation',copy/'outputs/correction-confirmation-recorded')
  result=invoke([sys.executable,str(copy/'companion_v1_1/qualify.py')],copy);(copy/'corrective-replay.log').write_text(result);outcome=read(copy/'outputs/correction-confirmation/summary.json')
  report={'kind':'known-input corrective replay, not fresh confirmation','output':str(copy/'outputs/correction-confirmation'),'accepted':outcome['accepted'],'case_count':outcome['case_count'],'original_records_preserved':True}
 else:
  result=invoke([sys.executable,str(copy/'economics/run_economics.py'),'--output',str(copy/'rerun-economics')],copy);(copy/'economic-replay.log').write_text(result)
  expected=read(ROOT/'economics/outputs/manifest.json')['files'];mismatch=[name for name,digest in expected.items() if sha(copy/'rerun-economics'/name)!=digest]
  report={'kind':'deterministic economic scenario replay, still simulation','output':str(copy/'rerun-economics'),'compared_files':len(expected),'byte_mismatches':mismatch,'original_records_preserved':True}
  if mismatch:raise RuntimeError('Economic replay differs from recorded outputs: '+str(mismatch))
 (copy/'REPLAY_REPORT.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
 p=argparse.ArgumentParser(description='Read-only evidence checks or isolated explicit replays; no network, installation or transactions.')
 p.add_argument('mode',nargs='?',default='check',choices=['check','hashes','primary-replay','corrective-replay','economic-replay']);p.add_argument('--output');args=p.parse_args()
 try:
  exact=exact_checks()
  if exact['status']!='PASS':print(json.dumps(exact,indent=2));return 1
  if args.mode=='hashes':report=exact
  elif args.mode=='check':report={'exact':exact,'independent_recomputations':auditor_checks(),'timings_replayed':False,'paid_or_remote_actions':False}
  else:report=replay(args.mode,args.output)
  print(json.dumps(report,indent=2));return 0
 except Exception as error:print(json.dumps({'status':'ERROR','type':type(error).__name__,'message':str(error)},indent=2),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
